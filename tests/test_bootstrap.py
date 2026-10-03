"""Verify native HTML ownership and the stock browser startup boundary."""

from pathlib import Path
import subprocess

import jinja2
import pytest

from homeassistant.components import frontend
from aiohttp.test_utils import make_mocked_request

from custom_components.loona.bootstrap import async_install, _routing, route_key
from custom_components.loona.compatibility import CompatibilityError
from custom_components.loona.panels import async_register_frontend


async def test_native_template_order_safe_mode_and_unload(loona_hass, frontend_http):
    view = next(resource for resource in frontend_http.app.router.resources() if type(resource) is frontend.IndexView)
    native = await loona_hass.async_add_executor_job(view.get_template)
    remove_reporter = await async_register_frontend(loona_hass)
    hook = await async_install(loona_hass)
    assert hook.root_supported
    kwargs = {"theme_color": "#123456", "extra_js_es5": [], "extra_modules": list(loona_hass.data[frontend.DATA_EXTRA_MODULE_URL].urls)}
    html = view.get_template().render(**kwargs)
    assert html.index("Object.defineProperty(window, \"hassConnection\"") < html.index("import(\"/frontend_latest/core.")
    assert '"routing": null' not in html
    assert view.get_template().render(**{**kwargs, "extra_modules": []}) == native.render(**{**kwargs, "extra_modules": []})
    remove_reporter()
    assert view.get_template().render(**{**kwargs, "extra_modules": []}) == native.render(**{**kwargs, "extra_modules": []})
    hook.remove()
    assert view._template_cache is native


async def test_foreign_template_preserved_before_and_after_install(loona_hass, frontend_http):
    view = next(resource for resource in frontend_http.app.router.resources() if type(resource) is frontend.IndexView)
    foreign = jinja2.Template("foreign frontend")
    view._template_cache = foreign
    with pytest.raises(CompatibilityError, match="Another owner"):
        await async_install(loona_hass)
    assert view._template_cache is foreign
    view._template_cache = None
    hook = await async_install(loona_hass)
    view._template_cache = foreign
    hook.remove()
    assert view._template_cache is foreign


async def test_conditional_foreign_template_is_not_overwritten(loona_hass, frontend_http):
    view = next(resource for resource in frontend_http.app.router.resources() if type(resource) is frontend.IndexView)
    source = await loona_hass.async_add_executor_job(lambda: (frontend._frontend_root(None) / "index.html").read_text())
    foreign = jinja2.Template(source + '{% if theme_color == "#not-a-probe-value" %}foreign customization{% endif %}')
    view._template_cache = foreign
    with pytest.raises(CompatibilityError, match="Another owner"):
        await async_install(loona_hass)
    assert view._template_cache is foreign


def test_unfamiliar_root_routing_remains_unknown():
    assert _routing('const defaultPanel="new-dashboard";') is None


async def test_unknown_root_probe_preserves_named_hook(loona_hass, frontend_http, monkeypatch):
    monkeypatch.setattr("custom_components.loona.bootstrap._routing", lambda source: None)
    hook = await async_install(loona_hass)
    assert not hook.root_supported
    hook.remove()


async def test_native_get_onboarding_and_safe_mode(loona_hass, frontend_http, monkeypatch):
    view = next(resource for resource in frontend_http.app.router.resources() if type(resource) is frontend.IndexView)
    remove_reporter = await async_register_frontend(loona_hass)
    hook = await async_install(loona_hass)
    loona_hass.data[frontend.DATA_EXTRA_JS_URL_ES5] = frontend.UrlManager(lambda *args: None, [])
    frontend_http.app[frontend.KEY_HASS] = loona_hass
    monkeypatch.setattr(frontend.onboarding, "async_is_onboarded", lambda hass: False)
    request = make_mocked_request("GET", "/", app=frontend_http.app)
    assert (await view.get(request)).status == 302
    monkeypatch.setattr(frontend.onboarding, "async_is_onboarded", lambda hass: True)
    assert 'Object.defineProperty(window, "hassConnection"' in (await view.get(request)).text
    loona_hass.config.safe_mode = True
    assert '__loonaBootstrap' not in (await view.get(request)).text
    hook.remove()
    remove_reporter()


def test_stock_client_bootstrap():
    result = subprocess.run(["node", str(Path(__file__).with_name("bootstrap.mjs"))], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


async def test_disabled_hook_refreshes_owned_template_only(loona_hass, frontend_http):
    policy = {"enabled": False, "routes": [route_key("private-dashboard")]}
    remove_reporter = await async_register_frontend(loona_hass)
    hook = await async_install(loona_hass, lambda: policy)
    view = next(resource for resource in frontend_http.app.router.resources() if type(resource) is frontend.IndexView)
    kwargs = {"theme_color":"#123456", "extra_js_es5":[], "extra_modules":list(loona_hass.data[frontend.DATA_EXTRA_MODULE_URL].urls)}
    assert "__loonaBootstrap" not in view.get_template().render(**kwargs)
    policy["enabled"] = True
    hook.refresh()
    html = view.get_template().render(**kwargs)
    assert "__loonaBootstrap" in html and "private-dashboard" not in html
    active = view.get_template()
    hook.refresh()
    assert view.get_template() is active
    policy["enabled"] = False
    hook.refresh()
    assert "__loonaBootstrap" not in view.get_template().render(**kwargs)
    foreign = jinja2.Template("foreign owner")
    view._template_cache = foreign
    with pytest.raises(CompatibilityError, match="ownership changed"):
        hook.refresh()
    hook.remove()
    assert view._template_cache is foreign
    remove_reporter()
