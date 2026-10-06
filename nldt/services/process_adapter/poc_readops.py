"""Read-only operaties op canonieke PoC-run-artefacten (harness-unificatie M1).

De server leest het bestandssysteem — de agent nooit direct. Alle functies
zijn puur en testbaar via de `runs_dir`-injectie; de MCP-registratie (poc-
en data-server) roept ze met de canonieke locatie aan.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
POC_RUNS = WORKSPACE / "poc" / "runs"
POC_SCENARIO_RUNS = WORKSPACE / "poc" / "scenario-runs"


def _resolve_run_dir(runs_dir: Path | None, run_id: str) -> Path | None:
    """Zoek `<runs_dir>/<run_id>` (en scenario-runs als fallback)."""
    roots = [runs_dir] if runs_dir else [POC_RUNS, POC_SCENARIO_RUNS]
    for root in roots:
        candidate = root / run_id
        if candidate.is_dir():
            return candidate
    return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def get_provenance(run_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    work = _resolve_run_dir(runs_dir, run_id)
    if work is None:
        return {"error": f"Geen run-directory voor '{run_id}' onder poc/runs of poc/scenario-runs.", "runId": run_id}
    prov_path = work / "prov.json"
    entities: list[dict[str, Any]] = []
    if prov_path.is_file():
        prov = _read_json(prov_path)
        entities = [
            {k: e.get(k) for k in ("id", "type", "generatedBy", "sha256") if e.get(k)}
            for e in prov.get("entity", [])
            if isinstance(e, dict)
        ]
    return {"runId": run_id, "entities": entities}


def inspect_geo_layer(run_id: str, layer: str, runs_dir: Path | None = None) -> dict[str, Any]:
    work = _resolve_run_dir(runs_dir, run_id)
    if work is None:
        return {"error": f"Geen run-directory voor '{run_id}'.", "runId": run_id}
    layers_path = work / "layers.json"
    if not layers_path.is_file():
        return {"error": f"Geen layers.json in run '{run_id}'.", "runId": run_id}
    layers = _read_json(layers_path)
    if layer not in layers:
        return {"error": f"Laag '{layer}' niet in run '{run_id}'.", "available": sorted(layers), "runId": run_id}
    zones_path = work / "zones.json"
    zones_raw: Any = _read_json(zones_path) if zones_path.is_file() else []
    if isinstance(zones_raw, dict):
        zones_raw = zones_raw.get("features", [])
    matching = [
        z for z in zones_raw
        if isinstance(z, dict)
        and (z.get("zoneId") == layer or z.get("properties", {}).get("zoneId") == layer)
    ]
    return {"runId": run_id, "layer": layer, "meta": layers[layer], "zoneCount": len(matching), "zones": matching[:20]}


def crosscheck_formal_rule(scenario_run_id: str, formal_rule_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    rid = scenario_run_id.removeprefix("-worldscene")
    work = _resolve_run_dir(runs_dir, rid)
    report_path = work / "scenario-report.json" if work else None
    if report_path is None or not report_path.is_file():
        return {
            "error": f"Geen scenario-report voor '{scenario_run_id}' — gebruik het scenario-run-id en bouw eerst de world-scene.",
            "formalRuleId": formal_rule_id.upper(),
        }
    report = _read_json(report_path)
    rid_arg = formal_rule_id.upper()
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for sc in report.get("scenarios", []):
        for m in sc.get("mutationsApplied") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                applied.append({"scenarioId": sc.get("scenarioId"), "action": m.get("action"), "note": (m.get("note") or "")[:120]})
        for m in sc.get("mutationsSkipped") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                skipped.append({"scenarioId": sc.get("scenarioId"), "reason": (m.get("reason") or m.get("note") or "")[:120]})
    return {
        "scenarioRunId": rid,
        "formalRuleId": rid_arg,
        "executedByEngine": bool(applied),
        "appliedMutations": applied,
        "skippedMutations": skipped,
    }
