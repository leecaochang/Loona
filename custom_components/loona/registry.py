"""Filter native registry lists and refresh existing frontend collections."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast

import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.components import websocket_api
from homeassistant.components.config import (
    area_registry,
    device_registry,
    entity_registry,
    floor_registry,
    label_registry,
)
from homeassistant.components.websocket_api import commands, messages
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.util.json import json_loads_object

from .compatibility import CompatibilityError, HandlerEntry, HandlerTable
from .const import SUPPORTED_CORE_VERSIONS
from .dependencies import DiscoveryResult
from .websocket import ScopePolicy

_LISTS = {
    "config/entity_registry/list": (
        entity_registry.websocket_list_entities,
        "entity_id",
        "entities",
    ),
    "config/entity_registry/list_for_display": (
        entity_registry.websocket_list_entities_for_display,
        "ei",
        "entities",
    ),
    "config/device_registry/list": (
        device_registry.websocket_list_devices,
        "id",
        "devices",
    ),
    "config/area_registry/list": (
        area_registry.websocket_list_areas,
        "area_id",
        "areas",
    ),
    "config/floor_registry/list": (
        floor_registry.websocket_list_floors,
        "floor_id",
        "floors",
    ),
    "config/label_registry/list": (
        label_registry.websocket_list_labels,
        "label_id",
        "labels",
    ),
}
_EVENTS = {
    er.EVENT_ENTITY_REGISTRY_UPDATED: "entities",
    dr.EVENT_DEVICE_REGISTRY_UPDATED: "devices",
    ar.EVENT_AREA_REGISTRY_UPDATED: "areas",
    "floor_registry_updated": "floors",
    "label_registry_updated": "labels",
}


@dataclass(frozen=True)
class RegistryScope:
    """Retain direct dashboard targets and the metadata relationship closure."""

    entities: frozenset[str] = frozenset()
    devices: frozenset[str] = frozenset()
    areas: frozenset[str] = frozenset()
    floors: frozenset[str] = frozenset()
    labels: frozenset[str] = frozenset()


def registry_scope(
    hass: HomeAssistant,
    entity_ids: frozenset[str],
    dashboards: Iterable[DiscoveryResult],
) -> RegistryScope:
    """Keep parent devices, explicit/inherited areas, floors, and labels."""
    entities = set(entity_ids)
    devices: set[str] = set()
    areas: set[str] = set()
    floors: set[str] = set()
    labels: set[str] = set()
    targets = {
        "device_id": devices,
        "area_id": areas,
        "floor_id": floors,
        "label_id": labels,
    }
    for result in dashboards:
        for key, identifiers in result.targets.items():
            targets[key].update(identifiers)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    seen_entities: set[str] = set()
    seen_devices: set[str] = set()
    seen_areas: set[str] = set()
    while entities - seen_entities or devices - seen_devices or areas - seen_areas:
        for entity_id in entities - seen_entities:
            seen_entities.add(entity_id)
            if (entry := entity_registry.async_get(entity_id)) is None:
                continue
            if entry.device_id:
                devices.add(entry.device_id)
            if entry.area_id:
                areas.add(entry.area_id)
            labels.update(entry.labels)
        for device_id in devices - seen_devices:
            seen_devices.add(device_id)
            if (device := device_registry.async_get(device_id)) is None:
                continue
            if device.area_id:
                areas.add(device.area_id)
            labels.update(device.labels)
            for key in (
                ("parent_device_id",)
                if isinstance(device, dr.ChildDeviceEntry)
                else ("via_device_id",)
            ):
                if parent := getattr(device, key, None):
                    devices.add(parent)
        for area_id in areas - seen_areas:
            seen_areas.add(area_id)
            if (area := area_registry.async_get_area(area_id)) is None:
                continue
            if area.floor_id:
                floors.add(area.floor_id)
            labels.update(area.labels)
            for key in ("temperature_entity_id", "humidity_entity_id"):
                if metadata_entity := getattr(area, key, None):
                    entities.add(metadata_entity)
    return RegistryScope(
        *(frozenset(ids) for ids in (entities, devices, areas, floors, labels))
    )


class _ListConnection:
    """A single-call facade, including native handlers sending cached bytes."""

    def __init__(
        self,
        adapter: "RegistryAdapter",
        connection: websocket_api.ActiveConnection,
        request: dict[str, Any],
    ) -> None:
        self.adapter, self.connection, self.request = adapter, connection, request

    def __getattr__(self, name: str) -> Any:
        return getattr(self.connection, name)

    @callback
    def send_result(self, msg_id: int, result: Any = None) -> None:
        self.send_message(
            messages.message_to_json_bytes(messages.result_message(msg_id, result))
        )

    @callback
    def send_message(self, payload: bytes | str | dict[str, Any]) -> None:
        """Preserve errors, envelopes, fields, and native enabled-entry semantics."""
        try:
            message = (
                cast(dict[str, Any], json_loads_object(payload))
                if isinstance(payload, (bytes, str))
                else payload
            )
            if (
                message.get("type") != "result"
                or not message.get("success")
                or message.get("id") != self.request["id"]
            ):
                self.connection.send_message(payload)
                return
            _, key, kind = _LISTS[self.request["type"]]
            result = message["result"]
            display = self.request["type"].endswith("list_for_display")
            rows = result["entities"] if display else result
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not isinstance(row.get(key), str)
                for row in rows
            ):
                raise ValueError("Unrecognized registry list rows")
            if display and not isinstance(result.get("entity_categories"), dict):
                raise ValueError("Unrecognized entity category envelope")
            ids = getattr(self.adapter.scope, kind)
            filtered = [row for row in rows if row[key] in ids]
            message["result"] = (
                {**result, "entities": filtered} if display else filtered
            )
        except (ValueError, KeyError, TypeError, AttributeError) as err:
            self.adapter.fail(
                CompatibilityError(f"Registry response changed: {type(err).__name__}")
            )
            self.connection.send_message(payload)
            return
        self.connection.send_message(messages.message_to_json_bytes(message))


class RegistryAdapter:
    """Own list hooks and registry-specific refetch notifications only."""

    def __init__(
        self,
        hass: HomeAssistant,
        policy: ScopePolicy,
        scope: RegistryScope,
        on_failure: Callable[[CompatibilityError], None],
    ) -> None:
        self.hass, self.policy, self.scope = hass, policy, scope
        self.on_failure = on_failure
        self._table: HandlerTable | None = None
        self._originals: dict[str, HandlerEntry] = {}
        self._owned: dict[str, HandlerEntry] = {}
        self._watchers: dict[
            tuple[websocket_api.ActiveConnection, int],
            tuple[str, Callable[[], None], Callable[[], Any]],
        ] = {}

    def install(self) -> None:
        """Validate every original before installing any command replacement."""
        if self._table is not None:
            self.check_ownership()
            return
        if ha_const.__version__ not in SUPPORTED_CORE_VERSIONS:
            raise CompatibilityError(
                f"Unsupported registry Core version: {ha_const.__version__}"
            )
        table = self.hass.data.get(websocket_api.DOMAIN)
        if not isinstance(table, dict):
            raise CompatibilityError("Registry websocket commands are not registered")
        expected = {name: values[0] for name, values in _LISTS.items()}
        expected["subscribe_events"] = commands.handle_subscribe_events
        for name, native in expected.items():
            entry = table.get(name)
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or entry[0] is not native
                or entry[1] is not getattr(native, "_ws_schema", None)
                or not (entry[1] is False or isinstance(entry[1], vol.Schema))
            ):
                raise CompatibilityError(
                    f"Unrecognized native registry command: {name}"
                )
        self._table = cast(HandlerTable, table)
        self._originals = {name: table[name] for name in expected}
        for name in expected:
            handler = self._subscribe if name == "subscribe_events" else self._list
            self._owned[name] = (handler, table[name][1])
        table.update(self._owned)

    def check_ownership(self) -> None:
        if self._table is None:
            raise CompatibilityError("Loona no longer owns registry commands")
        for name, entry in self._owned.items():
            if self._table.get(name) is not entry:
                raise CompatibilityError(f"Loona no longer owns {name}")

    @callback
    def fail(self, error: CompatibilityError) -> None:
        self.uninstall()
        self.on_failure(error)

    @callback
    def _list(
        self,
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        native = self._originals[msg["type"]][0]
        try:
            self.check_ownership()
        except CompatibilityError as err:
            self.fail(err)
        if self._table is None or self.policy.scope_for(connection.user.id) is None:
            native(hass, connection, msg)
        else:
            native(
                hass,
                cast(
                    websocket_api.ActiveConnection,
                    _ListConnection(self, connection, msg),
                ),
                msg,
            )

    @callback
    def _subscribe(
        self,
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Delegate permission checks and leave native event contents unchanged."""
        try:
            self.check_ownership()
        except CompatibilityError as err:
            self.fail(err)
        self._originals["subscribe_events"][0](hass, connection, msg)
        event_type = msg["event_type"]
        if event_type not in _EVENTS or self._table is None:
            return
        key = (connection, msg["id"])
        original = connection.subscriptions[msg["id"]]

        @callback
        def unsubscribe() -> None:
            self._watchers.pop(key, None)
            original()

        connection.subscriptions[msg["id"]] = unsubscribe
        self._watchers[key] = (event_type, unsubscribe, original)

    @callback
    def _refresh(self, previous: ScopePolicy, scope: RegistryScope) -> None:
        for (connection, msg_id), (event_type, unsubscribe, _) in tuple(
            self._watchers.items()
        ):
            if connection.subscriptions.get(msg_id) is not unsubscribe:
                self._watchers.pop((connection, msg_id), None)
                continue
            before, after = (
                previous.scope_for(connection.user.id),
                self.policy.scope_for(connection.user.id),
            )
            kind = _EVENTS[event_type]
            if (before is None) == (after is None) and (
                after is None or getattr(scope, kind) == getattr(self.scope, kind)
            ):
                continue
            connection.send_event(
                msg_id, Event(event_type, {"action": "update"}).as_dict()
            )

    def set_policy(self, policy: ScopePolicy, scope: RegistryScope) -> None:
        self.check_ownership()
        previous, old_scope = self.policy, self.scope
        self.policy, self.scope = policy, scope
        self._refresh(previous, old_scope)

    def uninstall(self) -> None:
        """Restore only owned commands and refetch full lists before cleanup."""
        if self._table is None:
            return
        for name, entry in self._owned.items():
            if self._table.get(name) is entry:
                self._table[name] = self._originals[name]
        previous = self.policy
        self.policy = ScopePolicy(enabled=False)
        self._refresh(previous, self.scope)
        for (connection, msg_id), (_, unsubscribe, original) in self._watchers.items():
            if connection.subscriptions.get(msg_id) is unsubscribe:
                connection.subscriptions[msg_id] = original
        self._watchers.clear()
        self._table = None
