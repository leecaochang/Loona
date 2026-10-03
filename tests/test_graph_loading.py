"""Verify native config redaction, scoped policy events, assets, and HuiCard."""

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.components import frontend, websocket_api
from homeassistant.components.websocket_api import commands

from custom_components.loona.const import GRAPH_CONTEXT, GRAPH_SUBSCRIBE, VERSION
from custom_components.loona.graph_loading import async_register_frontend
from custom_components.loona.runtime import LoonaRuntime


@pytest.fixture
async def graph_runtime(loona_hass, make_entry, dashboards):
    """Exercise graph hooks through a fully started genuine Loona runtime."""
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    runtime = LoonaRuntime(loona_hass, entry)
    entry.runtime_data = runtime
    await runtime.async_start()
    assert runtime.graph_adapter is not None, runtime.graph_compatibility_problem
    yield runtime
    await runtime.async_stop()


async def test_native_bootstrap_and_redaction(graph_runtime, make_user, make_connection):
    user = make_user(admin=True)
    user.local_only = True
    connection, wire = make_connection(user)
    commands.handle_get_config(graph_runtime.hass, connection, {"id": 1})
    native = wire[-1]["result"]
    await graph_runtime.async_set_control("visible_first_graphs", True)
    connection.async_handle({"id": 2, "type": "get_config"})
    augmented = wire[-1]["result"]
    assert {key: value for key, value in augmented.items() if key != GRAPH_CONTEXT} == native
    assert "external_url" not in augmented
    context = augmented[GRAPH_CONTEXT]
    assert context["version"] == VERSION
    assert context["enabled"] is True
    assert context["motion"]["enabled"] is False
    assert context["motion"]["max_ms"] == 10000
    assert context["quiet_ms"] == 750
    assert context["dashboards"] == ["wall-panel"]
    assert "user_ids" not in json.dumps(context)
    assert set(context["profiles"]) == {
        "sensor", "custom:mini-graph-card", "custom:apexcharts-card"
    }
    connection.async_handle({"id": 3, "type": "get_config", "unexpected": True})
    assert wire[-1]["success"] is False


async def test_live_switches_targets_unsubscribe_and_unload(
    graph_runtime, make_user, make_connection
):
    user = make_user(admin=True)
    connection, wire = make_connection(user)
    connection.async_handle({"id": 1, "type": GRAPH_SUBSCRIBE})
    assert wire[-2] == {"id": 1, "type": "result", "success": True, "result": None}
    assert wire[-1]["event"]["enabled"] is False
    await graph_runtime.async_set_control("pause_animations_during_loading", True)
    assert wire[-1]["event"]["enabled"] is False
    assert wire[-1]["event"]["motion"]["enabled"] is True
    await graph_runtime.async_set_control("visible_first_graphs", True)
    assert wire[-1]["event"]["enabled"] is True
    before = len(wire)
    graph_runtime.notify()
    assert len(wire) == before
    await graph_runtime.async_set_control("entity_filtering", False)
    assert wire[-1]["event"]["enabled"] is True
    await graph_runtime.async_set_control("enabled", False)
    assert wire[-1]["event"]["enabled"] is False
    assert wire[-1]["event"]["motion"]["enabled"] is False
    await graph_runtime.async_set_control("enabled", True)
    assert wire[-1]["event"]["enabled"] is True
    graph_runtime.hass.config_entries.async_update_entry(
        graph_runtime.entry, options={"target_mode": "selected", "user_ids": ["other"]}
    )
    await graph_runtime.async_scan()
    assert wire[-1]["event"]["enabled"] is False
    assert wire[-1]["event"]["dashboards"] == []
    assert wire[-1]["event"]["motion"]["enabled"] is False
    graph_runtime.hass.config_entries.async_update_entry(
        graph_runtime.entry, options={"target_mode": "all", "dashboards": ["lovelace"]}
    )
    await graph_runtime.async_scan()
    assert wire[-1]["event"]["enabled"] is True
    assert wire[-1]["event"]["dashboards"] == ["lovelace"]
    other, other_wire = make_connection(make_user())
    other.async_handle({"id": 1, "type": GRAPH_SUBSCRIBE})
    other.async_handle({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    before = len(other_wire)
    await graph_runtime.async_stop()
    assert len(other_wire) == before
    assert wire[-1]["event"]["enabled"] is False
    assert wire[-1]["event"]["motion"]["enabled"] is False
    assert not graph_runtime.graph_adapter
    assert not graph_runtime._listeners
    connection.async_handle({"id": 2, "type": "get_config"})
    assert GRAPH_CONTEXT not in wire[-1]["result"]
    connection.async_handle({"id": 3, "type": "unsubscribe_events", "subscription": 1})
    assert wire[-1]["success"] is True


async def test_unknown_native_owners_preserved(loona_hass, make_entry, dashboards):
    table = loona_hass.data[websocket_api.DOMAIN]
    native = table["get_config"]
    foreign = (lambda *args: None, native[1])
    table["get_config"] = foreign
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    assert runtime.graph_adapter is None
    assert runtime.graph_compatibility_problem
    await runtime.async_stop()
    assert table["get_config"] is foreign
    table["get_config"] = native
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    await runtime.async_start()
    table["get_config"] = foreign
    await runtime.async_stop()
    assert table["get_config"] is foreign


async def test_unparseable_core_bypasses(loona_hass, make_entry, dashboards):
    native = loona_hass.data[websocket_api.DOMAIN]["get_config"]
    runtime = LoonaRuntime(loona_hass, make_entry({"dashboards": ["wall-panel"], "target_mode": "all"}))
    with patch("custom_components.loona.compatibility.ha_const.__version__", "unknown"):
        await runtime.async_start()
    assert runtime.graph_adapter is None
    assert loona_hass.data[websocket_api.DOMAIN]["get_config"] is native
    await runtime.async_stop()


async def test_native_static_asset_and_module_reload(loona_hass, frontend_http):
    url = f"/loona/graph-loading.js?v={VERSION}"
    manager = loona_hass.data[frontend.DATA_EXTRA_MODULE_URL]
    remove = await async_register_frontend(loona_hass)
    assert manager.urls == {url}
    remove()
    assert not manager.urls
    remove = await async_register_frontend(loona_hass)
    assert manager.urls == {url}
    async with TestClient(TestServer(frontend_http.app)) as client:
        response = await client.get(url)
        assert response.status == 200
        assert response.content_type in {"text/javascript", "application/javascript"}
        assert await response.text() == Path("custom_components/loona/frontend/graph-loading.js").read_text()
        response = await client.get(f"/loona/startup-motion.js?v={VERSION}")
        assert response.status == 200
        assert response.content_type in {"text/javascript", "application/javascript"}
        assert await response.text() == Path("custom_components/loona/frontend/startup-motion.js").read_text()
    remove()
    assert not manager.urls


@pytest.mark.parametrize("script", ["graph_loading.mjs", "graph_loading_bootstrap.mjs"])
def test_genuine_hui_card_scheduling(script):
    """Use native HuiCard and Lit to expose lifecycle and editor assumptions."""
    result = subprocess.run(
        ["node", str(Path("tests") / script)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("hook", ["_loadElement", "_updateElement", "_setElementVisibility"])
def test_missing_native_browser_hook_preserves_original_methods(hook):
    result = subprocess.run(
        ["node", "tests/graph_loading.mjs", hook], capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Missing native hook preserves ordinary graph loading" in result.stdout


def test_missing_native_container_falls_back_and_recovers_when_loaded():
    result = subprocess.run(
        ["node", "tests/graph_loading_bootstrap.mjs", "missing-container"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
