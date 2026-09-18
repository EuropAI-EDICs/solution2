"""Dual-plane routing: PoC lake (catalog+process) vs EU LDT Data Platform (data-mcp)."""

from __future__ import annotations

from typing import Any

LIVE_KEYWORDS = (
    "live",
    "real-time",
    "realtime",
    "sensor",
    "ngsi",
    "trino",
    "luchtkwaliteit",
    "air quality",
    "broker",
    "entity",
    "cdc",
    "stream",
)

LAKE_KEYWORDS = (
    "scenario",
    "scan",
    "qa",
    "opportunity",
    "crosstrack",
    "peil",
    "bp2op",
    "normcard",
    "gold",
    "lake",
    "pilot",
    "poc",
    "cdc",
    "timeseries",
    "tijdreeks",
    "neerslag",
    "knmi",
    "elasticsearch",
)

TS_KEYWORDS = (
    "timeseries",
    "tijdreeks",
    "neerslag",
    "peil",
    "waterstand",
    "knmi",
    "statline",
    "wkp",
    "scenario",
)


def infer_data_plane(request: str, recipe_id: str | None = None) -> str:
    """Return 'lake', 'data_platform', or 'hybrid'."""
    text = f"{request} {recipe_id or ''}".lower()
    if "cdc" in text or "peil-conflict-live" in text or (recipe_id or "").endswith("-live"):
        return "hybrid"
    live = any(k in text for k in LIVE_KEYWORDS)
    lake = any(k in text for k in LAKE_KEYWORDS)
    if live and lake:
        return "hybrid"
    if live:
        return "data_platform"
    return "lake"


def _wants_elasticsearch(request: str, recipe_id: str | None) -> bool:
    text = f"{request} {recipe_id or ''}".lower()
    return any(k in text for k in TS_KEYWORDS)


def enrich_catalog_hits(
    hits: list[dict[str, Any]],
    *,
    request: str,
    recipe_id: str | None = None,
) -> dict[str, Any]:
    """Attach lake datasets and data-plane routing hint to catalog search."""
    from services.catalog_adapter.seed import find_lake_datasets

    plane = infer_data_plane(request, recipe_id)
    poc = None
    if recipe_id:
        for tag in ("utrecht", "breda", "rijnland", "eindhoven"):
            if tag in recipe_id:
                poc = tag
                break

    elasticsearch_hits: list[dict[str, Any]] = []
    lake_hits: list[dict[str, Any]] = []
    search_backend = "substring"

    if _wants_elasticsearch(request, recipe_id):
        try:
            from services.elasticsearch import search_lake, use_mock

            elasticsearch_hits = search_lake(request or recipe_id or "", poc=poc, size=20)
            if elasticsearch_hits:
                search_backend = "elasticsearch-mock" if use_mock() else "elasticsearch"
                lake_hits = elasticsearch_hits
        except Exception:
            elasticsearch_hits = []

    if not lake_hits:
        lake_hits = find_lake_datasets(
            poc=poc, zone="gold" if "scenario" in (request or "").lower() else None
        )
        if not lake_hits and poc:
            lake_hits = find_lake_datasets(poc=poc)
        search_backend = "substring"

    return {
        "catalog_hits": hits,
        "lake_hits": lake_hits[:20],
        "elasticsearch_hits": elasticsearch_hits[:20],
        "search_backend": search_backend,
        "data_plane": plane,
        "lakeSeriesHints": [
            {
                "seriesId": h.get("seriesId"),
                "variable": h.get("variable"),
                "poc": h.get("poc"),
                "title": h.get("title"),
                "lakeUri": h.get("lakeUri"),
            }
            for h in lake_hits
            if h.get("kind") == "timeseries_series" or h.get("seriesId")
        ][:10],
    }
