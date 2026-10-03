"""Verify logical update counting against native delivery and permissions."""

from dataclasses import replace
from unittest.mock import patch

from custom_components.loona.statistics import LiveStatistics
from custom_components.loona.const import NOISY_ENTITY_LIMIT, NOISY_ENTITY_REPORT_LIMIT
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter


def test_entity_attribution_bounds_overflow_and_reset():
    statistics = LiveStatistics()
    for index in range(NOISY_ENTITY_LIMIT + 1):
        statistics.record(True, f"sensor.example_{index}")
    statistics.record(True, "sensor.example_0")
    statistics.record(False, "sensor.not_sent")
    report = statistics.noisy_report()
    assert len(statistics.noisy_entities) == NOISY_ENTITY_LIMIT
    assert len(report["entities"]) == NOISY_ENTITY_REPORT_LIMIT
    assert report["entities"][0] == {"entity_id": "sensor.example_0", "updates": 2}
    assert report["untracked_updates"] == 1
    statistics.reset()
    assert statistics.noisy_report() == {"entities": [], "untracked_updates": 0}


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
        assert statistics.noisy_report()["entities"] == [{"entity_id": "sensor.keep", "updates": 1}]
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


def test_rate_history_is_bounded_sampling_only_and_resets():
    """Reads do not add samples, and idle windows remain visible in history."""
    from datetime import datetime, timedelta, UTC
    from custom_components.loona.const import RATE_HISTORY_LIMIT
    with patch("custom_components.loona.statistics.monotonic", return_value=0):
        statistics = LiveStatistics()
    start = datetime(2026, 10, 3, tzinfo=UTC)
    for index in range(RATE_HISTORY_LIMIT + 5):
        if index % 2 == 0:
            for _ in range(60):
                statistics.record(True)
        at = start + timedelta(seconds=30 * (index + 1))
        with patch("custom_components.loona.statistics.monotonic", return_value=30 * (index + 1)), patch("custom_components.loona.statistics.dt_util.utcnow", return_value=at):
            statistics.sample()
    rows = list(statistics.rate_history)
    assert len(rows) == RATE_HISTORY_LIMIT
    assert rows[0]["at"] == (start + timedelta(seconds=180)).isoformat()
    assert rows[-1] == {"at": at.isoformat(), "seconds": 30.0, "sent": 2.0, "filtered": 0.0}
    assert {row["sent"] for row in rows} == {0.0, 2.0}
    statistics.metrics()
    assert list(statistics.rate_history) == rows
    statistics.reset()
    assert not statistics.rate_history
