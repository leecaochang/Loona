"""Discover dashboard dependencies without evaluating templates or card code."""

from dataclasses import dataclass, field
import re
from typing import Any

from homeassistant.core import valid_entity_id

from .const import ENTITY_KEYS, SERVER_TEMPLATE_CHIP_FIELDS, SERVER_TEMPLATE_FIELDS, TARGET_KEYS
from .templates import template_dependencies


@dataclass(frozen=True)
class DiscoveryContext:
    """A snapshot of states, registry targets, and group memberships."""

    entity_ids: frozenset[str] = frozenset()
    groups: dict[str, frozenset[str]] = field(default_factory=dict)
    targets: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)
    area_names: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryResult:
    """Dependency reasons and incomplete-scope findings for one dashboard."""

    entity_ids: frozenset[str]
    reasons: dict[str, tuple[str, ...]]
    problems: tuple[str, ...]
    warnings: tuple[str, ...]
    targets: dict[str, frozenset[str]] = field(default_factory=dict)

    unknown_cards: bool = False

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


_AUTO_GLOB = re.compile(r"[A-Za-z0-9_.*?\[\]!\- ]+")
# Rules that bound the candidates; attribute and state filters only narrow them in the browser.
_AUTO_NARROWING = ("entity_id", "domain", "area")
_AUTO_RULE_KEYS = frozenset(_AUTO_NARROWING) | {"attributes", "state", "options"}


def auto_entities_matcher(value: Any) -> Any:
    """Mirror auto-entities for plain values and * globs; None means it cannot be bounded."""
    if (not isinstance(value, str) or not value or value.startswith(("$$", "/", "<", ">", "=", "!"))
            or re.search(r"[mhd]\s+ago\s*$", value, re.IGNORECASE)):
        return None
    if "*" not in value:
        return lambda candidate: candidate == value
    if not _AUTO_GLOB.fullmatch(value):
        return None
    # auto-entities anchors the glob as a regular expression with only * rewritten.
    try:
        expression = re.compile(value.replace("*", ".*"))
    except re.error:
        return None
    return lambda candidate: isinstance(candidate, str) and expression.fullmatch(candidate) is not None


def discover(config: dict[str, Any], context: DiscoveryContext) -> DiscoveryResult:
    """Recursively scan known contexts and conservatively expand dependencies."""
    reasons: dict[str, set[str]] = {}
    problems: set[str] = set()
    warnings: set[str] = set()
    unknown_cards = False
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
            if (not isinstance(rule, dict) or set(rule) - _AUTO_RULE_KEYS
                    or not any(key in rule for key in _AUTO_NARROWING)):
                problems.add(f"{location}: unsupported auto-entities filter")
                continue
            matchers = {key: auto_entities_matcher(rule[key]) for key in _AUTO_NARROWING if key in rule}
            if None in matchers.values():
                problems.add(f"{location}: unsupported auto-entities pattern")
                continue
            candidates = set(context.entity_ids)
            if isinstance(rule.get("entity_id"), str) and valid_entity_id(rule["entity_id"]):
                candidates.add(rule["entity_id"])
            if "area" in matchers:
                # auto-entities matches the entity's area, else its device's, by name or ID.
                areas = context.targets.get("area_id", {})
                matched = {area_id for area_id in set(areas) | set(context.area_names)
                           if matchers["area"](area_id) or matchers["area"](context.area_names.get(area_id))}
                candidates &= set().union(*(areas.get(area_id, ()) for area_id in matched))
            for entity_id in candidates:
                if all(matchers[key](entity_id if key == "entity_id" else entity_id.split(".")[0])
                       for key in ("entity_id", "domain") if key in matchers):
                    add(entity_id, f"{location}.filter.include[{index}]")
        # Exclude, attribute and state filters cannot remove dependencies from the safe superset.

    def walk(
        node: Any,
        location: str,
        card_type: str = "",
        entity_id: str | None = None,
        dependency_value: bool = False,
        parent_type: str = "",
        server_rendered: bool = False,
    ) -> None:
        nonlocal unknown_cards
        if isinstance(node, list):
            for index, item in enumerate(node):
                walk(
                    item, f"{location}[{index}]", card_type, entity_id, dependency_value,
                    parent_type, server_rendered,
                )
            return
        if isinstance(node, str):
            if any(marker in node for marker in ("{{", "{%", "[[[")):
                result = template_dependencies(
                    node, card_type=card_type, entity_id=entity_id
                )
                for identifier in result.entity_ids:
                    add(identifier, location)
                # Core renders display Jinja itself; only browser JavaScript needs bounded inputs.
                rendered_by_core = server_rendered and "[[[" not in node
                if dependency_value or not (result.complete or rendered_by_core):
                    problems.add(f"{location}: template dependencies cannot be scoped")
            return
        if not isinstance(node, dict):
            return
        if "strategy" in node:
            problems.add(f"{location}: dashboard strategy cannot be scoped")
        node_type = node.get("type")
        if isinstance(node_type, str):
            # A nested configuration starts a new context, even below styles.
            parent_type, card_type, server_rendered = card_type, node_type, False
            entity_id = node.get("entity")
            if not isinstance(entity_id, str) or not valid_entity_id(entity_id):
                entity_id = None
        if node_type == "custom:auto-entities":
            auto_entities(node, location)
        elif isinstance(node_type, str) and node_type.startswith("custom:"):
            unknown_cards = True
            warnings.add(f"{location}: custom card may need extra entities")
        for key, value in node.items():
            path = f"{location}.{key}"
            if key == "entities" and isinstance(value, dict):
                for name, reference in value.items():
                    mapping_path = f"{path}.{name}"
                    references(reference, mapping_path)
                    walk(reference, mapping_path, card_type, entity_id, True)
                continue
            if key in ENTITY_KEYS:
                references(value, path)
            if key in TARGET_KEYS:
                target(key, value, path)
            if card_type == "area" and key == "area":
                target("area_id", value, path)
            display = (key in {"card_mod", "uix"} or key in SERVER_TEMPLATE_FIELDS.get(card_type, ())
                       or card_type == "template" and parent_type == "custom:mushroom-chips-card"
                       and key in SERVER_TEMPLATE_CHIP_FIELDS)
            walk(
                value,
                path,
                card_type,
                entity_id,
                key in ENTITY_KEYS | TARGET_KEYS | {"type"}
                or card_type == "area"
                and key == "area",
                parent_type,
                server_rendered or display,
            )

    walk(config, "dashboard")
    return DiscoveryResult(
        frozenset(reasons),
        {key: tuple(sorted(value)) for key, value in reasons.items()},
        tuple(sorted(problems)),
        tuple(sorted(warnings)),
        {key: frozenset(values) for key, values in targets.items()},
        unknown_cards,
    )


