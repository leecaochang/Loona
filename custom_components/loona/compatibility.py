"""Probe installed native commands before enabling independent optimizations."""

from collections.abc import Callable
from inspect import isawaitable, iscoroutinefunction, unwrap
import logging
from types import SimpleNamespace
from typing import Any, Literal, cast

from awesomeversion import AwesomeVersion
import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.auth.models import Group, User
from homeassistant.auth.permissions.models import PermissionLookup
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import commands, messages
from homeassistant.components.websocket_api.const import WebSocketCommandHandler
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util.json import json_loads_object

from .const import MIN_CORE_VERSION, SUBSCRIBE_ENTITIES

type HandlerEntry = tuple[WebSocketCommandHandler, vol.Schema | Literal[False]]
type HandlerTable = dict[str, HandlerEntry]


class CompatibilityError(RuntimeError):
    """A native capability cannot be safely interposed."""


def probe_error(message: str, cause: Exception) -> CompatibilityError:
    """Keep safe exception types in diagnostics and tracebacks in debug logs."""
    logging.getLogger(__name__).debug("%s", message, exc_info=(type(cause), cause, cause.__traceback__))
    types = []
    current: BaseException | None = cause
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        types.append(type(current).__name__)
        current = current.__cause__
    return CompatibilityError(f"{message} ({', '.join(types)})")


def check_baseline() -> None:
    """Accept any parseable Core release at or above the minimum baseline."""
    try:
        supported = AwesomeVersion(ha_const.__version__) >= AwesomeVersion(MIN_CORE_VERSION)
    except Exception as err:
        raise probe_error("Core version could not be determined", err) from err
    if not supported:
        raise CompatibilityError(f"Core {MIN_CORE_VERSION} or newer is required")


def inspect_native_command(
    hass: HomeAssistant, name: str, native: Any, arguments: dict[str, Any] | None = None,
    *, require_schema_identity: bool = True,
) -> tuple[HandlerTable, HandlerEntry]:
    """Require native ownership and validate the arguments used by the adapter."""
    check_baseline()
    table = hass.data.get(websocket_api.DOMAIN)
    entry = table.get(name) if isinstance(table, dict) else None
    if (not callable(native) or not isinstance(entry, tuple) or len(entry) != 2
        or entry[0] is not native
        or require_schema_identity and entry[1] is not getattr(native, "_ws_schema", None)
        or entry[1] is False and getattr(native, "_ws_schema", None) is not False
        or not (entry[1] is False or isinstance(entry[1], vol.Schema))):
        raise CompatibilityError(f"Unrecognized native command: {name}")
    request = {"id": 1, "type": name, **(arguments or {})}
    try:
        validated = request if entry[1] is False else entry[1](request)
        if any(validated.get(key) != value for key, value in request.items()):
            raise ValueError("Native command arguments changed")
    except Exception as err:
        raise probe_error(f"Native command schema changed: {name}", err) from err
    return cast(HandlerTable, table), cast(HandlerEntry, entry)


class ProbeConnection:
    """Collect native responses without a socket, persistent user or subscription."""

    def __init__(self, hass: HomeAssistant, *, admin: bool = True) -> None:
        policy = {"entities": True} if admin else {
            "entities": {"entity_ids": {"sensor.loona_probe": {"read": True}}}
        }
        self.user = User(
            name="Loona capability probe", is_active=True,
            perm_lookup=PermissionLookup(er.async_get(hass), dr.async_get(hass)),
            groups=[Group(name="Loona probe", id="system-admin" if admin else "loona-probe", policy=policy)],
        )
        self.subscriptions: dict[int, Callable[[], None]] = {}
        self.packets: list[dict[str, Any]] = []

    @callback
    def send_message(self, payload: bytes | str | dict[str, Any]) -> None:
        self.packets.append(cast(dict[str, Any], json_loads_object(payload))
                            if isinstance(payload, (bytes, str)) else payload)

    @callback
    def send_result(self, msg_id: int, result: Any = None) -> None:
        self.send_message(messages.message_to_json_bytes(messages.result_message(msg_id, result)))

    @callback
    def send_event(self, msg_id: int, event: Any) -> None:
        self.send_message({"id": msg_id, "type": "event", "event": event})

    def result(self) -> Any:
        """Reject missing, duplicate or failed native result envelopes."""
        replies = [packet for packet in self.packets if packet.get("type") == "result"]
        if len(replies) != 1 or replies[0].get("id") != 1 or replies[0].get("success") is not True:
            raise CompatibilityError("Native command response changed")
        return replies[0]["result"]

    def close(self) -> None:
        for unsubscribe in self.subscriptions.values():
            unsubscribe()
        self.subscriptions.clear()


