"""Redacted downloadable scope diagnostics for native HA administrators."""

from homeassistant import const as ha_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .compatibility import CompatibilityError
from .const import CONF_ALWAYS_FORWARD, CONF_DASHBOARDS, CONF_USER_IDS
from .runtime import LoonaConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LoonaConfigEntry
) -> dict:
    """Keep account IDs, entity IDs, patterns, paths, and scan locations private."""
    runtime = entry.runtime_data
    try:
        preview = await runtime.async_resource_preview()
    except CompatibilityError:
        preview = {"available": False}
    data = {
        "core_version": ha_const.__version__,
        "available_controls": sorted(runtime.available_controls),
        "settings": runtime.settings,
        "controls": runtime.controls,
        "metrics": runtime.metrics(),
        "noisy_entities": runtime.live_statistics.noisy_report(),
        "browser_reports": list(runtime.live_statistics.browser_reports.values()),
        "compatibility_problem": runtime.compatibility_problem,
        "panel_compatibility_problem": runtime.panel_compatibility_problem,
        "bootstrap_compatibility_problem": runtime.bootstrap_compatibility_problem,
        "registry_compatibility_problem": runtime.registry_compatibility_problem,
        "graph_compatibility_problem": runtime.graph_compatibility_problem,
        "resource_preview": preview,
        "resource_compatibility_problem": runtime.resource_compatibility_problem,
        "statistics_card_problem": runtime.statistics_card_problem,
        "registry_scope_counts": {
            key: len(getattr(runtime.registry_scope, key))
            for key in ("entities", "devices", "areas", "floors", "labels")
        },
        "scope_complete": not runtime.problems,
        "unfiltered_dashboards": len(runtime.unfiltered_dashboards),
        "problems": runtime.problems,
        "warnings": runtime.warnings,
        "dependencies": [
            {"entity_id": key, "reasons": value}
            for key, value in runtime.reasons.items()
        ],
        "dashboards": [
            {
                "dashboard": key,
                "discovered": len(result.entity_ids),
                "unresolved": len(runtime.unresolved[key]),
                "complete": result.complete,
            }
            for key, result in runtime.dashboards.items()
        ],
    }
    return async_redact_data(
        data,
        {
            CONF_USER_IDS,
            CONF_ALWAYS_FORWARD,
            "url",
            "source",
            "id",
            "reason",
            "stale_exceptions",
            CONF_DASHBOARDS,
            "entity_id",
            "reasons",
            "dashboard",
            "extra_entities",
            "include_domains",
            "include_globs",
            "exclude_globs",
            "problems",
            "warnings",
        },
    )
