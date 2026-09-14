"""Gold upload + Data Space publish (ODRL stub, accessClass gates)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.lake import DEFAULT_BUCKET, NLDT_ROOT, get_lake_client, load_deny
from services.lake.sync import access_class_for_local, sync_file

OFFERS_DIR = NLDT_ROOT / "data" / "dataspace" / "offers"


def _offers_dir() -> Path:
    override = os.environ.get("NLDT_DATASPACE_OFFERS_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    OFFERS_DIR.mkdir(parents=True, exist_ok=True)
    return OFFERS_DIR


def upload_execution_gold(
    execution: dict[str, Any],
    *,
    run_id: str | None = None,
    poc: str = "utrecht",
) -> dict[str, Any]:
    """Upload recipe execution outputs JSON to gold zone."""
    rid = run_id or execution.get("runId") or uuid.uuid4().hex[:12]
    recipe = execution.get("recipeId") or "unknown"
    key = f"gold/{poc}/run/{rid}/{recipe}-outputs.json"
    client = get_lake_client()
    payload = json.dumps(execution.get("outputs") or execution, indent=2).encode("utf-8")
    uri = client.put_bytes(key, payload, content_type="application/json")
    return {"lakeUri": uri, "key": key, "runId": rid}


def _deny_publish(access_class: str, force_hitl: bool) -> str | None:
    if access_class == "restricted" and not force_hitl:
        return "accessClass=restricted requires forceHitlApproved=true"
    return None


def build_odrl_offer(
    *,
    dataset_id: str,
    lake_uri: str,
    access_class: str,
    license_: str | None = None,
) -> dict[str, Any]:
    """Minimal ODRL-shaped offer stub (not full ODRL JSON-LD)."""
    offer_id = f"offer-{uuid.uuid4().hex[:10]}"
    permission = {
        "action": "use",
        "constraint": [
            {"leftOperand": "accessClass", "operator": "eq", "rightOperand": access_class},
        ],
    }
    if access_class == "internal":
        permission["constraint"].append(
            {"leftOperand": "spatial", "operator": "isA", "rightOperand": "nldt-participant"}
        )
    return {
        "@type": "Offer",
        "uid": offer_id,
        "datasetId": dataset_id,
        "lakeUri": lake_uri,
        "accessClass": access_class,
        "license": license_ or "unknown",
        "permission": [permission],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "draft" if access_class == "restricted" else "published",
    }


def publish_dataset(
    *,
    lake_uri: str | None = None,
    lake_key: str | None = None,
    dataset_id: str | None = None,
    access_class: str | None = None,
    force_hitl_approved: bool = False,
    license_: str | None = None,
) -> dict[str, Any]:
    """Create a Data Space offer; refuse restricted without HITL."""
    if not lake_uri and lake_key:
        lake_uri = f"lake://{DEFAULT_BUCKET}/{lake_key.lstrip('/')}"
    if not lake_uri:
        raise ValueError("lake_uri or lake_key required")

    key = lake_key or lake_uri.split(f"{DEFAULT_BUCKET}/")[-1]
    cls = access_class
    if not cls:
        # infer from deny defaults / inventory if present
        inv_path = NLDT_ROOT / "data" / "lake-inventory.json"
        if inv_path.is_file():
            for row in json.loads(inv_path.read_text(encoding="utf-8")).get("datasets") or []:
                if row.get("lakeUri") == lake_uri or row.get("lakeKey") == key:
                    cls = row.get("accessClass")
                    dataset_id = dataset_id or row.get("id")
                    license_ = license_ or row.get("license")
                    break
        cls = cls or "internal"

    err = _deny_publish(cls, force_hitl_approved)
    if err:
        return {
            "status": "rejected",
            "reason": err,
            "accessClass": cls,
            "lakeUri": lake_uri,
        }

    ds_id = dataset_id or key.replace("/", "-")
    offer = build_odrl_offer(
        dataset_id=ds_id,
        lake_uri=lake_uri,
        access_class=cls,
        license_=license_,
    )
    if force_hitl_approved and cls == "restricted":
        offer["status"] = "published"
        offer["hitlApproved"] = True

    offers = _offers_dir()
    path = offers / f"{offer['uid']}.json"
    path.write_text(json.dumps(offer, indent=2), encoding="utf-8")

    # also store under lake offers/
    client = get_lake_client()
    client.put_bytes(
        f"offers/{offer['uid']}.json",
        path.read_bytes(),
        content_type="application/json",
    )

    from services.adapters.dataspace_connector import mock_register_offer

    connector = mock_register_offer(offer)
    return {
        "status": "ok",
        "offer": offer,
        "offerPath": str(path),
        "connector": connector,
    }


def sync_local_to_gold(src: Path, poc: str, run_type: str, run_id: str) -> dict[str, Any]:
    client = get_lake_client()
    deny = load_deny()
    key = f"gold/{poc}/{run_type}/{run_id}/{src.name}"
    meta = {
        "poc": poc,
        "accessClass": access_class_for_local(src, poc, deny, zone="gold"),
    }
    return sync_file(client, src, key, metadata=meta)
