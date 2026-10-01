"""Native problem indicators for compatibility and dashboard discovery."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LoonaEntity
from .runtime import LoonaConfigEntry, LoonaRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [
            LoonaProblem(entry.runtime_data, key, name)
            for key, name in (
                ("compatibility_problem", "Compatibility problem"),
                ("scope_problem", "Scope problem"),
            )
        ]
    )


class LoonaProblem(LoonaEntity, BinarySensorEntity):
    """Repairs explains an active problem without copying dashboard data."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime: LoonaRuntime, key: str, name: str) -> None:
        super().__init__(runtime, key, name)
        self.key = key

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.runtime, self.key))