_PROBLEM_REASONS = (("auto-entities", "auto_entities"), ("template", "template"), ("strategy", "strategy"))


def describe_problem(config: Any, problem: str) -> tuple[str, str]:
    """Name the view and top-level card behind a discovery problem, plus a reason code."""
    location, _, message = problem.partition(": ")
    reason = next((code for needle, code in _PROBLEM_REASONS if needle in message), "other")
    steps = [name or int(index) for name, index in re.findall(r"\.([A-Za-z_]\w*)|\[(\d+)\]", location.removeprefix("dashboard"))]
    places: list[str] = []
    node: Any = config
    try:
        if steps[:1] == ["views"] and isinstance(steps[1], int):
            node = config["views"][steps[1]]
            places.append(str(node.get("title") or node.get("path") or f"#{steps[1] + 1}"))
            rest = steps[2:]
            # A card sits directly in the view or in one of its sections.
            if rest[:1] == ["sections"] and len(rest) > 1 and isinstance(rest[1], int):
                node, rest = node["sections"][rest[1]], rest[2:]
            if rest[:1] in (["cards"], ["badges"]) and len(rest) > 1 and isinstance(rest[1], int):
                card = node[rest[0]][rest[1]]
                title = card.get("title") if isinstance(card, dict) else None
                kind = card.get("type", "card") if isinstance(card, dict) else "card"
                places.append(f"{kind} \"{title}\"" if isinstance(title, str) and title else str(kind))
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    return " / ".join(places), reason


def saved_view_routes(config: dict[str, Any]) -> dict[str, int]:
    """Map unambiguous saved routes using native first-match precedence."""
    views = config.get("views")
    if not isinstance(views, list) or not views or any(not isinstance(view, dict) for view in views):
        return {}
    indices = {str(index) for index in range(len(views))}
    routes = set(indices)
    routes.update(view["path"] for view in views if isinstance(view.get("path"), str) and view["path"])
    plans = {}
    for route in routes:
        # Noncanonical numeric spellings can collide via Core's Number(path).
        # Keep dashboard delivery rather than partially emulating JS coercion.
        if route not in indices:
            numeric_route = route.replace("\ufeff", "").strip()
            if not numeric_route:
                continue
            try:
                float(numeric_route)
            except ValueError:
                try:
                    int(numeric_route, 0)
                except ValueError:
                    pass
                else:
                    continue
            else:
                continue
        # Core takes the first matching path or numeric index, even on collisions.
        index = next(index for index, view in enumerate(views)
                     if view.get("path") == route or str(index) == route)
        if route != "hass-unused-entities":
            plans[route] = index
    return plans


def discover_views(config: dict[str, Any], context: DiscoveryContext) -> dict[str, frozenset[str]]:
    """Scan each saved view with shared config and preserve native route precedence."""
    routes = saved_view_routes(config)
    if not routes:
        return {}
    results = [discover({**config, "views": [view]}, context) for view in config["views"]]
    return {route: results[index].entity_ids for route, index in routes.items() if results[index].complete}
