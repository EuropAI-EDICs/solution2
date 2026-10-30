"""Validatie-engine (F2): beoordeelt het conceptformulier tegen de
geconfigureerde voorwaarden. Blokkades en waarschuwingen krijgen een melding
met correctiepad — een autonome eindbeslissing is er niet (FR-13)."""

from __future__ import annotations

from core.rules import matches


def valideer(manifest: dict, service_id: str, formulier: dict) -> dict:
    waarden = {v["veld"]: v["waarde"] for v in formulier["velden"]}
    bevindingen: list[dict] = []
    for veld in formulier.get("ontbrekend", []):
        bevindingen.append({"id": f"V0-{veld}", "ernst": "blokkade",
                            "melding": f"Ontbrekend gegeven: {veld} — vraag het aan bij de bronhouder."})
    for check in manifest["services"][service_id].get("validaties", []):
        vuurde, _reden = matches(check["wanneer"], waarden)
        if vuurde:
            bevindingen.append({"id": check["id"], "ernst": check["ernst"], "melding": check["melding"]})
    if any(b["ernst"] == "blokkade" for b in bevindingen):
        status = "blokkade"
    elif any(b["ernst"] == "waarschuwing" for b in bevindingen):
        status = "gereed-met-waarschuwing"
    else:
        status = "gereed"
    return {"status": status, "bevindingen": bevindingen}
