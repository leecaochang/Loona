"""Exercise the adapter through Core's actual command dispatch and event bus."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from homeassistant.components import websocket_api
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event

from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter


def snapshot(output):
    """Read the last native compressed initial state response."""
    return next(
        msg["event"]["a"] for msg in reversed(output) if "a" in msg.get("event", {})
    )


def subscribe(connection, msg_id=1, **fields):
    """Run native validation, including its added include/exclude defaults."""
    connection.async_handle({"id": msg_id, "type": "subscribe_entities", **fields})


@pytest.mark.parametrize("admin", [True, False])
async def test_selected_accounts_initial_and_live(
    hass, make_user, make_connection, admin
):
    user = make_user(admin=admin)
    assert user.is_admin is admin
    connection, output = make_connection(user)
    hass.states.async_set("sensor.keep", "0")
    hass.states.async_set("sensor.drop", "0")
    await hass.async_block_till_done()
    policy = ScopePolicy(frozenset({"sensor.keep"}), frozenset({user.id}))
    adapter = SubscriptionAdapter(hass, policy)
    adapter.install()
    subscribe(connection)
    assert set(snapshot(output)) == {"sensor.keep"}
    assert adapter.managed_count == adapter.filtered_count == 1
    output.clear()
    hass.states.async_set("sensor.keep", "1")
    hass.states.async_set("sensor.drop", "1")
    await hass.async_block_till_done()
    assert len(output) == 1
    assert set(output[0]["event"]["c"]) == {"sensor.keep"}
    adapter.uninstall()


async def test_permissions_initial_live_and_revocation(
    hass, make_user, make_connection
):
    user = make_user(allowed={"sensor.allowed"})
    connection, output = make_connection(user)
    for entity_id in ("sensor.allowed", "sensor.denied"):
        hass.states.async_set(entity_id, "0")
    await hass.async_block_till_done()
    adapter = SubscriptionAdapter(
        hass,
        ScopePolicy(frozenset({"sensor.allowed", "sensor.denied"}), all_users=True),
    )
    adapter.install()
    subscribe(connection)
    assert set(snapshot(output)) == {"sensor.allowed"}
    output.clear()
    hass.states.async_set("sensor.denied", "1")
    hass.states.async_set("sensor.allowed", "1")
    await hass.async_block_till_done()
    assert len(output) == 1
    assert set(output[0]["event"]["c"]) == {"sensor.allowed"}
    user.groups = []
    output.clear()
    hass.states.async_set("sensor.allowed", "2")
    await hass.async_block_till_done()
    assert output == []
    adapter.uninstall()
    assert snapshot(output) == {}


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"entity_ids": ["sensor.other"]}, {"sensor.other"}),
        ({"entity_ids": []}, {"sensor.keep", "sensor.other", "light.other"}),
        ({"include": {"domains": ["light"]}}, {"light.other"}),
        ({"exclude": {"entities": ["sensor.keep"]}}, {"sensor.other", "light.other"}),
    ],
)
async def test_explicit_native_scopes(
    hass, make_user, make_connection, fields, expected
):
    connection, output = make_connection(make_user(admin=True))
    for entity_id in ("sensor.keep", "sensor.other", "light.other"):
        hass.states.async_set(entity_id, "0")
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    subscribe(connection, **fields)
    assert set(snapshot(output)) == expected
    assert adapter.managed_count == 0
    adapter.set_policy(replace(adapter.policy, enabled=False))
    assert len(output) == 2
    adapter.uninstall()


@pytest.mark.parametrize(
    "policy",
    [
        ScopePolicy(),
        ScopePolicy(frozenset({"sensor.keep"}), all_users=True, complete=False),
        ScopePolicy(frozenset({"sensor.keep"}), all_users=True, enabled=False),
        ScopePolicy(frozenset({"sensor.keep"})),
    ],
)
async def test_empty_incomplete_disabled_unselected_bypass(
    hass, make_user, make_connection, policy
):
    connection, output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.keep", "0")
    hass.states.async_set("sensor.other", "0")
    adapter = SubscriptionAdapter(hass, policy)
    adapter.install()
    subscribe(connection)
    assert set(snapshot(output)) == {"sensor.keep", "sensor.other"}
    assert adapter.filtered_count == 0
    adapter.uninstall()


async def test_target_changes_and_missing_entity_appearance(
    hass, make_user, make_connection
):
    user = make_user(admin=True)
    connection, output = make_connection(user)
    hass.states.async_set("sensor.other", "0")
    adapter = SubscriptionAdapter(hass, ScopePolicy(frozenset({"sensor.future"})))
    adapter.install()
    subscribe(connection)
    assert set(snapshot(output)) == {"sensor.other"}
    adapter.set_policy(replace(adapter.policy, user_ids=frozenset({user.id})))
    assert snapshot(output) == {}
    output.clear()
    hass.states.async_set("sensor.future", "1")
    await hass.async_block_till_done()
    assert set(snapshot(output)) == {"sensor.future"}
    output.clear()
    hass.states.async_remove("sensor.future")
    await hass.async_block_till_done()
    assert output[-1]["event"]["r"] == ["sensor.future"]
    adapter.uninstall()


async def test_scope_changes_queued_events_and_unload_with_real_js_client(
    hass, make_user, make_connection
):
    """Replay Core-generated packets into the pinned stock JS collection."""
    connection, output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.one", "0")
    hass.states.async_set("sensor.two", "0")
    await hass.async_block_till_done()
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.one"}), all_users=True)
    )
    adapter.install()
    steps = []

    def checkpoint(label, expected):
        steps.append({"label": label, "messages": list(output), "expected": expected})
        output.clear()

    subscribe(connection, msg_id=3)
    checkpoint("initial", {"sensor.one": "0"})
    hass.states.async_set("sensor.one", "queued-old")
    adapter.set_policy(replace(adapter.policy, entity_ids=frozenset({"sensor.two"})))
    await hass.async_block_till_done()
    checkpoint("shrink and queued callbacks", {"sensor.two": "0"})
    hass.states.async_set("sensor.two", "live")
    await hass.async_block_till_done()
    checkpoint("new listener delivers", {"sensor.two": "live"})
    adapter.set_policy(replace(adapter.policy, enabled=False))
    checkpoint("master bypass", {"sensor.one": "queued-old", "sensor.two": "live"})
    hass.states.async_set("sensor.transient", "1")
    await hass.async_block_till_done()
    checkpoint(
        "entity created while bypassed",
        {"sensor.one": "queued-old", "sensor.two": "live", "sensor.transient": "1"},
    )
    hass.states.async_remove("sensor.transient")
    adapter.set_policy(replace(adapter.policy, enabled=True))
    await hass.async_block_till_done()
    checkpoint("tighten after queued removal", {"sensor.two": "live"})
    adapter.set_policy(
        replace(adapter.policy, entity_ids=frozenset({"sensor.one", "sensor.two"}))
    )
    checkpoint("expand", {"sensor.one": "queued-old", "sensor.two": "live"})
    adapter.set_policy(replace(adapter.policy, complete=False))
    checkpoint(
        "scan failure bypass", {"sensor.one": "queued-old", "sensor.two": "live"}
    )
    adapter.set_policy(replace(adapter.policy, complete=True))
    checkpoint("scope restored", {"sensor.one": "queued-old", "sensor.two": "live"})
    adapter.uninstall()
    checkpoint(
        "unload restores native", {"sensor.one": "queued-old", "sensor.two": "live"}
    )
    hass.states.async_set("sensor.after_unload", "1")
    await hass.async_block_till_done()
    checkpoint(
        "native listener survives",
        {"sensor.one": "queued-old", "sensor.two": "live", "sensor.after_unload": "1"},
    )
    assert adapter.managed_count == 0
    for arguments in ([], ["--coalesced"]):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("client_protocol.mjs")), *arguments],
            input=json.dumps(steps),
            text=True,
            capture_output=True,
            timeout=15,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "11 checkpoints" in result.stdout


async def test_concurrent_connections_and_cleanup(hass, make_user, make_connection):
    selected = make_user(admin=True)
    first, first_output = make_connection(selected)
    second, second_output = make_connection(make_user())
    hass.states.async_set("sensor.keep", "0")
    hass.states.async_set("sensor.other", "0")
    baseline = hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0)
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), frozenset({selected.id}))
    )
    adapter.install()
    subscribe(first)
    subscribe(second)
    first_output.clear()
    second_output.clear()
    adapter.set_policy(replace(adapter.policy, enabled=False))
    assert set(snapshot(first_output)) == {"sensor.keep", "sensor.other"}
    assert second_output == []
    first.async_handle({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert adapter.managed_count == 1
    second.async_handle_close()
    assert adapter.managed_count == 0
    adapter.uninstall()
    adapter.uninstall()
    assert hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0) == baseline


async def test_scheduled_native_callback_from_retired_generation(
    hass, make_user, make_connection
):
    """Invoke a retained real Core callback after its listener is replaced."""
    connection, output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.old", "0")
    hass.states.async_set("sensor.new", "0")
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.old"}), all_users=True)
    )
    adapter.install()
    subscribe(connection)
    native_callback = next(
        job.target
        for job, _ in hass.bus._listeners[EVENT_STATE_CHANGED]
        if getattr(getattr(job.target, "func", None), "__name__", "")
        == "_forward_entity_changes"
    )
    old_state = hass.states.get("sensor.old")
    hass.states.async_set("sensor.old", "1")
    event = Event(
        EVENT_STATE_CHANGED,
        {
            "entity_id": "sensor.old",
            "old_state": old_state,
            "new_state": hass.states.get("sensor.old"),
        },
    )
    hass.loop.call_soon(native_callback, event)
    adapter.set_policy(replace(adapter.policy, entity_ids=frozenset({"sensor.new"})))
    output.clear()
    await hass.async_block_till_done()
    assert output == []
    adapter.uninstall()


async def test_invalid_request_still_uses_native_schema(
    hass, make_user, make_connection
):
    connection, output = make_connection(make_user())
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    subscribe(connection, entity_ids=["not an entity"])
    assert output[-1]["error"]["code"] == "invalid_format"
    assert adapter.managed_count == 0
    assert connection.subscriptions == {}
    adapter.uninstall()


async def test_handler_failure_rolls_back_all_staged_listeners(
    hass, make_user, make_connection
):
    first, first_output = make_connection(make_user(admin=True))
    second, second_output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.keep", "0")
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    subscribe(first)
    subscribe(second)
    first_output.clear()
    second_output.clear()
    baseline = hass.bus.async_listeners()
    original = adapter._original
    calls = 0

    def fail_after_listener(hass, connection, msg):
        nonlocal calls
        calls += 1
        original[0](hass, connection, msg)
        if calls == 2:
            raise RuntimeError("Injected failure after native subscription creation")

    adapter._original = (fail_after_listener, original[1])
    with pytest.raises(RuntimeError, match="Injected failure"):
        adapter.set_policy(replace(adapter.policy, enabled=False))
    assert adapter.policy.enabled
    assert adapter.filtered_count == 2
    assert first_output == second_output == []
    assert hass.bus.async_listeners() == baseline
    adapter._original = original
    hass.states.async_set("sensor.keep", "1")
    await hass.async_block_till_done()
    assert len(first_output) == len(second_output) == 1
    adapter.uninstall()


async def test_initial_handler_failure_leaks_no_listener(
    hass, make_user, make_connection
):
    connection, output = make_connection(make_user(admin=True))
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    baseline = hass.bus.async_listeners()
    original = adapter._original

    def fail(hass, connection, msg):
        original[0](hass, connection, msg)
        raise RuntimeError("Injected failure")

    adapter._original = (fail, original[1])
    subscribe(connection)
    assert output[-1]["success"] is False
    assert len(output) == 1
    assert connection.subscriptions == {}
    assert adapter.managed_count == 0
    assert hass.bus.async_listeners() == baseline
    adapter._original = original
    adapter.uninstall()


async def test_competing_replacement_is_preserved_on_unload(
    hass, make_user, make_connection
):
    original = hass.data[websocket_api.DOMAIN]["subscribe_entities"]
    connection, output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.keep", "0")
    hass.states.async_set("sensor.other", "0")
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    adapter.install()
    subscribe(connection)
    competitor = (lambda *_: None, original[1])
    hass.data[websocket_api.DOMAIN]["subscribe_entities"] = competitor
    with pytest.raises(CompatibilityError):
        adapter.set_policy(replace(adapter.policy, enabled=False))
    adapter.uninstall()
    assert hass.data[websocket_api.DOMAIN]["subscribe_entities"] is competitor
    assert set(snapshot(output)) == {"sensor.keep", "sensor.other"}


async def test_unload_restores_exact_original_and_reinstall(hass):
    original = hass.data[websocket_api.DOMAIN]["subscribe_entities"]
    adapter = SubscriptionAdapter(hass, ScopePolicy())
    adapter.install()
    adapter.uninstall()
    assert hass.data[websocket_api.DOMAIN]["subscribe_entities"] is original
    adapter.install()
    adapter.uninstall()


async def test_only_entity_subscription_command_changes(hass):
    table = hass.data[websocket_api.DOMAIN]
    before = dict(table)
    adapter = SubscriptionAdapter(hass, ScopePolicy())
    adapter.install()
    assert table.keys() == before.keys()
    for command in before:
        if command != "subscribe_entities":
            assert table[command] is before[command]
    assert table["subscribe_entities"][1] is before["subscribe_entities"][1]
    adapter.uninstall()


async def test_foreign_subscription_callback_preserved_on_unload(
    hass, make_user, make_connection
):
    connection, output = make_connection(make_user(admin=True))
    hass.states.async_set("sensor.keep", "0")
    baseline = hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0)
    adapter = SubscriptionAdapter(
        hass, ScopePolicy(frozenset({"sensor.keep"}), all_users=True)
    )
    adapter.install()
    subscribe(connection)
    foreign_callback = lambda: None
    connection.subscriptions[1] = foreign_callback
    with pytest.raises(CompatibilityError, match="managed listener"):
        adapter.set_policy(replace(adapter.policy, enabled=False))
    adapter.uninstall()
    assert connection.subscriptions[1] is foreign_callback
    assert adapter.managed_count == 0
    assert hass.bus.async_listeners().get(EVENT_STATE_CHANGED, 0) == baseline
    output.clear()
    hass.states.async_set("sensor.keep", "1")
    await hass.async_block_till_done()
    assert output == []


async def test_changed_native_schema_reports_compatibility_failure(hass, monkeypatch):
    import voluptuous as vol
    from homeassistant.components.websocket_api import commands

    native = commands.handle_subscribe_entities
    schema = vol.Schema({"id": int, "type": "subscribe_entities"})
    monkeypatch.setattr(native, "_ws_schema", schema)
    table = hass.data[websocket_api.DOMAIN]
    entry = (native, schema)
    table["subscribe_entities"] = entry
    with pytest.raises(CompatibilityError, match="validation changed"):
        SubscriptionAdapter(hass, ScopePolicy()).install()
    assert table["subscribe_entities"] is entry


@pytest.mark.parametrize(
    "problem", ["version", "missing", "shape", "handler", "schema"]
)
async def test_unsupported_adapter_does_not_change_command_table(
    hass, monkeypatch, problem
):
    from homeassistant import const as ha_const

    table = hass.data[websocket_api.DOMAIN]
    handler, schema = table["subscribe_entities"]
    if problem == "version":
        monkeypatch.setattr(ha_const, "__version__", "2026.10.0")
    elif problem == "missing":
        del table["subscribe_entities"]
    elif problem == "shape":
        table["subscribe_entities"] = [handler, schema]
    elif problem == "handler":
        table["subscribe_entities"] = (lambda *_: None, schema)
    else:
        table["subscribe_entities"] = (handler, False)
    before = dict(table)
    baseline = hass.bus.async_listeners()
    with pytest.raises(CompatibilityError):
        SubscriptionAdapter(hass, ScopePolicy()).install()
    assert table == before
    assert hass.bus.async_listeners() == baseline


def test_malformed_scope_rejected():
    with pytest.raises(ValueError):
        ScopePolicy(frozenset({"bad value"}), all_users=True)
