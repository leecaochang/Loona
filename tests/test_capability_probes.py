"""Verify capability admission, real behavior failures and independent fallback."""

from functools import wraps
from types import SimpleNamespace

import pytest
from homeassistant import const as ha_const
from homeassistant.components import websocket_api
from homeassistant.components.config import entity_registry
from homeassistant.components.websocket_api import commands

from custom_components.loona.compatibility import inspect_command
from custom_components.loona.runtime import LoonaRuntime


@pytest.mark.parametrize("version", ["2024.6.0", "2025.1.0", "2026.9.2", "2026.10.0", "2026.10.0.dev0"])
async def test_unlisted_core_with_capabilities_enables_all_features(loona_hass, dashboards, make_entry, monkeypatch, version):
    """Changing the version alone must never disable a compatible native hook."""
    monkeypatch.setattr(ha_const, "__version__", version)
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    try:
        assert runtime.compatibility_problem is None
        assert runtime.available_controls == {
            "enabled", "entity_filtering", "registry_filtering", "resource_filtering",
            "delay_card_resources",
            "visible_first_graphs", "pause_animations_during_loading",
        }
    finally:
        await runtime.async_stop()


async def test_entity_probe_does_not_touch_real_states_users_or_listeners(loona_hass):
    loona_hass.states.async_set("sensor.existing", "1")
    states = loona_hass.states.async_all()
    listeners = loona_hass.bus.async_listeners()
    users = await loona_hass.auth.async_get_users()
    commands_before = dict(loona_hass.data[websocket_api.DOMAIN])
    inspect_command(loona_hass)
    assert loona_hass.states.async_all() == states
    assert loona_hass.bus.async_listeners() == listeners
    assert await loona_hass.auth.async_get_users() == users
    assert loona_hass.data[websocket_api.DOMAIN] == commands_before


@pytest.mark.parametrize("feature", ["entity", "registry", "graph", "resource"])
async def test_failed_native_probe_disables_only_its_feature(loona_hass, dashboards, make_entry, monkeypatch, feature):
    """Mutate real native behavior while preserving handler and schema identity."""
    table = loona_hass.data[websocket_api.DOMAIN]
    names = {
        "entity": "subscribe_entities", "registry": "config/entity_registry/list",
        "graph": "get_config", "resource": "lovelace/resources/list",
    }
    name = names[feature]
    native, schema = table[name]
    if feature == "resource":
        # Keep valid schemas and real collection data, corrupt only the emitted result.
        from homeassistant.components.lovelace import resources
        async def changed(hass, connection, msg):
            connection.send_result(msg["id"], {"unexpected": []})
        @wraps(native)
        def wrapper(*args):
            return native(*args)
        wrapper.__wrapped__ = changed
        monkeypatch.setattr(resources.ResourceStorageCollectionWebsocket, "ws_list_item", wrapper)
        for alias in ("lovelace/resources", "lovelace/resources/list"):
            old = table[alias]
            table[alias] = (wrapper, old[1])
    else:
        @wraps(native)
        def changed(hass, connection, msg):
            if feature == "entity":
                # A native implementation ignoring entity_ids must fail the semantic probe.
                return native(hass, connection, {key: value for key, value in msg.items() if key != "entity_ids"})
            connection.send_result(msg["id"], {"unexpected": []} if feature == "registry" else [])
        owner = entity_registry if feature == "registry" else commands
        attribute = {"entity": "handle_subscribe_entities", "registry": "websocket_list_entities", "graph": "handle_get_config"}[feature]
        monkeypatch.setattr(owner, attribute, changed)
        table[name] = (changed, schema)
    originals = {key: value for key, value in table.items() if key == name or feature == "resource" and key.startswith("lovelace/resources")}
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    try:
        assert getattr(runtime, feature + "_compatibility_problem")
        assert getattr(runtime, "adapter" if feature == "entity" else feature + "_adapter") is None
        assert all(table[key] is value for key, value in originals.items())
        for other in {"entity", "registry", "graph", "resource"} - {feature}:
            assert getattr(runtime, other + "_compatibility_problem") is None
            assert getattr(runtime, "adapter" if other == "entity" else other + "_adapter") is not None
    finally:
        await runtime.async_stop()


async def test_resource_aliases_are_discovered_from_registered_capabilities(loona_hass, dashboards, make_entry):
    table = loona_hass.data[websocket_api.DOMAIN]
    table.pop("lovelace/resources")
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    try:
        assert runtime.resource_compatibility_problem is None
        assert runtime.resource_adapter is not None
        assert set(runtime.resource_adapter._originals) == {"lovelace/resources/list"}
    finally:
        await runtime.async_stop()


@pytest.mark.parametrize("failure", ["live", "event_type"])
async def test_live_probe_rejects_changed_listeners_without_real_bus_effects(loona_hass, monkeypatch, failure):
    from custom_components.loona.compatibility import CompatibilityError

    native = commands.handle_subscribe_entities
    table = loona_hass.data[websocket_api.DOMAIN]
    schema = table["subscribe_entities"][1]
    @wraps(native)
    def changed(hass, connection, msg):
        def listen(event_type, listener):
            if failure == "event_type":
                return hass.bus.async_listen("unexpected_event", listener)
            return hass.bus.async_listen(event_type, lambda event: None)
        native(SimpleNamespace(states=hass.states, bus=SimpleNamespace(async_listen=listen)), connection, msg)
    monkeypatch.setattr(commands, "handle_subscribe_entities", changed)
    table["subscribe_entities"] = (changed, schema)
    listeners = loona_hass.bus.async_listeners()
    with pytest.raises(CompatibilityError, match="live entity diffs|event type"):
        inspect_command(loona_hass)
    assert loona_hass.bus.async_listeners() == listeners
    assert table["subscribe_entities"] == (changed, schema)
