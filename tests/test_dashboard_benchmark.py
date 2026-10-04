"""Exercise benchmark ownership, native delivery and safe removal with Core objects."""

from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.loona.benchmark import BenchmarkManager, _SAMPLE, websocket_benchmark
from custom_components.loona.const import BENCHMARK_COMMAND, DOMAIN
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter

CARD = {"type": "custom:loona-benchmark-card"}


@pytest.fixture
async def benchmark_runtime(loona_hass, dashboards):
    await dashboards["wall-panel"].async_save({"views": [{"path": "main", "cards": [CARD, {"type": "entity", "entity": "sensor.wall"}]}]})
    runtime = SimpleNamespace(hass=loona_hass, settings={"dashboards": ["wall-panel"]}, controls={"enabled": True},
                              bootstrap_installed=True, resource_preview={"resources": []}, _panel_changed=Mock())
    runtime.benchmark = BenchmarkManager(runtime)
    loona_hass.data[DOMAIN] = runtime
    websocket_api.async_register_command(loona_hass, websocket_benchmark)
    yield runtime
    runtime.benchmark.stop()


def sample(seconds=3):
    return dict(ready_ms=500, duration_ms=seconds * 1000, initial_entities=1, initial_bytes=20,
                registry_bytes=0, updates=0, update_bytes=0, loaf_supported=False, startup_blocking_ms=0,
                blocking_ms=0, startup_frames=0, frames=0, resources=[], scripts=[], issues=[], browser="Test", viewport=[1000, 800])


async def test_owner_connection_local_native_order_and_cleanup(benchmark_runtime, make_connection, make_user):
    manager = benchmark_runtime.benchmark
    user = make_user(admin=True)
    owner, output = make_connection(user)
    other, _ = make_connection(user)
    stranger, _ = make_connection(make_user(admin=True))
    result = await manager.execute(owner, dict(action="start", dashboard="wall-panel", view="main"))
    token = result["token"]
    assert [row["mode"] for row in result["sequence"]] == ["native", "loona", "native", "loona", "loona", "native", "native", "loona"]
    with pytest.raises(ValueError, match="unavailable"):
        await manager.execute(stranger, dict(action="status", token=token))
    await manager.execute(owner, dict(id=40, action="attach", token=token, dashboard="wall-panel", view="main", index=0))
    assert manager.native(owner) and not manager.native(other)
    with pytest.raises(ValueError, match="already attached"):
        await manager.execute(other, dict(id=40, action="attach", token=token, dashboard="wall-panel", view="main", index=0))
    with pytest.raises(ValueError, match="no longer attached"):
        await manager.execute(other, dict(action="pass", token=token, index=0, sample=sample()))
    # Native command permissions are still applied by Core. Only the owning connection bypasses the scope.
    benchmark_runtime.hass.states.async_set("sensor.wall", "1")
    benchmark_runtime.hass.states.async_set("sensor.other", "1")
    adapter = SubscriptionAdapter(benchmark_runtime.hass, ScopePolicy(frozenset({"sensor.wall"}), all_users=True),
                                  dashboard_active=lambda connection: not manager.native(connection))
    adapter.install()
    try:
        owner.async_handle({"id": 1, "type": "subscribe_entities"})
        other.async_handle({"id": 1, "type": "subscribe_entities"})
        assert "sensor.other" in output[-1]["event"]["a"]
        report = await manager.execute(owner, dict(action="pass", token=token, index=0, sample=sample()))
        assert report["index"] == 1 and not manager.native(owner)
        assert benchmark_runtime.controls == {"enabled": True}
        await manager.execute(other, dict(id=40, action="attach", token=token, dashboard="wall-panel", view="main", index=1))
        assert not manager.native(other)
        other.subscriptions[40]()
        assert manager.runs[token].connection is None
        await manager.execute(owner, dict(action="cancel", token=token))
        assert not manager.bound
    finally:
        adapter.uninstall()


async def test_changed_configuration_expiry_and_admin_gate(benchmark_runtime, make_connection, make_user, dashboards):
    manager = benchmark_runtime.benchmark
    owner, _ = make_connection(make_user(admin=True))
    guest, output = make_connection(make_user())
    guest.async_handle({"id": 1, "type": BENCHMARK_COMMAND, "action": "start", "dashboard": "wall-panel", "view": "main"})
    await benchmark_runtime.hass.async_block_till_done()
    assert output[-1]["error"]["code"] == "unauthorized"
    result = await manager.execute(owner, dict(action="start", dashboard="wall-panel", view="main"))
    request = dict(id=5, action="attach", token=result["token"], dashboard="wall-panel", view="main", index=0)
    benchmark_runtime.controls["enabled"] = False
    with pytest.raises(ValueError, match="settings changed"):
        await manager.execute(owner, request)
    benchmark_runtime.controls["enabled"] = True
    await manager.execute(owner, request)
    manager.runs[result["token"]].expires = 0
    assert not manager.native(owner)
    with pytest.raises(ValueError, match="expired"):
        await manager.execute(owner, dict(action="status", token=result["token"]))
    assert not manager.bound
    result = await manager.execute(owner, dict(action="start", dashboard="wall-panel", view="main"))
    await dashboards["wall-panel"].async_save({"views": [{"path": "main", "cards": [CARD]}]})
    with pytest.raises(ValueError, match="Dashboard changed"):
        await manager.execute(owner, {**request, "token": result["token"]})


async def test_remove_exact_unique_instance_preserves_latest(benchmark_runtime, dashboards, make_connection, make_user):
    manager = benchmark_runtime.benchmark
    owner, _ = make_connection(make_user(admin=True))
    board = dashboards["wall-panel"]
    config = await board.async_load(False)
    config["title"] = "Latest edit"
    config["views"][0]["cards"].append({"type": "markdown", "content": "Preserve me"})
    await board.async_save(config)
    result = await manager.execute(owner, dict(action="remove", dashboard="wall-panel", view="main", card=CARD))
    saved = await board.async_load(False)
    assert result == {"removed": True} and saved["title"] == "Latest edit"
    assert saved["views"][0]["cards"][-1]["content"] == "Preserve me"
    saved["views"][0]["cards"] += [CARD, CARD]
    await board.async_save(saved)
    with pytest.raises(ValueError, match="uniquely"):
        await manager.execute(owner, dict(action="remove", dashboard="wall-panel", view="main", card=CARD))
    assert (await board.async_load(False)) == saved


def test_bounded_readings_and_shipped_card():
    for patch in ({"duration_ms": float("nan")}, {"updates": True}, {"resources": [{"source": "x" * 513, "bytes": None, "cached": False, "before_ready": False}]}):
        with pytest.raises(vol.Invalid):
            _SAMPLE({**sample(), **patch})
    result = subprocess.run(["node", str(Path(__file__).with_name("dashboard_benchmark.mjs"))], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
