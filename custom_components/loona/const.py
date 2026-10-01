"""Configuration keys, defaults, and supported dependency contexts for Loona."""

from typing import Final

DOMAIN: Final = "loona"
SUBSCRIBE_ENTITIES: Final = "subscribe_entities"
SUPPORTED_CORE_VERSIONS: Final = frozenset({"2026.9.3", "2026.9.4"})
VERSION: Final = "0.2.0"
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
CONTROL_DEFAULTS: Final = {
    CONTROL_MASTER: True,
    CONTROL_ENTITIES: True,
    CONTROL_REGISTRIES: False,
}
SCAN_DEBOUNCE: Final = 1.0
MAINTENANCE_SECONDS: Final = 60
METRIC_SECONDS: Final = 30
ENTITY_KEYS: Final = frozenset(
    {"entity", "entity_id", "entities", "badges", "camera_image", "image_entity"}
)
TARGET_KEYS: Final = frozenset({"device_id", "area_id", "floor_id", "label_id"})
RULE_KEYS: Final = (CONF_INCLUDE_DOMAINS, CONF_INCLUDE_GLOBS, CONF_EXCLUDE_GLOBS)
