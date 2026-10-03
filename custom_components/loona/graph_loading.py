"""Bootstrap account-scoped graph scheduling without changing Lovelace configs."""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol

from homeassistant.components import frontend, websocket_api
from homeassistant.components.websocket_api import commands
from homeassistant.core import HomeAssistant, callback

from .compatibility import (
    CompatibilityError, probe_error, HandlerEntry, ProbeConnection, inspect_native_command, probe_sync,
)
from .const import (
    CONF_DASHBOARDS,
    CONF_TARGET_MODE,
    CONF_USER_IDS,
    CONTROL_GRAPHS,
    CONTROL_MASTER,
    CONTROL_MOTION,
    MOTION_MAX_MS,
    MOTION_POLL_MS,
    MOTION_PROGRESS_TAGS,
    MOTION_QUIET_MS,
    MOTION_VIEW_TAGS,
    GRAPH_CONTEXT,
    GRAPH_POLL_MS,
    GRAPH_PROBE_MS,
    GRAPH_PROFILES,
    GRAPH_QUIET_MS,
    GRAPH_SUBSCRIBE,
    GRAPH_TRACE_LIMIT,
    TARGET_ALL,
    VERSION,
)

if TYPE_CHECKING:
    from .runtime import LoonaRuntime

_ASSET_PATH = "/loona/graph-loading.js"
_ASSET_URL = f"{_ASSET_PATH}?v={VERSION}"
_ASSET_REGISTERED = "loona_graph_asset_registered"


async def async_register_frontend(hass: HomeAssistant) -> Callable[[], None]:
    """Keep frontend API changes isolated from working backend adapters."""
    try:
        return await _async_register_frontend(hass)
    except CompatibilityError:
        raise
    except Exception as err:
        raise probe_error("Native frontend registration probe failed", err) from err


async def _async_register_frontend(hass: HomeAssistant) -> Callable[[], None]:
    """Register a native extra module once, without editing resource storage."""
    register_many = getattr(hass.http, "async_register_static_paths", None)
    register_one = getattr(hass.http, "register_static_path", None)
    if not callable(getattr(frontend, "add_extra_js_url", None)) or not (
        callable(getattr(frontend, "remove_extra_js_url", None))
        or callable(getattr(hass.data.get(frontend.DATA_EXTRA_MODULE_URL), "remove", None))
    ):
        raise CompatibilityError("Frontend module APIs are unavailable")
    if not hass.data.get(_ASSET_REGISTERED):
        paths = (
            (_ASSET_PATH, str(Path(__file__).parent / "frontend" / "graph-loading.js")),
            ("/loona/startup-motion.js", str(Path(__file__).parent / "frontend" / "startup-motion.js")),
        )
        if callable(register_many):
            from homeassistant.components.http import StaticPathConfig
            await register_many([StaticPathConfig(url, path, cache_headers=True) for url, path in paths])
        elif callable(register_one):
            for url, path in paths:
                register_one(url, path, cache_headers=True)
        else:
            raise CompatibilityError("Frontend static path API is unavailable")
        hass.data[_ASSET_REGISTERED] = True

    def remove() -> None:
        if callable(unregister := getattr(frontend, "remove_extra_js_url", None)):
            unregister(hass, _ASSET_URL)
        else:
            hass.data[frontend.DATA_EXTRA_MODULE_URL].remove(_ASSET_URL)

    frontend.add_extra_js_url(hass, _ASSET_URL)
    return remove


class _ConfigConnection:
    """Preserve native config generation and account-specific redaction."""

    def __init__(
        self, adapter: "GraphLoadingAdapter", connection: websocket_api.ActiveConnection
    ) -> None:
        self.adapter, self.connection = adapter, connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self.connection, name)

    @callback
    def send_result(self, msg_id: int, result: Any = None) -> None:
        context = self.adapter.context(self.connection)
        if isinstance(result, dict) and (context["enabled"] or context["motion"]["enabled"]):
            result = {**result, GRAPH_CONTEXT: context}
        self.connection.send_result(msg_id, result)


