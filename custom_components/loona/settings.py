"""Administrator settings for prefilled cards using native option validation."""

import hashlib
import json
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .compatibility import CompatibilityError
from .config_flow import entity_rule_choices, human_accounts, validate_dashboards, validate_targets
from .const import (
    CONF_ALWAYS_FORWARD, CONF_DASHBOARDS, CONF_EXTRA_ENTITIES,
    CONF_TARGET_MODE, CONF_USER_IDS, DOMAIN, TARGET_SELECTED, CONTROL_RESOURCES, CONTROL_DEFAULTS,
    VERSION,
    SETTINGS_COMMAND, SETTINGS_SAVE_COMMAND, SETTINGS_GROUPS, SETTINGS_CHOICE_PAGE, SETTINGS_EMPTY_DEFAULTS,
)
from .dashboard import dashboard_titles
from .runtime import LoonaRuntime


def revision(runtime: LoonaRuntime) -> str:
    """Reject a draft after another card, native form or switch changed values."""
    return _revision(runtime.settings, runtime.controls)


def _revision(settings: dict[str, Any], controls: dict[str, bool]) -> str:
    return hashlib.sha256(json.dumps([settings, controls], sort_keys=True).encode()).hexdigest()


def known_entities(runtime: LoonaRuntime) -> set[str]:
    """Native live states plus registered entities, including unavailable ones."""
    return set(runtime.hass.states.async_entity_ids()) | set(er.async_get(runtime.hass).entities)