def probe_sync(hass: HomeAssistant, handler: Any, request: dict[str, Any], connection: ProbeConnection) -> None:
    """Run a synchronous, read-only native command and fail closed on changes."""
    try:
        if iscoroutinefunction(unwrap(handler)):
            raise CompatibilityError("Native command is no longer synchronous")
        schema = getattr(handler, "_ws_schema", False)
        validated = schema(request) if isinstance(schema, vol.Schema) else request
        result = handler(hass, cast(websocket_api.ActiveConnection, connection), validated)
        if isawaitable(result):
            if callable(close := getattr(result, "close", None)):
                close()
            raise CompatibilityError("Native command is no longer synchronous")
        connection.result()
    except CompatibilityError:
        raise
    except Exception as err:
        raise probe_error(f"Native behavior probe failed: {request['type']} ({type(err).__name__})", err) from err


def probe_subscription(
    hass: HomeAssistant, handler: Any, request: dict[str, Any], connection: ProbeConnection,
) -> Callable[[Event[Any]], None]:
    """Capture a listener on an isolated bus; never fire a real HA event."""
    listeners: list[Callable[[Event[Any]], None]] = []

    @callback
    def listen(event_type: str, listener: Callable[[Event[Any]], None]) -> Callable[[], None]:
        if event_type != request.get("event_type", ha_const.EVENT_STATE_CHANGED):
            raise CompatibilityError("Native subscription event type changed")
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    states = [State("sensor.loona_probe", "1"), State("sensor.loona_denied", "2")]
    isolated = SimpleNamespace(
        states=SimpleNamespace(async_all=lambda: states), bus=SimpleNamespace(async_listen=listen),
    )
    probe_sync(cast(HomeAssistant, isolated), handler, request, connection)
    if len(listeners) != 1 or not callable(connection.subscriptions.get(1)):
        raise CompatibilityError("Native subscription lifecycle changed")
    return listeners[0]


def inspect_command(hass: HomeAssistant) -> tuple[HandlerTable, HandlerEntry]:
    """Probe snapshots, explicit scopes, live diffs and read permissions."""
    table, entry = inspect_native_command(
        hass, SUBSCRIBE_ENTITIES, getattr(commands, "handle_subscribe_entities", None),
        {"entity_ids": ["sensor.loona_probe"]},
    )
    for admin, arguments, expected in (
        (True, {}, {"sensor.loona_probe", "sensor.loona_denied"}),
        (True, {"entity_ids": []}, {"sensor.loona_probe", "sensor.loona_denied"}),
        (True, {"entity_ids": ["sensor.loona_probe"]}, {"sensor.loona_probe"}),
        (False, {}, {"sensor.loona_probe"}),
    ):
        connection = ProbeConnection(hass, admin=admin)
        try:
            request = {"id": 1, "type": SUBSCRIBE_ENTITIES, **arguments}
            listener = probe_subscription(hass, entry[0], request, connection)
            snapshots = [packet["event"]["a"] for packet in connection.packets if "a" in packet.get("event", {})]
            if len(snapshots) != 1 or set(snapshots[0]) != expected:
                raise CompatibilityError("Native snapshot filtering or permissions changed")
            for entity_id in ("sensor.loona_probe", "sensor.loona_denied"):
                before = State(entity_id, "1")
                after = State(entity_id, "3")
                for old, new, key in ((None, after, "a"), (before, after, "c"), (after, None, "r")):
                    connection.packets.clear()
                    listener(Event(ha_const.EVENT_STATE_CHANGED, {
                        "entity_id": entity_id, "old_state": old, "new_state": new,
                    }))
                    diffs = [packet.get("event", {}).get(key, {}) for packet in connection.packets]
                    if entity_id in expected:
                        if len(diffs) != 1 or set(diffs[0]) != {entity_id}:
                            raise CompatibilityError("Native live entity diffs changed")
                    elif connection.packets:
                        raise CompatibilityError("Native live filtering or permissions changed")
        except CompatibilityError:
            raise
        except Exception as err:
            raise probe_error(f"Native entity behavior probe failed ({type(err).__name__})", err) from err
        finally:
            connection.close()
    return table, entry
