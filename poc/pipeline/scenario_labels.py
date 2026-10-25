"""Nederlandse éénregel-labels voor Utrecht scenario-sweep.

Gedeeld door de Leia-viewer (``make_viewer_config.py``) en de simulatie-
contextkaarten (``context_map.py`` / what-if-demo). Geen km², geen IoU,
geen FR-codes — alleen wat er t.o.v. de baseline verandert.
"""

from __future__ import annotations

SCENARIO_KLEUREN = (
    "#1a7f37",  # meer ruimte / soepeler
    "#c01c28",  # strenger / minder ruimte
    "#1c71d8",  # buffer / band
    "#e5a50a",  # overig
)

BASELINE_VERSCHIL = "Baseline: kanszone met de huidige regels"

# scenarioId → éénregel-verschil t.o.v. de baseline
SCENARIO_VERSCHIL: dict[str, str] = {
    # wind
    "SC-W-NNN-EXCEPTION":
        "Verschil: Natuurnetwerk mag open — uitzondering overal aangenomen",
    "SC-W-STILTE-HARD":
        "Verschil: stiltegebieden volledig uitgesloten (nu nog voorwaardelijk)",
    "SC-W-NATURA-SETBACK":
        "Verschil: extra buffer van 500 m rond Natura 2000 en ganzenrust",
    # zon
    "SC-Z-GROENE-CONTOUR-HARD":
        "Verschil: groene contour volledig uitgesloten (natuur eerst)",
    "SC-Z-GEEN-NATURA-CARVE":
        "Verschil: Natura/ganzenrust niet meer uit het zonneveld gehaald",
    "SC-Z-ZONE-BUFFER-500":
        "Verschil: zoekgebied zonneveld 500 m breder",
    # bos
    "SC-B-OUDE-BOS-HARD":
        "Verschil: oude bosgroeiplaatsen volledig uitgesloten",
    "SC-B-COMPENSATIE-HARD":
        "Verschil: compensatieplicht als harde uitsluiting",
    "SC-B-EXPAND-1KM":
        "Verschil: zoekgebied 1 km breder",
    # water
    "SC-WA-OVERSTROOMBAAR-HARD":
        "Verschil: overstroombaar gebied volledig uitgesloten",
    "SC-WA-VRIJWARING-HARD":
        "Verschil: vrijwaringszone waterkering volledig uitgesloten",
    "SC-WA-WATERBERGING-BUFFER-500":
        "Verschil: waterbergingsgebied 500 m breder uitgesloten",
    # bodem
    "SC-BO-ALLEEN-REKENING-HOUDEN":
        "Verschil: grondwaterbescherming alleen ‘rekening houden met’",
    "SC-BO-STORTPLAATS-HARD":
        "Verschil: gesloten stortplaats volledig uitgesloten",
    "SC-BO-GWB-BUFFER-500":
        "Verschil: grondwaterbeschermingszone 500 m breder uitgesloten",
    # mobiliteit
    "SC-MO-GELUID-HARD":
        "Verschil: geluidcontouren volledig uitgesloten voor bebouwing",
    "SC-MO-WEG-HARD":
        "Verschil: beperkingengebied provinciale weg volledig uitgesloten",
    "SC-MO-LUCHTVAART-ONVOORWAARDELIJK":
        "Verschil: luchtvaartverbod als harde uitsluiting over het hele gebied",
    # landschap
    "SC-LS-CHS-HARD":
        "Verschil: cultuurhistorische hoofdstructuur volledig uitgesloten",
    "SC-LS-AARDKUNDIG-HARD":
        "Verschil: aardkundige waarden volledig uitgesloten",
    "SC-LS-LIMES-BUFFER-100":
        "Verschil: Limes-kernzone 100 m breder uitgesloten",
    # landbouw
    "SC-LB-STABILISERING-OPEN":
        "Verschil: landbouwstabiliseringsgebied niet meer uitgesloten",
    "SC-LB-BEDRIJVEN-HARD":
        "Verschil: gebied agrarische bedrijven volledig uitgesloten",
    "SC-LB-GLASTUIN-OVERAL":
        "Verschil: glastuinbouw overal mogelijk (concentratielimiet weg)",
    # wonen
    "SC-WN-ALLEEN-STEDELIJK":
        "Verschil: woningbouw alleen in bestaand stedelijk gebied",
    "SC-WN-FLEXWONINGEN-DICHT":
        "Verschil: route voor flexwoningen dichtgezet",
    "SC-WN-STILTE-1KM":
        "Verschil: stiltegebied hard uitgesloten, aandachtszone tot 1 km",
    # werken
    "SC-WE-DETAILHANDEL-HARD":
        "Verschil: detailhandelsverbod als harde uitsluiting",
    "SC-WE-ALLEEN-STEDELIJK":
        "Verschil: bedrijventerrein alleen in bestaand stedelijk gebied",
    "SC-WE-BEDRIJVENTERREIN-BUFFER-500":
        "Verschil: zoekgebied bedrijventerrein 500 m breder",
    # recreatie
    "SC-RC-ALLEEN-DAGRECREATIE":
        "Verschil: alleen bovenlokale dagrecreatie blijft open",
    "SC-RC-DAGRECREATIE-BUFFER-500":
        "Verschil: dagrecreatieterrein 500 m breder",
    "SC-RC-DAGRECREATIE-ALLEEN-AANDACHT":
        "Verschil: dagrecreatie alleen als aandachtsgebied (niet meer open)",
    # biomassa
    "SC-BM-LANDELIJK-HARD":
        "Verschil: landelijk vestigingsgebied biomassa volledig uitgesloten",
    "SC-BM-STEDELIJK-HARD":
        "Verschil: stedelijk vestigingsgebied biomassa volledig uitgesloten",
    "SC-BM-BUFFER-500":
        "Verschil: landelijk biomassa-gebied 500 m breder uitgesloten",
    # energietoets
    "SC-ET-TOETS-HARD":
        "Verschil: energietoets als ruimtelijke blokkade",
    "SC-ET-GEEN-MOTIVATIE":
        "Verschil: motivatieplicht energieparagraaf weggelaten",
    "SC-ET-NETCONGESTIE":
        "Verschil: netcongestiezones uitgesloten (data netbeheerders)",
    # what-ifs
    "SC-WON-NETCONGESTIE-INCLUSIE-500M":
        "Verschil: woningbouw binnen 500 m van netcongestie toegestaan",
    "SC-WER-NETCONGESTIE-1KM":
        "Verschil: bedrijventerreinen 1 km rond netcongestie uitgesloten",
}


