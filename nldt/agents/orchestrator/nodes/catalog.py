from __future__ import annotations

import os
from typing import Any

import httpx

from agents.orchestrator.data_plane import enrich_catalog_hits
from agents.orchestrator.llm_hook import rank_recipes

CATALOG_URL = os.environ.get("NLDT_CATALOG_URL", "http://localhost:8083")
COOKBOOK_URL = os.environ.get("NLDT_COOKBOOK_URL", "http://localhost:8081")


def catalog_search(state: dict[str, Any]) -> dict[str, Any]:
    q = state.get("natural_language_request", "")
    recipe_id = state.get("recipe_id")
    if os.environ.get("NLDT_OFFLINE") == "1":
        from services.catalog_adapter.seed import find_records

        hits = find_records(q=q or recipe_id)
    else:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{CATALOG_URL}/records", params={"q": q or recipe_id})
            resp.raise_for_status()
            hits = resp.json().get("features", [])
    if recipe_id:
        hits = [
            h
            for h in hits
            if h.get("properties", {}).get("recipeId") == recipe_id
            or h.get("id") == f"recipe-{recipe_id}"
            or recipe_id in h.get("id", "")
        ] or hits
    hits = rank_recipes(q, hits)
    enriched = enrich_catalog_hits(hits, request=q, recipe_id=recipe_id)
    return enriched
