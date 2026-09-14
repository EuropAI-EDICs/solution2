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
    lake_hits = find_lake_datasets(poc=poc, zone="gold" if "scenario" in (request or "").lower() else None)
    if not lake_hits and poc:
        lake_hits = find_lake_datasets(poc=poc)
    return {
        "catalog_hits": hits,
        "lake_hits": lake_hits[:20],
        "data_plane": plane,
    }
