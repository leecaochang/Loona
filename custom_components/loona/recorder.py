"""Remove statistics only for sensors with native Loona ownership records."""

import asyncio
import logging
from collections.abc import Callable, Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, RECORDER_CLEANUP_SECONDS

_LOGGER = logging.getLogger(__name__)


def owned_statistic_ids(hass: HomeAssistant, entry_id: str) -> list[str]:
    """Include this entry and deleted Loona sensors whose entry no longer exists."""
    registry = er.async_get(hass)
    candidates: list[er.RegistryEntry | er.DeletedRegistryEntry] = [
        item for item in registry.entities.values()
        if item.platform == DOMAIN and item.config_entry_id == entry_id
    ]
    candidates.extend(
        item for item in registry.deleted_entities.values()
        if item.platform == DOMAIN and (item.config_entry_id == entry_id
        or item.config_entry_id is None
        or hass.config_entries.async_get_entry(item.config_entry_id) is None)
    )
    result = set()
    for item in candidates:
        if item.platform != DOMAIN or item.domain != "sensor":
            continue
        current = registry.async_get(item.entity_id)
        if current is None and hass.states.get(item.entity_id) is not None:
            # An unregistered active entity can also reuse a retired Loona ID.
            continue
        if current is not None and (
            current.platform != DOMAIN or current.config_entry_id != entry_id
        ):
            # A foreign entity can reuse an ID from an old Loona tombstone.
            continue
        result.add(item.entity_id)
    return sorted(result)


def retired_statistic_ids(hass: HomeAssistant, entity_ids: Iterable[str]) -> list[str]:
    """Skip IDs that a registered or active entity has taken back since removal."""
    registry = er.async_get(hass)
    return sorted(
        entity_id for entity_id in set(entity_ids)
        if registry.async_get(entity_id) is None and hass.states.get(entity_id) is None
    )


async def async_clear_owned_statistics(hass: HomeAssistant, entry_id: str) -> None:
    """Clear every sensor this entry owns or once owned when it is uninstalled."""
    await _async_clear(hass, lambda: owned_statistic_ids(hass, entry_id))


async def async_clear_retired_statistics(hass: HomeAssistant, entity_ids: Iterable[str]) -> None:
    """Clear sensors removed while the entry keeps running, such as untracked dashboards."""
    await _async_clear(hass, lambda: retired_statistic_ids(hass, entity_ids))


async def _async_clear(hass: HomeAssistant, select: Callable[[], list[str]]) -> None:
    """Queue native deletion and bound waiting without blocking entity removal."""
    if "recorder" not in hass.config.components:
        return
    try:
        from homeassistant.components.recorder.util import get_instance

        # Selected right before queueing so nothing can reclaim an ID in between.
        statistic_ids = select()
        if not statistic_ids:
            return
        instance = get_instance(hass)
        clear = instance.async_clear_statistics
        code = getattr(clear, "__code__", None)
        supports_done = code is not None and "on_done" in code.co_varnames[:code.co_argcount + code.co_kwonlyargcount]
        async with asyncio.timeout(RECORDER_CLEANUP_SECONDS):
            if supports_done:
                done = asyncio.Event()
                def completed() -> None:
                    hass.loop.call_soon_threadsafe(done.set)
                clear(statistic_ids, on_done=completed)
                await done.wait()
            else:
                # Core 2024.6 has no completion callback; its queue still owns deletion.
                clear(statistic_ids)
                await instance.async_block_till_done()
    except TimeoutError:
        _LOGGER.warning("Loona statistics cleanup is still queued in Recorder after the wait limit")
    except Exception:
        _LOGGER.exception("Unable to clean up Loona Recorder statistics")
