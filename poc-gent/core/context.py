"""Contextpipeline: intake-gate, GIS-koppeling en samenvatting met herkomst
(FR-04/05/23). De gate vraagt nooit om wat uit authentieke bronnen kan komen
(once-only); GIS-uitkomsten zijn afgeleid en dragen hun laag als bron."""

from __future__ import annotations

from pathlib import Path

from adapters import gis_zones


def open_questions(manifest: dict, slots: dict) -> list[dict]:
    vragen = []
    for slot, spec in manifest["contextSchema"]["slots"].items():
        if spec["required"] and spec.get("authenticSource") is None and slot not in slots:
            vragen.append({"slot": slot, "vraag": spec["vraag"]})
    return vragen


def build(manifest: dict, slots: dict, poc_root: Path) -> tuple[dict, dict]:
    context = dict(slots)
    herkomst = {slot: {"label": "gebruiker", "bron": "gesprek"} for slot in slots}
    try:
        gis_zones.apply_checks(manifest, context, herkomst, poc_root)
    except gis_zones.AddressError:
        # Onbekend (of adversarieel) adres: nooit gokken — zones worden
        # onbekend en de beslistabellen escaleren (unknownPolicy: escalate).
        for check in manifest.get("gisChecks", []):
            context[check["output"]] = "onbekend-adres"
            herkomst[check["output"]] = {"label": "afgeleid", "bron": "gis:adres-niet-gevonden"}
    return context, herkomst


def summary(manifest: dict, context: dict, herkomst: dict) -> dict:
    regels = []
    for slot in manifest["contextSchema"]["slots"]:
        if slot in context:
            regels.append({"feit": slot, "waarde": context[slot], **herkomst[slot]})
    for check in manifest.get("gisChecks", []):
        out = check["output"]
        if out in context:
            regels.append({"feit": out, "waarde": context[out], **herkomst[out]})
    tekst = (f"U bent {context.get('applicantType', 'onbekend')} en wilt: "
             f"{context.get('activity', 'onbekend')}. Adres: {context.get('address', 'onbekend')}.")
    return {"tekst": tekst, "regels": regels}
