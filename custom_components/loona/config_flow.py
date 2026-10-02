"""Native singleton setup and options flows for Loona."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback, valid_entity_id
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CONF_DASHBOARDS,
    CONF_ALWAYS_FORWARD,
    CONTROL_RESOURCES,
    CONF_TARGET_MODE,
    CONF_USER_IDS,
    CONF_EXTRA_ENTITIES,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_GLOBS,
    CONF_EXCLUDE_GLOBS,
    CONTROL_ENTITIES,
    CONTROL_MASTER,
    CONTROL_GRAPHS,
    CONTROL_MOTION,
    CONTROL_REGISTRIES,
    DOMAIN,
    TARGET_ALL,
    TARGET_SELECTED,
    TARGET_MODES,
)
from .compatibility import CompatibilityError
from .dashboard import dashboard_titles
from .preview import dependency_rows


def entity_rule_choices(
    hass: HomeAssistant, current: dict[str, Any]
) -> dict[str, list[str]]:
    """Offer current states, registry entries, domain globs and saved rules."""
    entities = set(hass.states.async_entity_ids()) | set(er.async_get(hass).entities)
    domains = {entity_id.split(".", 1)[0] for entity_id in entities}
    patterns = entities | {f"{domain}.*" for domain in domains}
    choices = {
        CONF_INCLUDE_DOMAINS: domains,
        CONF_INCLUDE_GLOBS: patterns.copy(),
        CONF_EXCLUDE_GLOBS: patterns.copy(),
    }
    for key, values in choices.items():
        values.update(current.get(key, []))
    return {key: sorted(values) for key, values in choices.items()}


async def human_accounts(hass: HomeAssistant) -> dict[str, str]:
    """Keep active human accounts selectable, including administrators."""
    return {
        user.id: user.name or user.id
        for user in await hass.auth.async_get_users()
        if user.is_active and not user.system_generated
    }


def dashboard_schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    """Keep stale values visible so users can remove them deliberately."""
    titles = dashboard_titles(hass)
    for key in current.get(CONF_DASHBOARDS, []):
        titles.setdefault(key, key)
    return vol.Schema(
        {
            vol.Required(
                CONF_DASHBOARDS, default=current.get(CONF_DASHBOARDS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=key, label=title)
                        for key, title in titles.items()
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


async def target_schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    """Expose account-wide targeting in a standard form."""
    accounts = await human_accounts(hass)
    for key in current.get(CONF_USER_IDS, []):
        accounts.setdefault(key, key)
    return vol.Schema(
        {
            vol.Required(
                CONF_TARGET_MODE, default=current.get(CONF_TARGET_MODE, TARGET_SELECTED)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[TARGET_SELECTED, TARGET_ALL],
                    translation_key="target_mode",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_USER_IDS, default=current.get(CONF_USER_IDS, [])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=key, label=label)
                        for key, label in accounts.items()
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def validate_dashboards(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Validate stable identifiers, nonempty choices, and duplicates."""
    keys = data.get(CONF_DASHBOARDS, [])
    if (
        not isinstance(keys, list)
        or not keys
        or any(not isinstance(key, str) for key in keys)
    ):
        return "no_dashboards"
    if len(keys) != len(set(keys)) or not set(keys) <= dashboard_titles(hass).keys():
        return "invalid_selection"
    return None


