"""Bevestigingsmoment H1: de gebruiker bevestigt of corrigeert de context
(FR-05). Correcties zijn transactie-input met eigen herkomstlabel en
overschrijven nooit een authentieke bron — daarvoor wordt de gebruiker naar
de bronhouder verwezen (DATA-06)."""

from __future__ import annotations

from pathlib import Path

from adapters import gis_zones


def confirm_h1(manifest: dict, context: dict, herkomst: dict, corrections: dict, poc_root: Path) -> tuple[dict, dict]:
    slots = manifest["contextSchema"]["slots"]
    context = dict(context)
    herkomst = dict(herkomst)
    for slot, waarde in corrections.items():
        if slot not in slots:
            raise KeyError(f"onbekende correctie-slot: {slot}")
        if slots[slot].get("authenticSource") is not None:
            raise ValueError(f"'{slot}' is een authentiek gegeven: correctie loopt via de bronhouder")
        context[slot] = waarde
        herkomst[slot] = {"label": "correctie", "bron": "gebruiker (H1)"}
    if "address" in corrections:
        zones = gis_zones.load_zones(poc_root)
        lon, lat = gis_zones.lookup_address(poc_root, context["address"])
        for check in manifest.get("gisChecks", []):
            context[check["output"]] = gis_zones.zone_result(zones, check["layer"], lon, lat)
            herkomst[check["output"]] = {"label": "afgeleid", "bron": f"gis:{check['layer']} (fixture v1, na correctie)"}
    return context, herkomst
