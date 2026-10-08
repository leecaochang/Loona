"""Exercise dependency privacy, paging, reset and bootstrap attribution."""

import pytest
from pathlib import Path
import subprocess

from homeassistant.helpers import entity_registry as er

from custom_components.loona import async_setup_entry, async_unload_entry
from custom_components.loona.preview import statistics_report
from custom_components.loona.diagnostics import async_get_config_entry_diagnostics


def test_browser_performance_measurement():
    result = subprocess.run(["node", str(Path(__file__).with_name("performance.mjs"))],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


async def test_browser_reports_are_admin_only_bounded_and_separate(preview_runtime, make_user, make_connection):
    runtime = preview_runtime
    report = {"type": "loona/browser_report", "dashboard": "wall-panel", "duration_ms": 30000,
              "loaf_supported": True, "frames": 1, "blocking_ms": 10,
              "scripts": [{"source": "/hacsfiles/example/card.js", "phase": "window",
                           "duration_ms": 60, "forced_layout_ms": 5}],
              "subscriptions": [{"type": "subscribe_events/state_changed", "count": 1}]}
    admin, output = make_connection(make_user(admin=True))
    admin.async_handle({"id": 1, **report})
    assert output[-1]["success"]
    assert runtime.live_statistics.browser_reports["wall-panel"]["frames"] == 1
    assert runtime.live_statistics.forwarded == 0
    diagnostics = await async_get_config_entry_diagnostics(runtime.hass, runtime.entry)
    assert diagnostics["browser_reports"][0]["scripts"][0]["source"] != report["scripts"][0]["source"]
    assert report["scripts"][0]["source"] not in str(diagnostics)
    for i, fields in enumerate([{"blocking_ms": float('nan')}, {"blocking_ms": float('inf')},
                               {"scripts": report["scripts"] * 41}, {"duration_ms": -1},
                               {"dashboard": "missing"}, {"sent": 999}], 2):
        admin.async_handle({"id": i, **report, **fields})
        assert not output[-1]["success"]
    reader, denied = make_connection(make_user(allowed={"sensor.wall"}))
    reader.async_handle({"id": 1, **report})
    assert not denied[-1]["success"]
    runtime.live_statistics.reset()
    assert not runtime.live_statistics.browser_reports


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


async def test_page_load_reported_before_card_files_gets_them_later(preview_runtime, make_user, make_connection):
    # The statistics module reports as soon as states arrive, before the dashboard asks for its card files.
    runtime = preview_runtime
    connection, _ = make_connection(make_user(admin=True))
    connection.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    connection.async_handle({'id': 2, 'type': 'subscribe_entities'})
    connection.async_handle({'id': 3, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] is None
    runtime._observe_resource_load(connection, 9, 4)
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] == {'available': 9, 'sent': 4}
    # Later lists on the same page never replace the first counts.
    runtime._observe_resource_load(connection, 9, 9)
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] == {'available': 9, 'sent': 4}
    # A newer load of the same dashboard is never overwritten with an older page's counts.
    late, _ = make_connection(make_user(admin=True))
    late.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    late.async_handle({'id': 2, 'type': 'subscribe_entities'})
    late.async_handle({'id': 3, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    newer, _ = make_connection(make_user(admin=True))
    newer.async_handle({'id': 1, 'type': 'loona/subscribe_panel', 'dashboard': 'wall-panel'})
    newer.async_handle({'id': 2, 'type': 'subscribe_entities'})
    newer.async_handle({'id': 3, 'type': 'loona/page_load', 'dashboard': 'wall-panel'})
    runtime._observe_resource_load(late, 9, 8)
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] is None
    runtime._observe_resource_load(newer, 9, 3)
    assert runtime.live_statistics.page_loads['wall-panel']['resources'] == {'available': 9, 'sent': 3}


async def test_optional_dashboard_failure_keeps_filtering_alive(preview_runtime, monkeypatch, make_user, make_connection):
    runtime = preview_runtime

    def fail_collection():
        raise OSError('Native collection storage is unavailable')

    runtime.hass.config_entries.async_update_entry(runtime.entry, options={"dashboard_cards": ["statistics"]})
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


async def test_rate_history_requires_admin_and_explicit_opt_in(preview_runtime, make_user, make_connection):
    """History adds no payload to default readers and no new sampling on reads."""
    from unittest.mock import patch
    runtime = preview_runtime
    for _ in range(3):
        runtime.live_statistics.record(True)
    with patch("custom_components.loona.statistics.monotonic", return_value=runtime.live_statistics._sample_time + 30):
        runtime.live_statistics.sample()
    admin, output = make_connection(make_user(admin=True))
    admin.async_handle({"id": 1, "type": "loona/statistics"})
    assert output[-1]["result"]["rate_history"] == []
    admin.async_handle({"id": 2, "type": "loona/statistics", "include_rate_history": True})
    history = output[-1]["result"]["rate_history"]
    assert len(history) == 1 and history[0]["sent"] == .1
    admin.async_handle({"id": 3, "type": "loona/statistics", "include_rate_history": True})
    assert output[-1]["result"]["rate_history"] == history
    reader, denied = make_connection(make_user())
    reader.async_handle({"id": 1, "type": "loona/statistics", "include_rate_history": True})
    assert denied[-1]["error"]["code"] == "unauthorized"
    runtime.live_statistics.reset()
    assert statistics_report(runtime, True)["rate_history"] == []
