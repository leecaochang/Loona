"""Small administrator-only dependency pages for native forms and the card."""

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DEPENDENCY_PAGE_SIZE, DOMAIN, METRIC_SECONDS, PAGE_LOAD_COMMAND, PAGE_LOAD_LIMIT
from .dashboard import dashboard_objects
from homeassistant.util import dt as dt_util
from .runtime import LoonaRuntime


def dependency_rows(runtime: LoonaRuntime) -> list[dict[str, Any]]:
    """Explain retained and excluded dependencies without changing the scope."""
    known = set(runtime.hass.states.async_entity_ids()) | set(er.async_get(runtime.hass).entities)
    rows = []
    for entity_id, reasons in (runtime.reasons | runtime.excluded_reasons).items():
        excluded = entity_id in runtime.excluded_reasons
        rows.append({
            "entity_id": entity_id,
            "status": "excluded" if excluded else "retained",
            "unresolved": entity_id not in known,
            "reasons": list(reasons),
            "dashboards": [key for key, result in runtime.dashboards.items() if entity_id in result.entity_ids],
        })
    return sorted(rows, key=lambda row: row["entity_id"])


def statistics_report(runtime: LoonaRuntime, search: str = "", status: str = "all", offset: int = 0, *, include_dependencies: bool = False) -> dict[str, Any]:
    """Paginate details and keep statistics and operating status compact."""
    rows = dependency_rows(runtime) if include_dependencies else []
    query = search.casefold()
    matching = [row for row in rows if (not query or query in row["entity_id"].casefold())
                and (status == "all" or (status == "unresolved" and row["unresolved"])
                     or status == row["status"])]
    return {
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
        "total": len(matching),
        "offset": offset,
        "page_size": DEPENDENCY_PAGE_SIZE,
        "dependencies": matching[offset:offset + DEPENDENCY_PAGE_SIZE],
        "page_loads": list(reversed(runtime.live_statistics.page_loads.values())),
        "reset_entity": next((item.entity_id for item in er.async_get(runtime.hass).entities.values()
                              if item.config_entry_id == runtime.entry.entry_id
                              and item.unique_id.endswith(":reset_live_statistics")), None),
    }


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "loona/statistics",
    vol.Optional("include_dependencies", default=False): bool,
    vol.Optional("search", default=""): vol.All(str, vol.Length(max=160)),
    vol.Optional("status", default="all"): vol.In(("all", "retained", "excluded", "unresolved")),
    vol.Optional("offset", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
})
def websocket_statistics(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Never expose configuration or dependency IDs to non-admin accounts."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    connection.send_result(msg["id"], statistics_report(runtime, msg["search"], msg["status"], msg["offset"], include_dependencies=msg["include_dependencies"]))


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
