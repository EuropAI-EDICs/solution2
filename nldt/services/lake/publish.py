"""Gold upload + Data Space publish (ODRL stub, accessClass gates, Critic)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.common.artifact_validate import validate_artifact
from services.common.prov import utc_now
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


def _offer_validation_report(
    *,
    offer: dict[str, Any] | None,
    status: str,
    access_class: str,
    force_hitl: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a ValidationReport for a publish attempt (Phase 6 Critic/HITL)."""
    checks_v0: list[dict[str, Any]] = []
    checks_v2: list[dict[str, Any]] = []
    evidence: list[dict[str, str]] = []

    if offer:
        schema_result = validate_artifact(
            "dataspace-offer.schema.json",
            offer,
            artifact_id=str(offer.get("uid") or "offer"),
            artifact_type="process-output",
        )
        if schema_result["valid"]:
            checks_v0.append({"id": "offer-schema", "status": "pass"})
        else:
            checks_v0.append(
                {
                    "id": "offer-schema",
                    "status": "fail",
                    "detail": "; ".join(e.get("detail", "") for e in schema_result["errors"]),
                }
            )
    else:
        checks_v0.append({"id": "offer-schema", "status": "skipped", "detail": "no offer"})

    if status == "rejected":
        checks_v2.append(
            {
                "id": "access-gate",
                "status": "pass",
                "detail": reason or "rejected by accessClass gate",
            }
        )
        evidence.append({"ref": "accessClass", "note": reason or access_class})
        verdict = "fail"
        v4 = {"status": "pending", "checks": [{"id": "hitl", "status": "fail", "detail": "HITL required"}]}
    elif access_class == "restricted":
        if force_hitl and offer and offer.get("hitlApproved"):
            checks_v2.append({"id": "access-gate", "status": "pass", "detail": "HITL approved"})
            v4 = {"status": "pass", "checks": [{"id": "hitl", "status": "pass", "detail": "forceHitlApproved"}]}
            verdict = "pass" if all(c["status"] == "pass" for c in checks_v0 if c["status"] != "skipped") else "fail"
        else:
            checks_v2.append({"id": "access-gate", "status": "fail", "detail": "restricted without HITL"})
            v4 = {"status": "pending", "checks": [{"id": "hitl", "status": "fail"}]}
            verdict = "needs_human"
    else:
        checks_v2.append({"id": "access-gate", "status": "pass", "detail": access_class})
        v4 = {"status": "not_applicable"}
        verdict = "pass" if all(c["status"] == "pass" for c in checks_v0 if c["status"] != "skipped") else "fail"

    report: dict[str, Any] = {
        "id": f"VR-offer-{uuid.uuid4().hex[:8]}",
        "artifactId": (offer or {}).get("uid") or "offer-rejected",
        "artifactType": "process-output",
        "levels": {
            "V0": {"status": "pass" if all(c["status"] == "pass" for c in checks_v0 if c["status"] != "skipped") else "fail", "checks": checks_v0},
            "V1": {"status": "not_applicable"},
            "V2": {"status": "pass" if all(c["status"] == "pass" for c in checks_v2) else "fail", "checks": checks_v2},
            "V3": {"status": "not_applicable"},
            "V4": v4,
        },
        "verdict": verdict,
        "evaluatorRun": "lake-publish#offer",
        "evaluatedAt": utc_now(),
    }
    if evidence:
        report["evidence"] = evidence
    return report


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
        report = _offer_validation_report(
            offer=None,
            status="rejected",
            access_class=cls,
            force_hitl=force_hitl_approved,
            reason=err,
        )
        return {
            "status": "rejected",
            "reason": err,
            "accessClass": cls,
            "lakeUri": lake_uri,
            "validationReport": report,
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

    # Schema-validate before persistence
    schema_result = validate_artifact(
        "dataspace-offer.schema.json",
        offer,
        artifact_id=str(offer["uid"]),
        artifact_type="process-output",
    )
    if not schema_result["valid"]:
        report = schema_result["validationReport"]
        report["verdict"] = "fail"
        return {
            "status": "rejected",
            "reason": "offer failed dataspace-offer.schema.json",
            "accessClass": cls,
            "lakeUri": lake_uri,
            "validationReport": report,
            "schemaErrors": schema_result["errors"],
        }

    offers = _offers_dir()
    path = offers / f"{offer['uid']}.json"
    path.write_text(json.dumps(offer, indent=2), encoding="utf-8")

    client = get_lake_client()
    client.put_bytes(
        f"offers/{offer['uid']}.json",
        path.read_bytes(),
        content_type="application/json",
    )

    from services.adapters.dataspace_connector import register_offer

    connector = register_offer(offer)
    report = _offer_validation_report(
        offer=offer,
        status="ok",
        access_class=cls,
        force_hitl=force_hitl_approved,
    )
    return {
        "status": "ok",
        "offer": offer,
        "offerPath": str(path),
        "connector": connector,
        "validationReport": report,
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
