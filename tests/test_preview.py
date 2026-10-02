"""Exercise dependency privacy, paging, reset and bootstrap attribution."""

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.loona import async_setup_entry, async_unload_entry
from custom_components.loona.preview import statistics_report


@pytest.fixture
async def preview_runtime(loona_hass, make_entry, dashboards, frontend_http):
    loona_hass.config.components.update({'lovelace', 'frontend'})
    loona_hass.states.async_set('sensor.wall', '0')
    loona_hass.states.async_set('sensor.other', '0')
    entry = make_entry({'dashboards': ['wall-panel'], 'target_mode': 'all'}, options={
        'extra_entities': ['sensor.future'], 'exclude_globs': ['sensor.wall'],
    })
    async with entry.setup_lock:
        assert await async_setup_entry(loona_hass, entry)
    await loona_hass.async_block_till_done()
    yield entry.runtime_data
    assert await async_unload_entry(loona_hass, entry)
    await entry._async_process_on_unload(loona_hass)


async def test_statistics_privacy_and_removed_dependency_preview(preview_runtime, make_user, make_connection):
    admin, output = make_connection(make_user(admin=True))
    admin.async_handle({'id': 1, 'type': 'loona/statistics'})
    assert output[-1]['success']
    assert 'dependencies' not in output[-1]['result']
    notices = {row['code']: row for row in output[-1]['result']['notices']}
    assert notices['excluded_dependencies']['items'] == ['sensor.wall']
    reader, denied = make_connection(make_user(allowed={'sensor.wall'}))
    reader.async_handle({'id': 1, 'type': 'loona/statistics'})
    assert not denied[-1]['success'] and 'result' not in denied[-1]
    admin.async_handle({'id': 2, 'type': 'loona/statistics', 'offset': -1})
    assert not output[-1]['success']
    admin.async_handle({'id': 3, 'type': 'loona/statistics', 'search': 'x' * 161})
    assert not output[-1]['success']


async def test_native_reset_and_own_telemetry_exclusion(preview_runtime, make_user, make_connection):
    runtime = preview_runtime
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={'extra_entities': ['sensor.future']})
    await runtime.async_scan()
    connection, _ = make_connection(make_user(admin=True))
    connection.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    connection.async_handle({'id': 2, 'type': 'subscribe_entities'})
    runtime.hass.states.async_set('sensor.wall', '1')
    runtime.hass.states.async_set('sensor.other', '1')
    await runtime.hass.async_block_till_done()
    assert runtime.live_statistics.forwarded == runtime.live_statistics.avoided == 1
    entities = er.async_entries_for_config_entry(er.async_get(runtime.hass), runtime.entry.entry_id)
    reset = next(item for item in entities if item.unique_id.endswith(':reset_live_statistics'))
    settings, controls = dict(runtime.settings), dict(runtime.controls)
    await runtime.hass.services.async_call('button', 'press', {'entity_id': reset.entity_id}, blocking=True)
    await runtime.hass.async_block_till_done()
    assert set(runtime.live_statistics.metrics().values()) == {0}
    assert runtime.settings == settings and runtime.controls == controls
    runtime.notify()
    await runtime.hass.async_block_till_done()
    assert set(runtime.live_statistics.metrics().values()) == {0}, 'Sensor refreshes must not count themselves'
    assert runtime.adapter.managed_count == 1


async def test_page_load_counts_are_per_socket_and_only_server_observed(preview_runtime, make_user, make_connection):
    runtime = preview_runtime
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    connection.async_handle({'id': 2, 'type': 'subscribe_entities'})
    native_snapshot = output[-1]['event']['a']
    connection.async_handle({'id': 3, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    row = runtime.live_statistics.page_loads['wall-panel']
    assert row['entities']['sent'] == len(native_snapshot)
    assert row['entities']['available'] == len(runtime.hass.states.async_entity_ids())
    assert row['resources'] is None
    connection.async_handle({'id': 4, 'type': 'loona/page_load', 'dashboard': 'wall-panel', 'sent': 999999})
    assert not output[-1]['success']
    other, _ = make_connection(make_user(allowed={'sensor.other'}))
    other.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    other.async_handle({'id': 2, 'type': 'subscribe_entities'})
    other.async_handle({'id': 3, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    assert runtime.live_statistics.page_loads['wall-panel']['entities']['available'] == 1
    assert runtime.live_statistics.page_loads['wall-panel']['entities']['sent'] == 0
    runtime.adapter.observe_resources(connection, 7, 2)
    connection.async_handle({'id': 5, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] == {'available': 7, 'sent': 2}
    connection.async_handle_close()
    assert runtime.adapter.initial_counts(connection) is None
    assert runtime.adapter.resource_counts(connection) is None
    runtime.live_statistics.reset()
    assert runtime.live_statistics.page_loads == {}


async def test_optional_dashboard_failure_keeps_filtering_alive(preview_runtime, monkeypatch, make_user, make_connection):
    runtime = preview_runtime

    def fail_collection():
        raise OSError('Native collection storage is unavailable')

    monkeypatch.setattr(runtime.statistics_card, 'collection', fail_collection)
    await runtime.async_update_statistics_card()
    assert runtime.statistics_card_problem == 'Native statistics dashboard operation failed'
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    connection.async_handle({'id': 2, 'type': 'subscribe_entities'})
    assert 'sensor.other' not in output[-1]['event']['a']
    assert runtime.adapter.managed_count == 1


async def test_statistics_endpoint_rejects_removed_dependency_queries(preview_runtime, make_user, make_connection):
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({'id': 1, 'type': 'loona/statistics', 'include_dependencies': True})
    assert not output[-1]['success']
    assert 'dependencies' not in statistics_report(preview_runtime)
