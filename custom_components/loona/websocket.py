"""Delegate entity subscriptions and reconcile scope changes without reconnects.

Only the synchronous Core 2026.9.3 and .4 handler is supported. Preparing, publishing,
and retiring subscriptions must remain in one event-loop turn without awaits.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import messages
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
    valid_entity_id,
)

from .compatibility import (
    CompatibilityError,
    HandlerEntry,
    HandlerTable,
    inspect_command,
)
from .const import SUBSCRIBE_ENTITIES

type Payload = bytes | str | dict[str, Any]
type SubscriptionKey = tuple[websocket_api.ActiveConnection, int]


@dataclass(frozen=True, slots=True)
class ScopePolicy:
    """An immutable, already computed union and account targeting policy."""

    entity_ids: frozenset[str] = frozenset()
    user_ids: frozenset[str] = frozenset()
    all_users: bool = False
    enabled: bool = True
    complete: bool = True

    def __post_init__(self) -> None:
        """Reject malformed IDs before a policy reaches the native handler."""
        if any(not valid_entity_id(entity_id) for entity_id in self.entity_ids):
            raise ValueError("Scope contains an invalid entity ID")

    def scope_for(self, user_id: str) -> frozenset[str] | None:
        """An empty or incomplete scope intentionally passes through."""
        if (
            not self.enabled
            or not self.complete
            or not self.entity_ids
            or not (self.all_users or user_id in self.user_ids)
        ):
            return None
        return self.entity_ids


class _SubscriptionRelay:
    """Per-subscription facade; never change the real connection's sender."""

    def __init__(
        self, connection: websocket_api.ActiveConnection, *, acknowledge: bool
    ) -> None:
        self.connection = connection
        self.user = connection.user
        self.logger = connection.logger
        self.subscriptions = connection.subscriptions
        self.acknowledge = acknowledge
        self.active = True
        self.buffer: list[Payload] | None = []

    @callback
    def send_result(self, msg_id: int, result: Any = None) -> None:
        """Keep the initial acknowledgement; suppress replacement replies."""
        if self.acknowledge:
            self.send_message(
                messages.message_to_json_bytes(messages.result_message(msg_id, result))
            )

    @callback
    def send_message(self, payload: Payload) -> None:
        """Gate queued callbacks from retired generations without parsing JSON."""
        if not self.active:
            return
        if self.buffer is not None:
            self.buffer.append(payload)
        else:
            self.connection.send_message(payload)

    def flush(self) -> None:
        """Publish the staged snapshot in protocol order."""
        pending = self.buffer
        self.buffer = None
        assert pending is not None
        for payload in pending:
            self.send_message(payload)


@dataclass(slots=True)
class _Subscription:
    """One listener plus a conservative superset of possible client IDs."""

    connection: websocket_api.ActiveConnection
    request: dict[str, Any]
    scope: frozenset[str] | None
    relay: _SubscriptionRelay
    native_unsubscribe: Callable[[], Any]
    possible_ids: set[str]
    owned_unsubscribe: Callable[[], None] | None = None

    def stop(self) -> None:
        """Suppress scheduled deliveries before releasing the old listener."""
        self.relay.active = False
        self.native_unsubscribe()


