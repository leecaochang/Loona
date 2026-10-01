"""Loona native dashboard entity filtering integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

from .compatibility import CompatibilityError
from .const import DOMAIN, STATISTICS_COMMAND, PAGE_LOAD_COMMAND
from .graph_loading import async_register_frontend
from .runtime import LoonaConfigEntry, LoonaRuntime
from .preview import websocket_statistics, websocket_page_load
from .statistics_card import StatisticsCard, StatisticsCardError

_PLATFORMS = (Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON)


async def async_setup_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> bool:
    """Dependencies guarantee native commands exist before hook installation."""
    runtime = LoonaRuntime(hass, entry)
    entry.runtime_data = runtime
    table = hass.data[websocket_api.DOMAIN]
    if any(name in table for name in (STATISTICS_COMMAND, PAGE_LOAD_COMMAND)):
        raise CompatibilityError("Another handler owns Loona statistics")
    try:
        await runtime.async_start()
        # The route must exist before Core freezes its HTTP router. The optional
        # module URL is added only when the user installs the statistics card.
        if hasattr(hass, "http"):
            try:
                await runtime.statistics_card.register_asset()
            except StatisticsCardError:
                pass
        if runtime.graph_adapter is not None:
            try:
                unsubscribe = await async_register_frontend(hass)
            except CompatibilityError as err:
                runtime.graph_compatibility_problem = str(err)
                runtime.graph_adapter.uninstall()
                runtime.graph_adapter = None
                runtime._update_issues()
            else:
                runtime._unsubscribers.append(unsubscribe)
        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
        await runtime.async_scan()
    except Exception:
        await runtime.async_stop()
        raise
    hass.data[DOMAIN] = runtime
    websocket_api.async_register_command(hass, websocket_statistics)
    websocket_api.async_register_command(hass, websocket_page_load)
    owned = {name: table[name] for name in (STATISTICS_COMMAND, PAGE_LOAD_COMMAND)}
    def remove_command() -> None:
        for name, command in owned.items():
            if table.get(name) is command:
                table.pop(name)
    runtime._unsubscribers.append(remove_command)
    await runtime.async_update_statistics_card()
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: LoonaConfigEntry) -> None:
    """Keep the adapter and its existing subscriptions alive on options edits."""
    await entry.runtime_data.async_scan()
    await entry.runtime_data.async_update_statistics_card()


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
    card = StatisticsCard(hass, entry.entry_id)
    try:
        await card.set_enabled(False)
    except StatisticsCardError:
        # Removing an integration must preserve edited or unverifiable boards.
        await card.store.async_remove()
