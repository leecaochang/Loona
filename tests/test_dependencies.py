"""Verify scope discovery against explicit expected dashboard dependencies."""

import pytest

from custom_components.loona.dependencies import (
    DiscoveryContext,
    describe_problem,
    discover,
    valid_glob,
)
from custom_components.loona.resources import resource_dependencies


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


def test_visibility_condition_entities_stay_in_scope():
    # Frontend 2026.10 seeds the first frame from hass.states; a missing entity
    # keeps the card hidden until Core's subscribe_condition result arrives.
    result = discover(
        {
            "cards": [
                {
                    "type": "tile",
                    "entity": "light.host",
                    "visibility": [
                        {"condition": "state", "state": "on"},
                        {
                            "condition": "or",
                            "conditions": [
                                {"condition": "state", "entity": "sensor.ui", "state": "a"},
                                {
                                    "condition": "numeric_state",
                                    "entity_id": "sensor.core",
                                    "above": 1,
                                },
                            ],
                        },
                    ],
                }
            ]
        },
        DiscoveryContext(),
    )
    assert result.entity_ids == {"light.host", "sensor.ui", "sensor.core"}


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
                        "type": "custom:example",
                        "text": "{{ states('sensor.one') }} {{ states(states('input_text.source')) }}",
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


def test_core_rendered_display_templates_need_no_browser_entities():
    # Core renders these through render_template, so enumerating states cannot hide data.
    lights = "{{ states.light | selectattr('state', 'eq', 'on') | list | count }} on"
    result = discover(
        {"views": [{"cards": [
            {"type": "markdown", "content": lights + " {{ states('sensor.literal') }}"},
            {"type": "custom:mushroom-template-card", "entity": "light.host", "primary": lights},
            {"type": "custom:mushroom-chips-card", "chips": [{"type": "template", "content": lights, "icon": "mdi:lightbulb"}]},
            {"type": "tile", "entity": "light.styled", "card_mod": {"style": "ha-card { --x: {{ states.light | count }}; }"}},
        ]}]},
        DiscoveryContext(),
    )
    assert result.complete, result.problems
    assert result.entity_ids == {"sensor.literal", "light.host", "light.styled"}


@pytest.mark.parametrize(
    "card",
    [
        {"type": "custom:other-chips", "chips": [{"type": "template", "content": "{{ states.light | count }}"}]},
        {"type": "markdown", "content": "[[[ return Object.keys(hass.states).length ]]]"},
        {"type": "markdown", "entity": "{{ states.light | first }}"},
    ],
)
def test_browser_or_reference_templates_still_bypass(card):
    assert not discover({"cards": [card]}, DiscoveryContext()).complete


def test_bubble_expressions_add_the_entities_they_read():
    # Bubble Card passes the configured entity ID as entity and its state as state.
    styles = (".bubble-button-background { background: ${hass.states['sensor.alarm'].state === 'on' ? 'red' : 'green'}; }"
              " .bubble-name { opacity: ${state === 'on' ? hass.states[entity].attributes.brightness / 255 : 1}; }")
    result = discover({"views": [{"cards": [
        {"type": "custom:bubble-card", "card_type": "button", "entity": "light.kitchen", "styles": styles},
        {"type": "custom:bubble-card", "entity": "light.styled", "card_mod": {"style": "ha-card { --x: ${1}; }"}},
    ]}]}, DiscoveryContext())
    assert result.complete, result.problems
    assert result.entity_ids == {"light.kitchen", "sensor.alarm", "light.styled"}


@pytest.mark.parametrize("card", [
    {"type": "custom:bubble-card", "entity": "light.kitchen", "styles": ".x { color: ${hass.states['sensor.' + name].state}; }"},
    {"type": "custom:bubble-card", "styles": ".x { color: ${hass.states[entity].state}; }"},
    {"type": "custom:bubble-card", "entity": "light.kitchen", "styles": ".x { color: ${(() => { return hass.states['sensor.alarm'].state; })()}; }"},
    {"type": "custom:bubble-card", "entity": "${hass.states['light.kitchen'].entity_id}"},
])
def test_unbounded_bubble_expressions_bypass(card):
    result = discover({"views": [{"cards": [card]}]}, DiscoveryContext())
    assert not result.complete


@pytest.mark.parametrize("card", [
    # config-template-card fills watched entities and nested cards from ${} JavaScript.
    {"type": "custom:config-template-card", "entities": ["sensor.mode", "${states['sensor.mode'].state === 'on' ? 'light.kitchen' : 'light.hall'}"],
     "card": {"type": "entity", "entity": "${states['sensor.mode'].state === 'on' ? 'light.kitchen' : 'light.hall'}"}},
    {"type": "custom:config-template-card", "entities": ["sensor.mode"],
     "card": {"type": "markdown", "content": "${states['sensor.mode'].state}"}},
])
def test_other_dollar_brace_templates_bypass_but_keep_literals(card):
    result = discover({"views": [{"cards": [card]}]}, DiscoveryContext())
    assert not result.complete
    assert "sensor.mode" in result.entity_ids
    assert resource_dependencies([card]).dynamic


