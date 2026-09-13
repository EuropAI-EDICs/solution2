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
                    help="baseline run-map (bevat value-scan.json)")
    ap.add_argument("--author", choices=["file", "auto", "llm"], default="file")
    ap.add_argument("--set", type=Path, default=DEFAULT_SET,
                    help="set-bestand bij --author file")
    ap.add_argument("--max-scenarios", type=int, default=6)
    ap.add_argument("--out", type=Path, default=None,
                    help="uitvoermap (default: poc-breda/scenario-runs/<ts>-breda-scen)")
    args = ap.parse_args(argv)

    baseline = json.loads(
        (args.run / "value-scan.json").read_text(encoding="utf-8")
    )

    # auteurs: voorstellen alleen, altijd achter dezelfde gate
    if args.author == "file":
        specs, rejected = scenarios.author_from_file(args.set)
    elif args.author == "auto":
        specs, rejected = scenarios.deterministic_author(args.max_scenarios)
    else:
        specs, rejected = scenarios.LLMScenarioAuthor().propose(args.max_scenarios)

    # lagen cache-first (offline herhaal na één scan-run)
    fetched = fetch.fetch_all(include_bomen=True)
    layers = fetched["layers"]
    if layers.get("buurten") is None:
        print("FATAAL: CBS-buurtvlakten ontbreken (cache leeg? draai poc-breda/run.py)",
              file=sys.stderr)
        return 2

    report = scenarios.run_scenarios(baseline, layers, specs)
    report["rejectedAuthoring"] = rejected
    report["author"] = args.author
    report["baselineRun"] = args.run.name

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
    summary = {
        "generatedAt": _now_iso(),
        "baselineRun": args.run.name,
        "author": args.author,
        "verdict": report["validation"]["verdict"],
        "nScenarios": report["nScenarios"],
        "nAccepted": report["nAccepted"],
        "controlIdentical": report["control"]["identicalToBaseline"],
        "rejected": report["rejected"] + report.get("rejectedAuthoring", []),
        "artifacts": {
            p.name: {"sha256": _sha256(p), "bytes": p.stat().st_size}
            for p in sorted(out_dir.glob("scenario-report.*"))
        },
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"What-if run: {out_dir}")
    print(f"  auteur: {args.author} · aangenomen: {report['nAccepted']}/{report['nScenarios']}")
    print(f"  control identiek aan baseline: {report['control']['identicalToBaseline']}")
    for v in report["variants"]:
        movers = ", ".join(
            g["buurtcode"] for g in v["grootsteVerschuivers"][:2]
        ) or "—"
        print(f"  - {v['name']}: {v['nBuurtenVeranderd']} buurten Δ (verschuivers: {movers})")
    for r in report["rejected"] + report.get("rejectedAuthoring", []):
        print(f"  - AFGEWEZEN {r.get('scenarioId') or '?'}: "
              f"{r.get('reden') or r.get('reason', '')[:100]}")
    print(f"  verdict: {report['validation']['verdict']}")
    print(f"  rapport: {out_dir / 'scenario-report.md'}")
    return 0 if report["validation"]["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())
