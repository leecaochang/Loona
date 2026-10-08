"""Preview and filter native Lovelace resources without changing their storage."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from inspect import isawaitable, unwrap
import re
from typing import Any, cast
from urllib.parse import urlsplit

from homeassistant.components import websocket_api
from homeassistant.components.lovelace import const as lovelace_const
from homeassistant.components.lovelace import resources as native_resources
from homeassistant.components.lovelace import websocket as native_websocket
from homeassistant.core import HomeAssistant, callback

from .compatibility import (
    CompatibilityError, probe_error, HandlerEntry, HandlerTable, ProbeConnection, check_baseline, inspect_native_command,
)
from .const import (
    BUNDLED_CARD_TYPES, RESOURCE_CARDS, RESOURCE_COMMANDS,
    RESOURCE_SHARED, RESOURCE_SHARED_PATHS, RESOURCE_NATIVE_STRATEGIES,
    RESOURCE_VALUE_FIELDS, RESOURCE_SHARED_TYPES,
    MAX_TEMPLATE_LENGTH, SERVER_TEMPLATE_CHIP_FIELDS, SERVER_TEMPLATE_FIELDS,
)
from .templates import template_dependencies
from .dependencies import saved_view_routes
from .websocket import ScopePolicy


@dataclass(frozen=True)
class ResourceDependencies:
    """Custom types from every branch, nested card, badge, feature and layout."""

    custom_types: frozenset[str] = frozenset()
    dynamic: bool = False


def _scalar_template_safe(source: str, card_type: str, entity_id: str | None) -> bool:
    """Classify scalar expressions, including Bubble's CSS interpolations."""
    if len(source) > MAX_TEMPLATE_LENGTH or "[[" in source.replace("[[[", ""):
        return False
    if "${" in source:
        if card_type != "custom:bubble-card":
            return False
        expressions = re.findall(r"\$\{([^{}]*)\}", source)
        if len(expressions) != source.count("${"):
            return False
        for expression in expressions:
            icon_value = re.fullmatch(r"\s*icon\.setAttribute\(\s*(['\"])icon\1\s*,(.*)\)\s*", expression, re.DOTALL)
            if icon_value is not None:
                expression = icon_value[2]
            # Bubble exposes state as the configured entity's scalar state.
            wrapped = "[[[ const state = entity.state; return (" + expression + "); ]]]"
            if not template_dependencies(wrapped, card_type="custom:button-card", entity_id=entity_id).complete:
                return False
        source = re.sub(r"\$\{[^{}]*\}", "", source)
    return template_dependencies(source, card_type=card_type, entity_id=entity_id).complete


def resource_dependencies(configs: Iterable[dict[str, Any]]) -> ResourceDependencies:
    """Read configuration only; never execute or fetch arbitrary module code."""
    types: set[str] = set()
    dynamic = False

    def walk(node: Any, card_type: str = "", scalar: bool = False, card_mod: bool = False, entity: str | None = None,
             parent_type: str = "", server: bool = False) -> None:
        nonlocal dynamic
        if isinstance(node, list):
            for value in node:
                walk(value, card_type, scalar, card_mod, entity, parent_type, server)
        elif isinstance(node, dict):
            # A nested configuration starts a new context, even below styles.
            if isinstance(node.get("type"), str):
                parent_type, card_type = card_type, node["type"]
                scalar = card_mod = server = False
                entity = node.get("entity") if isinstance(node.get("entity"), str) else None
            for key, value in node.items():
                if key in {"type", "layout_type"} and isinstance(value, str):
                    if value.startswith("custom:"):
                        types.add(value.removeprefix("custom:"))
                    if any(marker in value for marker in ("{{", "{%", "[[", "${")):
                        dynamic = True
                if key == "strategy":
                    if not isinstance(value, dict) or value.get("type") not in RESOURCE_NATIVE_STRATEGIES:
                        dynamic = True
                style_context = card_mod or key in {"card_mod", "uix"}
                value_context = (scalar or key in RESOURCE_VALUE_FIELDS.get(card_type, ())
                                 or style_context and key == "style")
                display = (key in {"card_mod", "uix"} or key in SERVER_TEMPLATE_FIELDS.get(card_type, ())
                           or card_type == "template" and parent_type == "custom:mushroom-chips-card"
                           and key in SERVER_TEMPLATE_CHIP_FIELDS)
                walk(value, card_type, value_context and key not in {"type", "layout_type"}, style_context, entity,
                     parent_type, server or display)
        elif isinstance(node, str) and any(marker in node for marker in ("{{", "{%", "[[", "${")):
            # Core renders display Jinja into text or CSS; markdown output keeps only native tags.
            if (server and ("{{" in node or "{%" in node) and "[[" not in node and "${" not in node
                    and not re.search(r"<[a-zA-Z][\w]*-[\w-]+", node)):
                return
            # CSS and known display fields cannot be blanket exemptions for
            # arbitrary JavaScript or strings that construct custom elements.
            safe = scalar and not re.search(r"<[a-zA-Z][\w]*-[\w-]+|['\"`]\s*<", node)
            if safe:
                safe = _scalar_template_safe(node, card_type, entity)
            if not safe:
                dynamic = True

    for config in configs:
        walk(config)
    return ResourceDependencies(frozenset(types), dynamic)


