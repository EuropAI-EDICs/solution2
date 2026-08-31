#!/usr/bin/env python3
"""Golden-set author regression: deterministic author vs the LLM seam.

B2 of docs/GENAI_SEAMS.md: run both authors over the same baseline run (no
zone re-execution — proposals only, so this is cheap) and compare what they
target. The deterministic author is the reproducible golden set; the LLM
author's drift against it (and its reject ledger) is the regression signal.

    python3 poc/scenarios/compare_authors.py                  # wind, latest
    python3 poc/scenarios/compare_authors.py --use-case zon
    python3 poc/scenarios/compare_authors.py --use-case bos --max-scenarios 12

Output: poc/scenario-runs/<ts>-<use-case>-authorcmp/comparison.json + console
table. Offline for the deterministic author; the LLM leg needs
LDT_SCENARIO_LLM_ENDPOINT (local open model, temperature 0).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import scenario_author, scenarios  # noqa: E402

OUT_ROOT = POC_ROOT / "scenario-runs"


def latest_baseline_run(use_case: str) -> Path:
    runs = sorted((POC_ROOT / "runs").glob(f"*-{use_case}"))
    dirs = [p for p in runs if (p / "run_summary.json").is_file()]
    if not dirs:
        raise SystemExit(f"no pipeline run found for {use_case!r} under poc/runs/")
    return dirs[-1]


def _author_stats(specs: List[Dict[str, Any]], rejected: List[Dict[str, Any]]) -> Dict[str, Any]:
    targeted: Dict[str, List[str]] = {}
    for s in specs:
        for m in s["mutations"]:
            targeted.setdefault(str(m["ruleId"]), []).append(str(m["action"]))
    return {
        "accepted": len(specs),
        "rejected": len(rejected),
        "rejectKinds": sorted({r.get("kind", "?") for r in rejected}),
        "targetedRules": {k: sorted(v) for k, v in sorted(targeted.items())},
        "basisTypes": sorted({s["basis"]["type"] for s in specs}),
        "scenarioIds": [s["id"] for s in specs],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--use-case", default="wind")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--max-scenarios", type=int, default=10)
    args = ap.parse_args(argv)

    baseline_dir = Path(args.baseline) if args.baseline else latest_baseline_run(args.use_case)
    baseline = scenarios.load_baseline(baseline_dir)

    det = scenario_author.DeterministicScenarioAuthor()
    det_specs, det_rej = det.propose(baseline, args.max_scenarios)
    det_stats = _author_stats(det_specs, det_rej)

    llm_stats: Optional[Dict[str, Any]] = None
    llm_specs: List[Dict[str, Any]] = []
    llm_error: Optional[str] = None
    if scenario_author.LLMScenarioAuthor().endpoint:
        llm = scenario_author.LLMScenarioAuthor()
        llm_specs, llm_rej = llm.propose(baseline, args.max_scenarios)
        llm_stats = _author_stats(llm_specs, llm_rej)
    else:
        llm_error = "LDT_SCENARIO_LLM_ENDPOINT not set — LLM leg skipped"

    det_rules = set(det_stats["targetedRules"])
    llm_rules = set((llm_stats or {}).get("targetedRules", {}))
    comparison = {
        "useCase": args.use_case,
        "baselineRun": str(baseline_dir),
        "maxScenarios": args.max_scenarios,
        "deterministic": det_stats,
        "llm": llm_stats,
        "llmError": llm_error,
        "overlap": {
            "bothTarget": sorted(det_rules & llm_rules),
            "llmOnly": sorted(llm_rules - det_rules),
            "deterministicOnly": sorted(det_rules - llm_rules),
        },
    }

    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_ROOT / f"{run_ts}-{args.use_case}-authorcmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"[authorcmp] baseline {baseline_dir.name} (budget {args.max_scenarios})")
    for name, stats in (("deterministic", det_stats), ("llm", llm_stats)):
        if stats is None:
            print(f"  llm: SKIPPED ({llm_error})")
            continue
        print(f"  {name:<13} accepted={stats['accepted']} rejected={stats['rejected']} "
              f"bases={','.join(stats['basisTypes'])} "
              f"targets={len(stats['targetedRules'])} rules")
    if llm_stats is not None:
        ov = comparison["overlap"]
        print(f"  overlap: both={len(ov['bothTarget'])} "
              f"llm-only={ov['llmOnly'] or '—'} det-only={ov['deterministicOnly'] or '—'}")
    print(f"[authorcmp] {out_dir / 'comparison.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
