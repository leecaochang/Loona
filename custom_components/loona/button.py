"""Optional troubleshooting rescan using the native Lovelace loader."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import LoonaEntity
from .runtime import LoonaConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoonaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([
        LoonaRescan(entry.runtime_data, "rescan", "Rescan dashboards"),
        LoonaResetStatistics(entry.runtime_data, "reset_live_statistics", "Reset live statistics"),
    ])


class LoonaRescan(LoonaEntity, ButtonEntity):
    """Coalesce manual requests with automatic scans."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        await self.runtime.async_scan(force=True)


class LoonaResetStatistics(LoonaEntity, ButtonEntity):
    """Clear live totals and rates without altering entity-count gauges."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:counter"

    async def async_press(self) -> None:
        self.runtime.async_reset_live_statistics()
