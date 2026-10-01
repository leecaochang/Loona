"""Verify real native platforms, device hierarchy, and options lifecycle."""

import asyncio

from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.loona import async_setup_entry, async_unload_entry
from custom_components.loona.config_flow import LoonaOptionsFlow
from custom_components.loona.const import DOMAIN


async def test_native_platforms_and_dashboard_selection_cleanup(
    loona_hass, make_entry, dashboards, frontend_http
):
    loona_hass.states.async_set("sensor.wall", "1")
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    async with entry.setup_lock:
        assert await async_setup_entry(loona_hass, entry)
    await loona_hass.async_block_till_done()
    runtime = entry.runtime_data
    assert runtime.controls["visible_first_graphs"] is False
    assert runtime.controls["pause_animations_during_loading"] is False
    entities = er.async_entries_for_config_entry(
        er.async_get(loona_hass), entry.entry_id
    )
    assert len(entities) == 24
    assert {entity.domain for entity in entities} == {
        "sensor",
        "switch",
        "binary_sensor",
        "button",
    }
    assert {entity.entity_id for entity in entities} <= runtime.entity_ids
    assert (
        len(
            dr.async_child_entries_for_config_entry(
                dr.async_get(loona_hass), entry.entry_id
            )
        )
        == 1
    )
    master = next(
        entity for entity in entities if entity.unique_id.endswith(":enabled")
    )
    await loona_hass.services.async_call(
        "switch", "turn_off", {"entity_id": master.entity_id}, blocking=True
    )
    assert not runtime.controls["enabled"]
    flow = LoonaOptionsFlow()
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = await flow.async_step_filters(
        {"entity_filtering": False, "registry_filtering": True, "visible_first_graphs": True, "pause_animations_during_loading": True}
    )
    assert result["data"] == {}
    assert not runtime.controls["entity_filtering"]
    assert runtime.controls["registry_filtering"]
    assert runtime.controls["visible_first_graphs"]
    assert runtime.controls["pause_animations_during_loading"]
    assert runtime.registry_adapter is not None, runtime.registry_compatibility_problem
    assert runtime.registry_adapter.policy.enabled is False
    adapter = runtime.adapter
    old_device = runtime.dashboard_devices["wall-panel"]
    loona_hass.config_entries.async_update_entry(
        entry, options={"dashboards": ["lovelace"]}
    )
    await loona_hass.async_block_till_done()
    assert runtime.adapter is adapter
    assert runtime.selected_dashboards == ("lovelace",)
    assert dr.async_get(loona_hass).async_get(old_device) is None
    entities = er.async_entries_for_config_entry(
        er.async_get(loona_hass), entry.entry_id
    )
    assert len(entities) == 24
    assert not any(
        ":dashboard:wall-panel" in identifier
        for device in dr.async_child_entries_for_config_entry(
            dr.async_get(loona_hass), entry.entry_id
        )
        for _, identifier in device.identifiers
    )
    assert await async_unload_entry(loona_hass, entry)
    assert DOMAIN not in loona_hass.data
    await entry._async_process_on_unload(loona_hass)
    assert not runtime._listeners
    await asyncio.sleep(0)


async def test_missing_optional_frontend_api_keeps_entity_filtering_operational(
    loona_hass, make_entry, dashboards, frontend_http, make_user, make_connection
):
    from unittest.mock import patch

    # These dependencies are represented by the native fixtures above.
    loona_hass.config.components.update({"lovelace", "frontend"})
    loona_hass.states.async_set("sensor.wall", "1")
    loona_hass.states.async_set("sensor.other", "2")
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    with patch.object(frontend_http, "async_register_static_paths", None):
        async with entry.setup_lock:
            assert await async_setup_entry(loona_hass, entry)
    await loona_hass.async_block_till_done()
    runtime = entry.runtime_data
    try:
        assert runtime.available_controls == {"enabled", "entity_filtering", "registry_filtering", "resource_filtering"}
        assert runtime.graph_adapter is None and runtime.graph_compatibility_problem
        assert runtime.adapter is not None
        assert not runtime.scope_problem, runtime.problems
        connection, wire = make_connection(make_user(admin=True))
        connection.async_handle({"id": 1, "type": "subscribe_entities"})
        assert "sensor.wall" in wire[-1]["event"]["a"]
        assert "sensor.other" not in wire[-1]["event"]["a"]
        entities = er.async_entries_for_config_entry(er.async_get(loona_hass), entry.entry_id)
        assert not any(entity.unique_id.endswith((":visible_first_graphs", ":pause_animations_during_loading")) for entity in entities)
    finally:
        assert await async_unload_entry(loona_hass, entry)
        await entry._async_process_on_unload(loona_hass)
