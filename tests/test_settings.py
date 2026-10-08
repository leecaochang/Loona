"""Verify card settings through native admin dispatch, storage and scope scans."""

import json
import string
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from custom_components.loona import async_setup_entry, async_unload_entry
from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.settings import revision, settings_report
from custom_components.loona.const import CONTROL_DEFAULTS, SETTINGS_DEFAULTS


@pytest.fixture
async def settings_runtime(loona_hass, make_entry, dashboards, frontend_http):
    loona_hass.config.components.update({'lovelace', 'frontend'})
    loona_hass.states.async_set('sensor.wall', '0')
    loona_hass.states.async_set('sensor.other', '0')
    entry = make_entry({'dashboards': ['wall-panel'], 'target_mode': 'all'}, options={
        'extra_entities': ['sensor.future'], 'include_globs': ['sensor.saved_*'],
    })
    async with entry.setup_lock:
        assert await async_setup_entry(loona_hass, entry)
    await loona_hass.async_block_till_done()
    yield entry.runtime_data
    assert await async_unload_entry(loona_hass, entry)
    await entry._async_process_on_unload(loona_hass)


async def request(runtime, client, output, name='loona/settings', **fields):
    msg_id = client.last_id + 1
    client.async_handle({'id': msg_id, 'type': name, **fields})
    await runtime.hass.async_block_till_done(wait_background_tasks=True)
    return next(row for row in reversed(output) if row.get('id') == msg_id)


async def test_control_order_and_native_action_entities(settings_runtime):
    runtime = settings_runtime
    report = await settings_report(runtime)
    assert list(report['values']['controls']) == [key for key in CONTROL_DEFAULTS
                                                if key in runtime.available_controls]
    assert list(report['action_entities']) == ['rescan', 'reset_live_statistics']
    for key, entity_id in report['action_entities'].items():
        assert entity_id is not None and entity_id.startswith('button.')
        assert entity_id in runtime.hass.states.async_entity_ids()
        before_scan = runtime.last_scan
        runtime.live_statistics.record(True)
        await runtime.hass.services.async_call('button', 'press',
                                               {'entity_id': entity_id}, blocking=True)
        if key == 'rescan':
            assert runtime.last_scan >= before_scan
            assert runtime.live_statistics.forwarded == 1
        else:
            assert runtime.live_statistics.forwarded == 0


async def test_restore_defaults_confirmation_permissions_revision_persistence_and_failure(settings_runtime, make_user, make_connection, monkeypatch):
    runtime = settings_runtime
    await runtime.async_set_controls({key: not value for key, value in CONTROL_DEFAULTS.items() if key in runtime.available_controls})
    runtime.live_statistics.record(True)
    runtime.live_statistics.page_loads["fixture"] = {}
    runtime.live_statistics.browser_reports["fixture"] = {}
    client, output = make_connection(make_user(admin=True))
    reader, errors = make_connection(make_user())
    before = dict(runtime.entry.options), dict(runtime.controls)
    fields = {"revision": revision(runtime), "confirmed": True}
    denied = await request(runtime, reader, errors, "loona/restore_defaults", **fields)
    assert denied["error"]["code"] == "unauthorized"
    for confirmation in (False, 1):
        rejected = await request(runtime, client, output, "loona/restore_defaults", **{**fields, "confirmed": confirmation})
        assert not rejected["success"]
    stale = await request(runtime, client, output, "loona/restore_defaults", revision="0" * 64, confirmed=True)
    assert stale["error"]["code"] == "conflict"
    with monkeypatch.context() as patch:
        patch.setattr(runtime._store, "async_save", AsyncMock(side_effect=OSError("Persist failed")))
        failed = await request(runtime, client, output, "loona/restore_defaults", **fields)
        assert failed["error"]["code"] == "save_failed"
    assert before == (dict(runtime.entry.options), dict(runtime.controls))
    assert runtime.live_statistics.forwarded == 1
    restored = await request(runtime, client, output, "loona/restore_defaults", **fields)
    assert restored["success"]
    assert runtime.entry.options == SETTINGS_DEFAULTS
    assert runtime.controls == await runtime._store.async_load() == CONTROL_DEFAULTS
    assert not runtime.selected_dashboards and runtime.settings["target_mode"] == "selected"
    assert not runtime.live_statistics.forwarded and not runtime.live_statistics.page_loads and not runtime.live_statistics.browser_reports
    assert runtime.hass.states.get("sensor.other").state == "0"
    assert runtime.entry.data["dashboards"] == ["wall-panel"], "Empty options must override original selections"


