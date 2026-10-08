"""Maintain dashboard scopes and apply native subscription policies in place."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from fnmatch import fnmatchcase
import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit

from homeassistant import auth, const as ha_const
from homeassistant.components.lovelace.const import EVENT_LOVELACE_UPDATED
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_PANELS_UPDATED, EVENT_STATE_CHANGED
from homeassistant.core import (
    Event,
    EventStateChangedData,
    EventType,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    issue_registry as ir,
    label_registry as lr,
    translation,
)
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .benchmark import BenchmarkManager
from .compatibility import CompatibilityError
from .const import (
    CONTROL_DASHBOARD_LIVE,
    CONF_DASHBOARDS,
    CONF_DASHBOARD_CARDS,
    CONF_ALWAYS_FORWARD,
    CONTROL_RESOURCES,
    CONTROL_RESOURCE_DELAY,
    RESOURCE_DELAY_QUIET_MS,
    RESOURCE_DELAY_MAX_MS,
    RESOURCE_DELAY_LOAD_MS,
    RESOURCE_DELAY_IDLE_MS,
    CONF_EXCLUDE_GLOBS,
    CONF_EXTRA_ENTITIES,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_GLOBS,
    CONF_TARGET_MODE,
    CONF_USER_IDS,
    CONTROL_DEFAULTS,
    CONTROL_ENTITIES,
    CONTROL_GRAPHS,
    CONTROL_MOTION,
    CONTROL_MASTER,
    CONTROL_REGISTRIES,
    DOMAIN,
    MAINTENANCE_SECONDS,
    METRIC_SECONDS,
    SCAN_DEBOUNCE,
    TARGET_ALL,
    VERSION,
    RESOURCE_SHARED_TYPES,
    CONTROL_RESOURCE_PRELOAD, CONTROL_OFFSCREEN, CONTROL_IDLE,
    CONF_IDLE_AFTER, CONF_IDLE_REFRESH, IDLE_AFTER_MINUTES, IDLE_REFRESH_SECONDS,
)
from .graph_loading import GraphLoadingAdapter
from .panels import PanelContext
from .dashboard import (
    dashboard_titles,
    discovery_context,
    load_dashboard,
    protected_entities,
)
from .dependencies import DiscoveryResult, describe_problem, discover, discover_views
from .const import SETTINGS_DEFAULTS
from .resources import (ResourceAdapter, ResourceDependencies, async_resource_rows,
                        resource_dependencies, resource_view_dependencies, resource_report)
from .registry import RegistryAdapter, RegistryScope, registry_scope
from .websocket import ScopePolicy, SubscriptionAdapter
from .statistics import LiveStatistics
from .statistics_card import StatisticsCard, StatisticsCardError

_LOGGER = logging.getLogger(__name__)
# Reasons for one blocked card, most specific first.
_BLOCKER_PRIORITY = ("load", "auto_entities", "strategy", "template", "other")


class LoonaRuntime:
    """One singleton entry with serialized scans and persisted controls."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._policy_settings = self.settings
        self.controls = dict(CONTROL_DEFAULTS)
        self.entity_ids: frozenset[str] = frozenset()
        self.dashboard_live_entities: dict[str, frozenset[str]] = {}
        self.view_live_entities: dict[str, dict[str, frozenset[str]]] = {}
        self.reasons: dict[str, tuple[str, ...]] = {}
        self.excluded_reasons: dict[str, tuple[str, ...]] = {}
        self.dashboards: dict[str, DiscoveryResult] = {}
        self.unresolved: dict[str, frozenset[str]] = {}
        self.missing_extra_entities: frozenset[str] = frozenset()
        self.problems: tuple[str, ...] = ()
        # Readable dashboard / view / card labels for scan problems, with a reason code each.
        self.scan_blockers: dict[str, str] = {}
        # Selected dashboards Loona cannot read; they are served in full while the rest stay filtered.
        self.unfiltered_dashboards: tuple[str, ...] = ()
        self.warnings: tuple[str, ...] = ()
        self.entity_compatibility_problem: str | None = None
        self.panel_compatibility_problem: str | None = None
        self.bootstrap_compatibility_problem: str | None = None
        self.bootstrap_installed: bool | None = None
        self.registry_compatibility_problem: str | None = None
        self.last_scan: datetime | None = None
        self.scan_duration = 0.0
        self.live_statistics = LiveStatistics()
        self.statistics_card = StatisticsCard(hass, entry.entry_id)
        self.statistics_card_problem: str | None = None
        self.adapter: SubscriptionAdapter | None = None
        self.benchmark = BenchmarkManager(self)
        self.panel_context = PanelContext(hass, self._panel_changed)
        self.panel_context.resource_plan = self.resource_loading_plan
        self.panel_context.idle_policy = self.idle_policy
        self.panel_context.idle_refresh = self._refresh_idle
        self.registry_adapter: RegistryAdapter | None = None
        self.graph_adapter: GraphLoadingAdapter | None = None
        self.graph_compatibility_problem: str | None = None
        self.registry_scope = RegistryScope()
        self.resource_dependencies = ResourceDependencies()
        self.dashboard_resources: dict[str, ResourceDependencies] = {}
        self.view_resources: dict[str, dict[str, ResourceDependencies]] = {}
        self.resource_complete = False
        self.resource_adapter: ResourceAdapter | None = None
        self.resource_compatibility_problem: str | None = None
        self.resource_scan_problem: str | None = None
        self.resource_preview: dict[str, Any] = {}
        self.device_id: str | None = None
        self.dashboard_devices: dict[str, str] = {}
        self._store: Store[dict[str, bool]] = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}.controls"
        )
        self._control_lock = asyncio.Lock()
        self._listeners: set[Callable[[], None]] = set()
        self._unsubscribers: list[Callable[[], None]] = []
        self._debounce: Callable[[], None] | None = None
        self._scan_task: asyncio.Task[None] | None = None
        self._revision = 0
        self._force = False
        self._stopped = False
        self._reported_problems: dict[str, str] = {}
        self._failed_dashboards: set[str] = set()
        self.unknown_cards = False

    @property
    def settings(self) -> dict[str, Any]:
        """Options override initial selections without duplicating controls."""
        return {**self.entry.data, **self.entry.options}

    @property
    def selected_dashboards(self) -> tuple[str, ...]:
        return tuple(self.settings.get(CONF_DASHBOARDS, ()))

    @property
    def scope_problem(self) -> bool:
        return bool(self.problems)

    @property
    def compatibility_problem(self) -> str | None:
        return (
            self.entity_compatibility_problem
            or self.panel_compatibility_problem
            or self.bootstrap_compatibility_problem
            or self.registry_compatibility_problem
            or self.graph_compatibility_problem
            or self.resource_compatibility_problem
            or self.statistics_card_problem
        )

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    @callback
    def notify(self) -> None:
        self.panel_context.publish()
        for listener in tuple(self._listeners):
            listener()

    async def async_start(self) -> None:
        """Load controls before installing a hook and register invalidation."""
        self.panel_context.install()
        stored = await self._store.async_load()
        if stored:
            self.controls.update(
                {
                    key: stored[key]
                    for key in CONTROL_DEFAULTS
                    if isinstance(stored.get(key), bool)
                }
            )
        registry = dr.async_get(self.hass)
        self.device_id = registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Loona",
            manufacturer="Loona",
            model="Loona",
            sw_version=None,
        ).id
        for event_type in (
            EVENT_LOVELACE_UPDATED,
            EVENT_PANELS_UPDATED,
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            ar.EVENT_AREA_REGISTRY_UPDATED,
            fr.EVENT_FLOOR_REGISTRY_UPDATED,
            lr.EVENT_LABEL_REGISTRY_UPDATED,
            auth.EVENT_USER_UPDATED,
            auth.EVENT_USER_REMOVED,
        ):
            self._unsubscribers.append(
                self.hass.bus.async_listen(
                    cast(EventType[Any], event_type), self._invalidate
                )
            )
        self._unsubscribers.append(
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)
        )
        self._unsubscribers.append(
            async_track_time_interval(
                self.hass, self._maintenance, timedelta(seconds=MAINTENANCE_SECONDS)
            )
        )
        self._unsubscribers.append(
            async_track_time_interval(
                self.hass, self._metrics, timedelta(seconds=METRIC_SECONDS)
            )
        )
        await self.async_scan()
        adapter = SubscriptionAdapter(self.hass, self._policy(), self.live_statistics, self._dashboard_active, self._delivery_scope, self._idle)
        try:
            adapter.install()
        except CompatibilityError as err:
            self.entity_compatibility_problem = str(err)
        else:
            self.adapter = adapter
        registry_adapter = RegistryAdapter(
                self.hass,
                self._policy(CONTROL_REGISTRIES),
                self.registry_scope,
                self._registry_failed,
                self._dashboard_active,
            )
        try:
            registry_adapter.install()
        except CompatibilityError as err:
            self.registry_compatibility_problem = str(err)
        else:
            self.registry_adapter = registry_adapter
        graph_adapter = GraphLoadingAdapter(self)
        try:
            graph_adapter.install()
        except CompatibilityError as err:
            self.graph_compatibility_problem = str(err)
        else:
            self.graph_adapter = graph_adapter
        if self.resource_compatibility_problem is None:
            resource_adapter = ResourceAdapter(
                self.hass, self._policy(CONTROL_RESOURCES), self.resource_report,
                self._resources_failed,
                self._observe_resource_load,
                self._dashboard_active,
            )
            try:
                if self.resource_scan_problem is None:
                    await resource_adapter.async_probe()
                resource_adapter.install()
            except CompatibilityError as err:
                self.resource_compatibility_problem = str(err)
            else:
                self.resource_adapter = resource_adapter
        self._update_issues()

    async def async_update_statistics_card(self) -> None:
        """Ensure automatic presentation independently of the filtering adapters."""
        try:
            await self.statistics_card.set_enabled(True, tuple(self.settings.get(CONF_DASHBOARD_CARDS, ())))
        except StatisticsCardError as err:
            self.statistics_card_problem = str(err)
        else:
            self.statistics_card_problem = None
            if self.statistics_card.opted_out:
                self.hass.config_entries.async_update_entry(self.entry, options={**self.entry.options, CONF_DASHBOARD_CARDS: []})
        self._update_issues()
        self.notify()

    def _resource_modules(self) -> tuple[set[str], set[str]]:
        """Keep extra-module ownership separate from saved resource declarations."""
        from homeassistant.components import frontend
        manager = self.hass.data.get(frontend.DATA_EXTRA_MODULE_URL)
        extra = set(manager.urls) if manager else set()
        provided: set[str] = set()
        for url in extra:
            parsed = urlsplit(url)
            if not parsed.scheme and not parsed.netloc:
                provided.update(RESOURCE_SHARED_TYPES.get(parsed.path, ()))
        return extra, provided

    def resource_report(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate every newly installed resource using the published union."""
        extra, provided = self._resource_modules()
        self.resource_preview = resource_report(
            rows, self.resource_dependencies,
            self._policy_settings.get(CONF_ALWAYS_FORWARD, ()),
            provided,
        )
        # Modules are global for the page, including extra_module_url helpers.
        for row in self.resource_preview["resources"]:
            if row["url"] in extra:
                row.update(status="required", forwarded=True, reason="Shared frontend module")
        self._update_issues()
        return self.resource_preview

    async def async_resource_preview(self) -> dict[str, Any]:
        """Read the current native collection for the administrator preview."""
        return self.resource_report(await async_resource_rows(self.hass))

    def resource_loading_plan(self, connection: websocket_api.ActiveConnection, dashboard: str | None) -> dict[str, Any]:
        """Delay only verified optional files; new URLs remain immediate."""
        enabled = bool(self.resource_adapter is not None and self.resource_complete
                       and self.panel_compatibility_problem is None and self.bootstrap_installed is not False
                       and not self.resource_preview.get("unresolved_custom_types")
                       and self._dashboard_active(connection) and connection.user.is_active
                       and not self.panel_context.expanded(connection)
                       and self.controls[CONTROL_MASTER]
                       and (self.controls[CONTROL_RESOURCE_DELAY] or self.controls[CONTROL_RESOURCE_PRELOAD])
                       and (self._policy_settings.get(CONF_TARGET_MODE) == TARGET_ALL
                            or connection.user.id in self._policy_settings.get(CONF_USER_IDS, ())))
        if enabled and self.resource_adapter is not None:
            try:
                self.resource_adapter.check_ownership()
            except CompatibilityError:
                enabled = False
        dependencies = self.dashboard_resources.get(dashboard or "")
        if self.panel_context.delivery_dashboard(connection) == dashboard:
            view = self.panel_context.delivery_view(connection)
            dependencies = self.view_resources.get(dashboard or "", {}).get(view or "", dependencies)
        delayed: list[str] = []
        preload: list[str] = []
        if enabled and dependencies is not None:
            rows = self.resource_preview.get("resources", [])
            immediate, provided = self._resource_modules()
            report = resource_report(rows, dependencies, self._policy_settings.get(CONF_ALWAYS_FORWARD, ()), provided)
            delayed = [row["url"] for row in report["resources"] if row["type"] == "module"
                       and not row["forwarded"] and row["url"] not in immediate]
            preload = [row["url"] for row in report["resources"] if row["type"] == "module"
                       and row["status"] == "required" and row["url"].startswith(("/local/", "/hacsfiles/", "/uix/"))]
        return {"enabled": enabled and dependencies is not None and self.controls[CONTROL_RESOURCE_DELAY], "defer": delayed,
                "preload": preload if enabled and self.controls[CONTROL_RESOURCE_PRELOAD] else [],
                "quiet_ms": RESOURCE_DELAY_QUIET_MS, "max_ms": RESOURCE_DELAY_MAX_MS,
                "load_ms": RESOURCE_DELAY_LOAD_MS, "idle_ms": RESOURCE_DELAY_IDLE_MS}

    def idle_policy(self, connection: websocket_api.ActiveConnection) -> dict[str, Any]:
        """Only eligible selected-account entity feeds may enter idle mode."""
        allowed = bool(not self.benchmark.native(connection) and self.adapter is not None and self.panel_compatibility_problem is None
                       and self.controls[CONTROL_IDLE] and self.panel_context.delivery_dashboard(connection) is not None
                       and connection.user.is_active and self._policy().scope_for(connection.user.id) is not None)
        from .config_flow import validate_idle_settings
        values = {CONF_IDLE_AFTER: self._policy_settings.get(CONF_IDLE_AFTER, IDLE_AFTER_MINUTES),
                  CONF_IDLE_REFRESH: self._policy_settings.get(CONF_IDLE_REFRESH, IDLE_REFRESH_SECONDS)}
        try:
            values = validate_idle_settings(values)
        except ValueError:
            allowed = False
            values = {CONF_IDLE_AFTER: IDLE_AFTER_MINUTES, CONF_IDLE_REFRESH: IDLE_REFRESH_SECONDS}
        return {"enabled": allowed, "version": VERSION,
                "after_ms": values[CONF_IDLE_AFTER] * 60000, "refresh_seconds": values[CONF_IDLE_REFRESH]}

    def _idle(self, connection: websocket_api.ActiveConnection) -> bool:
        """The client idle flag grants no new access or scope."""
        return self.panel_context.idle(connection) and self.idle_policy(connection)["enabled"]

    @callback
    def _refresh_idle(self, connection: websocket_api.ActiveConnection) -> None:
        if self.adapter is not None and self._idle(connection):
            try:
                self.adapter.refresh_idle(connection)
            except CompatibilityError as err:
                self.entity_compatibility_problem = str(err)
                self.adapter.uninstall()
                self.adapter = None
                self.notify()

    def _observe_resource_load(self, connection: Any, available: int, sent: int) -> None:
        if self.adapter is not None:
            self.adapter.observe_resources(connection, available, sent)
        pending = self.panel_context.note_resources(connection, {"available": available, "sent": sent})
        rows = self.live_statistics.page_loads
        # Fill a page load recorded before its card files, unless a newer load replaced it.
        if pending and rows.get(pending[0]) is pending[1]:
            pending[1]["resources"] = self.panel_context.resource_counts(connection)

    @callback
    def _resources_failed(self, error: CompatibilityError) -> None:
        self.resource_compatibility_problem = str(error)
        self.resource_adapter = None
        self._update_issues()
        self.notify()

    @callback
    def _invalidate(self, event: Event) -> None:
        self.request_scan()

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Ordinary value changes and telemetry updates do not trigger scans."""
        old, new = event.data["old_state"], event.data["new_state"]
        if (
            old is None
            or new is None
            or old.attributes.get("entity_id") != new.attributes.get("entity_id")
        ):
            self.request_scan()

    @callback
    def _maintenance(self, now: datetime) -> None:
        """Native YAML mtime checks and deleted selections have a bounded delay."""
        self.request_scan()

    @callback
    def _metrics(self, now: datetime) -> None:
        self.live_statistics.sample()
        self.notify()

    @callback
    def async_reset_live_statistics(self) -> None:
        """Reset this runtime's counters and rates, preserving all controls."""
        self.live_statistics.reset()
        self.notify()

    @callback
    def request_scan(self) -> None:
        """Collapse event bursts while invalidating any in-flight candidate."""
        if self._stopped:
            return
        self._revision += 1
        if self._scan_task is not None and not self._scan_task.done():
            return
        if self._debounce:
            self._debounce()
        self._debounce = async_call_later(self.hass, SCAN_DEBOUNCE, self._begin_scan)

    @callback
    def _begin_scan(self, now: datetime | None = None) -> None:
        self._debounce = None
        if not self._stopped and (self._scan_task is None or self._scan_task.done()):
            self._scan_task = self.hass.async_create_task(
                self._scan_loop(), "Loona dashboard scan"
            )

    async def async_scan(self, *, force: bool = False) -> None:
        """Join the scan worker rather than starting overlapping loaders."""
        if self._stopped:
            return
        self._revision += 1
        self._force |= force
        if self._debounce:
            self._debounce()
            self._debounce = None
        self._begin_scan()
        assert self._scan_task is not None
        await asyncio.shield(self._scan_task)

    async def _scan_loop(self) -> None:
        """Discard a candidate if configuration changed during a native load."""
        while not self._stopped:
            await translation.async_get_translations(self.hass, self.hass.config.language, "dashboard", {"onboarding"})
            revision, force = self._revision, self._force
            self._force = False
            started = perf_counter()
            settings = self.settings
            context = discovery_context(self.hass)
            results: dict[str, DiscoveryResult] = {}
            configs: list[dict[str, Any]] = []
            dashboard_resources: dict[str, ResourceDependencies] = {}
            view_resources: dict[str, dict[str, ResourceDependencies]] = {}
            view_entities: dict[str, dict[str, frozenset[str]]] = {}
            problems: list[str] = []
            warnings: list[str] = []
            reasons: dict[str, set[str]] = {}
            excluded: dict[str, tuple[str, ...]] = {}
            blockers: dict[str, str] = {}
            titles = dashboard_titles(self.hass)
            for key in settings.get(CONF_DASHBOARDS, ()):
                title = titles.get(key, key)
                try:
                    config = await load_dashboard(self.hass, key, force=force)
                    configs.append(config)
                    dashboard_resources[key] = resource_dependencies([config])
                    view_resources[key] = resource_view_dependencies(config)
                    result = discover(config, context)
                    if result.complete:
                        view_entities[key] = discover_views(config, context)
                    for problem in result.problems:
                        place, reason = describe_problem(config, problem)
                        label = " / ".join(part for part in (title, place) if part)
                        # One card can raise several problems; keep the most specific reason.
                        if _BLOCKER_PRIORITY.index(reason) < _BLOCKER_PRIORITY.index(blockers.get(label, "other")):
                            blockers[label] = reason
                        else:
                            blockers.setdefault(label, reason)
                    self._failed_dashboards.discard(key)
                except Exception as err:
                    blockers[title] = "load"
                    # Failed boards are retained as incomplete, never silently dropped.
                    if key not in self._failed_dashboards:
                        _LOGGER.warning("Dashboard load failed (%s); filtering is bypassed", type(err).__name__)
                        _LOGGER.debug("Dashboard load failure details", exc_info=True)
                        self._failed_dashboards.add(key)
                    result = DiscoveryResult(
                        frozenset(),
                        {},
                        (
                            "Dashboard could not be loaded; save its configuration and check the selection",
                        ),
                        (),
                    )
                results[key] = result
                warnings.extend(result.warnings)
            # Each connection reports its dashboard, so an unreadable dashboard is served in full
            # like an unselected one while the readable ones keep their union. Only a selection
            # with nothing readable stops filtering everywhere.
            readable = {key: result for key, result in results.items() if result.complete}
            included = readable or results
            unfiltered = tuple(sorted(set(results) - set(readable))) if readable else ()
            if results and not readable:
                problems.extend(problem for result in results.values() for problem in result.problems)
            for key, result in included.items():
                for entity_id, locations in result.reasons.items():
                    reasons.setdefault(entity_id, set()).update(
                        f"{key}:{location}" for location in locations
                    )
            if not results:
                problems.append("Select at least one dashboard")
            for entity_id in settings.get(CONF_EXTRA_ENTITIES, ()):
                reasons.setdefault(entity_id, set()).add("extra entity")
            for entity_id in context.entity_ids:
                if entity_id.split(".")[0] in settings.get(
                    CONF_INCLUDE_DOMAINS, ()
                ) or any(
                    fnmatchcase(entity_id, pattern)
                    for pattern in settings.get(CONF_INCLUDE_GLOBS, ())
                ):
                    reasons.setdefault(entity_id, set()).add("include rule")
            for entity_id in tuple(reasons):
                if any(
                    fnmatchcase(entity_id, pattern)
                    for pattern in settings.get(CONF_EXCLUDE_GLOBS, ())
                ):
                    if any(
                        entity_id in result.entity_ids for result in included.values()
                    ):
                        warnings.append("An exclusion removes a dashboard dependency")
                    excluded[entity_id] = tuple(sorted(reasons.pop(entity_id)))
            if not reasons:
                problems.append("The dashboard scope is empty")
            self.live_statistics.ignored = protected_entities(self.hass, self.entry.entry_id)
            # The app's sidebar, avatar and maps share the dashboard connection.
            for entity_id in context.entity_ids:
                if entity_id.split(".", 1)[0] in {"person", "update", "zone"}:
                    reasons.setdefault(entity_id, set()).add("Home Assistant app context")
                    excluded.pop(entity_id, None)
            valid_targets = True
            if settings.get(CONF_TARGET_MODE) != TARGET_ALL:
                users = {
                    user.id
                    for user in await self.hass.auth.async_get_users()
                    if user.is_active and not user.system_generated
                }
                targets = set(settings.get(CONF_USER_IDS, ()))
                if not targets or not targets <= users:
                    valid_targets = False
                    problems.append("Select current active accounts in Loona options")
            # Lovelace loads modules once per page, so retain dependencies of
            # unselected dashboards too. A failed load keeps the full file list.
            resource_configs = list(configs)
            resources_complete = bool(results) and len(configs) == len(results)
            resource_scan_problem = None
            for key in dashboard_titles(self.hass):
                if key in results:
                    continue
                try:
                    from .dashboard import load_resource_dashboard
                    resource_configs.append(await load_resource_dashboard(self.hass, key, force=force))
                except Exception as err:
                    resources_complete = False
                    resource_scan_problem = f"A native dashboard could not be loaded ({type(err).__name__})"
                    _LOGGER.debug("Resource dependency scan failed; all files are retained", exc_info=err)
            resource_error = None
            try:
                resource_rows = await async_resource_rows(self.hass)
            except CompatibilityError as err:
                resource_error = err
                resource_rows = None
            if revision != self._revision:
                continue
            self.dashboards = results
            self.unresolved = {
                key: result.entity_ids - context.entity_ids
                for key, result in results.items()
            }
            self.missing_extra_entities = frozenset(settings.get(CONF_EXTRA_ENTITIES, ())) - context.entity_ids
            self.reasons = {key: tuple(sorted(value)) for key, value in reasons.items()}
            self.excluded_reasons = excluded
            self.entity_ids = frozenset(reasons)
            pinned = {entity_id for entity_id, locations in reasons.items()
                      if locations & {"extra entity", "include rule", "Home Assistant app context"}}
            self.dashboard_live_entities = {key: frozenset((result.entity_ids | pinned) & self.entity_ids)
                                           for key, result in results.items() if result.complete}
            self.view_live_entities = {key: {route: frozenset((entities | pinned) & self.entity_ids)
                                             for route, entities in views.items()}
                                       for key, views in view_entities.items()}
            self.registry_scope = registry_scope(self.hass, self.entity_ids, included.values())
            self.resource_dependencies = resource_dependencies(resource_configs)
            self.dashboard_resources = dashboard_resources
            self.view_resources = view_resources
            self.resource_scan_problem = resource_scan_problem
            self.resource_complete = resources_complete and valid_targets and not self.resource_dependencies.dynamic
            self.unknown_cards = any(result.unknown_cards for result in results.values())
            self._policy_settings = settings
            self.problems, self.warnings = (
                tuple(sorted(set(problems))),
                tuple(sorted(set(warnings))),
            )
            self.scan_blockers = blockers
            self.unfiltered_dashboards = unfiltered
            self.scan_duration = round((perf_counter() - started) * 1000, 2)
            if not self.problems:
                self.last_scan = dt_util.utcnow()
            self.resource_preview = {}
            if resource_rows is not None:
                self.resource_report(resource_rows)
            elif resource_error:
                # A temporary native load error must not retire a valid adapter.
                self.resource_complete = False
                self.resource_scan_problem = str(resource_error)
                _LOGGER.debug("Resource preview unavailable; will retry on the next scan", exc_info=resource_error)
            self._sync_devices()
            self._apply_policy()
            self._update_issues()
            self.notify()
            if revision == self._revision:
                return

    @callback
    def _sync_devices(self) -> None:
        """Create selected dashboard children; the entity platform removes old ones."""
        assert self.device_id is not None
        registry, titles = dr.async_get(self.hass), dashboard_titles(self.hass)
        for key in self.selected_dashboards:
            identifiers = {(DOMAIN, f"{self.entry.entry_id}:dashboard:{key}")}
            create_child = getattr(registry, "async_get_or_create_child", None)
            if create_child is not None:
                device = create_child(
                    config_entry_id=self.entry.entry_id, identifiers=identifiers,
                    name=titles.get(key, key), parent_device_id=self.device_id,
                )
            else:
                device = registry.async_get_or_create(
                    config_entry_id=self.entry.entry_id, identifiers=identifiers,
                    name=titles.get(key, key),
                    via_device=(DOMAIN, self.entry.entry_id),
                )
            self.dashboard_devices[key] = device.id

    def _policy(self, control: str = CONTROL_ENTITIES) -> ScopePolicy:
        settings = self._policy_settings
        return ScopePolicy(
            entity_ids=self.entity_ids,
            user_ids=frozenset(settings.get(CONF_USER_IDS, ())),
            all_users=settings.get(CONF_TARGET_MODE) == TARGET_ALL,
            enabled=self.controls[CONTROL_MASTER] and self.controls[control],
            complete=self.resource_complete if control == CONTROL_RESOURCES else not self.problems,
        )

    def filtered_dashboards(self) -> tuple[str, ...]:
        """Selected dashboards Loona filters; unreadable ones behave as unselected."""
        return tuple(key for key in self._policy_settings.get(CONF_DASHBOARDS, ()) if key not in self.unfiltered_dashboards)

    def _dashboard_active(self, connection: websocket_api.ActiveConnection) -> bool:
        """Native benchmark passes bypass only their own connection."""
        return self.panel_context.active(connection) and not self.benchmark.native(connection)

    def _delivery_scope(self, connection: websocket_api.ActiveConnection, retained: frozenset[str]) -> frozenset[str]:
        """Keep the active view and shared rules live; dialogs refresh the union."""
        if not self.controls[CONTROL_DASHBOARD_LIVE]:
            return retained
        dashboard = self.panel_context.delivery_dashboard(connection)
        fallback = self.dashboard_live_entities.get(dashboard or "", retained)
        view = self.panel_context.delivery_view(connection)
        return self.view_live_entities.get(dashboard or "", {}).get(view or "", fallback)

    def bootstrap_policy(self) -> dict[str, Any]:
        """Delay startup only where an available filter can reduce initial data."""
        from .bootstrap import route_key

        useful = any(adapter is not None and (policy := self._policy(control)).enabled
                     and policy.complete and bool(policy.entity_ids)
                     for control, adapter in ((CONTROL_ENTITIES, self.adapter),
                                              (CONTROL_REGISTRIES, self.registry_adapter),
                                              (CONTROL_RESOURCES, self.resource_adapter)))
        paths = self.filtered_dashboards()
        useful |= bool(self.resource_adapter is not None and self.resource_complete
                       and self.controls[CONTROL_MASTER]
                       and (self.controls[CONTROL_RESOURCE_DELAY] or self.controls[CONTROL_RESOURCE_PRELOAD]))
        return {"enabled": useful and bool(paths), "routes": sorted(route_key(path) for path in paths), "benchmark": True}

    @callback
    def _panel_changed(self, connection: websocket_api.ActiveConnection) -> None:
        """Restore native data before a non-dashboard panel's next request."""
        if self.adapter is not None:
            try:
                self.adapter.refresh_connection(connection)
                if (self.panel_context.active(connection)
                        and self.adapter.policy.scope_for(connection.user.id) is not None
                        and self.adapter.needs_resubscribe(connection)):
                    self.panel_context.request_resubscribe(connection)
            except CompatibilityError as err:
                self.entity_compatibility_problem = str(err)
                self.adapter.uninstall()
                self.adapter = None
        if self.registry_adapter is not None:
            try:
                self.registry_adapter.refresh_connection(connection)
            except CompatibilityError as err:
                self.registry_adapter.fail(err)
        self._update_issues()
        self.notify()

    @callback
    def _apply_policy(self) -> None:
        if self.adapter is not None:
            try:
                self.adapter.set_policy(self._policy())
            except CompatibilityError as err:
                self.entity_compatibility_problem = str(err)
                self.adapter.uninstall()
                self.adapter = None
            else:
                self.entity_compatibility_problem = None
        if self.registry_adapter is not None:
            try:
                self.registry_adapter.set_policy(
                    self._policy(CONTROL_REGISTRIES), self.registry_scope
                )
            except CompatibilityError as err:
                self.registry_adapter.fail(err)

        if self.resource_adapter is not None:
            try:
                self.resource_adapter.set_policy(self._policy(CONTROL_RESOURCES))
            except CompatibilityError as err:
                self.resource_adapter.fail(err)

        self.panel_context.set_dashboards(frozenset(self.filtered_dashboards()))

    @callback
    def _registry_failed(self, error: CompatibilityError) -> None:
        self.registry_compatibility_problem = str(error)
        self.registry_adapter = None
        self._update_issues()
        self.notify()

    @property
    def available_controls(self) -> frozenset[str]:
        """Offer controls only for adapters whose capability probes passed."""
        controls = {CONTROL_MASTER}
        if self.adapter is not None:
            controls.add(CONTROL_ENTITIES)
            if self.panel_compatibility_problem is None:
                controls.add(CONTROL_DASHBOARD_LIVE)
                controls.add(CONTROL_IDLE)
        if self.registry_adapter is not None:
            controls.add(CONTROL_REGISTRIES)
        if self.resource_adapter is not None:
            controls.add(CONTROL_RESOURCES)
            if self.panel_compatibility_problem is None and self.bootstrap_installed is not False:
                controls.add(CONTROL_RESOURCE_DELAY)
                controls.add(CONTROL_RESOURCE_PRELOAD)
        if self.graph_adapter is not None:
            controls.update((CONTROL_GRAPHS, CONTROL_MOTION, CONTROL_OFFSCREEN))
        return frozenset(controls)

    async def async_set_control(self, key: str, enabled: bool) -> None:
        """Persist a single source of truth and reconcile existing listeners."""
        if key not in self.available_controls or not isinstance(enabled, bool):
            raise ValueError("Invalid Loona control")
        await self.async_set_controls({key: enabled})

    async def async_restore_defaults(self, *, expected: dict[str, bool], expected_settings: dict[str, Any]) -> None:
        """Restore unconfigured selections and persisted controls without reinstalling."""
        async with self._control_lock:
            if expected != self.controls or expected_settings != self.settings:
                raise ValueError("conflict")
            await self._store.async_save(dict(CONTROL_DEFAULTS))
            self.controls = dict(CONTROL_DEFAULTS)
            options = {key: list(value) if isinstance(value, list) else value for key, value in SETTINGS_DEFAULTS.items()}
            self.hass.config_entries.async_update_entry(self.entry, options=options)
            await self.async_scan(force=True)
            await self.async_update_statistics_card()
            self.async_reset_live_statistics()

    async def async_set_controls(self, changes: dict[str, bool], *, expected: dict[str, bool] | None = None, expected_settings: dict[str, Any] | None = None) -> None:
        """Persist a validated card section once, preserving native switches."""
        if set(changes) - self.available_controls or any(not isinstance(v, bool) for v in changes.values()):
            raise ValueError("Invalid Loona control")
        async with self._control_lock:
            if (expected is not None and expected != self.controls) or (expected_settings is not None and expected_settings != self.settings):
                raise ValueError("conflict")
            candidate = {**self.controls, **changes}
            await self._store.async_save(candidate)
            self.controls = candidate
            self._apply_policy()
            self._update_issues()
            self.notify()

    @callback
    def _update_issues(self) -> None:
        """Retire legacy Repairs and log changes in feature availability."""
        for key in ("compatibility", "scope", "exclusion", "resources"):
            ir.async_delete_issue(self.hass, DOMAIN, f"{self.entry.entry_id}_{key}")
        for feature in ("entity", "panel", "bootstrap", "registry", "graph", "resource", "statistics_card", "resource_scan"):
            attribute = feature + "_problem" if feature in {"statistics_card", "resource_scan"} else feature + "_compatibility_problem"
            problem = getattr(self, attribute)
            if feature == "resource_scan" and not (self.controls[CONTROL_MASTER] and self.controls[CONTROL_RESOURCES]):
                problem = None
            previous = self._reported_problems.get(feature)
            if problem and problem != previous:
                _LOGGER.warning("Loona %s unavailable on Core %s: %s", feature, ha_const.__version__, problem)
                self._reported_problems[feature] = problem
            elif not problem and previous:
                _LOGGER.info("Loona %s recovered", feature)
                self._reported_problems.pop(feature, None)

    def notice_report(self) -> list[dict[str, Any]]:
        """Describe detected conditions without publishing HA notifications."""
        notices: list[dict[str, Any]] = []

        def add(code: str, active: Any, *, severity: str = "warning", items: Any = (), **extra: Any) -> None:
            if active:
                notices.append({"code": code, "severity": severity, "items": sorted(set(items)), **extra})

        for feature in ("entity", "panel", "bootstrap", "registry", "graph", "resource"):
            add(feature + "_compatibility", getattr(self, feature + "_compatibility_problem"))
        add("card_installation", self.statistics_card_problem)
        filtering = self.controls[CONTROL_MASTER] and (
            self.controls[CONTROL_ENTITIES] or self.controls[CONTROL_REGISTRIES])
        add("scan_incomplete", filtering and self.problems, items=self.scan_blockers, reasons=dict(self.scan_blockers))
        add("unfiltered_dashboards", filtering and self.unfiltered_dashboards, items=self.scan_blockers,
            reasons=dict(self.scan_blockers))
        missing = set().union(*self.unresolved.values()) if self.unresolved else set()
        missing.update(self.missing_extra_entities)
        add("missing_entities", missing, items=missing)
        excluded = set(self.excluded_reasons) & set().union(
            *(result.entity_ids for result in self.dashboards.values()))
        add("excluded_dependencies", filtering and excluded, items=excluded)
        add("unknown_cards", filtering and self.unknown_cards, severity="info")
        if self.controls[CONTROL_MASTER] and self.controls[CONTROL_RESOURCES]:
            add("resource_scan", self.resource_scan_problem)
            report = self.resource_preview
            add("unmatched_resources", report.get("unresolved_custom_types"), severity="info",
                items=report.get("unresolved_custom_types", ()))
            add("dynamic_resources", report.get("dynamic_configuration"), severity="info")
            add("stale_resources", report.get("stale_exceptions"), items=report.get("stale_exceptions", ()))
        return notices

    def metrics(self) -> dict[str, Any]:
        """Entity count estimates use current state IDs, not transport bytes."""
        current = set(self.hass.states.async_entity_ids())
        scoped = len(current & self.entity_ids)
        return {
            **self.live_statistics.metrics(),
            "warnings": sum(item["severity"] == "warning" for item in self.notice_report()),
            "version": VERSION,
            "union_entities": len(self.entity_ids),
            "current_scope": scoped,
            "reduction_estimate": round(100 * (1 - scoped / len(current)), 1)
            if current
            else 0,
            "managed_subscriptions": self.adapter.managed_count if self.adapter else 0,
            "filtered_subscriptions": self.adapter.filtered_count
            if self.adapter
            else 0,
            "last_scan": self.last_scan,
            "scan_duration": self.scan_duration,
        }

    async def async_stop(self) -> None:
        """Cancel work before restoring subscriptions and releasing references."""
        self._stopped = True
        self.benchmark.stop()
        if self._debounce:
            self._debounce()
            self._debounce = None
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        if self._scan_task is not None and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        self.panel_context.disable_clients()
        if self.adapter:
            self.adapter.uninstall()
            self.adapter = None
        if self.registry_adapter:
            self.registry_adapter.uninstall()
            self.registry_adapter = None
        if self.resource_adapter:
            self.resource_adapter.uninstall()
            self.resource_adapter = None
        if self.graph_adapter:
            self.graph_adapter.uninstall()
            self.graph_adapter = None
        self.panel_context.uninstall()
        self._listeners.clear()
        self.statistics_card.unload()
        self._update_issues()


if TYPE_CHECKING:
    type LoonaConfigEntry = ConfigEntry[LoonaRuntime]
else:
    # Core 2024.5 ConfigEntry is not generic at runtime.
    LoonaConfigEntry = ConfigEntry
