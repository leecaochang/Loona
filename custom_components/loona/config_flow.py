"""Native singleton setup and options flows for Loona."""

import re
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
    CONF_TARGET_MODE,
    CONF_USER_IDS,
    CONF_EXTRA_ENTITIES,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_GLOBS,
    CONF_EXCLUDE_GLOBS,
    CONTROL_ENTITIES,
    CONTROL_GRAPHS,
    CONTROL_MOTION,
    CONTROL_REGISTRIES,
    DOMAIN,
    TARGET_ALL,
    TARGET_SELECTED,
    TARGET_MODES,
)
from .dashboard import dashboard_titles
from .dependencies import valid_glob


async def human_accounts(hass: HomeAssistant) -> dict[str, str]:
    """Keep active human accounts selectable, including administrators."""
    return {
        user.id: f"{user.name or 'Unnamed account'}{' (administrator)' if user.is_admin else ''}"
        for user in await hass.auth.async_get_users()
        if user.is_active and not user.system_generated
    }


def dashboard_schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    """Keep stale values visible so users can remove them deliberately."""
    titles = dashboard_titles(hass)
    for key in current.get(CONF_DASHBOARDS, []):
        titles.setdefault(key, f"{key} (unavailable)")
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
        accounts.setdefault(key, "Unavailable account")
    return vol.Schema(
        {
            vol.Required(
                CONF_TARGET_MODE, default=current.get(CONF_TARGET_MODE, TARGET_SELECTED)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=TARGET_SELECTED, label="Selected accounts"
                        ),
                        selector.SelectOptionDict(
                            value=TARGET_ALL, label="All accounts"
                        ),
                    ],
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
        return LoonaOptionsFlow()

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

    @property
    def settings(self) -> dict[str, Any]:
        """Read current values after the options manager initializes the flow."""
        return {**self.config_entry.data, **self.config_entry.options}

    def finish(self, changes: dict[str, Any]) -> ConfigFlowResult:
        """Do not reset unrelated fields or duplicate persisted switch states."""
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **changes}
        )

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
                await runtime.async_set_control(
                    CONTROL_ENTITIES, user_input[CONTROL_ENTITIES]
                )
                if CONTROL_REGISTRIES in user_input:
                    await runtime.async_set_control(
                        CONTROL_REGISTRIES, user_input[CONTROL_REGISTRIES]
                    )
                if CONTROL_GRAPHS in user_input:
                    await runtime.async_set_control(
                        CONTROL_GRAPHS, user_input[CONTROL_GRAPHS]
                    )
                if CONTROL_MOTION in user_input:
                    await runtime.async_set_control(
                        CONTROL_MOTION, user_input[CONTROL_MOTION]
                    )
                return self.finish({})
        current = runtime.controls[CONTROL_ENTITIES] if runtime else True
        return self.async_show_form(
            step_id="filters",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONTROL_ENTITIES, default=current
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONTROL_REGISTRIES,
                        default=runtime.controls[CONTROL_REGISTRIES]
                        if runtime
                        else False,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONTROL_GRAPHS,
                        default=runtime.controls[CONTROL_GRAPHS] if runtime else False,
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONTROL_MOTION,
                        default=runtime.controls[CONTROL_MOTION] if runtime else False,
                    ): selector.BooleanSelector(),
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
        """Keep optional, potentially card-breaking exclusions in Advanced."""
        errors: dict[str, str] = {}
        if user_input is not None:
            domains = user_input.get(CONF_INCLUDE_DOMAINS, [])
            globs = user_input.get(CONF_INCLUDE_GLOBS, []) + user_input.get(
                CONF_EXCLUDE_GLOBS, []
            )
            if any(
                not re.fullmatch(r"[a-z_][a-z0-9_]*", domain) for domain in domains
            ) or any(not valid_glob(pattern) for pattern in globs):
                errors["base"] = "invalid_pattern"
            elif any(len(values) != len(set(values)) for values in user_input.values()):
                errors["base"] = "invalid_selection"
            else:
                return self.finish(user_input)
        return self.async_show_form(
            step_id="rules",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        key, default=self.settings.get(key, [])
                    ): selector.TextSelector(selector.TextSelectorConfig(multiple=True))
                    for key in (
                        CONF_INCLUDE_DOMAINS,
                        CONF_INCLUDE_GLOBS,
                        CONF_EXCLUDE_GLOBS,
                    )
                }
            ),
        )
