"""Map CKAN package JSON to DCAT-AP-NL 3-shaped catalog records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

DCAT_CONTEXT = (
    "https://raw.githubusercontent.com/SEMICeu/DCAT-AP/mappings/"
    "DCAT-AP-3.0/dcat-ap-3.0.jsonld"
)

SERVICE_FORMAT_TOKENS = {
    "WFS",
    "WMS",
    "WCS",
    "ATOM",
    "OGC WFS",
    "OGC WMS",
    "OGC WCS",
    "SPARQL",
    "API",
    "ESRI REST",
    "OGC:WFS",
    "OGC:WMS",
}


def _lang_value(text: str | None, lang: str = "nl") -> dict[str, str] | None:
    if not text:
        return None
    return {f"@{lang}": text}


def _format_token(fmt: str | None) -> str:
    if not fmt:
        return ""
    return fmt.rsplit("/", 1)[-1].upper()


def _is_service_resource(resource: dict[str, Any]) -> bool:
    fmt = _format_token(resource.get("format"))
    if fmt in SERVICE_FORMAT_TOKENS:
        return True
    url = (resource.get("url") or "").lower()
    service_hints = ("wfs?", "wms?", "wcs?", "atom?", "ogc", "arcgis/rest/services")
    return any(h in url for h in service_hints)


def _distribution_type(resource: dict[str, Any]) -> str:
    return "DataService" if _is_service_resource(resource) else "Download"


def _distribution(resource: dict[str, Any], *, dataset_id: str) -> dict[str, Any]:
    fmt = resource.get("format") or resource.get("mimetype") or "application/octet-stream"
    dist_type = _distribution_type(resource)
    dist: dict[str, Any] = {
        "@type": "dcat:Distribution",
        "dcterms:identifier": f"{dataset_id}:{resource.get('id')}",
        "dcterms:title": _lang_value(resource.get("name") or resource.get("description")),
        "dcat:accessURL": resource.get("url"),
        "dcterms:format": fmt,
        "dcat:mediaType": resource.get("mimetype"),
        "nldt:distributionType": dist_type,
    }
    if dist_type == "DataService":
        dist["dcat:accessService"] = {
            "@type": "dcat:DataService",
            "dcterms:title": _lang_value(resource.get("name")),
            "dcat:endpointURL": resource.get("url"),
            "dcterms:format": fmt,
        }
    return dist


def _license_uri(package: dict[str, Any]) -> str | None:
    for extra in package.get("extras") or []:
        if extra.get("key") in {"license", "licence", "license_id"}:
            return extra.get("value")
    return None


def _themes(package: dict[str, Any]) -> list[str]:
    themes: list[str] = []
    for tag in package.get("tags") or []:
        name = tag.get("name") if isinstance(tag, dict) else str(tag)
        if name:
            themes.append(name)
    for group in package.get("groups") or []:
        title = group.get("title") if isinstance(group, dict) else str(group)
        if title:
            themes.append(title)
    return themes


def map_package_to_dcat(
    package: dict[str, Any],
    *,
    lake_uri: str | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Return a DCAT-AP-NL 3-compatible dataset record."""
    dataset_id = package.get("name") or package.get("id") or "unknown"
    retrieved = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    org = package.get("organization") or {}
    publisher = {
        "@type": "foaf:Organization",
        "foaf:name": org.get("title") or org.get("name"),
    }
    if org.get("id"):
        publisher["dcterms:identifier"] = org["id"]

    resources = package.get("resources") or []
    distributions = [_distribution(r, dataset_id=dataset_id) for r in resources]
    download_count = sum(1 for d in distributions if d.get("nldt:distributionType") == "Download")
    service_count = len(distributions) - download_count

    record: dict[str, Any] = {
        "@context": DCAT_CONTEXT,
        "@type": "dcat:Dataset",
        "dcterms:identifier": dataset_id,
        "dcterms:title": _lang_value(package.get("title")),
        "dcterms:description": _lang_value(package.get("notes")),
        "dcterms:issued": package.get("metadata_created"),
        "dcterms:modified": package.get("metadata_modified"),
        "dcterms:license": _license_uri(package) or "http://creativecommons.org/publicdomain/zero/1.0/",
        "dcat:keyword": _themes(package),
        "dcat:landingPage": f"https://data.overheid.nl/dataset/{dataset_id}",
        "dcat:distribution": distributions,
        "dcat:contactPoint": {
            "@type": "vcard:Kind",
            "vcard:fn": (package.get("maintainer") or package.get("author") or "unknown"),
            "vcard:hasEmail": package.get("maintainer_email") or package.get("author_email"),
        },
        "dcterms:publisher": publisher,
        "prov:wasDerivedFrom": f"https://data.overheid.nl/dataset/{dataset_id}",
        "nldt:hadPrimarySource": "data.overheid.nl",
        "nldt:poc": "donl",
        "nldt:zone": "catalog",
        "nldt:accessClass": "open",
        "nldt:retrievedAt": retrieved,
        "nldt:distributionSummary": {
            "total": len(distributions),
            "download": download_count,
            "dataService": service_count,
        },
    }
    if lake_uri:
        record["nldt:lakeUri"] = lake_uri
    return record


def package_registry_entry(package: dict[str, Any]) -> dict[str, Any]:
    """Build a source-monitor registry row for a DONL package."""
    resources = package.get("resources") or []
    return {
        "id": package.get("name") or package.get("id"),
        "type": "donl",
        "ckanId": package.get("name") or package.get("id"),
        "title": package.get("title"),
        "metadataModified": package.get("metadata_modified"),
        "resourceCount": len(resources),
        "resourceUrls": [r.get("url") for r in resources if r.get("url")],
        "resourceFormats": [_format_token(r.get("format")) for r in resources],
        "lastChecked": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def safe_filename(name: str, fallback: str = "resource") -> str:
    parsed = urlparse(name)
    base = parsed.path.rsplit("/", 1)[-1] if parsed.path else fallback
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)
    return cleaned or fallback
