"""European Data Space connector — mock + EDC-compatible backends (Phase 6).

Backends (``NLDT_DATASPACE_CONNECTOR``):

- ``mock`` (default) — local JSON registry (PoC stand-in)
- ``edc-manifest`` — write Eclipse Dataspace Connector–shaped Asset /
  ContractDefinition manifests for later import into a real EDC
- ``http`` — POST Asset to ``NLDT_EDC_MANAGEMENT_URL`` (EDC Management API);
  on transport failure, falls back to writing the manifest + recording error
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NLDT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = NLDT_ROOT / "data" / "dataspace" / "connector-registry.json"
MANIFEST_DIR = NLDT_ROOT / "data" / "dataspace" / "edc-manifests"


def _registry_path() -> Path:
    override = os.environ.get("NLDT_DATASPACE_REGISTRY")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    return REGISTRY


def _manifest_dir() -> Path:
    override = os.environ.get("NLDT_EDC_MANIFEST_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    return MANIFEST_DIR


def offer_to_edc_asset(offer: dict[str, Any]) -> dict[str, Any]:
    """Map an nLDT ODRL-stub offer to a minimal EDC Management API v3 Asset."""
    asset_id = offer.get("uid") or offer.get("datasetId")
    lake_uri = offer.get("lakeUri") or ""
    return {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@id": asset_id,
        "properties": {
            "name": offer.get("datasetId"),
            "contenttype": "application/json",
            "nldt:accessClass": offer.get("accessClass"),
            "nldt:lakeUri": lake_uri,
            "nldt:license": offer.get("license"),
            "nldt:offerStatus": offer.get("status"),
        },
        "dataAddress": {
            "@type": "DataAddress",
            "type": "HttpData" if lake_uri.startswith("http") else "AmazonS3",
            "baseUrl": lake_uri if lake_uri.startswith("http") else None,
            "keyName": lake_uri,
        },
    }


def offer_to_edc_contract_definition(offer: dict[str, Any]) -> dict[str, Any]:
    """Minimal ContractDefinition referencing the offer's accessClass policy."""
    offer_id = offer.get("uid")
    return {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@id": f"contract-{offer_id}",
        "accessPolicyId": f"policy-{offer.get('accessClass', 'internal')}",
        "contractPolicyId": f"policy-{offer.get('accessClass', 'internal')}",
        "assetsSelector": {
            "@type": "CriterionDto",
            "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
            "operator": "=",
            "operandRight": offer_id,
        },
    }


def write_edc_manifest(offer: dict[str, Any]) -> dict[str, Any]:
    """Persist EDC-shaped Asset + ContractDefinition for operator import."""
    asset = offer_to_edc_asset(offer)
    contract = offer_to_edc_contract_definition(offer)
    bundle = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "participantId": os.environ.get("NLDT_DATASPACE_PARTICIPANT", "nldt-nl-poc"),
        "asset": asset,
        "contractDefinition": contract,
        "sourceOffer": {"uid": offer.get("uid"), "datasetId": offer.get("datasetId")},
    }
    path = _manifest_dir() / f"{offer.get('uid')}.edc.json"
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return {
        "backend": "edc-manifest",
        "manifestPath": str(path),
        "assetId": asset.get("@id"),
        "status": "manifest_written",
    }


def http_register_offer(offer: dict[str, Any]) -> dict[str, Any]:
    """POST Asset to EDC Management API; fall back to manifest on failure."""
    base = (os.environ.get("NLDT_EDC_MANAGEMENT_URL") or "").rstrip("/")
    asset = offer_to_edc_asset(offer)
    if not base:
        manifest = write_edc_manifest(offer)
        manifest["status"] = "manifest_only_no_url"
        manifest["backend"] = "http"
        return manifest

    import httpx

    url = f"{base}/v3/assets"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=asset)
            remote = {
                "backend": "http",
                "url": url,
                "httpStatus": resp.status_code,
                "assetId": asset.get("@id"),
            }
            if resp.status_code >= 400:
                remote["status"] = "remote_error"
                remote["body"] = resp.text[:500]
                remote["fallback"] = write_edc_manifest(offer)
            else:
                remote["status"] = "registered"
                # still write manifest for audit
                remote["manifest"] = write_edc_manifest(offer)
            return remote
    except Exception as exc:  # noqa: BLE001 — connector must not crash publish
        manifest = write_edc_manifest(offer)
        return {
            "backend": "http",
            "url": url,
            "status": "transport_error",
            "error": str(exc),
            "fallback": manifest,
        }


def mock_register_offer(offer: dict[str, Any]) -> dict[str, Any]:
    """Register an offer in the local mock connector registry."""
    path = _registry_path()
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
    reg["offers"] = [o for o in reg.get("offers", []) if o.get("datasetId") != entry["datasetId"]]
    reg["offers"].append(entry)
    reg["updatedAt"] = entry["registeredAt"]
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    return {
        "backend": "mock",
        "participantId": reg["participantId"],
        "registered": entry,
        "status": "registered",
    }


def register_offer(offer: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the configured Data Space connector backend."""
    backend = (os.environ.get("NLDT_DATASPACE_CONNECTOR") or "mock").strip().lower()
    if backend in {"http", "edc", "edc-http"}:
        result = http_register_offer(offer)
        # also keep local registry for operators
        mock = mock_register_offer(offer)
        result["localRegistry"] = mock
        return result
    if backend in {"edc-manifest", "manifest", "file"}:
        result = write_edc_manifest(offer)
        result["localRegistry"] = mock_register_offer(offer)
        return result
    return mock_register_offer(offer)


def list_offers() -> list[dict[str, Any]]:
    path = _registry_path()
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("offers") or []
