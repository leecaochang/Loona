"""Configuration keys, defaults, and supported dependency contexts for Loona."""

from typing import Final

DOMAIN: Final = "loona"
SUBSCRIBE_ENTITIES: Final = "subscribe_entities"
PANEL_SUBSCRIBE: Final = "loona/subscribe_panel"
PANEL_COMMAND: Final = "loona/panel"
PANEL_ASSET: Final = "/loona/panel-context.js"
PANEL_POLL_MS: Final = 2000
BOOTSTRAP_TIMEOUT_MS: Final = 2000
RECORDER_CLEANUP_SECONDS: Final = 15
MIN_CORE_VERSION: Final = "2024.6.0"
VERSION: Final = "0.9.6"
CONF_DASHBOARD_CARDS: Final = "dashboard_cards"
DASHBOARD_CARDS: Final = ("statistics", "settings")
CONF_DASHBOARDS: Final = "dashboards"
CONF_TARGET_MODE: Final = "target_mode"
CONF_USER_IDS: Final = "user_ids"
CONF_EXTRA_ENTITIES: Final = "extra_entities"
CONF_INCLUDE_DOMAINS: Final = "include_domains"
CONF_INCLUDE_GLOBS: Final = "include_globs"
CONF_EXCLUDE_GLOBS: Final = "exclude_globs"
TARGET_SELECTED: Final = "selected"
TARGET_ALL: Final = "all"
TARGET_MODES: Final = (TARGET_SELECTED, TARGET_ALL)
DEFAULT_DASHBOARD: Final = "lovelace"
# Native strategies generate built-in cards; unknown strategies retain all files.
RESOURCE_NATIVE_STRATEGIES: Final = frozenset({"map", "iframe", "original-states", "areas", "area", "areas-overview", "home", "home-overview", "home-area", "home-media-players", "home-other-devices"})
CONTROL_MASTER: Final = "enabled"
CONTROL_ENTITIES: Final = "entity_filtering"
CONTROL_DASHBOARD_LIVE: Final = "current_dashboard_updates"
CONTROL_REGISTRIES: Final = "registry_filtering"
CONTROL_RESOURCES: Final = "resource_filtering"
CONTROL_RESOURCE_DELAY: Final = "delay_card_resources"
RESOURCE_DELAY_QUIET_MS: Final = 750
RESOURCE_DELAY_MAX_MS: Final = 10000
RESOURCE_DELAY_LOAD_MS: Final = 10000
RESOURCE_DELAY_IDLE_MS: Final = 1000
CONF_ALWAYS_FORWARD: Final = "always_forward_resources"
RESOURCE_COMMANDS: Final = ("lovelace/resources", "lovelace/resources/list")
# Published bundle names and the custom element families they register.
RESOURCE_CARDS: Final = {
    "card-mod.js": ("mod-card",),
    "bubble-card.js": ("bubble-card",),
    "button-card.js": ("button-card",),
    "mini-graph-card-bundle.js": ("mini-graph-card",),
    "apexcharts-card.js": ("apexcharts-card",),
    "sunsynk-power-flow-card.js": ("sunsynk-power-flow-card",),
    "lovelace-horizon-card.js": ("horizon-card",),
    "stack-in-card.js": ("stack-in-card",),
    "vertical-stack-in-card.js": ("vertical-stack-in-card",),
    "auto-entities.js": ("auto-entities",),
    "layout-card.js": ("layout-card", "gap-card", "layout-break", "grid-layout", "horizontal-layout", "vertical-layout", "masonry-layout"),
    "mushroom.js": ("mushroom-",),
    "yet-another-media-player.js": ("yet-another-media-player",),
    "battery-state-card.js": ("battery-state-card",),
    "plotly-graph-card.js": ("plotly-graph",),
    "my-cards.js": ("my-button", "my-slider", "my-slider-v2"),
    "swipe-card.js": ("swipe-card",),
    "universal-remote-card.min.js": ("android-tv-card", "universal-remote-card"),
    "multiple-entity-row.js": ("multiple-entity-row",),
    "energy-period-selector-plus.js": ("energy-period-selector-plus",),
    "custom-card-features.min.js": ("custom-features-card", "service-call"),
    "calendar-card-pro.js": ("calendar-card-pro",),
    "config-template-card.js": ("config-template-card",),
    "html-template-card.js": ("html-template-card",),
    "nodalia-cards.js": (
        "nodalia-navigation-bar", "nodalia-media-player", "nodalia-light-card",
        "nodalia-fan-card", "nodalia-humidifier-card", "nodalia-circular-gauge-card",
        "nodalia-graph-card", "nodalia-power-flow-card", "nodalia-cover-card",
        "nodalia-climate-card", "nodalia-alarm-panel-card", "nodalia-advance-vacuum-card",
        "nodalia-entity-card", "nodalia-fav-card", "nodalia-insignia-card",
        "nodalia-person-card", "nodalia-scenes-card", "nodalia-weather-card",
        "nodalia-calendar-card", "nodalia-notifications-card", "nodalia-vacuum-card",
        "nodalia-news-card", "nodalia-camera-card", "nodalia-room-summary-card",
    ),
    "loona-deferred-card.js": ("loona-deferred-card",),
}
# card-mod also applies theme styles and patches native cards globally.
RESOURCE_SHARED: Final = frozenset({"card-mod.js", "kiosk-mode.js"})
# Only these fields are known to produce scalar display values or CSS.
RESOURCE_VALUE_FIELDS: Final = {
    "custom:button-card": frozenset({"styles", "name", "label", "state_display", "icon", "color"}),
    "custom:mushroom-template-card": frozenset({"primary", "secondary", "icon", "icon_color", "color", "badge_icon", "badge_color"}),
    "custom:bubble-card": frozenset({"styles"}),
}
NOISY_ENTITY_LIMIT: Final = 1024
NOISY_ENTITY_REPORT_LIMIT: Final = 20
BROWSER_REPORT_COMMAND: Final = "loona/browser_report"
BROWSER_REPORT_LIMIT: Final = 30
BROWSER_SCRIPT_LIMIT: Final = 40
BROWSER_SUBSCRIPTION_LIMIT: Final = 40
BROWSER_MEASURE_MS: Final = 30000
# These cards are installed as frontend modules, outside Lovelace's file list.
BUNDLED_CARD_TYPES: Final = frozenset({"loona-statistics-card", "loona-settings-card"})
# Browser Mod registers this resource for Cast as well as an extra frontend module.
RESOURCE_SHARED_PATHS: Final = {"/browser_mod.js": "Browser Mod frontend service and Cast companion",
                               "/uix/uix.js": "UI eXtension styling and Cast companion"}