def matches(card_type: str, declarations: tuple[str, ...]) -> bool:
    return any(
        card_type.startswith(value) if value.endswith("-") else card_type == value
        for value in declarations
    )


def resource_view_dependencies(config: dict[str, Any]) -> dict[str, ResourceDependencies]:
    """Keep dashboard-wide declarations and every branch of the initial view."""
    routes = saved_view_routes(config)
    if not routes:
        return {}
    plans = [resource_dependencies([{**config, "views": [view]}]) for view in config["views"]]
    return {route: plans[index] for route, index in routes.items()}


def resource_report(
    rows: list[dict[str, Any]], dependencies: ResourceDependencies,
    always_forward: Iterable[str] = (),
    provided_types: Iterable[str] = (),
) -> dict[str, Any]:
    """Classify a fresh native list, preserving URL queries and resource IDs."""
    exceptions = frozenset(always_forward)
    found: set[str] = set(BUNDLED_CARD_TYPES) | set(provided_types)
    report_rows = []
    for row in rows:
        url, kind = row["url"], row["type"]
        parsed = urlsplit(url)
        filename = parsed.path.rsplit("/", 1)[-1]
        declarations = RESOURCE_CARDS.get(filename, ())
        required = {card for card in dependencies.custom_types if matches(card, declarations)}
        # Custom filenames/remotely hosted bundles are unclassified, even if a
        # basename happens to match a supported package.
        local = url.startswith(("/local/", "/hacsfiles/"))
        if not local or kind not in {"module", "js"}:
            required = set()
        if kind == "css":
            status, reason = "required", "Shared stylesheet"
        elif (kind in {"module", "js"} and not parsed.scheme and not parsed.netloc
              and parsed.path in RESOURCE_SHARED_PATHS):
            status, reason = "required", RESOURCE_SHARED_PATHS[parsed.path]
            found.update(RESOURCE_SHARED_TYPES.get(parsed.path, ()))
        elif local and kind in {"module", "js"} and filename in RESOURCE_SHARED:
            status, reason = "required", "Shared frontend helper"
        elif required:
            status, reason = "required", "Custom types: " + ", ".join(sorted(required))
        elif local and kind in {"module", "js"} and declarations:
            status, reason = "unused", "No matching custom type in configured dashboards"
        else:
            status, reason = "unclassified", "No verified dependency mapping; retained"
        if local and kind in {"module", "js"}:
            found.update(required)
        report_rows.append({
            **row, "status": status, "reason": reason,
            "forwarded": dependencies.dynamic or status != "unused" or url in exceptions,
        })
    unresolved = dependencies.custom_types - found
    if unresolved:
        for item in report_rows:
            item["forwarded"] = True
    return {
        "resources": report_rows,
        "counts": {status: sum(row["status"] == status for row in report_rows)
                   for status in ("required", "unused", "unclassified")},
        "unresolved_custom_types": sorted(unresolved),
        "dynamic_configuration": dependencies.dynamic,
        "stale_exceptions": sorted(exceptions - {row["url"] for row in rows}),
    }


def validate_resource_rows(rows: Any) -> list[dict[str, Any]]:
    """Validate the native list both during probing and on each response."""
    if not isinstance(rows, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("url"), str)
        or row.get("type") not in {"module", "js", "css", "html"} for row in rows
    ):
        raise CompatibilityError("Native resource list shape changed")
    return rows


