"""Preview and filter native Lovelace resources without changing their storage."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.components import websocket_api
from homeassistant.components.lovelace import const as lovelace_const
from homeassistant.components.lovelace import resources as native_resources
from homeassistant.components.lovelace.websocket import websocket_lovelace_resources
from homeassistant.core import HomeAssistant, callback

from .compatibility import CompatibilityError, HandlerEntry, HandlerTable
from .const import (
    RESOURCE_CARDS, RESOURCE_COMMANDS, RESOURCE_COMMAND_PROFILES, RESOURCE_CONFIG_KEYS,
    RESOURCE_CORE_VERSIONS, RESOURCE_SHARED, RESOURCE_SHARED_PATHS,
)
from .websocket import ScopePolicy


@dataclass(frozen=True)
class ResourceDependencies:
    """Custom types from every branch, nested card, badge, feature and layout."""

    custom_types: frozenset[str] = frozenset()
    dynamic: bool = False
    configuration_keys: frozenset[str] = frozenset()


def resource_dependencies(configs: Iterable[dict[str, Any]]) -> ResourceDependencies:
    """Read configuration only; never execute or fetch arbitrary module code."""
    types: set[str] = set()
    dynamic = False
    configuration_keys: set[str] = set()

    def walk(node: Any) -> None:
        nonlocal dynamic
        if isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in {"type", "layout_type"} and isinstance(value, str):
                    if value.startswith("custom:"):
                        types.add(value.removeprefix("custom:"))
                    if any(marker in value for marker in ("{{", "{%", "[[[")):
                        dynamic = True
                if key == "strategy":
                    dynamic = True
                walk(value)
        elif isinstance(node, str) and any(marker in node for marker in ("{{", "{%", "[[[")):
            # Templates can generate card configurations as well as values.
            dynamic = True

    for config in configs:
        configuration_keys.update(key for key in RESOURCE_CONFIG_KEYS if isinstance(config.get(key), dict))
        walk(config)
    return ResourceDependencies(frozenset(types), dynamic, frozenset(configuration_keys))


def matches(card_type: str, declarations: tuple[str, ...]) -> bool:
    return any(
        card_type.startswith(value) if value.endswith("-") else card_type == value
        for value in declarations
    )


def resource_report(
    rows: list[dict[str, Any]], dependencies: ResourceDependencies,
    always_forward: Iterable[str] = (),
) -> dict[str, Any]:
    """Classify a fresh native list, preserving URL queries and resource IDs."""
    exceptions = frozenset(always_forward)
    found: set[str] = set()
    report_rows = []
    for row in rows:
        url, kind = row["url"], row["type"]
        parsed = urlsplit(url)
        filename = parsed.path.rsplit("/", 1)[-1]
        declarations = RESOURCE_CARDS.get(filename, ())
        required = {card for card in dependencies.custom_types if matches(card, declarations)}
        # Custom filenames/remotely hosted bundles are unclassified, even if a
        # basename happens to match a supported package.
        local = url.startswith(("/local/", "/hacsfiles/")) and not url.startswith("//")
        if not local or kind not in {"module", "js"}:
            required = set()
        if kind == "css":
            status, reason = "required", "Shared stylesheet"
        elif (kind in {"module", "js"} and not parsed.scheme and not parsed.netloc
              and parsed.path in RESOURCE_SHARED_PATHS):
            status, reason = "required", RESOURCE_SHARED_PATHS[parsed.path]
        elif local and kind in {"module", "js"} and filename in RESOURCE_SHARED:
            status, reason = "required", "Shared native-card and theme styling"
        elif local and kind in {"module", "js"} and filename in RESOURCE_CONFIG_KEYS.values():
            keys = sorted(key for key in dependencies.configuration_keys if RESOURCE_CONFIG_KEYS[key] == filename)
            if keys:
                status, reason = "required", "Dashboard configuration: " + ", ".join(keys)
            else:
                status, reason = "unclassified", "Browser settings or URL options may require this helper"
        elif required:
            status, reason = "required", "Custom types: " + ", ".join(sorted(required))
        elif local and kind in {"module", "js"} and declarations:
            status, reason = "unused", "No matching custom type in selected dashboards"
        else:
            status, reason = "unclassified", "No verified dependency mapping; omitted when enabled"
        if local and kind in {"module", "js"}:
            found.update(required)
        report_rows.append({
            **row, "status": status, "reason": reason,
            "forwarded": status == "required" or url in exceptions,
        })
    return {
        "resources": report_rows,
        "counts": {status: sum(row["status"] == status for row in report_rows)
                   for status in ("required", "unused", "unclassified")},
        "unresolved_custom_types": sorted(dependencies.custom_types - found),
        "dynamic_configuration": dependencies.dynamic,
        "stale_exceptions": sorted(exceptions - {row["url"] for row in rows}),
    }


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
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("url"), str)
            or row.get("type") not in {"module", "js", "css", "html"}
            for row in rows
        ):
            raise CompatibilityError("Native resource list shape changed")
    except Exception as err:
        raise CompatibilityError("Native resource collection could not be read") from err
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
            if self.adapter.targeted(self.connection.user.id):
                if not isinstance(result, list) or any(
                    not isinstance(row, dict) or not isinstance(row.get("url"), str)
                    or row.get("type") not in {"module", "js", "css", "html"}
                    for row in result
                ):
                    raise CompatibilityError("Native resource list shape changed")
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
    ) -> None:
        self.hass, self.policy, self.report, self.on_failure = hass, policy, report, on_failure
        self.observe = observe
        self._table: HandlerTable | None = None
        self._originals: dict[str, HandlerEntry] = {}
        self._owned: dict[str, HandlerEntry] = {}

    def targeted(self, user_id: str) -> bool:
        """Unlike entity subscriptions, an empty retained resource list is valid."""
        return bool(self.policy.enabled and self.policy.complete
                    and (self.policy.all_users or user_id in self.policy.user_ids))

    def install(self) -> None:
        if self._table is not None:
            self.check_ownership()
            return
        if ha_const.__version__ not in RESOURCE_CORE_VERSIONS:
            raise CompatibilityError("Unsupported resource Core version")
        table = self.hass.data.get(websocket_api.DOMAIN)
        if not isinstance(table, dict):
            raise CompatibilityError("Native resource commands are unavailable")
        storage_type = getattr(native_resources, "ResourceStorageCollectionWebsocket", None)
        storage_handler = getattr(storage_type, "ws_list_item", None)
        commands = RESOURCE_COMMAND_PROFILES[ha_const.__version__]
        if any(name in table for name in RESOURCE_COMMANDS if name not in commands):
            raise CompatibilityError("Unexpected resource command for this Core version")
        for name in commands:
            entry = table.get(name)
            if (not isinstance(entry, tuple) or len(entry) != 2
                or entry[0] not in (storage_handler, websocket_lovelace_resources)
                or not (isinstance(entry[1], vol.Schema)
                        or entry[1] is False and getattr(entry[0], "_ws_schema", None) is False)):
                raise CompatibilityError(f"Unrecognized native resource command: {name}")
            # Older no-argument native commands use False for BASE schema only.
            if entry[1] is False:
                continue
            try:
                if entry[1]({"id": 1, "type": name}) != {"id": 1, "type": name}:
                    raise ValueError("Unexpected schema defaults")
            except (vol.Invalid, ValueError) as err:
                raise CompatibilityError("Native resource schema changed") from err
        self._table = cast(HandlerTable, table)
        self._originals = {name: table[name] for name in commands}
        self._owned = {name: (self._list, table[name][1]) for name in commands}
        table.update(self._owned)

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
        if self._table is not None and self.targeted(connection.user.id):
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
