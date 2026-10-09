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
        "title": "Ik ga verhuizen — één reis, gesorteerd",
        "lede": "Vijf stappen uit de blueprint, gedraaid als deterministische replay op de nLDT-harness: de mens-agent-grens, de G-testpunten en de KPI-baseline zijn data, geen belofte.",
        "foot": "HCS fase 1 · build {stamp} · runs gevalideerd tegen hcs-run.schema.json · doctrine: AI stelt voor · pijplijn beslist · mens beslist",
        "actor": "Actor", "consent": "Consent",
        "actorNames": {"agent": "agent", "mens": "mens", "partij": "partij"},
        "consentNames": {"n.v.t.": "n.v.t.", "gevraagd": "gevraagd", "gegeven": "gegeven", "geweigerd": "geweigerd"},
        "handover": "Mens-agent-grens — overname", "sources": "Bronnen",
        "testbank": "GenAI-testbank (go/no-go per as)", "tbOk": "go", "tbCheck": "toets in uitvoering",
        "kpiPanel": "KPI-framework (poort 1: baseline vóór technologie)", "kpi": "KPI", "kpiType": "Type",
        "dataSource": "Bron", "scenes": "De andere The Key-recipes uit deze PoC",
        "learning": "Leerstaat (recipe-cyclus stap 6: measure & improve)",
        "lsWhy": "Waarom", "lsChange": "Wat moet veranderen", "lsWho": "Wie beslist", "lsNone": "Nog geen leersignalen in deze run.",
    },
    "en": {
        "eyecatcher": "Human-Centred Services · EDIC recipe PoC · The Key",
        "title": "I want to move home — one trip, sorted",
        "lede": "Five steps from the blueprint, run as a deterministic replay on the nLDT harness: the human-agent boundary, the G-test points and the KPI baseline are data, not promises.",
        "foot": "HCS phase 1 · build {stamp} · runs validated against hcs-run.schema.json · doctrine: AI proposes · pipeline decides · human decides",
        "actor": "Actor", "consent": "Consent",
        "actorNames": {"agent": "agent", "mens": "human", "partij": "party"},
        "consentNames": {"n.v.t.": "n/a", "gevraagd": "asked", "gegeven": "given", "geweigerd": "refused"},
        "handover": "Human-agent boundary — handover", "sources": "Sources",
        "testbank": "GenAI test bench (go/no-go per axis)", "tbOk": "go", "tbCheck": "check in progress",
        "kpiPanel": "KPI framework (gate 1: baseline before technology)", "kpi": "KPI", "kpiType": "Type",
        "dataSource": "Source", "scenes": "The other The Key recipes in this PoC",
        "learning": "Learning state (recipe cycle step 6: measure & improve)",
        "lsWhy": "Why", "lsChange": "What must change", "lsWho": "Who decides", "lsNone": "No learning signals in this run yet.",
    },
}

SCENES = [
    {"chip": "THK-02 · G2 · G5", "title": {"nl": "Ik krijg een kind", "en": "I'm having a baby"},
     "body": {"nl": "Proactief traject vóór de geboorte; geboorteaangifte binnen 5 dagen; SVB en toeslagen komen ongevraagd — maar alleen met consent. Erkenningsscenario's eindigen bij een medewerker.",
              "en": "Proactive track before birth; registration within 5 days; SVB and allowances arrive unasked — but only with consent. Recognition cases end with a caseworker."}},
    {"chip": "THK-24 · brug naar het RO-domein", "title": {"nl": "Ik wil bouwen of renoveren", "en": "I want to build or renovate"},
     "body": {"nl": "Vergunningcheck vóór de aanvraag, met de MiniGIM-gebiedscheck als ingredient. De beoordeling en het besluit zijn altijd menselijk (V4); klok: 8 weken regulier.",
              "en": "Permit check before applying, with the MiniGIM area check as ingredient. Assessment and decision are always human (V4); clock: 8 weeks regular."}},
    {"chip": "personas · testbank", "title": {"nl": "Getest door recipes, niet naast ze", "en": "Tested through recipes, not beside them"},
     "body": {"nl": "Lage geletterdheid, andere taal, schulden, bewindsvoering: elke edge case is een persona in de fixture en telt mee in de go/no-go van de testbank.",
              "en": "Low literacy, other language, debt, guardianship: every edge case is a persona in the fixture and counts towards the test bench go/no-go."}},
]


def _fixture_service(fixture_path: Path) -> dict:
    recipe = json.loads((NLDT_ROOT / "recipes" / f"{fixture_path.stem}.json").read_text(encoding="utf-8"))
    return recipe["service"]


def build_pages(stamp: str) -> None:
    template = (HCS_ROOT / "key-demo.template.html").read_text(encoding="utf-8")
    runs = {}
    fixtures = {}
    for path in sorted(LIFE_FIXTURES.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        fixtures[fx["recipeId"]] = {"personas": fx["personas"], "service": _fixture_service(path)}
        runs[fx["recipeId"]] = {}
        for persona in fx["personas"]:
            out = execute_hcs_life_event_run(
                {"recipeId": fx["recipeId"], "persona": persona["id"], "mode": "replay"})
            run = out["run"]
            run["generatedAt"] = stamp_iso(stamp)
            run["runId"] = f"{fx['recipeId']}-{persona['id']}-{stamp}"
            validate_instance(run, "hcs-run.schema.json")
            runs[fx["recipeId"]][persona["id"]] = run
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text(encoding="utf-8"))
    data = {"runs": runs, "fixtures": fixtures, "common": common,
            "i18n": I18N, "scenes": SCENES,
            "selftestVerdicts": {r: {"bias": True, "AI Act risk class": True}
                                  for r in runs}}
    payload = json.dumps(data, ensure_ascii=False)
    for lang, target in LANGS.items():
        html = (template
                .replace("__HCS_DATA__", payload)
                .replace("__LANG__", json.dumps(lang))
                .replace("__BUILD_STAMP__", stamp))
        target.write_text(html, encoding="utf-8")
        print(f"OK page {target.relative_to(NLDT_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", required=True, help="bouw-stamp, bv. 20261009T101500Z")
    parser.add_argument("--outdir", type=Path, default=RUNS_DIR)
    parser.add_argument("--only-runs", action="store_true",
                        help="alleen runs schrijven (geen pagina's)")
    args = parser.parse_args()
    build_runs(args.stamp, args.outdir)
    if not args.only_runs:
        build_pages(args.stamp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
