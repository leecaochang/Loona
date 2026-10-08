"""Keep configuration selectors native while dashboard connections stay scoped."""

from pathlib import Path
import subprocess

import pytest

from homeassistant.helpers import entity_registry as er

from custom_components.loona.const import PANEL_COMMAND, PANEL_SUBSCRIBE
from custom_components.loona.runtime import LoonaRuntime
from tests.test_websocket import snapshot


def command(connection, output, kind, **fields):
    """Use native schema validation and monotonically increasing IDs."""
    msg_id = connection.last_id + 1
    connection.async_handle({"id": msg_id, "type": kind, **fields})
    result = next(row for row in reversed(output) if row.get("id") == msg_id and row["type"] == "result")
    assert result["success"], result
    return result["result"]


@pytest.fixture
async def panel_runtime(loona_hass, make_entry, dashboards):
    """A loaded, enabled AI Task deliberately has no dashboard reference."""
    registry = er.async_get(loona_hass)
    for domain, name in (("sensor", "wall"), ("sensor", "other"), ("ai_task", "configured")):
        entry = registry.async_get_or_create(domain, "test", name, suggested_object_id=name)
        loona_hass.states.async_set(entry.entity_id, "1")
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    runtime.entry.runtime_data = runtime
    await runtime.async_start()
    await runtime.async_set_control("registry_filtering", True)
    yield runtime
    await runtime.async_stop()


def entity_list(connection, output):
    return {row["entity_id"] for row in command(connection, output, "config/entity_registry/list")}


@pytest.mark.parametrize("panel", [None, "config", "developer-tools", "history", "lovelace"])
async def test_non_dashboard_panels_preserve_ai_task_and_native_lists(panel_runtime, make_user, make_connection, panel):
    connection, wire = make_connection(make_user(admin=True))
    if panel is not None:
        command(connection, wire, PANEL_SUBSCRIBE, dashboard=panel)
    command(connection, wire, "subscribe_entities")
    expected = {"sensor.wall", "sensor.other", "ai_task.configured"}
    assert set(snapshot(wire)) == expected
    assert entity_list(connection, wire) == expected
    compact = command(connection, wire, "config/entity_registry/list_for_display")
    assert {row["ei"] for row in compact["entities"]} == expected
    assert panel_runtime.adapter.filtered_count == 0


async def test_navigation_and_exceptions_reconcile_existing_feeds_and_registry_collections(
    panel_runtime, make_user, make_connection
):
    runtime = panel_runtime
    user = make_user(admin=True)
    dashboard, wire = make_connection(user)
    settings, settings_wire = make_connection(user)
    # Context arriving after bootstrap must repair an existing full collection.
    command(dashboard, wire, "subscribe_entities")
    command(dashboard, wire, "subscribe_events", event_type=er.EVENT_ENTITY_REGISTRY_UPDATED)
    command(settings, settings_wire, PANEL_SUBSCRIBE, dashboard="config")
    command(settings, settings_wire, "subscribe_entities")
    before = len(settings_wire)
    command(dashboard, wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
    assert set(snapshot(wire)) == {"sensor.wall"}
    assert entity_list(dashboard, wire) == {"sensor.wall"}
    assert len(settings_wire) == before
    assert "ai_task.configured" in snapshot(settings_wire)

    original = dict(runtime.entry.options)
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={**original, "extra_entities": ["ai_task.configured"]})
    await runtime.async_scan()
    assert set(snapshot(wire)) == {"sensor.wall", "ai_task.configured"}
    assert entity_list(dashboard, wire) == {"sensor.wall", "ai_task.configured"}
    runtime.hass.config_entries.async_update_entry(runtime.entry, options=original)
    await runtime.async_scan()
    assert set(snapshot(wire)) == {"sensor.wall"}
    assert entity_list(dashboard, wire) == {"sensor.wall"}

    start = len(wire)
    command(dashboard, wire, PANEL_COMMAND, dashboard="config")
    assert set(snapshot(wire)) == {"sensor.wall", "sensor.other", "ai_task.configured"}
    assert entity_list(dashboard, wire) == set(snapshot(wire))
    assert any(row.get("event", {}).get("event_type") == er.EVENT_ENTITY_REGISTRY_UPDATED for row in wire[start:])
    command(dashboard, wire, PANEL_COMMAND, dashboard="wall-panel")
    assert set(snapshot(wire)) == {"sensor.wall"}
    assert entity_list(dashboard, wire) == {"sensor.wall"}
    assert len(settings_wire) == before
    assert runtime.adapter.filtered_count == 1

    runtime.hass.states.async_set("ai_task.configured", "2")
    await runtime.hass.async_block_till_done()
    assert any("ai_task.configured" in row.get("event", {}).get("c", {}) for row in settings_wire[before:])
    assert not any("ai_task.configured" in row.get("event", {}).get("c", {}) for row in wire)


