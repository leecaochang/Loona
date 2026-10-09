"""Verify retained snapshots and native current-dashboard live subscriptions."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from homeassistant.const import EVENT_STATE_CHANGED

from custom_components.loona.runtime import LoonaRuntime
from custom_components.loona.dependencies import DiscoveryContext, discover_views
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter
from tests.test_panels import command
from tests.test_websocket import snapshot, subscribe


async def test_retained_union_with_stock_client_navigation_rules_removal_and_unload(hass, make_user, make_connection):
    connection, output = make_connection(make_user(allowed={"sensor.one", "sensor.two", "sensor.rule", "sensor.later"}))
    for entity in ("sensor.one", "sensor.two", "sensor.rule", "sensor.denied"):
        hass.states.async_set(entity, "0")
    await hass.async_block_till_done()
    live = frozenset({"sensor.one", "sensor.rule"})
    adapter = SubscriptionAdapter(hass, ScopePolicy(frozenset({"sensor.one", "sensor.two", "sensor.rule", "sensor.denied"}), all_users=True),
                                  delivery_scope=lambda connection, retained: live)
    adapter.install()
    baseline = hass.bus.async_listeners()[EVENT_STATE_CHANGED]
    steps = []
    def checkpoint(label, expected):
        steps.append({"label":label, "messages":list(output), "expected":expected})
        output.clear()
    subscribe(connection, msg_id=3)
    assert len([row for row in output if "a" in row.get("event", {})]) == 1
    assert hass.bus.async_listeners()[EVENT_STATE_CHANGED] == baseline + 1
    checkpoint("one complete permission-safe initial union", {"sensor.one":"0", "sensor.two":"0", "sensor.rule":"0"})
    hass.states.async_set("sensor.two", "background")
    hass.states.async_set("sensor.one", "visible")
    hass.states.async_set("sensor.rule", "pinned")
    hass.states.async_set("sensor.denied", "private")
    await hass.async_block_till_done()
    checkpoint("only delivery and explicit rules change", {"sensor.one":"visible", "sensor.two":"0", "sensor.rule":"pinned"})
    live = frozenset({"sensor.two", "sensor.rule"})
    adapter.refresh_connection(connection)
    assert not any("r" in row.get("event", {}) for row in output)
    checkpoint("navigation refreshes without removing retained IDs", {"sensor.one":"visible", "sensor.two":"background", "sensor.rule":"pinned"})
    hass.states.async_set("sensor.one", "stale")
    await hass.async_block_till_done()
    checkpoint("inactive values remain cached", {"sensor.one":"visible", "sensor.two":"background", "sensor.rule":"pinned"})
    live = adapter.policy.entity_ids
    adapter.refresh_connection(connection)
    checkpoint("expanded interface refreshes the union", {"sensor.one":"stale", "sensor.two":"background", "sensor.rule":"pinned"})
    live = frozenset({"sensor.two", "sensor.rule"})
    adapter.refresh_connection(connection)
    checkpoint("closing interface preserves all IDs", {"sensor.one":"stale", "sensor.two":"background", "sensor.rule":"pinned"})
    hass.states.async_set("sensor.later", "new")
    adapter.set_policy(replace(adapter.policy, entity_ids=adapter.policy.entity_ids | {"sensor.later"}))
    await hass.async_block_till_done()
    checkpoint("new union dependencies get a complete snapshot", {"sensor.one":"stale", "sensor.two":"background", "sensor.rule":"pinned", "sensor.later":"new"})
    hass.states.async_remove("sensor.one")
    adapter.refresh_connection(connection)
    # A retained-only deletion is reconciled on the next restaging change.
    live = frozenset({"sensor.rule"})
    adapter.refresh_connection(connection)
    await hass.async_block_till_done()
    checkpoint("retained deletions reconcile", {"sensor.two":"background", "sensor.rule":"pinned", "sensor.later":"new"})
    adapter.uninstall()
    checkpoint("unload restores native values", {"sensor.two":"background", "sensor.rule":"pinned", "sensor.later":"new"})
    for args in ([], ["--coalesced"]):
        result = subprocess.run(["node", str(Path(__file__).with_name("client_protocol.mjs")), *args], input=json.dumps(steps), text=True, capture_output=True, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr


async def test_retained_snapshot_live_handler_failure_is_atomic(hass, make_user, make_connection):
    connection, output = make_connection(make_user(admin=True))
    for entity in ("sensor.one", "sensor.two"):
        hass.states.async_set(entity, "0")
    adapter = SubscriptionAdapter(hass, ScopePolicy(frozenset({"sensor.one", "sensor.two"}), all_users=True), delivery_scope=lambda connection, retained: frozenset({"sensor.one"}))
    adapter.install()
    baseline = hass.bus.async_listeners()
    original = adapter._original
    calls = 0
    def fail(hass, relay, message):
        nonlocal calls
        calls += 1
        original[0](hass, relay, message)
        if calls == 2:
            raise RuntimeError("Live listener failed after union snapshot")
    adapter._original = (fail, original[1])
    subscribe(connection)
    assert output[-1]["success"] is False and len(output) == 1
    assert not connection.subscriptions and not adapter.managed_count
    assert hass.bus.async_listeners() == baseline
    adapter._original = original
    adapter.uninstall()


@pytest.fixture
async def dashboard_runtime(loona_hass, make_entry, dashboards):
    for entity in ("sensor.wall", "sensor.overview", "sensor.rule", "sensor.outside", "person.interface"):
        loona_hass.states.async_set(entity, "0")
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards":["wall-panel", "lovelace"], "target_mode":"all", "extra_entities":["sensor.rule"]}))
    runtime.entry.runtime_data = runtime
    await runtime.async_start()
    yield runtime
    await runtime.async_stop()


async def test_runtime_opt_in_capability_dialogs_editors_navigation_and_rules(dashboard_runtime, make_user, make_connection):
    runtime = dashboard_runtime
    connection, output = make_connection(make_user(admin=True))
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", live_dashboard=True)
    command(connection, output, "subscribe_entities")
    retained = {"sensor.wall", "sensor.overview", "sensor.rule", "person.interface"}
    assert set(snapshot(output)) == retained
    assert runtime.adapter._records[(connection, 2)].scope == frozenset(retained)
    await runtime.async_set_control("current_dashboard_updates", True)
    assert runtime.adapter._records[(connection, 2)].scope == frozenset({"sensor.wall", "sensor.rule", "person.interface"})
    for expanded in (True, False):
        command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True, expanded=expanded)
        assert runtime.adapter._records[(connection, 2)].scope == (frozenset(retained) if expanded else frozenset({"sensor.wall", "sensor.rule", "person.interface"}))
    command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True, expanded=True, editing=True)
    assert runtime.adapter._records[(connection, 2)].scope is None, "The native editor sees every entity"
    assert "sensor.outside" in snapshot(output)
    command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True)
    assert runtime.adapter._records[(connection, 2)].scope == frozenset({"sensor.wall", "sensor.rule", "person.interface"}), "Filtering resumes after editing"
    command(connection, output, "loona/panel", dashboard="lovelace", live_dashboard=True)
    assert runtime.adapter._records[(connection, 2)].scope == frozenset({"sensor.overview", "sensor.rule", "person.interface"})
    command(connection, output, "loona/panel", dashboard="config", live_dashboard=True)
    assert runtime.adapter._records[(connection, 2)].scope is None
    assert "sensor.outside" in snapshot(output)
    command(connection, output, "loona/panel", dashboard="wall-panel")
    assert runtime.adapter._records[(connection, 2)].scope == frozenset(retained), "Old reporters remain union scoped"
    command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True)
    await runtime.async_set_control("entity_filtering", False)
    assert runtime.adapter._records[(connection, 2)].scope is None


async def test_runtime_restricted_users_missing_scope_and_explicit_feeds(dashboard_runtime, make_user, make_connection):
    runtime = dashboard_runtime
    await runtime.async_set_control("current_dashboard_updates", True)
    connection, output = make_connection(make_user(allowed={"sensor.wall", "sensor.overview"}))
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", live_dashboard=True)
    command(connection, output, "subscribe_entities")
    assert set(snapshot(output)) == {"sensor.wall", "sensor.overview"}
    command(connection, output, "subscribe_entities", entity_ids=[])
    assert runtime.adapter.managed_count == 1
    runtime.hass.states.async_set("sensor.overview", "fresh")
    await runtime.hass.async_block_till_done()
    assert [row["id"] for row in output if "sensor.overview" in row.get("event", {}).get("c", {})] == [3]
    command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True, expanded=True)
    assert snapshot(output)["sensor.overview"]["s"] == "fresh"
    assert all("sensor.rule" not in row.get("event", {}).get("a", {}) for row in output)
    runtime.dashboard_live_entities.pop("wall-panel")
    command(connection, output, "loona/panel", dashboard="wall-panel", live_dashboard=True, expanded=False)
    assert runtime.adapter._records[(connection, 2)].scope == runtime.entity_ids
    connection.async_handle_close()
    assert not runtime.adapter.managed_count and not runtime.panel_context._connections


def test_view_discovery_shared_dependencies_groups_and_native_route_collisions():
    context = DiscoveryContext(groups={"group.shared": frozenset({"sensor.shared"})})
    config = {"badges": [{"entity": "group.shared"}], "views": [
        {"path": "1", "cards": [{"type": "entity", "entity": "sensor.one"}]},
        {"path": "other", "subview": True, "cards": [{"type": "entity", "entity": "sensor.two"}]},
        {"path": "other", "cards": [{"type": "entity", "entity": "sensor.three"}]},
    ]}
    shared = {"group.shared", "sensor.shared"}
    plans = discover_views(config, context)
    assert plans["0"] == plans["1"] == frozenset(shared | {"sensor.one"}), "Native first match wins over numeric index"
    assert plans["other"] == frozenset(shared | {"sensor.two"}), "Native first duplicate path wins"
    assert plans["2"] == frozenset(shared | {"sensor.three"})
    assert "" not in plans and "missing" not in plans
    for numeric_path in ("01", "1.0", "0x1", "1e0", " ", "\ufeff1"):
        config["views"][2]["path"] = numeric_path
        assert numeric_path not in discover_views(config, context), "Ambiguous JS numeric coercion must retain dashboard delivery"
    assert discover_views({"strategy": {"type": "custom:dynamic"}, **config}, context) == {}
    assert discover_views({"views": [None]}, context) == {}


async def test_runtime_tabs_retained_values_navigation_fallback_and_rescan(dashboard_runtime, dashboards, make_user, make_connection):
    runtime = dashboard_runtime
    for entity in ("sensor.hidden", "sensor.shared"):
        runtime.hass.states.async_set(entity, "0")
    config = {"header": {"entity": "sensor.shared"}, "views": [
        {"path": "main", "cards": [{"type": "entity", "entity": "sensor.wall"}]},
        {"path": "hidden", "visible": False, "subview": True,
         "cards": [{"type": "entity", "entity": "sensor.hidden"}]},
    ]}
    await dashboards["wall-panel"].async_save(config)
    await runtime.async_scan(force=True)
    await runtime.async_set_control("current_dashboard_updates", True)
    connection, output = make_connection(make_user(admin=True))
    command(connection, output, "loona/subscribe_panel", dashboard="wall-panel", view="main", live_dashboard=True)
    command(connection, output, "subscribe_entities")
    record = lambda: runtime.adapter._records[(connection, 2)]
    pinned = {"sensor.shared", "sensor.rule", "person.interface"}
    retained = pinned | {"sensor.wall", "sensor.hidden", "sensor.overview"}
    assert set(snapshot(output)) == retained
    assert record().scope == frozenset(pinned | {"sensor.wall"})
    output.clear()
    runtime.hass.states.async_set("sensor.hidden", "background")
    runtime.hass.states.async_set("sensor.wall", "visible")
    await runtime.hass.async_block_till_done()
    assert "sensor.hidden" not in str(output) and "sensor.wall" in str(output)
    for route in ("hidden", "1"):
        command(connection, output, "loona/panel", dashboard="wall-panel", view=route, live_dashboard=True)
        assert record().scope == frozenset(pinned | {"sensor.hidden"})
    assert snapshot(output)["sensor.hidden"]["s"] == "background"
    assert not any("r" in row.get("event", {}) for row in output)
    for route in (None, "missing", "01"):
        command(connection, output, "loona/panel", dashboard="wall-panel", view=route, live_dashboard=True)
        assert record().scope == frozenset(pinned | {"sensor.wall", "sensor.hidden"})
    for expanded in (True, False):
        command(connection, output, "loona/panel", dashboard="wall-panel", view="0", live_dashboard=True, expanded=expanded)
        assert record().scope == (frozenset(retained) if expanded else frozenset(pinned | {"sensor.wall"}))
    # Saving a changed configuration replaces view plans with the same atomic union.
    config["views"][0]["cards"][0]["entity"] = "sensor.hidden"
    await dashboards["wall-panel"].async_save(config)
    await runtime.async_scan(force=True)
    assert record().scope == frozenset(pinned | {"sensor.hidden"})
    assert "sensor.wall" not in record().retained_scope
