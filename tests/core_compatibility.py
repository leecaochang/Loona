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
from homeassistant.auth.models import Group, RefreshToken, User  # noqa: E402
from homeassistant.auth.permissions.models import PermissionLookup  # noqa: E402
from homeassistant.components import lovelace, websocket_api  # noqa: E402
from homeassistant.components.lovelace import const as lovelace_const  # noqa: E402
from homeassistant.components.lovelace.dashboard import LovelaceStorage, LovelaceYAML  # noqa: E402
from homeassistant.components.lovelace import resources as native_resources  # noqa: E402
from homeassistant.components.lovelace.websocket import websocket_lovelace_resources  # noqa: E402
from homeassistant.components.websocket_api import commands, messages  # noqa: E402
from homeassistant.components.websocket_api.connection import ActiveConnection  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.storage import Store  # noqa: E402
from homeassistant.helpers import entity as entity_helper, restore_state, template, translation  # noqa: E402
from homeassistant.helpers import (  # noqa: E402
    area_registry as ar, device_registry as dr, entity_registry as er,
    floor_registry as fr, issue_registry as ir, label_registry as lr,
)

from custom_components.loona.config_flow import LoonaConfigFlow  # noqa: E402
from custom_components.loona.const import DOMAIN  # noqa: E402
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
    hass.config.components.update({"config", "websocket_api", "lovelace", "frontend", "http"})
    from homeassistant.components import frontend
    from homeassistant.components.http import HomeAssistantHTTP
    from homeassistant.components.http.cors import setup_cors
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    setup_cors(hass.http.app, [])
    hass.http.app.router.register_resource(frontend.IndexView(None, hass))
    manager_args = ([],)
    if frontend.UrlManager.__init__.__code__.co_argcount > 2:
        manager_args = (lambda *args: None, [])
    hass.data[frontend.DATA_EXTRA_MODULE_URL] = frontend.UrlManager(*manager_args)

    assert await lovelace.async_setup(hass, {"lovelace": {"mode": "storage"}})

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
        previous = hass.data.get(key, {})
        hass.data[key] = data_class(mode, boards, collection, {}) if data_class else {
            "dashboards": boards, "resources": collection,
            "dashboards_collection": previous.get("dashboards_collection"),
        }

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
    assert resource_originals, "No native resource list capability"
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
    assert result["step_id"] == "cards"
    result = await flow.async_step_cards({"dashboard_cards": ["statistics", "settings"]})
    assert result["step_id"] == "finish"
    result = await flow.async_step_finish({})
    assert result["type"] == "create_entry"
    kwargs = dict(domain=DOMAIN, data=result["data"], options={}, version=1, minor_version=1,
                  title="Loona", source="user", unique_id=DOMAIN)
    parameters = config_entries.ConfigEntry.__init__.__code__.co_varnames
    if "discovery_keys" in parameters:
        kwargs["discovery_keys"] = MappingProxyType({})
    if "subentries_data" in parameters:
        kwargs["subentries_data"] = ()
    entry = config_entries.ConfigEntry(**kwargs)
    hass.config_entries._entries[entry.entry_id] = entry
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
            packets.append(json.loads(payload if isinstance(payload, (bytes, str)) else messages.message_to_json_bytes(payload)))

        kwargs = dict(logger=logging.getLogger("loona.compat"), hass=hass, send_message=send,
                      user=user, refresh_token=token)
        if "remote" in ActiveConnection.__init__.__code__.co_varnames:
            kwargs["remote"] = None
        connection = ActiveConnection(**kwargs)
        clients.append(connection)
        if "loona/subscribe_panel" in hass.data[websocket_api.DOMAIN]:
            connection.async_handle({"id": 1, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
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
        if getattr(websocket_lovelace_resources, "_ws_schema", None) is False:
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
        assert packet["success"] and packet["result"] == [yaml_collection.async_items()[index] for index in (0, 2, 3)]
        assert table[name][1] is yaml_native[name][1]
    yaml_adapter.uninstall()
    assert not errors and all(table[name] is handler for name, handler in yaml_native.items())
    table.update(resource_originals)
    set_collection(collection, "storage")

    # Core may reconnect before Loona, on both four- and five-argument listeners.
    early, early_output = client(admin)
    early.async_handle({"id": 1, "type": "subscribe_entities"})
    early.async_handle({"id": 2, "type": "subscribe_entities", "entity_ids": []})
    explicit_early = early.subscriptions[2]

    runtime = None
    try:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        assert not runtime.compatibility_problem, runtime.compatibility_problem
        early.async_handle({"id": 3, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
        assert any(row.get("event", {}).get("resubscribe") for row in early_output)
        assert early.subscriptions[2] is explicit_early
        early.async_handle_close()
        clients.remove(early)
        index = next(resource for resource in hass.http.app.router.resources() if type(resource) is frontend.IndexView)
        html = index.get_template().render(theme_color="#123456", extra_modules=list(hass.data[frontend.DATA_EXTRA_MODULE_URL].urls), extra_js_es5=[])
        assert html.index('Object.defineProperty(window, "hassConnection"') < html.index('import("/frontend_latest/core.')
        assert '"routing": null' not in html
        assert runtime.statistics_card.enabled
        assert not any(domain == DOMAIN for domain, _ in ir.async_get(hass).issues)
        from custom_components.loona.statistics_card import StatisticsCard
        # Exercise each optional installation against the real native collection.
        await runtime.statistics_card.set_enabled(False)
        for cards in ((), ("settings",), ("statistics",), ("statistics", "settings")):
            await runtime.statistics_card.set_enabled(True, cards)
            boards_now = hass.data[key].dashboards if data_class else hass.data[key]["dashboards"]
            if cards:
                generated_cards = (await boards_now["loona-statistics"].async_load(False))["views"][0]["cards"]
                assert [row["type"] for row in generated_cards] == [f"custom:loona-{name}-card" for name in cards]
                assert boards_now["loona-statistics"].config["icon"] == "mdi:weather-night"
            else:
                assert "loona-statistics" not in boards_now
            # Reloaded ownership must remove one-card dashboards too.
            await StatisticsCard(hass, entry.entry_id).set_enabled(False)
            runtime.statistics_card.unload()
        await runtime.statistics_card.set_enabled(True)
        # Native deletion opts out across object recreation and entry reloads.
        board_map = hass.data[key].dashboards if data_class else hass.data[key]["dashboards"]
        await runtime.statistics_card.collection().async_delete_item(board_map["loona-statistics"].config["id"])
        await runtime.async_update_statistics_card()
        assert entry.options["dashboard_cards"] == []
        assert "loona-statistics" not in board_map
        await StatisticsCard(hass, entry.entry_id).set_enabled(True, ())
        assert "loona-statistics" not in board_map
        hass.config_entries.async_update_entry(entry, options={**entry.options, "dashboard_cards": ["statistics", "settings"]})
        await hass.async_block_till_done()
        statistics_board = hass.data[key].dashboards["loona-statistics"] if data_class else hass.data[key]["dashboards"]["loona-statistics"]
        statistics_id = statistics_board.config["id"]
        generated = await statistics_board.async_load(False)
        assert [row["type"] for row in generated["views"][0]["cards"]] == ["custom:loona-statistics-card", "custom:loona-settings-card"]
        await statistics_board.async_save({"views": [{"title": "Statistics", "path": "statistics", "cards": [{"type": "custom:loona-statistics-card"}]}]})
        await runtime.statistics_card.set_enabled(True)
        assert (await statistics_board.async_load(False))["views"][0]["title"] == "Statistics"
        edited_statistics = {"views": [{"title": "User edit", "cards": []}]}
        await statistics_board.async_save(edited_statistics)
        await runtime.statistics_card.set_enabled(True)
        assert await statistics_board.async_load(False) == edited_statistics
        await statistics_board.async_save(generated)
        assert not runtime.scope_problem, runtime.problems
        assert not runtime.resource_compatibility_problem, runtime.resource_compatibility_problem
        resource_client, resource_output = client(admin)
        await runtime.async_set_control("resource_filtering", True)
        for name in resource_originals:
            assert (await resource_request(resource_client, resource_output, name))["result"] == [rows[2], rows[3]]
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
            assert (await resource_request(reader, reader_output, name))["result"] == [rows[0], rows[1], rows[2], rows[3]]
        installed = await collection.async_create_item({"url": "/local/new.js", "res_type": "module"})
        assert installed in (await resource_request(reader, reader_output, next(iter(resource_originals))))["result"]
        await runtime.async_set_control("resource_filtering", False)
        assert (await resource_request(reader, reader_output, next(iter(resource_originals))))["result"] == collection.async_items()
        await wall.async_save({"cards": [{"entity": "sensor.wall"}, {"entity": "sensor.denied"}]})
        await runtime.async_scan()
        expected = {"enabled", "entity_filtering", "registry_filtering", "resource_filtering",
                    "visible_first_graphs", "pause_animations_during_loading"}
        assert runtime.available_controls == expected
        rows = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        controls = {row.unique_id.rsplit(":", 1)[-1]: row.entity_id for row in rows if row.domain == "switch"}
        assert set(controls) == {"enabled", "entity_filtering", "registry_filtering", "resource_filtering", "visible_first_graphs", "pause_animations_during_loading"}
        assert all(hass.states.get(controls[key]).state == "unavailable" for key in set(controls) - expected)
        assert len(rows) == 26
        assert all(hass.states.get(row.entity_id) is not None for row in rows)
        assert not ({row.entity_id for row in rows} & runtime.entity_ids)
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
        connection.async_handle({"id": 2, "type": "subscribe_entities"})
        assert "sensor.wall" in snapshot(output)
        assert "sensor.other" not in snapshot(output)
        lookup = PermissionLookup(er.async_get(hass), dr.async_get(hass))
        limited = User(name="Limited", perm_lookup=lookup, is_active=True, groups=[Group(
            name="Limited", policy={"entities": {"entity_ids": {"sensor.wall": {"read": True}}}}, id="limited",
        )])
        restricted, limited_output = client(limited)
        restricted.async_handle({"id": 2, "type": "subscribe_entities"})
        assert set(snapshot(limited_output)) == {"sensor.wall"}
        explicit, explicit_output = client(admin)
        explicit.async_handle({"id": 2, "type": "subscribe_entities", "entity_ids": ["sensor.other"]})
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

        connection.async_handle({"id": 3, "type": "loona/statistics"})
        assert "dependencies" not in output[-1]["result"]
        restricted.async_handle({"id": 3, "type": "loona/statistics"})
        assert limited_output[-1]["success"] is False
        connection.async_handle({"id": 4, "type": "loona/settings"})
        await hass.async_block_till_done()
        card_settings = next(row["result"] for row in output if row.get("id") == 4)
        assert set(card_settings["values"]["controls"]) == expected
        extras = card_settings["values"]["rules"]
        connection.async_handle({"id": 5, "type": "loona/save_settings", "group": "rules",
                                 "revision": card_settings["revision"], "values": {**extras, "extra_entities": ["sensor.other"]}})
        await hass.async_block_till_done()
        saved = next(row for row in output if row.get("id") == 5)
        assert saved["success"] and runtime.settings["extra_entities"] == ["sensor.other"]
        connection.async_handle({"id": 6, "type": "loona/save_settings", "group": "rules",
                                 "revision": saved["result"]["revision"], "values": extras})
        await hass.async_block_till_done()
        assert next(row for row in output if row.get("id") == 6)["success"]
        restricted.async_handle({"id": 4, "type": "loona/settings"})
        restricted.async_handle({"id": 5, "type": "loona/save_settings", "group": "rules",
                                 "revision": card_settings["revision"], "values": extras})
        assert all(not row["success"] for row in limited_output if row.get("id") in {4, 5} and row.get("type") == "result")
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
        assert "sensor.*" in fields["exclude_globs"].config["options"]
        assert fields["extra_entities"].selector_type == "entity"
        rejected = await options.async_configure(rules["flow_id"], {"include_globs": ["sensor.invented"]})
        assert rejected["errors"] == {"base": "invalid_selection"}
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
        unselected.async_handle({"id": 2, "type": "subscribe_entities"})
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
        assert not {"loona/statistics", "loona/page_load", "loona/settings", "loona/save_settings"} & table.keys()
        hass.config.language = "zh-Hans"
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        translated_rows = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        assert {row.entity_id for row in translated_rows} == {row.entity_id for row in rows}
        for row in translated_rows:
            if row.translation_key == "discovered_entities":
                assert row.original_name == "仪表盘引用的实体数"
            elif row.translation_key == "unresolved_entities":
                assert row.original_name == "未找到的实体数"
        assert not runtime.controls["enabled"] and runtime.controls["entity_filtering"]
        assert runtime.available_controls == expected
        board_map = hass.data[key].dashboards if data_class else hass.data[key]["dashboards"]
        assert board_map["loona-statistics"].config["id"] == statistics_id
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert hass.data[websocket_api.DOMAIN]["subscribe_entities"] is native
        assert await hass.config_entries.async_remove(entry.entry_id)
        assert await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.controls").async_load() is None
        assert await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.statistics_dashboard").async_load() is None
        assert "loona-statistics" not in board_map
        assert not set(runtime.statistics_card.module_urls) & hass.data[frontend.DATA_EXTRA_MODULE_URL].urls
        # A fresh native entry starts with defaults, including after a prior opt-out.
        from custom_components.loona.const import CONTROL_DEFAULTS
        fresh = config_entries.ConfigEntry(**kwargs)
        hass.config_entries._entries[fresh.entry_id] = fresh
        assert await hass.config_entries.async_setup(fresh.entry_id)
        await hass.async_block_till_done()
        fresh_runtime = fresh.runtime_data
        assert fresh_runtime.controls == CONTROL_DEFAULTS
        assert not fresh_runtime.statistics_card.opted_out
        assert "loona-statistics" in board_map
        edited = {"views": [{"cards": [{"type": "markdown", "content": "Personal dashboard"}]}]}
        await board_map["loona-statistics"].async_save(edited)
        assert await hass.config_entries.async_remove(fresh.entry_id)
        assert await board_map["loona-statistics"].async_load(False) == edited
        assert await fresh_runtime.statistics_card.store.async_load() is None
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
        hass.config.skip_pip = True
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
    assert errors.count("Error handling message: Unauthorized (unauthorized) Resource reader") == 1, errors
    assert errors.count("Error handling message: Unauthorized (unauthorized) Limited") == 3, errors
    assert not [error for error in errors if error not in expected_denials], errors


if __name__ == "__main__":
    asyncio.run(main())
