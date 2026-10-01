"""Use real HA state, permission, schema, dispatch, and connection classes."""

import ctypes
import json
import logging
from pathlib import Path
import sys
from types import MappingProxyType

import pytest
import orjson

from homeassistant.auth.models import Group, User
from homeassistant.auth.permissions.models import PermissionLookup
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import commands
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.loona.const import DOMAIN


@pytest.fixture
async def hass(tmp_path):
    """Create a genuine Core with its native websocket command table."""
    instance = HomeAssistant(str(tmp_path))
    dr.async_setup(instance)
    await dr.async_load(instance, load_empty=True)
    await er.async_load(instance, load_empty=True)
    commands.async_register_commands(instance, websocket_api.async_register_command)
    yield instance
    await instance.async_block_till_done()
    await instance.async_stop(force=True)


def pytest_configure():
    """Keep orjson 3.11.9's heap type alive until the test process exits.

    Fragment instances do not retain their heap type in this pinned release.
    Native registry storage can outlive module cleanup during focused tests.
    A process-lifetime type reference avoids dereferencing a freed type without
    replacing native serialization or changing production dependencies.
    """
    if sys.implementation.name == "cpython" and orjson.__version__ == "3.11.9":
        incref = ctypes.pythonapi.Py_IncRef
        incref.argtypes = [ctypes.py_object]
        incref.restype = None
        incref(orjson.Fragment)


@pytest.fixture
def make_user(hass):
    """Construct HA users with real entity permission policies."""
    lookup = PermissionLookup(er.async_get(hass), dr.async_get(hass))

    def create(*, admin=False, allowed=None):
        policy = (
            {"entities": True}
            if allowed is None
            else {"entities": {"entity_ids": {key: {"read": True} for key in allowed}}}
        )
        group = Group(
            name="Test group", policy=policy, id="system-admin" if admin else "test"
        )
        return User(
            name="Test user", perm_lookup=lookup, is_active=True, groups=[group]
        )

    return create


@pytest.fixture
def make_connection(hass):
    """Capture actual Core serialization instead of emulating the handler."""
    connections = []

    def create(user):
        output = []

        def send(message):
            output.append(
                json.loads(message) if isinstance(message, (str, bytes)) else message
            )

        connection = ActiveConnection(
            logging.getLogger("loona.test"), hass, send, user, None, None
        )
        connections.append(connection)
        return connection, output

    yield create
    for connection in connections:
        connection.async_handle_close()


@pytest.fixture
async def loona_hass(hass):
    """Initialize real auth, entries, and registries for integration lifecycle tests."""
    from homeassistant import auth, config_entries, loader
    from homeassistant.helpers import (
        area_registry as ar,
        floor_registry as fr,
        issue_registry as ir,
        label_registry as lr,
    )

    await fr.async_load(hass, load_empty=True)
    await lr.async_load(hass, load_empty=True)
    await ar.async_load(hass, load_empty=True)
    await ir.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [], [])
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    from homeassistant.components.config import (
        area_registry,
        device_registry,
        entity_registry,
        floor_registry,
        label_registry,
    )

    for module in (
        area_registry,
        device_registry,
        entity_registry,
        floor_registry,
        label_registry,
    ):
        module.async_setup(hass)
    hass.config.components.update({"config", "websocket_api"})
    Path(hass.config.path("custom_components")).symlink_to(
        Path(__file__).resolve().parents[1] / "custom_components",
        target_is_directory=True,
    )
    loader.async_setup(hass)
    return hass


@pytest.fixture
def make_entry(loona_hass):
    """Register native ConfigEntry objects without mocking their lifecycle model."""
    from homeassistant.config_entries import ConfigEntry

    def create(data, options=None):
        entry = ConfigEntry(
            domain=DOMAIN,
            data=data,
            options=options or {},
            version=1,
            minor_version=1,
            title="Loona",
            source="user",
            unique_id=DOMAIN,
            discovery_keys=MappingProxyType({}),
            subentries_data=(),
        )
        loona_hass.config_entries._entries[entry.entry_id] = entry
        return entry

    return create


@pytest.fixture
async def dashboards(loona_hass):
    """Use genuine native storage dashboards and their invalidation events."""
    from homeassistant.components.lovelace import LovelaceData
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import LovelaceStorage

    default = LovelaceStorage(loona_hass, None)
    wall = LovelaceStorage(
        loona_hass, {"id": "wall", "url_path": "wall-panel", "title": "Wall"}
    )
    await default.async_save(
        {"views": [{"cards": [{"type": "entity", "entity": "sensor.overview"}]}]}
    )
    await wall.async_save(
        {"views": [{"cards": [{"type": "entity", "entity": "sensor.wall"}]}]}
    )
    loona_hass.data[LOVELACE_DATA] = LovelaceData(
        "storage", {None: default, "wall-panel": wall}, None, {}
    )
    return {"lovelace": default, "wall-panel": wall}
