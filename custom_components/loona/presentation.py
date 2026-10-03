"""Read-only display labels for administrator card reports."""

from typing import Any
from urllib.parse import urlsplit

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


def entity_label(hass: HomeAssistant, entity_id: str) -> str:
    """Prefer the configured name, then the live or original friendly name."""
    entry = er.async_get(hass).entities.get(entity_id)
    state = hass.states.get(entity_id)
    return str((entry.name if entry else None)
               or (state.attributes.get("friendly_name") if state else None)
               or (entry.original_name if entry else None) or entity_id)


def resource_labels(hass: HomeAssistant, urls: list[str]) -> dict[str, str]:
    """Use optional local HACS metadata; unknown resources keep their URL."""
    names: dict[str, str] = {}
    try:
        hacs = hass.data.get("hacs")
        repositories = hacs.repositories.list_downloaded if hacs is not None else ()
    except (AttributeError, TypeError):
        repositories = ()
    for repository in repositories:
        try:
            if repository.data.category == "plugin":
                path = urlsplit(repository.generate_dashboard_resource_url()).path
            elif repository.data.category == "integration":
                domain = repository.data.domain
                if not isinstance(domain, str) or not domain.isidentifier():
                    continue
                path = f"/{domain}/{domain}.js"
            else:
                continue
            name = repository.display_name
            if isinstance(name, str) and name:
                names[path] = name
        except (AttributeError, TypeError, ValueError):
            continue
    labels = {}
    for url in urls:
        try:
            parts = urlsplit(url)
            labels[url] = names.get(parts.path, url) if not parts.netloc else url
        except ValueError:
            labels[url] = url
    return labels


def notice_labels(hass: HomeAssistant, notices: list[dict[str, Any]]) -> dict[str, str]:
    """Label only affected entities and resources present in this report."""
    labels: dict[str, str] = {}
    resources: list[str] = []
    for item in notices:
        for value in item.get("items", ()):
            if item["code"] in {"missing_entities", "excluded_dependencies"}:
                labels[value] = entity_label(hass, value)
            elif item["code"] in {"unchecked_resources", "stale_resources"}:
                resources.append(value)
    labels.update(resource_labels(hass, resources))
    return labels
