"""Bevestigingsmoment H1: de gebruiker bevestigt of corrigeert de context
(FR-05). Correcties zijn transactie-input met eigen herkomstlabel en
overschrijven nooit een authentieke bron — daarvoor wordt de gebruiker naar
de bronhouder verwezen (DATA-06)."""

from __future__ import annotations

from pathlib import Path

from adapters import acm_idm_mock, gis_zones


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
        gis_zones.apply_checks(manifest, context, herkomst, poc_root, suffix=", na correctie")
    return context, herkomst


def h2_uitleg(manifest: dict, service_ids: list[str]) -> dict:
    """Leg uit welke authentieke bronnen nodig zijn, waarvoor en waarom (FR-09)."""
    doelen = {bron["source"]: bron["purpose"] for bron in manifest.get("authenticSources", [])}
    benodigd: set[str] = set()
    for service_id in service_ids:
        for regel in manifest["services"][service_id].get("formulier", []):
            referentie = regel["bron"]
            if not referentie.startswith("slot:"):
                benodigd.add(referentie.split(".")[0])
    bronnen = [{"tool": tool, "purpose": doelen[tool]} for tool in sorted(benodigd) if tool in doelen]
    waarom = ("Voor deze aanvraag hebben we een paar gegevens nodig die we niet aan u mogen vragen: "
              "die halen we veilig op bij de officiële bronnen, alléén voor het doel hierboven. "
              "Daarom vragen we u eerst om een korte authenticatie.")
    return {"bronnen": bronnen, "waarom": waarom}


def decide_h2(manifest: dict, context: dict, identiteit: dict, service_ids: list[str]) -> dict:
    """Mandaatcontrole vóór gegevensgebruik: zonder geldig mandaat geen doorgang
    — de menselijke route geldt (AI-05-geest)."""
    if not acm_idm_mock.geldig_mandaat(identiteit, context):
        return {"doorgang": False, "reden": "Mandaat niet geverifieerd: overname door een medewerker (Gentinfo) voor de mandatencontrole."}
    return {"doorgang": True, "reden": "geverifieerd"}
