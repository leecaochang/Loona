"""Exercise native dashboard loading, policy changes, and runtime cleanup."""

import asyncio
from unittest.mock import patch

import pytest

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from custom_components.loona.const import DOMAIN
from custom_components.loona.diagnostics import async_get_config_entry_diagnostics
from custom_components.loona.runtime import LoonaRuntime


def settings(**overrides):
    return {"dashboards": ["wall-panel"], "target_mode": "all", **overrides}


@pytest.fixture
async def runtime(loona_hass, make_entry, dashboards):
    loona_hass.states.async_set("sensor.wall", "1")
    loona_hass.states.async_set("sensor.other", "2")
    entry = make_entry(settings())
    value = LoonaRuntime(loona_hass, entry)
    entry.runtime_data = value
    await value.async_start()
    yield value
    await value.async_stop()


async def test_native_scan_and_switch_updates_existing_admin(
    runtime, make_user, make_connection
):
    assert runtime.entity_ids == {"sensor.wall"}
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall"}
    await runtime.async_set_control("enabled", False)
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall", "sensor.other"}
    assert runtime.adapter.managed_count == 1
    assert runtime.adapter.filtered_count == 0
    await runtime.async_set_control("enabled", True)
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall"}
    assert runtime.adapter.filtered_count == 1


async def test_dashboard_save_group_change_and_state_lifecycle_automatically_rescan(
    runtime, dashboards, loona_hass
):
    with patch("custom_components.loona.runtime.SCAN_DEBOUNCE", 0):
        await dashboards["wall-panel"].async_save({"cards": [{"entity": "group.room"}]})
        loona_hass.states.async_set("group.room", "on", {"entity_id": ["light.first"]})
        await loona_hass.async_block_till_done()
        await asyncio.sleep(0.02)
        await loona_hass.async_block_till_done()
        assert runtime.entity_ids == {"group.room", "light.first"}
        loona_hass.states.async_set(
            "group.room", "off", {"entity_id": ["light.second"]}
        )
        await loona_hass.async_block_till_done()
        await asyncio.sleep(0.02)
        await loona_hass.async_block_till_done()
        assert runtime.entity_ids == {"group.room", "light.second"}
        await dashboards["wall-panel"].async_save(
            {
                "cards": [
                    {
                        "type": "custom:auto-entities",
                        "filter": {"include": [{"entity_id": "sensor.new_*"}]},
                    }
                ]
            }
        )
        loona_hass.states.async_set("sensor.new_one", "5")
        await loona_hass.async_block_till_done()
        await asyncio.sleep(0.02)
        await loona_hass.async_block_till_done()
        assert "sensor.new_one" in runtime.entity_ids


async def test_metrics_do_not_invalidate_on_value_changes(runtime, loona_hass):
    before = runtime._revision
    loona_hass.states.async_set("sensor.wall", "3")
    await loona_hass.async_block_till_done()
    assert runtime._revision == before
    metrics = runtime.metrics()
    assert metrics["union_entities"] == 1
    assert metrics["current_scope"] == 1
    assert metrics["reduction_estimate"] == 50
    assert metrics["last_scan"] is not None


@pytest.mark.parametrize(
    "config",
    [
        {"strategy": {"type": "custom:example"}},
        {"cards": []},
        {"cards": [{"name": "{{ states(states('sensor.wall')) }}"}]},
    ],
)
async def test_empty_or_dynamic_scopes_bypass_entire_union(
    runtime, dashboards, make_user, make_connection, config
):
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    last_success = runtime.last_scan
    await dashboards["wall-panel"].async_save(config)
    await runtime.async_scan()
    assert runtime.scope_problem
    assert runtime.last_scan == last_success
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall", "sensor.other"}
    assert ir.async_get(runtime.hass).async_get_issue(
        DOMAIN, f"{runtime.entry.entry_id}_scope"
    )
    await dashboards["wall-panel"].async_save({"cards": [{"entity": "sensor.wall"}]})
    await runtime.async_scan()
    assert not runtime.scope_problem
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall"}


async def test_deleted_dashboard_and_deleted_account_bypass(runtime, loona_hass):
    loona_hass.data[LOVELACE_DATA].dashboards.pop("wall-panel")
    await runtime.async_scan()
    assert runtime.scope_problem and not runtime.adapter.policy.complete
    assert "wall-panel" in runtime.dashboards
    loona_hass.config_entries.async_update_entry(
        runtime.entry, options={"target_mode": "selected", "user_ids": ["deleted"]}
    )
    await runtime.async_scan()
    assert any("active accounts" in problem for problem in runtime.problems)


