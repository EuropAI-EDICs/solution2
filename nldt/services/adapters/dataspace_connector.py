"""Mock European Data Space connector (IDS/EDC stand-in for PoC)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NLDT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = NLDT_ROOT / "data" / "dataspace" / "connector-registry.json"


def _registry_path() -> Path:
    import os

    override = os.environ.get("NLDT_DATASPACE_REGISTRY")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    return REGISTRY


def mock_register_offer(offer: dict[str, Any]) -> dict[str, Any]:
    """Register an offer in the local mock connector registry."""
    path = _registry_path()
    reg: dict[str, Any]
    if path.is_file():
        reg = json.loads(path.read_text(encoding="utf-8"))
    else:
        reg = {"participantId": "nldt-nl-poc", "offers": [], "updatedAt": None}
    entry = {
        "offerId": offer.get("uid"),
        "datasetId": offer.get("datasetId"),
        "lakeUri": offer.get("lakeUri"),
        "accessClass": offer.get("accessClass"),
        "status": offer.get("status"),
        "registeredAt": datetime.now(timezone.utc).isoformat(),
    }
    # replace existing same dataset
    reg["offers"] = [o for o in reg.get("offers", []) if o.get("datasetId") != entry["datasetId"]]
    reg["offers"].append(entry)
    reg["updatedAt"] = entry["registeredAt"]
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    return {"participantId": reg["participantId"], "registered": entry}


def list_offers() -> list[dict[str, Any]]:
    if not REGISTRY.is_file():
        return []
    return json.loads(REGISTRY.read_text(encoding="utf-8")).get("offers") or []
