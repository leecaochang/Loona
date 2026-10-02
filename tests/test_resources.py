"""Verify dependency previews and filtering through genuine native collections."""

import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest

from homeassistant.components import websocket_api
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceYAMLCollection
from homeassistant.helpers import issue_registry as ir

from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.config_flow import LoonaOptionsFlow
from custom_components.loona.diagnostics import async_get_config_entry_diagnostics
from custom_components.loona.resources import (
    ResourceAdapter, resource_dependencies, resource_report,
)
from custom_components.loona.runtime import LoonaRuntime
from custom_components.loona.websocket import ScopePolicy


async def request(hass, connection, output, name="lovelace/resources/list", **fields):
    msg_id = connection.last_id + 1
    connection.async_handle({"id": msg_id, "type": name, **fields})
    await hass.async_block_till_done()
    return next(packet for packet in reversed(output) if packet.get("id") == msg_id)


def test_nested_types_shared_styles_dynamic_and_unclassified_preview():
    dependencies = resource_dependencies([{
        "button_card_templates": {"inner": {"type": "custom:button-card"}},
        "views": [{"type": "custom:layout-card", "layout_type": "custom:grid-layout",
                   "cards": [{"type": "conditional", "card": {"type": "custom:mini-graph-card"}},
                             {"type": "custom:unknown", "value": "[[[ return 1; ]]]"}]}],
    }])
    rows = [{"id": str(index), "url": url, "type": kind} for index, (url, kind) in enumerate([
        ("/hacsfiles/button-card/button-card.js?v=1", "module"),
        ("/local/mini-graph-card-bundle.js", "module"),
        ("/hacsfiles/lovelace-layout-card/layout-card.js", "module"),
        ("/local/apexcharts-card.js", "module"),
        ("/local/card-mod.js", "module"),
        ("/local/site.css", "css"),
        ("/local/helper.js", "module"),
        ("https://example.invalid/button-card.js", "module"),
    ])]
    report = resource_report(rows, dependencies, ["/local/deleted.js"])
    assert [item["status"] for item in report["resources"]] == [
        "required", "required", "required", "unused", "required", "required", "unclassified", "unclassified",
    ]
    assert report["unresolved_custom_types"] == ["unknown"]
    assert report["dynamic_configuration"]
    assert report["stale_exceptions"] == ["/local/deleted.js"]
    assert all("status" not in row for row in rows)
    optional = resource_report(rows, dependencies, ["/local/helper.js"])["resources"][6]
    assert optional["status"] == "unclassified" and optional["forwarded"]


def test_configured_helpers_popups_features_and_exact_bundle_tags():
    configs = [{"kiosk_mode": {"hide_header": True}, "views": [{"cards": [
        {"type": "conditional", "conditions": [], "card": {"type": "custom:battery-state-card"}},
        {"type": "tile", "features": [{"type": "custom:service-call", "entries": []}]},
        {"type": "button", "tap_action": {"browser_mod": {"service": "browser_mod.popup", "data": {
            "content": {"type": "custom:nodalia-camera-card"}}}}},
    ]}]}]
    urls = ["/local/battery-state-card.js?v=2", "/local/custom-card-features.min.js",
            "/hacsfiles/nodalia-cards/nodalia-cards.js", "/local/kiosk-mode.js",
            "/browser_mod.js?automatically-added&2", "/local/calendar-card-pro.js"]
    rows = [{"url": url, "type": "module"} for url in urls]
    initial = resource_report(rows, resource_dependencies(configs))
    assert [row["forwarded"] for row in initial["resources"]] == [True] * 5 + [False]
    assert not initial["unresolved_custom_types"]
    # Removing dashboard dependencies releases card bundles and kiosk becomes
    # uncertain because browser-local settings can still require its runtime.
    changed = resource_report(rows, resource_dependencies([{}]))
    assert [row["status"] for row in changed["resources"]] == [
        "unused", "unused", "unused", "unclassified", "required", "unused",
    ]
    unknown = resource_report(rows, resource_dependencies([{"type": "custom:nodalia-new-card"}]))
    assert unknown["unresolved_custom_types"] == ["nodalia-new-card"]
    assert not unknown["resources"][2]["forwarded"]
    nested = resource_report(rows, resource_dependencies([{"card": {"kiosk_mode": {}}}]))
    assert nested["resources"][3]["status"] == "unclassified"


