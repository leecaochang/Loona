"""Limit shared frontend filters to explicitly reported dashboard connections."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend, websocket_api
from homeassistant.core import HomeAssistant, callback

from .compatibility import CompatibilityError, probe_error, HandlerEntry
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
    loading: dict[str, Any] | None = None


class PanelContext:
    """Unknown clients and non-dashboard panels always use native HA data."""

    def __init__(self, hass: HomeAssistant, changed: Callable[[websocket_api.ActiveConnection], None]) -> None:
        self.hass = hass
        self.changed = changed
        self.dashboards: frozenset[str] = frozenset()
        self._connections: dict[websocket_api.ActiveConnection, _Panel] = {}
        self._owned: dict[str, HandlerEntry] = {}
        self.resource_plan: Callable[[websocket_api.ActiveConnection, str | None], dict[str, Any]] | None = None

    @callback
    def publish(self) -> None:
        """Publish changed loading plans through the existing context subscription."""
        if self.resource_plan is not None:
            for connection, panel in self._connections.items():
                plan = self.resource_plan(connection, panel.dashboard)
                if plan != panel.loading:
                    panel.loading = plan
                    connection.send_event(panel.msg_id, {"resources": plan})

    def active(self, connection: websocket_api.ActiveConnection) -> bool:
        """Panel reports narrow performance filtering without granting access."""
        panel = self._connections.get(connection)
        return bool(panel is not None and panel.dashboard in self.dashboards)

    def install(self) -> None:
        """Register public context commands without changing any native schema."""
        table = self.hass.data[websocket_api.DOMAIN]
        if any(command in table for command in (PANEL_COMMAND, PANEL_SUBSCRIBE)):
            raise CompatibilityError("Another handler owns Loona panel context")

        @callback
        @websocket_api.websocket_command({
            vol.Required("type"): PANEL_SUBSCRIBE,
            vol.Required("dashboard"): vol.Any(None, str),
        })
        def subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
            before = self.active(connection)

            @callback
            def unsubscribe() -> None:
                panel = self._connections.get(connection)
                if panel is not None and panel.unsubscribe is unsubscribe:
                    active = self.active(connection)
                    self._connections.pop(connection)
                    # Native close iterates its dictionary without popping entries.
                    # Explicit unsubscribe pops this ID before invoking us.
                    if active and msg["id"] not in connection.subscriptions:
                        self.changed(connection)

            previous = self._connections.get(connection)
            if previous is not None:
                connection.send_error(msg["id"], "already_subscribed", "Panel context is already subscribed")
                return
            self._connections[connection] = _Panel(msg["dashboard"], unsubscribe, msg["id"])
            connection.subscriptions[msg["id"]] = unsubscribe
            connection.send_result(msg["id"])
            if before != self.active(connection):
                self.changed(connection)
            self.publish()

        @callback
        @websocket_api.websocket_command({
            vol.Required("type"): PANEL_COMMAND,
            vol.Required("dashboard"): vol.Any(None, str),
        })
        def update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
            panel = self._connections.get(connection)
            if panel is None:
                connection.send_error(msg["id"], "not_subscribed", "Subscribe to panel context first")
                return
            before = self.active(connection)
            panel.dashboard = msg["dashboard"]
            if before != self.active(connection):
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
