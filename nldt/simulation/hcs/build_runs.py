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
    {"chip": "THK-02 · vóór en ná de geboorte", "title": {"nl": "Ik krijg een kind", "en": "I'm having a baby"},
     "body": {"nl": "We beginnen al vóór de geboorte met regelen. De geboorte meld je binnen 5 dagen, gewoon online. Kinderbijslag en toeslagen komen vanzelf — maar alleen als jij dat goed vindt. Bij een bijzondere situatie (zoals erkenning met een ouder in het buitenland) neemt een medewerker het over.",
              "en": "We start arranging things before the birth. You register the birth within 5 days, simply online. Child benefit and allowances arrive automatically — but only if you agree. In a special situation (such as recognition with a parent abroad) a caseworker takes over."}},
    {"chip": "THK-24 · bouwen en wonen", "title": {"nl": "Ik wil bouwen of renoveren", "en": "I want to build or renovate"},
     "body": {"nl": "Je beschrijft je bouwplan in gewone woorden en ziet vooraf of je een vergunning nodig hebt. Je levert één keer alles aan, compleet. Een vergunningverlener — een mens — beoordeelt je aanvraag en beslist binnen 8 weken. Daarna wijzen wij je de volgende stappen.",
              "en": "You describe your building plan in plain words and see up front whether you need a permit. You submit everything once, complete. A permitting officer — a person — assesses your application and decides within 8 weeks. Afterwards, we point out your next steps."}},
    {"chip": "getest met lastige situaties", "title": {"nl": "Eerst getest, dan pas live", "en": "Tested first, live later"},
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
        data = {"runs": runs, "fixtures": fixtures, "common": common,
                "i18n": I18N, "scenes": SCENES,
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
