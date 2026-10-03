"""Native singleton setup and options flows for Loona."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    CONTROL_DASHBOARD_LIVE,
    CONF_DASHBOARDS,
    CONF_DASHBOARD_CARDS,
    DASHBOARD_CARDS,
    CONF_ALWAYS_FORWARD,
    CONTROL_RESOURCES,
    CONTROL_RESOURCE_DELAY,
    CONTROL_RESOURCE_PRELOAD, CONTROL_OFFSCREEN, CONTROL_IDLE,
    CONF_IDLE_AFTER, CONF_IDLE_REFRESH, IDLE_AFTER_MINUTES, IDLE_REFRESH_SECONDS,
    IDLE_AFTER_MAX, IDLE_REFRESH_MAX,
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


def validate_idle_settings(values: dict[str, Any]) -> dict[str, int]:
    """Accept whole-number timing only, including native numeric selector values."""
    limits = {CONF_IDLE_AFTER: (1, IDLE_AFTER_MAX), CONF_IDLE_REFRESH: (0, IDLE_REFRESH_MAX)}
    if set(values) != set(limits):
        raise ValueError("invalid_selection")
    for key, value in values.items():
        low, high = limits[key]
        if type(value) not in (int, float) or not low <= value <= high or int(value) != value:
            raise ValueError("invalid_selection")
    return {key: int(value) for key, value in values.items()}


def entity_rule_choices(
    hass: HomeAssistant, current: dict[str, Any]
) -> dict[str, list[str]]:
    """Offer current states, registry entries, domain globs and saved rules."""
    entities = set(hass.states.async_entity_ids()) | set(er.async_get(hass).entities)
    domains = {entity_id.split(".", 1)[0] for entity_id in entities}
    patterns = entities | {f"{domain}.*" for domain in domains}
    choices = {
        CONF_EXTRA_ENTITIES: entities,
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
                        for key, title in sorted(titles.items(), key=lambda item: (item[1].casefold(), item[0]))
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
                        for key, label in sorted(accounts.items(), key=lambda item: (item[1].casefold(), item[0]))
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

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the setup selections."""
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
        """Select active accounts or apply to every account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := await validate_targets(self.hass, user_input):
                errors["base"] = error
            else:
                self._settings.update(user_input)
                return await self.async_step_cards()
        return self.async_show_form(
            step_id="targets",
            data_schema=await target_schema(self.hass, user_input or self._settings),
            errors=errors,
        )

    async def async_step_cards(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Offer either bundled card, both, or no generated dashboard."""
        schema = vol.Schema({vol.Optional(CONF_DASHBOARD_CARDS, default=[]):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=list(DASHBOARD_CARDS), multiple=True,
                translation_key="dashboard_cards", mode=selector.SelectSelectorMode.LIST,
            ))})
        errors = {}
        if user_input is not None:
            try:
                values = schema(user_input)
                cards = values[CONF_DASHBOARD_CARDS]
                if len(cards) != len(set(cards)):
                    raise vol.Invalid("Duplicate card")
            except vol.Invalid:
                errors["base"] = "invalid_selection"
            else:
                self._settings.update(values)
                if cards:
                    return await self.async_step_finish()
                return self.async_create_entry(title="Loona", data=self._settings)
        return self.async_show_form(step_id="cards", data_schema=schema, errors=errors)

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Make the browser refresh requirement visible before completing setup."""
        if user_input is not None:
            return self.async_create_entry(title="Loona", data=self._settings)
        return self.async_show_form(step_id="finish", data_schema=vol.Schema({}), last_step=True)


class LoonaOptionsFlow(OptionsFlow):
    """Update one category while preserving every other saved option."""

    def __init__(self, entry_id: str | None = None) -> None:
        super().__init__()
        self._entry_id = entry_id
        self._pending_cards: dict[str, Any] | None = None

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
                "idle",
                "rules",
                "resource_preview",
                "cards",
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
                if (set(user_input) - (runtime.available_controls - {CONTROL_MASTER})
                    or any(not isinstance(value, bool) for value in user_input.values())):
                    errors["base"] = "invalid_selection"
                else:
                    await runtime.async_set_controls(user_input)
                    return self.finish({})
        return self.async_show_form(
            step_id="filters", errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(key, default=runtime.controls[key]): selector.BooleanSelector()
                    for key in (
                        CONTROL_ENTITIES, CONTROL_DASHBOARD_LIVE, CONTROL_REGISTRIES, CONTROL_RESOURCES, CONTROL_RESOURCE_DELAY, CONTROL_RESOURCE_PRELOAD, CONTROL_GRAPHS, CONTROL_MOTION, CONTROL_OFFSCREEN, CONTROL_IDLE
                    )
                    if runtime is not None and key in runtime.available_controls
                }
            ),
        )

    async def async_step_idle(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Expose the same idle timing in native Configure and the settings card."""
        errors = {}
        if user_input is not None:
            try:
                values = validate_idle_settings(user_input)
            except ValueError:
                errors["base"] = "invalid_selection"
            else:
                return self.finish(values)
        return self.async_show_form(step_id="idle", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_IDLE_AFTER, default=self.settings.get(CONF_IDLE_AFTER, IDLE_AFTER_MINUTES)):
                selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=IDLE_AFTER_MAX, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")),
            vol.Required(CONF_IDLE_REFRESH, default=self.settings.get(CONF_IDLE_REFRESH, IDLE_REFRESH_SECONDS)):
                selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=IDLE_REFRESH_MAX, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s")),
        }))

    async def async_step_rules(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select known entities and domains without accepting arbitrary text."""
        errors: dict[str, str] = {}
        choices = entity_rule_choices(self.hass, self.settings)
        schema = vol.Schema(
            {
                vol.Optional(key, default=self.settings.get(key, [])):
                    (selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)) if key == CONF_EXTRA_ENTITIES
                     else selector.SelectSelector(selector.SelectSelectorConfig(
                        options=[value for value in values if ".*" in value or value in self.settings.get(key, [])]
                        if key in {CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS} else values,
                        multiple=True,
                        custom_value=key in {CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS},
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )))
                for key, values in choices.items()
            }
        )
        if user_input is not None:
            try:
                values = schema(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_selection"
            else:
                if any(len(items) != len(set(items)) or not set(items) <= set(choices[key]) for key, items in values.items()):
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
        current = self.settings.get(CONF_ALWAYS_FORWARD, [])
        choices = {
            row["url"]: f"{row['url']} ({row['type']})"
            for row in report["resources"] if row["status"] == "unused" or row["url"] in current and row["status"] != "required"
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
            for row in report["resources"] if row["status"] != "unused"
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

    async def async_step_cards(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the generated dashboard's card selection."""
        schema = vol.Schema({vol.Optional(CONF_DASHBOARD_CARDS, default=self.settings.get(CONF_DASHBOARD_CARDS, [])):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=list(DASHBOARD_CARDS), multiple=True, translation_key="dashboard_cards",
                mode=selector.SelectSelectorMode.LIST,
            ))})
        errors = {}
        if user_input is not None:
            try:
                values = schema(user_input)
                if len(values[CONF_DASHBOARD_CARDS]) != len(set(values[CONF_DASHBOARD_CARDS])):
                    raise vol.Invalid("Duplicate card")
            except vol.Invalid:
                errors["base"] = "invalid_selection"
            else:
                if self.settings.get(CONF_DASHBOARD_CARDS) and not values[CONF_DASHBOARD_CARDS]:
                    self._pending_cards = values
                    return await self.async_step_confirm_remove_dashboard()
                return self.finish(values)
        return self.async_show_form(step_id="cards", data_schema=schema, errors=errors)

    async def async_step_confirm_remove_dashboard(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Require explicit native-form confirmation before removing the owned board."""
        if self._pending_cards is None:
            return await self.async_step_cards()
        if user_input and user_input.get("confirm") is True:
            values, self._pending_cards = self._pending_cards, None
            return self.finish(values)
        return self.async_show_form(
            step_id="confirm_remove_dashboard",
            data_schema=vol.Schema({vol.Required("confirm", default=False): selector.BooleanSelector()}),
            errors={"base": "confirmation_required"} if user_input is not None else {},
        )
