"""Limit shared frontend filters to explicitly reported dashboard connections."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


from homeassistant.components import frontend, websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .compatibility import CompatibilityError, probe_error, HandlerEntry
from .schema import vol
from .const import PANEL_ASSET, PANEL_COMMAND, PANEL_SUBSCRIBE, PANEL_POLL_MS, VERSION, BROWSER_MEASURE_MS


@callback
def _released_context() -> None:
    """Let a surviving client unsubscribe without retaining the runtime."""


async def async_register_frontend(hass: HomeAssistant) -> Callable[[], None]:
    """Keep frontend API changes isolated from working backend adapters."""
    try:
        return await _async_register_frontend(hass)
    except CompatibilityError:
        raise
    except Exception as err:
        raise probe_error("Native frontend registration probe failed", err) from err


async def _async_register_frontend(hass: HomeAssistant) -> Callable[[], None]:
    """Load context reporting using the available native frontend APIs."""
    key = "loona_panel_asset_registered"
    if not hass.data.get(key):
        path = str(Path(__file__).parent / "frontend" / "panel-context.js")
        if callable(getattr(hass.http, "async_register_static_paths", None)):
            from homeassistant.components.http import StaticPathConfig
            await hass.http.async_register_static_paths([
                StaticPathConfig(PANEL_ASSET, path, cache_headers=True),
                StaticPathConfig("/loona/performance.js", str(Path(__file__).parent / "frontend" / "performance.js"), cache_headers=True),
                StaticPathConfig("/loona/resource-loading.js", str(Path(__file__).parent / "frontend" / "resource-loading.js"), cache_headers=True),
            ])
        elif callable(register := getattr(hass.http, "register_static_path", None)):
            register(PANEL_ASSET, path, cache_headers=True)
            register("/loona/performance.js", str(Path(__file__).parent / "frontend" / "performance.js"), cache_headers=True)
            register("/loona/resource-loading.js", str(Path(__file__).parent / "frontend" / "resource-loading.js"), cache_headers=True)
        else:
            raise CompatibilityError("Frontend panel context registration is unavailable")
        hass.data[key] = True
    url = f"{PANEL_ASSET}?v={VERSION}&poll={PANEL_POLL_MS}&measure={BROWSER_MEASURE_MS}"
    frontend.add_extra_js_url(hass, url)

    def remove() -> None:
        if callable(unregister := getattr(frontend, "remove_extra_js_url", None)):
            unregister(hass, url)
        else:
            hass.data[frontend.DATA_EXTRA_MODULE_URL].remove(url)

    return remove


@dataclass(slots=True)
class _Panel:
    """The context lifetime belongs to a native websocket subscription."""

    dashboard: str | None
    unsubscribe: Callable[[], None]
    msg_id: int
    live_dashboard: bool = False
    expanded: bool = False
    view: str | None = None
    editing: bool = False
    loading: dict[str, Any] | None = None
    idle: bool = False
    idle_settings: dict[str, Any] | None = None
    timer: Callable[[], None] | None = None
    refresh_seconds: int = 0
    # The page's first card-file counts, and a page-load record written before they arrived.
    resource_counts: dict[str, int] | None = None
    pending_page_load: tuple[str, dict[str, Any]] | None = None


class PanelContext:
    """Unknown clients and non-dashboard panels always use native HA data."""

    def __init__(self, hass: HomeAssistant, changed: Callable[[websocket_api.ActiveConnection], None]) -> None:
        self.hass = hass
        self.changed = changed
        self.dashboards: frozenset[str] = frozenset()
        self._connections: dict[websocket_api.ActiveConnection, _Panel] = {}
        self._owned: dict[str, HandlerEntry] = {}
        self.resource_plan: Callable[[websocket_api.ActiveConnection, str | None], dict[str, Any]] | None = None
        self.idle_policy: Callable[[websocket_api.ActiveConnection], dict[str, Any]] | None = None
        self.idle_refresh: Callable[[websocket_api.ActiveConnection], None] | None = None

    @callback
    def publish(self) -> None:
        """Publish changed loading plans through the existing context subscription."""
        for connection, panel in self._connections.items():
            event = {}
            if self.resource_plan is not None:
                plan = self.resource_plan(connection, panel.dashboard)
                if plan != panel.loading:
                    panel.loading = plan
                    event["resources"] = plan
            if self.idle_policy is not None:
                policy = self.idle_policy(connection)
                if policy != panel.idle_settings:
                    panel.idle_settings = policy
                    event["idle"] = policy
                seconds = policy["refresh_seconds"] if policy["enabled"] and panel.idle else 0
                if seconds != panel.refresh_seconds:
                    if panel.timer:
                        panel.timer()
                        panel.timer = None
                    panel.refresh_seconds = seconds
                    if seconds:
                        self._schedule_idle(connection, panel)
            if event:
                connection.send_event(panel.msg_id, event)

    def _schedule_idle(self, connection: websocket_api.ActiveConnection, panel: _Panel) -> None:
        """Allocate a timer only while this socket is periodically idle."""
        @callback
        def refresh(_now: Any) -> None:
            panel.timer = None
            if self._connections.get(connection) is not panel or not panel.refresh_seconds:
                return
            if self.idle_refresh is not None:
                self.idle_refresh(connection)
            self.publish()
            if self._connections.get(connection) is panel and panel.refresh_seconds and panel.timer is None:
                self._schedule_idle(connection, panel)
        panel.timer = async_call_later(self.hass, panel.refresh_seconds, refresh)

    def active(self, connection: websocket_api.ActiveConnection) -> bool:
        """Panel reports narrow performance filtering without granting access.

        A dashboard open in the native editor is unfiltered until editing ends.
        """
        panel = self._connections.get(connection)
        return bool(panel is not None and panel.dashboard in self.dashboards and not panel.editing)

    def dashboard_for(self, connection: websocket_api.ActiveConnection) -> str | None:
        """The panel path this connection last reported, if any."""
        panel = self._connections.get(connection)
        return panel.dashboard if panel else None

    def delivery_dashboard(self, connection: websocket_api.ActiveConnection) -> str | None:
        """Old reporters and expanded native interfaces keep union delivery."""
        panel = self._connections.get(connection)
        return panel.dashboard if panel and panel.live_dashboard and not panel.expanded and self.active(connection) else None

    def delivery_view(self, connection: websocket_api.ActiveConnection) -> str | None:
        """Absent view context keeps dashboard delivery for older reporters."""
        panel = self._connections.get(connection)
        return panel.view if panel and self.delivery_dashboard(connection) is not None else None

    def expanded(self, connection: websocket_api.ActiveConnection) -> bool:
        """Native dialogs and editors release pending card files immediately."""
        panel = self._connections.get(connection)
        return bool(panel and panel.expanded)

    def idle(self, connection: websocket_api.ActiveConnection) -> bool:
        """Idle reports can only narrow a selected ordinary dashboard feed."""
        panel = self._connections.get(connection)
        return bool(panel and panel.idle and self.delivery_dashboard(connection) is not None)

    def install(self) -> None:
        """Register public context commands without changing any native schema."""
        table = self.hass.data[websocket_api.DOMAIN]
        if any(command in table for command in (PANEL_COMMAND, PANEL_SUBSCRIBE)):
            raise CompatibilityError("Another handler owns Loona panel context")

        @callback
        @websocket_api.websocket_command({
            vol.Required("type"): PANEL_SUBSCRIBE,
            vol.Required("dashboard"): vol.Any(None, str),
            vol.Optional("live_dashboard", default=False): bool,
            vol.Optional("expanded", default=False): bool,
            vol.Optional("editing", default=False): bool,
            vol.Optional("view", default=None): vol.Any(None, vol.All(str, vol.Length(max=255))),
            vol.Optional("idle", default=False): bool,
        })
        def subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
            before = self.active(connection)

            @callback
            def unsubscribe() -> None:
                panel = self._connections.get(connection)
                if panel is not None and panel.unsubscribe is unsubscribe:
                    active = self.active(connection)
                    if panel.timer:
                        panel.timer()
                    self._connections.pop(connection)
                    # Native close iterates its dictionary without popping entries.
                    # Explicit unsubscribe pops this ID before invoking us.
                    if active and msg["id"] not in connection.subscriptions:
                        self.changed(connection)

            previous = self._connections.get(connection)
            if previous is not None:
                connection.send_error(msg["id"], "already_subscribed", "Panel context is already subscribed")
                return
            self._connections[connection] = _Panel(msg["dashboard"], unsubscribe, msg["id"], msg["live_dashboard"], msg["expanded"], msg["view"], msg["editing"])
            self._connections[connection].idle = msg["idle"]
            connection.subscriptions[msg["id"]] = unsubscribe
            connection.send_result(msg["id"])
            if before != self.active(connection):
                self.changed(connection)
            self.publish()

        @callback
        @websocket_api.websocket_command({
            vol.Required("type"): PANEL_COMMAND,
            vol.Required("dashboard"): vol.Any(None, str),
            vol.Optional("live_dashboard", default=False): bool,
            vol.Optional("expanded", default=False): bool,
            vol.Optional("editing", default=False): bool,
            vol.Optional("view", default=None): vol.Any(None, vol.All(str, vol.Length(max=255))),
            vol.Optional("idle", default=False): bool,
        })
        def update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
            panel = self._connections.get(connection)
            if panel is None:
                connection.send_error(msg["id"], "not_subscribed", "Subscribe to panel context first")
                return
            before = (panel.dashboard, panel.live_dashboard, panel.expanded, panel.view, panel.editing, panel.idle)
            panel.dashboard = msg["dashboard"]
            panel.live_dashboard = msg["live_dashboard"]
            panel.expanded = msg["expanded"]
            panel.view = msg["view"]
            panel.editing = msg["editing"]
            panel.idle = msg["idle"]
            if before != (panel.dashboard, panel.live_dashboard, panel.expanded, panel.view, panel.editing, panel.idle):
                self.changed(connection)
            self.publish()
            connection.send_result(msg["id"])

        for handler in (subscribe, update):
            websocket_api.async_register_command(self.hass, handler)
        self._owned = {name: table[name] for name in (PANEL_COMMAND, PANEL_SUBSCRIBE)}

    def request_resubscribe(self, connection: websocket_api.ActiveConnection) -> None:
        """Ask the stock client to replay the original, lossless requests."""
        if panel := self._connections.get(connection):
            connection.send_event(panel.msg_id, {"resubscribe": True})

    def note_resources(self, connection: websocket_api.ActiveConnection, counts: dict[str, int]) -> tuple[str, dict[str, Any]] | None:
        """Keep the page's first card-file counts and hand back a page load waiting for them."""
        panel = self._connections.get(connection)
        if panel is None:
            return None
        if panel.resource_counts is None:
            panel.resource_counts = counts
        pending, panel.pending_page_load = panel.pending_page_load, None
        return pending

    def resource_counts(self, connection: websocket_api.ActiveConnection) -> dict[str, int] | None:
        panel = self._connections.get(connection)
        return panel.resource_counts if panel else None

    def await_resources(self, connection: websocket_api.ActiveConnection, path: str, row: dict[str, Any]) -> None:
        """The page-load report usually arrives before the dashboard requests its card files."""
        if panel := self._connections.get(connection):
            panel.pending_page_load = (path, row)

    def set_dashboards(self, dashboards: frozenset[str]) -> None:
        """Changing selected dashboards also reconciles already open panels."""
        before = {connection: self.active(connection) for connection in self._connections}
        self.dashboards = dashboards
        for connection, active in before.items():
            if active != self.active(connection):
                self.changed(connection)

    def uninstall(self) -> None:
        """Clear socket references and release only commands still owned."""
        for connection, panel in self._connections.items():
            if panel.timer:
                panel.timer()
            if connection.subscriptions.get(panel.msg_id) is panel.unsubscribe:
                connection.subscriptions[panel.msg_id] = _released_context
        self._connections.clear()
        table = self.hass.data[websocket_api.DOMAIN]
        for name, entry in self._owned.items():
            if table.get(name) is entry:
                table.pop(name)
        self._owned.clear()

    @callback
    def disable_clients(self) -> None:
        """Stop frontend reports before restoring and releasing backend hooks."""
        for connection, panel in self._connections.items():
            if connection.subscriptions.get(panel.msg_id) is panel.unsubscribe:
                connection.send_event(panel.msg_id, {"enabled": False})
