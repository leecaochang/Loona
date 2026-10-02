"""Manage the bundled frontend module and an owned native storage dashboard."""

import asyncio
from inspect import unwrap
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, websocket_api
from homeassistant.components.lovelace.dashboard import DashboardsCollection
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STATISTICS_ASSET, STATISTICS_DASHBOARD, VERSION
from .dashboard import dashboard_objects


class StatisticsCardError(ValueError):
    """Installation cannot safely complete without changing user-owned data."""


def card_dashboard_config() -> dict[str, Any]:
    """Only this exact generated configuration may be automatically removed."""
    return {"views": [{"title": "Statistics", "path": "statistics", "cards": [
        {"type": "custom:loona-statistics-card"}
    ]}]}


class StatisticsCard:
    """Use native collections; never overwrite existing dashboard configurations."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.store: Store[dict[str, str]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.statistics_dashboard")
        self.url = f"{STATISTICS_ASSET}?v={VERSION}"
        self.lock = asyncio.Lock()
        self.enabled = False

    def collection(self) -> DashboardsCollection:
        """Resolve Core's original dashboard collection instead of a stale copy."""
        entry = self.hass.data.get(websocket_api.DOMAIN, {}).get("lovelace/dashboards/list")
        handler = unwrap(entry[0]) if isinstance(entry, tuple) else None
        collection = getattr(getattr(handler, "__self__", None), "storage_collection", None)
        if not isinstance(collection, DashboardsCollection):
            # Older Core registers a standalone list handler and stores the
            # native collection in its legacy Lovelace data dictionary.
            data = self.hass.data.get("lovelace")
            if isinstance(data, dict):
                collection = data.get("dashboards_collection")
        if not isinstance(collection, DashboardsCollection):
            raise StatisticsCardError("Native dashboard collection is unavailable")
        return collection

    async def register_asset(self) -> None:
        """Support the admitted older synchronous and current async static APIs."""
        try:
            await self._register_asset()
        except StatisticsCardError:
            raise
        except Exception as err:
            raise StatisticsCardError("Native statistics asset registration failed") from err

    async def _register_asset(self) -> None:
        """Register the route before Core freezes its HTTP router."""
        key = "loona_statistics_asset_registered"
        if not self.hass.data.get(key):
            path = str(Path(__file__).parent / "frontend" / "statistics-card.js")
            if callable(getattr(self.hass.http, "async_register_static_paths", None)):
                from homeassistant.components.http import StaticPathConfig
                await self.hass.http.async_register_static_paths([
                    StaticPathConfig(STATISTICS_ASSET, path, cache_headers=False)
                ])
            elif callable(register := getattr(self.hass.http, "register_static_path", None)):
                # Core 2024.5's native API registers the router synchronously.
                register(STATISTICS_ASSET, path, cache_headers=False)
            else:
                raise StatisticsCardError("Native frontend asset API is unavailable")
            self.hass.data[key] = True

    async def set_enabled(self, enabled: bool) -> None:
        """Create/remove only the dedicated dashboard recorded as ours."""
        try:
            await self._set_enabled(enabled)
        except StatisticsCardError:
            raise
        except Exception as err:
            raise StatisticsCardError("Native statistics dashboard operation failed") from err

    async def _set_enabled(self, enabled: bool) -> None:
        """Serialize installation and preserve native failures for diagnosis."""
        async with self.lock:
            owned = await self.store.async_load() or {}
            if not enabled and not owned:
                self.unload()
                return
            collection = self.collection()
            board = dashboard_objects(self.hass).get(STATISTICS_DASHBOARD)
            if board is not None and (board.config or {}).get("id") != owned.get("id"):
                if enabled:
                    raise StatisticsCardError("The statistics dashboard URL is already in use")
                self.unload()
                return
            if not enabled:
                if board is not None:
                    try:
                        config = await board.async_load(False)
                    except Exception as err:
                        raise StatisticsCardError("Cannot verify the statistics dashboard") from err
                    if config != card_dashboard_config():
                        raise StatisticsCardError("The statistics dashboard was edited; remove it manually first")
                    await collection.async_delete_item(owned["id"])
                await self.store.async_remove()
                self.unload()
                return
            await self.register_asset()
            frontend.add_extra_js_url(self.hass, self.url)
            try:
                if board is None:
                    created = await collection.async_create_item({
                        "url_path": STATISTICS_DASHBOARD, "title": "Loona statistics",
                        "icon": "mdi:chart-box-outline", "require_admin": True, "show_in_sidebar": True,
                    })
                    try:
                        await self.store.async_save({"id": created["id"]})
                        await dashboard_objects(self.hass)[STATISTICS_DASHBOARD].async_save(card_dashboard_config())
                    except Exception:
                        await collection.async_delete_item(created["id"])
                        await self.store.async_remove()
                        raise
            except Exception:
                self._remove_module()
                raise
            self.enabled = True

    def _remove_module(self) -> None:
        """Use Core's module remover or its older native URL manager."""
        if callable(remove := getattr(frontend, "remove_extra_js_url", None)):
            remove(self.hass, self.url)
        else:
            self.hass.data[frontend.DATA_EXTRA_MODULE_URL].remove(self.url)

    def unload(self) -> None:
        """Unload the module registration while retaining the saved dashboard."""
        if self.enabled:
            self._remove_module()
        self.enabled = False