async def test_fixed_templates_filter_both_categories_and_dynamic_lookups_bypass(
    runtime, dashboards, make_user, make_connection
):
    registry = er.async_get(runtime.hass)
    registered = [
        registry.async_get_or_create(
            "sensor", "test", name, suggested_object_id=name
        ).entity_id
        for name in ("registered_wall", "template_only", "registered_other")
    ]
    wall, template_only, other = registered
    for identifier in registered:
        runtime.hass.states.async_set(identifier, "12")
    await runtime.async_set_control("registry_filtering", True)
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    fixed = {
        "cards": [
            {
                "type": "custom:mushroom-template-card",
                "primary": "{{ states('" + wall + "') }}",
                "secondary": "{{ states('" + template_only + "') }}",
            }
        ]
    }
    await dashboards["wall-panel"].async_save(fixed)
    await runtime.async_scan()
    assert not runtime.scope_problem
    assert set(wire[-1]["event"]["a"]) == {wall, template_only}
    connection.async_handle({"id": 2, "type": "config/entity_registry/list"})
    assert {row["entity_id"] for row in wire[-1]["result"]} == {wall, template_only}
    await dashboards["wall-panel"].async_save(
        {
            "cards": [
                {"type": "markdown", "content": "{{ states(states('" + wall + "')) }}"}
            ]
        }
    )
    await runtime.async_scan()
    assert runtime.scope_problem
    assert other in wire[-1]["event"]["a"]
    connection.async_handle({"id": 3, "type": "config/entity_registry/list"})
    assert {row["entity_id"] for row in wire[-1]["result"]} == set(registered)
    await dashboards["wall-panel"].async_save(fixed)
    await runtime.async_scan()
    assert not runtime.scope_problem
    assert other in wire[-2]["event"]["r"]
    connection.async_handle({"id": 4, "type": "config/entity_registry/list"})
    assert {row["entity_id"] for row in wire[-1]["result"]} == {wall, template_only}


async def test_entity_mapping_updates_existing_state_and_registry_collections(
    runtime, dashboards, make_user, make_connection
):
    registry = er.async_get(runtime.hass)
    power, other = [
        registry.async_get_or_create(
            "sensor", "test", name, suggested_object_id=name
        ).entity_id
        for name in ("mapped_power", "mapped_other")
    ]
    runtime.hass.states.async_set(power, "1234")
    runtime.hass.states.async_set(other, "5678")
    await runtime.async_set_control("registry_filtering", True)
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    assert power not in wire[-1]["event"]["a"]
    await dashboards["wall-panel"].async_save(
        {
            "cards": [
                {"entity": "sensor.wall"},
                {
                    "type": "custom:sunsynk-power-flow-card",
                    "entities": {"inverter_power_175": power},
                },
            ]
        }
    )
    await runtime.async_scan()
    assert not runtime.scope_problem
    assert wire[-1]["event"]["a"][power]["s"] == "1234"
    assert other not in wire[-1]["event"]["a"]
    connection.async_handle({"id": 2, "type": "config/entity_registry/list"})
    assert {row["entity_id"] for row in wire[-1]["result"]} == {power}
    runtime.hass.states.async_set(power, "4321")
    await runtime.hass.async_block_till_done()
    assert wire[-1]["event"]["c"][power]["+"]["s"] == "4321"


async def test_rules_protect_controls_and_keep_missing_reference(
    runtime, dashboards, loona_hass
):
    control = er.async_get(loona_hass).async_get_or_create(
        "switch", DOMAIN, "control", config_entry=runtime.entry
    )
    loona_hass.states.async_set(control.entity_id, "on")
    await dashboards["wall-panel"].async_save(
        {"cards": [{"entity": "sensor.future"}, {"entity": "sensor.wall"}]}
    )
    loona_hass.config_entries.async_update_entry(
        runtime.entry,
        options={
            "exclude_globs": ["switch.*", "sensor.wall"],
            "extra_entities": ["light.extra"],
            "include_domains": ["sensor"],
        },
    )
    await runtime.async_scan()
    assert runtime.entity_ids == {
        control.entity_id,
        "sensor.future",
        "sensor.other",
        "light.extra",
    }
    assert runtime.unresolved["wall-panel"] == {"sensor.future"}
    assert any("exclusion removes" in warning for warning in runtime.warnings)


