"""Delegate entity subscriptions and reconcile scope changes without reconnects.

Delegate to the native synchronous handler after its capability probe passes. Preparing,
publishing, and retiring subscriptions stay in one event-loop turn without awaits.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, cast
from weakref import WeakSet

from homeassistant.components import websocket_api
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components.websocket_api import messages
from homeassistant.components.websocket_api import commands
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
from .statistics import LiveStatistics

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
    retained_scope: frozenset[str] | None
    relay: _SubscriptionRelay
    native_unsubscribe: Callable[[], Any]
    possible_ids: set[str]
    initial_counts: dict[str, int] | None = None
    resource_counts: dict[str, int] | None = None
    owned_unsubscribe: Callable[[], None] | None = None

    def stop(self) -> None:
        """Suppress scheduled deliveries before releasing the old listener."""
        self.relay.active = False
        self.native_unsubscribe()


class SubscriptionAdapter:
    """Own one command replacement and its tracked unscoped subscriptions."""

    def __init__(self, hass: HomeAssistant, policy: ScopePolicy, statistics: LiveStatistics | None = None, dashboard_active: Callable[[websocket_api.ActiveConnection], bool] | None = None, delivery_scope: Callable[[websocket_api.ActiveConnection, frozenset[str]], frozenset[str]] | None = None, idle: Callable[[websocket_api.ActiveConnection], bool] | None = None) -> None:
        self.hass = hass
        self.policy = policy
        self.statistics = statistics
        self.dashboard_active = dashboard_active
        self.delivery_scope = delivery_scope
        self.idle = idle
        self._table: HandlerTable | None = None
        self._original: HandlerEntry | None = None
        self._owned_entry: HandlerEntry | None = None
        self._records: dict[SubscriptionKey, _Subscription] = {}
        self._explicit_subscriptions: WeakSet[Any] = WeakSet()
        self._unsubscribe_lifecycle: Callable[[], None] | None = None

    @property
    def managed_count(self) -> int:
        """Tracked unscoped subscriptions, including intentional bypasses."""
        return len(self._records)

    @property
    def filtered_count(self) -> int:
        """Tracked subscriptions with a nonempty restricted scope."""
        return sum(record.scope is not None for record in self._records.values())

    def feed_report(self) -> list[tuple[websocket_api.ActiveConnection, bool]]:
        """Each tracked subscription's connection and whether it is filtered."""
        return [(record.connection, record.scope is not None) for record in self._records.values()]

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
        """Count eligible logical changes and track new IDs for bypassed clients."""
        entity_id = event.data["entity_id"]
        for record in self._records.values():
            user = record.connection.user
            permissions = user.permissions
            readable = (user.is_admin or permissions.access_all_entities(POLICY_READ)
                        or permissions.check_entity(entity_id, POLICY_READ))
            if (event.data["old_state"] is None and readable
                and (record.retained_scope is None or entity_id in record.retained_scope)):
                record.possible_ids.add(entity_id)
            statistics = self.statistics
            if (statistics is None or entity_id in statistics.ignored
                or not record.relay.active
                or record.connection.subscriptions.get(record.request["id"]) is not record.owned_unsubscribe
                or not (self.policy.all_users or user.id in self.policy.user_ids)):
                continue
            permissions = user.permissions
            if (not user.is_admin and not permissions.access_all_entities(POLICY_READ)
                and not permissions.check_entity(entity_id, POLICY_READ)):
                continue
            statistics.record(record.scope is None or entity_id in record.scope, entity_id)

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
            # Explicit full feeds have the same native callback as early feeds.
            # Remember requests seen here without retaining their connections.
            if isinstance(remove := connection.subscriptions.get(msg["id"]), partial):
                self._explicit_subscriptions.add(remove)
            return
        retained = self._scope_for(self.policy, connection)
        candidate = self._prepare(connection, msg, self._delivery_for(connection, retained), retained, initial=True)
        self._publish(candidate, previous=None, managed=True)

    def _scope_for(self, policy: ScopePolicy, connection: websocket_api.ActiveConnection) -> frozenset[str] | None:
        """Runtime filtering requires an explicitly reported selected dashboard."""
        if self.dashboard_active is not None and not self.dashboard_active(connection):
            return None
        return policy.scope_for(connection.user.id)

    def _delivery_for(self, connection: websocket_api.ActiveConnection, retained: frozenset[str] | None) -> frozenset[str] | None:
        """Only narrow an already eligible union; empty native scopes mean full."""
        if retained is None or self.delivery_scope is None:
            return retained
        if self.idle is not None and self.idle(connection):
            return frozenset()
        delivery = self.delivery_scope(connection, retained) & retained
        return delivery or retained

    def _prepare(
        self,
        connection: websocket_api.ActiveConnection,
        request: dict[str, Any],
        scope: frozenset[str] | None,
        retained_scope: frozenset[str] | None,
        *,
        initial: bool = False,
        refresh_retained: bool = False,
        parked_snapshot: frozenset[str] | None = None,
    ) -> _Subscription:
        """Stage Core's listener and snapshot; roll back on handler failure."""
        assert self._original is not None
        if scope == frozenset():
            # Native empty entity_ids means full data. Park the live listener
            # explicitly, retaining a permission-safe native snapshot instead.
            assert retained_scope
            if parked_snapshot is None and not initial and not refresh_retained and self.delivery_scope:
                parked_snapshot = self.delivery_scope(connection, retained_scope) & retained_scope
            parked = self._prepare(connection, request, parked_snapshot or retained_scope, retained_scope, initial=initial)
            parked.stop()
            relay = _SubscriptionRelay(connection, acknowledge=initial)
            relay.buffer = parked.relay.buffer
            return _Subscription(connection, dict(request), scope, retained_scope, relay,
                                 lambda: None, parked.possible_ids, parked.initial_counts)
        msg_id = request["id"]
        previous_callback = connection.subscriptions.get(msg_id)
        seed = None
        if scope != retained_scope and (initial or refresh_retained):
            # Use Core itself for the permission-safe union snapshot. Its
            # temporary listener is retired before staging the live listener,
            # all in the same synchronous event-loop turn.
            seed = self._prepare(connection, request, retained_scope, retained_scope, initial=initial)
            seed.stop()
        relay = _SubscriptionRelay(connection, acknowledge=initial and seed is None)
        effective = dict(request)
        if scope is not None:
            effective["entity_ids"] = sorted(scope)
        user = connection.user
        permissions = user.permissions
        allowed = {entity_id for entity_id in self.hass.states.async_entity_ids()
                   if user.is_admin or permissions.access_all_entities(POLICY_READ)
                   or permissions.check_entity(entity_id, POLICY_READ)}
        possible_ids = allowed if retained_scope is None else allowed & retained_scope
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
        counts = None
        if seed is not None:
            relay.buffer = seed.relay.buffer
        if initial and self.statistics is not None:
            counts = {"available": len(allowed), "sent": len(possible_ids)}
        return _Subscription(
            connection, dict(request), scope, retained_scope, relay, native_unsubscribe, possible_ids,
            counts,
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
            candidate.initial_counts = previous.initial_counts
            candidate.resource_counts = previous.resource_counts
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
        removed = previous.possible_ids - candidate.possible_ids if previous else set()
        if removed:
            connection.send_event(msg_id, {"r": sorted(removed)})
        candidate.relay.flush()

    def _stage_changes(
        self, policy: ScopePolicy, *, unloading: bool = False,
        connection: websocket_api.ActiveConnection | None = None,
    ) -> list[tuple[_Subscription, _Subscription]]:
        """Stage all listeners before changing any client or published policy."""
        staged: list[tuple[_Subscription, _Subscription]] = []
        try:
            for previous in self._records.values():
                if connection is not None and previous.connection is not connection:
                    continue
                if (
                    previous.connection.subscriptions.get(previous.request["id"])
                    is not previous.owned_unsubscribe
                ):
                    if unloading:
                        continue
                    raise CompatibilityError(
                        "Another owner replaced a managed listener"
                    )
                retained = (
                    None if unloading else self._scope_for(policy, previous.connection)
                )
                scope = self._delivery_for(previous.connection, retained)
                if unloading or scope != previous.scope or retained != previous.retained_scope:
                    candidate = self._prepare(
                        previous.connection, previous.request, scope, retained,
                        refresh_retained=retained != previous.retained_scope or previous.scope == frozenset(),
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
    def refresh_connection(self, connection: websocket_api.ActiveConnection) -> None:
        """Reconcile this socket's ordinary feeds after a panel transition."""
        self._check_owner()
        staged = self._stage_changes(self.policy, connection=connection)
        for previous, candidate in staged:
            self._publish(candidate, previous=previous, managed=True)

    @callback
    def refresh_idle(self, connection: websocket_api.ActiveConnection) -> None:
        """Refresh parked feeds from Core snapshots without replaying stale diffs."""
        self._check_owner()
        staged: list[tuple[_Subscription, _Subscription]] = []
        try:
            for previous in self._records.values():
                if previous.connection is not connection or previous.scope != frozenset():
                    continue
                if connection.subscriptions.get(previous.request["id"]) is not previous.owned_unsubscribe:
                    raise CompatibilityError("Another owner replaced a parked listener")
                retained = self._scope_for(self.policy, connection)
                if retained is None or self._delivery_for(connection, retained) != frozenset():
                    continue
                delivery = self.delivery_scope(connection, retained) & retained if self.delivery_scope else retained
                staged.append((previous, self._prepare(connection, previous.request, frozenset(), retained,
                                                       parked_snapshot=delivery or retained)))
        except Exception:
            for _, candidate in staged:
                candidate.stop()
            raise
        for previous, candidate in staged:
            self._publish(candidate, previous=previous, managed=True)

    def needs_resubscribe(self, connection: websocket_api.ActiveConnection) -> bool:
        """Detect early native feeds without guessing their original request scope."""
        forward = getattr(commands, "_forward_entity_changes", None)
        if forward is None:
            return False
        for msg_id, remove in tuple(connection.subscriptions.items()):
            if ((connection, msg_id) in self._records or not isinstance(remove, partial)
                or remove in self._explicit_subscriptions
                or remove.func != self.hass.bus._async_remove_listener
                or len(remove.args) != 2 or remove.args[0] != EVENT_STATE_CHANGED):
                continue
            job, event_filter = remove.args[1]
            listener = job.target
            if (event_filter is not None or not isinstance(listener, partial)
                or listener.func is not forward):
                continue
            sender = listener.args[0]
            relay = getattr(sender, "__self__", None)
            if (sender != connection.send_message
                and not (type(relay) is _SubscriptionRelay and relay.connection is connection
                         and relay.active and sender == relay.send_message)):
                continue
            if (len(listener.args) == 5 and listener.args[1] is None
                and listener.args[2] is None and listener.args[3] is connection.user
                and listener.args[4] == str(msg_id).encode()):
                return True
            if (len(listener.args) == 4 and listener.args[1] == set()
                and listener.args[2] is connection.user and listener.args[3] == str(msg_id).encode()):
                return True
        return False

    def initial_counts(self, connection: websocket_api.ActiveConnection) -> dict[str, int] | None:
        """Return the latest ordinary initial snapshot for this exact socket."""
        return next((record.initial_counts for record in reversed(tuple(self._records.values()))
                     if record.connection is connection and record.initial_counts is not None), None)

    def observe_resources(self, connection: websocket_api.ActiveConnection, available: int, sent: int) -> None:
        """Attach counts to owned listeners, which are released on socket close."""
        for record in self._records.values():
            if record.connection is connection and record.resource_counts is None:
                record.resource_counts = {"available": available, "sent": sent}

    def resource_counts(self, connection: websocket_api.ActiveConnection) -> dict[str, int] | None:
        """Resource lists preceding an owned subscription are not attributed."""
        return next((record.resource_counts for record in self._records.values()
                     if record.connection is connection and record.resource_counts is not None), None)

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
        self._explicit_subscriptions.clear()
        self._table = self._original = self._owned_entry = None
