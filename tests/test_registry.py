"""Verify native registry envelopes, relationships, refreshes, and ownership."""

from dataclasses import replace
from unittest.mock import patch

import pytest

from homeassistant.components import websocket_api
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    label_registry as lr,
)

from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.dependencies import discover, DiscoveryContext
from custom_components.loona.registry import (
    RegistryAdapter,
    RegistryScope,
    registry_scope,
)
from custom_components.loona.websocket import ScopePolicy


@pytest.fixture
def registry_entries(loona_hass, make_entry):
    entry = make_entry({})
    floor = fr.async_get(loona_hass).async_create("Floor")
    label = lr.async_get(loona_hass).async_create("Label")
    area = ar.async_get(loona_hass).async_create("Area", floor_id=floor.floor_id)
    ar.async_get(loona_hass).async_update(area.id, labels={label.label_id})
    registry = dr.async_get(loona_hass)
    parent = registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "parent")}
    )
    registry.async_update_device(parent.id, area_id=area.id)
    child = registry.async_get_or_create_child(
        config_entry_id=entry.entry_id,
        identifiers={("test", "child")},
        parent_device_id=parent.id,
    )
    kept = er.async_get(loona_hass).async_get_or_create(
        "sensor", "test", "kept", device_id=child.id, original_name="Kept"
    )
    other = er.async_get(loona_hass).async_get_or_create("sensor", "test", "other")
    disabled = er.async_get(loona_hass).async_get_or_create(
        "sensor", "test", "disabled", disabled_by=er.RegistryEntryDisabler.USER
    )
    ar.async_get(loona_hass).async_create("Other area")
    fr.async_get(loona_hass).async_create("Other floor")
    lr.async_get(loona_hass).async_create("Other label")
    return kept, other, disabled, parent, child, area, floor, label


def request(connection, output, command):
    msg_id = connection.last_id + 1
    connection.async_handle({"id": msg_id, "type": command})
    result = next(
        message for message in reversed(output) if message.get("id") == msg_id
    )
    assert result["success"]
    return result["result"]


@pytest.mark.parametrize("admin", [True, False])
async def test_native_lists_preserve_fields_disabled_entries_and_relationships(
    loona_hass, registry_entries, make_user, make_connection, admin
):
    kept, other, disabled, parent, child, area, floor, label = registry_entries
    user = make_user(admin=admin)
    connection, output = make_connection(user)
    names = [
        "config/entity_registry/list",
        "config/entity_registry/list_for_display",
        "config/device_registry/list",
        "config/area_registry/list",
        "config/floor_registry/list",
        "config/label_registry/list",
    ]
    baseline = {name: request(connection, output, name) for name in names}
    scope = registry_scope(
        loona_hass, frozenset({kept.entity_id, disabled.entity_id}), []
    )
    assert scope.devices == {parent.id, child.id}
    assert scope.areas == {area.id}
    assert scope.floors == {floor.floor_id}
    assert scope.labels == {label.label_id}
    errors = []
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(scope.entities, frozenset({user.id})),
        scope,
        errors.append,
    )
    adapter.install()
    try:
        for name, key, ids in zip(
            names,
            ["entity_id", "ei", "id", "area_id", "floor_id", "label_id"],
            [
                scope.entities,
                scope.entities,
                scope.devices,
                scope.areas,
                scope.floors,
                scope.labels,
            ],
            strict=True,
        ):
            result = request(connection, output, name)
            expected = baseline[name]
            if name.endswith("list_for_display"):
                assert result == {
                    **expected,
                    "entities": [
                        row for row in expected["entities"] if row[key] in ids
                    ],
                }
                assert {row["ei"] for row in result["entities"]} == {kept.entity_id}
            else:
                assert result == [row for row in expected if row[key] in ids]
        assert not errors
        unselected, unselected_output = make_connection(make_user(admin=True))
        assert request(unselected, unselected_output, names[0]) == baseline[names[0]]
        adapter.set_policy(replace(adapter.policy, enabled=False), scope)
        assert request(connection, output, names[0]) == baseline[names[0]]
    finally:
        adapter.uninstall()