async def test_unreadable_dashboard_is_served_in_full_while_others_stay_filtered(
    loona_hass, make_entry, dashboards, make_user, make_connection
):
    registry = er.async_get(loona_hass)
    for name in ("wall", "other", "overview"):
        entry = registry.async_get_or_create("sensor", "test", name, suggested_object_id=name)
        loona_hass.states.async_set(entry.entity_id, "1")
    # An unknown card's template output could be an entity reference, so Overview is unreadable.
    await dashboards["lovelace"].async_save({"views": [{"title": "Home", "cards": [
        {"type": "entity", "entity": "sensor.overview"},
        {"type": "custom:example", "text": "{{ states(states('sensor.other')) }}"},
    ]}]})
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel", "lovelace"], "target_mode": "all"}))
    runtime.entry.runtime_data = runtime
    await runtime.async_start()
    await runtime.async_set_control("registry_filtering", True)
    everything = {"sensor.wall", "sensor.other", "sensor.overview"}
    try:
        assert not runtime.problems and runtime.unfiltered_dashboards == ("lovelace",)
        assert runtime.entity_ids == {"sensor.wall"}
        assert runtime.filtered_dashboards() == ("wall-panel",)
        notices = {item["code"]: item for item in runtime.notice_report()}
        assert "scan_incomplete" not in notices
        assert notices["unfiltered_dashboards"]["items"] == ["Overview / Home / custom:example"]
        tab, wire = make_connection(make_user(admin=True))
        command(tab, wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
        command(tab, wire, "subscribe_entities")
        assert set(snapshot(wire)) == {"sensor.wall"}
        assert entity_list(tab, wire) == {"sensor.wall"}
        # The same tab widens on the unreadable dashboard, exactly like an unselected page.
        command(tab, wire, PANEL_COMMAND, dashboard="lovelace")
        assert set(snapshot(wire)) == everything
        assert entity_list(tab, wire) == everything
        command(tab, wire, PANEL_COMMAND, dashboard="wall-panel")
        assert set(snapshot(wire)) == {"sensor.wall"}
        # With nothing readable, filtering stops everywhere as before.
        await dashboards["wall-panel"].async_save({"strategy": {"type": "unknown"}})
        await runtime.async_scan()
        assert runtime.problems and runtime.unfiltered_dashboards == ()
        assert set(snapshot(wire)) == everything
        assert "scan_incomplete" in {item["code"] for item in runtime.notice_report()}
    finally:
        await runtime.async_stop()


async def test_native_permissions_and_explicit_scopes_survive_panel_changes(panel_runtime, make_user, make_connection):
    connection, wire = make_connection(make_user(allowed={"sensor.wall"}))
    command(connection, wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
    command(connection, wire, "subscribe_entities")
    command(connection, wire, "subscribe_entities", entity_ids=["ai_task.configured"])
    assert snapshot(wire) == {}
    start = len(wire)
    command(connection, wire, PANEL_COMMAND, dashboard="config")
    assert set(snapshot(wire)) == {"sensor.wall"}
    assert panel_runtime.adapter.managed_count == 1
    assert all("ai_task.configured" not in row.get("event", {}).get("a", {}) for row in wire[start:])


async def test_dashboard_selection_unsubscribe_close_and_unload(panel_runtime, make_user, make_connection):
    runtime = panel_runtime
    connection, wire = make_connection(make_user(admin=True))
    command(connection, wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
    command(connection, wire, "subscribe_entities")
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={"dashboards": ["lovelace"]})
    await runtime.async_scan()
    assert "ai_task.configured" in snapshot(wire)
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={})
    await runtime.async_scan()
    assert set(snapshot(wire)) == {"sensor.wall"}
    command(connection, wire, "unsubscribe_events", subscription=1)
    assert "ai_task.configured" in snapshot(wire)
    assert connection not in runtime.panel_context._connections
    command(connection, wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
    connection.async_handle_close()
    assert not runtime.panel_context._connections
    assert runtime.adapter.managed_count == 0
    other, other_wire = make_connection(make_user(admin=True))
    command(other, other_wire, PANEL_SUBSCRIBE, dashboard="wall-panel")
    command(other, other_wire, "subscribe_entities")
    await runtime.async_stop()
    assert "ai_task.configured" in snapshot(other_wire)
    assert any(row.get("event") == {"enabled": False} for row in other_wire)
    command(other, other_wire, "unsubscribe_events", subscription=1)
    assert not runtime.panel_context._connections
    assert PANEL_SUBSCRIBE not in runtime.hass.data["websocket_api"]


def test_frontend_context_uses_native_connection_and_navigation():
    result = subprocess.run(["node", str(Path(__file__).with_name("panel_context.mjs"))], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
