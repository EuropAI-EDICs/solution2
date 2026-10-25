"""Parsers over gecachte DSO Presenteren-annotaties (IMOW/TPOD-laag).

De Presenteren-API levert per regeling de IMOW-annotaties terug die op een
geometrie van toepassing zijn: regelteksten (OP-objecten, verankerd aan de
STOP-tekst via wId), juridische regels (regelsVoorIedereen / instructieregels),
activiteiten (met de functionele structuur via bovenliggendeActiviteitRef),
locaties (met geometrieIdentificatie in de GIO), gebiedsaanwijzingen en
geselecteerdeLocatieRefs (de locaties die het bevraagde punt daadwerkelijk
bevatten). Dit zijn exact de objecttypen uit IMOW 3.0.1 (def-im-imow) en het
toepassingsprofiel TPOD omgevingsplan/omgevingsverordening.

Alle functies zijn pure functies over de payload: geen I/O, geen netwerk,
deterministisch. Zie docs/POC_TPOD_IMOW_KANSEN.md voor de kansenkaart.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

#: Segmenten zoals ze in LVBB-wIds voorkomen: gm0772_<hash>__chp_5__subchp_5.4
#: __subsec_5.4.2__art_5.117__para_1 (para is optioneel; ook subchp/subsec
#: kunnen ontbreken).
_SEGMENT_RE = re.compile(r"^(chp|subchp|subsec|art|para)_(.+)$")

_REGELTYPES = (
    ("regelsVoorIedereen", "regelVoorIedereen"),
    ("instructieregels", "instructieregel"),
)


def parse_wid(wid: str) -> dict[str, Any]:
    """Splits een LVBB-wId in locator-onderdelen (STOP/IMOW-tekstanker).

    Het prefix (voor de eerste ``__``) is de bronhouder + document-hash;
    de segmenten erna lopen van hoofdstuk naar lid. Onbekende segmenten
    worden bewust bewaard in ``onbekend`` in plaats van stil weggegooid.
    """
    onderdelen: dict[str, Any] = {
        "prefix": "",
        "hoofdstuk": None,
        "afdeling": None,
        "paragraaf": None,
        "artikel": None,
        "lid": None,
        "onbekend": [],
    }
    if not wid:
        return onderdelen
    delen = wid.split("__")
    onderdelen["prefix"] = delen[0]
    for seg in delen[1:]:
        m = _SEGMENT_RE.match(seg)
        if m is None:
            onderdelen["onbekend"].append(seg)
            continue
        soort, waarde = m.group(1), m.group(2)
        if soort == "chp":
            onderdelen["hoofdstuk"] = waarde
        elif soort == "subchp":
            onderdelen["afdeling"] = waarde
        elif soort == "subsec":
            onderdelen["paragraaf"] = waarde
        elif soort == "art":
            onderdelen["artikel"] = waarde
        elif soort == "para":
            onderdelen["lid"] = waarde
    return onderdelen


def parse_regelteksten(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Regelteksten (OP-objecten) met hun locator, in payload-volgorde."""
    uit: list[dict[str, Any]] = []
    for rt in payload.get("regelteksten") or []:
        parts = parse_wid(rt.get("wId") or "")
        uit.append(
            {
                "identificatie": rt.get("identificatie"),
                "wId": rt.get("wId"),
                "hoofdstuk": parts["hoofdstuk"],
                "afdeling": parts["afdeling"],
                "paragraaf": parts["paragraaf"],
                "artikel": parts["artikel"],
                "lid": parts["lid"],
                "onbekend": parts["onbekend"],
            }
        )
    return uit