async def test_card_removal_requires_explicit_confirmation(settings_runtime, make_user, make_connection):
    runtime = settings_runtime
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={**runtime.entry.options, "dashboard_cards": ["settings"]})
    await runtime.hass.async_block_till_done()
    client, output = make_connection(make_user(admin=True))
    fields = {"group": "cards", "revision": revision(runtime), "values": {"dashboard_cards": []}}
    response = await request(runtime, client, output, "loona/save_settings", **fields)
    assert response["error"]["code"] == "confirmation_required"
    assert runtime.settings["dashboard_cards"] == ["settings"]
    response = await request(runtime, client, output, "loona/save_settings", **fields, confirmed=True)
    assert response["success"] and runtime.settings["dashboard_cards"] == []


async def test_prefilled_choices_and_private_dispatch(settings_runtime, make_user, make_connection):
    runtime = settings_runtime
    admin = await runtime.hass.auth.async_create_user('Administrator', group_ids=['system-admin'])
    inactive = await runtime.hass.auth.async_create_user('Inactive')
    await runtime.hass.auth.async_update_user(inactive, is_active=False)
    await runtime.hass.auth.async_create_system_user('Service')
    client, output = make_connection(make_user(admin=True))
    report = (await request(runtime, client, output))['result']
    assert report['choices']['user_ids'] == [{'value': admin.id, 'label': 'Administrator', 'unavailable': False}]
    assert {'sensor.*', 'sensor.saved_*'} <= {row['value'] for row in report['choices']['include_globs']}
    assert next(row for row in report['choices']['extra_entities'] if row['value'] == 'sensor.future')['unavailable']
    assert set(report['values']['controls']) == runtime.available_controls
    denied, errors = make_connection(make_user())
    before = dict(runtime.entry.options), dict(runtime.controls)
    for name, fields in [('loona/settings', {}), ('loona/save_settings', {
        'group': 'rules', 'revision': report['revision'], 'values': {'extra_entities': []},
    })]:
        response = await request(runtime, denied, errors, name, **fields)
        assert not response['success'] and response['error']['code'] == 'unauthorized'
        assert 'result' not in response
    assert before == (dict(runtime.entry.options), dict(runtime.controls))


@pytest.mark.parametrize(('group', 'values', 'error'), [
    ('dashboards', {'dashboards': []}, 'no_dashboards'),
    ('dashboards', {'dashboards': ['wall-panel', 'wall-panel']}, 'invalid_selection'),
    ('dashboards', {'dashboards': ['invented']}, 'invalid_selection'),
    ('targets', {'target_mode': 'selected', 'user_ids': []}, 'no_accounts'),
    ('targets', {'target_mode': 'selected', 'user_ids': ['invented']}, 'invalid_selection'),
    ('rules', {'extra_entities': ['sensor.invented'], 'include_domains': [], 'include_globs': [], 'exclude_globs': []}, 'invalid_selection'),
    ('rules', {'extra_entities': ['sensor.wall', 'sensor.wall'], 'include_domains': [], 'include_globs': [], 'exclude_globs': []}, 'invalid_selection'),
    ('rules', {'extra_entities': [], 'include_domains': [], 'include_globs': ['sensor.invented'], 'exclude_globs': []}, 'invalid_selection'),
    ('rules', {'extra_entities': [], 'include_domains': [], 'include_globs': ['sensor.['], 'exclude_globs': []}, 'invalid_selection'),
    ('rules', {'extra_entities': [], 'include_domains': [], 'include_globs': [], 'exclude_globs': ['sensor.' + 'a' * 250 + '*']}, 'invalid_selection'),
    ('rules', {'extra_entities': ['sensor.kitchen_*'], 'include_domains': [], 'include_globs': [], 'exclude_globs': []}, 'invalid_selection'),
    ('resources', {'always_forward_resources': ['/local/invented.js']}, 'invalid_selection'),
    ('controls', {'enabled': True}, 'invalid_selection'),
])
async def test_forged_choices_do_not_mutate(settings_runtime, make_user, make_connection, group, values, error):
    runtime = settings_runtime
    client, output = make_connection(make_user(admin=True))
    before = dict(runtime.entry.options), dict(runtime.controls)
    response = await request(runtime, client, output, 'loona/save_settings', group=group, revision=revision(runtime), values=values)
    assert not response['success'] and response['error']['code'] == error
    assert before == (dict(runtime.entry.options), dict(runtime.controls))


