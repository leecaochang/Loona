"""Maintain dashboard scopes and apply native subscription policies in place."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from fnmatch import fnmatchcase
import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

from homeassistant import auth, const as ha_const
from homeassistant.components.lovelace.const import EVENT_LOVELACE_UPDATED
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
)
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .compatibility import CompatibilityError
from .const import (
    CONF_DASHBOARDS,
    CONF_ALWAYS_FORWARD,
    CONTROL_RESOURCES,
    RESOURCE_CORE_VERSIONS,
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
    REGISTRY_CORE_VERSIONS,
    FRONTEND_CORE_VERSIONS,
    CONTROL_MASTER,
    CONTROL_REGISTRIES,
    DOMAIN,
    MAINTENANCE_SECONDS,
    METRIC_SECONDS,
    SCAN_DEBOUNCE,
    TARGET_ALL,
    VERSION,
)
from .graph_loading import GraphLoadingAdapter
from .dashboard import (
    dashboard_titles,
    discovery_context,
    load_dashboard,
    protected_entities,
)
from .dependencies import DiscoveryResult, discover
from .resources import (ResourceAdapter, ResourceDependencies, async_resource_rows,
                        resource_dependencies, resource_report)
from .registry import RegistryAdapter, RegistryScope, registry_scope
from .websocket import ScopePolicy, SubscriptionAdapter
from .statistics import LiveStatistics
from .statistics_card import StatisticsCard, StatisticsCardError

_LOGGER = logging.getLogger(__name__)


class LoonaRuntime:
    """One singleton entry with serialized scans and persisted controls."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._policy_settings = self.settings
        self.controls = dict(CONTROL_DEFAULTS)
        self.entity_ids: frozenset[str] = frozenset()
        self.reasons: dict[str, tuple[str, ...]] = {}
        self.excluded_reasons: dict[str, tuple[str, ...]] = {}
        self.dashboards: dict[str, DiscoveryResult] = {}
        self.unresolved: dict[str, frozenset[str]] = {}
        self.problems: tuple[str, ...] = ()
        self.warnings: tuple[str, ...] = ()
        self.entity_compatibility_problem: str | None = None
        self.registry_compatibility_problem: str | None = None
        self.last_scan: datetime | None = None
        self.scan_duration = 0.0
        self.live_statistics = LiveStatistics()
        self.statistics_card = StatisticsCard(hass, entry.entry_id)
        self.statistics_card_problem: str | None = None
        self.adapter: SubscriptionAdapter | None = None
        self.registry_adapter: RegistryAdapter | None = None
        self.graph_adapter: GraphLoadingAdapter | None = None
        self.graph_compatibility_problem: str | None = None
        self.registry_scope = RegistryScope()
        self.resource_dependencies = ResourceDependencies()
        self.resource_complete = False
        self.resource_adapter: ResourceAdapter | None = None
        self.resource_compatibility_problem: str | None = None
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
        for listener in tuple(self._listeners):
            listener()

    async def async_start(self) -> None:
        """Load controls before installing a hook and register invalidation."""
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
            model="Dashboard entity filtering",
            sw_version=VERSION,
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
        adapter = SubscriptionAdapter(self.hass, self._policy(), self.live_statistics)
        try:
            adapter.install()
        except CompatibilityError as err:
            self.entity_compatibility_problem = str(err)
        else:
            self.adapter = adapter
        if ha_const.__version__ in REGISTRY_CORE_VERSIONS:
            registry_adapter = RegistryAdapter(
                self.hass,
                self._policy(CONTROL_REGISTRIES),
                self.registry_scope,
                self._registry_failed,
            )
            try:
                registry_adapter.install()
            except CompatibilityError as err:
                self.registry_compatibility_problem = str(err)
            else:
                self.registry_adapter = registry_adapter
        if ha_const.__version__ in FRONTEND_CORE_VERSIONS:
            graph_adapter = GraphLoadingAdapter(self)
            try:
                graph_adapter.install()
            except CompatibilityError as err:
                self.graph_compatibility_problem = str(err)
            else:
                self.graph_adapter = graph_adapter
        if (ha_const.__version__ in RESOURCE_CORE_VERSIONS
            and self.resource_compatibility_problem is None):
            resource_adapter = ResourceAdapter(
                self.hass, self._policy(CONTROL_RESOURCES), self.resource_report,
                self._resources_failed,
                self._observe_resource_load,
            )
            try:
                resource_adapter.install()
            except CompatibilityError as err:
                self.resource_compatibility_problem = str(err)
            else:
                self.resource_adapter = resource_adapter
        self._update_issues()

    async def async_update_statistics_card(self) -> None:
        """Ensure automatic presentation independently of the filtering adapters."""
        if self.statistics_card.enabled:
            return
        try:
            await self.statistics_card.set_enabled(True)
        except StatisticsCardError as err:
            self.statistics_card_problem = str(err)
        else:
            self.statistics_card_problem = None
        self._update_issues()
        self.notify()

    def resource_report(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate every newly installed resource using the published union."""
        self.resource_preview = resource_report(
            rows, self.resource_dependencies,
            self._policy_settings.get(CONF_ALWAYS_FORWARD, ()),
        )
        self._update_issues()
        return self.resource_preview

    async def async_resource_preview(self) -> dict[str, Any]:
        """Read the current native collection for the administrator preview."""
        return self.resource_report(await async_resource_rows(self.hass))

    def _observe_resource_load(self, connection: Any, available: int, sent: int) -> None:
        if self.adapter is not None:
            self.adapter.observe_resources(connection, available, sent)

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
            revision, force = self._revision, self._force
            self._force = False
            started = perf_counter()
            settings = self.settings
            context = discovery_context(self.hass)
            results: dict[str, DiscoveryResult] = {}
            configs: list[dict[str, Any]] = []
            problems: list[str] = []
            warnings: list[str] = []
            reasons: dict[str, set[str]] = {}
            excluded: dict[str, tuple[str, ...]] = {}
            for key in settings.get(CONF_DASHBOARDS, ()):
                try:
                    config = await load_dashboard(self.hass, key, force=force)
                    configs.append(config)
                    result = discover(config, context)
                except Exception as err:
                    # Failed boards are retained as incomplete, never silently dropped.
                    _LOGGER.debug("Dashboard load failed (%s)", type(err).__name__)
                    result = DiscoveryResult(
                        frozenset(),
                        {},
                        (
                            "Dashboard could not be loaded; save its configuration and check the selection",
                        ),
                        (),
                    )
                results[key] = result
                problems.extend(result.problems)
                warnings.extend(result.warnings)
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
                        entity_id in result.entity_ids for result in results.values()
                    ):
                        warnings.append("An exclusion removes a dashboard dependency")
                    excluded[entity_id] = tuple(sorted(reasons.pop(entity_id)))
            if not reasons:
                problems.append("The dashboard scope is empty")
            self.live_statistics.ignored = protected_entities(self.hass, self.entry.entry_id)
            for entity_id in self.live_statistics.ignored:
                reasons.setdefault(entity_id, set()).add("Loona control or statistic")
                excluded.pop(entity_id, None)
            if settings.get(CONF_TARGET_MODE) != TARGET_ALL:
                users = {
                    user.id
                    for user in await self.hass.auth.async_get_users()
                    if user.is_active and not user.system_generated
                }
                targets = set(settings.get(CONF_USER_IDS, ()))
                if not targets or not targets <= users:
                    problems.append("Select current active accounts in Loona options")
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
            self.reasons = {key: tuple(sorted(value)) for key, value in reasons.items()}
            self.excluded_reasons = excluded
            self.entity_ids = frozenset(reasons)
            if ha_const.__version__ in REGISTRY_CORE_VERSIONS:
                self.registry_scope = registry_scope(
                    self.hass, self.entity_ids, results.values()
                )
            self.resource_dependencies = resource_dependencies(configs)
            self.resource_complete = bool(results) and len(configs) == len(results) and not any(
                "Select current active accounts" in problem for problem in problems
            )
            self._policy_settings = settings
            self.problems, self.warnings = (
                tuple(sorted(set(problems))),
                tuple(sorted(set(warnings))),
            )
            self.scan_duration = round((perf_counter() - started) * 1000, 2)
            if not self.problems:
                self.last_scan = dt_util.utcnow()
            self.resource_preview = {}
            if resource_rows is not None:
                self.resource_report(resource_rows)
            elif resource_error and ha_const.__version__ in RESOURCE_CORE_VERSIONS:
                if self.resource_adapter is not None:
                    self.resource_adapter.fail(resource_error)
                else:
                    self.resource_compatibility_problem = str(resource_error)
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

    @callback
    def _registry_failed(self, error: CompatibilityError) -> None:
        self.registry_compatibility_problem = str(error)
        self.registry_adapter = None
        self._update_issues()
        self.notify()

    @property
    def available_controls(self) -> frozenset[str]:
        """Offer controls only for adapters admitted and installed on this Core."""
        controls = {CONTROL_MASTER}
        if self.adapter is not None:
            controls.add(CONTROL_ENTITIES)
        if self.registry_adapter is not None:
            controls.add(CONTROL_REGISTRIES)
        if self.resource_adapter is not None:
            controls.add(CONTROL_RESOURCES)
        if self.graph_adapter is not None:
            controls.update((CONTROL_GRAPHS, CONTROL_MOTION))
        return frozenset(controls)

    async def async_set_control(self, key: str, enabled: bool) -> None:
        """Persist a single source of truth and reconcile existing listeners."""
        if key not in self.available_controls or not isinstance(enabled, bool):
            raise ValueError("Invalid Loona control")
        await self.async_set_controls({key: enabled})

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
        for key, active in (
            ("compatibility", self.compatibility_problem is not None),
            ("scope", bool(self.problems)),
            ("resources", bool(
                self.controls[CONTROL_MASTER] and self.controls[CONTROL_RESOURCES]
                and (self.resource_preview.get("unresolved_custom_types")
                     or self.resource_preview.get("dynamic_configuration")
                     or self.resource_preview.get("stale_exceptions")
                     or self.resource_preview.get("counts", {}).get("unclassified"))
            )),
            (
                "exclusion",
                any("exclusion removes" in warning for warning in self.warnings),
            ),
        ):
            issue_id = f"{self.entry.entry_id}_{key}"
            if active:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=key,
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    def metrics(self) -> dict[str, Any]:
        """Entity count estimates use current state IDs, not transport bytes."""
        current = set(self.hass.states.async_entity_ids())
        scoped = len(current & self.entity_ids)
        return {
            **self.live_statistics.metrics(),
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
        self._listeners.clear()
        self.statistics_card.unload()
        for key in ("compatibility", "scope", "exclusion", "resources"):
            ir.async_delete_issue(self.hass, DOMAIN, f"{self.entry.entry_id}_{key}")


if TYPE_CHECKING:
    type LoonaConfigEntry = ConfigEntry[LoonaRuntime]
else:
    # Core 2024.5 ConfigEntry is not generic at runtime.
    LoonaConfigEntry = ConfigEntry
