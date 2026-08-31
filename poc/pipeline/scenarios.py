#!/usr/bin/env python3
"""Deterministic scenario engine for the opportunity-map PoC (Phase A).

Implements the scenario-planning stage of docs/GENAI_SEAMS.md with **no LLM
at runtime**: a scenario is a ``ScenarioSpec`` (schema-validated contract,
``poc/schemas/scenario-spec.schema.json``) — an ordered list of deterministic
mutations over a *baseline run's* FormalRule set, plus a provenance ``basis``
that keeps hypotheticals traceable without faking a legal citation:

* ``baseline``      — reserved for the control the runner always synthesises:
                      the unmutated rule set re-executed over the baseline
                      run's cached layers. Deltas are measured against THIS
                      reproduction, never against a stale summary number.
* ``norm_variance`` — varies a parameter of a CITED rule (``normCardId``
                      required; e.g. the art. 9.25 lid 2 1500 m buffer).
* ``policy_variant``— flips a documented discretionary choice (e.g. the
                      art. 6.3 lid 2 NNN exception applied province-wide).
* ``hypothetical``  — free parameter exploration with NO legal grounding
                      (``rationale`` required). This is the honest counterpart
                      of the cite-or-abstain ledger: abstained topics (e.g.
                      setback distances) may be *explored* here, explicitly
                      flagged as not legally grounded.

Mutations are restricted to what the zone engine actually consumes —
``drop``, ``set_semantics``, ``set_buffer_distance_m`` — so a scenario can
never smuggle in new geometry or re-derived conditions. Only rules that the
baseline actually executed (``status == formalized``) are eligible; anything
else is skipped with a recorded reason, never guessed.

The GenAI ScenarioAuthor of Phase B (docs/GENAI_SEAMS.md) does exactly what
the deterministic author does today — emit ScenarioSpec proposals
(``proposedBy: llm-proposal#...``) — and nothing more: the engine executes,
the critic validates (V0–V3 + V4 pending), humans stay on the buttons.
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from shapely.geometry import shape
from shapely.ops import transform as _shp_transform

from pipeline import cartographer, contracts, engine

try:
    from pyproj import Transformer

    _WGS84_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
except Exception:  # pragma: no cover - toolchain guarantees pyproj
    raise ImportError("pipeline/scenarios.py requires pyproj")

__all__ = [
    "SCENARIOS_VERSION",
    "ScenarioError",
    "CONTROL_REPRODUCTION_REL_TOLERANCE",
    "apply_mutations",
    "build_validation_report",
    "check_narrative_grounding",
    "deterministic_narrative",
    "eligible_rules",
    "execute_rule_set",
    "final_and_inclusion",
    "load_baseline",
    "load_layers",
    "narrate_report",
    "aoi_from_baseline",
    "final_geometry_rd",
    "report_markdown",
    "run_scenario_set",
    "sources_prov_from_manifest",
]

SCENARIOS_VERSION = "poc-scenario-engine/0.1"
SCENARIO_AUTHOR = "deterministic-scenario-author#poc-v0"
SCENARIO_CRITIC_RUN = "scenario-critic#poc-v0.1"

#: same-code-path replay of the baseline should agree far tighter than the
#: critic's cross-implementation V3 gate (1%); 0.1% guards library drift only
CONTROL_REPRODUCTION_REL_TOLERANCE = 0.001


class ScenarioError(ValueError):
    """Raised for scenario inputs the runner refuses to guess about."""


# --------------------------------------------------------------------------- #
# baseline loading (a scenario run REPLAYS a pipeline run: same request, same
# rules, same cached layers, same tunings — offline by construction)
# --------------------------------------------------------------------------- #

def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_baseline(run_dir: Path) -> Dict[str, Any]:
    """Load everything a scenario sweep needs from a canonical pipeline run.

    Required files: request.json, formalrules.json, normcards.json,
    run_summary.json, layers.json (the manifest with per-zone cache paths).
    The input simplification tolerance is read from the baseline's recorded
    tunings so the replay matches the baseline's engine inputs exactly.
    """
    run_dir = Path(run_dir)
    missing = [
        n for n in ("request.json", "formalrules.json", "normcards.json",
                    "run_summary.json", "layers.json")
        if not (run_dir / n).is_file()
    ]
    if missing:
        raise ScenarioError(
            f"baseline run {run_dir} is missing {', '.join(missing)} — run "
            f"poc/run.py first (a scenario sweep replays a pipeline run)"
        )
    request = _read_json(run_dir / "request.json")
    contracts.validate(request, "opportunity-map-request")
    rules = _read_json(run_dir / "formalrules.json")
    normcards = _read_json(run_dir / "normcards.json")
    summary = _read_json(run_dir / "run_summary.json")
    manifest = _read_json(run_dir / "layers.json")
    simplify_m = 2.0  # default matches run.py's --input-simplify-m
    for t in summary.get("tunings", []):
        if t.get("k") == "input_simplify_m":
            simplify_m = float(t.get("v") or 0) or simplify_m
    run_id = str(summary.get("runId") or run_dir.name)
    return {
        "runDir": run_dir,
        "runId": run_id,
        "request": request,
        "formalrules": rules,
        "normcards": normcards,
        "runSummary": summary,
        "manifest": manifest,
        "inputSimplifyM": simplify_m,
    }


def load_layers(
    manifest: Mapping[str, Mapping[str, Any]], *, simplify_m: float = 0.0
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Rebuild the engine's ``layers`` dict from the baseline run's manifest.

    Reads each zone's recorded cache file (EPSG:28992 computation twin) —
    no network. Missing/corrupt caches degrade per zone, exactly like a
    failed fetch in the pipeline run.
    """
    layers: Dict[str, Dict[str, Any]] = {}
    degradations: List[Dict[str, Any]] = []
    for zone, entry in sorted(manifest.items()):
        cache = entry.get("cachePath")
        if not cache or not Path(cache).is_file():
            degradations.append(
                {"kind": "layer-cache-missing",
                 "error": f"zone {zone!r}: cache file {cache!r} absent — rules "
                          f"referencing it will be dropped this run"}
            )
            continue
        try:
            fc = _read_json(Path(cache))
        except (OSError, ValueError) as exc:
            degradations.append(
                {"kind": "layer-cache-corrupt",
                 "error": f"zone {zone!r}: {type(exc).__name__}: {exc}"}
            )
            continue
        layers[str(zone)] = fc
    if simplify_m and simplify_m > 0:
        layers, _notes = engine.simplify_layers(layers, simplify_m)
    return layers, degradations


