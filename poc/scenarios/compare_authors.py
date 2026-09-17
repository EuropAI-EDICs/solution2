#!/usr/bin/env python3
"""Golden-set author regression: deterministic vs LLM vs hybrid.

B2 of docs/GENAI_SEAMS.md: run authors over the same baseline run (no
zone re-execution — proposals only) and compare what they target. The
deterministic author is the reproducible golden set; hybrid must keep the
det floor intact (``overlap.floorIntact``).

    python3 poc/scenarios/compare_authors.py                  # wind, latest
    python3 poc/scenarios/compare_authors.py --use-case zon
    python3 poc/scenarios/compare_authors.py --use-case bos --max-scenarios 12

Requires for the LLM leg:
    export LDT_SCENARIO_LLM_ENDPOINT=http://localhost:11434
    export LDT_SCENARIO_LLM_API=ollama
    export LDT_SCENARIO_LLM_MODEL=qwen3.8:latest

Output: poc/scenario-runs/<ts>-<use-case>-authorcmp/comparison.json + console
table. Offline for the deterministic/hybrid (soft) legs; the LLM-only leg
needs LDT_SCENARIO_LLM_ENDPOINT.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
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

    t0 = time.perf_counter()
    det = scenario_author.DeterministicScenarioAuthor()
    det_specs, det_rej = det.propose(baseline, args.max_scenarios)
    det_stats = _author_stats(det_specs, det_rej)
    det_stats["seconds"] = round(time.perf_counter() - t0, 3)

    llm_stats: Optional[Dict[str, Any]] = None
    llm_error: Optional[str] = None
    llm_model = os.environ.get("LDT_SCENARIO_LLM_MODEL")
    endpoint = scenario_author.LLMScenarioAuthor().endpoint
    if endpoint:
        t1 = time.perf_counter()
        try:
            llm = scenario_author.LLMScenarioAuthor()
            llm_specs, llm_rej = llm.propose(baseline, args.max_scenarios)
            llm_stats = _author_stats(llm_specs, llm_rej)
            llm_stats["seconds"] = round(time.perf_counter() - t1, 3)
            llm_stats["model"] = llm.model
            llm_model = llm.model
        except Exception as exc:  # noqa: BLE001 — benchmark must still emit comparison
            llm_error = f"{type(exc).__name__}: {exc}"
            llm_stats = {
                "accepted": 0,
                "rejected": 0,
                "rejectKinds": [],
                "targetedRules": {},
                "basisTypes": [],
                "scenarioIds": [],
                "seconds": round(time.perf_counter() - t1, 3),
                "model": llm_model,
            }
    else:
        llm_error = "LDT_SCENARIO_LLM_ENDPOINT not set — LLM leg skipped"

    t2 = time.perf_counter()
    hyb = scenario_author.HybridScenarioAuthor()
    hyb_specs, hyb_rej = hyb.propose(baseline, args.max_scenarios)
    hyb_stats = _author_stats(hyb_specs, hyb_rej)
    hyb_stats["seconds"] = round(time.perf_counter() - t2, 3)
    hyb_stats["model"] = getattr(hyb, "model", None)

    det_ids = {s["id"] for s in det_specs}
    floor_intact = det_ids <= {s["id"] for s in hyb_specs}

    det_rules = set(det_stats["targetedRules"])
    llm_rules = set((llm_stats or {}).get("targetedRules", {}))
    comparison = {
        "useCase": args.use_case,
        "baselineRun": str(baseline_dir),
        "maxScenarios": args.max_scenarios,
        "model": llm_model,
        "endpoint": os.environ.get("LDT_SCENARIO_LLM_ENDPOINT"),
        "api": os.environ.get("LDT_SCENARIO_LLM_API"),
        "deterministic": det_stats,
        "llm": llm_stats,
        "llmError": llm_error,
        "hybrid": hyb_stats,
        "overlap": {
            "bothTarget": sorted(det_rules & llm_rules),
            "llmOnly": sorted(llm_rules - det_rules),
            "deterministicOnly": sorted(det_rules - llm_rules),
            "hybridAccepted": hyb_stats["scenarioIds"],
            "floorIntact": floor_intact,
        },
    }

    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_ROOT / f"{run_ts}-{args.use_case}-authorcmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"[authorcmp] baseline {baseline_dir.name} (budget {args.max_scenarios})")
    if llm_model:
        print(f"  model={llm_model} api={os.environ.get('LDT_SCENARIO_LLM_API', 'openai')}")
    for name, stats in (("deterministic", det_stats), ("llm", llm_stats), ("hybrid", hyb_stats)):
        if stats is None:
            print(f"  llm: SKIPPED ({llm_error})")
            continue
        print(f"  {name:<13} accepted={stats['accepted']} rejected={stats['rejected']} "
              f"bases={','.join(stats['basisTypes']) or '—'} "
              f"targets={len(stats['targetedRules'])} rules "
              f"({stats.get('seconds', '?')}s)")
    print(f"  floorIntact={floor_intact}")
    if llm_error and endpoint:
        print(f"  llm error: {llm_error}")
    elif llm_stats is not None and not llm_error:
        ov = comparison["overlap"]
        print(f"  overlap: both={len(ov['bothTarget'])} "
              f"llm-only={ov['llmOnly'] or '—'} det-only={ov['deterministicOnly'] or '—'}")
    print(f"[authorcmp] {out_dir / 'comparison.json'}")
    bad_llm = bool(llm_error and endpoint)
    bad_floor = not floor_intact
    return 1 if (bad_llm or bad_floor) else 0


if __name__ == "__main__":
    sys.exit(main())