def scenario_verschil(s: dict) -> str:
    """Eénregel-verschil t.o.v. baseline — voor kaarttitel, popup en paneel."""
    scid = str(s.get("scenarioId") or "")
    if scid in SCENARIO_VERSCHIL:
        return SCENARIO_VERSCHIL[scid]
    naam = str(s.get("name") or "").strip()
    if naam:
        return f"Verschil: {naam}"
    return f"Verschil: scenario {scid or '?'}"


def scenario_kort(s: dict | str) -> str:
    """Korte laagtitel zonder herhaald 'Verschil:'-prefix."""
    if isinstance(s, str):
        tekst = SCENARIO_VERSCHIL.get(s, s)
    else:
        tekst = scenario_verschil(s)
    return tekst.removeprefix("Verschil: ").strip()


def scenario_kleur(index: int, delta: float = 0.0) -> str:
    """Eigen kleur per scenario; richting (meer/minder) als fallback."""
    if 0 <= index < len(SCENARIO_KLEUREN):
        return SCENARIO_KLEUREN[index]
    return "#1a7f37" if delta >= 0 else "#c01c28"


def final_only_fc(fc: dict) -> dict:
    """Houd alleen de final-kanszone over uit een scenario-GeoJSON.

    Scenario-bestanden bevatten de hele engine-keten (inclusion ≈ provincie,
    intersection, differences, markers, final). Unie daarvan tekent de hele
    provincie; de zichtbare 'vlekken' zijn uitsluitend ``operation == final``.
    """
    feats = []
    for f in fc.get("features") or []:
        props = f.get("properties") or {}
        op = str(props.get("operation") or "")
        fid = str(props.get("id") or "")
        if op == "final" or fid.startswith("zr-final"):
            feats.append(f)
    return {"type": "FeatureCollection", "features": feats,
            "properties": fc.get("properties") or {}}
