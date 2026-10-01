"""Configuration keys, defaults, and supported dependency contexts for Loona."""

from typing import Final

DOMAIN: Final = "loona"
SUBSCRIBE_ENTITIES: Final = "subscribe_entities"
SUPPORTED_CORE_VERSIONS: Final = frozenset({"2026.9.3", "2026.9.4"})
VERSION: Final = "0.4.2"
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
CONTROL_MASTER: Final = "enabled"
CONTROL_ENTITIES: Final = "entity_filtering"
CONTROL_REGISTRIES: Final = "registry_filtering"
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
    CONTROL_REGISTRIES: False,
    CONTROL_GRAPHS: False,
    CONTROL_MOTION: False,
}
SCAN_DEBOUNCE: Final = 1.0
MAINTENANCE_SECONDS: Final = 60
METRIC_SECONDS: Final = 30
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
