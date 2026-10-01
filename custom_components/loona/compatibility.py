"""Isolate the private websocket adapter verified against HA 2026.9.3 and .4."""

from typing import Literal, cast

import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import commands
from homeassistant.components.websocket_api.const import WebSocketCommandHandler
from homeassistant.core import HomeAssistant

from .const import SUBSCRIBE_ENTITIES, SUPPORTED_CORE_VERSIONS

type HandlerEntry = tuple[WebSocketCommandHandler, vol.Schema | Literal[False]]
type HandlerTable = dict[str, HandlerEntry]


class CompatibilityError(RuntimeError):
    """The native command cannot be safely interposed."""


def inspect_command(hass: HomeAssistant) -> tuple[HandlerTable, HandlerEntry]:
    """Require the tested version, original handler, and original schema."""
    if ha_const.__version__ not in SUPPORTED_CORE_VERSIONS:
        raise CompatibilityError(f"Unsupported Core version: {ha_const.__version__}")
    table = hass.data.get(websocket_api.DOMAIN)
    if not isinstance(table, dict):
        raise CompatibilityError("Websocket commands are not registered yet")
    entry = table.get(SUBSCRIBE_ENTITIES)
    if not isinstance(entry, tuple) or len(entry) != 2:
        raise CompatibilityError("Missing native subscribe_entities command")
    handler, schema = entry
    native = commands.handle_subscribe_entities
    if handler is not native:
        raise CompatibilityError("Another handler owns subscribe_entities")
    if schema is not getattr(native, "_ws_schema", None) or not isinstance(
        schema, vol.Schema
    ):
        raise CompatibilityError("Unrecognized subscribe_entities schema")
    try:
        probe = schema(
            {"id": 1, "type": SUBSCRIBE_ENTITIES, "entity_ids": ["sensor.loona_probe"]}
        )
        if probe["entity_ids"] != ["sensor.loona_probe"]:
            raise CompatibilityError("Native entity filter semantics changed")
    except (vol.Invalid, KeyError, TypeError) as err:
        raise CompatibilityError("Native entity filter validation changed") from err
    return cast(HandlerTable, table), cast(HandlerEntry, entry)