def parse_regels(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Juridische regels (OW-objecten) opgelost naar artikel, locaties en activiteiten.

    Elke regel verwijst via regeltekstRef naar zijn tekstanker (wId →
    artikel/lid), via locatieRefs naar locaties (waaronder het ambtsgebied),
    via gebiedsaanwijzingRefs naar gebiedsaanwijzingen en via
    activiteitLocatieaanduidingen naar activiteiten. Regels waarvan de
    regeltekstRef niet in de payload zit worden teruggegeven met
    ``artikel: None`` (en tellen in de index onder ``regelsZonderTekstInPayload``).
    """
    tekst_by_id = {
        rt.get("identificatie"): rt for rt in (payload.get("regelteksten") or [])
    }
    uit: list[dict[str, Any]] = []
    for sleutel, soort in _REGELTYPES:
        for regel in payload.get(sleutel) or []:
            rt = tekst_by_id.get(regel.get("regeltekstRef"))
            parts = parse_wid(rt.get("wId") or "") if rt else parse_wid("")
            ala = regel.get("activiteitLocatieaanduidingen") or []
            uit.append(
                {
                    "soort": soort,
                    "identificatie": regel.get("identificatie"),
                    "idealisatie": (regel.get("idealisatie") or {}).get("waarde"),
                    "regeltekstRef": regel.get("regeltekstRef"),
                    "tekstInPayload": rt is not None,
                    "artikel": parts["artikel"],
                    "lid": parts["lid"],
                    "locatieRefs": list(regel.get("locatieRefs") or []),
                    "gebiedsaanwijzingRefs": list(
                        regel.get("gebiedsaanwijzingRefs") or []
                    ),
                    "activiteitRefs": sorted(
                        {
                            item.get("activiteitRef")
                            for item in ala
                            if item.get("activiteitRef")
                        }
                    ),
                }
            )
    return uit


def activiteit_structuur(payload: dict[str, Any]) -> dict[str, Any]:
    """De functionele structuur van de activiteiten (IMOW: bovenliggendeActiviteit).

    In de praktijk (Eindhoven én Utrecht, PRE v8) is de enige root de landelijke
    tophaak ``nl.imow-mnre1034.activiteit.ActiviteitGevolgenFysiekeLeefomg`` — de
    lokale tophaak ("… gereguleerd in het omgevingsplan/-verordening") hangt er
    als kind onder. Daarom staan roots en "gereguleerd"-activiteiten
    (tophaakKandidaten) los gerapporteerd. Een ouder die niet in de payload zit
    is een activiteit van een andere aanbieder en wordt apart geteld.
    """
    activiteiten = payload.get("activiteiten") or []
    ids = {a.get("identificatie") for a in activiteiten}
    kinderen: dict[Any, list[Any]] = {}
    roots: list[dict[str, Any]] = []
    externe_ouder = 0
    groepen: Counter[str] = Counter()
    diepte: dict[Any, int] = {}

    by_id = {a.get("identificatie"): a for a in activiteiten}

    def _diepte(act: dict[str, Any]) -> int:
        ident = act.get("identificatie")
        if ident in diepte:
            return diepte[ident]
        ouder = act.get("bovenliggendeActiviteitRef")
        if not ouder:
            d = 0
        elif ouder in by_id:
            d = 1 + _diepte(by_id[ouder])
        else:  # externe ouder: diepte voorbij de payload is onbekend
            d = 1
        diepte[ident] = d
        return d

    for a in activiteiten:
        groep = a.get("groep") or {}
        if groep.get("waarde"):
            groepen[groep["waarde"]] += 1
        ouder = a.get("bovenliggendeActiviteitRef")
        if not ouder:
            roots.append(a)
        elif ouder in ids:
            kinderen.setdefault(ouder, []).append(a.get("identificatie"))
        else:
            externe_ouder += 1

    max_diepte = max((_diepte(a) for a in activiteiten), default=0)
    return {
        "totaal": len(activiteiten),
        "roots": [
            {"identificatie": a.get("identificatie"), "naam": a.get("naam")}
            for a in roots
        ],
        "tophaakKandidaten": [
            {"identificatie": a.get("identificatie"), "naam": a.get("naam")}
            for a in activiteiten
            if "gereguleerd" in (a.get("naam") or "")
        ],
        "metBovenliggende": len(activiteiten) - len(roots),
        "metExterneBovenliggende": externe_ouder,
        "maxDiepte": max_diepte,
        "groepen": dict(sorted(groepen.items())),
    }


def geo_feiten(payload: dict[str, Any]) -> dict[str, Any]:
    """Locaties en gebiedsaanwijzingen rond het bevraagde punt (K1: werkingsgebieden).

    ``geselecteerdeLocatieRefs`` zijn de locaties die het punt daadwerkelijk
    bevatten — dat is een door de DSO geleverd punt-in-gebied-feit. Locaties
    dragen naast hun IMOW-identificatie een ``geometrieIdentificatie`` die naar
    de GIO-geometrie (GML) verwijst; die geometrie zelf zit niet in het
    Presenteren-antwoord en vraagt de Omgevingsdocumenten-downloaden-API.
    """
    geselecteerd = list(payload.get("geselecteerdeLocatieRefs") or [])
    geselecteerd_set = set(geselecteerd)
    locaties: list[dict[str, Any]] = []
    for loc in payload.get("locaties") or []:
        locaties.append(
            {
                "identificatie": loc.get("identificatie"),
                "locatieType": loc.get("locatieType"),
                "noemer": loc.get("noemer"),
                "geometrieIdentificatie": loc.get("geometrieIdentificatie"),
                "geselecteerdOpPunt": loc.get("identificatie") in geselecteerd_set,
            }
        )
    gebieden: list[dict[str, Any]] = []
    for ga in payload.get("gebiedsaanwijzingen") or []:
        gebieden.append(
            {
                "identificatie": ga.get("identificatie"),
                "naam": ga.get("naam"),
                "groep": (ga.get("groep") or {}).get("waarde"),
                "type": (ga.get("type") or {}).get("waarde"),
            }
        )
    return {
        "geselecteerdeLocatieRefs": geselecteerd,
        "ambtsgebiedRef": next(
            (ref for ref in geselecteerd if ".ambtsgebied." in ref), None
        ),
        "locaties": sorted(locaties, key=lambda l: l["identificatie"] or ""),
        "aantalLocatiesMetGeometrie": sum(
            1 for l in locaties if l.get("geometrieIdentificatie")
        ),
        "gebiedsaanwijzingen": sorted(
            gebieden, key=lambda g: g["identificatie"] or ""
        ),
    }


def pons_annotaties(payload: dict[str, Any]) -> dict[str, Any]:
    """Pons (alleen omgevingsplan): waar oude bestemmingsplannen niet meer gelden.

    De Presenteren-annotaties-op-vraag-punt bevat (oktober 2026, v8, PRE) geen
    pons-objecten: die leven in de OW-aanlevering en zijn op te vragen via de
    Omgevingsdocumenten-downloaden-API (key-gated, zie
    docs/POC_TPOD_IMOW_KANSEN.md, kans 2). Zit de sleutel er wél in (toekomstige
    API-versie), dan worden de objecten 1-op-1 meegenomen — nooit geïnterpreteerd.
    """
    pons = payload.get("pons")
    if not pons:
        return {"beschikbaar": False, "aantal": 0, "objecten": []}
    return {
        "beschikbaar": True,
        "aantal": len(pons),
        "objecten": sorted(pons, key=lambda p: p.get("identificatie") or ""),
    }


_DOCUMENTSTRUCTUUR_TYPE_NIVEAU = {
    "LICHAAM": 0,
    "HOOFDSTUK": 1,
    "AFDELING": 2,
    "PARAGRAAF": 3,
    "SUBPARAGRAAF": 4,
    "SUBSUBPARAGRAAF": 5,
    "ARTIKEL": 6,
    "LID": 7,
}


def parse_documentstructuur(payload: dict[str, Any]) -> dict[str, Any]:
    """Hele-instrument wId-boom uit het Presenteren-documentstructuur-endpoint.

    Dit is de anchoring los van het bevraagde punt (kans 3): elk documentComponent
    draagt zijn LVBB-wId als identificatie. Aggregaten per componenttype plus
    het diepteprofiel; de boom zelf blijft in de cache (te groot voor de index).
    """
    types: Counter[str] = Counter()

    def walk(component: dict[str, Any]) -> int:
        soort = component.get("type")
        if soort:
            types[soort] += 1
        kinderen = (component.get("_embedded") or {}).get("documentComponenten") or []
        diepte = max((walk(k) for k in kinderen), default=0)
        return diepte + 1 if kinderen else 0

    root_diepte = 0
    for c in (payload.get("_embedded") or {}).get("documentComponenten") or []:
        root_diepte = max(root_diepte, walk(c))
    return {
        "componenten": dict(sorted(types.items())),
        "artikelen": types.get("ARTIKEL", 0),
        "leden": types.get("LID", 0),
        "hoofdstukken": types.get("HOOFDSTUK", 0),
        "maxDiepte": root_diepte,
    }
