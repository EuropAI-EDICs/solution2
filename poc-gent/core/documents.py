"""Documentenmodule (F3): compleetheid, type, grootte en virusscan-uitslag van
aangeleverde bewijzen (FR-12). OCR is assisterend en komt in F3 niet voor;
beslissingen blijven bij de mens (H4)."""

from __future__ import annotations

TOEGESTANE_TYPES = ("pdf", "jpg", "png")
MAX_KB = 10240


def controleer(manifest: dict, service_id: str, aangeleverd: list[dict]) -> dict:
    eisen = manifest["services"][service_id].get("documenten", [])
    per_id = {d["id"]: d for d in aangeleverd}
    bevindingen: list[dict] = []
    for eis in eisen:
        doc = per_id.get(eis["id"])
        if doc is None:
            if eis.get("verplicht"):
                bevindingen.append({"id": f"D0-{eis['id']}", "ernst": "blokkade",
                                    "melding": f"Ontbrekend document: {eis['titel']}."})
            continue
        if doc.get("type") not in TOEGESTANE_TYPES:
            bevindingen.append({"id": f"D1-{eis['id']}", "ernst": "blokkade",
                                "melding": f"Bestandstype niet toegestaan ({doc.get('type')}): gebruik pdf, jpg of png."})
        if (doc.get("grootteKB") or 0) > MAX_KB:
            bevindingen.append({"id": f"D2-{eis['id']}", "ernst": "blokkade",
                                "melding": f"Bestand te groot ({doc.get('grootteKB')} kB; max {MAX_KB} kB)."})
        if doc.get("scanSchoon") is False:
            bevindingen.append({"id": f"D3-{eis['id']}", "ernst": "waarschuwing",
                                "melding": "Virusscan niet schoon — bestand staat in quarantaine; lever opnieuw aan."})
    volledig = not bevindingen
    return {"volledig": volledig, "bevindingen": bevindingen}
