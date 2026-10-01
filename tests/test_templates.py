"""Verify complete template scopes and conservative unsupported-code bypass."""

import pytest
from jinja2 import Environment

from homeassistant.helpers.template import Template

from custom_components.loona.const import MAX_TEMPLATE_LENGTH, MAX_TEMPLATE_NODES
from custom_components.loona.dependencies import DiscoveryContext, discover
from custom_components.loona.templates import template_dependencies


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            "{{ states('sensor.temperature') | float(0) | round(1) }}",
            {"sensor.temperature"},
        ),
        (
            "{{ state_attr('climate.room', 'temperature') | default(20) }}",
            {"climate.room"},
        ),
        (
            "{{ states.sensor.future.attributes.unit_of_measurement }}",
            {"sensor.future"},
        ),
        ("{{ states['sensor.future'].state }}", {"sensor.future"}),
        (
            "{{ 'red' if is_state('binary_sensor.door', 'on') else 'green' }}",
            {"binary_sensor.door"},
        ),
        (
            "{% set status = states('input_select.mode') %}"
            "{% if status == 'active' %}{{ states('sensor.first') }}"
            "{% elif is_state_attr('climate.room', 'hvac_action', 'heating') %}"
            "{{ states('sensor.second') }}{% else %}{{ states('sensor.third') }}{% endif %}",
            {
                "input_select.mode",
                "climate.room",
                "sensor.first",
                "sensor.second",
                "sensor.third",
            },
        ),
        ("Updated {{ now().strftime('%H:%M') }}", set()),
        (
            "{% if false %}{{ states('sensor.hidden_branch') }}{% endif %}",
            {"sensor.hidden_branch"},
        ),
        ("{{ has_value('sensor.available') }}", {"sensor.available"}),
        (r"{{ states('sensor.\u0066uture') }}", {"sensor.future"}),
    ],
)
def test_fixed_jinja_dependencies_cover_every_branch(source, expected):
    result = template_dependencies(source)
    assert result.complete
    assert result.entity_ids == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ("[[[ return Number(entity.state).toFixed(1); ]]]", {"sensor.card"}),
        (
            "[[[ let t=Number(entity.state); if(t>38)return 'red'; if(t>28)return 'yellow'; return 'blue'; ]]]",
            {"sensor.card"},
        ),
        ("[[[ return states['sensor.extra'].state; ]]]", {"sensor.extra"}),
        (
            "[[[ return hass['states']['sensor.extra'].attributes.value; ]]]",
            {"sensor.extra"},
        ),
        (
            "[[[ if (entity.state === 'on') { return Math.round(Number(states['sensor.first'].state)); }"
            " else { return hass.states['sensor.second'].state; } ]]]",
            {"sensor.card", "sensor.first", "sensor.second"},
        ),
        (
            "[[[ return entity.state === 'on' ? states['sensor.first'].state : states['sensor.second'].state; ]]]",
            {"sensor.card", "sensor.first", "sensor.second"},
        ),
        (
            "[[[ // A comment\n return Math.round(Number(entity.state)) + ' km/h'; /* Another comment */ ]]]",
            {"sensor.card"},
        ),
        ("[[[ const v=Number(entity.state); return (v + 1) / 2; ]]]", {"sensor.card"}),
    ],
)
def test_bounded_button_card_expressions(source, expected):
    result = template_dependencies(
        source, card_type="custom:button-card", entity_id="sensor.card"
    )
    assert result.complete
    assert result.entity_ids == expected


@pytest.mark.parametrize(
    "source",
    [
        "{{ states }}",
        "{{ states.sensor }}",
        "{{ states(states('input_text.source')) }}",
        "{{ states['sensor.' ~ states('input_text.source')] }}",
        "{% for item in states.sensor %}{{ item.state }}{% endfor %}",
        "{{ states('sensor.fixed') | custom_filter }}",
        "{{ expand('group.room') }}",
        "{{ area_entities('room') }}",
        "{% include 'dynamic.jinja' %}",
        "{% set source = 'sensor.fixed' %}{{ states(source) }}",
        "{% if true %}{% set source = 'sensor.first' %}{% else %}{% set source = 'sensor.second' %}{% endif %}{{ states(source) }}",
        "{% set states = 'shadow' %}{{ states }}",
        "{{ states('sensor.fixed').__class__ }}",
        "{{ states('sensor.fixed') ",
        "[[[ return hass.states[entity.attributes.source].state; ]]]",
        "[[[ const source = 'sensor.fixed'; return states[source].state; ]]]",
        "[[[ if (true) { let source='sensor.first'; } else { let source='sensor.second'; } return states[source].state; ]]]",
        "[[[ return Object.values(hass.states); ]]]",
        "[[[ return states; ]]]",
        "[[[ return hass; ]]]",
        "[[[ return variables.dynamic; ]]]",
        "[[[ return helpers.someFunction(entity); ]]]",
        "[[[ return eval(entity.state); ]]]",
        "[[[ return entity.constructor('return hass.states')(); ]]]",
        "[[[ return states[`sensor.${entity.state}`].state; ]]]",
        "[[[ for (const item of Object.values(states)) return item.state; ]]]",
        "[[[ return entity.state++; ]]]",
        "[[[ return entity.state--; ]]]",
        "[[[ let return = 1; return return; ]]]",
        "[[[ return entity.state; unexpected(); ]]]",
        "[[[ return entity.state; ]]] trailing code",
    ],
)
def test_unbounded_or_unsupported_templates_bypass(source):
    assert not template_dependencies(
        source, card_type="custom:button-card", entity_id="sensor.card"
    ).complete


