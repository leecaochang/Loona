"""Install an owned, optional browser hook before native frontend bootstrap."""

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import re

import jinja2

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant

from .compatibility import CompatibilityError, probe_error
from .const import BOOTSTRAP_TIMEOUT_MS, PANEL_ASSET, PANEL_POLL_MS, VERSION, BROWSER_MEASURE_MS


def route_key(path: str) -> str:
    """Avoid publishing dashboard names; collisions only add harmless hook work."""
    value = 2166136261
    for byte in path.encode("utf8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return f"{value:08x}"


def _routing(source: str) -> dict[str, str | bool] | None:
    """Recognize native root routing; unfamiliar shapes retain full initial data."""
    modern = 'userData?.default_panel' in source and 'systemData?.default_panel' in source
    patterns = (
        r'getItem\("defaultPanel"\);return \w+\?JSON\.parse\(\w+\):null\}\)\(\)\|\|(\w+)',
        r'localStorage\.defaultPanel\?JSON\.parse\(localStorage\.defaultPanel\):(\w+)',
        r'getItem\("defaultPanel"\);return \w+\?JSON\.parse\(\w+\):(\w+)',
    )
    for pattern in patterns:
        if match := re.search(pattern, source):
            # Resolve the constant in this module, rather than a same-named variable elsewhere.
            prefix = source[max(0, match.start() - 1200):match.start()]
            constants = re.findall(r'(?:const |var |[,;])' + re.escape(match[1]) + r'="(home|lovelace)"', prefix)
            if constants:
                return {"default": constants[-1], "preferences": modern}
    return None


@dataclass(frozen=True, slots=True)
class BootstrapHook:
    """Keep installation and root-routing capability results independent."""

    remove: Callable[[], None]
    root_supported: bool
    refresh: Callable[[], None]


async def async_install(hass: HomeAssistant, policy: Callable[[], dict] | None = None) -> BootstrapHook:
    """Probe the shipped template and promise boundary before replacing its cache."""
    try:
        views = [resource for resource in hass.http.app.router.resources()
                 if type(resource) is frontend.IndexView]
        if len(views) != 1 or views[0].repo_path is not None:
            raise CompatibilityError("Native frontend index ownership is unavailable")
        view = views[0]
        original = await hass.async_add_executor_job(view.get_template)
        if view._template_cache is not original:
            raise CompatibilityError("Native frontend template cache is unavailable")
        root_supported = False

        def prepare() -> tuple[str, str, str, dict | None]:
            nonlocal root_supported
            root = frontend._frontend_root(None)
            source = (root / "index.html").read_text(encoding="utf8")
            native = jinja2.Template(source)
            cached = original or native
            if (cached.environment is not native.environment
                    or cached.root_render_func.__code__ != native.root_render_func.__code__
                    or {name: block.__code__ for name, block in cached.blocks.items()}
                    != {name: block.__code__ for name, block in native.blocks.items()}):
                raise CompatibilityError("Another owner changed the native frontend template")
            url = f"{PANEL_ASSET}?v={VERSION}&poll={PANEL_POLL_MS}&measure={BROWSER_MEASURE_MS}"
            for modules in ([], [url, "/unrelated-module.js"]):
                args = {"theme_color": "#123456", "extra_modules": modules, "extra_js_es5": []}
                if cached.render(**args) != native.render(**args):
                    raise CompatibilityError("Another owner changed the native frontend template")
            core = re.search(r'/frontend_latest/(core\.[\w.-]+\.js)', source)
            app = re.search(r'/frontend_latest/(app\.[\w.-]+\.js)', source)
            if source.count("<head>") != 1 or core is None or app is None:
                raise CompatibilityError("Native frontend bootstrap layout is unavailable")
            core_source = (root / "frontend_latest" / core[1]).read_text(encoding="utf8")
            if "window.hassConnection=" not in core_source or "window.hassConnection.then(" not in core_source:
                raise CompatibilityError("Native frontend connection promise is unavailable")
            routing = _routing((root / "frontend_latest" / app[1]).read_text(encoding="utf8"))
            root_supported = routing is not None
            script = (Path(__file__).parent / "frontend" / "pre-bootstrap.js").read_text(encoding="utf8")
            reporter = (Path(__file__).parent / "frontend" / "panel-context.js").read_text(encoding="utf8")
            loader = (Path(__file__).parent / "frontend" / "resource-loading.js").read_text(encoding="utf8")
            import_line = f'import "./resource-loading.js?v={VERSION}";'
            if reporter.count(import_line) != 1:
                raise CompatibilityError("Resource loader bootstrap import changed")
            reporter = reporter.replace(import_line, loader)
            script = script.replace("/* LOONA_REPORTER */", reporter.replace("import.meta.url", json.dumps("http://loona.invalid" + url)))
            return source, script, url, routing

        source, script, url, routing = await hass.async_add_executor_job(prepare)
        if view._template_cache is not original:
            raise CompatibilityError("Native frontend template ownership changed during probing")
        owned = original
        previous = None

        def refresh() -> None:
            nonlocal owned, previous
            if view._template_cache is not owned:
                raise CompatibilityError("Native frontend template ownership changed")
            settings = {"timeout": BOOTSTRAP_TIMEOUT_MS, "routing": routing,
                        **(policy() if policy else {"enabled": True, "routes": None})}
            serialized = json.dumps(settings)
            if serialized == previous:
                return
            previous = serialized
            insertion = ""
            if settings["enabled"]:
                insertion = ('{% if ' + json.dumps(url) + ' in extra_modules %}<script>'
                             + script.replace("/* LOONA_CONFIG */ {}", serialized)
                             + '</script>{% endif %}')
            owned = jinja2.Template(source.replace("<head>", "<head>" + insertion, 1))
            view._template_cache = owned

        refresh()

        def remove() -> None:
            if view._template_cache is owned:
                view._template_cache = original

        return BootstrapHook(remove, root_supported, refresh)
    except CompatibilityError:
        raise
    except Exception as err:
        raise probe_error("Native frontend bootstrap probe failed", err) from err
