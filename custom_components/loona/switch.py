"""Persisted automation controls with immediate subscription reconciliation."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONTROL_ENTITIES, CONTROL_GRAPHS, CONTROL_MASTER, CONTROL_MOTION, CONTROL_REGISTRIES
from .entity import LoonaEntity
from .runtime import LoonaConfigEntry, LoonaRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [
            LoonaSwitch(entry.runtime_data, key, name)
            for key, name in (
                (CONTROL_MASTER, "Enabled"),
                (CONTROL_ENTITIES, "Entity filtering"),
                (CONTROL_REGISTRIES, "Registry filtering"),
                (CONTROL_GRAPHS, "Visible-first graphs"),
                (CONTROL_MOTION, "Pause animations during loading"),
            )
        ]
    )


class LoonaSwitch(LoonaEntity, SwitchEntity):
    """The options flow and switch operate the same stored boolean."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: LoonaRuntime, key: str, name: str) -> None:
        super().__init__(runtime, key, name)
        self.key = key

    @property
    def is_on(self) -> bool:
        return self.runtime.controls[self.key]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.runtime.async_set_control(self.key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.runtime.async_set_control(self.key, False)
