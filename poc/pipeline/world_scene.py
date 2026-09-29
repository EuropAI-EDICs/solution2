"""Build WorldSceneSpec artefacts from a deterministic scenario-report (Plane B).

Renderer/copilot layer only — never executes zone algebra. See docs/POC_WORLD_MODEL_UTRECHT.md.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from pipeline import contracts

GENERATED_BY = "world-scene-build#poc-v0"

_OBJECT_TO_TRACK = {
    "wind_turbine": "wind",
    "solar_field": "zon",
    "forest_planting": "bos",
    "biomass_installation": "wind",
    "energy_storage": "zon",
}


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mutation_summary(mutations: Sequence[Mapping[str, Any]]) -> str:
    if not mutations:
        return "No mutations applied."
    parts: List[str] = []
    for m in mutations:
        action = m.get("action", "?")
        rid = m.get("ruleId", "?")
        if action == "drop":
            parts.append(f"drop {rid}")
        elif action == "set_semantics":
            parts.append(f"{rid} semantics -> {m.get('zoneSemantics', '?')}")
        elif action == "set_buffer_distance_m":
            parts.append(f"{rid} buffer -> {m.get('bufferDistanceM')} m")
        else:
            parts.append(f"{action} on {rid}")
    return "; ".join(parts)


def _marble_prompt(
    *,
    track: str,
    scenario_name: str,
    basis: Mapping[str, Any],
    delta_km2: float,
    mutation_summary: str,
) -> str:
    basis_type = basis.get("type", "hypothetical")
    note = str(basis.get("provenanceNote", ""))[:400]
    return (
        f"Aerial exploratory view of Utrecht province, Netherlands ({track} track). "
        f"Policy scenario: {scenario_name}. "
        f"Opportunity zone delta vs control: {delta_km2:+.3f} km². "
        f"Mutations: {mutation_summary}. "
        f"Provenance: {basis_type}. {note} "
        "Stylized visualization for deliberation only — not a legal map."
    )


def build_spec_for_scenario(
    report: Mapping[str, Any],
    row: Mapping[str, Any],
    *,
    scenario_run_id: str,
    hitl_approved: bool = False,
    marble_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """PoC-local builder without nldt marble_client (tests + offline)."""
    import os
    import urllib.parse

    sid = str(row["scenarioId"])
    basis = dict(row["basis"])
    basis_type = str(basis.get("type", "hypothetical"))
    object_type = str(report["objectType"])
    track = _OBJECT_TO_TRACK.get(object_type, "zon")
    control = report["control"]
    mutations = row.get("mutationsApplied") or []
    mutation_summary = _mutation_summary(mutations)
    delta = float(row.get("deltaVsControlKm2", 0.0))
    allow_gen = basis_type == "hypothetical"
    grounding = "marble-explore-not-legal" if allow_gen else "engine-only"

    geo_refs: List[Dict[str, str]] = [
        {
            "role": "control",
            "path": "scenarios/CONTROL.geojson",
            "relativeTo": "scenarioRunDir",
        }
    ]
    geom_file = str(row.get("geometryFile") or "").strip()
    if geom_file and row.get("geometryValid"):
        geo_refs.append(
            {
                "role": "scenario",
                "path": geom_file.replace("\\", "/"),
                "relativeTo": "scenarioRunDir",
            }
        )

    prompt = _marble_prompt(
        track=track,
        scenario_name=str(row.get("name", sid)),
        basis=basis,
        delta_km2=delta,
        mutation_summary=mutation_summary,
    )

    base = marble_base_url or os.environ.get(
        "MARBLE_API_BASE", "https://marble.worldlabs.ai"
    ).rstrip("/")
    marble_url = f"{base}/explore?prompt={urllib.parse.quote(prompt[:2000])}"
    hitl = hitl_approved or os.environ.get("MARBLE_HITL_APPROVED") == "1"
    marble_enabled = allow_gen and hitl and bool(geom_file)

    spec: Dict[str, Any] = {
        "id": f"WSS-{sid}",
        "scenarioRunId": scenario_run_id,
        "scenarioReportId": str(report["id"]),
        "scenarioId": sid,
        "baselineRunId": str(report["baselineRunId"]),
        "track": track,
        "objectType": object_type,
        "provenanceBasis": basis,
        "headlineDeltaKm2": round(delta, 9),
        "headlineDeltaPct": row.get("deltaVsControlPct"),
        "controlFinalAreaKm2": round(float(control["finalAreaKm2"]), 9),
        "scenarioFinalAreaKm2": round(float(row.get("finalAreaKm2", 0.0)), 9),
        "mutationSummary": mutation_summary,
        "geoLayerRefs": geo_refs,
        "marblePrompt": prompt,
        "allowGenerativeRenderer": allow_gen,
        "groundingStamp": "marble-explore-not-legal" if marble_enabled else grounding,
        "marble": {
            "exploreUrl": marble_url if marble_enabled else None,
            "hitlRequired": allow_gen,
            "enabled": marble_enabled,
        },
        "generatedAt": utcnow(),
        "generatedBy": GENERATED_BY,
    }
    contracts.validate(spec, "world-scene-spec")
    return spec


def build_specs_from_run_dir(
    scenario_run_dir: Path,
    *,
    hitl_approved: bool = False,
    marble_base_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    scenario_run_dir = scenario_run_dir.resolve()
    report_path = scenario_run_dir / "scenario-report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"missing scenario-report.json in {scenario_run_dir}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    contracts.validate(report, "scenario-report")
    run_id = scenario_run_dir.name
    builder = build_spec_for_scenario
    specs: List[Dict[str, Any]] = []
    for row in report.get("scenarios") or []:
        if row.get("status") == "degraded" and not row.get("geometryFile"):
            continue
        specs.append(
            builder(
                report,
                row,
                scenario_run_id=run_id,
                hitl_approved=hitl_approved,
                marble_base_url=marble_base_url,
            )
        )
    return specs


def write_world_scene_bundle(
    scenario_run_dir: Path,
    *,
    hitl_approved: bool = False,
    marble_base_url: Optional[str] = None,
) -> Path:
    specs = build_specs_from_run_dir(
        scenario_run_dir,
        hitl_approved=hitl_approved,
        marble_base_url=marble_base_url,
    )
    out = scenario_run_dir / "world-scene-specs.json"
    bundle = {
        "scenarioRunId": scenario_run_dir.name,
        "scenarioReportId": specs[0]["scenarioReportId"] if specs else None,
        "specCount": len(specs),
        "specs": specs,
        "generatedAt": utcnow(),
        "generatedBy": GENERATED_BY,
    }
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    prov_path = scenario_run_dir / "prov.json"
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        entity_id = "world-scene-specs.json"
        entities = prov.get("entity")
        if isinstance(entities, list) and not any(e.get("id") == entity_id for e in entities):
            digest = hashlib.sha256(out.read_bytes()).hexdigest()
            entities.append(
                {
                    "id": entity_id,
                    "type": "WorldSceneBundle (Renderer copilot contract)",
                    "path": str(out),
                    "sha256": digest,
                    "generatedBy": GENERATED_BY,
                }
            )
            prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out
