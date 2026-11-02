"""Contextpipeline: intake-gate, GIS-koppeling en samenvatting met herkomst
(FR-04/05/23). De gate vraagt nooit om wat uit authentieke bronnen kan komen
(once-only); GIS-uitkomsten zijn afgeleid en dragen hun laag als bron; het
burgerpakket voegt dataset-lookups (dataChecks) toe naast de zonechecks."""

from __future__ import annotations

from pathlib import Path

from adapters import data_lookups, gis_zones, timing_checks

DEFAULT_ZIN = "U bent {applicantType} en wilt: {activity}. Adres: {address}."


class _Onbekend(dict):
    def __missing__(self, key):
        return "onbekend"


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
    data_lookups.apply_checks(manifest, context, herkomst, poc_root)
    timing_checks.apply_checks(manifest, context, herkomst, poc_root)
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
    for check in manifest.get("dataChecks", []):
        for out in check["outputs"]:
            if out in context:
                regels.append({"feit": out, "waarde": context[out], **herkomst[out]})
    for check in manifest.get("timingChecks", []):
        if check["output"] in context:
            regels.append({"feit": check["output"], "waarde": context[check["output"]],
                           **herkomst[check["output"]]})
    zin = manifest.get("texts", {}).get("contextZin") or DEFAULT_ZIN
    tekst = zin.format_map(_Onbekend(context))
    return {"tekst": tekst, "regels": regels}
