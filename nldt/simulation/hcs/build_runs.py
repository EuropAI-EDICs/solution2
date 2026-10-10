#!/usr/bin/env python3
"""Genereert HCS-runs en demopagina's uit fixtures (patroon regelrecht/build_runs.py).

Deterministisch: zelfde --stamp levert byte-identieke uitvoer. Gevalideerd tegen
nldt/schemas/hcs-run.schema.json. Alleen-lezen ten opzichte van de fixtures en recipes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[2]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))

from services.common.schema import validate_instance  # noqa: E402
from services.process_adapter.poc_handlers import (  # noqa: E402
    execute_hcs_life_event_run,
    execute_hcs_recipe_run,
    localize,
)

HCS_ROOT = NLDT_ROOT / "simulation" / "hcs"
LIFE_FIXTURES = HCS_ROOT / "fixtures" / "life-events"
RUNS_DIR = HCS_ROOT / "runs"


def build_runs(stamp: str, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(LIFE_FIXTURES.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        for persona in fixture["personas"]:
            out = execute_hcs_life_event_run(
                {"recipeId": fixture["recipeId"], "persona": persona["id"], "mode": "replay"})
            run = out["run"]
            run["generatedAt"] = stamp_iso(stamp)
            run["runId"] = f"{fixture['recipeId']}-{persona['id']}-{stamp}"
            validate_instance(run, "hcs-run.schema.json")
            target = outdir / f"{fixture['recipeId']}_{persona['id']}.json"
            target.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8")
            written.append(target)
            try:
                shown = target.relative_to(NLDT_ROOT)
            except ValueError:  # outdir buiten NLDT_ROOT (bv. tmp_path in tests)
                shown = target
            print(f"OK run {shown}")
    return written


def stamp_iso(stamp: str) -> str:
    """20261009T000000Z -> 2026-10-09T00:00:00Z ( anders ongewijzigd)."""
    if len(stamp) == 16 and stamp.endswith("Z") and stamp[8] == "T":
        return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"
    return stamp


LANGS = {"nl": NLDT_ROOT / "simulation" / "hcs-key-demo.html",
         "en": NLDT_ROOT / "simulation" / "hcs-key-demo-en.html"}

I18N = {
    "nl": {
        "eyecatcher": "Human-Centred Services · EDIC recipe PoC · The Key",
        "title": "Ik ga verhuizen — alles in één keer geregeld",
        "lede": "Zo werkt het: vijf stappen die jij en de gemeente samen doorlopen. Je ziet steeds wat er met je gegevens gebeurt, wie ze mag zien en wanneer er een mens meekijkt.",
        "foot": "Deze aanpak is getest voordat die live ging · build {stamp} · AI stelt voor · pijplijn beslist · mens beslist",
        "actor": "Wie regelt dit", "consent": "Toestemming",
        "actorNames": {"agent": "de computer (AI)", "mens": "een medewerker", "partij": "de organisatie waar je iets vraagt"},
        "consentNames": {"n.v.t.": "nu niet nodig", "gevraagd": "aan jou gevraagd", "gegeven": "van jou gekregen", "geweigerd": "geweigerd"},
        "handover": "Wanneer een mens overneemt", "sources": "Waar deze informatie vandaan komt",
        "testbank": "Wat we hebben getest voordat dit live ging",
        "tbOk": "getest en goedgekeurd", "tbCheck": "wordt nu getest", "tbFail": "niet goedgekeurd",
        "axisNames": {"accuracy": "nauwkeurig", "plain language": "gewone taal", "once-only": "één keer vragen",
                      "explainability": "uitlegbaar", "human handover": "mens neemt over", "bias": "vooringenomenheid",
                      "AI Act risk class": "AI-wet risicoklasse"},
        "kpiPanel": "Wat we willen bereiken — gemeten vanaf dag één",
        "kpiSub": "Elke recipe meet of het echt beter wordt voor inwoners.",
        "kpi": "Wat we meten", "kpiType": "Soort",
        "dataSource": "Waar de cijfers vandaan komen", "scenes": "De andere verhalen in deze demo",
        "learning": "Wat we ervan leren",
        "lsWhy": "Waarom", "lsChange": "Wat gaan we doen", "lsWho": "Wie beslist",
        "lsNone": "Hier zijn we nog niets nieuws tegengekomen.",
    },
    "en": {
        "eyecatcher": "Human-Centred Services · EDIC recipe PoC · The Key",
        "title": "I want to move home — everything arranged in one go",
        "lede": "This is how it works: five steps that you and the municipality go through together. You can always see what happens to your details, who may see them, and when a person steps in.",
        "foot": "This approach was tested before it went live · build {stamp} · AI proposes · pipeline decides · human decides",
        "actor": "Who arranges this", "consent": "Permission",
        "actorNames": {"agent": "the computer (AI)", "mens": "a caseworker", "partij": "the organisation you ask something of"},
        "consentNames": {"n.v.t.": "not needed here", "gevraagd": "asked of you", "gegeven": "given by you", "geweigerd": "refused"},
        "handover": "When a person takes over", "sources": "Where this information comes from",
        "testbank": "What we tested before this went live",
        "tbOk": "tested and approved", "tbCheck": "being tested now", "tbFail": "not approved",
        "axisNames": {"accuracy": "accuracy", "plain language": "plain language", "once-only": "once-only",
                      "explainability": "explainability", "human handover": "human handover", "bias": "bias",
                      "AI Act risk class": "AI Act risk class"},
        "kpiPanel": "What we want to achieve — measured from day one",
        "kpiSub": "Every recipe measures whether life actually gets better for residents.",
        "kpi": "What we measure", "kpiType": "Kind",
        "dataSource": "Where the numbers come from", "scenes": "The other stories in this demo",
        "learning": "What we learn from this",
        "lsWhy": "Why", "lsChange": "What we will do", "lsWho": "Who decides",
        "lsNone": "Nothing new to report here yet.",
    },
}

SCENES = [
    {"chip": {"nl": "THK-02 · vóór en ná de geboorte", "en": "THK-02 · before and after the birth"},
     "title": {"nl": "Ik krijg een kind", "en": "I'm having a baby"},
     "body": {"nl": "We beginnen al vóór de geboorte met regelen. De geboorte meld je binnen 5 dagen, gewoon online. Kinderbijslag en toeslagen komen vanzelf — maar alleen als jij dat goed vindt. Bij een bijzondere situatie (zoals erkenning met een ouder in het buitenland) neemt een medewerker het over.",
              "en": "We start arranging things before the birth. You register the birth within 5 days, simply online. Child benefit and allowances arrive automatically — but only if you agree. In a special situation (such as recognition with a parent abroad) a caseworker takes over."}},
    {"chip": {"nl": "THK-24 · bouwen en wonen", "en": "THK-24 · building and living"},
     "title": {"nl": "Ik wil bouwen of renoveren", "en": "I want to build or renovate"},
     "body": {"nl": "Je beschrijft je bouwplan in gewone woorden en ziet vooraf of je een vergunning nodig hebt. Je levert één keer alles aan, compleet. Een vergunningverlener — een mens — beoordeelt je aanvraag en beslist binnen 8 weken. Daarna wijzen wij je de volgende stappen.",
              "en": "You describe your building plan in plain words and see up front whether you need a permit. You submit everything once, complete. A permitting officer — a person — assesses your application and decides within 8 weeks. Afterwards, we point out your next steps."}},
    {"chip": {"nl": "getest met lastige situaties", "en": "tested with tricky situations"},
     "title": {"nl": "Eerst getest, dan pas live", "en": "Tested first, live later"},
     "body": {"nl": "Iedereen moet mee kunnen doen. Daarom testen we met mensen die moeite hebben met lezen, liever een andere taal spreken of schulden hebben. Werkt het voor hen niet goed genoeg, dan gaat het niet live.",
              "en": "Everyone must be able to take part. That is why we test with people who find reading hard, prefer another language, or have debts. If it does not work well enough for them, it does not go live."}},
]


def _fixture_service(fixture_path: Path) -> dict:
    recipe = json.loads((NLDT_ROOT / "recipes" / f"{fixture_path.stem}.json").read_text(encoding="utf-8"))
    return recipe["service"]


def _page_bundle(stamp: str, lang: str) -> tuple[dict, dict]:
    """Runs (weergaveteksten in `lang`) + persona-labels in `lang` voor één pagina.

    Service-KPI's blijven canoniek; runs worden schema-gevalideerd.
    """
    runs: dict = {}
    fixtures: dict = {}
    for path in sorted(LIFE_FIXTURES.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        fixtures[fx["recipeId"]] = {
            "personas": [{"id": p["id"], "label": localize(p["label"], lang), "edge": p["edge"]}
                         for p in fx["personas"]],
            "service": _fixture_service(path),
        }
        runs[fx["recipeId"]] = {}
        for persona in fx["personas"]:
            out = execute_hcs_life_event_run(
                {"recipeId": fx["recipeId"], "persona": persona["id"], "mode": "replay",
                 "lang": lang})
            run = out["run"]
            run["generatedAt"] = stamp_iso(stamp)
            run["runId"] = f"{fx['recipeId']}-{persona['id']}-{stamp}"
            validate_instance(run, "hcs-run.schema.json")
            runs[fx["recipeId"]][persona["id"]] = run
    return runs, fixtures


def build_pages(stamp: str) -> None:
    template = (HCS_ROOT / "key-demo.template.html").read_text(encoding="utf-8")
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text(encoding="utf-8"))
    payloads: dict[str, str] = {}
    for lang in LANGS:
        runs, fixtures = _page_bundle(stamp, lang)
        # Scènes worden per taal gelokaliseerd (zelfs patroon als persona-labels
        # en runs), zodat de EN-pagina geen Nederlandse scèneteksten bevat.
        scenes = [{"chip": localize(sc["chip"], lang),
                   "title": localize(sc["title"], lang),
                   "body": localize(sc["body"], lang)} for sc in SCENES]
        data = {"runs": runs, "fixtures": fixtures, "common": common,
                "i18n": I18N, "scenes": scenes,
                "selftestVerdicts": {r: {"bias": True, "AI Act risk class": True}
                                      for r in runs}}
        payloads[lang] = json.dumps(data, ensure_ascii=False)
    for lang, target in LANGS.items():
        html = (template
                .replace("__HCS_DATA__", payloads[lang])
                .replace("__LANG__", json.dumps(lang))
                .replace("__BUILD_STAMP__", stamp)
                .replace('<html lang="nl">', f'<html lang="{lang}">'))
        target.write_text(html, encoding="utf-8")
        print(f"OK page {target.relative_to(NLDT_ROOT)}")


DISH_DEFS = {
    "uam": {"file": NLDT_ROOT / "simulation" / "hcs-uam-demo.html",
            "file-en": NLDT_ROOT / "simulation" / "hcs-uam-demo-en.html",
            "recipes": ["uam-01-medical-logistics", "uam-09-geofencing-zones"],
            "viz": {"uam-01-medical-logistics": {"kind": "map"},
                    "uam-09-geofencing-zones": {"kind": "map"}}},
    "grn": {"file": NLDT_ROOT / "simulation" / "hcs-grn-demo.html",
            "file-en": NLDT_ROOT / "simulation" / "hcs-grn-demo-en.html",
            "recipes": ["grn-01-canopy-measure", "grn-03-300m-gaps"],
            "viz": {"grn-01-canopy-measure": {"kind": "canopy"},
                    "grn-03-300m-gaps": {"kind": "canopy"}}},
    "cir": {"file": NLDT_ROOT / "simulation" / "hcs-cir-demo.html",
            "file-en": NLDT_ROOT / "simulation" / "hcs-cir-demo-en.html",
            "recipes": ["cir-04-shared-energy", "cir-01-circular-condition"],
            "viz": {"cir-04-shared-energy": {"kind": "series"},
                    "cir-01-circular-condition": {"kind": "series"}}},
    "min": {"file": NLDT_ROOT / "simulation" / "hcs-min-demo.html",
            "file-en": NLDT_ROOT / "simulation" / "hcs-min-demo-en.html",
            "recipes": ["min-01-proximity-analysis", "min-04-hub-network"],
            "viz": {"min-01-proximity-analysis": {"kind": "tiers"},
                    "min-04-hub-network": {"kind": "tiers"}}},
}

_DISH_I18N_UAM_NL = {
    "eyecatcher": "Human-Centred Services · dish: Urban Air Mobility", "title": "De lucht in — zonder de stad te verstoppen",
    "lede": "Twee recipes uit deze dish, gedraaid als deterministische replay: wat gebeurt er, wie bepaalt het, en waar komt de informatie vandaan.",
    "foot": "HCS fase 2 · build {stamp} · runs gevalideerd tegen hcs-run.schema.json · doctrine: AI stelt voor · pijplijn beslist · mens beslist",
    "testbank": "Wat we hebben getest voordat dit live ging", "tbOk": "go", "tbCheck": "nog niet getoetst", "tbFail": "geen go",
    "kpiPanel": "Wat we willen bereiken — gemeten vanaf dag één", "kpiSub": "Elke recipe meet of het echt beter wordt.",
    "kpi": "KPI", "kpiType": "Type", "dataSource": "Bron", "siblings": "De andere recipes in deze dish",
    "actor": "Wie handelt", "consent": "Toestemming", "handover": "Een mens neemt over", "sources": "Waar deze informatie vandaan komt",
    "actorNames": {"agent": "het systeem (onder toezicht)", "mens": "een mens", "partij": "de betrokken organisatie"},
    "consentNames": {"n.v.t.": "niet nodig", "gevraagd": "gevraagd", "gegeven": "gegeven", "geweigerd": "geweigerd"},
    "vizTarget": "doel:",
    "axisNames": {"accuracy": "nauwkeurig", "plain language": "gewone taal", "once-only": "één keer vragen",
                   "explainability": "uitlegbaar", "human handover": "mens neemt over",
                   "bias": "vooringenomenheid", "AI Act risk class": "AI-wet risicoklasse"}}
_DISH_I18N_UAM_EN = {
    "eyecatcher": "Human-Centred Services · dish: Urban Air Mobility", "title": "Into the air — without clogging the city",
    "lede": "Two recipes from this dish, run as a deterministic replay: what happens, who decides, and where the information comes from.",
    "foot": "HCS phase 2 · build {stamp} · runs validated against hcs-run.schema.json · doctrine: AI proposes · pipeline decides · human decides",
    "testbank": "What we tested before this went live", "tbOk": "go", "tbCheck": "not yet tested", "tbFail": "no go",
    "kpiPanel": "What we aim to achieve — measured from day one", "kpiSub": "Every recipe measures whether life actually gets better.",
    "kpi": "KPI", "kpiType": "Type", "dataSource": "Source", "siblings": "Other recipes in this dish",
    "actor": "Who acts", "consent": "Consent", "handover": "A human takes over", "sources": "Where this information comes from",
    "actorNames": {"agent": "the system (under supervision)", "mens": "a human", "partij": "the organisation involved"},
    "consentNames": {"n.v.t.": "not needed", "gevraagd": "asked", "gegeven": "given", "geweigerd": "refused"},
    "vizTarget": "target:",
    "axisNames": {"accuracy": "accuracy", "plain language": "plain language", "once-only": "ask only once",
                   "explainability": "explainable", "human handover": "human takes over",
                   "bias": "bias", "AI Act risk class": "AI Act risk class"}}

DISH_I18N = {
    "uam": {"nl": _DISH_I18N_UAM_NL, "en": _DISH_I18N_UAM_EN},
    "grn": {"nl": dict(_DISH_I18N_UAM_NL, title="Groen meten, groen doen",
                       lede="Twee 3-30-300-recipes: hoeveel bladerdak heeft je wijk, en wie woont verder dan 300 meter van echt goed groen?",
                       eyecatcher="Human-Centred Services · dish: 3-30-300"),
            "en": dict(_DISH_I18N_UAM_EN, title="Measure the green, then grow it",
                       lede="Two 3-30-300 recipes: how much canopy does your district have, and who lives further than 300 metres from truly good green?",
                       eyecatcher="Human-Centred Services · dish: 3-30-300")},
    "cir": {"nl": dict(_DISH_I18N_UAM_NL, title="Delen is het nieuwe bezitten",
                       lede="Twee circular-recipes: gedeelde energie in de buurt en circulariteit als harde eis bij nieuwbouw.",
                       eyecatcher="Human-Centred Services · dish: Circular neighborhoods"),
            "en": dict(_DISH_I18N_UAM_EN, title="Sharing is the new owning",
                       lede="Two circular recipes: shared energy in the neighbourhood and circularity as a hard requirement for new build.",
                       eyecatcher="Human-Centred Services · dish: Circular neighborhoods")},
    "min": {"nl": dict(_DISH_I18N_UAM_NL, title="Alles wat je dagelijks nodig hebt, dichtbij",
                       lede="Twee 15-minute-city-recipes: welke wijk ligt buiten bereik van voorzieningen, en waar komen de hubs?",
                       eyecatcher="Human-Centred Services · dish: 15-minute city"),
            "en": dict(_DISH_I18N_UAM_EN, title="Everything you need daily, close by",
                       lede="Two 15-minute-city recipes: which district falls outside reach of amenities, and where do the hubs go?",
                       eyecatcher="Human-Centred Services · dish: 15-minute city")},
}

# DISH_DEFS-sleutels ("uam") → dish-id's uit het recipe-schema ("urban-air-mobility"),
# de sleutels van menu-data.json.
MENU_DISH = {"uam": "urban-air-mobility", "grn": "3-30-300",
             "cir": "circular-neighborhoods", "min": "15-minute-city"}

# Viz-data per recipe (zones/routes, canopy-cellen, tijdreeks, hub-tiers); de
# exacte inhoud registreren de dish-taken (Tasks 3–6) in deze dict.
_VIZ_DATA: dict[str, dict] = {}

# Task 3 — Urban Air Mobility (display-only; deterministisch en vast).
UAM01_VIZ = {
    "kind": "map",
    "note": {"nl": "Schema van de situatie — geen echte kaart: corridors (oranje/blauw) en beschermde zones (rood gestippeld).",
             "en": "Schematic view — not a real map: corridors (orange/blue) and protected zones (red dashed)."},
    "data": {"zones": [{"x": 420, "y": 90, "r": 55}, {"x": 180, "y": 220, "r": 40}],
             "routes": {"routine": [{"points": [[60, 260], [220, 180], [380, 110], [560, 60]]}],
                          "spoed": [{"points": [[60, 260], [200, 230], [330, 170], [560, 60]]}]},
             "labels": [{"x": 470, "y": 95, "text": "no-fly"},
                         {"x": 70, "y": 250, "text": {"nl": "ziekenhuis", "en": "hospital"}},
                         {"x": 520, "y": 50, "text": {"nl": "lab", "en": "lab"}}]}}

UAM09_VIZ = {
    "kind": "map",
    "note": {"nl": "Schema: de nieuwe zone (blauw gevuld) tegen corridors (oranje) en bestaande zones (rood gestippeld).",
             "en": "Schematic: the new zone (blue) against corridors (orange) and existing zones (red dashed)."},
    "data": {"zones": [{"x": 150, "y": 100, "r": 45}],
             "routes": {"ziekenhuis": [{"points": [[320, 270], [320, 160], [320, 60]]}],
                          "evenement": [{"points": [[320, 270], [240, 190], [180, 130]]}]},
             "labels": [{"x": 130, "y": 105, "text": "no-fly"},
                         {"x": 300, "y": 50, "text": {"nl": "corridor", "en": "corridor"}}]}}

_VIZ_DATA["uam-01-medical-logistics"] = UAM01_VIZ
_VIZ_DATA["uam-09-geofencing-zones"] = UAM09_VIZ


def _canopy_cells(covers: list[int]) -> list[dict]:
    """4×3-raster op vaste posities (x = 40 + col*150, y = 30 + row*85, cel 70)."""
    return [{"x": 40 + (i % 4) * 150, "y": 30 + (i // 4) * 85, "cover": c}
            for i, c in enumerate(covers)]


# Task 4 — 3-30-300 (display-only; deterministisch en vast).
GRN01_VIZ = {
    "kind": "canopy",
    "note": {"nl": "Schema per wijkblok: mint = boven de 30% bladerdak, oranje = eronder. Geen echte kaart.",
             "en": "Schematic per district block: mint = above 30% canopy, orange = below. Not a real map."},
    "data": {"cell": 70,
             "cells": {"wijk-noord": _canopy_cells([21, 24, 19, 23, 25, 18, 22, 27, 20, 24, 19, 26]),
                        "wijk-zuid": _canopy_cells([38, 44, 41, 47, 33, 42, 36, 48, 39, 45, 40, 35])}}}

GRN03_VIZ = {
    "kind": "canopy",
    "note": {"nl": "Percentage bewoners binnen 300 meter goed groen per wijkblok (schema).",
             "en": "Share of residents within 300 metres of quality green per district block (schematic)."},
    "data": {"cell": 70,
             "cells": {"binnen-norm": _canopy_cells([88, 92, 85, 90, 79, 94, 87, 91, 83, 89, 95, 86]),
                        "groeidesert": _canopy_cells([61, 58, 72, 64, 47, 55, 51, 62, 57, 44, 66, 53])}}}

_VIZ_DATA["grn-01-canopy-measure"] = GRN01_VIZ
_VIZ_DATA["grn-03-300m-gaps"] = GRN03_VIZ


# Task 5 — Circular neighborhoods (display-only; deterministisch en vast).
CIR04_VIZ = {
    "kind": "series",
    "note": {"nl": "Lokale opwek als % van het verbruik (schema) — de oranje stippellijn is het doel.",
             "en": "Local generation as % of usage (schematic) — the orange dashed line is the target."},
    "data": {"series": {
        "overproductie": {"target": 50, "points": [{"label": {"nl": "jan", "en": "Jan"}, "value": 45}, {"label": {"nl": "feb", "en": "Feb"}, "value": 52},
                                                     {"label": {"nl": "mrt", "en": "Mar"}, "value": 60}, {"label": {"nl": "apr", "en": "Apr"}, "value": 68},
                                                     {"label": {"nl": "mei", "en": "May"}, "value": 62}, {"label": {"nl": "jun", "en": "Jun"}, "value": 55}]},
        "piek": {"target": 30, "points": [{"label": {"nl": "jan", "en": "Jan"}, "value": 22}, {"label": {"nl": "feb", "en": "Feb"}, "value": 25},
                                            {"label": {"nl": "mrt", "en": "Mar"}, "value": 30}, {"label": {"nl": "apr", "en": "Apr"}, "value": 28},
                                            {"label": {"nl": "mei", "en": "May"}, "value": 26}, {"label": {"nl": "jun", "en": "Jun"}, "value": 24}]}}}}

CIR01_VIZ = {
    "kind": "series",
    "note": {"nl": "Circulair/hergebruikt materiaal als % van het bouwmateriaal (schema) per projectfase.",
             "en": "Circular/reused material as % of build material (schematic) per project phase."},
    "data": {"series": {
        "tender": {"target": 50, "points": [{"label": {"nl": "start", "en": "start"}, "value": 20}, {"label": {"nl": "ontwerp", "en": "design"}, "value": 35},
                                              {"label": {"nl": "bouw", "en": "build"}, "value": 55}, {"label": {"nl": "oplevering", "en": "completion"}, "value": 68}]}}}}

_VIZ_DATA["cir-04-shared-energy"] = CIR04_VIZ
_VIZ_DATA["cir-01-circular-condition"] = CIR01_VIZ


# Task 6 — 15-minute city (display-only; deterministisch en vast).
MIN01_VIZ = {
    "kind": "tiers",
    "note": {"nl": "Bereikte voorzieningen per ring (schema) — de randwijk haalt de buitenringen niet.",
             "en": "Reached amenities per ring (schematic) — the edge district misses the outer rings."},
    "data": {"tiers": [
        {"name": {"nl": "winkels", "en": "shops"}, "r": 90, "live": 14, "plan": 15},
        {"name": {"nl": "zorg", "en": "care"}, "r": 130, "live": 9, "plan": 10},
        {"name": {"nl": "onderwijs", "en": "education"}, "r": 170, "live": 6, "plan": 8},
        {"name": {"nl": "groen", "en": "green"}, "r": 210, "live": 4, "plan": 6}]}}

MIN04_VIZ = {
    "kind": "tiers",
    "note": {"nl": "De hubladder: live versus gepland per niveau (micro → wijk → stadsdeel → stad).",
             "en": "The hub ladder: live versus planned per tier (micro → neighbourhood → district → city)."},
    "data": {"tiers": [
        {"name": {"nl": "micro", "en": "micro"}, "r": 80, "live": 11, "plan": 12},
        {"name": {"nl": "wijk", "en": "neighbourhood"}, "r": 125, "live": 4, "plan": 5},
        {"name": {"nl": "stadsdeel", "en": "district"}, "r": 165, "live": 2, "plan": 3},
        {"name": {"nl": "stad", "en": "city"}, "r": 205, "live": 1, "plan": 1}]}}

_VIZ_DATA["min-01-proximity-analysis"] = MIN01_VIZ
_VIZ_DATA["min-04-hub-network"] = MIN04_VIZ


def _viz_data(rid: str) -> dict:
    if rid not in _VIZ_DATA:
        raise KeyError(f"_viz_data: geen viz-data geregistreerd voor recipe {rid}")
    return _VIZ_DATA[rid]


def _localize_viz_data(data: dict, lang: str) -> dict:
    """Weergaveteksten in de viz-data (labels, tier-namen, serie-labels) naar `lang`."""
    out = json.loads(json.dumps(data))  # deep-copy zonder gedeelde referenties
    for label in out.get("labels", []):
        label["text"] = localize(label["text"], lang)
    for tier in out.get("tiers", []):
        tier["name"] = localize(tier["name"], lang)
    for series in out.get("series", {}).values():
        for point in series["points"]:
            point["label"] = localize(point["label"], lang)
    return out


def _menu_siblings(dish: str, lang: str = "nl") -> list[dict]:
    rows = json.loads((HCS_ROOT / "menu-data.json").read_text(encoding="utf-8"))[MENU_DISH[dish]]
    poc = set(DISH_DEFS[dish]["recipes"])
    title_col, kpi_col = (1, 3) if lang == "nl" else (6, 7)
    return [{"code": r[0], "title": r[title_col], "mode": r[2], "kpi": r[kpi_col], "lens": r[4],
             "poc": r[5] in poc} for r in rows]


def build_dish_pages(stamp: str) -> None:
    template = (HCS_ROOT / "dish-demo.template.html").read_text(encoding="utf-8")
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text(encoding="utf-8"))
    for dish, spec in DISH_DEFS.items():
        # SKIP bij een nog niet voltooide dish (fixtures/viz ontbreken), zodat
        # latere dishes eerdere successen niet maskeren.
        try:
            recipes_by_lang = {"nl": [], "en": []}
            for rid in spec["recipes"]:
                fx = json.loads((HCS_ROOT / "fixtures" / "city" / f"{rid}.json").read_text(encoding="utf-8"))
                recipe = json.loads((NLDT_ROOT / "recipes" / f"{rid}.json").read_text(encoding="utf-8"))
                vz = _viz_data(rid)
                for lang in ("nl", "en"):
                    runs, labels = [], []
                    for sc in fx["scenarios"]:
                        out = execute_hcs_recipe_run({"recipeId": rid, "scenario": sc["id"],
                                                      "mode": "replay", "lang": lang})
                        runs.append(out["run"])
                        labels.append(localize(sc["label"], lang))
                    recipes_by_lang[lang].append({
                        "id": rid, "runs": runs, "scenarioLabels": labels,
                        "service": recipe["service"],
                        # _viz_data levert {kind, note, data}; vlak dat af tot één niveau
                        # en lokaliseer de weergaveteksten (note, labels, tier-namen).
                        "viz": {"kind": vz["kind"], "note": localize(vz.get("note", ""), lang),
                                "data": _localize_viz_data(vz["data"], lang)},
                    })
            for lang in ("nl", "en"):
                data = {"dishId": dish, "recipes": recipes_by_lang[lang], "common": common,
                        "i18n": DISH_I18N[dish][lang], "siblings": _menu_siblings(dish, lang),
                        "selftestVerdicts": {dish: {"bias": True, "AI Act risk class": True}}}
                html = (template
                        .replace("__DISH_DATA__", json.dumps(data, ensure_ascii=False))
                        .replace("__DISH_ID__", json.dumps(dish))
                        .replace("__DISH_LANG__", json.dumps(lang))
                        .replace("__BUILD_STAMP__", stamp)
                        .replace('<html lang="nl">', f'<html lang="{lang}">'))
                target = spec["file"] if lang == "nl" else spec["file-en"]
                target.write_text(html, encoding="utf-8")
                print(f"OK dish {target.relative_to(NLDT_ROOT)} [{lang}]")
        except (KeyError, FileNotFoundError) as exc:
            print(f"SKIP dish {dish}: {exc}")
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", required=True, help="bouw-stamp, bv. 20261009T101500Z")
    parser.add_argument("--outdir", type=Path, default=RUNS_DIR)
    parser.add_argument("--only-runs", action="store_true",
                        help="alleen runs schrijven (geen pagina's; dish-demo's vallen daar ook onder)")
    args = parser.parse_args()
    build_runs(args.stamp, args.outdir)
    if not args.only_runs:
        build_pages(args.stamp)
        build_dish_pages(args.stamp)  # faalt netjes totdat de city-fixtures bestaan (Task 3+)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
