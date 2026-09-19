#!/usr/bin/env python3
"""PoC-4 what-if-naad: scenario's over de Breda vijf-waardenscan.

Een scenario is een contract (schemas/value-scenario.schema.json), geen
prompt: mutaties over de samenstel-parameters, verplichte bewijsklasse
(indicator_variance · policy_variant · hypothetical). De runner herhaalt
eerst een ongemuteerde control die de baseline bit-identiek moet
reproduceren; pas dan worden varianten geloofd. Offline: de lagen komen
cache-first uit data/cache (geen netwerk nodig na één scan-run).

    nldt/.venv/bin/python poc-breda/scenario_run.py --run poc-breda/runs/<ts>-breda-scan
    … --author auto            # deterministische auteur (golden set)
    … --author llm             # LDT_SCENARIO_LLM_ENDPOINT/-MODEL (voorstel-only)
    … --set mijn-set.json      # eigen set bij --author file

Exit 0 alleen bij validatorverdict ``pass``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(POC_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import fetch, scenarios  # noqa: E402

DEFAULT_SET = ROOT / "scenarios" / "breda.json"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True,
                    help="baseline run dir (contains value-scan.json)")
    ap.add_argument("--author", choices=["file", "auto", "llm"], default="file")
    ap.add_argument("--set", type=Path, default=DEFAULT_SET,
                    help="set file for --author file")
    ap.add_argument("--max-scenarios", type=int, default=6)
    ap.add_argument(
        "--horizon",
        type=int,
        default=2050,
        help="Linear CBS projection year for LLM digest + deterministic 2050 floor (0=off)",
    )
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default: poc-breda/scenario-runs/<ts>-breda-scen)")
    args = ap.parse_args(argv)

    baseline = json.loads(
        (args.run / "value-scan.json").read_text(encoding="utf-8")
    )

    # auteurs: voorstellen alleen, altijd achter dezelfde gate
    lake_hints: list = []
    projections: list = []
    if args.author == "file":
        specs, rejected = scenarios.author_from_file(args.set)
    elif args.author == "auto":
        specs, rejected = scenarios.deterministic_author(args.max_scenarios)
    else:
        lake_hints = scenarios.breda_lake_series_hints()
        if args.horizon and args.horizon > 0:
            projections = scenarios.breda_horizon_projections(args.horizon)
            lake_hints = scenarios.enrich_hints_with_projections(lake_hints, projections)
            floor, floor_rej = scenarios.deterministic_scenarios_2050(
                projections, max_scenarios=3
            )
            print(f"  horizon {args.horizon}: {len(projections)} projections, "
                  f"{len(floor)} floor scenarios")
            for p in projections[:4]:
                print(f"    · {p['buurtnaam']} {p['variable']}: "
                      f"{p['lastObserved']['value']}→{p['horizon']}≈{p['projected']}{p['unit']}")
        else:
            floor, floor_rej = [], []
        print(f"  lakeSeriesHints: {len(lake_hints)} series for LLM digest")
        llm_budget = max(1, args.max_scenarios - len(floor))
        llm_specs, llm_rej = scenarios.LLMScenarioAuthor().propose(
            llm_budget,
            lake_series_hints=lake_hints,
            horizon_projections=projections or None,
        )
        specs, merge_rej = scenarios.merge_horizon_floor_and_llm(
            floor, llm_specs, max_scenarios=args.max_scenarios
        )
        rejected = floor_rej + llm_rej + merge_rej

    # lagen cache-first (offline herhaal na één scan-run)
    fetched = fetch.fetch_all(include_bomen=True)
    layers = fetched["layers"]
    if layers.get("buurten") is None:
        print("FATAL: CBS neighbourhood polygons missing (empty cache? run poc-breda/run.py)",
              file=sys.stderr)
        return 2

    report = scenarios.run_scenarios(baseline, layers, specs)
    report["rejectedAuthoring"] = rejected
    report["author"] = args.author
    report["baselineRun"] = args.run.name
    if lake_hints:
        report["lakeSeriesHints"] = lake_hints
    if projections:
        report["horizonProjections"] = [
            {
                "seriesId": p.get("seriesId"),
                "buurtnaam": p.get("buurtnaam"),
                "variable": p.get("variable"),
                "unit": p.get("unit"),
                "horizon": p.get("horizon"),
                "projected": p.get("projected"),
                "slopePerYear": p.get("slopePerYear"),
                "lastObserved": p.get("lastObserved"),
                "method": p.get("method"),
            }
            for p in projections
        ]
        report["horizonYear"] = args.horizon

    if projections:
        print("  building horizon pathway keyframes (2026→2050, step=4)…")
        report["horizonPathway"] = scenarios.build_horizon_pathway_frames(
            layers,
            baseline,
            projections,
            start_year=2026,
            end_year=int(args.horizon),
            step=4,
        )
        print(f"  pathway keyframes: {list(report['horizonPathway']['keyframes'])}")

    llm_variants = [
        v for v in report.get("variants") or []
        if str(v.get("proposedBy") or "").lower().startswith("llm")
    ]
    if llm_variants:
        hz = int(args.horizon) if args.horizon and args.horizon > 0 else 2050
        print(f"  building per-AI pathways ({len(llm_variants)} proposals → {hz})…")
        llm_paths = scenarios.build_llm_scenario_pathways(
            layers,
            baseline,
            llm_variants,
            start_year=2026,
            end_year=hz,
            step=4,
        )
        if llm_paths:
            report["llmScenarioPathways"] = llm_paths
            # drop legacy merged pathway if present
            report.pop("llmHorizonPathway", None)
            print(f"  llm scenario pathways: {list(llm_paths)}")

    out_dir = args.out or (
        ROOT / "scenario-runs" /
        f"{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-breda-scen"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "scenario-report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out_dir / "scenario-report.md").write_text(
        scenarios.build_report_md(report), encoding="utf-8"
    )
    (out_dir / "what-if.html").write_text(
        scenarios.build_whatif_html(report, layers), encoding="utf-8"
    )
    summary = {
        "generatedAt": _now_iso(),
        "baselineRun": args.run.name,
        "author": args.author,
        "verdict": report["validation"]["verdict"],
        "nScenarios": report["nScenarios"],
        "nAccepted": report["nAccepted"],
        "controlIdentical": report["control"]["identicalToBaseline"],
        "rejected": report["rejected"] + report.get("rejectedAuthoring", []),
        "lakeSeriesHints": [
            {"seriesId": h.get("seriesId"), "variable": h.get("variable")}
            for h in lake_hints
        ],
        "horizonYear": args.horizon if args.author == "llm" and args.horizon else None,
        "horizonProjectionCount": len(projections),
        "artifacts": {
            p.name: {"sha256": _sha256(p), "bytes": p.stat().st_size}
            for p in sorted(out_dir.glob("scenario-report.*"))
        } | {
            "what-if.html": {"sha256": _sha256(out_dir / "what-if.html"),
                             "bytes": (out_dir / "what-if.html").stat().st_size},
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"What-if run: {out_dir}")
    print(f"  author: {args.author} · accepted: {report['nAccepted']}/{report['nScenarios']}")
    print(f"  control identical to baseline: {report['control']['identicalToBaseline']}")
    for v in report["variants"]:
        movers = ", ".join(
            g.get("buurt") or g["buurtcode"] for g in v["grootsteVerschuivers"][:2]
        ) or "—"
        print(f"  - {v['name']}: {v['nBuurtenVeranderd']} neighbourhoods Δ (movers: {movers})")
    for r in report["rejected"] + report.get("rejectedAuthoring", []):
        print(f"  - REJECTED {r.get('scenarioId') or '?'}: "
              f"{r.get('reden') or r.get('reason', '')[:100]}")
    print(f"  verdict: {report['validation']['verdict']}")
    print(f"  report: {out_dir / 'scenario-report.md'}")
    return 0 if report["validation"]["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
