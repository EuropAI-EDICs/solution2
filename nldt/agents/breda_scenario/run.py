"""CLI: run the Breda what-if LangGraph (stub or live dispose).

Examples::

    # Offline stub (CI / no CBS cache)
    python -m agents.breda_scenario.run --stub --deep-research

    # Live against a prior scan run (needs poc-breda cache + optional LLM)
    python -m agents.breda_scenario.run --live \\
        --baseline ../poc-breda/runs/<ts>-breda-scan \\
        --out ../poc-breda/scenario-runs/<ts>-breda-graph \\
        --deep-research --what-if
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agents.breda_scenario.graph import build_breda_scenario_graph
from agents.breda_scenario.nodes import _ensure_breda_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Breda LangGraph what-if plane")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--stub", action="store_true", help="Offline stub nodes (default)")
    mode.add_argument("--live", action="store_true", help="Call poc-breda engines")
    ap.add_argument("--baseline", type=Path, help="Scan run dir with value-scan.json")
    ap.add_argument("--horizon", type=int, default=2050)
    ap.add_argument("--max-scenarios", type=int, default=6)
    ap.add_argument("--deep-research", action="store_true", help="Enable S10 node")
    ap.add_argument("--research-topic", default="")
    ap.add_argument("--what-if", action="store_true", help="Write what-if.html (live)")
    ap.add_argument("--out", type=Path, help="Output directory for report / what-if")
    args = ap.parse_args(argv)

    live = bool(args.live)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:6]

    initial: dict = {
        "run_id": run_id,
        "mode": "live" if live else "stub",
        "enable_deep_research": bool(args.deep_research),
        "research_topic": args.research_topic
        or f"Breda five-value horizon {args.horizon}",
        "horizon_year": args.horizon,
        "max_scenarios": args.max_scenarios,
        "build_whatif": bool(args.what_if and live),
    }

    if live:
        if not args.baseline:
            print("FATAL: --live requires --baseline <scan-run-dir>", file=sys.stderr)
            return 2
        scan_path = args.baseline / "value-scan.json"
        if not scan_path.is_file():
            print(f"FATAL: missing {scan_path}", file=sys.stderr)
            return 2
        _ensure_breda_path()
        from breda import fetch  # type: ignore

        baseline = json.loads(scan_path.read_text(encoding="utf-8"))
        layers = fetch.fetch_all(include_bomen=True)["layers"]
        if layers.get("buurten") is None:
            print("FATAL: buurten layer missing (empty cache?)", file=sys.stderr)
            return 2
        initial["baseline_scan"] = baseline
        initial["layers"] = layers
        out = args.out
        if out is None:
            breda = _ensure_breda_path()
            out = breda / "scenario-runs" / f"{run_id}-breda-graph"
        initial["out_dir"] = str(out)
        initial["build_whatif"] = True if args.what_if or args.out else bool(args.what_if)
        # default: always write report when live + out
        if args.out or args.what_if:
            initial["build_whatif"] = True
            initial["out_dir"] = str(out)

    app = build_breda_scenario_graph()
    result = app.invoke(initial, config={"configurable": {"thread_id": run_id}})

    if result.get("error"):
        print(json.dumps({"error": result["error"], "runId": run_id}, indent=2))
        return 1

    report = result.get("report") or {}
    summary = {
        "runId": run_id,
        "mode": initial["mode"],
        "graph": report.get("graph"),
        "nAccepted": report.get("nAccepted"),
        "nScenarios": report.get("nScenarios"),
        "variantIds": [v.get("scenarioId") for v in report.get("variants") or []],
        "llmPathwayIds": result.get("llm_pathway_ids") or [],
        "hasResearchBrief": bool(report.get("researchBrief")),
        "whatIfHtml": result.get("whatif_html_path"),
        "validation": (report.get("validation") or {}).get("verdict"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if not live and args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "scenario-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"wrote {args.out / 'scenario-report.json'}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
