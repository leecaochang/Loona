"""Persisted filtering and performance controls with immediate subscription reconciliation."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONTROL_DEFAULTS
from .entity import LoonaEntity
from .runtime import LoonaConfigEntry, LoonaRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            LoonaSwitch(entry.runtime_data, key) for key in CONTROL_DEFAULTS
        ]
    )


class LoonaSwitch(LoonaEntity, SwitchEntity):
    """The options flow and switch operate the same stored boolean."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: LoonaRuntime, key: str) -> None:
        super().__init__(runtime, key)
        self.key = key

    @property
    def available(self) -> bool:
        return self.key in self.runtime.available_controls

    @property
    def is_on(self) -> bool:
        return self.runtime.controls[self.key]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.runtime.async_set_control(self.key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.runtime.async_set_control(self.key, False)
