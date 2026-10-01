"""Discover dashboard dependencies without evaluating templates or card code."""

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
import re
from typing import Any

from homeassistant.core import valid_entity_id

from .const import ENTITY_KEYS, TARGET_KEYS

_TEMPLATE_LITERAL = re.compile(
    r"(?:states|is_state|is_state_attr|state_attr)\s*\(\s*['\"]([a-z0-9_]+\.[a-z0-9_]+)['\"]"
    r"|(?:hass\.)?states\s*\[\s*['\"]([a-z0-9_]+\.[a-z0-9_]+)['\"]\s*\]"
    r"|states\.([a-z0-9_]+\.[a-z0-9_]+)"
)


@dataclass(frozen=True)
class DiscoveryContext:
    """A snapshot of states, registry targets, and group memberships."""

    entity_ids: frozenset[str] = frozenset()
    groups: dict[str, frozenset[str]] = field(default_factory=dict)
    targets: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryResult:
    """Dependency reasons and incomplete-scope findings for one dashboard."""

    entity_ids: frozenset[str]
    reasons: dict[str, tuple[str, ...]]
    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    targets: dict[str, frozenset[str]] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        """Only a scan without unsafe dynamic constructs is trustworthy."""
        return not self.problems


def valid_glob(pattern: str) -> bool:
    """Accept entity globs with balanced character classes and no whitespace."""
    if not isinstance(pattern, str) or pattern.count(".") != 1:
        return False
    if not re.fullmatch(r"[a-z0-9_.*?\[\]!\-]+", pattern):
        return False
    if "[]" in pattern or "[!]" in pattern:
        return False
    depth = 0
    for character in pattern:
        if character == "[":
            if depth:
                return False
            depth = 1
        elif character == "]":
            if not depth:
                return False
            depth = 0
    return not depth and not pattern.startswith(".") and not pattern.endswith(".")


def discover(config: dict[str, Any], context: DiscoveryContext) -> DiscoveryResult:
    """Recursively scan known contexts and conservatively expand dependencies."""
    reasons: dict[str, set[str]] = {}
    problems: set[str] = set()
    warnings: set[str] = set()
    targets: dict[str, set[str]] = {key: set() for key in TARGET_KEYS}

    def add(
        entity_id: str, location: str, ancestry: frozenset[str] = frozenset()
    ) -> None:
        if not isinstance(entity_id, str) or not valid_entity_id(entity_id):
            return
        reasons.setdefault(entity_id, set()).add(location)
        if entity_id in ancestry:
            return
        for member in context.groups.get(entity_id, ()):
            add(member, f"group:{entity_id}", ancestry | {entity_id})

    def references(value: Any, location: str) -> None:
        if isinstance(value, str):
            for entity_id in value.split(","):
                add(entity_id.strip(), location)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                references(item, f"{location}[{index}]")
        elif isinstance(value, dict):
            walk(value, location)

    def target(key: str, value: Any, location: str) -> None:
        values = value if isinstance(value, list) else [value]
        for identifier in values:
            if not isinstance(identifier, str):
                continue
            targets[key].add(identifier)
            for entity_id in context.targets.get(key, {}).get(identifier, ()):
                add(entity_id, location)

    def auto_entities(card: dict[str, Any], location: str) -> None:
        filters = card.get("filter", {})
        if not isinstance(filters, dict) or "template" in filters:
            problems.add(f"{location}: auto-entities template filter cannot be scoped")
            return
        includes = filters.get("include", [])
        if not isinstance(includes, list):
            problems.add(f"{location}: invalid auto-entities include filters")
            return
        for index, rule in enumerate(includes):
            if not isinstance(rule, dict) or set(rule) - {
                "entity_id",
                "domain",
                "options",
            }:
                problems.add(f"{location}: unsupported auto-entities filter")
                continue
            pattern = rule.get("entity_id", "*.*")
            domain = rule.get("domain", "*")
            if (
                not isinstance(pattern, str)
                or not valid_glob(pattern)
                or not isinstance(domain, str)
                or not re.fullmatch(r"[a-z0-9_*?]+", domain)
            ):
                problems.add(f"{location}: unsupported auto-entities pattern")
                continue
            candidates = set(context.entity_ids)
            if valid_entity_id(pattern):
                candidates.add(pattern)
            for entity_id in candidates:
                if fnmatchcase(entity_id, pattern) and fnmatchcase(
                    entity_id.split(".")[0], domain
                ):
                    add(entity_id, f"{location}.filter.include[{index}]")
        # Exclude filters cannot remove dependencies from the safe superset.

    def walk(node: Any, location: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{location}[{index}]")
            return
        if isinstance(node, str):
            if any(marker in node for marker in ("{{", "{%", "[[[")):
                for match in _TEMPLATE_LITERAL.finditer(node):
                    add(next(group for group in match.groups() if group), location)
                problems.add(f"{location}: runtime template requires a complete scope")
            return
        if not isinstance(node, dict):
            return
        if "strategy" in node:
            problems.add(f"{location}: dashboard strategy cannot be scoped")
        card_type = node.get("type", "")
        if card_type == "custom:auto-entities":
            auto_entities(node, location)
        elif isinstance(card_type, str) and card_type.startswith("custom:"):
            warnings.add(f"{location}: custom card may need extra entities")
        for key, value in node.items():
            path = f"{location}.{key}"
            if key in ENTITY_KEYS:
                references(value, path)
            if key in TARGET_KEYS:
                target(key, value, path)
            if card_type == "area" and key == "area":
                target("area_id", value, path)
            walk(value, path)

    walk(config, "dashboard")
    return DiscoveryResult(
        frozenset(reasons),
        {key: tuple(sorted(value)) for key, value in reasons.items()},
        tuple(sorted(problems)),
        tuple(sorted(warnings)),
        {key: frozenset(values) for key, values in targets.items()},
    )
