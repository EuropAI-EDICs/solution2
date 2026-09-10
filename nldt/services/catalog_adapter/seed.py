from __future__ import annotations

import os
from typing import Any

COOKBOOK_BASE = os.environ.get("NLDT_COOKBOOK_URL", "http://localhost:8081")
CATALOG_BASE = os.environ.get("NLDT_CATALOG_URL", "http://localhost:8083")


def seed_records() -> list[dict[str, Any]]:
    processes = [
        ("fetch-features", "Fetch GeoJSON features from URI"),
        ("spatial-intersection", "Intersect two feature collections"),
        ("compute-area-statistics", "Compute area statistics"),
        ("h3-polygon-to-cells", "H3 hex coverage of a polygon layer"),
        ("h3-cells-to-geojson", "H3 cell boundaries as GeoJSON"),
        ("h3-spatial-join-points", "Join points to H3 cells (counts per cell)"),
        ("h3-knn", "K nearest points by H3 grid distance"),
        ("h3-morans-i", "Global Moran's I over H3 cell values"),
    ]
    records: list[dict[str, Any]] = []
    for pid, title in processes:
        records.append(
            {
                "id": f"process-{pid}",
                "type": "process",
                "title": title,
                "properties": {"processId": pid},
                "links": [
                    {"rel": "self", "href": f"{CATALOG_BASE}/records/process-{pid}"},
                    {
                        "rel": "process-description",
                        "href": f"http://localhost:8082/processes/{pid}",
                        "type": "application/json",
                    },
                ],
            }
        )

    records.append(
        {
            "id": "recipe-spatial-overlay-analysis",
            "type": "recipe",
            "title": "Spatial Overlay Analysis",
            "properties": {
                "recipeId": "spatial-overlay-analysis",
                "tags": ["spatial", "overlay", "analysis", "generic"],
            },
            "links": [
                {"rel": "self", "href": f"{CATALOG_BASE}/records/recipe-spatial-overlay-analysis"},
                {
                    "rel": "recipe",
                    "href": f"{COOKBOOK_BASE}/recipes/spatial-overlay-analysis",
                    "type": "application/json",
                },
            ],
        }
    )
    return records


def find_records(
    *,
    q: str | None = None,
    record_type: str | None = None,
) -> list[dict[str, Any]]:
    records = seed_records()
    if record_type:
        records = [r for r in records if r.get("type") == record_type]
    if q:
        q_lower = q.lower()
        records = [
            r
            for r in records
            if q_lower in r.get("title", "").lower()
            or q_lower in str(r.get("properties", {})).lower()
        ]
    return records
