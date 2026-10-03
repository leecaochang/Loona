"""Verify uninstall ownership and deletion using the native Recorder and SQLite."""

import asyncio

import pytest
from sqlalchemy import select

from homeassistant.components import recorder
from homeassistant.components.recorder.db_schema import Statistics, StatisticsMeta, StatisticsShortTerm
from homeassistant.components.recorder.util import get_instance
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.recorder import async_initialize_recorder

from custom_components.loona import async_remove_entry
from custom_components.loona.recorder import owned_statistic_ids


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

    def seed():
        with native_recorder.get_session() as session:
            for statistic_id in wanted | preserved:
                meta = StatisticsMeta(statistic_id=statistic_id, source="recorder", has_sum=True)
                session.add(meta)
                session.flush()
                for table in (Statistics, StatisticsShortTerm):
                    session.add(table(metadata_id=meta.id, start_ts=1000, state=12, sum=12))
            session.commit()

    await native_recorder.async_add_executor_job(seed)
    if legacy_api:
        clear = native_recorder.async_clear_statistics
        def legacy_clear(statistic_ids):
            clear(statistic_ids)
        monkeypatch.setattr(native_recorder, "async_clear_statistics", legacy_clear)
    await async_remove_entry(loona_hass, entry)
    await native_recorder.async_block_till_done()

    def remaining():
        with native_recorder.get_session() as session:
            return [
                set(session.scalars(select(StatisticsMeta.statistic_id)))
            ] + [
                set(session.scalars(select(StatisticsMeta.statistic_id).join(table, table.metadata_id == StatisticsMeta.id)))
                for table in (Statistics, StatisticsShortTerm)
            ]
    assert await native_recorder.async_add_executor_job(remaining) == [preserved] * 3
