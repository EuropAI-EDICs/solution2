"""Submit-engine (F3): bereidt een inzending voor met idempotentiesleutel over
de canonieke conceptlading en dient die in bij het backoffice-contract."""

from __future__ import annotations

import hashlib
import json

from adapters import backoffice_mock

BACKOFFICE_CONTRACT = "district09-vergunningen"


def contract_van(manifest: dict) -> str:
    """Per-pakket backoffice-contract (config-is-data): het manifest kan een
    ander contract declareren; de mobiliteitsdefault blijft het bestaande."""
    return manifest.get("submission", {}).get("contract") or BACKOFFICE_CONTRACT


def bereid_voor(package_id: str, persona_id: str, service_id: str, draft: dict) -> dict:
    lading = json.dumps(draft, ensure_ascii=False, sort_keys=True)
    sleutel = hashlib.sha256(f"{package_id}|{persona_id}|{service_id}|{lading}".encode("utf-8")).hexdigest()[:16]
    return {"service": service_id, "lading": draft, "idempotentie_sleutel": sleutel}


def dien_in(manifest: dict, package_id: str, persona_id: str, formulieren: list[dict]) -> list[dict]:
    contract = contract_van(manifest)
    resultaten = []
    for formulier in formulieren:
        voorbereid = bereid_voor(package_id, persona_id, formulier["service"], formulier)
        ontvangst = backoffice_mock.dien_in(contract, voorbereid["lading"],
                                            voorbereid["idempotentie_sleutel"])
        resultaten.append({"service": formulier["service"], "referentie": ontvangst["referentie"],
                           "status": ontvangst["status"]})
    return resultaten
