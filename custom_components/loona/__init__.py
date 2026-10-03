"""Loona native dashboard entity filtering integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

from .compatibility import CompatibilityError
from .bootstrap import async_install as async_install_bootstrap
from .const import DOMAIN, STATISTICS_COMMAND, PAGE_LOAD_COMMAND, SETTINGS_COMMAND, SETTINGS_SAVE_COMMAND, SETTINGS_CHOICES_COMMAND, BROWSER_REPORT_COMMAND
from .graph_loading import async_register_frontend
from .panels import async_register_frontend as async_register_panel_frontend
from .runtime import LoonaConfigEntry, LoonaRuntime
from .preview import websocket_statistics, websocket_page_load, websocket_browser_report
from .recorder import async_clear_owned_statistics
from .settings import websocket_settings, websocket_save_settings, websocket_settings_choices
from .statistics_card import StatisticsCard, StatisticsCardError

_PLATFORMS = (Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON)


async def async_setup_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> bool:
    """Install filtering adapters, native entities and frontend assets."""
    runtime = LoonaRuntime(hass, entry)
    entry.runtime_data = runtime
    table = hass.data[websocket_api.DOMAIN]
    if any(name in table for name in (STATISTICS_COMMAND, PAGE_LOAD_COMMAND, SETTINGS_COMMAND, SETTINGS_SAVE_COMMAND, SETTINGS_CHOICES_COMMAND, BROWSER_REPORT_COMMAND)):
        raise CompatibilityError("Another handler owns Loona statistics")
    try:
        await runtime.async_start()
        if hasattr(hass, "http"):
            try:
                runtime._unsubscribers.append(await async_register_panel_frontend(hass))
            except CompatibilityError as err:
                runtime.panel_compatibility_problem = str(err)
                runtime._update_issues()
            else:
                try:
                    bootstrap = await async_install_bootstrap(hass, runtime.bootstrap_policy)
                    runtime._unsubscribers.append(bootstrap.remove)
                    def refresh_bootstrap() -> None:
                        try:
                            bootstrap.refresh()
                        except CompatibilityError as err:
                            runtime.bootstrap_compatibility_problem = str(err)
                            runtime._update_issues()
                    runtime._unsubscribers.append(runtime.async_add_listener(refresh_bootstrap))
                    if not bootstrap.root_supported:
                        runtime.bootstrap_compatibility_problem = "Native root routing is unfamiliar; named dashboard URLs still support initial filtering"
                        runtime._update_issues()
                except CompatibilityError as err:
                    runtime.bootstrap_compatibility_problem = str(err)
                    runtime._update_issues()
        # The bundled route must exist before Core freezes its HTTP router.
        # Dashboard creation follows native platform and scope setup.
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
    websocket_api.async_register_command(hass, websocket_browser_report)
    websocket_api.async_register_command(hass, websocket_settings)
    websocket_api.async_register_command(hass, websocket_save_settings)
    websocket_api.async_register_command(hass, websocket_settings_choices)
    owned = {name: table[name] for name in (STATISTICS_COMMAND, PAGE_LOAD_COMMAND, SETTINGS_COMMAND, SETTINGS_SAVE_COMMAND, SETTINGS_CHOICES_COMMAND, BROWSER_REPORT_COMMAND)}
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
    """Remove owned settings, the unedited dashboard and Recorder statistics."""
    from homeassistant.helpers.storage import Store

    runtime = getattr(entry, "runtime_data", None)
    store = runtime._store if isinstance(runtime, LoonaRuntime) else Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.controls")
    card = runtime.statistics_card if isinstance(runtime, LoonaRuntime) else StatisticsCard(hass, entry.entry_id)
    await store.async_remove()
    try:
        await card.set_enabled(False)
    except StatisticsCardError:
        # Removing an integration must preserve edited or unverifiable boards.
        pass
    finally:
        await card.store.async_remove()
    await async_clear_owned_statistics(hass, entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: LoonaConfigEntry) -> bool:
    """Preserve existing choices and opt older installations out of new cards."""
    if entry.version > 2:
        return False
    if entry.version < 2:
        from .const import CONF_DASHBOARD_CARDS
        hass.config_entries.async_update_entry(
            entry, data={CONF_DASHBOARD_CARDS: [], **entry.data}, version=2
        )
    return True
