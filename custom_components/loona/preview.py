"""Administrator statistics and server-observed page-load summaries."""

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import VERSION, DOMAIN, METRIC_SECONDS, PAGE_LOAD_COMMAND, PAGE_LOAD_LIMIT
from .dashboard import dashboard_objects
from homeassistant.util import dt as dt_util
from .runtime import LoonaRuntime


def statistics_report(runtime: LoonaRuntime) -> dict[str, Any]:
    """Keep statistics, notices and operating status compact."""
    return {
        "version": VERSION,
        "notices": runtime.notice_report(),
        "metrics": runtime.metrics(),
        "controls": runtime.controls,
        "available_controls": sorted(runtime.available_controls),
        "complete": not runtime.scope_problem,
        "compatibility_problem": runtime.compatibility_problem,
        "problems": list(runtime.problems),
        "warnings": list(runtime.warnings),
        "reset_at": runtime.live_statistics.reset_at.isoformat(),
        "interval_seconds": METRIC_SECONDS,
        "sample_seconds": runtime.live_statistics.sample_seconds,
        "page_loads": list(reversed(runtime.live_statistics.page_loads.values())),
        "reset_entity": next((item.entity_id for item in er.async_get(runtime.hass).entities.values()
                              if item.config_entry_id == runtime.entry.entry_id
                              and item.unique_id.endswith(":reset_live_statistics")), None),
    }


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "loona/statistics",
})
def websocket_statistics(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Never expose configuration or dependency IDs to non-admin accounts."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    connection.send_result(msg["id"], statistics_report(runtime))


@callback
@websocket_api.websocket_command({
    vol.Required("type"): PAGE_LOAD_COMMAND,
    vol.Required("dashboard"): vol.All(str, vol.Length(max=128)),
})
def websocket_page_load(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Latch server-observed bootstrap counts; accept no client-supplied totals."""
    runtime = hass.data.get(DOMAIN)
    path = msg["dashboard"]
    board = dashboard_objects(hass).get(path)
    if runtime is None or board is None:
        connection.send_result(msg["id"], None)
        return
    if (board.config or {}).get("require_admin") and not connection.user.is_admin:
        connection.send_result(msg["id"], None)
        return
    initial = runtime.adapter.initial_counts(connection) if runtime.adapter else None
    if initial is not None:
        rows = runtime.live_statistics.page_loads
        rows.pop(path, None)
        rows[path] = {"dashboard": path, "title": (board.config or {}).get("title", "Overview"),
                      "at": dt_util.utcnow().isoformat(), "entities": initial,
                      "resources": runtime.adapter.resource_counts(connection) if runtime.adapter else None,
                      "shared_scope": True}
        while len(rows) > PAGE_LOAD_LIMIT:
            rows.pop(next(iter(rows)))
    connection.send_result(msg["id"], None)
