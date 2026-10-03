"""Check native setup selectors, stale values, and preservation of options."""

import pytest

from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers import entity_registry as er

from custom_components.loona.config_flow import (
    LoonaConfigFlow,
    LoonaOptionsFlow,
    human_accounts,
    validate_dashboards,
    validate_targets,
)


async def test_setup_targets_admin_and_confirms_card_refresh(loona_hass, dashboards):
    admin = await loona_hass.auth.async_create_user(
        "Administrator", group_ids=["system-admin"]
    )
    inactive = await loona_hass.auth.async_create_user("Inactive")
    await loona_hass.auth.async_update_user(inactive, is_active=False)
    await loona_hass.auth.async_create_system_user("Service")
    accounts = await human_accounts(loona_hass)
    assert list(accounts) == [admin.id]
    assert accounts[admin.id] == "Administrator"
    flow = LoonaConfigFlow()
    flow.hass = loona_hass
    flow.handler = "loona"
    flow.context = {"source": "user"}
    form = await flow.async_step_user()
    assert form["step_id"] == "user"
    values = form["data_schema"]({"dashboards": ["lovelace", "wall-panel"]})
    form = await flow.async_step_user(values)
    assert form["step_id"] == "targets"
    values = form["data_schema"]({"target_mode": "selected", "user_ids": [admin.id]})
    result = await flow.async_step_targets(values)
    assert result["step_id"] == "cards"
    result = await flow.async_step_cards({"dashboard_cards": ["settings", "statistics"]})
    assert result["step_id"] == "finish" and result["last_step"]
    result = await flow.async_step_finish({})
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "dashboards": ["lovelace", "wall-panel"],
        "target_mode": "selected",
        "user_ids": [admin.id],
        "dashboard_cards": ["settings", "statistics"],
    }


async def test_singleton_and_stale_selections(loona_hass, dashboards, make_entry):
    make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    flow = LoonaConfigFlow()
    flow.hass, flow.handler, flow.context = loona_hass, "loona", {"source": "user"}
    with pytest.raises(AbortFlow, match="already_configured"):
        await flow.async_step_user()
    assert validate_dashboards(loona_hass, {"dashboards": []}) == "no_dashboards"
    assert (
        validate_dashboards(loona_hass, {"dashboards": ["gone"]}) == "invalid_selection"
    )
    assert (
        validate_dashboards(loona_hass, {"dashboards": ["wall-panel", "wall-panel"]})
        == "invalid_selection"
    )
    assert (
        await validate_targets(
            loona_hass, {"target_mode": "selected", "user_ids": ["gone"]}
        )
        == "invalid_selection"
    )
    assert (
        await validate_targets(loona_hass, {"target_mode": "selected", "user_ids": []})
        == "no_accounts"
    )
    values = {"target_mode": "all", "user_ids": ["gone"]}
    assert await validate_targets(loona_hass, values) is None
    assert values["user_ids"] == []


async def test_options_preserve_unrelated_fields_and_stale_labels(
    loona_hass, dashboards, make_entry
):
    entry = make_entry(
        {
            "dashboards": ["removed"],
            "target_mode": "selected",
            "user_ids": ["removed-user"],
        },
        options={
            "extra_entities": ["sensor.future"],
            "exclude_globs": ["sensor.hidden*"],
        },
    )
    flow = LoonaOptionsFlow()
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = await flow.async_step_init()
    assert set(result["menu_options"]) == {
        "dashboards",
        "targets",
        "filters",
        "rules",
        "resource_preview",
        "cards",
    }
    result = await flow.async_step_dashboards()
    selector = next(iter(result["data_schema"].schema.values()))
    assert any(choice["value"] == "removed" for choice in selector.config["options"])
    result = await flow.async_step_targets()
    selectors = list(result["data_schema"].schema.values())
    assert any(
        choice["value"] == "removed-user" for choice in selectors[1].config["options"]
    )
    result = await flow.async_step_dashboards({"dashboards": ["wall-panel"]})
    assert result["data"] == {
        "dashboards": ["wall-panel"],
        "extra_entities": ["sensor.future"],
        "exclude_globs": ["sensor.hidden*"],
    }


async def test_rules_and_extra_entities_validate(loona_hass, make_entry):
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    flow = LoonaOptionsFlow()
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = await flow.async_step_rules({"include_domains": ["light.bad"]})
    assert result["errors"]["base"] == "invalid_selection"
    result = await flow.async_step_rules({"include_globs": ["sensor.["]})
    assert result["errors"]["base"] == "invalid_selection"
    loona_hass.states.async_set("sensor.future", "1")
    result = await flow.async_step_rules({"extra_entities": ["sensor.future"]})
    assert result["data"]["extra_entities"] == ["sensor.future"]
    result = await flow.async_step_rules({"extra_entities": ["bad value"]})
    assert result["errors"]["base"] == "invalid_selection"
    result = await flow.async_step_filters({"entity_filtering": False})
    assert result["errors"]["base"] == "not_loaded"


