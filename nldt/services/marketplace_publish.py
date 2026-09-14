from __future__ import annotations

import json
import os
from typing import Any

import httpx

MARKETPLACE_URL = os.environ.get("MARKETPLACE_AGENT_URL", "").rstrip("/")
MARKETPLACE_TOKEN = os.environ.get("MARKETPLACE_TOKEN", "")
MARKETPLACE_BASE = os.environ.get("MARKETPLACE_BASE_URL", "https://marketplace.ldttoolbox.app")
MOCK = os.environ.get("MARKETPLACE_MOCK", "true").lower() in ("1", "true", "yes")


def _headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if MARKETPLACE_TOKEN:
        h["Authorization"] = f"Bearer {MARKETPLACE_TOKEN}"
    return h


def upload_asset(payload: dict[str, Any], file_name: str) -> dict[str, Any]:
    if MOCK or not MARKETPLACE_URL:
        return {"id": f"mock-asset-{file_name}", "mock": True}
    data = json.dumps(payload, indent=2).encode("utf-8")
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{MARKETPLACE_URL}/api/v1/agent/assets",
            files={"file": (file_name, data, "application/json")},
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def publish_asset(
    asset_id: str,
    *,
    name: str,
    description: str,
    categories: list[str],
    licence: str = "EUPL-1.2",
) -> dict[str, Any]:
    if MOCK or not MARKETPLACE_URL:
        return {
            "id": asset_id,
            "status": "published",
            "publishState": {"offering_id": f"mock-offering-{asset_id}"},
            "mock": True,
        }
    body = {
        "name": name,
        "description": description,
        "categories": categories,
        "licence": licence,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{MARKETPLACE_URL}/api/v1/agent/assets/{asset_id}/publish",
            json=body,
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def publish_recipe(
    recipe: dict[str, Any],
    *,
    categories: list[str] | None = None,
    licence: str = "EUPL-1.2",
) -> dict[str, Any]:
    recipe_id = recipe["id"]
    file_name = f"recipe-{recipe_id}-v{recipe.get('version', '1.0.0')}.json"
    upload = upload_asset(recipe, file_name)
    asset_id = upload["id"]
    pub = publish_asset(
        asset_id,
        name=recipe.get("title", recipe_id),
        description=recipe.get("description", f"nLDT recipe {recipe_id}"),
        categories=categories or ["urn:ngsi-ld:category:processes"],
        licence=licence,
    )
    offering_id = pub.get("publishState", {}).get("offering_id")
    link = f"{MARKETPLACE_BASE}/catalogue/offering/{offering_id}" if offering_id else ""
    return {
        "assetId": asset_id,
        "offeringId": offering_id,
        "marketplaceLink": link,
        "publishResponse": pub,
        "mock": pub.get("mock", False),
    }
