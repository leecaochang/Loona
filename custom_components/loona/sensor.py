"""Graphable entity estimates and per-dashboard discovery counts."""

import asyncio
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import LoonaEntity
from .runtime import LoonaConfigEntry, LoonaRuntime

_METRICS = {
    "union_entities": "Union entities",
    "current_scope": "Current scope entities",
    "reduction_estimate": "Entity count reduction estimate",
    "managed_subscriptions": "Managed subscriptions",
    "filtered_subscriptions": "Filtered subscriptions",
    "last_scan": "Last successful scan",
    "scan_duration": "Scan duration",
    "forwarded_rate": "Entity updates forwarded per second",
    "avoided_rate": "Entity updates avoided per second",
    "update_reduction": "Live entity update reduction",
    "forwarded_updates": "Entity updates forwarded",
    "avoided_updates": "Entity updates avoided",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    async_add_entities(
        [LoonaSensor(runtime, key, name) for key, name in _METRICS.items()]
    )
    children: dict[str, list[LoonaSensor]] = {}
    tasks: set[asyncio.Task] = set()
    removing: set[str] = set()
    stopped = False

    async def remove(key: str, entities: list[LoonaSensor]) -> None:
        if key in runtime.selected_dashboards:
            removing.discard(key)
            return
        for entity in entities:
            if entity.hass is not None:
                await entity.async_remove(force_remove=True)
                registry = er.async_get(hass)
                if registry.async_get(entity.entity_id):
                    registry.async_remove(entity.entity_id)
        children.pop(key, None)
        device_id = runtime.dashboard_devices.get(key)
        if device_id and key not in runtime.selected_dashboards:
            runtime.dashboard_devices.pop(key)
            dr.async_get(hass).async_remove_device(device_id)
        removing.discard(key)
        sync()

    @callback
    def sync() -> None:
        if stopped:
            return
        for key in runtime.selected_dashboards:
            if key not in children:
                children[key] = [
                    LoonaSensor(runtime, metric, name, key)
                    for metric, name in (
                        ("discovered_entities", "Discovered entities"),
                        ("unresolved_entities", "Unresolved entities"),
                    )
                ]
                async_add_entities(children[key])
        for key in set(children) - set(runtime.selected_dashboards) - removing:
            removing.add(key)
            task = hass.async_create_task(
                remove(key, children[key]), "Remove Loona dashboard statistics"
            )
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    @callback
    def cleanup() -> None:
        nonlocal stopped
        stopped = True
        unsubscribe()
        for task in tasks:
            task.cancel()

    unsubscribe = runtime.async_add_listener(sync)
    entry.async_on_unload(cleanup)
    sync()


class LoonaSensor(LoonaEntity, SensorEntity):
    """Counts are gauges; reduction estimates do not measure bytes or CPU."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, runtime: LoonaRuntime, key: str, name: str, dashboard: str | None = None
    ) -> None:
        super().__init__(runtime, key, name, dashboard)
        self.key = key
        if key == "last_scan":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if key in ("reduction_estimate", "update_reduction"):
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif key == "scan_duration":
            self._attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
        elif key in ("forwarded_rate", "avoided_rate"):
            self._attr_native_unit_of_measurement = "updates/s"
        elif key in ("forwarded_updates", "avoided_updates"):
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_native_unit_of_measurement = "updates"

    @property
    def native_value(self) -> Any:
        if self.dashboard is not None:
            if self.key == "unresolved_entities":
                return len(self.runtime.unresolved.get(self.dashboard, ()))
            result = self.runtime.dashboards.get(self.dashboard)
            return len(result.entity_ids) if result else 0
        return self.runtime.metrics()[self.key]