class GraphLoadingAdapter:
    """Own only the probed native config hook and a read-only policy subscription."""

    def __init__(self, runtime: "LoonaRuntime") -> None:
        self.runtime = runtime
        self.hass = runtime.hass
        self.original: HandlerEntry | None = None
        self.owned: HandlerEntry | None = None
        self.subscription: HandlerEntry | None = None
        self.listeners: set[Callable[[], None]] = set()
        self.stopped = False

    def context(self, connection: websocket_api.ActiveConnection) -> dict[str, Any]:
        """Do not disclose target accounts or send enabled policy to other users."""
        settings = self.runtime._policy_settings
        targeted = settings.get(CONF_TARGET_MODE) == TARGET_ALL or (
            connection.user.id in settings.get(CONF_USER_IDS, ())
        )
        table = self.hass.data.get(websocket_api.DOMAIN, {})
        allowed = (
            not self.stopped
            and table.get("get_config") == self.owned
            and table.get(GRAPH_SUBSCRIBE) == self.subscription
            and connection.user.is_active
            and targeted
            and self.runtime.controls[CONTROL_MASTER]
        )
        return {
            "version": VERSION,
            "active": not self.stopped,
            "enabled": bool(allowed and self.runtime.controls[CONTROL_GRAPHS]),
            "motion": {
                "enabled": bool(allowed and self.runtime.controls[CONTROL_MOTION]),
                "quiet_ms": MOTION_QUIET_MS,
                "poll_ms": MOTION_POLL_MS,
                "max_ms": MOTION_MAX_MS,
                "progress_tags": MOTION_PROGRESS_TAGS,
                "view_tags": MOTION_VIEW_TAGS,
            },
            "dashboards": list(settings.get(CONF_DASHBOARDS, ())) if targeted else [],
            "probe_ms": GRAPH_PROBE_MS,
            "quiet_ms": GRAPH_QUIET_MS,
            "poll_ms": GRAPH_POLL_MS,
            "trace_limit": GRAPH_TRACE_LIMIT,
            "profiles": GRAPH_PROFILES,
        }

    def install(self) -> None:
        """Probe native configuration before installing the policy commands."""
        native = getattr(commands, "handle_get_config", None)
        table, original = inspect_native_command(self.hass, "get_config", native)
        native = original[0]
        if GRAPH_SUBSCRIBE in table:
            raise CompatibilityError("Another handler owns graph loading commands")
        connection = ProbeConnection(self.hass)
        probe_sync(self.hass, native, {"id": 1, "type": "get_config"}, connection)
        if not isinstance(connection.result(), dict):
            raise CompatibilityError("Native configuration response changed")
        self.original = original

        @callback
        def get_config(
            hass: HomeAssistant,
            connection: websocket_api.ActiveConnection,
            msg: dict[str, Any],
        ) -> None:
            native(
                hass,
                cast(websocket_api.ActiveConnection, _ConfigConnection(self, connection)),
                msg,
            )

        @callback
        @websocket_api.websocket_command({vol.Required("type"): GRAPH_SUBSCRIBE})
        def subscribe(
            hass: HomeAssistant,
            connection: websocket_api.ActiveConnection,
            msg: dict[str, Any],
        ) -> None:
            last: dict[str, Any] | None = None

            @callback
            def publish() -> None:
                nonlocal last
                context = self.context(connection)
                if context != last:
                    last = context
                    connection.send_event(msg["id"], context)

            remove = self.runtime.async_add_listener(publish)

            @callback
            def unsubscribe() -> None:
                remove()
                self.listeners.discard(unsubscribe)

            self.listeners.add(unsubscribe)
            connection.subscriptions[msg["id"]] = unsubscribe
            connection.send_result(msg["id"])
            publish()

        self.owned = (get_config, original[1])
        table["get_config"] = self.owned
        websocket_api.async_register_command(self.hass, subscribe)
        self.subscription = table[GRAPH_SUBSCRIBE]

    @callback
    def uninstall(self) -> None:
        """Disable open pages before restoring hooks; leave foreign owners alone."""
        self.stopped = True
        self.runtime.notify()
        for unsubscribe in tuple(self.listeners):
            unsubscribe()
        table = self.hass.data.get(websocket_api.DOMAIN, {})
        if self.owned is not None and table.get("get_config") == self.owned:
            table["get_config"] = self.original
        if (
            self.subscription is not None
            and table.get(GRAPH_SUBSCRIBE) == self.subscription
        ):
            table.pop(GRAPH_SUBSCRIBE)
