"""Administrator settings for prefilled cards using native option validation."""

import hashlib
import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .compatibility import CompatibilityError
from .config_flow import entity_rule_choices, human_accounts, validate_dashboards, validate_targets, validate_idle_settings
from .const import (
    CONF_ALWAYS_FORWARD, CONF_DASHBOARDS, CONF_EXTRA_ENTITIES,
    CONF_TARGET_MODE, CONF_USER_IDS, DOMAIN, TARGET_SELECTED, CONTROL_RESOURCES, CONTROL_DEFAULTS,
    VERSION,
    SETTINGS_COMMAND, SETTINGS_SAVE_COMMAND, SETTINGS_GROUPS, SETTINGS_CHOICE_PAGE, SETTINGS_EMPTY_DEFAULTS,
    SETTINGS_CHOICES_COMMAND, CONF_DASHBOARD_CARDS, DASHBOARD_CARDS,
    SETTINGS_RESTORE_COMMAND,
    CONF_IDLE_AFTER, CONF_IDLE_REFRESH, IDLE_AFTER_MINUTES, IDLE_REFRESH_SECONDS,
)
from .dashboard import dashboard_titles
from .runtime import LoonaRuntime
from .presentation import entity_label, resource_labels

_LOGGER = logging.getLogger(__name__)
_PAGED_CHOICES = frozenset({"extra_entities", "include_globs", "exclude_globs"})


