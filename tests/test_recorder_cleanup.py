"""Verify uninstall ownership and deletion using the native Recorder and SQLite."""

import asyncio

import pytest
from sqlalchemy import select

from homeassistant.components import recorder
from homeassistant.components.recorder.db_schema import Statistics, StatisticsMeta, StatisticsShortTerm
from homeassistant.components.recorder.util import get_instance
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.recorder import async_initialize_recorder

from custom_components.loona import async_remove_entry, async_setup_entry, async_unload_entry
from custom_components.loona.recorder import owned_statistic_ids, retired_statistic_ids


@pytest.fixture
async def native_recorder(loona_hass):
    """Start the genuine Recorder thread, schema and task queue in a temporary file."""
    async_initialize_recorder(loona_hass)
    config = recorder.CONFIG_SCHEMA({"recorder": {
        "db_url": "sqlite:///" + loona_hass.config.path("recorder-test.db"),
        "auto_purge": False,
        "commit_interval": 0,
    }})
    assert await recorder.async_setup(loona_hass, config)
    loona_hass.config.components.add("recorder")
    await loona_hass.async_start()
    instance = get_instance(loona_hass)
    await asyncio.wait_for(instance.async_recorder_ready.wait(), 15)
    yield instance


def _seed(instance, statistic_ids):
    """Write long-term and short-term rows the way Recorder compiles them."""
    with instance.get_session() as session:
        for statistic_id in statistic_ids:
            meta = StatisticsMeta(statistic_id=statistic_id, source="recorder", has_sum=True)
            session.add(meta)
            session.flush()
            for table in (Statistics, StatisticsShortTerm):
                session.add(table(metadata_id=meta.id, start_ts=1000, state=12, sum=12))
        session.commit()


def _remaining(instance):
    with instance.get_session() as session:
        return [
            set(session.scalars(select(StatisticsMeta.statistic_id)))
        ] + [
            set(session.scalars(select(StatisticsMeta.statistic_id).join(table, table.metadata_id == StatisticsMeta.id)))
            for table in (Statistics, StatisticsShortTerm)
        ]


async def _wait_for_remaining(instance, expected):
    # The Recorder thread can still be committing the queued deletion under a busy suite.
    for _ in range(50):
        if await instance.async_add_executor_job(_remaining, instance) == [expected] * 3:
            break
        await instance.async_block_till_done()
        await asyncio.sleep(0.05)
    assert await instance.async_add_executor_job(_remaining, instance) == [expected] * 3


@pytest.mark.parametrize("legacy_api", [False, True])
async def test_uninstall_removes_both_statistic_tables_and_preserves_foreign_data(
    loona_hass, make_entry, native_recorder, monkeypatch, legacy_api,
):
    entry = make_entry({"dashboard_cards": []})
    other_entry = make_entry({"dashboard_cards": []})
    registry = er.async_get(loona_hass)
    current = registry.async_get_or_create("sensor", "loona", "active", config_entry=entry)
    deleted = registry.async_get_or_create("sensor", "loona", "deleted", config_entry=entry)
    registry.async_remove(deleted.entity_id)
    orphan = registry.async_get_or_create("sensor", "loona", "orphan", config_entry=entry)
    registry.async_remove(orphan.entity_id)
    # Native cleanup detaches orphaned records, as it does after an earlier uninstall.
    import attr
    key = (orphan.domain, orphan.platform, orphan.unique_id)
    registry.deleted_entities[key] = attr.evolve(registry.deleted_entities[key], config_entry_id=None)
    reused = registry.async_get_or_create("sensor", "loona", "reused", config_entry=entry)
    registry.async_remove(reused.entity_id)
    foreign = registry.async_get_or_create("sensor", "foreign", "foreign", suggested_object_id=reused.entity_id.split(".")[1])
    assert foreign.entity_id == reused.entity_id
    unregistered = registry.async_get_or_create("sensor", "loona", "unregistered", config_entry=entry)
    registry.async_remove(unregistered.entity_id)
    loona_hass.states.async_set(unregistered.entity_id, "9")
    # Even the loona_ name prefix confers no ownership.
    prefixed = registry.async_get_or_create("sensor", "foreign", "prefixed", suggested_object_id="loona_foreign")
    other = registry.async_get_or_create("sensor", "loona", "other", config_entry=other_entry)
    registry.async_remove(other.entity_id)
    wanted = {current.entity_id, deleted.entity_id, orphan.entity_id}
    preserved = {foreign.entity_id, unregistered.entity_id, prefixed.entity_id, other.entity_id, "sensor.dashboard_energy"}
    assert set(owned_statistic_ids(loona_hass, entry.entry_id)) == wanted

    await native_recorder.async_add_executor_job(_seed, native_recorder, wanted | preserved)
    if legacy_api:
        clear = native_recorder.async_clear_statistics
        def legacy_clear(statistic_ids):
            clear(statistic_ids)
        monkeypatch.setattr(native_recorder, "async_clear_statistics", legacy_clear)
    await async_remove_entry(loona_hass, entry)
    await native_recorder.async_block_till_done()
    await _wait_for_remaining(native_recorder, preserved)


async def test_untracking_a_dashboard_clears_its_statistics_and_keeps_the_rest(
    loona_hass, make_entry, dashboards, frontend_http, native_recorder,
):
    loona_hass.states.async_set("sensor.wall", "1")
    entry = make_entry({"dashboards": ["lovelace", "wall-panel"], "target_mode": "all"})
    async with entry.setup_lock:
        assert await async_setup_entry(loona_hass, entry)
    await loona_hass.async_block_till_done()
    registry = er.async_get(loona_hass)

    def sensors(scope):
        return {
            item.entity_id for item in er.async_entries_for_config_entry(registry, entry.entry_id)
            if item.domain == "sensor" and f":{scope}:" in item.unique_id
        }

    untracked, tracked, overall = sensors("wall-panel"), sensors("lovelace"), sensors("global")
    assert len(untracked) == len(tracked) == 2
    preserved = tracked | overall | {"sensor.wall"}
    await native_recorder.async_add_executor_job(_seed, native_recorder, untracked | preserved)
    loona_hass.config_entries.async_update_entry(entry, options={"dashboards": ["lovelace"]})
    await loona_hass.async_block_till_done()
    assert not sensors("wall-panel")
    await native_recorder.async_block_till_done()
    await _wait_for_remaining(native_recorder, preserved)
    assert await async_unload_entry(loona_hass, entry)
    await entry._async_process_on_unload(loona_hass)


async def test_retired_statistics_skip_ids_that_came_back(loona_hass):
    registry = er.async_get(loona_hass)
    registry.async_get_or_create("sensor", "foreign", "returned", suggested_object_id="returned")
    loona_hass.states.async_set("sensor.active", "1")
    retired = ["sensor.gone", "sensor.returned", "sensor.active", "sensor.gone"]
    assert retired_statistic_ids(loona_hass, retired) == ["sensor.gone"]
