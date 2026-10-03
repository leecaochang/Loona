"""Exercise startup order, recovery, permissions, global resources and payload bounds."""

import json
from pathlib import Path
import re
import subprocess
import tomllib

import pytest
from homeassistant import const as ha_const
from homeassistant.components import websocket_api

from custom_components.loona.const import VERSION
from custom_components.loona.runtime import LoonaRuntime
from custom_components.loona.settings import settings_report, websocket_settings_choices


@pytest.fixture
async def audit_runtime(loona_hass, dashboards, make_entry):
    """Start real adapters against native dashboards and resource storage."""
    loona_hass.states.async_set("sensor.wall", "1")
    loona_hass.states.async_set("sensor.other", "2")
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all", "dashboard_cards": []})
    runtime = LoonaRuntime(loona_hass, entry)
    entry.runtime_data = runtime
    await runtime.async_start()
    yield runtime
    await runtime.async_stop()


@pytest.mark.parametrize("version", ["2024.5.5", "2024.6.0b1", "unknown"])
async def test_below_baseline_versions_explain_every_disabled_feature(loona_hass, dashboards, make_entry, monkeypatch, caplog, version):
    monkeypatch.setattr(ha_const, "__version__", version)
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    try:
        assert runtime.available_controls == {"enabled"}
        assert {item["code"] for item in runtime.notice_report()} >= {
            "entity_compatibility", "registry_compatibility", "resource_compatibility", "graph_compatibility",
        }
        before = len(caplog.records)
        runtime._update_issues()
        assert len(caplog.records) == before
    finally:
        await runtime.async_stop()