def test_helper_mapping_does_not_trust_remote_names_or_wrong_resource_kinds():
    rows = [{"url": url, "type": kind} for url, kind in [
        ("https://example.invalid/browser_mod.js", "module"),
        ("//example.invalid/browser_mod.js", "module"),
        ("/local/browser_mod.js", "module"),
        ("/browser_mod.js", "html"),
        ("/local/card-mod.js", "html"),
        ("/local/kiosk-mode.js", "html"),
    ]]
    report = resource_report(rows, resource_dependencies([{"kiosk_mode": {}}]))
    assert all(row["status"] == "unclassified" and not row["forwarded"] for row in report["resources"])


def test_bundled_cards_do_not_need_lovelace_resource_registrations():
    dependencies = resource_dependencies([{"cards": [
        {"type": "custom:loona-statistics-card"},
        {"type": "custom:loona-settings-card"},
        {"type": "custom:loona-unknown-card"},
        {"type": "custom:unknown-card"},
    ]}])
    report = resource_report([], dependencies)
    assert report["unresolved_custom_types"] == ["loona-unknown-card", "unknown-card"]
    assert not report["resources"]


@pytest.fixture
async def resources_runtime(loona_hass, dashboards, make_entry):
    await dashboards["wall-panel"].async_save({"cards": [{"type": "custom:mini-graph-card", "entity": "sensor.wall"}]})
    collection = loona_hass.data[LOVELACE_DATA].resources
    for url, kind in [("/local/mini-graph-card-bundle.js?v=1", "module"),
                      ("/local/button-card.js", "module"),
                      ("/local/shared.css", "css"), ("/local/helper.js", "module")]:
        await collection.async_create_item({"url": url, "res_type": kind})
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    runtime = LoonaRuntime(loona_hass, entry)
    entry.runtime_data = runtime
    await runtime.async_start()
    yield runtime, collection
    await runtime.async_stop()


async def test_native_storage_aliases_live_changes_master_and_unload(
    resources_runtime, make_user, make_connection,
):
    runtime, collection = resources_runtime
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    full = (await request(runtime.hass, connection, output))["result"]
    assert full == collection.async_items()
    await runtime.async_set_control("resource_filtering", True)
    for name in ("lovelace/resources", "lovelace/resources/list"):
        reduced = (await request(runtime.hass, connection, output, name))["result"]
        assert reduced == [row for row in full if row["type"] == "css" or "mini-graph" in row["url"]]
    # A freshly installed module is evaluated without a manual rescan.
    new = await collection.async_create_item({"url": "/local/unknown-new.js", "res_type": "module"})
    assert new not in (await request(runtime.hass, connection, output))["result"]
    # Native editing commands still see and update original registrations.
    result = await request(runtime.hass, connection, output, "lovelace/resources/update",
                           resource_id=new["id"], url="/local/apexcharts-card.js")
    assert result["success"], result
    await runtime.async_set_control("enabled", False)
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()
    await runtime.async_set_control("enabled", True)
    adapter = runtime.resource_adapter
    originals = dict(adapter._originals)
    await runtime.async_stop()
    for name, native in originals.items():
        assert runtime.hass.data[websocket_api.DOMAIN][name] is native
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()


async def test_account_targets_native_permissions_and_incomplete_bypass(
    resources_runtime, make_user, make_connection,
):
    runtime, collection = resources_runtime
    selected = make_user(admin=False)
    runtime.resource_adapter.set_policy(ScopePolicy(user_ids=frozenset({selected.id})))
    connection, output = make_connection(selected)
    connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    assert len((await request(runtime.hass, connection, output))["result"]) == 2
    denied = await request(runtime.hass, connection, output, "lovelace/resources/create",
                           url="/local/denied.js", res_type="module")
    assert not denied["success"] and denied["error"]["code"] == "unauthorized"
    unselected, other_output = make_connection(make_user(admin=True))
    assert (await request(runtime.hass, unselected, other_output))["result"] == collection.async_items()
    runtime.resource_adapter.set_policy(replace(runtime.resource_adapter.policy, complete=False))
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()