class SubscriptionAdapter:
    """Own one command replacement and its tracked unscoped subscriptions."""

    def __init__(self, hass: HomeAssistant, policy: ScopePolicy) -> None:
        self.hass = hass
        self.policy = policy
        self._table: HandlerTable | None = None
        self._original: HandlerEntry | None = None
        self._owned_entry: HandlerEntry | None = None
        self._records: dict[SubscriptionKey, _Subscription] = {}
        self._unsubscribe_lifecycle: Callable[[], None] | None = None

    @property
    def managed_count(self) -> int:
        """Tracked unscoped subscriptions, including intentional bypasses."""
        return len(self._records)

    @property
    def filtered_count(self) -> int:
        """Tracked subscriptions with a nonempty restricted scope."""
        return sum(record.scope is not None for record in self._records.values())

    @callback
    def install(self) -> None:
        """Install after native registration, without replacing another owner."""
        if self._table is not None:
            self._check_owner()
            return
        table, original = inspect_command(self.hass)
        self._table, self._original = table, original
        self._owned_entry = (self._handle, original[1])
        self._unsubscribe_lifecycle = self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._track_creations
        )
        table[SUBSCRIBE_ENTITIES] = self._owned_entry

    def _check_owner(self) -> None:
        """A later integration's replacement is never overwritten."""
        if (
            self._table is None
            or self._table.get(SUBSCRIBE_ENTITIES) is not self._owned_entry
        ):
            raise CompatibilityError("Loona no longer owns subscribe_entities")

    @callback
    def _track_creations(self, event: Event[EventStateChangedData]) -> None:
        """Track new IDs for bypassed clients, without inspecting state payloads."""
        if event.data["old_state"] is not None:
            return
        entity_id = event.data["entity_id"]
        for record in self._records.values():
            if record.scope is None:
                record.possible_ids.add(entity_id)

    @callback
    def _handle(
        self,
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Keep explicit entity lists and nonempty native filters untouched."""
        assert self._original is not None
        if "entity_ids" in msg or any(
            any(msg.get(key, {}).values()) for key in ("include", "exclude")
        ):
            self._original[0](hass, connection, msg)
            return
        candidate = self._prepare(
            connection, msg, self.policy.scope_for(connection.user.id), initial=True
        )
        self._publish(candidate, previous=None, managed=True)

    def _prepare(
        self,
        connection: websocket_api.ActiveConnection,
        request: dict[str, Any],
        scope: frozenset[str] | None,
        *,
        initial: bool = False,
    ) -> _Subscription:
        """Stage Core's listener and snapshot; roll back on handler failure."""
        assert self._original is not None
        msg_id = request["id"]
        previous_callback = connection.subscriptions.get(msg_id)
        relay = _SubscriptionRelay(connection, acknowledge=initial)
        effective = dict(request)
        if scope is not None:
            effective["entity_ids"] = sorted(scope)
        possible_ids = set(
            scope if scope is not None else self.hass.states.async_entity_ids()
        )
        try:
            self._original[0](
                self.hass, cast(websocket_api.ActiveConnection, relay), effective
            )
            native_unsubscribe = connection.subscriptions[msg_id]
        except Exception:
            relay.active = False
            created = connection.subscriptions.get(msg_id)
            if created is not None and created is not previous_callback:
                created()
            raise
        finally:
            if previous_callback is None:
                connection.subscriptions.pop(msg_id, None)
            else:
                connection.subscriptions[msg_id] = previous_callback
        return _Subscription(
            connection, dict(request), scope, relay, native_unsubscribe, possible_ids
        )

    def _publish(
        self,
        candidate: _Subscription,
        *,
        previous: _Subscription | None,
        managed: bool,
    ) -> None:
        """Retire old callbacks, remove old states, then send the native snapshot."""
        connection = candidate.connection
        msg_id = candidate.request["id"]
        key = (connection, msg_id)
        if previous is not None:
            previous.stop()
        if managed:

            @callback
            def unsubscribe() -> None:
                """Release tracking on client unsubscribe or connection close."""
                if self._records.get(key) is candidate:
                    self._records.pop(key)
                    candidate.stop()

            candidate.owned_unsubscribe = unsubscribe
            self._records[key] = candidate
            connection.subscriptions[msg_id] = unsubscribe
        else:
            connection.subscriptions[msg_id] = candidate.native_unsubscribe
            self._records.pop(key, None)
        if previous is not None and previous.possible_ids:
            connection.send_event(msg_id, {"r": sorted(previous.possible_ids)})
        candidate.relay.flush()

    def _stage_changes(
        self, policy: ScopePolicy, *, unloading: bool = False
    ) -> list[tuple[_Subscription, _Subscription]]:
        """Stage all listeners before changing any client or published policy."""
        staged: list[tuple[_Subscription, _Subscription]] = []
        try:
            for previous in self._records.values():
                if (
                    previous.connection.subscriptions.get(previous.request["id"])
                    is not previous.owned_unsubscribe
                ):
                    if unloading:
                        continue
                    raise CompatibilityError(
                        "Another owner replaced a managed listener"
                    )
                scope = (
                    None if unloading else policy.scope_for(previous.connection.user.id)
                )
                if unloading or scope != previous.scope:
                    candidate = self._prepare(
                        previous.connection, previous.request, scope
                    )
                    staged.append((previous, candidate))
        except Exception:
            for _, candidate in staged:
                candidate.stop()
            raise
        return staged

    @callback
    def set_policy(self, policy: ScopePolicy) -> None:
        """Apply scope/target/bypass changes synchronously under original IDs."""
        self._check_owner()
        staged = self._stage_changes(policy)
        self.policy = policy
        for previous, candidate in staged:
            self._publish(candidate, previous=previous, managed=True)

    @callback
    def uninstall(self) -> None:
        """Restore full native subscriptions and only the command still owned."""
        if self._table is None:
            return
        staged = self._stage_changes(self.policy, unloading=True)
        for previous, candidate in staged:
            self._publish(candidate, previous=previous, managed=False)
        for record in tuple(self._records.values()):
            record.stop()
            self._records.pop((record.connection, record.request["id"]))
        if self._table.get(SUBSCRIBE_ENTITIES) is self._owned_entry:
            assert self._original is not None
            self._table[SUBSCRIBE_ENTITIES] = self._original
        assert self._unsubscribe_lifecycle is not None
        self._unsubscribe_lifecycle()
        self._unsubscribe_lifecycle = None
        self._table = self._original = self._owned_entry = None
