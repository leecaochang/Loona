"""Loona native dashboard entity filtering integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .graph_loading import async_register_frontend
from .runtime import LoonaConfigEntry, LoonaRuntime

_PLATFORMS = (Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON)


async def async_setup_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> bool:
    """Dependencies guarantee native commands exist before hook installation."""
    runtime = LoonaRuntime(hass, entry)
    entry.runtime_data = runtime
    try:
        await runtime.async_start()
        runtime._unsubscribers.append(await async_register_frontend(hass))
        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
        await runtime.async_scan()
    except Exception:
        await runtime.async_stop()
        raise
    hass.data[DOMAIN] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: LoonaConfigEntry) -> None:
    """Keep the adapter and its existing subscriptions alive on options edits."""
    await entry.runtime_data.async_scan()


async def async_unload_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> bool:
    """Restore surviving native subscriptions after platforms unload."""
    if not await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        return False
    await entry.runtime_data.async_stop()
    if hass.data.get(DOMAIN) is entry.runtime_data:
        hass.data.pop(DOMAIN)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> None:
    """Remove Loona's own control storage when the entry is deleted."""
    from homeassistant.helpers.storage import Store

    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.controls").async_remove()
