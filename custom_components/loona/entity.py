"""Common native entities for Loona controls and compact statistics."""

from typing import Any

from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .runtime import LoonaRuntime


class LoonaEntity(Entity):
    """Listen to runtime publications without polling or large attributes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, runtime: LoonaRuntime, key: str, name: str, dashboard: str | None = None
    ) -> None:
        self.runtime = runtime
        self.dashboard = dashboard
        self._attr_unique_id = f"{runtime.entry.entry_id}:{dashboard or 'global'}:{key}"
        self._attr_name = name
        self._attr_translation_key = key

    @property
    def device_info(self) -> Any:
        if self.dashboard is not None:
            return {
                "identifiers": {
                    (
                        DOMAIN,
                        f"{self.runtime.entry.entry_id}:dashboard:{self.dashboard}",
                    )
                },
                "parent_device_id": self.runtime.device_id,
            }
        return {"identifiers": {(DOMAIN, self.runtime.entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.async_add_listener(self.async_write_ha_state))
