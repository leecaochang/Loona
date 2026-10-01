"""Measure native wire payloads and stock-client processing with synthetic data."""

from dataclasses import replace
import json
import logging
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time

from homeassistant import const as ha_const
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.messages import message_to_json_bytes
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    label_registry as lr,
)

from custom_components.loona.const import VERSION
from custom_components.loona.registry import RegistryAdapter, registry_scope
from custom_components.loona.websocket import ScopePolicy, SubscriptionAdapter

COMMANDS = (
    "config/entity_registry/list",
    "config/entity_registry/list_for_display",
    "config/device_registry/list",
    "config/area_registry/list",
    "config/floor_registry/list",
    "config/label_registry/list",
)


class Capture:
    """Count Core's serialized bytes outside handler timing regions."""

    def __init__(self, hass, user):
        self.packets = []
        self.connection = ActiveConnection(
            logging.getLogger("loona.benchmark"), hass, self.send, user, None, None
        )

    def send(self, payload):
        self.packets.append(
            payload
            if isinstance(payload, bytes)
            else payload.encode()
            if isinstance(payload, str)
            else message_to_json_bytes(payload)
        )

    def request(self, command, **fields):
        started = time.perf_counter_ns()
        self.connection.async_handle(
            {"id": self.connection.last_id + 1, "type": command, **fields}
        )
        return (time.perf_counter_ns() - started) / 1_000_000

    def take(self):
        packets, self.packets = self.packets, []
        return packets


def summarize_events(packets):
    """Logical event objects are distinct from websocket transport frames."""
    events = [
        (packet, message["event"])
        for packet in packets
        if (message := json.loads(packet)).get("type") == "event"
    ]
    return {
        "logical_events": len(events),
        "json_bytes": sum(len(packet) for packet, _ in events),
        "entity_records": sum(
            len(event.get(key, {})) for _, event in events for key in ("a", "c", "r")
        ),
    }