async def test_scan_never_publishes_outdated_candidate(runtime, loona_hass, dashboards):
    entered, release = asyncio.Event(), asyncio.Event()
    original = dashboards["wall-panel"].async_load
    loads = 0

    async def slow(force):
        nonlocal loads
        loads += 1
        if loads == 1:
            entered.set()
            await release.wait()
            return {"cards": [{"entity": "sensor.stale"}]}
        return await original(force)

    with patch.object(dashboards["wall-panel"], "async_load", slow):
        job = asyncio.create_task(runtime.async_scan())
        await entered.wait()
        await dashboards["wall-panel"].async_save({"cards": [{"entity": "sensor.new"}]})
        await asyncio.sleep(0)
        runtime.request_scan()
        assert runtime.entity_ids == {"sensor.wall"}
        release.set()
        await job
    assert "sensor.stale" not in runtime.entity_ids
    assert runtime.entity_ids == {"sensor.new"}


async def test_controls_persist_and_unload_restores_native(
    runtime, make_user, make_connection
):
    original = runtime.adapter._original
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    await runtime.async_set_control("entity_filtering", False)
    await runtime.async_stop()
    assert runtime.hass.data["websocket_api"]["subscribe_entities"] is original
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall", "sensor.other"}
    new = LoonaRuntime(runtime.hass, runtime.entry)
    await new.async_start()
    assert not new.controls["entity_filtering"]
    assert not new._policy().enabled
    await new.async_stop()
    assert not new._unsubscribers and not new._listeners


async def test_registry_control_defaults_persistence_and_independent_policy(runtime):
    assert runtime.registry_adapter is not None
    assert not runtime.controls["registry_filtering"]
    assert not runtime.registry_adapter.policy.enabled
    await runtime.async_set_control("registry_filtering", True)
    await runtime.async_set_control("entity_filtering", False)
    assert runtime.registry_adapter.policy.enabled
    assert not runtime.adapter.policy.enabled
    await runtime.async_stop()
    new = LoonaRuntime(runtime.hass, runtime.entry)
    await new.async_start()
    try:
        assert new.controls["registry_filtering"]
        assert new.registry_adapter.policy.enabled
        assert not new.adapter.policy.enabled
    finally:
        await new.async_stop()


async def test_unsupported_version_leaves_native_hook_and_reports_problem(
    loona_hass, make_entry, dashboards
):
    native = loona_hass.data["websocket_api"]["subscribe_entities"]
    runtime = LoonaRuntime(loona_hass, make_entry(settings()))
    with patch("homeassistant.const.__version__", "2025.1.0"):
        await runtime.async_start()
    assert runtime.compatibility_problem and runtime.adapter is None
    assert loona_hass.data["websocket_api"]["subscribe_entities"] is native
    await runtime.async_stop()


async def test_diagnostics_redact_identifiers_and_patterns(runtime, loona_hass):
    loona_hass.config_entries.async_update_entry(
        runtime.entry,
        options={"user_ids": ["private-user"], "include_globs": ["sensor.private_*"]},
    )
    data = await async_get_config_entry_diagnostics(loona_hass, runtime.entry)
    encoded = str(data)
    assert all(
        value not in encoded
        for value in ("private-user", "sensor.private_*", "sensor.wall", "wall-panel")
    )
    assert data["metrics"]["union_entities"] == 1


async def test_dashboard_devices_are_actual_children(runtime, loona_hass):
    child = dr.async_get(loona_hass).async_get(runtime.dashboard_devices["wall-panel"])
    assert child.parent_device_id == runtime.device_id


async def test_later_command_owner_preserved_and_known_connections_bypass(
    runtime, make_user, make_connection
):
    connection, wire = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "subscribe_entities"})
    table = runtime.hass.data["websocket_api"]
    foreign = (lambda *args: None, table["subscribe_entities"][1])
    table["subscribe_entities"] = foreign
    await runtime.async_set_control("enabled", False)
    assert table["subscribe_entities"] is foreign
    assert runtime.compatibility_problem and runtime.adapter is None
    assert set(wire[-1]["event"]["a"]) == {"sensor.wall", "sensor.other"}


async def test_stop_cancels_inflight_dashboard_load(runtime, dashboards):
    entered = asyncio.Event()

    async def stalled(force):
        entered.set()
        await asyncio.Event().wait()

    with patch.object(dashboards["wall-panel"], "async_load", stalled):
        task = asyncio.create_task(runtime.async_scan())
        await entered.wait()
        await runtime.async_stop()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert runtime._scan_task.done()
    assert not runtime._unsubscribers