async def settings_report(runtime: LoonaRuntime) -> dict[str, Any]:
    """Share authoritative choices, saved values and supported controls."""
    settings, controls = dict(runtime.settings), dict(runtime.controls)
    titles = dashboard_titles(runtime.hass)
    accounts = await human_accounts(runtime.hass)
    rules = entity_rule_choices(runtime.hass, settings)
    resource_available = True
    try:
        resources = await runtime.async_resource_preview()
    except CompatibilityError:
        resource_available = False
        resources = {"resources": [], "stale_exceptions": list(settings.get(CONF_ALWAYS_FORWARD, []))}
    registry = er.async_get(runtime.hass)
    available_entities = known_entities(runtime)
    entities = available_entities | set(settings.get(CONF_EXTRA_ENTITIES, []))
    return {
        "version": VERSION,
        "notices": runtime.notice_report(),
        "revision": _revision(settings, controls),
        "choice_page": SETTINGS_CHOICE_PAGE,
        "values": {
            "controls": {key: controls[key] for key in CONTROL_DEFAULTS if key in runtime.available_controls},
            "dashboards": {CONF_DASHBOARDS: list(settings.get(CONF_DASHBOARDS, []))},
            "targets": {CONF_TARGET_MODE: settings.get(CONF_TARGET_MODE, TARGET_SELECTED), CONF_USER_IDS: list(settings.get(CONF_USER_IDS, []))},
            "rules": {key: list(settings.get(key, [])) for key in rules},
            "resources": {CONF_ALWAYS_FORWARD: list(settings.get(CONF_ALWAYS_FORWARD, []))},
        },
        "choices": {
            CONF_DASHBOARDS: [{"value": key, "label": titles.get(key, key), "unavailable": key not in titles}
                                for key in sorted(titles.keys() | set(settings.get(CONF_DASHBOARDS, [])))],
            CONF_USER_IDS: [{"value": key, "label": accounts.get(key, key), "unavailable": key not in accounts}
                           for key in sorted(accounts.keys() | set(settings.get(CONF_USER_IDS, [])))],
            CONF_EXTRA_ENTITIES: [{"value": key, "label": (registry.entities[key].name or registry.entities[key].original_name or key)
                                   if key in registry.entities else key, "unavailable": key not in available_entities}
                                 for key in sorted(entities)],
            **{key: [{"value": value, "label": value} for value in values]
               for key, values in rules.items() if key != CONF_EXTRA_ENTITIES},
            CONF_ALWAYS_FORWARD: [{"value": row["url"], "label": row["url"], "status": row["status"]}
                                  for row in resources["resources"] if row["status"] != "required"]
                + [{"value": url, "label": url, "unavailable": True} for url in resources["stale_exceptions"]],
        },
        "required_resources": [row["url"] for row in resources["resources"] if row["status"] == "required"],
        "resources_editable": resource_available and CONTROL_RESOURCES in runtime.available_controls,
        "entry_id": runtime.entry.entry_id,
        "action_entities": {key: next((item.entity_id for item in registry.entities.values()
            if item.config_entry_id == runtime.entry.entry_id
            and item.domain == "button" and item.unique_id.endswith(":" + key)), None)
            for key in ("rescan", "reset_live_statistics")},
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): SETTINGS_COMMAND})
@websocket_api.async_response
async def websocket_settings(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """No account names, entity IDs or configuration reach non-admin users."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    try:
        result = await settings_report(runtime)
    except Exception:
        connection.send_error(msg["id"], "unavailable", "Settings are unavailable")
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): SETTINGS_SAVE_COMMAND,
    vol.Required("group"): vol.In(SETTINGS_GROUPS),
    vol.Required("revision"): vol.All(str, vol.Length(min=64, max=64)),
    vol.Required("values"): dict,
})
@websocket_api.async_response
async def websocket_save_settings(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Validate all values before publishing one section through native storage."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    try:
        group, values = msg["group"], msg["values"]
        if revision(runtime) != msg["revision"]:
            connection.send_error(msg["id"], "conflict", "Settings changed; refresh before saving")
            return
        if group == "controls":
            if set(values) != runtime.available_controls or any(not isinstance(v, bool) for v in values.values()):
                raise ValueError("invalid_selection")
        else:
            if set(values) != SETTINGS_GROUPS[group]:
                raise ValueError("invalid_selection")
            if group == "dashboards":
                if error := validate_dashboards(hass, values):
                    raise ValueError(error)
            elif group == "targets":
                if error := await validate_targets(hass, values):
                    raise ValueError(error)
            else:
                choices = entity_rule_choices(hass, runtime.settings)
                if group == "resources":
                    if CONTROL_RESOURCES not in runtime.available_controls:
                        raise ValueError("unsupported")
                    report = await runtime.async_resource_preview()
                    choices = {CONF_ALWAYS_FORWARD: [row["url"] for row in report["resources"]] + report["stale_exceptions"]}
                for key, items in values.items():
                    if (not isinstance(items, list) or any(not isinstance(v, str) for v in items)
                        or len(items) != len(set(items)) or not set(items) <= set(choices[key])):
                        raise ValueError("invalid_selection")
                if group == "resources":
                    required = {row["url"] for row in report["resources"] if row["status"] == "required"}
                    values = {CONF_ALWAYS_FORWARD: sorted((set(values[CONF_ALWAYS_FORWARD]) - required)
                              | (set(runtime.settings.get(CONF_ALWAYS_FORWARD, [])) & required))}
        if revision(runtime) != msg["revision"]:
            connection.send_error(msg["id"], "conflict", "Settings changed; refresh before saving")
            return
        if group == "controls":
            await runtime.async_set_controls(values, expected=dict(runtime.controls), expected_settings=dict(runtime.settings))
        else:
            options = {**runtime.entry.options, **values}
            for key, value in values.items():
                if value == runtime.entry.data.get(key) or (key in SETTINGS_EMPTY_DEFAULTS and not value and key not in runtime.entry.data):
                    options.pop(key, None)
            hass.config_entries.async_update_entry(runtime.entry, options=options)
            await runtime.async_scan()
        connection.send_result(msg["id"], await settings_report(runtime))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), "Choose valid values from the current lists")
    except Exception:
        connection.send_error(msg["id"], "save_failed", "Settings could not be saved; refresh and check current values")
