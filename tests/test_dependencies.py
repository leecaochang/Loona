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
