from __future__ import annotations

import json
import os
from typing import Any

import httpx

from services.common.schema import edic_entry_for_recipe

MARKETPLACE_URL = os.environ.get("MARKETPLACE_AGENT_URL", "").rstrip("/")
MARKETPLACE_TOKEN = os.environ.get("MARKETPLACE_TOKEN", "")
MARKETPLACE_BASE = os.environ.get("MARKETPLACE_BASE_URL", "https://marketplace.ldttoolbox.app")
MOCK = os.environ.get("MARKETPLACE_MOCK", "true").lower() in ("1", "true", "yes")


def _headers() -> dict[str, Any]:
    h: dict[str, str] = {}
    if MARKETPLACE_TOKEN:
        h["Authorization"] = f"Bearer {MARKETPLACE_TOKEN}"
    return h


def marketplace_asset_payload(
    recipe: dict[str, Any],
    *,
    validation_report: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recipe plus trust artefacts for EDIC / Marketplace acceptance."""
    recipe_id = recipe["id"]
    entry = edic_entry_for_recipe(recipe_id) or {}
    payload: dict[str, Any] = {
        "recipe": recipe,
        "validationReport": validation_report,
        "provenance": provenance,
        "edic": {
            "destination": entry.get("edic", "ldt-citiverse"),
            "assetClass": entry.get("assetClass", "spatial-blueprint"),
            "readiness": entry.get("readiness", "mock"),
            "owner": entry.get("owner", "ICTU"),
        },
    }
    return payload


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
    validation_report: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recipe_id = recipe["id"]
    file_name = f"recipe-{recipe_id}-v{recipe.get('version', '1.0.0')}.json"
    payload = marketplace_asset_payload(
        recipe,
        validation_report=validation_report,
        provenance=provenance,
    )
    upload = upload_asset(payload, file_name)
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
        "payload": payload,
        "mock": pub.get("mock", False),
    }
