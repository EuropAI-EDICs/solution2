from __future__ import annotations

import os
from typing import Any

import httpx


def fetch_marketplace_assets() -> list[dict[str, Any]]:
    """Optional wrapper around EU LDT Marketplace Agent categories/assets."""
    base = os.environ.get("MARKETPLACE_AGENT_URL", "").rstrip("/")
    if not base:
        return []
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base}/api/v1/agent/categories")
            if resp.status_code != 200:
                return []
            data = resp.json()
    except httpx.HTTPError:
        return []

    records: list[dict[str, Any]] = []
    items = data if isinstance(data, list) else data.get("categories", [])
    for item in items:
        name = item.get("name") or item.get("id") or "marketplace-asset"
        records.append(
            {
                "id": f"marketplace-{name}",
                "type": "asset",
                "title": str(name),
                "properties": {"source": "marketplace-agent", "raw": item},
                "links": [{"rel": "self", "href": f"marketplace://{name}"}],
            }
        )
    return records
