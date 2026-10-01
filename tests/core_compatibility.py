"""Run full native backend acceptance against an installed supported Core.

Run from the repository with that Core's Python: python tests/core_compatibility.py.
No handlers, schemas, permissions, or version admission are replaced by this test.
"""

from __future__ import annotations

import asyncio
import ctypes
from datetime import timedelta
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import patch

import orjson

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant import auth, config_entries, const as ha_const, loader  # noqa: E402
import voluptuous as vol  # noqa: E402
from homeassistant.auth.models import Group, RefreshToken, User  # noqa: E402
from homeassistant.auth.permissions.models import PermissionLookup  # noqa: E402
from homeassistant.components import lovelace, websocket_api  # noqa: E402
from homeassistant.components.lovelace import const as lovelace_const  # noqa: E402
from homeassistant.components.lovelace.dashboard import LovelaceStorage, LovelaceYAML  # noqa: E402
from homeassistant.components.lovelace import resources as native_resources  # noqa: E402
from homeassistant.components.lovelace.websocket import websocket_lovelace_resources  # noqa: E402
from homeassistant.components.websocket_api import commands  # noqa: E402
from homeassistant.components.websocket_api.connection import ActiveConnection  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.storage import Store  # noqa: E402
from homeassistant.helpers import entity as entity_helper, restore_state, template, translation  # noqa: E402
from homeassistant.helpers import (  # noqa: E402
    area_registry as ar, device_registry as dr, entity_registry as er,
    floor_registry as fr, issue_registry as ir, label_registry as lr,
)

from custom_components.loona.config_flow import LoonaConfigFlow  # noqa: E402
from custom_components.loona.const import DOMAIN, FRONTEND_CORE_VERSIONS, REGISTRY_CORE_VERSIONS, RESOURCE_COMMAND_PROFILES, RESOURCE_CORE_VERSIONS  # noqa: E402
from custom_components.loona.dashboard import discovery_context, load_dashboard  # noqa: E402
from custom_components.loona.diagnostics import async_get_config_entry_diagnostics  # noqa: E402
from custom_components.loona.resources import ResourceAdapter, resource_dependencies, resource_report  # noqa: E402
from custom_components.loona.websocket import ScopePolicy  # noqa: E402


