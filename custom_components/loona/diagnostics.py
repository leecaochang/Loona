"""Redacted downloadable scope diagnostics for native HA administrators."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_DASHBOARDS, CONF_USER_IDS
from .runtime import LoonaConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LoonaConfigEntry
) -> dict:
    """Keep account IDs, entity IDs, patterns, paths, and scan locations private."""
    runtime = entry.runtime_data
    data = {
        "settings": runtime.settings,
        "controls": runtime.controls,
        "metrics": runtime.metrics(),
        "compatibility_problem": runtime.compatibility_problem,
        "registry_compatibility_problem": runtime.registry_compatibility_problem,
        "registry_scope_counts": {
            key: len(getattr(runtime.registry_scope, key))
            for key in ("entities", "devices", "areas", "floors", "labels")
        },
        "scope_complete": not runtime.problems,
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
