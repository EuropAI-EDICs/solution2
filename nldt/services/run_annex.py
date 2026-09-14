"""S9 run annex — traceability receipts for policy documents (BK-3).

Given recipe executions (services.recipe_runner.run_recipe shape), build a
deterministic annex document: every spatial number in an exported policy
document must trace to a step jobId + PROV bundle recorded here. Annex
generation is a pure function of the recorded executions: re-generating
from the same execution JSON is byte-identical. Re-executing a recipe
produces fresh jobIds and PROV timestamps by design — the annex records
the runs that actually produced the numbers.
"""

from __future__ import annotations

import json
from typing import Any

ANNEX_VERSION = "1.0.0"


def build_run_annex(executions: list[dict[str, Any]]) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for ex in executions:
        run: dict[str, Any] = {
            "recipeId": ex.get("recipeId", ""),
            "steps": [
                {
                    "stepId": s.get("stepId", ""),
                    "processId": s.get("processId", ""),
                    "jobId": s.get("jobId"),
                    "prov": s.get("prov") or {},
                }
                for s in ex.get("steps", [])
            ],
            "outputKeys": sorted(ex.get("outputs", {}).keys()),
        }
        if isinstance(ex.get("validation_report"), dict):
            run["validationReport"] = ex["validation_report"]
        runs.append(run)
    return {"annexVersion": ANNEX_VERSION, "runs": runs}


def render_annex_markdown(annex: dict[str, Any]) -> str:
    lines = [
        "## Annex: nLDT run receipts (seam S9)",
        "",
        "Every spatial figure in this document traces to the engine runs below",
        "(jobId + PROV). Runs replay offline and bit-identically via",
        "`PYTHONPATH=. python -m services.cli run-recipe <recipeId>`.",
        "",
    ]
    for run in annex.get("runs", []):
        lines.append(f"### Recipe: {run['recipeId']}")
        lines.append("")
        lines.append("| Step | Process | Job ID |")
        lines.append("|---|---|---|")
        for s in run["steps"]:
            lines.append(f"| {s['stepId']} | {s['processId']} | {s['jobId']} |")
        if "validationReport" in run:
            lines.append("")
            lines.append(f"Validation: `{json.dumps(run['validationReport'], sort_keys=True)}`")
        lines.append("")
    return "\n".join(lines)