async def test_direct_empty_targets_and_area_sensor_metadata_are_retained(
    loona_hass, registry_entries
):
    kept, _, _, parent, _, area, floor, label = registry_entries
    empty = ar.async_get(loona_hass).async_create("Empty")
    loona_hass.states.async_set(kept.entity_id, "22", {"device_class": "temperature"})
    ar.async_get(loona_hass).async_update(area.id, temperature_entity_id=kept.entity_id)
    result = discover(
        {
            "cards": [
                {"type": "area", "area": empty.id},
                {
                    "target": {
                        "device_id": parent.id,
                        "area_id": area.id,
                        "floor_id": floor.floor_id,
                        "label_id": label.label_id,
                    }
                },
            ]
        },
        DiscoveryContext(),
    )
    scope = registry_scope(loona_hass, frozenset(), [result])
    assert {area.id, empty.id} <= scope.areas
    assert kept.entity_id in scope.entities
    assert parent.id in scope.devices
    assert floor.floor_id in scope.floors
    assert label.label_id in scope.labels


async def test_registry_refresh_on_scope_bypass_targets_and_unload(
    loona_hass, registry_entries, make_user, make_connection
):
    kept, other, *_ = registry_entries
    user = make_user(admin=True)
    selected, selected_output = make_connection(user)
    unselected, unselected_output = make_connection(make_user())
    policy = ScopePolicy(frozenset({kept.entity_id}), frozenset({user.id}))
    scope = RegistryScope(entities=policy.entity_ids)
    adapter = RegistryAdapter(
        loona_hass, policy, scope, lambda error: pytest.fail(str(error))
    )
    originals = dict(loona_hass.data[websocket_api.DOMAIN])
    adapter.install()
    for connection in (selected, unselected):
        connection.async_handle(
            {
                "id": 1,
                "type": "subscribe_events",
                "event_type": "entity_registry_updated",
            }
        )
        connection.async_handle(
            {"id": 2, "type": "subscribe_events", "event_type": "service_registered"}
        )
    selected_output.clear()
    unselected_output.clear()
    expanded = replace(scope, entities=frozenset({kept.entity_id, other.entity_id}))
    adapter.set_policy(replace(policy, entity_ids=expanded.entities), expanded)
    assert len(selected_output) == 1 and selected_output[0]["id"] == 1
    assert selected_output[0]["event"]["event_type"] == "entity_registry_updated"
    assert not unselected_output
    selected_output.clear()
    adapter.set_policy(replace(adapter.policy, enabled=False), expanded)
    assert len(selected_output) == 1
    selected_output.clear()
    adapter.set_policy(replace(adapter.policy, enabled=True, all_users=True), expanded)
    assert len(selected_output) == len(unselected_output) == 1
    selected_output.clear()
    unselected_output.clear()
    adapter.uninstall()
    assert len(selected_output) == len(unselected_output) == 1
    assert not adapter._watchers
    assert all(
        loona_hass.data[websocket_api.DOMAIN][name] is entry
        for name, entry in originals.items()
    )
    loona_hass.bus.async_fire(
        "entity_registry_updated", {"action": "update", "entity_id": kept.entity_id}
    )
    await loona_hass.async_block_till_done()
    assert selected_output[-1]["event"]["data"]["entity_id"] == kept.entity_id


async def test_generic_events_mutations_and_admin_checks_are_native(
    loona_hass, registry_entries, make_user, make_connection
):
    kept, *_ = registry_entries
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(frozenset({kept.entity_id}), all_users=True),
        RegistryScope(entities=frozenset({kept.entity_id})),
        lambda error: pytest.fail(str(error)),
    )
    adapter.install()
    connection, output = make_connection(make_user())
    try:
        connection.async_handle(
            {
                "id": 1,
                "type": "config/entity_registry/update",
                "entity_id": kept.entity_id,
                "name": "Unauthorized",
            }
        )
        assert output[-1]["error"]["code"] == "unauthorized"
        assert er.async_get(loona_hass).async_get(kept.entity_id).name is None
        connection.async_handle(
            {"id": 2, "type": "subscribe_events", "event_type": "unknown_private_event"}
        )
        assert output[-1]["error"]["code"] == "unauthorized"
        assert not connection.subscriptions and not adapter._watchers
    finally:
        adapter.uninstall()