def seed(hass, entry, count):
    """Create ten sensors per device, ten devices per area, ten areas per floor."""
    entities = []
    for index in range(count):
        if index % 1000 == 0:
            floor = fr.async_get(hass).async_create(f"Floor {index // 1000:04}")
        if index % 100 == 0:
            area = ar.async_get(hass).async_create(
                f"Area {index // 100:04}", floor_id=floor.floor_id
            )
            label = lr.async_get(hass).async_create(f"Label {index // 100:04}")
            ar.async_get(hass).async_update(area.id, labels={label.label_id})
        if index % 10 == 0:
            device = dr.async_get(hass).async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={("benchmark", str(index // 10))},
                name=f"Device {index // 10:05}",
                manufacturer="Synthetic",
                model="Ten sensors",
            )
            dr.async_get(hass).async_update_device(device.id, area_id=area.id)
        entity = er.async_get(hass).async_get_or_create(
            "sensor",
            "benchmark",
            str(index),
            config_entry=entry,
            device_id=device.id,
            original_name=f"Reading {index:05}",
        )
        entities.append(entity.entity_id)
        hass.states.async_set(
            entity.entity_id,
            "0",
            {
                "friendly_name": f"Reading {index:05}",
                "unit_of_measurement": "W",
                "device_class": "power",
                "padding": "x" * 64,
            },
        )
    return entities


async def test_native_performance_comparison(loona_hass, make_entry, make_user):
    """Verify counters on a small fixture; opt in to the 10,000-entity benchmark."""
    large = os.environ.get("LOONA_BENCHMARK") == "1"
    count, retained, changes, samples = (
        (10000, 200, 1000, 5) if large else (100, 20, 20, 2)
    )
    hass = loona_hass
    ids = seed(hass, make_entry({}), count)
    await hass.async_block_till_done()
    policy = ScopePolicy(frozenset(ids[:retained]), all_users=True)
    scope = registry_scope(hass, policy.entity_ids, [])
    user = make_user(admin=True)
    entities_adapter = SubscriptionAdapter(hass, replace(policy, enabled=False))
    registry_adapter = RegistryAdapter(
        hass, replace(policy, enabled=False), scope, lambda error: errors.append(error)
    )
    errors = []
    captures = []
    cases, report = {}, {}
    entities_adapter.install()
    registry_adapter.install()
    try:
        for filtered in (False, True):
            label = "filtered" if filtered else "full"
            entities_adapter.set_policy(replace(policy, enabled=filtered))
            registry_adapter.set_policy(replace(policy, enabled=filtered), scope)
            timings = []
            for sample in range(samples + 1):
                capture = Capture(hass, user)
                captures.append(capture)
                # The stock client reserves protocol IDs 1 and 2 before subscribing.
                capture.connection.last_id = 2
                duration = capture.request("subscribe_entities")
                packets = capture.take()
                summary = summarize_events(packets)
                assert summary["entity_records"] == (retained if filtered else count)
                if sample:
                    timings.append(duration)
                capture.connection.async_handle_close()
            report[label] = {
                "snapshot": {
                    **summary,
                    "handler_median_ms": statistics.median(timings),
                },
                "registries": {},
            }
            capture = Capture(hass, user)
            captures.append(capture)
            for command in COMMANDS:
                timings = []
                for sample in range(samples + 1):
                    duration = capture.request(command)
                    packets = capture.take()
                    assert len(packets) == 1
                    response = json.loads(packets[0])
                    assert response["success"]
                    result = response["result"]
                    rows = (
                        result["entities"]
                        if command.endswith("list_for_display")
                        else result
                    )
                    if sample:
                        timings.append(duration)
                report[label]["registries"][command] = {
                    "rows": len(rows),
                    "json_bytes": len(packets[0]),
                    "handler_median_ms": statistics.median(timings),
                }
            capture.connection.async_handle_close()
            capture = Capture(hass, user)
            captures.append(capture)
            capture.connection.last_id = 2
            # An explicit empty list requests the native full stream in this release.
            capture.request(
                "subscribe_entities", **({} if filtered else {"entity_ids": []})
            )
            cases[label] = {"initial": [packet.decode() for packet in capture.take()]}
            cases[label]["capture"] = capture
        assert entities_adapter.managed_count == entities_adapter.filtered_count == 1
        changed_ids = ids[:: count // changes][:changes]
        for entity_id in changed_ids:
            state = hass.states.get(entity_id)
            hass.states.async_set(entity_id, "1", state.attributes)
        await hass.async_block_till_done()
        for label, case in cases.items():
            packets = case.pop("capture").take()
            case["updates"] = [packet.decode() for packet in packets]
            case["expected_count"] = retained if label == "filtered" else count
            case["expected_changes"] = (
                len(set(changed_ids) & policy.entity_ids)
                if label == "filtered"
                else changes
            )
            report[label]["updates"] = summarize_events(packets)
            assert (
                report[label]["updates"]["entity_records"] == case["expected_changes"]
            )
            assert (
                report[label]["updates"]["logical_events"] == case["expected_changes"]
            )
        assert not errors
        client = subprocess.run(
            ["node", str(Path(__file__).with_name("client_benchmark.mjs"))],
            input=json.dumps({"cases": cases, "samples": samples}),
            text=True,
            capture_output=True,
            check=True,
            timeout=180,
        )
        processing = json.loads(client.stdout)
        for label in cases:
            report[label]["stock_client"] = processing["cases"][label]
        result = {
            "conditions": {
                "core": ha_const.__version__,
                "loona": VERSION,
                "python": platform.python_version(),
                "node": processing["node"],
                "system": platform.system(),
                "architecture": platform.machine(),
                "entities": count,
                "retained_entities": retained,
                "changed_entities": changes,
                "samples_after_warmup": samples,
                "transport_compression": False,
                "rendering_measured": False,
            },
            "measurements": report,
        }
        output = os.environ.get("LOONA_BENCHMARK_OUTPUT")
        if output:
            Path(output).write_text(json.dumps(result, indent=2) + "\n")
        if large:
            print(json.dumps(result, indent=2))
    finally:
        for capture in captures:
            capture.connection.async_handle_close()
        registry_adapter.uninstall()
        entities_adapter.uninstall()
