"""Verify scope discovery against explicit expected dashboard dependencies."""

import pytest

from custom_components.loona.dependencies import (
    DiscoveryContext,
    discover,
    valid_glob,
)


def test_nested_contexts_groups_targets_and_missing():
    context = DiscoveryContext(
        frozenset({"sensor.value", "group.a", "group.b", "light.one"}),
        {
            "group.a": frozenset({"group.b", "light.one"}),
            "group.b": frozenset({"group.a"}),
        },
        {
            "area_id": {"room": frozenset({"light.area"})},
            "device_id": {"device": frozenset({"sensor.device"})},
        },
    )
    result = discover(
        {
            "views": [
                {
                    "sections": [
                        {
                            "cards": [
                                {
                                    "type": "conditional",
                                    "conditions": [
                                        {"entity": "sensor.value", "state": "on"}
                                    ],
                                    "card": {
                                        "type": "entities",
                                        "entities": [
                                            "group.a",
                                            {"entity": "sensor.future"},
                                        ],
                                    },
                                },
                                {
                                    "type": "picture-elements",
                                    "camera_image": "camera.entry",
                                    "elements": [{"entity": "sensor.element"}],
                                },
                                {
                                    "type": "button",
                                    "tap_action": {
                                        "action": "perform-action",
                                        "perform_action": "light.turn_on",
                                        "target": {"device_id": "device"},
                                    },
                                },
                                {"type": "area", "area": "room"},
                            ]
                        }
                    ],
                    "badges": ["sensor.badge"],
                    "title": "light.decoy",
                }
            ]
        },
        context,
    )
    # A scalar badge is a native entity shorthand, unlike arbitrary dotted strings.
    assert result.entity_ids == frozenset(
        {
            "sensor.value",
            "group.a",
            "group.b",
            "light.one",
            "sensor.future",
            "camera.entry",
            "sensor.element",
            "sensor.device",
            "light.area",
            "sensor.badge",
        }
    )
    assert result.complete
    assert "group:group.a" in result.reasons["light.one"]


def test_backend_template_sensor_does_not_pull_sources():
    result = discover(
        {"cards": [{"entity": "sensor.template_result"}]},
        DiscoveryContext(frozenset({"sensor.template_result", "sensor.source"})),
    )
    assert result.entity_ids == {"sensor.template_result"}


@pytest.mark.parametrize(
    "config, literal",
    [
        (
            {
                "cards": [
                    {
                        "type": "custom:button-card",
                        "name": "[[[ return hass.states['sensor.one'].state + hass.states[variables.source].state ]]]",
                    }
                ]
            },
            "sensor.one",
        ),
        (
            {
                "cards": [
                    {
                        "type": "markdown",
                        "content": "{{ states('sensor.one') }} {{ states(states('input_text.source')) }}",
                    }
                ]
            },
            "sensor.one",
        ),
        (
            {"strategy": {"type": "original-states"}, "entity": "sensor.one"},
            "sensor.one",
        ),
    ],
)
def test_dynamic_constructs_keep_literals_but_bypass(config, literal):
    result = discover(config, DiscoveryContext())
    assert literal in result.entity_ids
    assert not result.complete


def test_unknown_custom_card_reports_warning_without_blanket_bypass():
    result = discover(
        {"type": "custom:example", "entity": "sensor.example"}, DiscoveryContext()
    )
    assert result.complete and result.warnings
    assert result.entity_ids == {"sensor.example"}


def test_sunsynk_entity_mapping_includes_all_explicit_dependencies():
    # Sunsynk 7.3.3 maps logical names to IDs instead of using entity rows.
    result = discover(
        {
            "type": "custom:sunsynk-power-flow-card",
            "entities": {
                "inverter_power_175": "sensor.inverter_power",
                "grid_power_169": "sensor.grid_power",
                "battery_soc_184": "sensor.battery_soc",
                "grid_connected_status_194": "binary_sensor.grid_connected",
                "pv1_power_186": "sensor.pv1_power",
                "battery_rated_capacity": "number.battery_capacity",
                "prog1_time": "time.program_1",
                "prog1_charge": "select.program_1_charge",
                "future_input": "sensor.future",
                "unused": "none",
                "constant": 100,
                "friendly_name": "Inverter Grid L1 Power",
            },
            "name": "sensor.decoy",
        },
        DiscoveryContext(),
    )
    assert result.complete
    assert result.entity_ids == {
        "sensor.inverter_power",
        "sensor.grid_power",
        "sensor.battery_soc",
        "binary_sensor.grid_connected",
        "sensor.pv1_power",
        "number.battery_capacity",
        "time.program_1",
        "select.program_1_charge",
        "sensor.future",
    }
    assert result.reasons["sensor.grid_power"] == (
        "dashboard.entities.grid_power_169",
    )


def test_entity_mapping_preserves_native_rows_groups_and_nested_objects():
    result = discover(
        {
            "cards": [
                {
                    "type": "entities",
                    "entities": [{"entity": "sensor.row", "name": "sensor.decoy"}],
                },
                {
                    "type": "custom:example",
                    "entities": {
                        "members": ["group.room", "sensor.future"],
                        "nested": {"entity": "sensor.nested", "name": "sensor.decoy"},
                    },
                },
            ]
        },
        DiscoveryContext(groups={"group.room": frozenset({"light.member"})}),
    )
    assert result.complete
    assert result.entity_ids == {
        "sensor.row",
        "group.room",
        "light.member",
        "sensor.future",
        "sensor.nested",
    }


def test_template_in_entity_mapping_requires_bypass():
    result = discover(
        {
            "type": "custom:sunsynk-power-flow-card",
            "entities": {
                "pv1_power_186": "sensor.pv1_power",
                "pv2_power_187": "{{ states('input_text.entity_source') }}",
            },
        },
        DiscoveryContext(),
    )
    assert not result.complete
    assert result.entity_ids == {"sensor.pv1_power", "input_text.entity_source"}


def test_auto_entities_safe_superset_and_missing_exact_reference():
    result = discover(
        {
            "type": "custom:auto-entities",
            "filter": {
                "include": [
                    {
                        "entity_id": "sensor.room_*",
                        "options": {"entity": "light.option"},
                    },
                    {"domain": "light"},
                    {"entity_id": "sensor.future"},
                ],
                "exclude": [{"entity_id": "sensor.room_hidden"}],
            },
        },
        DiscoveryContext(
            frozenset(
                {"sensor.room_one", "sensor.room_hidden", "sensor.other", "light.one"}
            )
        ),
    )
    assert result.complete
    assert result.entity_ids == {
        "sensor.room_one",
        "sensor.room_hidden",
        "light.one",
        "sensor.future",
        "light.option",
    }


@pytest.mark.parametrize(
    "filter_config",
    [
        {"template": "sensor.dynamic"},
        {"include": [{"state": "on"}]},
        {"include": [{"entity_id": "/sensor.*/"}]},
    ],
)
def test_auto_entities_unsupported_filter_bypasses(filter_config):
    assert not discover(
        {"type": "custom:auto-entities", "filter": filter_config}, DiscoveryContext()
    ).complete


@pytest.mark.parametrize(
    "pattern, valid",
    [
        ("sensor.*", True),
        ("sensor.room_[1-3]", True),
        ("*.*", True),
        ("sensor.[", False),
        ("sensor.room *", False),
        ("sensor..x", False),
        ("sensor.[]", False),
    ],
)
def test_patterns(pattern, valid):
    assert valid_glob(pattern) is valid