async def test_empty_resource_scope_and_native_yaml_collection(
    loona_hass, dashboards, make_user, make_connection,
):
    rows = [{"url": "/local/button-card.js", "type": "module"}]
    loona_hass.data[LOVELACE_DATA].resources = ResourceYAMLCollection(rows)
    errors = []
    adapter = ResourceAdapter(loona_hass, ScopePolicy(all_users=True),
                              lambda items: resource_report(items, resource_dependencies([{}])), errors.append)
    adapter.install()
    try:
        connection, output = make_connection(make_user())
        assert (await request(loona_hass, connection, output))["result"] == []
        assert rows == loona_hass.data[LOVELACE_DATA].resources.async_items()
        assert not errors
    finally:
        adapter.uninstall()


async def test_preview_exceptions_dashboard_edits_and_redaction(resources_runtime):
    runtime, collection = resources_runtime
    flow = LoonaOptionsFlow(runtime.entry.entry_id)
    flow.hass, flow.handler = runtime.hass, runtime.entry.entry_id
    form = await flow.async_step_resource_preview()
    assert "/local/mini-graph-card-bundle.js?v=1" in form["description_placeholders"]["required"]
    assert "/local/button-card.js" not in form["description_placeholders"]["required"]
    assert not runtime.controls["resource_filtering"]
    form = await flow.async_step_resource_exceptions()
    assert form["data_schema"]({}) == {"resource_filtering": False, "always_forward_resources": []}
    result = await flow.async_step_resource_exceptions({"always_forward_resources": ["/local/helper.js"]})
    runtime.hass.config_entries.async_update_entry(runtime.entry, options=result["data"])
    await runtime.async_scan()
    assert (await runtime.async_resource_preview())["resources"][-1]["forwarded"]
    board = runtime.hass.data[LOVELACE_DATA].dashboards["wall-panel"]
    await board.async_save({"cards": [{"type": "custom:button-card", "entity": "sensor.wall"}]})
    await runtime.async_scan()
    statuses = {row["url"]: row["status"] for row in runtime.resource_preview["resources"]}
    assert statuses["/local/button-card.js"] == "required"
    assert statuses["/local/mini-graph-card-bundle.js?v=1"] == "unused"
    diagnostics = await async_get_config_entry_diagnostics(runtime.hass, runtime.entry)
    assert "/local/helper.js" not in str(diagnostics)


async def test_native_optional_checkboxes_required_rows_and_master(
    resources_runtime, make_user, make_connection,
):
    runtime, collection = resources_runtime
    flow = LoonaOptionsFlow(runtime.entry.entry_id)
    flow.hass, flow.handler = runtime.hass, runtime.entry.entry_id
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    form = await flow.async_step_resource_preview()
    schema = {str(key.schema): value for key, value in form["data_schema"].schema.items()}
    picker = schema["always_forward_resources"]
    assert picker.config["mode"] == "list" and picker.config["multiple"]
    assert {choice["value"] for choice in picker.config["options"]} == {
        "/local/button-card.js", "/local/helper.js",
    }
    assert form["data_schema"]({})["always_forward_resources"] == []
    assert "/local/shared.css" in form["description_placeholders"]["required"]
    result = await flow.async_step_resource_preview({
        "resource_filtering": True, "always_forward_resources": ["/local/helper.js"],
    })
    runtime.hass.config_entries.async_update_entry(runtime.entry, options=result["data"])
    await runtime.async_scan()
    assert runtime.controls["resource_filtering"]
    assert len((await request(runtime.hass, connection, output))["result"]) == 3
    form = await flow.async_step_resource_preview()
    assert form["data_schema"]({})["always_forward_resources"] == ["/local/helper.js"]
    assert runtime.resource_preview["resources"][-1]["status"] == "unclassified"
    # Optional resources remain editable after being enabled.
    result = await flow.async_step_resource_preview({"always_forward_resources": []})
    runtime.hass.config_entries.async_update_entry(runtime.entry, options=result["data"])
    await runtime.async_scan()
    reduced = (await request(runtime.hass, connection, output))["result"]
    assert {row["url"] for row in reduced} == {
        "/local/mini-graph-card-bundle.js?v=1", "/local/shared.css",
    }
    await flow.async_step_resource_preview({"resource_filtering": False})
    assert not runtime.controls["resource_filtering"]
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()