async def test_rules_select_known_entities_domains_and_preserve_saved_patterns(
    loona_hass, make_entry
):
    loona_hass.states.async_set("sensor.room_temperature", "20")
    registered = er.async_get(loona_hass).async_get_or_create(
        "light", "test", "registry-only", suggested_object_id="registry_only"
    )
    entry = make_entry(
        {"dashboards": ["wall-panel"], "target_mode": "all"},
        options={"extra_entities": ["sensor.future"],
                 "include_domains": ["retired"],
                 "include_globs": ["sensor.room_*", "sensor.removed"],
                 "exclude_globs": ["light.old_*"]},
    )
    flow = LoonaOptionsFlow(entry.entry_id)
    flow.hass, flow.handler = loona_hass, entry.entry_id
    form = await flow.async_step_rules()
    selectors = {str(key.schema): value for key, value in form["data_schema"].schema.items()}
    assert selectors["include_domains"].config["options"] == ["light", "retired", "sensor"]
    assert {"sensor.*", "light.*",
            "sensor.room_*", "sensor.removed"} <= set(selectors["include_globs"].config["options"])
    assert "light.old_*" in selectors["exclude_globs"].config["options"]
    assert "light.old_*" not in selectors["include_globs"].config["options"]
    assert selectors["extra_entities"].selector_type == "entity"
    assert selectors["include_globs"].config["custom_value"]
    assert (await flow.async_step_rules({"include_globs": ["sensor.invented"]}))["errors"] == {"base": "invalid_selection"}
    values = form["data_schema"]({"include_domains": ["retired", "light"],
        "include_globs": ["sensor.room_*", registered.entity_id],
        "exclude_globs": ["sensor.*"]})
    result = await flow.async_step_rules(values)
    assert result["data"] == {**values, "extra_entities": ["sensor.future"]}
    # Rebuild against current entities at submission, while retaining saved rules.
    loona_hass.states.async_remove("sensor.room_temperature")
    result = await flow.async_step_rules({"include_globs": ["sensor.room_temperature"]})
    assert result["errors"]["base"] == "invalid_selection"
    result = await flow.async_step_rules({"include_globs": ["sensor.room_*"]})
    assert result["data"]["include_globs"] == ["sensor.room_*"]
    result = await flow.async_step_rules({"include_domains": [], "include_globs": [], "exclude_globs": []})
    assert result["data"] == {"extra_entities": ["sensor.future"], "include_domains": [],
                              "include_globs": [], "exclude_globs": []}


@pytest.mark.parametrize("values", [
    {"include_domains": ["invented"]},
    {"include_globs": ["sensor.invented"]},
    {"exclude_globs": ["sensor.invented*"]},
    {"include_domains": ["sensor", "sensor"]},
    {"include_globs": "sensor.live"},
    {"exclude_globs": [None]},
    {"include_globs": [["sensor.live"]]},
    {"include_domains": None},
    {"unexpected": []},
])
async def test_rules_reject_invalid_or_forged_selections(loona_hass, make_entry, values):
    loona_hass.states.async_set("sensor.live", "1")
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all"})
    flow = LoonaOptionsFlow(entry.entry_id)
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = await flow.async_step_rules(values)
    assert result["errors"]["base"] == "invalid_selection"


async def test_restore_initial_choices_and_empty_exceptions_preserves_other_options(loona_hass, make_entry):
    entry = make_entry(
        {"dashboards": ["wall-panel"], "target_mode": "all", "user_ids": []},
        options={"dashboards": ["temporary"], "always_forward_resources": ["/local/helper.js"],
                 "extra_entities": ["sensor.future"]},
    )
    flow = LoonaOptionsFlow(entry.entry_id)
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = flow.finish({"dashboards": ["wall-panel"], "always_forward_resources": []})
    assert result["data"] == {"extra_entities": ["sensor.future"]}


@pytest.mark.parametrize("cards", [[], ["statistics"], ["settings"], ["statistics", "settings"]])
async def test_optional_card_selections(loona_hass, cards):
    flow = LoonaConfigFlow()
    flow.hass, flow.handler, flow.context = loona_hass, "loona", {"source": "user"}
    result = await flow.async_step_cards({"dashboard_cards": cards})
    if cards:
        assert result["step_id"] == "finish"
        result = await flow.async_step_finish({})
    assert result["type"] == "create_entry"
    assert result["data"]["dashboard_cards"] == cards


@pytest.mark.parametrize("cards", [["unknown"], ["settings", "settings"], "settings", [None]])
async def test_invalid_card_selections(loona_hass, cards):
    flow = LoonaConfigFlow()
    flow.hass, flow.handler, flow.context = loona_hass, "loona", {"source": "user"}
    result = await flow.async_step_cards({"dashboard_cards": cards})
    assert result["errors"]["base"] == "invalid_selection"


async def test_native_options_dashboard_removal_confirmation(loona_hass, make_entry):
    entry = make_entry({"dashboards": ["wall-panel"], "target_mode": "all", "dashboard_cards": ["settings"]})
    flow = LoonaOptionsFlow(entry.entry_id)
    flow.hass, flow.handler = loona_hass, entry.entry_id
    result = await flow.async_step_cards({"dashboard_cards": []})
    assert result["step_id"] == "confirm_remove_dashboard"
    assert entry.data["dashboard_cards"] == ["settings"]
    result = await flow.async_step_confirm_remove_dashboard({"confirm": False})
    assert result["errors"] == {"base": "confirmation_required"}
    assert entry.data["dashboard_cards"] == ["settings"]
    result = await flow.async_step_confirm_remove_dashboard({"confirm": True})
    assert result["type"] == "create_entry" and result["data"]["dashboard_cards"] == []