def test_javascript_entity_requires_known_button_card_context():
    source = "[[[ return entity.state; ]]]"
    assert not template_dependencies(source, card_type="custom:button-card").complete
    assert not template_dependencies(
        source, card_type="custom:unknown", entity_id="sensor.card"
    ).complete


def test_dynamic_templates_keep_literal_dependencies_without_execution(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Template rendering must not run during discovery")

    monkeypatch.setattr(Environment, "from_string", fail)
    result = template_dependencies(
        "{{ states('sensor.fixed') }} {{ unsafe_function() }}"
    )
    assert not result.complete and result.entity_ids == {"sensor.fixed"}


def test_template_complexity_limits_bypass():
    assert not template_dependencies("{{ 1 }}" + " " * MAX_TEMPLATE_LENGTH).complete
    assert not template_dependencies(
        "[[[" + "return 1;" * MAX_TEMPLATE_NODES + "]]]", card_type="custom:button-card"
    ).complete


def test_template_entities_expand_groups_and_preserve_nested_card_context():
    result = discover(
        {
            "cards": [
                {
                    "type": "custom:button-card",
                    "entity": "sensor.card",
                    "styles": {
                        "icon": [
                            {
                                "color": "[[[ return Number(entity.state)>20 ? 'red' : 'blue'; ]]]"
                            }
                        ]
                    },
                    "custom_fields": {
                        "child": {
                            "card": {
                                "type": "custom:button-card",
                                "entity": "sensor.child",
                                "label": "[[[ return entity.state + states['group.room'].state; ]]]",
                            }
                        }
                    },
                    "card_mod": {
                        "style": "ha-card { color: {{ 'red' if is_state('binary_sensor.door', 'on') else 'green' }}; }"
                    },
                }
            ]
        },
        DiscoveryContext(groups={"group.room": frozenset({"light.member"})}),
    )
    assert result.complete
    assert result.entity_ids == {
        "sensor.card",
        "sensor.child",
        "group.room",
        "light.member",
        "binary_sensor.door",
    }
    assert any(
        "custom_fields.child.card.label" in reason
        for reason in result.reasons["sensor.child"]
    )


@pytest.mark.parametrize(
    "key", ["entity", "entity_id", "entities", "area_id", "device_id", "type"]
)
def test_templated_entity_target_or_card_type_still_bypasses(key):
    assert not discover(
        {"type": "custom:button-card", key: "{{ 'sensor.generated' }}"},
        DiscoveryContext(),
    ).complete


def test_templates_in_entity_row_presentation_do_not_become_dynamic_references():
    result = discover(
        {
            "type": "entities",
            "entities": [
                {"entity": "sensor.card", "name": "{{ states('sensor.label') }}"}
            ],
        },
        DiscoveryContext(),
    )
    assert result.complete and result.entity_ids == {"sensor.card", "sensor.label"}


def test_templated_area_card_target_still_bypasses():
    assert not discover(
        {"type": "area", "area": "{{ 'room' }}"}, DiscoveryContext()
    ).complete


async def test_static_scope_contains_native_jinja_reads_across_state_changes(hass):
    source = (
        "{% set mode = states('input_select.mode') %}"
        "{{ states('sensor.first') if mode == 'first' else states('sensor.second') }}"
    )
    scope = template_dependencies(source)
    assert scope.complete
    assert scope.entity_ids == {"input_select.mode", "sensor.first", "sensor.second"}
    hass.states.async_set("sensor.first", "11")
    hass.states.async_set("sensor.second", "22")
    for mode, expected in (("first", 11), ("second", 22)):
        hass.states.async_set("input_select.mode", mode)
        native = Template(source, hass).async_render_to_info()
        assert native.result() == expected
        assert native.entities <= scope.entity_ids
        assert "input_select.mode" in native.entities