async def test_required_transitions_preserve_explicit_choices_and_new_optional_defaults(resources_runtime):
    runtime, collection = resources_runtime
    flow = LoonaOptionsFlow(runtime.entry.entry_id)
    flow.hass, flow.handler = runtime.hass, runtime.entry.entry_id
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={
        "always_forward_resources": ["/local/button-card.js"],
    })
    board = runtime.hass.data[LOVELACE_DATA].dashboards["wall-panel"]
    await board.async_save({"cards": [{"type": "custom:button-card", "entity": "sensor.wall"}]})
    await runtime.async_scan()
    form = await flow.async_step_resource_preview()
    assert form["data_schema"]({})["always_forward_resources"] == []
    # A required module is never a checkbox, even with a saved optional choice.
    picker = next(value for value in form["data_schema"].schema.values() if getattr(value, "selector_type", None) == "select")
    assert "/local/button-card.js" not in {item["value"] for item in picker.config["options"]}
    result = await flow.async_step_resource_preview({"always_forward_resources": []})
    assert result["data"]["always_forward_resources"] == ["/local/button-card.js"]
    await board.async_save({"cards": [{"type": "entity", "entity": "sensor.wall"}]})
    await runtime.async_scan()
    new = await collection.async_create_item({"url": "/local/new-optional.js", "res_type": "module"})
    form = await flow.async_step_resource_preview()
    selected = form["data_schema"]({})["always_forward_resources"]
    assert selected == ["/local/button-card.js"]
    assert new["url"] not in selected
    # Clearing optional choices cannot turn off shared required styling.
    result = await flow.async_step_resource_preview({"always_forward_resources": []})
    runtime.hass.config_entries.async_update_entry(runtime.entry, options=result["data"])
    await runtime.async_scan()
    assert [row["url"] for row in runtime.resource_preview["resources"] if row["forwarded"]] == ["/local/shared.css"]


async def test_preview_is_read_only_when_resource_adapter_unavailable(resources_runtime):
    runtime, _ = resources_runtime
    runtime.resource_adapter.uninstall()
    runtime.resource_adapter = None
    flow = LoonaOptionsFlow(runtime.entry.entry_id)
    flow.hass, flow.handler = runtime.hass, runtime.entry.entry_id
    form = await flow.async_step_resource_preview()
    assert not form["data_schema"].schema
    assert form["description_placeholders"]["stale_count"] == "0"
    invalid = await flow.async_step_resource_preview({"resource_filtering": True})
    assert invalid["errors"] == {"base": "invalid_selection"}


async def test_delayed_native_result_rechecks_policy_and_survives_unload(
    resources_runtime, make_user, make_connection,
):
    runtime, collection = resources_runtime
    await runtime.async_set_control("resource_filtering", True)
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    gate = asyncio.Event()
    entered = asyncio.Event()
    original_load = collection.async_load

    async def slow_native_load():
        entered.set()
        await gate.wait()
        await original_load()

    for mode in ("switch", "panel", "unload"):
        collection.loaded = False
        gate.clear()
        entered.clear()
        with patch.object(collection, "async_load", side_effect=slow_native_load):
            msg_id = connection.last_id + 1
            connection.async_handle({"id": msg_id, "type": "lovelace/resources/list"})
            await entered.wait()
            # Other native traffic is unaffected while the list handler awaits.
            connection.async_handle({"id": msg_id + 1, "type": "subscribe_entities"})
            assert any(packet.get("id") == msg_id + 1 for packet in output)
            if mode == "unload":
                runtime.resource_adapter.uninstall()
            elif mode == "panel":
                connection.async_handle({"id": msg_id + 2, "type": "loona/panel", "dashboard": "config"})
            else:
                await runtime.async_set_control("resource_filtering", False)
            gate.set()
            await runtime.hass.async_block_till_done()
        assert next(packet for packet in output if packet.get("id") == msg_id)["result"] == collection.async_items()
        assert runtime.resource_compatibility_problem is None
        if mode == "switch":
            await runtime.async_set_control("resource_filtering", True)
        elif mode == "panel":
            connection.async_handle({"id": connection.last_id + 1, "type": "loona/panel", "dashboard": "wall-panel"})


