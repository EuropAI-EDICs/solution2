"""Prefill-engine (F2): zet het formulier van één dienst klaar met per veld een
zichtbaar herkomstlabel (FR-11). Authentieke velden komen uitsluitend uit de
Magda-records; gespreksvelden uit de bevestigde context. Ontbrekende velden
worden benoemd, nooit verzonnen (AI-05-geest)."""

from __future__ import annotations


def _uit_record(record: dict, pad: str):
    waarde: object = record
    for stap in pad.split("."):
        if not isinstance(waarde, dict) or stap not in waarde:
            return None
        waarde = waarde[stap]
    return waarde


def bouw(manifest: dict, service_id: str, context: dict, herkomst: dict, records: dict) -> dict:
    formulier_regels = manifest["services"][service_id]["formulier"]
    velden: list[dict] = []
    ontbrekend: list[str] = []
    for regel in formulier_regels:
        bron_referentie = regel["bron"]
        if bron_referentie.startswith("slot:"):
            slot = bron_referentie[5:]
            waarde = context.get(slot)
            herkomst_regel = herkomst.get(slot) or {"label": "gebruiker", "bron": "gesprek (niet verstrekt)"}
            veld = {"veld": regel["veld"], "waarde": waarde, **herkomst_regel}
            if waarde is None:
                ontbrekend.append(regel["veld"])
        else:
            tool, _, pad = bron_referentie.partition(".")
            record = records.get(tool)
            waarde = _uit_record(record, pad) if record else None
            veld = {"veld": regel["veld"], "waarde": waarde, "label": "authentiek", "bron": f"{tool} (mock v1)"}
            if waarde is None:
                ontbrekend.append(regel["veld"])
        velden.append(veld)
    return {"service": service_id, "velden": velden, "ontbrekend": ontbrekend}
