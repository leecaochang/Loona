"""Bootstrap account-scoped graph scheduling without changing Lovelace configs."""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.components import frontend, websocket_api
from homeassistant.components.websocket_api import commands
from homeassistant.core import HomeAssistant, callback

from .compatibility import CompatibilityError, HandlerEntry, HandlerTable
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
    GRAPH_PROFILES,
    GRAPH_QUIET_MS,
    GRAPH_SUBSCRIBE,
    GRAPH_TRACE_LIMIT,
    FRONTEND_CORE_VERSIONS,
    TARGET_ALL,
    VERSION,
)

if TYPE_CHECKING:
    from .runtime import LoonaRuntime

_ASSET_PATH = "/loona/graph-loading.js"
_ASSET_URL = f"{_ASSET_PATH}?v={VERSION}"
_ASSET_REGISTERED = "loona_graph_asset_registered"


async def async_register_frontend(hass: HomeAssistant) -> Callable[[], None]:
    """Register a native extra module once, without editing resource storage."""
    try:
        from homeassistant.components.http import StaticPathConfig
    except ImportError as err:
        raise CompatibilityError("Frontend static path API is unavailable") from err
    if not all(callable(api) for api in (
        StaticPathConfig,
        getattr(hass.http, "async_register_static_paths", None),
        getattr(frontend, "add_extra_js_url", None),
        getattr(frontend, "remove_extra_js_url", None),
    )):
        raise CompatibilityError("Frontend registration APIs are unavailable")

    if not hass.data.get(_ASSET_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    _ASSET_PATH,
                    str(Path(__file__).parent / "frontend" / "graph-loading.js"),
                    cache_headers=False,
                ),
                StaticPathConfig(
                    "/loona/startup-motion.js",
                    str(Path(__file__).parent / "frontend" / "startup-motion.js"),
                    cache_headers=False,
                )
            ]
        )
        hass.data[_ASSET_REGISTERED] = True
    frontend.add_extra_js_url(hass, _ASSET_URL)
    return lambda: frontend.remove_extra_js_url(hass, _ASSET_URL)


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
        if isinstance(result, dict):
            result = {**result, GRAPH_CONTEXT: self.adapter.context(self.connection)}
        self.connection.send_result(msg_id, result)


class GraphLoadingAdapter:
    """Own only the tested native config hook and a read-only policy subscription."""

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
            "quiet_ms": GRAPH_QUIET_MS,
            "poll_ms": GRAPH_POLL_MS,
            "trace_limit": GRAPH_TRACE_LIMIT,
            "profiles": GRAPH_PROFILES,
        }

    def install(self) -> None:
        """Decline unfamiliar versions, handlers, schemas, or another policy owner."""
        if ha_const.__version__ not in FRONTEND_CORE_VERSIONS:
            raise CompatibilityError("Graph loading requires a tested Core version")
        table = cast(HandlerTable, self.hass.data.get(websocket_api.DOMAIN, {}))
        if not isinstance(table, dict):
            raise CompatibilityError("Websocket commands are not registered yet")
        original = table.get("get_config")
        native = commands.handle_get_config
        if (
            not isinstance(original, tuple)
            or len(original) != 2
            or original[0] is not native
            or original[1] is not getattr(native, "_ws_schema", None)
            or original[1] is not False
            or GRAPH_SUBSCRIBE in table
        ):
            raise CompatibilityError("Another handler owns graph loading commands")
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