async def test_resource_lists_bypass_unknown_and_non_dashboard_panels(resources_runtime, make_user, make_connection):
    runtime, collection = resources_runtime
    await runtime.async_set_control("resource_filtering", True)
    connection, output = make_connection(make_user(admin=True))
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()
    await request(runtime.hass, connection, output, "loona/subscribe_panel", dashboard="config")
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()
    await request(runtime.hass, connection, output, "loona/panel", dashboard="wall-panel")
    assert len((await request(runtime.hass, connection, output))["result"]) == 2
    await request(runtime.hass, connection, output, "loona/panel", dashboard="developer-tools")
    assert (await request(runtime.hass, connection, output))["result"] == collection.async_items()


async def test_resource_repair_stale_exception_and_collection_failure_isolation(resources_runtime):
    runtime, collection = resources_runtime
    issue_key = ("loona", f"{runtime.entry.entry_id}_resources")
    issues = ir.async_get(runtime.hass)
    assert issue_key not in issues.issues
    await runtime.async_set_control("resource_filtering", True)
    assert issue_key in issues.issues  # Unclassified helper is disclosed.
    await runtime.async_set_control("resource_filtering", False)
    assert issue_key not in issues.issues
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={
        "always_forward_resources": ["/local/helper.js"],
    })
    await collection.async_delete_item(collection.async_items()[-1]["id"])
    await runtime.async_scan()
    assert runtime.resource_preview["stale_exceptions"] == ["/local/helper.js"]
    with patch.object(collection, "async_items", return_value=None):
        await runtime.async_scan()
    assert runtime.adapter is not None and runtime.registry_adapter is not None
    assert runtime.resource_adapter is None and runtime.resource_compatibility_problem


async def test_schema_conflict_is_atomic(resources_runtime):
    runtime, _ = resources_runtime
    runtime.resource_adapter.uninstall()
    table = runtime.hass.data[websocket_api.DOMAIN]
    first = table["lovelace/resources"]
    other = table["lovelace/resources/list"]
    table["lovelace/resources/list"] = (lambda *args: None, other[1])
    try:
        with pytest.raises(CompatibilityError):
            runtime.resource_adapter.install()
        assert table["lovelace/resources"] is first
    finally:
        table["lovelace/resources/list"] = other


async def test_changed_response_fails_open_and_unknown_owner_is_preserved(resources_runtime, make_user, make_connection):
    runtime, collection = resources_runtime
    await runtime.async_set_control("resource_filtering", True)
    connection, output = make_connection(make_user())
    connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    # Apply a shape mutation at the native boundary; no fake list handler.
    with patch.object(collection, "async_items", return_value=[{"url": "/local/bad.js"}]):
        assert (await request(runtime.hass, connection, output))["result"] == [{"url": "/local/bad.js"}]
    assert runtime.resource_adapter is None
    assert runtime.resource_compatibility_problem
    errors = []
    adapter = ResourceAdapter(runtime.hass, ScopePolicy(all_users=True), runtime.resource_report, errors.append)
    adapter.install()
    name = "lovelace/resources/list"
    foreign = (lambda *args: None, adapter._originals[name][1])
    runtime.hass.data[websocket_api.DOMAIN][name] = foreign
    with pytest.raises(CompatibilityError):
        adapter.check_ownership()
    adapter.uninstall()
    assert runtime.hass.data[websocket_api.DOMAIN][name] is foreign
