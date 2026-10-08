"""Administrator statistics and server-observed page-load summaries."""

from typing import Any
import math


from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .schema import vol
from .const import (VERSION, DOMAIN, METRIC_SECONDS, PAGE_LOAD_COMMAND, PAGE_LOAD_LIMIT,
                    BROWSER_REPORT_COMMAND, BROWSER_REPORT_LIMIT, BROWSER_SCRIPT_LIMIT,
                    BROWSER_SUBSCRIPTION_LIMIT)
from .dashboard import dashboard_objects, dashboard_titles
from homeassistant.util import dt as dt_util
from .runtime import LoonaRuntime
from .presentation import entity_label, notice_labels, resource_labels


def statistics_report(runtime: LoonaRuntime, include_rate_history: bool = False) -> dict[str, Any]:
    """Keep statistics, notices and operating status compact."""
    notices = runtime.notice_report()
    noisy = runtime.live_statistics.noisy_report()
    for row in noisy["entities"]:
        row["label"] = entity_label(runtime.hass, row["entity_id"])
    reports = list(reversed(runtime.live_statistics.browser_reports.values()))
    return {
        "version": VERSION,
        "notices": notices,
        "notice_labels": notice_labels(runtime.hass, notices),
        "resource_labels": resource_labels(runtime.hass, [script["source"] for report in reports for script in report["scripts"]]),
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
        "rate_history": list(runtime.live_statistics.rate_history) if include_rate_history else [],
        "page_loads": list(reversed(runtime.live_statistics.page_loads.values())),
        "noisy_entities": noisy,
        "browser_reports": reports,
        "reset_entity": next((item.entity_id for item in er.async_get(runtime.hass).entities.values()
                              if item.config_entry_id == runtime.entry.entry_id
                              and item.unique_id.endswith(":reset_live_statistics")), None),
    }


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "loona/statistics",
    vol.Optional("include_rate_history", default=False): bool,
})
def websocket_statistics(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Never expose configuration or dependency IDs to non-admin accounts."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    connection.send_result(msg["id"], statistics_report(runtime, msg["include_rate_history"]))


def _finite_duration(value: Any) -> float:
    """Reject non-finite and unbounded browser-supplied measurements."""
    try:
        result = float(value)
    except (TypeError, ValueError) as err:
        raise vol.Invalid("Invalid duration") from err
    if not math.isfinite(result) or not 0 <= result <= 3600000:
        raise vol.Invalid("Duration is outside the allowed range")
    return result


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): BROWSER_REPORT_COMMAND,
    vol.Required("dashboard"): vol.All(str, vol.Length(max=128)),
    vol.Required("duration_ms"): _finite_duration,
    vol.Required("loaf_supported"): bool,
    vol.Required("frames"): vol.All(int, vol.Range(min=0, max=10000)),
    vol.Required("blocking_ms"): _finite_duration,
    vol.Required("scripts"): vol.All([{
        vol.Required("source"): vol.All(str, vol.Length(max=512), vol.Match(r"^/(?:frontend_latest|hacsfiles|local|uix|loona)/[^?#\s]+$")),
        vol.Required("phase"): vol.In(("buffered", "window")),
        vol.Required("duration_ms"): _finite_duration,
        vol.Required("forced_layout_ms"): _finite_duration,
    }], vol.Length(max=BROWSER_SCRIPT_LIMIT)),
    vol.Required("subscriptions"): vol.All([{
        vol.Required("type"): vol.All(str, vol.Length(max=80), vol.Match(r"^[a-zA-Z0-9_/*:.-]+$")),
        vol.Required("count"): vol.All(int, vol.Range(min=0, max=10000)),
    }], vol.Length(max=BROWSER_SUBSCRIPTION_LIMIT)),
})
def websocket_browser_report(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Store bounded administrator observations separately from native counters."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    if msg["dashboard"] not in dashboard_objects(hass):
        connection.send_error(msg["id"], "invalid_dashboard", "Dashboard is unavailable")
        return
    rows = runtime.live_statistics.browser_reports
    rows.pop(msg["dashboard"], None)
    rows[msg["dashboard"]] = {key: value for key, value in msg.items() if key not in {"id", "type"}}
    rows[msg["dashboard"]]["at"] = dt_util.utcnow().isoformat()
    while len(rows) > BROWSER_REPORT_LIMIT:
        rows.pop(next(iter(rows)))
    connection.send_result(msg["id"], None)


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
        rows[path] = {"dashboard": path, "title": dashboard_titles(hass).get(path, path),
                      "at": dt_util.utcnow().isoformat(), "entities": initial,
                      "resources": runtime.adapter.resource_counts(connection) if runtime.adapter else None}
        while len(rows) > PAGE_LOAD_LIMIT:
            rows.pop(next(iter(rows)))
    connection.send_result(msg["id"], None)
