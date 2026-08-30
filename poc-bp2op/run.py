#!/usr/bin/env python3
"""CLI orchestrator of the bp2op PoC — "van bestemmingsplan naar omgevingsplan met AI",
the methods recorded in the VNG netwerksessie of 19 juni 2026 (the Amsterdams model,
tool: Plangids) projected on gemeente Eindhoven.

    Intake (use-case request, MC-1/MC-2/MC-9)
      -> RegelParser (MC-4: automatisch inlezen + opknippen)
      -> Kennisbank seeding (MC-5: published 'komt in de plaats van' relations)
      -> Matcher (MC-5: scored suggestions, bands 0.90/0.70; MC-6: never auto-coupled)
      -> Analyser (MC-8: conversie-gereedheid + needs-new-rules + portfolio)
      -> Critic (V0 schemas, V1 completeness, V2 grounding, V3 independent re-execution,
         V4 jurist checkpoint always pending)
      -> Explainer (MC-3: omzettabel exports + PROV) -> single-file HTML report (MC-7).

Usage (stdlib + verified toolchain, from the workspace root):

    python3 poc-bp2op/run.py                    # corpus-first (no network)
    python3 poc-bp2op/run.py --use-case eindhoven --out poc-bp2op/runs/demo
    python3 -m unittest discover -s poc-bp2op/tests

Exit code 0 only when the Critic's pipeline-run verdict is 'pass' (V4 stays pending
by design — MC-6: de mens blijft op de knoppen).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

POC_ROOT = Path(__file__).resolve().parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import analyser, contracts, critic, explainer, knowledgebank, parsers, report  # noqa: E402

RUN_VERSION = "poc-bp2op-run/1.0"
ORCHESTRATOR_AGENT = {"id": "orchestrator", "name": "run.py orchestrator", "version": RUN_VERSION,
                      "role": "intake -> dispatch -> verify -> synthesize (MC-3 omzettabel assembly)"}

GEbruiksdoel_QUOTE = (
    "Het begrip gebruiksdoel komt in de plaats van het begrip bestemming zoals we dat kennen "
    "vanuit de bestemmingsplannen.")

# hoofdstukken of the doelregeling that form the NEW-style core (match targets);
# 22 (bruidschat) and 23 (overgangsrecht) are the tijdelijk-deel-era chapters = bron side;
# 24 slotbepalingen carry no convertible rules.
BRON_HOOFDSTUKKEN = {22, 23}
DOEL_HOOFDSTUKKEN = set(range(1, 22))  # 1..21 incl. gereserveerde hoofdstukken (empty)

PLANVIEWER_URL = "https://www.planviewer.nl/bestemmingsplannen/Eindhoven"
PLANVIEWER_FILE = POC_ROOT / "corpus" / "eindhoven" / "planviewer-eindhoven-inventory.html"

_QA_CHECKLIST = [
    {"item": "algoritmeregister", "status": "n.v.t. in PoC — deterministisch, geen ML-model in productie (MC-12)"},
    {"item": "modelkeuze", "status": "geen extern model: deterministic offline matching; LLM-hook bewust uit (MC-4, 30:49)"},
    {"item": "privacy", "status": "geen persoonsgegevens; alleen openbare regelgeving (MC-12)"},
    {"item": "beveiliging", "status": "geen netwerkcomponent actief in de run; corpus-first"},
    {"item": "mens-op-de-knoppen", "status": "V4-juristtoets verplicht per rij (MC-6)"},
]


def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_request(use_case: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "id": use_case["id"],
        "municipality": use_case["municipality"],
        "beleid": use_case["beleid"],
        "doelregeling": use_case["doelregeling"],
        "bronset": use_case["bronset"],
        "kennisbankSeeds": use_case["kennisbankSeeds"],
        "pilotCriteria": use_case["pilotCriteria"],
        "methodCardsRef": use_case["methodCardsRef"],
    }
    contracts.validate("conversion-request", req)
    return req


def run(use_case_name: str, out_dir: Path) -> int:
    ts_tag = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = out_dir / f"{ts_tag}-{use_case_name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    now, today = _now_iso(), _today()

    use_case = contracts.load_json(POC_ROOT / "use-cases" / f"{use_case_name}.json")
    request = build_request(use_case)
    (run_dir / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=1), encoding="utf-8")

    doelregel_file = POC_ROOT / request["doelregeling"]["file"]
    cvdr_raw = doelregel_file.read_text(encoding="utf-8", errors="replace")
    doc_by_id = {b["docId"]: b for b in request["bronset"]}

    # ---- MC-4: automatisch inlezen + opknippen ----------------------------- #
    print("[1/7] MC-4 opknippen: doelregeling-index uit CVDR696400 …", file=sys.stderr)
    full_index = parsers.parse_doelregeling(
        cvdr_raw, cvdr=request["doelregeling"]["naam"], cvdr_id=request["doelregeling"]["cvdrId"],
        versie=request["doelregeling"]["versie"], exclude_hoofdstukken=set(), today=today)
    doel_regels = parsers.filter_doel_index(full_index, DOEL_HOOFDSTUKKEN)
    bron_regels = parsers.bronregels_uit_doelindex(
        full_index, BRON_HOOFDSTUKKEN, doc_id="B01",
        instrument=f"{request['doelregeling']['naam']} (CVDR696400/4, geldend 29-06-2026), hoofdstukken 22-23",
        url=request["doelregeling"]["url"], today=today)
    print(f"      {len(full_index)} artikelen geindexeerd; {len(doel_regels)} doelregels (hfd 1-21), "
          f"{len(bron_regels)} bronregels (hfd 22-23, tijdelijk deel/bruidschat)", file=sys.stderr)

    # ---- MC-5: kennisbank --------------------------------------------------- #
    print("[2/7] MC-5 kennisbank: vervangingsrelaties uit de wijzigingsbesluiten …", file=sys.stderr)
    kb_pairs: List[Dict[str, Any]] = []
    for doc_id in request["kennisbankSeeds"]:
        doc = doc_by_id[doc_id]
        raw = (POC_ROOT / doc["file"]).read_text(encoding="utf-8", errors="replace")
        kb_pairs.extend(parsers.parse_kennisbank_pairs(raw, doc_id, doc["url"], today, doel_regels))
    kb_pairs.extend(parsers.taxonomie_pairs(
        doel_regels, "B02", doc_by_id["B02"]["url"], today, GEbruiksdoel_QUOTE))
    # renumber + dedupe on (doelLocator, bronLabel)
    seen = set()
    uniq = []
    for p in kb_pairs:
        key = (p["doelLocator"], p["bronLabel"].lower())
        if key in seen:
            continue
        seen.add(key)
        p["id"] = f"KB-{len(uniq) + 1:03d}"
        uniq.append(p)
    kb_pairs = uniq
    kb = knowledgebank.Kennisbank(kb_pairs)
    print(f"      {len(kb_pairs)} kennisbank-relaties geseed", file=sys.stderr)

    # ---- MC-5/MC-6: matcher -------------------------------------------------- #
    print("[3/7] MC-5 matcher: gescoorde suggesties (nooit automatisch gekoppeld) …", file=sys.stderr)
    index = knowledgebank.TfidfIndex(
        {d["id"]: f"artikel {d['locator']['artikel']} {d['locator']['titel']} {d['tekst']}" for d in doel_regels})
    omzettabel: List[Dict[str, Any]] = []
    for bron in bron_regels:
        suggesties = knowledgebank.suggereer(bron, doel_regels, index, kb)
        if bron["statusInBron"] == "vervallen_in_bron":
            status = "needs_human"
            reden = ("Regel is in de bron gemarkeerd [Vervallen]: later besluit heeft de regel al opgeheven — "
                     "verifieer de stapelvolgorde (MC-10) vóór koppeling.")
        elif suggesties and suggesties[0]["score"] >= knowledgebank.BAND_STERK:
            status = "voorgesteld"
            reden = None
        elif suggesties and suggesties[0]["score"] >= knowledgebank.BAND_MOGELIJK:
            status = "voorgesteld"
            reden = None
        elif suggesties:
            status = "needs_human"
            reden = "Alleen zwakke overeenkomsten: geen verantwoorde koppeling zonder jurist (MC-6)."
        else:
            status = "nieuwe_regel_voorgesteld"
            reden = None
        omzettabel.append({
            "id": f"OT-{len(omzettabel) + 1:03d}",
            "bronRegelId": bron["id"],
            "suggesties": suggesties,
            "status": status,
            "needsHumanReden": reden,
            "toelichting": "",
            "reviewTrail": [{"ts": now, "actor": "pipeline", "actie": "rij gegenereerd met gescoorde suggesties (MC-5)"}],
            "werkingsgebiedRef": None,
            "methodTrace": ["MC-3", "MC-5", "MC-6"] + (["MC-10"] if status == "needs_human" and bron["statusInBron"] == "vervallen_in_bron" else []),
        })
    print(f"      {len(omzettabel)} rijen: "
          f"{sum(1 for r in omzettabel if r['status'] == 'voorgesteld')} voorgesteld, "
          f"{sum(1 for r in omzettabel if r['status'] == 'nieuwe_regel_voorgesteld')} nieuwe-regel, "
          f"{sum(1 for r in omzettabel if r['status'] == 'needs_human')} needs_human", file=sys.stderr)

    # ---- MC-8: bulk-analyse --------------------------------------------------- #
    print("[4/7] MC-8 bulk-analyse: conversie-gereedheid + portefeuille …", file=sys.stderr)
    coverage = analyser.coverage(
        bron_regels, omzettabel,
        {b["docId"]: b["naam"] for b in request["bronset"]}, today)
    portfolio = {"bronhouder": request["municipality"]["naam"], "laatstGeverifieerd": today,
                 "bron": PLANVIEWER_URL}
    if PLANVIEWER_FILE.exists():
        pv_raw = PLANVIEWER_FILE.read_text(encoding="utf-8", errors="replace")
        inv = parsers.parse_planviewer_inventory(pv_raw)
        portfolio.update({k: inv[k] for k in ("plannenTotaal", "vastgesteld", "tamOmgevingsplannen")})
        (run_dir / "plan-inventory.json").write_text(
            json.dumps(inv["records"], ensure_ascii=False, indent=1), encoding="utf-8")
    coverage["portfolio"] = portfolio
    contracts.validate("coverage-report", coverage)
    (run_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- MC-6: critic ---------------------------------------------------------- #
    print("[5/7] MC-6 critic: V0-V4 …", file=sys.stderr)
    sources = {"doelregeling": doelregel_file}
    sources.update({b["docId"]: POC_ROOT / b["file"] for b in request["bronset"]})
    validation, v3_detail = critic.validate_pipeline(
        request, bron_regels, doel_regels, kb_pairs, omzettabel, coverage, sources, now)
    contracts.validate("validation-report", validation)
    (run_dir / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- MC-3: explainer ------------------------------------------------------- #
    print("[6/7] MC-3 explainer: omzettabel + PROV …", file=sys.stderr)
    written = explainer.write_outputs(run_dir, omzettabel, bron_regels, doel_regels, kb_pairs)
    entities = {name: path for name, path in written.items()}
    entities["doelregeling-bronbestand"] = doelregel_file
    for b in request["bronset"]:
        entities[f"bronpublicatie-{b['docId']}"] = POC_ROOT / b["file"]
    activities = [
        {"naam": "intake", "agent": ORCHESTRATOR_AGENT["id"], "methodTrace": ["MC-1", "MC-2", "MC-9"], "ts": now},
        {"naam": "opknippen", "agent": parsers.PARSER_AGENT, "methodTrace": ["MC-4"], "ts": now},
        {"naam": "kennisbank-seed", "agent": parsers.PARSER_AGENT, "methodTrace": ["MC-5"], "ts": now},
        {"naam": "matchen", "agent": knowledgebank.MATCHER_AGENT, "methodTrace": ["MC-5", "MC-6"], "ts": now},
        {"naam": "bulk-analyse", "agent": analyser.ANALYSER_AGENT, "methodTrace": ["MC-8"], "ts": now},
        {"naam": "kritiek", "agent": critic.CRITIC_AGENT, "methodTrace": ["MC-6"], "ts": now},
        {"naam": "verantwoording", "agent": explainer.EXPLAIN_AGENT, "methodTrace": ["MC-3", "MC-7"], "ts": now},
    ]
    derivations = [
        {"generated": "omzettabel.json", "derivedFrom": ["bronregels.json", "doelregels.json", "kennisbank.json"]},
        {"generated": "coverage.json", "derivedFrom": ["omzettabel.json", "plan-inventory.json"]},
        {"generated": "report.html", "derivedFrom": ["omzettabel.json", "coverage.json", "validation.json"]},
    ]
    prov = explainer.prov_bundle(
        [ORCHESTRATOR_AGENT,
         {"id": "regel-parser", "name": parsers.PARSER_AGENT},
         {"id": "matcher", "name": knowledgebank.MATCHER_AGENT},
         {"id": "analyser", "name": analyser.ANALYSER_AGENT},
         {"id": "critic", "name": critic.CRITIC_AGENT},
         {"id": "explainer", "name": explainer.EXPLAIN_AGENT}],
        entities, activities, derivations,
        ["MC-1", "MC-2", "MC-3", "MC-4", "MC-5", "MC-6", "MC-7", "MC-8", "MC-9", "MC-10", "MC-11", "MC-12"])
    (run_dir / "prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- MC-7: report ----------------------------------------------------------- #
    print("[7/7] MC-7 rapport …", file=sys.stderr)
    n_sterk = sum(1 for r in omzettabel if r["suggesties"] and r["suggesties"][0]["band"] == "sterk")
    n_mog = sum(1 for r in omzettabel if r["suggesties"] and r["suggesties"][0]["band"] == "mogelijk")
    best_ratio = max((d["matchRatio"] for d in coverage["perBronDocument"]), default=0)
    headline = [
        {"label": "bronregels opgeknipt (MC-4)", "value": str(len(bron_regels)),
         "note": "hoofdstuk 22-23-artikelen van het geldende omgevingsplan (tijdelijk deel/bruidschat)"},
        {"label": "doelregels geïndexeerd (MC-1)", "value": str(len(doel_regels)),
         "note": "alle artikelen hfd 1-21 van CVDR696400/4"},
        {"label": "kennisbank-relaties (MC-5)", "value": str(len(kb_pairs)),
         "note": "uit Eindhovense wijzigingsbesluiten (2023/2025/2026) + gebruiksdoel-taxonomie"},
        {"label": "rijen met sterke suggestie", "value": str(n_sterk),
         "note": f"score ≥ 0,90 (band zoals de tool: 90-70%); {n_mog} rijen mogelijk (0,70-0,90)"},
        {"label": "beste match-ratio brondocument", "value": f"{best_ratio:.0%}",
         "note": "conversie-gereedheid conform de bulk-analyse (MC-8)"},
        {"label": "jurist-rijen (V4, MC-6)", "value": str(sum(1 for r in omzettabel if r["status"] == "needs_human")),
         "note": "nooit automatisch gekoppeld; de mens blijft op de knoppen"},
    ]
    report.render(
        run_dir / "report.html",
        title="bp2op Eindhoven — omzettabel van tijdelijk deel naar omgevingsplan",
        subtitle=("Methodes van de VNG-netwerksessie ‘van bestemmingsplan naar omgevingsplan met AI — "
                  "de Amsterdams aanpak’ (19-06-2026), geprojecteerd op gemeente Eindhoven. "
                  "Doelregeling: Omgevingsplan gemeente Eindhoven, CVDR696400/4, geldend 29-06-2026."),
        generated=now, run_id=ts_tag, verdict=validation["verdict"], headline_cards=headline,
        coverage_rows=coverage["perBronDocument"], needs_new=coverage["needsNewRules"],
        portfolio=portfolio, kb_pairs=kb_pairs, omzettabel=omzettabel, bron_regels=bron_regels,
        doel_regels=doel_regels, validation=validation,
        footer=(f"{RUN_VERSION} · methodes: corpus/METHOD-CARDS.md (transcript met tijdstempels) · "
                f"V3-detail: {json.dumps(v3_detail)} · QA-self-assessment: "
                + " | ".join(f"{c['item']}: {c['status']}" for c in _QA_CHECKLIST)))

    # ---- run summary --------------------------------------------------------------- #
    summary = {
        "runId": ts_tag,
        "useCase": use_case_name,
        "verdict": validation["verdict"],
        "levels": validation["levels"],
        "v3Detail": v3_detail,
        "counts": {
            "bronRegels": len(bron_regels), "doelRegels": len(doel_regels),
            "kennisbank": len(kb_pairs), "omzettabelRijen": len(omzettabel),
            "voorgesteld": sum(1 for r in omzettabel if r["status"] == "voorgesteld"),
            "nieuweRegel": sum(1 for r in omzettabel if r["status"] == "nieuwe_regel_voorgesteld"),
            "needsHuman": sum(1 for r in omzettabel if r["status"] == "needs_human"),
        },
        "portfolio": portfolio,
        "businessCase": {
            "bron": "corpus/METHOD-CARDS.md — nummers zoals opgenomen in de sessie",
            "amsterdam": {"plannen": 530, "uurPerPlan": ">1000", "fte": "≈450", "versnelling": "≈20×",
                          "kosten": "≈€300k / 1,5 jaar"},
            "eindhoven": {"plannenTotaal": portfolio.get("plannenTotaal"),
                          "tamOmgevingsplannen": portfolio.get("tamOmgevingsplannen"),
                          "deadline": request["municipality"]["deadline"]},
        },
        "qaSelfAssessment": _QA_CHECKLIST,
        "methodTrace": ["MC-1", "MC-2", "MC-3", "MC-4", "MC-5", "MC-6", "MC-7", "MC-8", "MC-9", "MC-10", "MC-11", "MC-12"],
        "artifacts": {p.name: explainer.sha256_file(p) for p in sorted(run_dir.iterdir()) if p.is_file()},
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nrun dir: {run_dir}", file=sys.stderr)
    print(f"verdict: {validation['verdict']} (V4 human: pending by design)", file=sys.stderr)
    return 0 if validation["verdict"] == "pass" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--use-case", default="eindhoven", help="use-case name in poc-bp2op/use-cases/")
    ap.add_argument("--out", default=str(POC_ROOT / "runs"), help="output root (run subdir is created)")
    args = ap.parse_args()
    try:
        return run(args.use_case, Path(args.out))
    except contracts.ContractError as exc:
        print(f"CONTRACT FAILURE: {exc}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