async def validate_targets(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Validate selections against current active accounts on the server."""
    mode = data.get(CONF_TARGET_MODE)
    if mode not in TARGET_MODES:
        return "invalid_selection"
    if mode == TARGET_ALL:
        data[CONF_USER_IDS] = []
        return None
    ids = data.get(CONF_USER_IDS, [])
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(key, str) for key in ids)
    ):
        return "no_accounts"
    if len(ids) != len(set(ids)) or not set(ids) <= (await human_accounts(hass)).keys():
        return "invalid_selection"
    return None


class LoonaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Select dashboards and accounts once through native HA selectors."""

    VERSION = 1

    def __init__(self) -> None:
        """Collect the two short setup forms."""
        super().__init__()
        self._settings: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Use in-place options updates to preserve managed subscriptions."""
        return LoonaOptionsFlow(config_entry.entry_id)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select at least one existing dashboard and enforce singleton setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := validate_dashboards(self.hass, user_input):
                errors["base"] = error
            else:
                self._settings.update(user_input)
                return await self.async_step_targets()
        return self.async_show_form(
            step_id="user",
            data_schema=dashboard_schema(self.hass, user_input or self._settings),
            errors=errors,
        )

    async def async_step_targets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Target administrators intentionally; never infer a role bypass."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := await validate_targets(self.hass, user_input):
                errors["base"] = error
            else:
                self._settings.update(user_input)
                return self.async_create_entry(title="Loona", data=self._settings)
        return self.async_show_form(
            step_id="targets",
            data_schema=await target_schema(self.hass, user_input or self._settings),
            errors=errors,
        )

class LoonaOptionsFlow(OptionsFlow):
    """Update one category while preserving every other saved option."""

    def __init__(self, entry_id: str | None = None) -> None:
        super().__init__()
        self._entry_id = entry_id

    @property
    def config_entry(self) -> ConfigEntry:
        """Resolve through native entries on older and current options managers."""
        entry = self.hass.config_entries.async_get_entry(self._entry_id or self.handler)
        if entry is None:
            raise ValueError("Loona config entry no longer exists")
        return entry

    @property
    def settings(self) -> dict[str, Any]:
        """Read current values after the options manager initializes the flow."""
        return {**self.config_entry.data, **self.config_entry.options}

    def finish(self, changes: dict[str, Any]) -> ConfigFlowResult:
        """Do not reset unrelated fields or duplicate persisted switch states."""
        data = {**self.config_entry.options, **changes}
        for key, value in changes.items():
            if (key in self.config_entry.data and value == self.config_entry.data[key]) or (
                key == CONF_ALWAYS_FORWARD and not value and key not in self.config_entry.data
            ):
                data.pop(key, None)
        return self.async_create_entry(title="", data=data)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer only implemented capabilities in the native menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "dashboards",
                "targets",
                "filters",
                "extra_entities",
                "rules",
                "resource_preview",
                "dependency_preview",
            ],
        )

    async def async_step_dashboards(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Refresh dashboard labels without changing stable identifiers."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := validate_dashboards(self.hass, user_input):
                errors["base"] = error
            else:
                return self.finish(user_input)
        return self.async_show_form(
            step_id="dashboards",
            data_schema=dashboard_schema(self.hass, self.settings),
            errors=errors,
        )

    async def async_step_dependency_preview(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Inspect one dependency at a time without storing any configuration."""
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="not_loaded")
        rows = {row["entity_id"]: row for row in dependency_rows(runtime)}
        selected = (user_input or {}).get("entity", "")
        errors = {} if selected in rows or not selected else {"base": "invalid_selection"}
        row = rows.get(selected)
        reasons = row["reasons"] if row else []
        # Localized prose belongs to HA translations; provenance paths stay literal.
        special = {"extra entity", "include rule", "Loona control or statistic"}
        detail = "\n".join("- " + reason.replace("`", "") for reason in reasons if reason not in special)
        return self.async_show_form(step_id="dependency_preview", errors=errors,
            description_placeholders={
                "count": str(len(rows)), "detail": detail or "-",
                "retained": selected if row and row["status"] == "retained" else "-",
                "excluded": selected if row and row["status"] == "excluded" else "-",
                "unresolved": selected if row and row["unresolved"] else "-",
                "extra": selected if "extra entity" in reasons else "-",
                "rule": selected if "include rule" in reasons else "-",
                "protected": selected if "Loona control or statistic" in reasons else "-",
            },
            data_schema=vol.Schema({vol.Optional("entity", default=selected if selected in rows else ""):
                selector.SelectSelector(selector.SelectSelectorConfig(
                    options=[""] + list(rows), mode=selector.SelectSelectorMode.DROPDOWN,
                ))}))

    async def async_step_targets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Apply target changes to existing managed subscriptions."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := await validate_targets(self.hass, user_input):
                errors["base"] = error
            else:
                return self.finish(user_input)
        return self.async_show_form(
            step_id="targets",
            data_schema=await target_schema(self.hass, self.settings),
            errors=errors,
        )

    async def async_step_filters(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the actual persisted category switch, not a second enabled flag."""
        runtime = getattr(self.config_entry, "runtime_data", None)
        errors: dict[str, str] = {}
        if user_input is not None:
            if runtime is None:
                errors["base"] = "not_loaded"
            else:
                if set(user_input) - (runtime.available_controls - {CONTROL_MASTER}):
                    raise ValueError("Unsupported Loona control")
                for key, enabled in user_input.items():
                    await runtime.async_set_control(key, enabled)
                return self.finish({})
        return self.async_show_form(
            step_id="filters", errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(key, default=runtime.controls[key]): selector.BooleanSelector()
                    for key in (
                        CONTROL_ENTITIES, CONTROL_REGISTRIES, CONTROL_RESOURCES, CONTROL_GRAPHS, CONTROL_MOTION
                    )
                    if runtime is not None and key in runtime.available_controls
                }
            ),
        )

    async def async_step_extra_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Augment discovered dependencies through the native entity picker."""
        errors: dict[str, str] = {}
        if user_input is not None:
            raw = user_input.get(CONF_EXTRA_ENTITIES, [])
            entities = [
                er.async_resolve_entity_id(er.async_get(self.hass), item) or item
                for item in raw
            ]
            if any(not valid_entity_id(item) for item in entities) or len(
                entities
            ) != len(set(entities)):
                errors["base"] = "invalid_selection"
            else:
                return self.finish({CONF_EXTRA_ENTITIES: entities})
        return self.async_show_form(
            step_id="extra_entities",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_EXTRA_ENTITIES,
                        default=self.settings.get(CONF_EXTRA_ENTITIES, []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(multiple=True)
                    )
                }
            ),
        )

    async def async_step_rules(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select known entities and domains without accepting arbitrary text."""
        errors: dict[str, str] = {}
        choices = entity_rule_choices(self.hass, self.settings)
        schema = vol.Schema(
            {
                vol.Optional(key, default=self.settings.get(key, [])):
                    selector.SelectSelector(selector.SelectSelectorConfig(
                        options=values,
                        multiple=True,
                        custom_value=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ))
                for key, values in choices.items()
            }
        )
        if user_input is not None:
            try:
                values = schema(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_selection"
            else:
                if any(len(items) != len(set(items)) for items in values.values()):
                    errors["base"] = "invalid_selection"
                else:
                    return self.finish(values)
        return self.async_show_form(
            step_id="rules",
            errors=errors,
            data_schema=schema,
        )


    async def async_step_resource_preview(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show fixed requirements and optional resource checkboxes together."""
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="not_loaded")
        try:
            report = await runtime.async_resource_preview()
        except CompatibilityError:
            return self.async_abort(reason="resources_unavailable")
        required = {row["url"] for row in report["resources"] if row["status"] == "required"}
        choices = {
            row["url"]: f"{row['url']} ({row['type']})"
            for row in report["resources"] if row["status"] != "required"
        }
        current = self.settings.get(CONF_ALWAYS_FORWARD, [])
        for url in report["stale_exceptions"]:
            choices[url] = url
        editable = CONTROL_RESOURCES in runtime.available_controls
        errors = {}
        if user_input is not None:
            selected = user_input.get(
                CONF_ALWAYS_FORWARD, [url for url in current if url in choices]
            )
            if (not isinstance(selected, list)
                or any(not isinstance(value, str) for value in selected)
                or len(selected) != len(set(selected))
                or not set(selected) <= choices.keys() | required):
                errors["base"] = "invalid_selection"
            elif set(user_input) - {CONF_ALWAYS_FORWARD, CONTROL_RESOURCES}:
                errors["base"] = "invalid_selection"
            elif not editable:
                if user_input:
                    errors["base"] = "invalid_selection"
                else:
                    return self.finish({})
            elif CONTROL_RESOURCES in user_input and not isinstance(user_input[CONTROL_RESOURCES], bool):
                errors["base"] = "invalid_selection"
            else:
                if CONTROL_RESOURCES in user_input:
                    await runtime.async_set_control(CONTROL_RESOURCES, user_input[CONTROL_RESOURCES])
                # Preserve prior explicit choices while they are required. They
                # become editable again if the dashboard stops requiring them.
                saved = (set(selected) - required) | (set(current) & required)
                return self.finish({CONF_ALWAYS_FORWARD: sorted(saved)})
        fixed = [
            f"- `{row['url']}` ({row['type']})"
            for row in report["resources"] if row["status"] == "required"
        ]
        schema: dict[Any, Any] = {}
        if editable:
            schema[vol.Required(CONTROL_RESOURCES, default=runtime.controls[CONTROL_RESOURCES])] = selector.BooleanSelector()
            if choices:
                schema[vol.Optional(
                    CONF_ALWAYS_FORWARD,
                    default=[url for url in current if url in choices],
                )] = selector.SelectSelector(selector.SelectSelectorConfig(
                    options=[selector.SelectOptionDict(value=url, label=label)
                             for url, label in choices.items()],
                    multiple=True, mode=selector.SelectSelectorMode.LIST,
                ))
        return self.async_show_form(
            step_id="resource_preview", errors=errors, data_schema=vol.Schema(schema),
            description_placeholders={
                # Keep HTML out of the translation's ICU message syntax.
                "required_start": "<details><summary>",
                "required_summary_end": "</summary>",
                "required_end": "</details>",
                "required": "\n".join(fixed),
                "required_count": str(len(fixed)),
                "unresolved": ", ".join(report["unresolved_custom_types"]) or "-",
                "unresolved_count": str(len(report["unresolved_custom_types"])),
                "stale": ", ".join(report["stale_exceptions"]) or "-",
                "stale_count": str(len(report["stale_exceptions"])),
            },
        )

    async def async_step_resource_exceptions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Route older flow links to the combined resource settings form."""
        return await self.async_step_resource_preview(user_input)