def test_reusable_button_card_templates_take_the_using_card_context():
    config = {
        "button_card_templates": {
            "named": {"name": "[[[ return states['sensor.alarm'].state ]]]", "label": "[[[ return entity.state ]]]"},
            "owned": {"type": "custom:button-card", "entity": "sensor.owned",
                      "styles": {"icon": [{"color": "[[[ return entity.state === 'on' ? 'red' : 'blue' ]]]"}]}},
        },
        "views": [{"cards": [{"type": "custom:button-card", "template": ["named", "owned"], "entity": "light.kitchen"}]}],
    }
    result = discover(config, DiscoveryContext())
    assert result.complete, result.problems
    assert result.entity_ids == {"light.kitchen", "sensor.alarm", "sensor.owned"}
    assert not resource_dependencies([config]).dynamic
    assert resource_dependencies([config]).custom_types == {"button-card"}


@pytest.mark.parametrize("definition", [
    {"name": "[[[ return hass.states[variables.room].state ]]]"},
    # A nested card does not inherit the template's entity binding.
    {"custom_fields": {"inner": {"card": {"type": "custom:button-card", "label": "[[[ return entity.state ]]]"}}}},
])
def test_unbounded_reusable_templates_still_bypass(definition):
    config = {"button_card_templates": {"room": definition}, "views": []}
    assert not discover(config, DiscoveryContext()).complete
    assert resource_dependencies([config]).dynamic


def test_auto_entities_area_attribute_and_state_rules_use_safe_supersets():
    context = DiscoveryContext(
        frozenset({"light.studio", "sensor.studio", "light.hall", "binary_sensor.door", "binary_sensor.motion", "light.lama", "light.lamp_a"}),
        targets={"area_id": {"studio": frozenset({"light.studio", "sensor.studio"}), "hall": frozenset({"light.hall"})}},
        area_names={"studio": "Studio", "hall": "Hall", "empty": "Empty"},
    )
    result = discover(
        {"views": [{"cards": [
            {"type": "custom:auto-entities", "filter": {"include": [{"area": "Studio"}], "exclude": [{"domain": "sensor"}]}},
            {"type": "custom:auto-entities", "filter": {"include": [{"area": "hall", "domain": "light"}]}},
            {"type": "custom:auto-entities", "filter": {"include": [{"domain": "binary_sensor", "attributes": {"device_class": "door"}}]}},
            {"type": "custom:auto-entities", "filter": {"include": [{"domain": "light", "state": "on", "entity_id": "light.lamp?a*"}]}},
            {"type": "custom:auto-entities", "filter": {"include": [{"area": "Empty"}]}},
        ]}]},
        context,
    )
    assert result.complete, result.problems
    # With a *, auto-entities reads "lamp?a*" as a regular expression (optional "p"), not as a glob.
    assert result.entity_ids == {"light.studio", "sensor.studio", "light.hall", "binary_sensor.door", "binary_sensor.motion", "light.lama"}


@pytest.mark.parametrize(
    "rule",
    [{"state": "on"}, {"attributes": {"device_class": "door"}}, {"area": "/stud/"}, {"domain": "light", "device": "x"}, {"area": "<3"}],
)
def test_auto_entities_rules_without_bounds_still_bypass(rule):
    assert not discover({"type": "custom:auto-entities", "filter": {"include": [rule]}}, DiscoveryContext()).complete


@pytest.mark.parametrize(
    "problem, expected",
    [
        ("dashboard.views[0].sections[0].cards[1].chips[2].content: template dependencies cannot be scoped", ("Living / custom:mushroom-chips-card", "template")),
        ("dashboard.views[1].cards[0].filter: auto-entities template filter cannot be scoped", ('stats / custom:auto-entities "Rooms"', "auto_entities")),
        ("dashboard.views[1].badges[0].entity: template dependencies cannot be scoped", ("stats / entity", "template")),
        ("dashboard.views[2]: dashboard strategy cannot be scoped", ("#3", "strategy")),
        ("dashboard: dashboard strategy cannot be scoped", ("", "strategy")),
        ("dashboard.views[9].cards[0].text: template dependencies cannot be scoped", ("", "template")),
    ],
)
def test_problems_name_their_view_and_top_level_card(problem, expected):
    config = {"views": [
        {"title": "Living", "sections": [{"cards": [{"type": "tile"}, {"type": "custom:mushroom-chips-card", "chips": [{}, {}, {}]}]}]},
        {"path": "stats", "cards": [{"type": "custom:auto-entities", "title": "Rooms"}], "badges": [{"type": "entity"}]},
        {"strategy": {"type": "custom:unknown"}},
    ]}
    assert describe_problem(config, problem) == expected


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
        ("sensor." + "a" * 248, True),
        ("sensor." + "a" * 249, False),
    ],
)
def test_patterns(pattern, valid):
    assert valid_glob(pattern) is valid
