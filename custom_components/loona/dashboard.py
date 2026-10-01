"""Read native Lovelace objects and snapshot registry target relationships."""

from collections import defaultdict
from typing import Any

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceConfig
from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import DEFAULT_DASHBOARD, DOMAIN, TARGET_KEYS
from .dependencies import DiscoveryContext


def dashboard_objects(hass: HomeAssistant) -> dict[str, LovelaceConfig]:
    """Normalize the effective default exactly as native lovelace/config does."""
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        return {}
    dashboards = {
        key: value for key, value in data.dashboards.items() if key is not None
    }
    default = data.dashboards.get(DEFAULT_DASHBOARD) or data.dashboards.get(None)
    if default is not None:
        dashboards[DEFAULT_DASHBOARD] = default
    return dashboards


def dashboard_titles(hass: HomeAssistant) -> dict[str, str]:
    """Use stable URL paths as values and refresh mutable labels."""
    return {
        key: (dashboard.config or {}).get(
            "title", "Overview" if key == DEFAULT_DASHBOARD else key
        )
        for key, dashboard in dashboard_objects(hass).items()
    }


async def load_dashboard(
    hass: HomeAssistant, key: str, *, force: bool = False
) -> dict[str, Any]:
    """Use the native storage/YAML loader; never read .storage directly."""
    dashboard = dashboard_objects(hass).get(key)
    if dashboard is None:
        raise ValueError("Selected dashboard no longer exists")
    result = await dashboard.async_load(force)
    if not isinstance(result, dict):
        raise ValueError("Dashboard configuration is not a mapping")
    return result


def discovery_context(hass: HomeAssistant) -> DiscoveryContext:
    """Include registered and unregistered states and inherited target metadata."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    universe = set(entities.entities) | set(hass.states.async_entity_ids())
    groups: dict[str, frozenset[str]] = {}
    for state in hass.states.async_all():
        members = state.attributes.get("entity_id")
        if isinstance(members, (list, tuple)):
            groups[state.entity_id] = frozenset(
                member
                for member in members
                if isinstance(member, str) and valid_entity_id(member)
            )
    targets: dict[str, dict[str, set[str]]] = {
        key: defaultdict(set) for key in TARGET_KEYS
    }
    for entry in entities.entities.values():
        if entry.device_id:
            targets["device_id"][entry.device_id].add(entry.entity_id)
        area_id = er.async_get_effective_area_id(hass, entry)
        area = areas.async_get_area(area_id) if area_id else None
        if area_id:
            targets["area_id"][area_id].add(entry.entity_id)
        if area and area.floor_id:
            targets["floor_id"][area.floor_id].add(entry.entity_id)
        device = devices.async_get(entry.device_id) if entry.device_id else None
        labels = set(entry.labels)
        if device:
            labels.update(device.labels)
        if area:
            labels.update(area.labels)
        for label in labels:
            targets["label_id"][label].add(entry.entity_id)
    return DiscoveryContext(
        frozenset(universe),
        groups,
        {
            key: {
                identifier: frozenset(values) for identifier, values in mapping.items()
            }
            for key, mapping in targets.items()
        },
    )


def protected_entities(hass: HomeAssistant, entry_id: str) -> frozenset[str]:
    """Loona controls and telemetry always survive advanced exclusions."""
    return frozenset(
        entry.entity_id
        for entry in er.async_get(hass).entities.values()
        if entry.config_entry_id == entry_id and entry.platform == DOMAIN
    )