async def check(hass: HomeAssistant) -> None:
    """Use real Core loading, platforms, storage, auth and websocket dispatch."""
    for module in (dr, er, fr, lr, ar, ir):
        setup = getattr(module, "async_setup", None)
        if setup is not None:
            setup(hass)
        await module.async_load(hass)
    hass.auth = await auth.auth_manager_from_config(hass, [], [])
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    Path(hass.config.path("custom_components")).symlink_to(
        Path(__file__).resolve().parents[1] / "custom_components", target_is_directory=True
    )
    loader.async_setup(hass)
    translation.async_setup(hass)
    entity_helper.async_setup(hass)
    template.async_setup(hass)
    await restore_state.async_load(hass)
    commands.async_register_commands(hass, websocket_api.async_register_command)
    from homeassistant.components.config import (
        area_registry, device_registry, entity_registry, floor_registry, label_registry,
    )
    for module in (area_registry, device_registry, entity_registry, floor_registry, label_registry):
        module.async_setup(hass)
    hass.config.components.update({"config", "websocket_api", "lovelace", "frontend"})
    if ha_const.__version__ in FRONTEND_CORE_VERSIONS:
        from homeassistant.components import frontend
        from homeassistant.components.http import HomeAssistantHTTP
        from homeassistant.components.http.cors import setup_cors
        hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
        setup_cors(hass.http.app, [])
        hass.data[frontend.DATA_EXTRA_MODULE_URL] = frontend.UrlManager(lambda *args: None, [])

    default = LovelaceStorage(hass, None)
    wall = LovelaceStorage(hass, {"id": "wall", "url_path": "wall-panel", "title": "Wall"})
    await default.async_save({"cards": [{"entity": "sensor.other"}]})
    await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"}]})
    Path(hass.config.path("wall.yaml")).write_text("cards:\n  - entity: sensor.yaml\n")
    yaml_board = LovelaceYAML(hass, "yaml-panel", {"title": "YAML", "filename": "wall.yaml"})
    boards = {None: default, "wall-panel": wall, "yaml-panel": yaml_board}
    key = getattr(lovelace_const, "LOVELACE_DATA", "lovelace")
    data_class = getattr(lovelace, "LovelaceData", None)
    def set_collection(collection, mode):
        hass.data[key] = data_class(mode, boards, collection, {}) if data_class else {"dashboards": boards, "resources": collection}

    # Native 2024.5 setup deliberately disables the generic collection list.
    # Later Core releases expose the resource-specific collection list and alias.
    collection = native_resources.ResourceStorageCollection(hass, default)
    await collection.async_load()
    collection.loaded = True
    set_collection(collection, "storage")
    storage_ws = getattr(native_resources, "ResourceStorageCollectionWebsocket", None)
    if storage_ws is None:
        from homeassistant.helpers.collection import DictStorageCollectionWebsocket
        DictStorageCollectionWebsocket(collection, "lovelace/resources", "resource",
            lovelace_const.RESOURCE_CREATE_FIELDS, lovelace_const.RESOURCE_UPDATE_FIELDS).async_setup(hass, create_list=False)
        websocket_api.async_register_command(hass, websocket_lovelace_resources)
    else:
        storage_ws(collection, "lovelace/resources", "resource",
            lovelace_const.RESOURCE_CREATE_FIELDS, lovelace_const.RESOURCE_UPDATE_FIELDS).async_setup(hass)
    resource_originals = {name: hass.data[websocket_api.DOMAIN][name]
                          for name in ("lovelace/resources", "lovelace/resources/list")
                          if name in hass.data[websocket_api.DOMAIN]}
    assert tuple(resource_originals) == RESOURCE_COMMAND_PROFILES[ha_const.__version__]
    rows = []
    for url, kind in [("/local/battery-state-card.js", "module"), ("/local/button-card.js", "module"),
                      ("/local/unknown.js", "module"), ("/local/style.css", "css")]:
        rows.append(await collection.async_create_item({"url": url, "res_type": kind}))
    assert (await load_dashboard(hass, "lovelace"))["cards"][0]["entity"] == "sensor.other"
    assert (await load_dashboard(hass, "yaml-panel", force=True))["cards"][0]["entity"] == "sensor.yaml"

    admin = await hass.auth.async_create_user("Administrator", group_ids=["system-admin"])
    flow = LoonaConfigFlow()
    flow.hass, flow.handler, flow.context = hass, DOMAIN, {"source": "user"}
    form = await flow.async_step_user()
    assert form["step_id"] == "user"
    form = await flow.async_step_user(form["data_schema"]({"dashboards": ["wall-panel"]}))
    assert form["step_id"] == "targets"
    result = await flow.async_step_targets(form["data_schema"]({"target_mode": "all"}))
    assert result["step_id"] == "statistics_card"
    result = await flow.async_step_statistics_card(result["data_schema"]({"statistics_card": False}))
    kwargs = dict(domain=DOMAIN, data=result["data"], options={}, version=1, minor_version=1,
                  title="Loona", source="user", unique_id=DOMAIN)
    parameters = config_entries.ConfigEntry.__init__.__code__.co_varnames
    if "discovery_keys" in parameters:
        kwargs["discovery_keys"] = MappingProxyType({})
    if "subentries_data" in parameters:
        kwargs["subentries_data"] = ()
    entry = config_entries.ConfigEntry(**kwargs)
    hass.config_entries._entries[entry.entry_id] = entry
    if ha_const.__version__ not in FRONTEND_CORE_VERSIONS:
        await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.controls").async_save({
            "visible_first_graphs": True, "pause_animations_during_loading": True,
            "registry_filtering": True,
        })

    for identifier in ("sensor.wall", "sensor.denied", "sensor.other", "sensor.yaml"):
        hass.states.async_set(identifier, "1")
    native = hass.data[websocket_api.DOMAIN]["subscribe_entities"]
    clients = []

    def client(user):
        packets = []
        token = RefreshToken(user=user, client_id=None, access_token_expiration=timedelta(minutes=1))

        def send(payload):
            packets.append(json.loads(payload) if isinstance(payload, (bytes, str)) else payload)

        kwargs = dict(logger=logging.getLogger("loona.compat"), hass=hass, send_message=send,
                      user=user, refresh_token=token)
        if "remote" in ActiveConnection.__init__.__code__.co_varnames:
            kwargs["remote"] = None
        connection = ActiveConnection(**kwargs)
        clients.append(connection)
        return connection, packets

    def snapshot(packets):
        return next(packet["event"]["a"] for packet in reversed(packets) if "a" in packet.get("event", {}))

    def removals(packets):
        return next(packet["event"]["r"] for packet in reversed(packets) if "r" in packet.get("event", {}))

    async def resource_request(connection, packets, name, **fields):
        msg_id = connection.last_id + 1
        connection.async_handle({"id": msg_id, "type": name, **fields})
        await hass.async_block_till_done()
        return next(packet for packet in reversed(packets) if packet.get("id") == msg_id)

    # Exercise genuine YAML handlers with the aliases registered by each Core.
    # Native YAML setup does not manufacture /list in 2024.5.
    table = hass.data[websocket_api.DOMAIN]
    yaml_collection = native_resources.ResourceYAMLCollection([{"url": row["url"], "type": row["type"]} for row in rows])
    set_collection(yaml_collection, "yaml")
    for name in resource_originals:
        if ha_const.__version__ == "2024.5.5":
            websocket_api.async_register_command(hass, websocket_lovelace_resources)
        else:
            websocket_api.async_register_command(hass, name, websocket_lovelace_resources,
                websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({"type": name}))
    errors = []
    yaml_adapter = ResourceAdapter(hass, ScopePolicy(all_users=True),
        lambda items: resource_report(items, resource_dependencies([{"card": {"type": "custom:battery-state-card"}}])), errors.append)
    yaml_native = {name: table[name] for name in resource_originals}
    yaml_adapter.install()
    yaml_client, yaml_output = client(admin)
    for name in resource_originals:
        packet = await resource_request(yaml_client, yaml_output, name)
        assert packet["success"] and packet["result"] == [yaml_collection.async_items()[0], yaml_collection.async_items()[3]]
        assert table[name][1] is yaml_native[name][1]
    yaml_adapter.uninstall()
    assert not errors and all(table[name] is handler for name, handler in yaml_native.items())
    table.update(resource_originals)
    set_collection(collection, "storage")

    runtime = None
    try:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        assert not runtime.compatibility_problem, runtime.compatibility_problem
        assert not runtime.scope_problem, runtime.problems
        assert not runtime.resource_compatibility_problem, runtime.resource_compatibility_problem
        resource_client, resource_output = client(admin)
        await runtime.async_set_control("resource_filtering", True)
        for name in resource_originals:
            assert (await resource_request(resource_client, resource_output, name))["result"] == [rows[3]]
            assert table[name][1] is resource_originals[name][1]
        non_admin = await hass.auth.async_create_user("Resource reader", group_ids=["system-users"])
        reader, reader_output = client(non_admin)
        denied = await resource_request(reader, reader_output, "lovelace/resources/create", url="/local/denied.js", res_type="module")
        assert not denied["success"] and denied["error"]["code"] == "unauthorized"
        with patch("custom_components.loona.runtime.SCAN_DEBOUNCE", 0):
            await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"},
                {"type": "conditional", "conditions": [], "card": {"type": "custom:battery-state-card", "entity": "sensor.wall"}},
                {"type": "button", "tap_action": {"action": "fire-dom-event", "browser_mod": {"service": "browser_mod.popup", "data": {"content": {"type": "custom:button-card", "entity": "sensor.wall"}}}}}]})
            await asyncio.sleep(0.02)
            await hass.async_block_till_done()
        for name in resource_originals:
            assert (await resource_request(reader, reader_output, name))["result"] == [rows[0], rows[1], rows[3]]
        installed = await collection.async_create_item({"url": "/local/new.js", "res_type": "module"})
        assert installed not in (await resource_request(reader, reader_output, next(iter(resource_originals))))["result"]
        await runtime.async_set_control("resource_filtering", False)
        assert (await resource_request(reader, reader_output, next(iter(resource_originals))))["result"] == collection.async_items()
        await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"}]})
        await runtime.async_scan()
        expected = {"enabled", "entity_filtering"}
        if ha_const.__version__ in RESOURCE_CORE_VERSIONS:
            expected.add("resource_filtering")
        if ha_const.__version__ in REGISTRY_CORE_VERSIONS:
            expected.add("registry_filtering")
        if ha_const.__version__ in FRONTEND_CORE_VERSIONS:
            expected.update({"visible_first_graphs", "pause_animations_during_loading"})
        else:
            assert runtime.controls["visible_first_graphs"]
            assert runtime.controls["pause_animations_during_loading"]
            try:
                await runtime.async_set_control("visible_first_graphs", True)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsupported control was accepted")
        assert runtime.available_controls == expected
        rows = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        controls = {row.unique_id.rsplit(":", 1)[-1]: row.entity_id for row in rows if row.domain == "switch"}
        assert set(controls) == expected
        assert len(rows) == 18 + len(expected)
        assert all(hass.states.get(row.entity_id) is not None for row in rows)
        assert {row.entity_id for row in rows} <= runtime.entity_ids
        child = dr.async_get(hass).async_get(runtime.dashboard_devices["wall-panel"])
        assert (child.parent_device_id if hasattr(child, "parent_device_id") else child.via_device_id) == runtime.device_id

        # Exercise genuine registry relationships used by entity discovery.
        floor = fr.async_get(hass).async_create("Floor")
        label = lr.async_get(hass).async_create("Label")
        area = ar.async_get(hass).async_create("Area")
        ar.async_get(hass).async_update(area.id, floor_id=floor.floor_id, labels={label.label_id})
        device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("test", "target")})
        dr.async_get(hass).async_update_device(device.id, area_id=area.id)
        entity = er.async_get(hass).async_get_or_create("sensor", "test", "target", device_id=device.id)
        context = discovery_context(hass)
        for category, identifier in (("area_id", area.id), ("floor_id", floor.floor_id), ("label_id", label.label_id)):
            assert entity.entity_id in context.targets[category][identifier]

        # Older and current native serializers must preserve their envelopes.
        registry_originals = dict(runtime.registry_adapter._originals)
        registry_client, registry_output = client(admin)

        async def registry_request(name):
            msg_id = registry_client.last_id + 1
            registry_client.async_handle({"id": msg_id, "type": name})
            await hass.async_block_till_done()
            packet = next(item for item in reversed(registry_output) if item.get("id") == msg_id)
            assert packet["success"], packet
            return packet["result"]

        await runtime.async_set_control("registry_filtering", False)
        baseline = {name: await registry_request(name) for name in registry_originals if name != "subscribe_events"}
        # Native legacy via-device closure is required on every admitted Core.
        parent = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("test", "parent")})
        dr.async_get(hass).async_update_device(device.id, via_device_id=parent.id)
        await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"}, {"entity": entity.entity_id}]})
        await runtime.async_scan()
        await runtime.async_set_control("registry_filtering", True)
        scope = runtime.registry_scope
        assert {parent.id, device.id} <= scope.devices
        assert area.id in scope.areas and floor.floor_id in scope.floors and label.label_id in scope.labels
        for name in baseline:
            # Fetch native baseline again after adding relationships.
            await runtime.async_set_control("registry_filtering", False)
            full = await registry_request(name)
            await runtime.async_set_control("registry_filtering", True)
            filtered = await registry_request(name)
            kind, identifier = {
                "config/entity_registry/list": ("entities", "entity_id"),
                "config/entity_registry/list_for_display": ("entities", "ei"),
                "config/device_registry/list": ("devices", "id"),
                "config/area_registry/list": ("areas", "area_id"),
                "config/floor_registry/list": ("floors", "floor_id"),
                "config/label_registry/list": ("labels", "label_id"),
            }[name]
            if name.endswith("list_for_display"):
                assert filtered == {**full, "entities": [row for row in full["entities"] if row[identifier] in scope.entities]}
            else:
                assert filtered == [row for row in full if row[identifier] in getattr(scope, kind)]
        subscription = registry_client.last_id + 1
        registry_client.async_handle({"id": subscription, "type": "subscribe_events", "event_type": er.EVENT_ENTITY_REGISTRY_UPDATED})
        before = len(registry_output)
        await runtime.async_set_control("registry_filtering", False)
        assert any(packet.get("id") == subscription and packet.get("type") == "event" for packet in registry_output[before:])
        await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"}]})
        await runtime.async_scan()

        connection, output = client(admin)
        connection.async_handle({"id": 1, "type": "subscribe_entities"})
        assert "sensor.wall" in snapshot(output)
        assert "sensor.other" not in snapshot(output)
        lookup = PermissionLookup(er.async_get(hass), dr.async_get(hass))
        limited = User(name="Limited", perm_lookup=lookup, is_active=True, groups=[Group(
            name="Limited", policy={"entities": {"entity_ids": {"sensor.wall": {"read": True}}}}, id="limited",
        )])
        restricted, limited_output = client(limited)
        restricted.async_handle({"id": 1, "type": "subscribe_entities"})
        assert set(snapshot(limited_output)) == {"sensor.wall"}
        explicit, explicit_output = client(admin)
        explicit.async_handle({"id": 1, "type": "subscribe_entities", "entity_ids": ["sensor.other"]})
        assert set(snapshot(explicit_output)) == {"sensor.other"}
        before = len(output)
        hass.states.async_set("sensor.other", "2")
        await hass.async_block_till_done()
        assert len(output) == before
        hass.states.async_set("sensor.wall", "2")
        hass.states.async_set("sensor.denied", "2")
        await hass.async_block_till_done()
        assert any("sensor.wall" in packet.get("event", {}).get("c", {}) for packet in output[before:])
        assert all("sensor.denied" not in packet.get("event", {}).get("c", {}) for packet in limited_output)

        connection.async_handle({"id": 2, "type": "loona/statistics", "search": "sensor.wall"})
        assert output[-1]["result"]["dependencies"][0]["entity_id"] == "sensor.wall"
        restricted.async_handle({"id": 2, "type": "loona/statistics"})
        assert limited_output[-1]["success"] is False
        assert runtime.live_statistics.forwarded > 0 and runtime.live_statistics.avoided > 0
        reset = next(row.entity_id for row in rows if row.unique_id.endswith(":reset_live_statistics"))
        await hass.services.async_call("button", "press", {"entity_id": reset}, blocking=True)
        await hass.async_block_till_done()
        assert set(runtime.live_statistics.metrics().values()) == {0}

        options = hass.config_entries.options
        form = await options.async_init(entry.entry_id)
        assert form["type"] == "menu"
        assert "resource_exceptions" not in form["menu_options"]
        rules = await options.async_init(entry.entry_id)
        rules = await options.async_configure(rules["flow_id"], {"next_step_id": "rules"})
        fields = {str(marker.schema): field for marker, field in rules["data_schema"].schema.items()}
        assert "sensor" in fields["include_domains"].config["options"]
        assert {"sensor.wall", "sensor.*"} <= set(fields["exclude_globs"].config["options"])
        assert all(not field.config["custom_value"] for field in fields.values())
        try:
            rules["data_schema"]({"include_globs": ["sensor.invented"]})
        except vol.Invalid:
            pass
        else:
            raise AssertionError("Entity rules accepted an unknown selection")
        await options.async_configure(rules["flow_id"], {
            "include_domains": ["sensor"], "include_globs": ["sensor.wall"], "exclude_globs": []})
        assert entry.options["include_domains"] == ["sensor"]
        rules = await options.async_init(entry.entry_id)
        rules = await options.async_configure(rules["flow_id"], {"next_step_id": "rules"})
        await options.async_configure(rules["flow_id"], {
            "include_domains": [], "include_globs": [], "exclude_globs": []})
        await hass.async_block_till_done()
        preview = await options.async_init(entry.entry_id)
        preview = await options.async_configure(preview["flow_id"], {"next_step_id": "resource_preview"})
        assert preview["type"] == "form"
        fields = {str(marker.schema) for marker in preview["data_schema"].schema}
        assert fields == {"resource_filtering", "always_forward_resources"}
        await options.async_configure(preview["flow_id"], {})
        form = await options.async_configure(form["flow_id"], {"next_step_id": "filters"})
        assert {str(marker.schema) for marker in form["data_schema"].schema} == expected - {"enabled"}
        await options.async_configure(form["flow_id"], {key: False for key in expected - {"enabled"}})
        await hass.async_block_till_done()
        assert "sensor.other" in snapshot(output)
        assert set(snapshot(limited_output)) == {"sensor.wall"}
        await hass.services.async_call("switch", "turn_on", {"entity_id": controls["entity_filtering"]}, blocking=True)
        assert "sensor.other" not in snapshot(output)
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["metrics"]["filtered_subscriptions"] == 2
        assert "sensor.wall" not in str(diagnostics)
        adapter = runtime.adapter
        target_form = await options.async_init(entry.entry_id)
        target_form = await options.async_configure(target_form["flow_id"], {"next_step_id": "targets"})
        await options.async_configure(target_form["flow_id"], {"target_mode": "selected", "user_ids": [admin.id]})
        await hass.async_block_till_done()
        assert runtime.adapter is adapter
        assert "sensor.other" not in snapshot(output)
        other_admin = await hass.auth.async_create_user("Other administrator", group_ids=["system-admin"])
        unselected, unselected_output = client(other_admin)
        unselected.async_handle({"id": 1, "type": "subscribe_entities"})
        assert "sensor.other" in snapshot(unselected_output)
        target_form = await options.async_init(entry.entry_id)
        target_form = await options.async_configure(target_form["flow_id"], {"next_step_id": "targets"})
        await options.async_configure(target_form["flow_id"], {"target_mode": "all"})
        await hass.async_block_till_done()
        assert "sensor.other" not in snapshot(unselected_output)
        with patch("custom_components.loona.runtime.SCAN_DEBOUNCE", 0):
            await wall.async_save({"cards": [{"entity": "sensor.other"}]})
            await asyncio.sleep(0.02)
            await hass.async_block_till_done()
        assert runtime.adapter is adapter
        assert "sensor.wall" in removals(output)
        assert "sensor.other" in snapshot(output)
        assert snapshot(limited_output) == {}
        old_device = runtime.dashboard_devices["wall-panel"]
        board_form = await options.async_init(entry.entry_id)
        board_form = await options.async_configure(board_form["flow_id"], {"next_step_id": "dashboards"})
        await options.async_configure(board_form["flow_id"], {"dashboards": ["yaml-panel"]})
        await hass.async_block_till_done()
        assert runtime.adapter is adapter and "sensor.yaml" in snapshot(output)
        assert dr.async_get(hass).async_get(old_device) is None
        board_form = await options.async_init(entry.entry_id)
        board_form = await options.async_configure(board_form["flow_id"], {"next_step_id": "dashboards"})
        await options.async_configure(board_form["flow_id"], {"dashboards": ["wall-panel"]})
        await hass.async_block_till_done()
        assert "sensor.other" in snapshot(output)
        await wall.async_save({"cards": []})
        await runtime.async_scan()
        assert runtime.scope_problem and "sensor.wall" in snapshot(output)
        await wall.async_save({"cards": [{"entity": "sensor.other"}]})
        await runtime.async_scan()
        await hass.services.async_call("switch", "turn_off", {"entity_id": controls["enabled"]}, blocking=True)
        assert "sensor.wall" in snapshot(output)
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert hass.data[websocket_api.DOMAIN]["subscribe_entities"] is native
        assert all(hass.data[websocket_api.DOMAIN][name] is handler for name, handler in registry_originals.items())
        assert all(table[name] is handler for name, handler in resource_originals.items())
        assert not runtime._unsubscribers and not runtime._listeners
        assert "loona/statistics" not in table and "loona/page_load" not in table
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        assert not runtime.controls["enabled"] and runtime.controls["entity_filtering"]
        assert runtime.available_controls == expected
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert hass.data[websocket_api.DOMAIN]["subscribe_entities"] is native
        print(f"Passed full native backend acceptance on Core {ha_const.__version__}: setup, storage/YAML, discovery, controls/options, permissions, live updates, bypass, persistence and unload")
    finally:
        if runtime:
            await runtime.async_stop()
        for connection in clients:
            connection.async_handle_close()


async def main() -> None:
    # Match the pinned Fragment heap-type lifetime workaround in conftest.py.
    if sys.implementation.name == "cpython" and orjson.__version__ == "3.11.9":
        incref = ctypes.pythonapi.Py_IncRef
        incref.argtypes = [ctypes.py_object]
        incref.restype = None
        incref(orjson.Fragment)
    errors = []

    class ErrorCapture(logging.Handler):
        def emit(self, record):
            errors.append(record.getMessage())

    capture = ErrorCapture(logging.ERROR)
    logging.getLogger().addHandler(capture)
    with tempfile.TemporaryDirectory(prefix="loona-core-acceptance-") as config:
        hass = HomeAssistant(config)
        try:
            await check(hass)
        finally:
            await hass.async_block_till_done()
            await hass.async_stop(force=True)
    logging.getLogger().removeHandler(capture)
    # These native permission-denial regressions each emit one expected error.
    expected_denials = {
        "Error handling message: Unauthorized (unauthorized) Resource reader",
        "Error handling message: Unauthorized (unauthorized) Limited",
    }
    assert all(errors.count(error) == 1 for error in expected_denials), errors
    assert not [error for error in errors if error not in expected_denials], errors


if __name__ == "__main__":
    asyncio.run(main())
