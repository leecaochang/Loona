"""Verify logical update counting against native delivery and permissions."""

from dataclasses import replace
from unittest.mock import patch

from custom_components.loona.statistics import LiveStatistics
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter


def test_statistics_rates_idle_window_and_reset():
    with patch('custom_components.loona.statistics.monotonic', return_value=10):
        statistics = LiveStatistics()
    statistics.record(True)
    for _ in range(3):
        statistics.record(False)
    with patch('custom_components.loona.statistics.monotonic', return_value=12):
        statistics.sample()
    assert statistics.metrics() == {
        'forwarded_updates': 1, 'avoided_updates': 3,
        'forwarded_rate': .5, 'avoided_rate': 1.5, 'update_reduction': 75.0,
    }
    with patch('custom_components.loona.statistics.monotonic', return_value=14):
        statistics.sample()
    assert statistics.forwarded_rate == statistics.avoided_rate == statistics.reduction == 0
    assert statistics.forwarded == 1 and statistics.avoided == 3
    with patch('custom_components.loona.statistics.monotonic', return_value=15):
        statistics.reset()
    assert set(statistics.metrics().values()) == {0}
    statistics.record(False)
    with patch('custom_components.loona.statistics.monotonic', return_value=17):
        statistics.sample()
    assert statistics.avoided_rate == .5 and statistics.reduction == 100


async def test_updates_match_native_permission_scope_and_bypass(hass, make_user, make_connection):
    for entity_id in ('sensor.keep', 'sensor.drop', 'sensor.denied', 'sensor.telemetry'):
        hass.states.async_set(entity_id, '0')
    await hass.async_block_till_done()
    user = make_user(allowed={'sensor.keep', 'sensor.drop', 'sensor.telemetry'})
    connection, output = make_connection(user)
    other, other_output = make_connection(make_user(admin=True))
    statistics = LiveStatistics()
    statistics.ignored = frozenset({'sensor.telemetry'})
    adapter = SubscriptionAdapter(hass,
        ScopePolicy(frozenset({'sensor.keep', 'sensor.telemetry'}), frozenset({user.id})), statistics)
    adapter.install()
    try:
        connection.async_handle({'id': 1, 'type': 'subscribe_entities'})
        other.async_handle({'id': 1, 'type': 'subscribe_entities'})
        connection.async_handle({'id': 2, 'type': 'subscribe_entities', 'entity_ids': ['sensor.drop']})
        assert statistics.forwarded == statistics.avoided == 0, 'Snapshots are not live updates'
        output.clear()
        for entity_id in ('sensor.keep', 'sensor.drop', 'sensor.denied', 'sensor.telemetry'):
            hass.states.async_set(entity_id, '1')
        await hass.async_block_till_done()
        assert statistics.forwarded == statistics.avoided == 1
        assert len([packet for packet in output if packet.get('id') == 1]) == 2
        assert len([packet for packet in output if packet.get('id') == 2]) == 1
        adapter.set_policy(replace(adapter.policy, enabled=False))
        assert statistics.forwarded == statistics.avoided == 1, 'Reconciliation snapshots are excluded'
        hass.states.async_set('sensor.drop', '2')
        await hass.async_block_till_done()
        assert statistics.forwarded == 2 and statistics.avoided == 1
        user.groups = []
        hass.states.async_set('sensor.keep', '2')
        await hass.async_block_till_done()
        assert statistics.forwarded == 2 and statistics.avoided == 1
        connection.subscriptions[1]()
        hass.states.async_set('sensor.drop', '3')
        await hass.async_block_till_done()
        assert statistics.forwarded == 2 and statistics.avoided == 1
    finally:
        adapter.uninstall()


async def test_multiple_clients_creation_removal_and_reset(hass, make_user, make_connection):
    hass.states.async_set('sensor.keep', '0')
    await hass.async_block_till_done()
    statistics = LiveStatistics()
    adapter = SubscriptionAdapter(hass, ScopePolicy(frozenset({'sensor.keep'}), all_users=True), statistics)
    adapter.install()
    try:
        connections = [make_connection(make_user(admin=True))[0] for _ in range(2)]
        for connection in connections:
            connection.async_handle({'id': 1, 'type': 'subscribe_entities'})
        hass.states.async_set('sensor.drop', '0')
        hass.states.async_remove('sensor.keep')
        await hass.async_block_till_done()
        assert statistics.forwarded == statistics.avoided == 2
        statistics.reset()
        assert adapter.managed_count == 2
        hass.states.async_set('sensor.keep', '1')
        await hass.async_block_till_done()
        assert statistics.forwarded == 2 and statistics.avoided == 0
        adapter.uninstall()
        hass.states.async_set('sensor.drop', '1')
        await hass.async_block_till_done()
        assert statistics.forwarded == 2 and statistics.avoided == 0
    finally:
        adapter.uninstall()
