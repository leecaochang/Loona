"""Exercise parked ordinary feeds with Core snapshots, permissions and timers."""

from unittest.mock import Mock, patch
from pathlib import Path
import subprocess

import pytest

from custom_components.loona.config_flow import validate_idle_settings
from tests import test_panels
from tests.test_panels import command

panel_runtime = test_panels.panel_runtime
from tests.test_websocket import snapshot


def test_browser_idle_activity_lifecycle():
    result = subprocess.run(["node", str(Path(__file__).with_name("idle_updates.mjs"))], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("seconds", [0, 1, 10, 60])
async def test_idle_parks_live_listener_refreshes_native_snapshot_and_wakes(panel_runtime, make_user, make_connection, seconds):
    runtime = panel_runtime
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={"idle_refresh_seconds": seconds})
    await runtime.async_scan()
    await runtime.async_set_control("idle_updates", True)
    user = make_user(allowed={"sensor.wall"})
    connection, output = make_connection(user)
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", live_dashboard=True)
    command(connection, output, "subscribe_entities")
    retained = set(snapshot(output))
    timers = []

    def schedule(hass, delay, callback):
        cancel = Mock()
        timers.append((delay, callback, cancel))
        return cancel

    with patch("custom_components.loona.panels.async_call_later", side_effect=schedule):
        command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True, idle=True)
        assert set(snapshot(output)) == retained == {"sensor.wall"}
        assert not timers if seconds == 0 else timers[0][0] == seconds
        before = len(output)
        runtime.hass.states.async_set("sensor.wall", "2")
        runtime.hass.states.async_set("sensor.other", "private")
        await runtime.hass.async_block_till_done()
        assert not any("sensor.wall" in row.get("event", {}).get("c", {}) for row in output[before:])
        assert not any("sensor.other" in row.get("event", {}).get("a", {}) for row in output)
        if seconds:
            timers[0][1](None)
            assert snapshot(output)["sensor.wall"]["s"] == "2"
            assert len(timers) == 2
        else:
            assert snapshot(output)["sensor.wall"]["s"] == "1"
        command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True)
        assert snapshot(output)["sensor.wall"]["s"] == "2"
        if seconds:
            timers[-1][2].assert_called_once()
        before = len(output)
        runtime.hass.states.async_set("sensor.wall", "3")
        await runtime.hass.async_block_till_done()
        assert any("sensor.wall" in row.get("event", {}).get("c", {}) for row in output[before:])


async def test_idle_is_opt_in_and_preserves_explicit_and_native_panel_feeds(panel_runtime, make_user, make_connection):
    runtime = panel_runtime
    connection, output = make_connection(make_user(admin=True))
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", live_dashboard=True, idle=True)
    command(connection, output, "subscribe_entities")
    before = len(output)
    runtime.hass.states.async_set("sensor.wall", "2")
    await runtime.hass.async_block_till_done()
    assert any("sensor.wall" in row.get("event", {}).get("c", {}) for row in output[before:])
    await runtime.async_set_control("idle_updates", True)
    explicit = connection.last_id + 1
    command(connection, output, "subscribe_entities", entity_ids=["sensor.wall"])
    before = len(output)
    runtime.hass.states.async_set("sensor.wall", "3")
    await runtime.hass.async_block_till_done()
    assert {row["id"] for row in output[before:] if "c" in row.get("event", {})} == {explicit}
    command(connection, output, "loona/panel", dashboard="config", live_dashboard=True, idle=True)
    assert snapshot(output)["sensor.wall"]["s"] == "3"
    assert not runtime.idle_policy(connection)["enabled"]


@pytest.mark.parametrize("values", [
    {"idle_after_minutes": 0, "idle_refresh_seconds": 60},
    {"idle_after_minutes": 5, "idle_refresh_seconds": 61},
    {"idle_after_minutes": 5, "idle_refresh_seconds": -1},
    {"idle_after_minutes": 5, "idle_refresh_seconds": True},
    {"idle_after_minutes": 5, "idle_refresh_seconds": 1.5},
])
def test_idle_timing_rejects_invalid_values(values):
    with pytest.raises(ValueError):
        validate_idle_settings(values)


def test_native_number_values_are_integral():
    assert validate_idle_settings({"idle_after_minutes": 5.0, "idle_refresh_seconds": 60.0}) == {"idle_after_minutes": 5, "idle_refresh_seconds": 60}


async def test_idle_unload_restores_native_feeds_and_cancels_timer(panel_runtime, make_user, make_connection):
    runtime = panel_runtime
    await runtime.async_set_control("idle_updates", True)
    connection, output = make_connection(make_user(admin=True))
    cancel = Mock()
    with patch("custom_components.loona.panels.async_call_later", return_value=cancel):
        command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", live_dashboard=True, idle=True)
        command(connection, output, "subscribe_entities")
        runtime.hass.states.async_set("sensor.other", "new")
        await runtime.hass.async_block_till_done()
        await runtime.async_stop()
    cancel.assert_called_once()
    assert snapshot(output)["sensor.other"]["s"] == "new"
    before = len(output)
    runtime.hass.states.async_set("sensor.wall", "awake")
    await runtime.hass.async_block_till_done()
    assert any("sensor.wall" in row.get("event", {}).get("c", {}) for row in output[before:])


async def test_periodic_idle_refresh_preserves_hidden_tab_cache(panel_runtime, make_user, make_connection, dashboards):
    runtime = panel_runtime
    await dashboards["wall-panel"].async_save({"views": [
        {"path": "main", "cards": [{"type": "entity", "entity": "sensor.wall"}]},
        {"path": "other", "cards": [{"type": "entity", "entity": "sensor.other"}]},
    ]})
    await runtime.async_scan()
    await runtime.async_set_controls({**runtime.controls, "idle_updates": True, "current_dashboard_updates": True})
    connection, output = make_connection(make_user(admin=True))
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", view="main", live_dashboard=True)
    command(connection, output, "subscribe_entities")
    cached = dict(snapshot(output))
    assert cached["sensor.other"]["s"] == "1"
    runtime.hass.states.async_set("sensor.other", "waiting")
    await runtime.hass.async_block_till_done()
    command(connection, output, "loona/panel", dashboard="wall-panel", view="main", live_dashboard=True, idle=True)
    assert "sensor.other" not in snapshot(output), "Entering idle must preserve the hidden-tab cache"
    runtime.hass.states.async_set("sensor.wall", "2")
    runtime.hass.states.async_set("sensor.other", "2")
    await runtime.hass.async_block_till_done()
    before = len(output)
    runtime._refresh_idle(connection)
    additions = [row["event"]["a"] for row in output[before:] if "a" in row.get("event", {})]
    assert additions and all("sensor.other" not in row for row in additions)
    for row in additions:
        cached.update(row)
    assert cached["sensor.wall"]["s"] == "2"
    assert cached["sensor.other"]["s"] == "1"
    command(connection, output, "loona/panel", dashboard="wall-panel", view="other", live_dashboard=True)
    assert snapshot(output)["sensor.other"]["s"] == "2"
