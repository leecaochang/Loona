"""Manage the bundled frontend module and an owned native storage dashboard."""

import asyncio
import logging
from inspect import unwrap
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, websocket_api
from homeassistant.components.lovelace.dashboard import DashboardsCollection
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STATISTICS_ASSET, STATISTICS_DASHBOARD, SETTINGS_ASSET, I18N_ASSET, VERSION, DASHBOARD_CARDS
from .dashboard import dashboard_objects


_LOGGER = logging.getLogger(__name__)


class StatisticsCardError(ValueError):
    """Installation cannot safely complete without changing user-owned data."""


def card_dashboard_config(cards: tuple[str, ...] = DASHBOARD_CARDS) -> dict[str, Any]:
    """Only this exact generated configuration may be automatically removed."""
    return {"views": [{"title": "Loona", "path": "statistics", "cards": [
        {"type": f"custom:loona-{card}-card"} for card in cards
    ]}]}


class StatisticsCard:
    """Manage only the dashboard configuration recorded in Loona ownership storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.statistics_dashboard")
        self.url = f"{STATISTICS_ASSET}?v={VERSION}"
        self.module_urls = (self.url, f"{SETTINGS_ASSET}?v={VERSION}")
        self.lock = asyncio.Lock()
        self.enabled = False
        self.opted_out = False

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
        """Use the available synchronous or asynchronous native static API."""
        try:
            await self._register_asset()
        except StatisticsCardError:
            raise
        except Exception as err:
            _LOGGER.exception("Loona native dashboard or asset operation failed")
            raise StatisticsCardError("Native statistics asset registration failed") from err

    async def _register_asset(self) -> None:
        """Register the route before Core freezes its HTTP router."""
        key = "loona_statistics_asset_registered"
        if not self.hass.data.get(key):
            assets = [(asset, str(Path(__file__).parent / "frontend" / filename)) for asset, filename in (
                (STATISTICS_ASSET, "statistics-card.js"), (SETTINGS_ASSET, "settings-card.js"), (I18N_ASSET, "i18n.js")
            )]
            if callable(getattr(self.hass.http, "async_register_static_paths", None)):
                from homeassistant.components.http import StaticPathConfig
                await self.hass.http.async_register_static_paths([
                    StaticPathConfig(asset, path, cache_headers=True) for asset, path in assets
                ])
            elif callable(register := getattr(self.hass.http, "register_static_path", None)):
                # The legacy native API registers the router synchronously.
                for asset, path in assets:
                    register(asset, path, cache_headers=True)
            else:
                raise StatisticsCardError("Native frontend asset API is unavailable")
            self.hass.data[key] = True

    async def set_enabled(self, enabled: bool, cards: tuple[str, ...] = DASHBOARD_CARDS) -> None:
        """Create/remove only the dedicated dashboard recorded as ours."""
        try:
            await self._set_enabled(enabled, cards)
        except StatisticsCardError:
            raise
        except Exception as err:
            _LOGGER.exception("Loona native dashboard or asset operation failed")
            raise StatisticsCardError("Native statistics dashboard operation failed") from err

    async def _set_enabled(self, enabled: bool, cards: tuple[str, ...]) -> None:
        """Apply a card selection while preserving edited or deleted dashboards."""
        async with self.lock:
            owned = await self.store.async_load() or {}
            self.opted_out = False
            if enabled:
                await self.register_asset()
                for url in self.module_urls:
                    frontend.add_extra_js_url(self.hass, url)
                self.enabled = True
            if not owned and (not enabled or not cards):
                if not enabled:
                    self.unload()
                return
            board = dashboard_objects(self.hass).get(STATISTICS_DASHBOARD)
            if owned.get("id") and board is None:
                # Native deletion is an opt-out, including across reloads.
                await self.store.async_remove()
                self.opted_out = enabled
                if not enabled:
                    self.unload()
                return
            if board is not None and (board.config or {}).get("id") != owned.get("id"):
                if enabled:
                    raise StatisticsCardError("The Loona dashboard URL is already in use")
                self.unload()
                return
            collection = self.collection()
            if board is not None:
                existing = await board.async_load(False)
                previous = card_dashboard_config(tuple(owned.get("cards", DASHBOARD_CARDS)))
                if existing != previous:
                    if not enabled or not cards or tuple(owned.get("cards", DASHBOARD_CARDS)) != cards:
                        raise StatisticsCardError("The Loona dashboard was edited; manage it manually")
                    return
                if not enabled or not cards:
                    await collection.async_delete_item(owned["id"])
                    await self.store.async_remove()
                elif existing != card_dashboard_config(cards):
                    await board.async_save(card_dashboard_config(cards))
                    await self.store.async_save({"id": owned["id"], "cards": list(cards)})
            elif enabled and cards:
                created = await collection.async_create_item({
                    "url_path": STATISTICS_DASHBOARD, "title": "Loona",
                    "icon": "mdi:weather-night", "require_admin": True, "show_in_sidebar": True,
                })
                try:
                    await self.store.async_save({"id": created["id"], "cards": list(cards)})
                    await dashboard_objects(self.hass)[STATISTICS_DASHBOARD].async_save(card_dashboard_config(cards))
                except Exception:
                    await collection.async_delete_item(created["id"])
                    await self.store.async_remove()
                    raise
            if not enabled:
                self.unload()

    def _remove_module(self) -> None:
        """Use Core's module remover or its older native URL manager."""
        if callable(remove := getattr(frontend, "remove_extra_js_url", None)):
            for url in self.module_urls:
                remove(self.hass, url)
        else:
            for url in self.module_urls:
                self.hass.data[frontend.DATA_EXTRA_MODULE_URL].remove(url)

    def unload(self) -> None:
        """Unload the module registration while retaining the saved dashboard."""
        if self.enabled:
            self._remove_module()
        self.enabled = False