async def test_valid_sections_reconcile_without_replacing_subscriptions(settings_runtime, make_user, make_connection):
    runtime = settings_runtime
    admin = await runtime.hass.auth.async_create_user('Active', group_ids=['system-admin'])
    client, output = make_connection(make_user(admin=True))
    client.async_handle({'id': 1, 'type': 'subscribe_entities'})
    adapter = runtime.adapter
    for group, values in [
        ('dashboards', {'dashboards': ['lovelace', 'wall-panel']}),
        ('targets', {'target_mode': 'selected', 'user_ids': [admin.id]}),
        ('rules', {'extra_entities': ['sensor.other'], 'include_domains': ['sensor'], 'include_globs': ['sensor.saved_*'], 'exclude_globs': []}),
        ('resources', {'always_forward_resources': []}),
    ]:
        before = dict(runtime.entry.options)
        response = await request(runtime, client, output, 'loona/save_settings', group=group, revision=revision(runtime), values=values)
        assert response['success'], response
        assert response['result']['values'][group] == values
        assert all(runtime.entry.options.get(key) == value for key, value in before.items() if key not in values)
        assert runtime.adapter is adapter and runtime.adapter.managed_count == 1
    assert 'sensor.other' in runtime.entity_ids
    # Changes through Configure or native switches invalidate card revisions.
    old = revision(runtime)
    await runtime.async_set_control('enabled', False)
    response = await request(runtime, client, output, 'loona/save_settings', group='rules', revision=old, values={'extra_entities': []})
    assert response['error']['code'] == 'conflict'
    assert runtime.settings['extra_entities'] == ['sensor.other']
    old = revision(runtime)
    runtime.hass.config_entries.async_update_entry(runtime.entry, options={**runtime.entry.options, 'extra_entities': []})
    response = await request(runtime, client, output, 'loona/save_settings', group='rules', revision=old, values={'extra_entities': ['sensor.other']})
    assert response['error']['code'] == 'conflict'


async def test_new_wildcard_patterns_are_offered_saved_and_applied(settings_runtime, make_user, make_connection):
    from custom_components.loona.settings import entity_choices
    runtime = settings_runtime
    runtime.hass.states.async_set('sensor.kitchen_temperature', '20')
    runtime.hass.states.async_set('sensor.kitchen_humidity', '40')
    assert [row['value'] for row in entity_choices(runtime, 'include_globs', ' Sensor.Kitchen_* ')['choices']] == ['sensor.kitchen_*']
    assert '*' not in str(entity_choices(runtime, 'include_globs', 'sensor.kitchen_temperature')['choices'])
    assert not entity_choices(runtime, 'extra_entities', 'sensor.kitchen_*')['choices']
    client, output = make_connection(make_user(admin=True))
    values = {'extra_entities': [], 'include_domains': [], 'include_globs': ['sensor.kitchen_*'], 'exclude_globs': ['sensor.kitchen_h?midity']}
    response = await request(runtime, client, output, 'loona/save_settings', group='rules', revision=revision(runtime), values=values)
    assert response['success'], response
    assert response['result']['values']['rules'] == values
    assert 'sensor.kitchen_temperature' in runtime.entity_ids and 'sensor.kitchen_humidity' not in runtime.entity_ids


async def test_controls_batch_storage_failure_and_resource_fallback(settings_runtime, monkeypatch, make_user, make_connection):
    runtime = settings_runtime
    client, output = make_connection(make_user(admin=True))
    values = {key: False for key in runtime.available_controls}
    response = await request(runtime, client, output, 'loona/save_settings', group='controls', revision=revision(runtime), values=values)
    assert response['success'] and response['result']['values']['controls'] == values
    monkeypatch.setattr(runtime._store, 'async_save', AsyncMock(side_effect=OSError('Storage failed')))
    response = await request(runtime, client, output, 'loona/save_settings', group='controls', revision=revision(runtime), values={key: True for key in values})
    assert response['error']['code'] == 'save_failed' and runtime.controls['enabled'] is False
    monkeypatch.setattr(runtime, 'async_resource_preview', AsyncMock(side_effect=CompatibilityError('Unavailable')))
    report = await settings_report(runtime)
    assert not report['resources_editable'] and report['choices']['extra_entities']


