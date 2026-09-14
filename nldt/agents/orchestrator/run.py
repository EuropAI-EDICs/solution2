from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

from agents.orchestrator.graph import build_graph


def _parse_inputs(raw: list[str]) -> dict:
    out = {}
    for item in raw:
        key, _, value = item.partition("=")
        if value.startswith("{") or value.startswith("["):
            out[key] = json.loads(value)
        else:
            out[key] = value
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="nLDT LangGraph orchestrator")
    parser.add_argument("--request", required=True, help="Natural language request")
    parser.add_argument("--recipe", help="Force recipe id")
    parser.add_argument("--input", action="append", help="key=value")
    parser.add_argument("--aoi-file", help="GeoJSON AOI file")
    parser.add_argument("--auto-approve-hitl", action="store_true")
    parser.add_argument("--no-register-pv", action="store_true")
    parser.add_argument("--no-export-3d", action="store_true")
    parser.add_argument("--output-dir", help="Write run artifacts here")
    args = parser.parse_args(argv)

    inputs = _parse_inputs(args.input or [])
    if args.aoi_file:
        with Path(args.aoi_file).open(encoding="utf-8") as f:
            inputs.setdefault("aoi", json.load(f))

    run_id = str(uuid4())[:8]
    initial = {
        "run_id": run_id,
        "natural_language_request": args.request,
        "recipe_id": args.recipe,
        "resolved_inputs": inputs,
        "auto_approve_hitl": args.auto_approve_hitl,
        "register_pv": not args.no_register_pv,
        "export_3d": not args.no_export_3d,
    }

    app = build_graph()
    config = {"configurable": {"thread_id": run_id}}
    result = app.invoke(initial, config=config)

    payload = {
        "runId": run_id,
        "error": result.get("error"),
        "agentPlan": result.get("agent_plan"),
        "execution": result.get("execution"),
        "validationReport": result.get("validation_report"),
        "hybrid": result.get("hybrid"),
        "explanation": result.get("explanation"),
    }
    print(json.dumps(payload, indent=2))

    out_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parents[2] / "data" / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, key in [
        ("agent-plan.json", "agent_plan"),
        ("execution.json", "execution"),
        ("validation-report.json", "validation_report"),
        ("explanation.json", "explanation"),
    ]:
        if result.get(key):
            (out_dir / name).write_text(json.dumps(result[key], indent=2), encoding="utf-8")
    prov_steps = [s.get("prov") for s in (result.get("execution") or {}).get("steps", []) if s.get("prov")]
    prov_bundle = {
        "runId": run_id,
        "recipeId": (result.get("execution") or {}).get("recipeId"),
        "dataPlane": result.get("data_plane"),
        "steps": prov_steps,
    }
    if prov_steps or result.get("execution"):
        (out_dir / "prov.json").write_text(json.dumps(prov_bundle, indent=2), encoding="utf-8")
    if result.get("lake_hits"):
        (out_dir / "lake-hits.json").write_text(
            json.dumps(result.get("lake_hits"), indent=2), encoding="utf-8"
        )

    if result.get("error"):
        return 1
    if result.get("validation_report", {}).get("verdict") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
