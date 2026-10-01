"""Check native YAML/storage behavior and target registry relationships."""

from pathlib import Path

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceYAML
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    label_registry as lr,
)

from custom_components.loona.dashboard import (
    dashboard_objects,
    discovery_context,
    load_dashboard,
)


async def test_default_yaml_precedes_default_storage(loona_hass, dashboards):
    path = Path(loona_hass.config.path("ui-lovelace.yaml"))
    path.write_text(
        "views:\n  - cards:\n      - type: entity\n        entity: sensor.yaml\n"
    )
    yaml = LovelaceYAML(loona_hass, "lovelace", None)
    loona_hass.data[LOVELACE_DATA].dashboards["lovelace"] = yaml
    assert dashboard_objects(loona_hass)["lovelace"] is yaml
    assert (await load_dashboard(loona_hass, "lovelace"))["views"][0]["cards"][0][
        "entity"
    ] == "sensor.yaml"
    path.write_text("views:\n  - cards:\n      - entity: sensor.changed\n")
    assert (await load_dashboard(loona_hass, "lovelace", force=True))["views"][0][
        "cards"
    ][0]["entity"] == "sensor.changed"


async def test_target_expansion_inherits_device_area_floor_and_labels(
    loona_hass, make_entry
):
    entry = make_entry({})
    floor = fr.async_get(loona_hass).async_create("Floor")
    label = lr.async_get(loona_hass).async_create("Room label")
    area = ar.async_get(loona_hass).async_create(
        "Room", floor_id=floor.floor_id, labels={label.label_id}
    )
    device = dr.async_get(loona_hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "device")}
    )
    dr.async_get(loona_hass).async_update_device(device.id, area_id=area.id)
    entity = er.async_get(loona_hass).async_get_or_create(
        "light", "test", "light", config_entry=entry, device_id=device.id
    )
    loona_hass.states.async_set("sensor.unregistered", "on")
    context = discovery_context(loona_hass)
    assert {entity.entity_id, "sensor.unregistered"} <= context.entity_ids
    for key, identifier in (
        ("device_id", device.id),
        ("area_id", area.id),
        ("floor_id", floor.floor_id),
        ("label_id", label.label_id),
    ):
        assert context.targets[key][identifier] == {entity.entity_id}