RESOURCE_SHARED_TYPES: Final = {"/uix/uix.js": frozenset({"mod-card", "uix-forge"})}
CONTROL_GRAPHS: Final = "visible_first_graphs"
CONTROL_MOTION: Final = "pause_animations_during_loading"
MOTION_QUIET_MS: Final = 750
MOTION_POLL_MS: Final = 100
MOTION_MAX_MS: Final = 10000
MOTION_VIEW_TAGS: Final = ("HUI-SECTIONS-VIEW", "HUI-MASONRY-VIEW")
MOTION_PROGRESS_TAGS: Final = (
    "HA-SPINNER", "HA-PROGRESS-BUTTON",
    "HA-CIRCULAR-PROGRESS", "HA-LINEAR-PROGRESS", "MD-CIRCULAR-PROGRESS",
    "MD-LINEAR-PROGRESS", "MDC-CIRCULAR-PROGRESS",
)
GRAPH_CONTEXT: Final = "loona_graph_loading"
GRAPH_SUBSCRIBE: Final = "loona/subscribe_graph_loading"
GRAPH_QUIET_MS: Final = 750
GRAPH_PROBE_MS: Final = 10000
GRAPH_POLL_MS: Final = 100
GRAPH_TRACE_LIMIT: Final = 200
GRAPH_PROFILES: Final = {
    "sensor": {"height": 120, "size": 3, "columns": 6, "rows": 2},
    "custom:mini-graph-card": {"height": 150, "size": 3, "columns": 6, "rows": 3},
    "custom:apexcharts-card": {"height": 250, "size": 5, "columns": 6, "rows": 5},
}
CONTROL_DEFAULTS: Final = {
    CONTROL_MASTER: True,
    CONTROL_ENTITIES: True,
    CONTROL_DASHBOARD_LIVE: False,
    CONTROL_REGISTRIES: False,
    CONTROL_RESOURCES: False,
    CONTROL_RESOURCE_DELAY: False,
    CONTROL_GRAPHS: False,
    CONTROL_MOTION: False,
}
SCAN_DEBOUNCE: Final = 1.0
MAINTENANCE_SECONDS: Final = 60
METRIC_SECONDS: Final = 30
LIVE_RATE_PRECISION: Final = 1
STATISTICS_DASHBOARD: Final = "loona-statistics"
STATISTICS_ASSET: Final = "/loona/statistics-card.js"
SETTINGS_ASSET: Final = "/loona/settings-card.js"
I18N_ASSET: Final = "/loona/i18n.js"
SETTINGS_COMMAND: Final = "loona/settings"
SETTINGS_SAVE_COMMAND: Final = "loona/save_settings"
SETTINGS_CHOICES_COMMAND: Final = "loona/settings_choices"
SETTINGS_RESTORE_COMMAND: Final = "loona/restore_defaults"
SETTINGS_GROUPS: Final = {
    "controls": frozenset(),
    "dashboards": frozenset({CONF_DASHBOARDS}),
    "targets": frozenset({CONF_TARGET_MODE, CONF_USER_IDS}),
    "rules": frozenset({CONF_EXTRA_ENTITIES, CONF_INCLUDE_DOMAINS, CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS}),
    "resources": frozenset({CONF_ALWAYS_FORWARD}),
    "cards": frozenset({CONF_DASHBOARD_CARDS}),
}
SETTINGS_EMPTY_DEFAULTS: Final = frozenset({CONF_EXTRA_ENTITIES, CONF_INCLUDE_DOMAINS, CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS, CONF_ALWAYS_FORWARD})
SETTINGS_DEFAULTS: Final = {
    CONF_DASHBOARDS: [], CONF_TARGET_MODE: TARGET_SELECTED, CONF_USER_IDS: [],
    CONF_EXTRA_ENTITIES: [], CONF_INCLUDE_DOMAINS: [], CONF_INCLUDE_GLOBS: [],
    CONF_EXCLUDE_GLOBS: [], CONF_ALWAYS_FORWARD: [], CONF_DASHBOARD_CARDS: [],
}
SETTINGS_CHOICE_PAGE: Final = 50
STATISTICS_COMMAND: Final = "loona/statistics"
PAGE_LOAD_COMMAND: Final = "loona/page_load"
PAGE_LOAD_LIMIT: Final = 30
MAX_TEMPLATE_LENGTH: Final = 65536
MAX_TEMPLATE_NODES: Final = 4096
JINJA_STATE_FUNCTIONS: Final = frozenset(
    {"states", "is_state", "is_state_attr", "state_attr", "has_value"}
)
JINJA_FILTERS: Final = frozenset(
    {
        "abs",
        "capitalize",
        "default",
        "float",
        "int",
        "lower",
        "round",
        "string",
        "trim",
        "upper",
    }
)
JINJA_TESTS: Final = frozenset(
    {"boolean", "defined", "false", "none", "number", "string", "true", "undefined"}
)
JS_FUNCTIONS: Final = frozenset(
    {"Boolean", "Number", "String", "parseFloat", "parseInt"}
)
JS_MATH_METHODS: Final = frozenset(
    {"abs", "ceil", "floor", "max", "min", "pow", "round", "trunc"}
)
JS_VALUE_METHODS: Final = frozenset(
    {"toFixed", "toString", "toLowerCase", "toUpperCase", "trim"}
)
JS_RESERVED_NAMES: Final = JS_FUNCTIONS | frozenset(
    {
        "entity",
        "hass",
        "states",
        "Math",
        "true",
        "false",
        "null",
        "undefined",
        "if",
        "else",
        "return",
        "let",
        "const",
        "var",
        "for",
        "while",
        "do",
        "switch",
        "case",
        "default",
        "break",
        "continue",
        "function",
        "new",
        "class",
        "try",
        "catch",
        "finally",
        "throw",
        "delete",
        "typeof",
        "void",
        "await",
        "yield",
        "with",
        "this",
        "import",
        "export",
        "debugger",
        "extends",
        "super",
        "instanceof",
        "in",
    }
)
ENTITY_KEYS: Final = frozenset(
    {"entity", "entity_id", "entities", "badges", "camera_image", "image_entity"}
)
TARGET_KEYS: Final = frozenset({"device_id", "area_id", "floor_id", "label_id"})
RULE_KEYS: Final = (CONF_INCLUDE_DOMAINS, CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS)