def sources_prov_from_manifest(manifest: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per-zone source provenance for the engine (serviceUrl/layerId/lastChecked)."""
    return {
        zone: {
            "serviceUrl": entry.get("serviceUrl"),
            "layerId": entry.get("layerId"),
            "lastChecked": entry.get("lastChecked"),
        }
        for zone, entry in manifest.items()
    }


# --------------------------------------------------------------------------- #
# mutations
# --------------------------------------------------------------------------- #

def eligible_rules(rules: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Rules the baseline actually executed: status ``formalized``.

    Ambiguous/rejected rules are routed to V4 by the pipeline and carry no
    executable predicate — mutating them is a no-op, so they are never
    eligible (a mutation targeting one is skipped with a recorded reason).
    """
    return [dict(r) for r in rules if r.get("status") == "formalized"]


def apply_mutations(
    rules: Sequence[Mapping[str, Any]],
    mutations: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Apply ScenarioSpec mutations to a copy of the FULL rule list.

    Returns ``(new_rules, applied, skipped, unknown_rule_ids)`` where
    ``applied``/``skipped`` are report rows and ``unknown_rule_ids`` names
    authoring errors (rule ids that resolve nowhere — a V2 grounding failure,
    not a graceful skip).
    """
    by_id = {str(r.get("id")): r for r in rules}
    new_rules = [copy.deepcopy(r) for r in rules]
    new_by_id = {str(r.get("id")): r for r in new_rules}
    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    unknown: List[str] = []

    for m in mutations:
        rid = str(m.get("ruleId"))
        action = str(m.get("action"))
        base = by_id.get(rid)
        if base is None:
            unknown.append(rid)
            skipped.append({"ruleId": rid, "action": action,
                            "reason": f"unknown rule id: not in the baseline formalrules set"})
            continue
        target = new_by_id[rid]
        if base.get("status") != "formalized":
            skipped.append({
                "ruleId": rid, "action": action,
                "reason": f"rule status={base.get('status')!r}: not executed in the "
                          f"baseline (no executable predicate); nothing to mutate",
            })
            continue
        zs = target.get("zoneSelector")
        if action == "drop":
            target["status"] = "rejected"
            target["rationale"] = (
                f"scenario mutation: dropped (was {base.get('zoneSemantics')})"
            )
            applied.append({"ruleId": rid, "action": action,
                            "note": f"dropped {base.get('zoneSemantics')} rule"})
        elif action == "set_semantics":
            new_sem = str(m.get("zoneSemantics"))
            old_sem = str(base.get("zoneSemantics"))
            target["zoneSemantics"] = new_sem
            applied.append({"ruleId": rid, "action": action, "zoneSemantics": new_sem,
                            "note": f"{old_sem} -> {new_sem}"})
        elif action == "set_buffer_distance_m":
            if not isinstance(zs, dict):
                skipped.append({"ruleId": rid, "action": action,
                                "reason": "rule has no zoneSelector to buffer"})
                continue
            dist = float(m.get("bufferDistanceM"))
            old = zs.get("bufferDistanceM")
            zs["bufferDistanceM"] = dist
            applied.append({"ruleId": rid, "action": action, "bufferDistanceM": dist,
                            "note": f"bufferDistanceM {old} -> {dist} m"})
        else:  # pragma: no cover - schema constrains actions
            skipped.append({"ruleId": rid, "action": action, "reason": "unsupported action"})
    return new_rules, applied, skipped, unknown


# --------------------------------------------------------------------------- #
# execution
# --------------------------------------------------------------------------- #

def _rule_zone_ids(rule: Mapping[str, Any]) -> List[str]:
    zs = rule.get("zoneSelector") or {}
    zones = list(zs.get("zoneIds") or [])
    if zs.get("derivedFrom"):
        zones.append(zs["derivedFrom"])
    seen: set = set()
    out = []
    for z in zones:
        if z not in seen:
            seen.add(z)
            out.append(z)
    return out


def execute_rule_set(
    rules: Sequence[Mapping[str, Any]],
    layers: Mapping[str, Any],
    aoi,
    sources: Mapping[str, Any],
    *,
    scenario_id: str,
    degradations: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute the mutated formalized rules exactly like the pipeline does:
    drop rules whose zones are unavailable (recorded), retry-on-RuleError
    drop loop, then ``engine.execute_rules``. Returns (rich_zones, executed)."""
    engine_rules: List[Dict[str, Any]] = []
    for r in rules:
        if r.get("status") != "formalized":
            continue
        missing = [z for z in _rule_zone_ids(r) if z not in layers]
        if missing:
            degradations.append({
                "kind": "rule-dropped", "scenarioId": scenario_id,
                "rule": str(r.get("id") or ""),
                "error": f"zone layer(s) unavailable this run: {', '.join(missing)}",
            })
        else:
            engine_rules.append(dict(r))
    attempts = 0
    while True:
        try:
            rich = engine.execute_rules(engine_rules, layers, aoi=aoi, sources=dict(sources),
                                        payload_round_dp=6)
            return rich, engine_rules
        except engine.RuleError as exc:
            attempts += 1
            if attempts > 6:
                raise
            msg = str(exc)
            dropped = next((r for r in engine_rules if r.get("id") and r["id"] in msg), None)
            if dropped is None:
                raise
            degradations.append({"kind": "rule-dropped", "scenarioId": scenario_id,
                                 "rule": str(dropped.get("id") or ""), "error": msg})
            engine_rules.remove(dropped)


def final_and_inclusion(rich_zones: Sequence[Mapping[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    final = next((z for z in rich_zones if z.get("operation") == "final"), None)
    inclusion = next(
        (z for z in rich_zones if z.get("operation") == "intersection"),
        next((z for z in rich_zones if z.get("operation") == "inclusion_union"), None),
    )
    return final, inclusion


def _rd_from_payload(payload: Mapping[str, Any]):
    """Reproject a WGS84 GeoJSON payload back to EPSG:28992 for IoU."""
    if payload.get("type") == "GeometryCollection" and not payload.get("geometries"):
        from shapely.geometry import Polygon

        return Polygon()
    return _shp_transform(lambda x, y, z=None: _WGS84_TO_RD.transform(x, y), shape(dict(payload)))


def aoi_from_baseline(baseline: Mapping[str, Any]):
    """AOI geometry (EPSG:28992) of a baseline run, simplified at its recorded
    input tolerance — the exact input the pipeline's zone engine used."""
    aoi = shape(baseline["request"]["areaOfInterest"]["geometry"])
    tol = float(baseline.get("inputSimplifyM") or 0)
    if tol > 0:
        aoi = aoi.simplify(tol, preserve_topology=True)
    return aoi


def final_geometry_rd(rich_zones: Sequence[Mapping[str, Any]]):
    """Final zone of an engine execution as a shapely geometry in EPSG:28992
    (payload reprojected back; used for cross-run overlays and IoU)."""
    final, _incl = final_and_inclusion(rich_zones)
    if final is None:
        return None
    return _rd_from_payload(final["geometry"]["payload"])


# --------------------------------------------------------------------------- #
# the sweep
# --------------------------------------------------------------------------- #

def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_scenario_set(
    *,
    baseline: Mapping[str, Any],
    layers: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    scenario_set_id: str,
    report_id: str,
    generated_by: str = SCENARIO_AUTHOR,
    degradations: Optional[List[Dict[str, Any]]] = None,
    on_scenario_geojson=None,
    narrator=None,
) -> Dict[str, Any]:
    """Execute control + every spec; assemble the ScenarioReport dict.

    ``degradations`` (e.g. missing layer caches) seed the report's degradation
    ledger so the validated artifact includes them. ``on_scenario_geojson(
    scenario_id, rich_zones) -> str`` is called after each successful
    execution so the CLI can write the per-scenario GeoJSON and have its
    relative path recorded in the report row. ``narrator`` (seam S8) is a
    ``callable(report) -> str`` whose output is gated by the deterministic
    numeric-grounding check; the narration lands on ``report["_narrative"]``
    and its check joins the critic's V2 level (pop both in the CLI).
    """
    request = baseline["request"]
    manifest = baseline["manifest"]
    summary = baseline["runSummary"]
    rules = baseline["formalrules"]
    normcards = baseline["normcards"]
    sources = sources_prov_from_manifest(manifest)

    aoi = aoi_from_baseline(baseline)

    degradations: List[Dict[str, Any]] = list(degradations or [])
    eligible = eligible_rules(rules)

    # -- control (unmutated reproduction; deltas are measured against this) --
    control_rich, control_executed = execute_rule_set(
        eligible, layers, aoi, sources, scenario_id="CONTROL", degradations=degradations)
    control_final, control_incl = final_and_inclusion(control_rich)
    if control_final is None:
        raise ScenarioError("control execution produced no final zone — baseline unusable")
    control_area = float(control_final["areaKm2"])
    base_final = float(summary.get("headline", {}).get("finalOpportunityKm2") or 0.0)
    base_incl = summary.get("headline", {}).get("inclusionIntersectAoiKm2")
    repro_delta = control_area - base_final
    repro_rel = abs(repro_delta) / base_final if base_final else 0.0
    control_geom = _rd_from_payload(control_final["geometry"]["payload"])

    v2_unknown: List[str] = []
    v2_normcard_missing: List[str] = []
    outcomes: List[Dict[str, Any]] = []

    for spec in specs:
        contracts.validate(spec, "scenario-spec")  # V0 gate before execution
        sid = str(spec["id"])
        if spec["basis"]["type"] == "baseline":
            raise ScenarioError(
                f"spec {sid}: basis.type 'baseline' is reserved for the runner's control"
            )
        nc = spec["basis"].get("normCardId")
        if nc and not any(c.get("id") == nc for c in normcards):
            v2_normcard_missing.append(f"{sid}:{nc}")
        mutated, applied, skipped, unknown = apply_mutations(rules, spec["mutations"])
        v2_unknown.extend(f"{sid}:{rid}" for rid in unknown)
        rich, executed = execute_rule_set(
            eligible_rules(mutated), layers, aoi, sources,
            scenario_id=sid, degradations=degradations)
        final, incl = final_and_inclusion(rich)
        if final is None:
            degradations.append({"kind": "scenario-empty", "scenarioId": sid,
                                 "error": "execution produced no final zone"})
            outcomes.append({
                "scenarioId": sid, "name": spec["name"],
                "basis": spec["basis"], "proposedBy": spec["proposedBy"],
                "mutationsApplied": applied, "mutationsSkipped": skipped,
                "rulesTotal": len(eligible_rules(mutated)), "rulesExecuted": len(executed),
                "finalAreaKm2": 0.0, "inclusionIntersectAoiKm2": None,
                "deltaVsControlKm2": -control_area, "deltaVsControlPct": -100.0,
                "iouVsControl": 0.0, "geometryValid": False, "geometryFile": "",
                "status": "degraded",
            })
            continue
        geom = _rd_from_payload(final["geometry"]["payload"])
        delta = float(final["areaKm2"]) - control_area
        pct = (delta / control_area * 100.0) if control_area else None
        geom_file = ""
        if on_scenario_geojson is not None:
            geom_file = on_scenario_geojson(sid, rich)
        scen_degraded = any(d.get("scenarioId") == sid for d in degradations)
        outcomes.append({
            "scenarioId": sid, "name": spec["name"],
            "basis": spec["basis"], "proposedBy": spec["proposedBy"],
            "mutationsApplied": applied, "mutationsSkipped": skipped,
            "rulesTotal": len(eligible_rules(mutated)), "rulesExecuted": len(executed),
            "finalAreaKm2": round(float(final["areaKm2"]), 9),
            "inclusionIntersectAoiKm2": (round(float(incl["areaKm2"]), 9)
                                         if incl else None),
            "deltaVsControlKm2": round(delta, 9),
            "deltaVsControlPct": (round(pct, 6) if pct is not None else None),
            "iouVsControl": round(engine.iou(control_geom, geom), 9),
            "geometryValid": bool(final.get("geometryValid")),
            "geometryFile": geom_file,
            "status": "degraded" if scen_degraded else "ok",
        })

    control_block = {
        "finalAreaKm2": control_area,
        "inclusionIntersectAoiKm2": (round(float(control_incl["areaKm2"]), 9)
                                     if control_incl else None),
        "baselineFinalAreaKm2": base_final,
        "baselineInclusionKm2": base_incl,
        "reproductionDeltaKm2": round(repro_delta, 9),
        "reproductionRelDelta": round(repro_rel, 12),
        "reproductionWithinTolerance": repro_rel <= CONTROL_REPRODUCTION_REL_TOLERANCE,
    }
    report = {
        "id": report_id,
        "scenarioSetId": scenario_set_id,
        "baselineRunId": str(baseline.get("runId")),
        "requestId": str(request.get("id")),
        "objectType": request.get("objectType"),
        "generatedAt": utcnow(),
        "generatedBy": generated_by,
        "control": control_block,
        "scenarios": outcomes,
        "verdict": "fail",  # placeholder; set by evaluate_scenario_run below
        "validationReportFile": "validation.json",
        "degradations": degradations,
        "notes": [
            "Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; "
            "scenario specs are schema-validated contracts authored by "
            f"{generated_by}.",
            "Deltas are measured against the unmutated control re-executed over the "
            "baseline run's cached layers (same tunings), not against summary numbers.",
            "Marker semantics (attention/conditional/compensation) never alter the "
            "opportunity zone; set_semantics mutations make that policy choice "
            "explicit and visible in the delta.",
        ],
    }

    # critic first, narration second: the narrator must never see the
    # placeholder verdict ("fail", set during report construction) — a
    # qwen3.8 narration dutifully quoted that placeholder as "de
    # eindconclusie van het validatieproces is 'fail'" on a PASSING run.
    # Narrating against the final report is the only honest input.
    validation = evaluate_scenario_run(
        report=report, unknown_rule_ids=v2_unknown,
        normcard_missing=v2_normcard_missing, executed_count=len(control_executed))

    report["verdict"] = "pass" if validation["verdict"] == "pass" else "fail"

    narrative = None
    if narrator is not None:
        narrative, narration_check = narrate_report(report, narrator)
        if narration_check is not None:
            validation["levels"]["V2"]["checks"].append(narration_check)
            if narration_check["status"] == "fail":
                v2 = validation["levels"]["V2"]
                if v2["status"] == "pass":
                    v2["status"] = "fail"
                if report["verdict"] == "pass":
                    report["verdict"] = "fail"
                    validation["verdict"] = "fail"
    contracts.validate(report, "scenario-report")
    contracts.validate(validation, "validation-report")
    report["_validation"] = validation  # popped by the CLI before dumping
    report["_control_rich"] = control_rich  # idem: for the control GeoJSON
    if narrative is not None:
        report["_narrative"] = narrative
    return report


# --------------------------------------------------------------------------- #
# critic (V0–V3 deterministic + V4 pending, over the scenario artifacts)
# --------------------------------------------------------------------------- #

def evaluate_scenario_run(
    *,
    report: Mapping[str, Any],
    unknown_rule_ids: Sequence[str],
    normcard_missing: Sequence[str],
    executed_count: int,
    extra_v2_checks: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    """Scenario-run ValidationReport (validation-report contract).

    V0 set/spec/report schemas · V1 final-geometry validity · V2 basis
    grounding (normCardId resolution, mutation rule-id resolution, plus any
    seam checks such as narration grounding) · V3 control reproduction ·
    V4 human review — pending by design.
    """
    checks_v0: List[Dict[str, Any]] = [
        {"id": "v0-scenario-report-schema", "status": "pass",
         "detail": "scenario-report validated against scenario-report.schema.json"},
    ]
    checks_v1: List[Dict[str, Any]] = []
    for row in report.get("scenarios", []):
        ok = bool(row.get("geometryValid")) and row.get("status") != "degraded"
        checks_v1.append({
            "id": f"v1-final-geometry-{str(row['scenarioId']).lower()}",
            "status": "pass" if ok else "fail",
            "detail": (f"final zone geometryValid={row.get('geometryValid')}, "
                       f"status={row.get('status')}"),
            "evidenceRefs": [row["geometryFile"]] if row.get("geometryFile") else [],
        })
    checks_v2: List[Dict[str, Any]] = [
        {
            "id": "v2-mutation-rule-ids",
            "status": "fail" if unknown_rule_ids else "pass",
            "detail": (f"unknown rule ids: {', '.join(unknown_rule_ids)}"
                       if unknown_rule_ids else
                       "every mutation ruleId resolved in the baseline formalrules set "
                       "(skipped mutations carry recorded reasons)"),
        },
        {
            "id": "v2-basis-normcard-ids",
            "status": "fail" if normcard_missing else "pass",
            "detail": (f"normCardIds not in baseline normcards.json: "
                       f"{', '.join(normcard_missing)}" if normcard_missing else
                       "every norm_variance/policy_variant normCardId resolved in the "
                       "baseline run's normcards.json"),
        },
    ]
    checks_v2.extend(dict(c) for c in extra_v2_checks)
    control = report.get("control", {})
    repro_ok = bool(control.get("reproductionWithinTolerance"))
    checks_v3 = [{
        "id": "v3-control-reproduction",
        "status": "pass" if repro_ok else "fail",
        "detail": (f"control final {control.get('finalAreaKm2')} km2 vs baseline "
                   f"{control.get('baselineFinalAreaKm2')} km2 "
                   f"(rel delta {control.get('reproductionRelDelta')}, tolerance "
                   f"{CONTROL_REPRODUCTION_REL_TOLERANCE}); {executed_count} rules executed"),
    }]
    degraded = [r["scenarioId"] for r in report.get("scenarios", []) if r.get("status") == "degraded"]

    def _level(checks, note=None):
        status = "fail" if any(c["status"] == "fail" for c in checks) else "pass"
        lvl = {"status": status, "checks": checks}
        if note:
            lvl["notes"] = note
        return lvl

    levels = {
        "V0": _level(checks_v0),
        "V1": _level(checks_v1),
        "V2": _level(checks_v2),
        "V3": _level(checks_v3),
        "V4": {"status": "pending",
               "notes": "scenario choice remains a human decision; this report is "
                        "decision support, never a decision"},
    }
    hard_fail = any(lvl["status"] == "fail" for lvl in (levels["V0"], levels["V1"],
                                                        levels["V2"], levels["V3"]))
    verdict = "fail" if hard_fail else ("needs_human" if degraded else "pass")
    if degraded:
        levels["V1"]["notes"] = f"degraded scenario executions: {', '.join(degraded)}"
    return {
        "id": "VR-scenario-run",
        "artifactId": str(report.get("id", "scenario-report")),
        "artifactType": "scenario-report",
        "levels": levels,
        "verdict": verdict,
        "evidence": [
            {"ref": "scenario-report.json", "note": "the swept report this verdict gates"},
            {"ref": "validation.json", "note": "this report"},
        ],
        "evaluatorRun": SCENARIO_CRITIC_RUN,
        "evaluatedAt": utcnow(),
    }


# --------------------------------------------------------------------------- #
# narration (seam S8 — prose may only cite numbers the report contains)
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?!\w)")
_ID_RE = re.compile(r"\b(?:SC|FR|NC)-[A-Za-z0-9][A-Za-z0-9._-]*\b")
#: verdict-assertion words a narration may use ONLY in agreement with the
#: report's own verdict field (catches fabricated validation claims — a
#: qwen3.8 run asserted "de eindstatus van de validatie is 'fail'" on a
#: passing report; numbers and ids were all grounded, the claim was not)
_VERDICT_RE = re.compile(r"\b(pass|passed|fails?|failed|failing)\b", re.I)
_VERDICT_PASS_WORDS = {"pass", "passed"}
_VERDICT_FAIL_WORDS = {"fail", "fails", "failed", "failing"}


def deterministic_narrative(report: Mapping[str, Any]) -> str:
    """Ground-by-construction narration: every number is f-stringed from the
    report rows, so the grounding check below passes by construction. An LLM
    narrator (Phase B) must survive the same check: numbers only from the
    report, ids only from the report, or the narration is rejected."""
    c = report["control"]
    lines = [
        f"The unmutated control re-executes the baseline at {c['finalAreaKm2']:,.3f} km2, "
        f"reproducing the recorded {c['baselineFinalAreaKm2']:,.3f} km2 "
        f"(relative delta {c['reproductionRelDelta']:.6f}). Against that control:",
        "",
    ]
    for row in report["scenarios"]:
        b = row["basis"]
        base_txt = {
            "norm_variance": f"varies the cited rule behind {b.get('normCardId')}",
            "policy_variant": f"flips the documented choice on {b.get('normCardId')}",
            "hypothetical": "is explicitly not legally grounded",
        }.get(b["type"], "varies the rule set")
        aspect = f" ({b['variedAspect']})" if b.get("variedAspect") else ""
        lines.append(
            f"- {row['name']} ({row['scenarioId']}, {base_txt}){aspect} moves the "
            f"opportunity zone to {row['finalAreaKm2']:,.3f} km2 — "
            f"{row['deltaVsControlKm2']:+,.3f} km2 ({row['deltaVsControlPct']:+.2f}%) "
            f"versus the control, spatial agreement {row['iouVsControl']:.6f}."
        )
    lines += [
        "",
        "Every figure above comes from the scenario report rows; the deltas are "
        "measured against the re-executed control, not the baseline summary. "
        "Scenario choice remains a human decision (V4 pending by design).",
    ]
    return "\n".join(lines)


def check_narrative_grounding(narrative: str, report: Mapping[str, Any]) -> Dict[str, Any]:
    """Deterministic gate for narrations (V2 family): every numeric token in
    the prose must match a number in the serialized report (tolerance = half a
    ulp of the token's own precision), and every SC-/FR-/NC- id must resolve.
    Returns a ValidationReport check dict."""
    report_text = json.dumps(report, ensure_ascii=False, default=str)
    allowed_numbers = []
    for m in _NUMBER_RE.finditer(report_text):
        try:
            allowed_numbers.append(float(m.group(0).replace(",", "")))
        except ValueError:  # pragma: no cover
            continue
    allowed_ids = set(_ID_RE.findall(report_text))
    allowed_ids.add("CONTROL")

    problems: List[str] = []
    prose = str(narrative)
    for m in _ID_RE.finditer(prose):
        if m.group(0) not in allowed_ids:
            problems.append(f"unknown id {m.group(0)}")
    idless = _ID_RE.sub(" ", prose)
    for m in _NUMBER_RE.finditer(idless):
        token = m.group(0).replace(",", "")
        try:
            value = float(token)
        except ValueError:
            continue
        decimals = len(token.split(".")[1]) if "." in token else 0
        tol = 0.5 * (10 ** -decimals) + 1e-9
        # magnitude fold: narrations naturally state a negative delta as its
        # magnitude ("afname van 64.675 km2" for the reported -64.675); the
        # magnitude is grounded, so both signs of a reported value resolve
        if not any(abs(abs(value) - abs(a)) <= tol for a in allowed_numbers):
            problems.append(f"number {m.group(0)} not in the report")
    # verdict assertions must agree with the report (the gate may only let
    # through claims the deterministic artifact actually records)
    verdict = str(report.get("verdict") or "").strip().lower()
    allowed_verdict_words = (_VERDICT_FAIL_WORDS if verdict == "fail"
                             else _VERDICT_PASS_WORDS if verdict == "pass"
                             else set())
    if allowed_verdict_words:
        for m in _VERDICT_RE.finditer(prose):
            word = m.group(0).lower()
            if word not in allowed_verdict_words:
                problems.append(
                    f"verdict word {m.group(0)!r} contradicts the report verdict "
                    f"{verdict!r} — the verdict may only be stated as the report "
                    f"records it"
                )
    check = {
        "id": "v2-narrative-grounding",
        "status": "pass" if not problems else "fail",
        "detail": ("every number and id in the narration resolves to the report"
                   if not problems else "; ".join(problems[:12])),
    }
    return check


def narrate_report(report: Mapping[str, Any],
                   narrator=None) -> Tuple[str, Dict[str, Any]]:
    """Run a narrator (default: the deterministic one) and gate its output.

    ``narrator``: ``callable(report) -> str``. The grounding check always
    runs — a rejected narration is reported as a failed V2-family check, it
    never silently replaces the prose."""
    text = narrator(report) if narrator is not None else deterministic_narrative(report)
    return text, check_narrative_grounding(text, report)


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def report_markdown(report: Mapping[str, Any]) -> str:
    """Human-readable scenario table (mirrors decision-table.md style)."""
    c = report["control"]
    lines = [
        f"# Scenario report — {report['id']}",
        "",
        f"- baseline run: `{report['baselineRunId']}` · scenario set: `{report['scenarioSetId']}`",
        f"- control (unmutated re-execution): **{c['finalAreaKm2']:,.3f} km²** "
        f"(baseline run recorded {c['baselineFinalAreaKm2']:,.3f} km²; reproduction "
        f"Δ {c['reproductionDeltaKm2']:+.3f} km², rel {c['reproductionRelDelta']:.6f}, "
        f"tolerance {CONTROL_REPRODUCTION_REL_TOLERANCE})",
        f"- verdict: **{report['verdict']}** (V4 human review pending by design)",
        "",
        "| scenario | basis | mutations | final km² | Δ vs control | IoU | status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in report["scenarios"]:
        b = row["basis"]
        basis_txt = b["type"].replace("_", " ")
        if b.get("normCardId"):
            basis_txt += f" ({b['normCardId']})"
        if b["type"] == "hypothetical":
            basis_txt += " — *not legally grounded*"
        muts = "; ".join(
            f"{m['ruleId']}: {m['action']}"
            + (f"→{m['zoneSemantics']}" if m.get("zoneSemantics") else "")
            + (f"→{m['bufferDistanceM']:g}m" if m.get("bufferDistanceM") is not None else "")
            for m in row["mutationsApplied"]) or "—"
        if row["mutationsSkipped"]:
            muts += f" *(skipped: {len(row['mutationsSkipped'])})*"
        lines.append(
            f"| **{row['scenarioId']}** {row['name']} | {basis_txt} | {muts} "
            f"| {row['finalAreaKm2']:,.3f} | {row['deltaVsControlKm2']:+,.3f} "
            f"({row['deltaVsControlPct']:+.2f}%) | {row['iouVsControl']:.6f} "
            f"| {row['status']} |"
        )
    lines += ["", "## Control per-level validation", ""]
    if report.get("degradations"):
        lines += ["## Degradations", ""]
        for d in report["degradations"]:
            lines.append(f"- `{d.get('kind')}` {d.get('scenarioId') or ''} "
                         f"{d.get('rule') or ''}: {d['error']}")
        lines.append("")
    for note in report.get("notes", []):
        lines.append(f"> {note}")
        lines.append("")
    return "\n".join(lines)


def write_scenario_geojson(rich_zones: Sequence[Mapping[str, Any]], path: Path) -> Path:
    """Per-scenario zones GeoJSON (all emitted zones incl. the final)."""
    return cartographer.write_geojson(list(rich_zones), path)
