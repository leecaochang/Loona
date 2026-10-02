"""Verify card settings through native admin dispatch, storage and scope scans."""

import json
import string
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from custom_components.loona import async_setup_entry, async_unload_entry
from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.settings import revision, settings_report
from custom_components.loona.const import CONTROL_DEFAULTS


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
    for variant in ['zh', 'zh-Hant']:
        assert leaves(json.loads((root / f'translations/{variant}.json').read_text())) == chinese