async def test_early_native_feed_requests_lossless_replay_and_preserves_explicit_scopes(loona_hass, dashboards, make_entry, make_user, make_connection):
    loona_hass.states.async_set("sensor.wall", "1")
    loona_hass.states.async_set("sensor.other", "2")
    client, output = make_connection(make_user(admin=True))
    client.async_handle({"id": 1, "type": "subscribe_entities"})
    client.async_handle({"id": 2, "type": "subscribe_entities", "entity_ids": ["sensor.other"]})
    explicit = client.subscriptions[2]
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    try:
        client.async_handle({"id": 3, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
        assert not any(row.get("success") is False for row in output)
        assert runtime.adapter.managed_count == 0
        assert any(row.get("event", {}).get("resubscribe") for row in output)
        assert client.subscriptions[2] is explicit
        # Replay the original requests as the stock client does on recovery.
        recovered, recovered_output = make_connection(make_user(admin=True))
        recovered.async_handle({"id": 1, "type": "subscribe_entities"})
        recovered.async_handle({"id": 2, "type": "subscribe_entities", "entity_ids": []})
        recovered.async_handle({"id": 3, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
        assert runtime.adapter.managed_count == runtime.adapter.filtered_count == 1
        assert not runtime.adapter.needs_resubscribe(recovered)
        assert not any(row.get("event", {}).get("resubscribe") for row in recovered_output)
        assert "sensor.other" in next(row["event"]["a"] for row in recovered_output if row.get("id") == 2 and "a" in row.get("event", {}))
        output.clear()
        loona_hass.states.async_set("sensor.other", "3")
        await loona_hass.async_block_till_done()
        assert not any(row["id"] == 1 for row in recovered_output if "c" in row.get("event", {}))
        assert any(row["id"] == 2 for row in output)
        assert any(row["id"] == 2 for row in recovered_output if "c" in row.get("event", {}))
    finally:
        await runtime.async_stop()


async def test_removals_never_disclose_unreadable_unregistered_ids(audit_runtime, make_user, make_connection):
    runtime = audit_runtime
    runtime.hass.states.async_set("sensor.secret_unregistered", "private")
    client, output = make_connection(make_user(allowed=["sensor.wall", "sensor.other"]))
    client.async_handle({"id": 1, "type": "subscribe_entities"})
    delivered = set(output[-1]["event"]["a"])
    client.async_handle({"id": 2, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    removed = {value for row in output for value in row.get("event", {}).get("r", [])}
    assert removed == {"sensor.other"} and removed <= delivered
    assert "sensor.secret_unregistered" not in json.dumps(output)


async def test_bootstrap_is_full_then_live_feed_narrows(audit_runtime, make_user, make_connection):
    runtime = audit_runtime
    client, output = make_connection(make_user(admin=True))
    client.async_handle({"id": 1, "type": "subscribe_entities"})
    assert set(output[-1]["event"]["a"]) == {"sensor.wall", "sensor.other"}
    client.async_handle({"id": 2, "type": "config/entity_registry/list_for_display"})
    client.async_handle({"id": 3, "type": "get_config"})
    client.async_handle({"id": 4, "type": "loona/subscribe_panel", "dashboard": "wall-panel"})
    snapshots = [set(row["event"]["a"]) for row in output if "a" in row.get("event", {})]
    assert snapshots == [{"sensor.wall", "sensor.other"}, {"sensor.wall"}]
    assert runtime.adapter.initial_counts(client) == {"available": 2, "sent": 2}


async def test_chrome_entities_survive_rules_without_forced_telemetry(audit_runtime):
    runtime = audit_runtime
    for entity_id in ("person.owner", "update.core", "zone.home"):
        runtime.hass.states.async_set(entity_id, "1")
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={"exclude_globs": ["person.*", "update.*", "zone.*"]})
    await runtime.async_scan()
    assert runtime.entity_ids == {"sensor.wall", "person.owner", "update.core", "zone.home"}


async def test_global_helpers_and_other_dashboard_cards_are_retained(audit_runtime, dashboards):
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    runtime = audit_runtime
    await dashboards["lovelace"].async_save({"cards": [{"type": "custom:button-card", "entity": "sensor.overview"}]})
    collection = runtime.hass.data[LOVELACE_DATA].resources
    urls = ["/local/button-card.js", "/local/mini-graph-card-bundle.js", "/local/hass-hue-icons.js", "/local/custom-sidebar-yaml.js", "/local/kiosk-mode.js"]
    for url in urls:
        await collection.async_create_item({"url": url, "res_type": "module"})
    await runtime.async_scan()
    report = runtime.resource_preview
    assert {row["url"] for row in report["resources"] if row["forwarded"]} == set(urls) - {"/local/mini-graph-card-bundle.js"}
    await dashboards["lovelace"].async_save({"strategy": {"type": "custom:generated"}})
    await runtime.async_scan()
    assert not runtime.resource_complete
    assert all(row["forwarded"] for row in runtime.resource_preview["resources"])


async def test_temporary_resource_load_failure_recovers(audit_runtime, monkeypatch):
    from custom_components.loona.compatibility import CompatibilityError
    from custom_components.loona import runtime as runtime_module
    runtime = audit_runtime
    original = runtime_module.async_resource_rows
    adapter = runtime.resource_adapter
    async def unavailable(hass):
        raise CompatibilityError("Temporary native collection error")
    monkeypatch.setattr(runtime_module, "async_resource_rows", unavailable)
    await runtime.async_set_control("resource_filtering", True)
    await runtime.async_scan()
    assert runtime.resource_adapter is adapter and not runtime.resource_complete
    assert any(item["code"] == "resource_scan" for item in runtime.notice_report())
    monkeypatch.setattr(runtime_module, "async_resource_rows", original)
    await runtime.async_scan()
    assert runtime.resource_complete and runtime.resource_adapter is adapter
    assert not any(item["code"] == "resource_scan" for item in runtime.notice_report())


async def test_upgrade_preserves_cards_without_adding_them(loona_hass, make_entry):
    from custom_components.loona import async_migrate_entry
    for data in ({}, {"dashboard_cards": ["settings"]}):
        entry = make_entry(data)
        assert await async_migrate_entry(loona_hass, entry)
        assert entry.version == 2
        assert entry.data["dashboard_cards"] == data.get("dashboard_cards", [])


async def test_settings_and_native_rules_stay_small_at_scale(audit_runtime, make_user, make_connection):
    from custom_components.loona.config_flow import LoonaOptionsFlow
    runtime = audit_runtime
    for index in range(10000):
        runtime.hass.states.async_set(f"sensor.scale_{index:05}", "1")
    report = await settings_report(runtime)
    assert len(json.dumps(report).encode()) < 40000
    assert len(report["choices"]["extra_entities"]) == 50
    assert report["paged_choices"]["extra_entities"]
    flow = LoonaOptionsFlow(runtime.entry.entry_id)
    flow.hass, flow.handler = runtime.hass, runtime.entry.entry_id
    form = await flow.async_step_rules()
    assert len(json.dumps({str(key.schema): str(value.config) for key, value in form["data_schema"].schema.items()})) < 2000
    runtime.hass.data["loona"] = runtime
    websocket_api.async_register_command(runtime.hass, websocket_settings_choices)
    admin, output = make_connection(make_user(admin=True))
    admin.async_handle({"id": 1, "type": "loona/settings_choices", "key": "extra_entities", "query": "scale_099", "offset": 50})
    await runtime.hass.async_block_till_done()
    page = output[-1]["result"]
    assert len(page["choices"]) == 50 and not page["more"]
    assert all("scale_099" in row["value"] for row in page["choices"])
    reader, output = make_connection(make_user())
    reader.async_handle({"id": 1, "type": "loona/settings_choices", "key": "extra_entities"})
    await runtime.hass.async_block_till_done()
    assert output[-1]["error"]["code"] == "unauthorized"
    runtime.hass.data.pop("loona")


def test_release_versions_and_manifest_are_consistent():
    root = Path(__file__).resolve().parents[1]
    package = root / "custom_components/loona"
    manifest = json.loads((package / "manifest.json").read_text())
    assert manifest["version"] == VERSION == tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    assert list(manifest) == ["domain", "name"] + sorted(set(manifest) - {"domain", "name"})
    assert "http" in manifest["dependencies"]
    for path in (package / "frontend").glob("*.js"):
        for version in re.findall(r'(?:v=|moduleVersion = ")(\d+\.\d+\.\d+)', path.read_text()):
            assert version == VERSION, path


def test_real_client_restart_retry_and_cards():
    root = Path(__file__).parent
    for filename in ("panel_restart.mjs", "cards.mjs"):
        result = subprocess.run(["node", str(root / filename)], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr


async def test_native_defaults_allow_resource_filtering(audit_runtime, dashboards, make_connection, make_user):
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import LovelaceStorage
    runtime = audit_runtime
    data = runtime.hass.data[LOVELACE_DATA]
    data.dashboards[None] = LovelaceStorage(runtime.hass, None)
    await dashboards['lovelace'].async_delete()
    map_board = LovelaceStorage(runtime.hass, {'id':'map', 'url_path':'map', 'title':'Map'})
    await map_board.async_save({'strategy':{'type':'map'}})
    data.dashboards['map'] = map_board
    await data.resources.async_create_item({'url':'/local/button-card.js', 'res_type':'module'})
    await runtime.async_set_control('resource_filtering', True)
    await runtime.async_scan()
    assert runtime.resource_complete and not runtime.resource_scan_problem
    client, packets = make_connection(make_user(admin=True))
    client.async_handle({'id':1, 'type':'loona/subscribe_panel', 'dashboard':'wall-panel'})
    client.async_handle({'id':2, 'type':'lovelace/resources'})
    await runtime.hass.async_block_till_done()
    assert next(row['result'] for row in packets if row.get('id') == 2) == []
    await map_board.async_save({'strategy':{'type':'unfamiliar'}})
    await runtime.async_scan()
    assert not runtime.resource_complete
    assert all(row['forwarded'] for row in runtime.resource_preview['resources'])


async def test_resource_failure_warning_follows_control(audit_runtime, dashboards, monkeypatch, caplog):
    import logging
    runtime = audit_runtime
    async def unavailable(force):
        raise OSError('private-path')
    monkeypatch.setattr(dashboards['lovelace'], 'async_load', unavailable)
    caplog.set_level(logging.WARNING)
    await runtime.async_scan()
    assert not any('resource_scan unavailable' in row.message for row in caplog.records)
    assert not any(row['code'] == 'resource_scan' for row in runtime.notice_report())
    await runtime.async_set_control('resource_filtering', True)
    assert sum('resource_scan unavailable' in row.message for row in caplog.records) == 1
    await runtime.async_scan()
    assert sum('resource_scan unavailable' in row.message for row in caplog.records) == 1
    assert 'OSError' in runtime.resource_scan_problem and 'private-path' not in runtime.resource_scan_problem


async def test_reload_recognizes_restored_native_relay(audit_runtime, make_user, make_connection):
    runtime = audit_runtime
    client, packets = make_connection(make_user(admin=True))
    client.async_handle({'id':1, 'type':'loona/subscribe_panel', 'dashboard':'wall-panel'})
    client.async_handle({'id':2, 'type':'subscribe_entities'})
    client.async_handle({'id':3, 'type':'subscribe_entities', 'entity_ids':[]})
    explicit = client.subscriptions[3]
    await runtime.async_stop()
    assert set(packets[-1]['event']['a']) == {'sensor.wall','sensor.other'}
    new = LoonaRuntime(runtime.hass, runtime.entry)
    try:
        await new.async_start()
        packets.clear()
        client.async_handle({'id':4, 'type':'loona/subscribe_panel', 'dashboard':'wall-panel'})
        assert any(row.get('event',{}).get('resubscribe') for row in packets)
        assert client.subscriptions[3] is explicit
    finally:
        await new.async_stop()


@pytest.mark.parametrize('ownership', [{}, {'id':'former-owner','cards':['settings']}])
async def test_uninstall_clears_stores_and_pending_writes(audit_runtime, ownership):
    import asyncio
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import LovelaceStorage
    from homeassistant.helpers.storage import Store
    from custom_components.loona import async_remove_entry
    from custom_components.loona.const import CONTROL_DEFAULTS
    runtime = audit_runtime
    board = LovelaceStorage(runtime.hass, {'id':'foreign', 'url_path':'loona-statistics', 'title':'Personal'})
    config = {'views':[{'cards':[{'type':'markdown','content':'My dashboard'}]}]}
    await board.async_save(config)
    runtime.hass.data[LOVELACE_DATA].dashboards['loona-statistics'] = board
    await runtime.async_set_control('enabled', False)
    await runtime.statistics_card.store.async_save(ownership)
    await runtime.async_stop()
    # Real Store timers must be cancelled on their original instances.
    runtime._store.async_delay_save(lambda:{'enabled':False}, 0.01)
    runtime.statistics_card.store.async_delay_save(lambda:ownership, 0.01)
    await async_remove_entry(runtime.hass, runtime.entry)
    await asyncio.sleep(0.03)
    await runtime.hass.async_block_till_done()
    for key in ('controls','statistics_dashboard'):
        assert await Store(runtime.hass,1,f'loona.{runtime.entry.entry_id}.{key}').async_load() is None
    assert await board.async_load(False) == config
    fresh = LoonaRuntime(runtime.hass, runtime.entry)
    try:
        await fresh.async_start()
        assert fresh.controls == CONTROL_DEFAULTS
        assert not fresh.statistics_card.opted_out
    finally:
        await fresh.async_stop()


async def test_probe_cause_is_logged_and_redacted(loona_hass, dashboards, make_entry, monkeypatch, caplog):
    import logging
    from custom_components.loona import resources
    async def broken_load(self, force=False):
        raise OSError('private-resource-path')
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    loona_hass.data[LOVELACE_DATA].resources.loaded = False
    monkeypatch.setattr(resources.native_resources.ResourceStorageCollection, 'async_load', broken_load)
    caplog.set_level(logging.DEBUG, logger='custom_components.loona')
    runtime = LoonaRuntime(loona_hass, make_entry({'dashboards':['wall-panel'], 'target_mode':'all'}))
    try:
        await runtime.async_start()
        assert runtime.resource_adapter is not None and runtime.adapter is not None
        assert not runtime.resource_complete
        assert 'OSError' in runtime.resource_scan_problem
        assert 'private-resource-path' not in runtime.resource_scan_problem
        assert any(row.exc_info and isinstance(row.exc_info[1], OSError) for row in caplog.records)
    finally:
        await runtime.async_stop()


@pytest.mark.parametrize('language', ['de','zh-Hans','zh-Hant'])
async def test_default_dashboard_title_uses_native_translation(audit_runtime, language):
    from homeassistant.helpers import translation
    from custom_components.loona.dashboard import dashboard_titles
    runtime = audit_runtime
    runtime.hass.config.language = language
    await runtime.async_scan()
    native = translation.async_get_cached_translations(runtime.hass,language,'dashboard','onboarding')
    assert dashboard_titles(runtime.hass)['lovelace'] == native['component.onboarding.dashboard.overview.title']