def entity_choices(runtime: LoonaRuntime, key: str, query: str = "", offset: int = 0) -> dict[str, Any]:
    """Search authoritative entity/rule choices with bounded response size."""
    rules = entity_rule_choices(runtime.hass, runtime.settings)
    saved = set(runtime.settings.get(key, ()))
    available = known_entities(runtime)
    def row(value: str) -> dict[str, Any]:
        return {"value": value, "label": entity_label(runtime.hass, value),
                "unavailable": value not in available if key == CONF_EXTRA_ENTITIES else False}
    words = query.casefold().split()
    rows = [row(value) for value in rules[key] if value not in saved]
    matching = [item for item in rows if all(word in (item["value"] + " " + item["label"]).casefold()
                                           for word in words)]
    matching.sort(key=lambda item: ("*" in item["value"], item["label"].casefold(), item["value"]))
    return {"choices": matching[offset:offset + SETTINGS_CHOICE_PAGE],
            "selected": [row(value) for value in sorted(saved)],
            "more": offset + SETTINGS_CHOICE_PAGE < len(matching)}


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
    labels = resource_labels(runtime.hass, [row["url"] for row in resources["resources"]] + resources["stale_exceptions"])
    result: dict[str, Any] = {
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
            "cards": {CONF_DASHBOARD_CARDS: list(settings.get(CONF_DASHBOARD_CARDS, []))},
            "idle": {CONF_IDLE_AFTER: settings.get(CONF_IDLE_AFTER, IDLE_AFTER_MINUTES), CONF_IDLE_REFRESH: settings.get(CONF_IDLE_REFRESH, IDLE_REFRESH_SECONDS)},
        },
        "choices": {
            CONF_DASHBOARDS: [{"value": key, "label": titles.get(key, key), "unavailable": key not in titles}
                                for key in sorted(titles.keys() | set(settings.get(CONF_DASHBOARDS, [])))],
            CONF_USER_IDS: [{"value": key, "label": accounts.get(key, key), "unavailable": key not in accounts}
                           for key in sorted(accounts.keys() | set(settings.get(CONF_USER_IDS, [])))],
            **{key: [{"value": value, "label": value} for value in values]
               for key, values in rules.items() if key not in _PAGED_CHOICES},
            CONF_ALWAYS_FORWARD: [{"value": row["url"], "label": labels.get(row["url"], row["url"]), "status": row["status"]}
                                  for row in resources["resources"] if row["status"] == "unused" or row["url"] in settings.get(CONF_ALWAYS_FORWARD, []) and row["status"] != "required"]
                + [{"value": url, "label": labels.get(url, url), "unavailable": True} for url in resources["stale_exceptions"]],
            CONF_DASHBOARD_CARDS: [{"value": key, "label": "Loona " + key} for key in DASHBOARD_CARDS],
        },
        "required_resources": [row["url"] for row in resources["resources"] if row["status"] != "unused"],
        "resource_labels": labels,
        "resources_editable": resource_available and CONTROL_RESOURCES in runtime.available_controls,
        "entry_id": runtime.entry.entry_id,
        "action_entities": {key: next((item.entity_id for item in registry.entities.values()
            if item.config_entry_id == runtime.entry.entry_id
            and item.domain == "button" and item.unique_id.endswith(":" + key)), None)
            for key in ("rescan", "reset_live_statistics")},
    }
    result["paged_choices"] = {}
    for key in _PAGED_CHOICES:
        page = entity_choices(runtime, key)
        result["choices"][key] = page["selected"] + page["choices"]
        result["paged_choices"][key] = page["more"]
    for key in (CONF_DASHBOARDS, CONF_USER_IDS):
        result["choices"][key].sort(key=lambda item: (item["label"].casefold(), item["value"]))
    return result


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): SETTINGS_CHOICES_COMMAND,
    vol.Required("key"): vol.In(_PAGED_CHOICES),
    vol.Optional("query", default=""): vol.All(str, vol.Length(max=160)),
    vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0, max=1000000)),
})
@websocket_api.async_response
async def websocket_settings_choices(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Return a page of choices only to administrators."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    connection.send_result(msg["id"], entity_choices(runtime, msg["key"], msg["query"], msg["offset"]))


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
        _LOGGER.exception("Loona settings read failed")
        connection.send_error(msg["id"], "unavailable", "Settings are unavailable")
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): SETTINGS_SAVE_COMMAND,
    vol.Required("group"): vol.In(SETTINGS_GROUPS),
    vol.Required("revision"): vol.All(str, vol.Length(min=64, max=64)),
    vol.Required("values"): dict,
    vol.Optional("confirmed", default=False): bool,
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
        if (group == "cards" and runtime.settings.get(CONF_DASHBOARD_CARDS)
            and values.get(CONF_DASHBOARD_CARDS) == [] and not msg["confirmed"]):
            connection.send_error(msg["id"], "confirmation_required", "Confirm removal of the Loona dashboard")
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
            elif group == "idle":
                values = validate_idle_settings(values)
            else:
                choices = entity_rule_choices(hass, runtime.settings)
                if group == "cards":
                    choices = {CONF_DASHBOARD_CARDS: list(DASHBOARD_CARDS)}
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
            if group == "cards":
                await runtime.async_update_statistics_card()
        connection.send_result(msg["id"], await settings_report(runtime))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), "Choose valid values from the current lists")
    except Exception:
        _LOGGER.exception("Loona settings save failed")
        connection.send_error(msg["id"], "save_failed", "Settings could not be saved; refresh and check current values")


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): SETTINGS_RESTORE_COMMAND,
    vol.Required("revision"): vol.All(str, vol.Length(min=64, max=64)),
    vol.Required("confirmed"): vol.All(bool, vol.In([True])),
})
@websocket_api.async_response
async def websocket_restore_defaults(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Require explicit confirmation and a current administrator revision."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    try:
        if revision(runtime) != msg["revision"]:
            raise ValueError("conflict")
        await runtime.async_restore_defaults(expected=dict(runtime.controls), expected_settings=dict(runtime.settings))
        connection.send_result(msg["id"], await settings_report(runtime))
    except ValueError:
        connection.send_error(msg["id"], "conflict", "Settings changed; refresh before restoring defaults")
    except Exception:
        _LOGGER.exception("Loona defaults restore failed")
        connection.send_error(msg["id"], "save_failed", "Defaults could not be restored; refresh and check current values")