def test_translations_cover_native_ui_schema():
    root = Path(__file__).resolve().parents[1] / 'custom_components/loona'
    english = json.loads((root / 'strings.json').read_text())
    assert english == json.loads((root / 'translations/en.json').read_text())

    def leaves(value, prefix=()):
        if isinstance(value, dict):
            return {key: item for name, child in value.items() for key, item in leaves(child, (*prefix, name)).items()}
        return {prefix: value}

    source = leaves(english)
    chinese = leaves(json.loads((root / 'translations/zh-Hans.json').read_text()))
    assert source.keys() == chinese.keys()
    assert all(chinese[key] != value for key, value in source.items() if value != 'Loona')
    for key, value in source.items():
        fields = {part[1] for part in string.Formatter().parse(value) if part[1] is not None}
        localized_fields = {part[1] for part in string.Formatter().parse(chinese[key]) if part[1] is not None}
        assert fields == localized_fields, key
    assert not (root / "translations/zh-Hant.json").exists()
    assert not (root / "translations/zh.json").exists()


async def test_word_search_entity_priority_and_display_names(settings_runtime):
    """Words need not be adjacent; actual entities precede wildcard choices."""
    from homeassistant.helpers import entity_registry as er
    from custom_components.loona.settings import entity_choices
    runtime = settings_runtime
    runtime.hass.states.async_set("fan.bathroom_ceiling", "on", {"friendly_name": "Bathroom ceiling fan"})
    registry = er.async_get(runtime.hass)
    entity = registry.async_get_or_create("fan", "test", "registered", original_name="Old name")
    registry.async_update_entity(entity.entity_id, name="Bathroom wall fan")
    rows = entity_choices(runtime, "include_globs", "bathroom fan")["choices"]
    assert {item["label"] for item in rows} == {"Bathroom ceiling fan", "Bathroom wall fan"}
    rows = entity_choices(runtime, "exclude_globs", "fan")["choices"]
    first_pattern = next(index for index, item in enumerate(rows) if "*" in item["value"])
    assert first_pattern > 0
    assert all("*" not in item["value"] for item in rows[:first_pattern])
    report = await settings_report(runtime)
    assert report["choices"]["dashboard_cards"] == [
        {"value": "statistics", "label": "Loona statistics"}, {"value": "settings", "label": "Loona settings"},
        {"value": "benchmark", "label": "Loona benchmark"}]


async def test_optional_hacs_labels_are_read_only_and_exact(settings_runtime):
    """Metadata names never alter URLs or label foreign resources."""
    from types import SimpleNamespace
    from custom_components.loona.presentation import resource_labels, notice_labels
    from custom_components.loona.preview import statistics_report
    runtime = settings_runtime
    local = "/hacsfiles/example/card.js?v=2"
    foreign = "https://foreign.test/hacsfiles/example/card.js"
    urls = [local, foreign, "/local/unknown.js", "http://[invalid"]
    assert resource_labels(runtime.hass, urls) == dict(zip(urls, urls, strict=True))
    repository = SimpleNamespace(data=SimpleNamespace(category="plugin"), display_name="Example Card",
        generate_dashboard_resource_url=lambda: "/hacsfiles/example/card.js?hacstag=123")
    runtime.hass.data["hacs"] = SimpleNamespace(repositories=SimpleNamespace(list_downloaded=[repository, SimpleNamespace(data=SimpleNamespace(category="integration",domain="example"),display_name="Example Helper"), object()]))
    try:
        assert resource_labels(runtime.hass, urls) == {local: "Example Card", foreign: foreign, urls[2]: urls[2], urls[3]: urls[3]}
        assert resource_labels(runtime.hass, ["/example/example.js?v=1"])["/example/example.js?v=1"] == "Example Helper"
        runtime.hass.states.async_set("sensor.wall", "1", {"friendly_name": "Wall sensor"})
        assert notice_labels(runtime.hass, [{"code":"excluded_dependencies", "items":["sensor.wall"]}]) == {"sensor.wall":"Wall sensor"}
        runtime.live_statistics.record(True, "sensor.wall")
        assert statistics_report(runtime)["noisy_entities"]["entities"][0]["label"] == "Wall sensor"
        assert "label" not in runtime.live_statistics.noisy_report()["entities"][0]
    finally:
        runtime.hass.data.pop("hacs")