async def test_installation_is_atomic_and_later_foreign_owner_survives(
    loona_hass, registry_entries, make_user, make_connection
):
    kept, *_ = registry_entries
    table = loona_hass.data[websocket_api.DOMAIN]
    originals = dict(table)
    command = "config/device_registry/list"
    foreign = (lambda *args: None, table[command][1])
    table[command] = foreign
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(frozenset({kept.entity_id}), all_users=True),
        RegistryScope(entities=frozenset({kept.entity_id})),
        lambda error: None,
    )
    with pytest.raises(CompatibilityError):
        adapter.install()
    assert (
        table["config/entity_registry/list"] is originals["config/entity_registry/list"]
    )
    table[command] = originals[command]
    adapter.install()
    table[command] = foreign
    connection, output = make_connection(make_user(admin=True))
    result = request(connection, output, "config/entity_registry/list")
    assert len(result) == 3
    assert table[command] is foreign
    assert table["subscribe_events"] is originals["subscribe_events"]


async def test_malformed_native_response_passes_through_and_disables_registry_only(
    loona_hass, make_user, make_connection
):
    errors = []
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(frozenset({"sensor.kept"}), all_users=True),
        RegistryScope(entities=frozenset({"sensor.kept"})),
        errors.append,
    )
    adapter.install()
    connection, output = make_connection(make_user(admin=True))
    name = "config/entity_registry/list_for_display"

    def malformed(hass, conn, msg):
        conn.send_result(
            msg["id"], {"entities": [{"unexpected": True}], "entity_categories": {}}
        )

    adapter._originals[name] = (malformed, adapter._originals[name][1])
    result = request(connection, output, name)
    assert result["entities"] == [{"unexpected": True}]
    assert errors and adapter._table is None


async def test_unsubscribe_and_foreign_subscription_callback_are_preserved(
    loona_hass, make_user, make_connection
):
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(frozenset({"sensor.kept"}), all_users=True),
        RegistryScope(entities=frozenset({"sensor.kept"})),
        lambda error: None,
    )
    adapter.install()
    connection, output = make_connection(make_user(admin=True))
    connection.async_handle(
        {"id": 1, "type": "subscribe_events", "event_type": "entity_registry_updated"}
    )
    native = adapter._watchers[(connection, 1)][2]
    foreign = lambda: native()
    connection.subscriptions[1] = foreign
    adapter.set_policy(replace(adapter.policy, enabled=False), adapter.scope)
    assert len(output) == 1
    adapter.uninstall()
    assert connection.subscriptions[1] is foreign
    connection.async_handle({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert not adapter._watchers and not connection.subscriptions


async def test_response_error_and_concurrent_native_requests_do_not_interfere(
    loona_hass, make_user, make_connection
):
    adapter = RegistryAdapter(
        loona_hass,
        ScopePolicy(frozenset({"sensor.kept"}), all_users=True),
        RegistryScope(),
        lambda error: None,
    )
    adapter.install()
    connection, output = make_connection(make_user(admin=True))
    sender = connection.send_message
    try:
        request(connection, output, "config/entity_registry/list_for_display")
        assert connection.send_message is sender
        connection.async_handle(
            {
                "id": connection.last_id + 1,
                "type": "config/entity_registry/get",
                "entity_id": "sensor.missing",
            }
        )
        assert output[-1]["error"]["code"] == "not_found"
    finally:
        adapter.uninstall()


@pytest.mark.parametrize(
    "policy",
    [
        ScopePolicy(enabled=False),
        ScopePolicy(complete=False),
        ScopePolicy(),
    ],
)
async def test_empty_incomplete_and_disabled_scopes_preserve_native_metadata(
    loona_hass, registry_entries, make_user, make_connection, policy
):
    connection, output = make_connection(make_user(admin=True))
    adapter = RegistryAdapter(
        loona_hass,
        replace(policy, all_users=True),
        RegistryScope(),
        lambda error: pytest.fail(str(error)),
    )
    adapter.install()
    try:
        assert len(request(connection, output, "config/entity_registry/list")) == 3
    finally:
        adapter.uninstall()


async def test_unsupported_registry_version_leaves_all_commands_native(loona_hass):
    table = loona_hass.data[websocket_api.DOMAIN]
    originals = dict(table)
    adapter = RegistryAdapter(
        loona_hass, ScopePolicy(), RegistryScope(), lambda error: None
    )
    with (
        patch("homeassistant.const.__version__", "2025.1.0"),
        pytest.raises(CompatibilityError),
    ):
        adapter.install()
    assert all(table[name] is entry for name, entry in originals.items())
