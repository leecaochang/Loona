"""Authorize bounded browser benchmarks without editing ordinary dashboard settings."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
from secrets import token_hex
from time import monotonic
from typing import Any, TYPE_CHECKING

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import __version__ as CORE_VERSION
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (DOMAIN, VERSION, BENCHMARK_COMMAND, BENCHMARK_PAIRS,
                    BENCHMARK_SECONDS, BENCHMARK_READY_MS, BENCHMARK_CACHE_READ_MS, BENCHMARK_SESSION_SECONDS,
                    BENCHMARK_SESSION_LIMIT, BENCHMARK_RESOURCE_LIMIT, BENCHMARK_WARMUP_SECONDS,
                    BENCHMARK_SCRIPT_LIMIT, BENCHMARK_HISTORY_LIMIT, BENCHMARK_RETRY_LIMIT,
                    CONF_DASHBOARD_CARDS, STATISTICS_DASHBOARD)
from .dashboard import dashboard_objects, dashboard_titles, load_dashboard

if TYPE_CHECKING:
    from .runtime import LoonaRuntime


def digest(value: Any) -> str:
    """Compare configuration content rather than mutable object identity."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def number(value: Any) -> float:
    """Accept finite, nonnegative readings only within a bounded measurement."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1_000_000_000:
        raise vol.Invalid("Invalid benchmark reading")
    return float(value)


_SAMPLE = vol.Schema({
    vol.Required("ready_ms"): vol.Any(None, number),
    vol.Required("duration_ms"): number,
    vol.Required("initial_entities"): number,
    vol.Required("initial_bytes"): number,
    vol.Required("registry_bytes"): number,
    vol.Required("updates"): number,
    vol.Required("update_bytes"): number,
    vol.Required("loaf_supported"): bool,
    vol.Required("startup_blocking_ms"): number,
    vol.Required("blocking_ms"): number,
    vol.Required("startup_frames"): number,
    vol.Required("frames"): number,
    vol.Required("resources"): vol.All([{
        vol.Required("source"): vol.All(str, vol.Length(max=512)),
        vol.Required("bytes"): vol.Any(None, number),
        vol.Required("before_ready"): bool,
        vol.Required("cached"): bool,
    }], vol.Length(max=BENCHMARK_RESOURCE_LIMIT)),
    vol.Required("scripts"): vol.All([{
        vol.Required("source"): vol.All(str, vol.Length(max=512)),
        vol.Required("phase"): vol.In(("startup", "observation")),
        vol.Required("duration_ms"): number,
    }], vol.Length(max=BENCHMARK_SCRIPT_LIMIT)),
    vol.Required("issues"): vol.All([vol.In(("readiness_timeout", "card_error", "resource_error", "observer_limit"))], vol.Length(max=4)),
    vol.Required("browser"): vol.All(str, vol.Length(max=256)),
    vol.Required("viewport"): vol.All([number], vol.Length(min=2, max=2)),
})


def resolve_view(config: dict[str, Any], path: str) -> dict[str, Any]:
    """Follow native first-match precedence for named and numeric view routes."""
    for index, view in enumerate(config.get("views", [])):
        if isinstance(view, dict) and (view.get("path") == path or str(index) == path):
            return view
    if not path and config.get("views"):
        return config["views"][0]
    raise ValueError("Tab is unavailable. Open the tab containing the benchmark card.")


def remove_instance(view: dict[str, Any], card: dict[str, Any]) -> bool:
    """Remove one exact card from native lists; refuse ambiguous or generated shapes."""
    matches: list[tuple[list[Any], int]] = []

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        for key in ("cards", "sections"):
            rows = node.get(key)
            if not isinstance(rows, list):
                continue
            for index, item in enumerate(rows):
                if key == "cards" and item == card:
                    matches.append((rows, index))
                else:
                    visit(item)

    visit(view)
    if len(matches) != 1:
        return False
    rows, index = matches[0]
    rows.pop(index)
    return True


@dataclass
class BenchmarkRun:
    """A token authorizes only its creator, target tab and ordered page visits."""

    user_id: str
    dashboard: str
    view: str
    settings_hash: str
    dashboard_hash: str
    controls: dict[str, bool]
    settings: dict[str, Any]
    expires: float
    sequence: list[dict[str, Any]]
    names: dict[str, Any] = field(default_factory=dict)
    index: int = 0
    samples: list[dict[str, Any]] = field(default_factory=list)
    connection: Any = None
    remove_expiry: Any = None
    status: str = "running"
    retries: int = 0


class BenchmarkManager:
    """Keep bypasses connection-local and retire them on close, expiry or unload."""

    def __init__(self, runtime: "LoonaRuntime") -> None:
        self.runtime = runtime
        self.runs: dict[str, BenchmarkRun] = {}
        self.bound: dict[Any, str] = {}
        self.lock = asyncio.Lock()

    def native(self, connection: Any) -> bool:
        """A native pass retains HA permissions while suppressing Loona controls."""
        run = self.runs.get(self.bound.get(connection, ""))
        return bool(run and run.status == "running" and run.expires > monotonic()
                    and run.index < len(run.sequence) and run.sequence[run.index]["mode"] == "native")

    def fingerprint(self) -> str:
        return digest([self.runtime.settings, self.runtime.controls, self.runtime.resource_preview.get("resources", [])])

    def get(self, token: str, user_id: str) -> BenchmarkRun:
        run = self.runs.get(token)
        if run is None or run.user_id != user_id:
            raise ValueError("Benchmark session is unavailable. Start over.")
        if run.status == "running" and run.expires <= monotonic():
            self.cancel(token)
            raise ValueError("Benchmark session expired. Start over.")
        return run

    @callback
    def release(self, run: BenchmarkRun) -> None:
        connection = run.connection
        if connection is not None:
            self.bound.pop(connection, None)
            run.connection = None
            self.runtime._panel_changed(connection)

    @callback
    def cancel(self, token: str) -> None:
        run = self.runs.get(token)
        if run:
            run.status = "cancelled"
            self.release(run)
            if run.remove_expiry:
                run.remove_expiry()
                run.remove_expiry = None

    def stop(self) -> None:
        for token in tuple(self.runs):
            self.cancel(token)
        self.runs.clear()

    def report(self, run: BenchmarkRun) -> dict[str, Any]:
        return {"version": VERSION, "status": run.status, "index": run.index,
                "sequence": run.sequence, "seconds": BENCHMARK_WARMUP_SECONDS if run.index < len(run.sequence) and run.sequence[run.index]["warmup"] else BENCHMARK_SECONDS,
                "ready_ms": BENCHMARK_READY_MS, "cache_read_ms": BENCHMARK_CACHE_READ_MS, "session_seconds": BENCHMARK_SESSION_SECONDS, "history_limit": BENCHMARK_HISTORY_LIMIT,
                "controls": run.controls, "settings": run.settings, **run.names,
                "completed_at": dt_util.utcnow().isoformat() if run.status == "complete" else None,
                "samples": run.samples, "core_version": CORE_VERSION,
                "resource_urls": [row["url"] for row in self.runtime.resource_preview.get("resources", [])]}

    async def validate(self, run: BenchmarkRun) -> None:
        if run.status != "running":
            raise ValueError("Benchmark is no longer running. Start over.")
        if run.settings_hash != self.fingerprint():
            raise ValueError("Loona settings changed during testing. Start over.")
        config = await load_dashboard(self.runtime.hass, run.dashboard)
        if digest(config) != run.dashboard_hash:
            raise ValueError("Dashboard changed during testing. Start over.")

    async def execute(self, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]:
        action = msg["action"]
        user_id = connection.user.id
        if action in {"start", "remove"}:
            dashboard, path = msg["dashboard"], msg["view"]
            board = dashboard_objects(self.runtime.hass).get(dashboard)
            if board is None:
                raise ValueError("Dashboard is unavailable. Refresh this page.")
            config = await load_dashboard(self.runtime.hass, dashboard)
            view = resolve_view(config, path)
            if action == "remove":
                card = msg["card"]
                if type(board) is not LovelaceStorage or card.get("type") != "custom:loona-benchmark-card":
                    raise ValueError("Remove this card manually in the dashboard editor or YAML source.")
                updated = deepcopy(config)
                if not remove_instance(resolve_view(updated, path), card):
                    raise ValueError("This card cannot be uniquely identified. Remove it manually.")
                if digest(await board.async_load(False)) != digest(config):
                    raise ValueError("Dashboard changed. Refresh before removing the card.")
                if dashboard == STATISTICS_DASHBOARD:
                    remaining = await self.runtime.statistics_card.remove_benchmark(config)
                    if remaining is not None:
                        options = {**self.runtime.entry.options, CONF_DASHBOARD_CARDS: list(remaining)}
                        if list(remaining) == self.runtime.entry.data.get(CONF_DASHBOARD_CARDS):
                            options.pop(CONF_DASHBOARD_CARDS, None)
                        self.runtime.hass.config_entries.async_update_entry(self.runtime.entry, options=options)
                        await self.runtime.async_scan()
                        await self.runtime.async_update_statistics_card()
                        return {"removed": True}
                await board.async_save(updated)
                return {"removed": True}
            if self.runtime.bootstrap_installed is not True:
                raise ValueError("Early startup measurement is unavailable. Check Loona diagnostics and reload.")
            if not any_instance(view):
                raise ValueError("Add the benchmark card to this tab before starting.")
            for token, previous in tuple(self.runs.items()):
                if previous.user_id == user_id or previous.status != "running":
                    self.cancel(token)
                    self.runs.pop(token)
            if len(self.runs) >= BENCHMARK_SESSION_LIMIT:
                raise ValueError("Too many benchmark sessions. Try again later.")
            sequence = [{"mode": mode, "warmup": True} for mode in ("native", "loona")]
            for pair in range(BENCHMARK_PAIRS):
                sequence.extend({"mode": mode, "warmup": False} for mode in
                                (("native", "loona") if pair % 2 == 0 else ("loona", "native")))
            run = BenchmarkRun(user_id, dashboard, path, self.fingerprint(), digest(config),
                               dict(self.runtime.controls), deepcopy(self.runtime.settings), monotonic() + BENCHMARK_SESSION_SECONDS, sequence)
            titles = dashboard_titles(self.runtime.hass)
            accounts = await self.runtime.hass.auth.async_get_users() if run.settings.get("user_ids") else []
            run.names = {"dashboard_title": titles.get(dashboard, dashboard),
                         "view_title": view.get("title") or view.get("path") or str(config["views"].index(view) + 1),
                         "names": {"dashboards": titles, "user_ids": {user.id: user.name or user.id for user in accounts}}}
            token = token_hex(32)
            self.runs[token] = run
            run.remove_expiry = async_call_later(self.runtime.hass, BENCHMARK_SESSION_SECONDS,
                                                lambda _: self._expire(token))
            return {**self.report(run), "token": token}
        run = self.get(msg["token"], user_id)
        if action == "cancel":
            self.cancel(msg["token"])
        elif action == "attach":
            await self.validate(run)
            if (msg["dashboard"], msg["view"], msg["index"]) != (run.dashboard, run.view, run.index):
                raise ValueError("Benchmark route or pass changed. Start over.")
            if run.connection is not None or connection in self.bound:
                raise ValueError("Benchmark is already attached to a browser. Start over.")
            run.connection = connection
            self.bound[connection] = msg["token"]
            connection.subscriptions[msg["id"]] = lambda: self.release(run) if run.connection is connection else None
        elif action == "pass":
            await self.validate(run)
            if run.connection is not connection or msg["index"] != run.index:
                raise ValueError("Benchmark pass is no longer attached. Start over.")
            sample = _SAMPLE(msg["sample"])
            seconds = BENCHMARK_WARMUP_SECONDS if run.sequence[run.index]["warmup"] else BENCHMARK_SECONDS
            if not seconds * 900 <= sample["duration_ms"] <= seconds * 1500:
                raise ValueError("Observation duration was interrupted. Repeat the benchmark.")
            run.samples.append({**sample, **run.sequence[run.index]})
            run.index += 1
            self.release(run)
            if run.index == len(run.sequence):
                run.status = "complete"
                if run.remove_expiry:
                    run.remove_expiry()
                    run.remove_expiry = None
        elif action == "retry":
            if run.connection is not connection or msg["index"] != run.index or run.retries >= BENCHMARK_RETRY_LIMIT:
                self.cancel(msg["token"])
                raise ValueError("Too many interrupted passes. Keep the page visible and start over.")
            run.retries += 1
            self.release(run)
        return self.report(run)

    @callback
    def _expire(self, token: str) -> None:
        self.cancel(token)
        self.runs.pop(token, None)


def any_instance(view: dict[str, Any]) -> bool:
    """Search configured card containers, including conditional wrappers."""
    if view.get("type") == "custom:loona-benchmark-card":
        return True
    for key in ("cards", "sections"):
        rows = view.get(key)
        if isinstance(rows, list) and any(any_instance(item) for item in rows if isinstance(item, dict)):
            return True
    card = view.get("card")
    return isinstance(card, dict) and any_instance(card)


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): BENCHMARK_COMMAND,
    vol.Required("action"): vol.In(("start", "attach", "pass", "retry", "cancel", "status", "remove")),
    vol.Optional("token", default=""): vol.All(str, vol.Length(max=64)),
    vol.Optional("dashboard", default=""): vol.All(str, vol.Length(max=128)),
    vol.Optional("view", default=""): vol.All(str, vol.Length(max=255)),
    vol.Optional("index", default=0): vol.All(int, vol.Range(min=0, max=20)),
    vol.Optional("sample", default={}): dict,
    vol.Optional("card", default={}): dict,
})
@websocket_api.async_response
async def websocket_benchmark(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Keep all benchmark commands and detailed observations administrator-only."""
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Loona is not loaded")
        return
    try:
        async with runtime.benchmark.lock:
            result = await runtime.benchmark.execute(connection, msg)
    except (ValueError, vol.Invalid) as err:
        connection.send_error(msg["id"], "benchmark_unavailable", str(err))
        return
    connection.send_result(msg["id"], result)