async def async_resource_rows(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Use the same native collection loading as the Lovelace list handler."""
    data: Any = hass.data.get(getattr(lovelace_const, "LOVELACE_DATA", "lovelace"))
    resources = data.get("resources") if isinstance(data, dict) else getattr(data, "resources", None)
    if resources is None:
        raise CompatibilityError("Native Lovelace resource collection is unavailable")
    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        rows = resources.async_items()
        validate_resource_rows(rows)
    except Exception as err:
        raise probe_error("Native resource collection could not be read", err) from err
    return cast(list[dict[str, Any]], rows)


class _ResourceConnection:
    """Transform only the successful native list result for one request."""

    def __init__(self, adapter: "ResourceAdapter", connection: websocket_api.ActiveConnection) -> None:
        self.adapter, self.connection = adapter, connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self.connection, name)

    @callback
    def send_result(self, msg_id: int, result: Any = None) -> None:
        # Recheck policy after native async loading; a switch may have changed.
        if self.adapter._table is None:
            self.connection.send_result(msg_id, result)
            return
        try:
            self.adapter.check_ownership()
            if self.adapter.targets_connection(self.connection):
                validate_resource_rows(result)
                report = self.adapter.report(result)
                available = len(result)
                result = [row for row, item in zip(result, report["resources"], strict=True)
                          if item["forwarded"]]
                if self.adapter.observe is not None:
                    self.adapter.observe(self.connection, available, len(result))
        except (CompatibilityError, ValueError, TypeError, KeyError) as err:
            self.adapter.fail(CompatibilityError(str(err)))
        self.connection.send_result(msg_id, result)


class ResourceAdapter:
    """Own both list aliases; leave native create/update/delete commands alone."""

    def __init__(
        self, hass: HomeAssistant, policy: ScopePolicy,
        report: Callable[[list[dict[str, Any]]], dict[str, Any]],
        on_failure: Callable[[CompatibilityError], None],
        observe: Callable[[Any, int, int], None] | None = None,
        dashboard_active: Callable[[websocket_api.ActiveConnection], bool] | None = None,
    ) -> None:
        self.hass, self.policy, self.report, self.on_failure = hass, policy, report, on_failure
        self.observe = observe
        self.dashboard_active = dashboard_active
        self._table: HandlerTable | None = None
        self._originals: dict[str, HandlerEntry] = {}
        self._owned: dict[str, HandlerEntry] = {}

    def targeted(self, user_id: str) -> bool:
        """Unlike entity subscriptions, an empty retained resource list is valid."""
        return bool(self.policy.enabled and self.policy.complete
                    and (self.policy.all_users or user_id in self.policy.user_ids))

    def targets_connection(self, connection: websocket_api.ActiveConnection) -> bool:
        """Recheck the current panel when an asynchronous native list finishes."""
        return self.targeted(connection.user.id) and (
            self.dashboard_active is None or self.dashboard_active(connection)
        )

    def install(self) -> None:
        if self._table is not None:
            self.check_ownership()
            return
        table, originals = self._inspect_commands()
        self._table = table
        self._originals = originals
        commands = originals
        self._owned = {name: (self._list, table[name][1]) for name in commands}
        table.update(self._owned)

    def _inspect_commands(self) -> tuple[HandlerTable, dict[str, HandlerEntry]]:
        """Discover installed aliases and validate all before replacing any."""
        check_baseline()
        table = self.hass.data.get(websocket_api.DOMAIN)
        if not isinstance(table, dict):
            raise CompatibilityError("Native resource commands are unavailable")
        storage_type = getattr(native_resources, "ResourceStorageCollectionWebsocket", None)
        candidates = (
            getattr(storage_type, "ws_list_item", None),
            getattr(native_websocket, "websocket_lovelace_resources", None),
        )
        commands = tuple(name for name in RESOURCE_COMMANDS if name in table)
        if not commands:
            raise CompatibilityError("Native resource list commands are unavailable")
        for name in commands:
            entry = table[name]
            native = entry[0] if isinstance(entry, tuple) and len(entry) == 2 else None
            if native not in candidates or native is None:
                raise CompatibilityError(f"Unrecognized native resource command: {name}")
            inspect_native_command(self.hass, name, native, require_schema_identity=False)
        return cast(HandlerTable, table), {name: table[name] for name in commands}

    async def async_probe(self) -> None:
        """Read each native list result without sending to a browser or editing storage."""
        _, originals = self._inspect_commands()
        for name, (native, _) in originals.items():
            connection = ProbeConnection(self.hass)
            try:
                result = unwrap(native)(
                    self.hass, cast(websocket_api.ActiveConnection, connection), {"id": 1, "type": name}
                )
                if isawaitable(result):
                    await result
                validate_resource_rows(connection.result())
            except Exception as err:
                raise probe_error(f"Native resource behavior probe failed: {name}", err) from err
            finally:
                connection.close()

    def check_ownership(self) -> None:
        if self._table is None or any(self._table.get(name) is not entry for name, entry in self._owned.items()):
            raise CompatibilityError("Loona no longer owns resource list commands")

    @callback
    def _list(self, hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        native = self._originals[msg["type"]][0]
        try:
            self.check_ownership()
        except CompatibilityError as err:
            self.fail(err)
        if self._table is not None and self.targets_connection(connection):
            connection = cast(websocket_api.ActiveConnection, _ResourceConnection(self, connection))
        native(hass, connection, msg)

    def set_policy(self, policy: ScopePolicy) -> None:
        self.check_ownership()
        self.policy = policy

    @callback
    def fail(self, error: CompatibilityError) -> None:
        self.uninstall()
        self.on_failure(error)

    def uninstall(self) -> None:
        if self._table is not None:
            for name, entry in self._owned.items():
                if self._table.get(name) is entry:
                    self._table[name] = self._originals[name]
            self._table = None
