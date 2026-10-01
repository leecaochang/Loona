"""Optional troubleshooting rescan using the native Lovelace loader."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import LoonaEntity
from .runtime import LoonaConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([LoonaRescan(entry.runtime_data, "rescan", "Rescan dashboards")])


class LoonaRescan(LoonaEntity, ButtonEntity):
    """Coalesce manual requests with automatic scans."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        await self.runtime.async_scan(force=True)
