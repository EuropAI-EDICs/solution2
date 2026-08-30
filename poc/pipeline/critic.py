#!/usr/bin/env python3
"""Critic / Validator for the opportunity-map PoC (plan section 3.2, agent #7).

Implements the validation levels of MULTI_AGENT_PLAN.md section 4 as
deterministic functions over the artifact set:

* **V0 syntactic**   — every artifact instance is validated against its
  published draft-2020-12 JSON Schema (``pipeline.contracts.validate``).
* **V1 geometric**   — output geometries are validity-checked (shapely
  ``is_valid``), CRS correctness (payload EPSG:4326 in NL bounds, input
  layers EPSG:28992), non-empty final zone, area sanity versus the AOI and
  the inclusion zone, and an as-served invalid-feature census per input
  layer (repairs are recorded by the engine, reported here as evidence).
* **V2 legal grounding** — every FormalRule links an existing NormCard id;
  every NormCard carries a non-empty quote + uri + article + version +
  docId; every ZoneResult ruleId traces to a formalized rule; every
  DecisionTable row links an existing NormCard; every executableRef is a
  registered deterministic engine operation. Orphans are flagged, never
  silently dropped.
* **V3 semantic re-execution** — ``engine.reexecute_independent`` (the
  geopandas second implementation) re-executes the same FormalRules; the
  pipeline's final zone must agree within IoU >= 0.98 and relative area
  delta <= 1%.
* **V4 human expert** — always ``pending`` (checkpointed HITL, plan
  section 4): the deterministic levels cannot replace the professional's
  signature.

The verdict rolls up V0-V3 only: ``fail`` if any check failed,
``needs_human`` if any check was skipped (e.g. a degraded live layer) or a
degradation was recorded, otherwise ``pass``. V4 ``pending`` is the standing
HITL checkpoint and does not block a programming-stage run; the report
always surfaces it.

No LLM at PoC runtime: every check is deterministic (plan section 5,
determinism rules). Output: ValidationReport dicts validated against
``poc/schemas/validation-report.schema.json``.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Mapping, Optional, Sequence

import shapely
from shapely.geometry import shape

try:
    from pipeline import contracts
    from pipeline.agents import ENGINE_OPERATIONS
    from pipeline import engine
except ImportError:  # pragma: no cover - direct execution inside poc/pipeline
    import contracts as contracts  # type: ignore[no-redef]
    import engine as engine  # type: ignore[no-redef]
    from agents import ENGINE_OPERATIONS  # type: ignore[no-redef]

__all__ = [
    "Critic",
    "CRITIC_VERSION",
    "V3_IOU_THRESHOLD",
    "V3_AREA_DELTA_THRESHOLD",
]

CRITIC_VERSION = "critic-validator#deterministic-v0-v3-poc1"
V3_IOU_THRESHOLD = 0.98
V3_AREA_DELTA_THRESHOLD = 0.01

# NL-ish bounds for WGS84 sanity (province Utrecht sits well inside)
NL_LON = (3.0, 7.5)
NL_LAT = (50.5, 54.0)

_ZONE_EFFECT_BY_SEMANTICS = {
    "inclusion": "included",
    "exclusion": "excluded",
    "conditional": "conditional",
    "attention": "attention",
    "compensation": "compensation",
}


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check(cid: str, status: str, detail: str = "", evidence: Optional[List[str]] = None) -> Dict[str, Any]:
    c: Dict[str, Any] = {"id": cid, "status": status}
    if detail:
        c["detail"] = detail
    if evidence:
        c["evidenceRefs"] = evidence
    return c


def _level(status: str, checks: Sequence[Mapping[str, Any]], notes: str = "") -> Dict[str, Any]:
    lvl: Dict[str, Any] = {"status": status, "checks": [dict(c) for c in checks]}
    if notes:
        lvl["notes"] = notes
    return lvl


def _rollup_level(checks: Sequence[Mapping[str, Any]]) -> str:
    statuses = [c["status"] for c in checks]
    if "fail" in statuses:
        return "fail"
    if not statuses or all(s == "skipped" for s in statuses):
        return "not_applicable"
    return "pass"


def _verdict(levels: Mapping[str, Mapping[str, Any]], degradations: Sequence[Mapping[str, Any]]) -> str:
    for name in ("V0", "V1", "V2", "V3"):
        if levels[name]["status"] == "fail":
            return "fail"
    for name in ("V0", "V1", "V2", "V3"):
        for c in levels[name].get("checks", []):
            if c["status"] == "skipped":
                return "needs_human"
    if degradations:
        return "needs_human"
    return "pass"


class Critic:
    """Deterministic evaluator-optimizer over one pipeline artifact set."""

    agent_name = "critic-validator"

    def __init__(self, run_ref: str = CRITIC_VERSION) -> None:
        self.run_ref = run_ref

    # ------------------------------------------------------------------ #
    # V0 — syntactic
    # ------------------------------------------------------------------ #

    def v0_checks(self, artifact_sets: Mapping[str, Sequence[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
        """Validate every artifact instance against its named schema."""
        checks: List[Dict[str, Any]] = []
        for type_name, (schema_name, instances) in artifact_sets.items():
            ok, failed = 0, []
            for inst in instances:
                try:
                    contracts.validate(inst, schema_name)
                    ok += 1
                except contracts.ContractError as exc:
                    failed.append(f"{(inst or {}).get('id', '?')}: {exc}")
            if failed:
                checks.append(
                    _check(
                        f"v0-schema-{type_name}",
                        "fail",
                        f"{len(failed)}/{len(instances)} artifact(s) failed schema {schema_name!r}: "
                        + "; ".join(failed[:3]),
                    )
                )
            else:
                checks.append(
                    _check(
                        f"v0-schema-{type_name}",
                        "pass",
                        f"{ok}/{len(instances)} artifact(s) valid against {schema_name}.schema.json",
                    )
                )
        return checks

    # ------------------------------------------------------------------ #
    # V1 — geometric
    # ------------------------------------------------------------------ #

    def v1_checks(
        self,
        zones: Sequence[Mapping[str, Any]],
        layers: Mapping[str, Mapping[str, Any]],
        aoi_geom_rd,
        inclusion_area_m2: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []
        if aoi_geom_rd is not None and not hasattr(aoi_geom_rd, "area"):
            aoi_geom_rd = shape(aoi_geom_rd)  # accept GeoJSON dict in EPSG:28992
        final = next((z for z in zones if z.get("operation") in ("final", "difference") and z.get("id", "").startswith(("zr-final", "ZR-final"))), None)
        final = final or next((z for z in zones if z.get("isFinal")), zones[-1] if zones else None)

        # output validity + CRS + bounds
        bad_valid, bad_crs, bad_bounds = [], [], []
        for z in zones:
            zid = z.get("id", "?")
            geom = (z.get("geometry") or {})
            payload = geom.get("payload")
            if not isinstance(payload, dict) or "type" not in payload:
                bad_valid.append(f"{zid}: no GeoJSON payload")
                continue
            g = shape(payload)
            if not g.is_valid:
                bad_valid.append(zid)
            if geom.get("crs") != "EPSG:4326":
                bad_crs.append(f"{zid}: crs={geom.get('crs')!r}")
            minx, miny, maxx, maxy = g.bounds
            if not (NL_LON[0] <= minx and maxx <= NL_LON[1] and NL_LAT[0] <= miny and maxy <= NL_LAT[1]):
                bad_bounds.append(f"{zid}: {minx:.3f},{miny:.3f},{maxx:.3f},{maxy:.3f}")
        checks.append(
            _check(
                "v1-output-geometry-valid",
                "fail" if bad_valid else "pass",
                ("invalid output geometries: " + ", ".join(bad_valid[:5])) if bad_valid
                else f"all {len(zones)} zone geometries valid (shapely is_valid)",
            )
        )
        checks.append(
            _check(
                "v1-output-crs-and-bounds",
                "fail" if (bad_crs or bad_bounds) else "pass",
                "; ".join((bad_crs + bad_bounds)[:5]) if (bad_crs or bad_bounds)
                else f"all payloads EPSG:4326 with coordinates inside NL bounds lon{NL_LON}/lat{NL_LAT}",
            )
        )

        # input layer census: CRS member + as-served invalid features
        bad_layer_crs, invalid_census = [], []
        for lid, fc in layers.items():
            crs_name = str(((fc.get("crs") or {}).get("properties") or {}).get("name", ""))
            if "28992" not in crs_name and "CRS84" not in crs_name and "4326" not in crs_name:
                bad_layer_crs.append(f"{lid}: crs member {crs_name!r}")
            n_invalid = 0
            for f in fc.get("features", []):
                g = f.get("geometry")
                if g is not None and not shape(g).is_valid:
                    n_invalid += 1
            if n_invalid:
                invalid_census.append(f"{lid}: {n_invalid}/{len(fc.get('features', []))} invalid as served (repaired+recorded by engine)")
        checks.append(
            _check(
                "v1-input-layers-crs",
                "fail" if bad_layer_crs else "pass",
                "; ".join(bad_layer_crs[:5]) if bad_layer_crs
                else f"{len(layers)} input layer(s) declare a recognised CRS member (EPSG:28992 computation CRS)",
            )
        )
        checks.append(
            _check(
                "v1-input-invalid-census",
                "pass",
                "; ".join(invalid_census) if invalid_census else "no invalid as-served features in any input layer",
                evidence=[lid for lid in layers],
            )
        )

        # final zone sanity
        if final is None:
            checks.append(_check("v1-final-zone-sanity", "fail", "no final zone in artifact set"))
        else:
            area_km2 = final.get("areaKm2") or 0.0
            problems = []
            if not final.get("geometryValid", False):
                problems.append("geometryValid flag false")
            payload = (final.get("geometry") or {}).get("payload") or {}
            if payload.get("type") == "GeometryCollection" and not payload.get("geometries"):
                problems.append("empty GeometryCollection payload")
            if area_km2 <= 0:
                problems.append(f"areaKm2={area_km2}")
            aoi_km2 = aoi_geom_rd.area / 1e6 if aoi_geom_rd is not None else None
            if aoi_km2 and area_km2 > aoi_km2 * 1.0001:
                problems.append(f"final {area_km2:.3f} km2 exceeds AOI {aoi_km2:.3f} km2")
            if inclusion_area_m2 and area_km2 > inclusion_area_m2 / 1e6 * 1.0001:
                problems.append(f"final {area_km2:.3f} km2 exceeds inclusion union {inclusion_area_m2/1e6:.3f} km2")
            checks.append(
                _check(
                    "v1-final-zone-sanity",
                    "fail" if problems else "pass",
                    "; ".join(problems) if problems
                    else f"final zone non-empty, valid, {area_km2:.3f} km2 <= AOI {aoi_km2:.3f} km2"
                    + (f" and <= inclusion union {inclusion_area_m2/1e6:.3f} km2" if inclusion_area_m2 else ""),
                    evidence=[final.get("id", "?")],
                )
            )
        return checks

    # ------------------------------------------------------------------ #
    # V2 — legal grounding
    # ------------------------------------------------------------------ #

    def v2_checks(
        self,
        normcards: Sequence[Mapping[str, Any]],
        formalrules: Sequence[Mapping[str, Any]],
        zones: Sequence[Mapping[str, Any]],
        decision_table: Optional[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []
        card_ids = {c["id"] for c in normcards}

        # rule -> card links
        orphans = [r["id"] for r in formalrules if r.get("normCardId") not in card_ids]
        unknown_related = sorted(
            {rel for r in formalrules for rel in (r.get("relatedNormCardIds") or []) if rel not in card_ids}
        )
        checks.append(
            _check(
                "v2-rule-card-linkage",
                "fail" if (orphans or unknown_related) else "pass",
                (f"rules without an existing NormCard: {orphans}; unknown relatedNormCardIds: {unknown_related}")
                if (orphans or unknown_related)
                else f"all {len(formalrules)} FormalRule(s) link an existing NormCard (cite-or-abstain chain intact)",
            )
        )

        # card citation completeness
        bad_cites = []
        for c in normcards:
            src = c.get("source") or {}
            problems = []
            if len(str(src.get("quote") or "")) < 20:
                problems.append("quote<20")
            uri = str(src.get("uri") or "")
            if not (uri.startswith("http://") or uri.startswith("https://")):
                problems.append("uri")
            if len(str(src.get("article") or "")) < 2:
                problems.append("article")
            if len(str(src.get("version") or "")) < 4:
                problems.append("version")
            if not str(src.get("docId") or "").startswith("S"):
                problems.append("docId")
            if problems:
                bad_cites.append(f"{c.get('id')}: {','.join(problems)}")
        checks.append(
            _check(
                "v2-card-citations",
                "fail" if bad_cites else "pass",
                "; ".join(bad_cites[:5]) if bad_cites
                else f"all {len(normcards)} NormCard(s) carry docId+article+version+verbatim quote+uri",
            )
        )

        # zone ruleIds trace to formalized rules
        formalized_ids = {r["id"] for r in formalrules if r.get("status") == "formalized"}
        dangling_zone_rules = sorted(
            {rid for z in zones for rid in (z.get("ruleIds") or []) if rid not in formalized_ids}
        )
        checks.append(
            _check(
                "v2-zone-rule-traceability",
                "fail" if dangling_zone_rules else "pass",
                f"zone ruleIds not formalized: {dangling_zone_rules}" if dangling_zone_rules
                else f"every zone ruleId traces to a formalized rule ({len(formalized_ids)} available)",
            )
        )

        # decision table linkage
        if decision_table is None:
            checks.append(_check("v2-decision-table-linkage", "skipped", "no decision table in artifact set"))
        else:
            bad_rows = [
                str(i) for i, row in enumerate(decision_table.get("rows", []))
                if row.get("normCardId") not in card_ids
            ]
            checks.append(
                _check(
                    "v2-decision-table-linkage",
                    "fail" if bad_rows else "pass",
                    f"rows with unknown normCardId: {bad_rows}" if bad_rows
                    else f"all {len(decision_table.get('rows', []))} decision-table row(s) link an existing NormCard",
                )
            )

        # executable refs registered
        bad_refs = sorted(
            {r["id"] for r in formalrules if r.get("executableRef") not in ENGINE_OPERATIONS}
        )
        checks.append(
            _check(
                "v2-executable-refs-registered",
                "fail" if bad_refs else "pass",
                f"unregistered executableRef in: {bad_refs}" if bad_refs
                else f"all executableRefs are registered deterministic engine operations ({len(ENGINE_OPERATIONS)} registered)",
            )
        )
        return checks

    # ------------------------------------------------------------------ #
    # V3 — semantic re-execution
    # ------------------------------------------------------------------ #

    def v3_checks(
        self,
        rules: Sequence[Mapping[str, Any]],
        layers: Mapping[str, Mapping[str, Any]],
        aoi,
        final_zone: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []
        try:
            independent = engine.reexecute_independent(list(rules), dict(layers), aoi=aoi)
        except Exception as exc:  # pragma: no cover - engine failure is a hard V3 fail
            checks.append(_check("v3-reexecution-agreement", "fail", f"reexecute_independent raised: {exc}"))
            return checks

        pipeline_area = float(final_zone.get("areaM2") or final_zone.get("areaKm2", 0) * 1e6)
        indep_area = float(independent.area)
        denom = max(pipeline_area, indep_area, 1e-12)
        rel_delta = abs(pipeline_area - indep_area) / denom
        iou = engine.iou(independent, self._final_rd_geometry(final_zone))
        detail = (
            f"independent geopandas re-execution of {len(rules)} rule(s): "
            f"pipeline {pipeline_area/1e6:.3f} km2 vs independent {indep_area/1e6:.3f} km2; "
            f"relative area delta {rel_delta:.3e} (threshold {V3_AREA_DELTA_THRESHOLD}); "
            f"IoU {iou:.6f} (threshold {V3_IOU_THRESHOLD})"
        )
        ok = (iou >= V3_IOU_THRESHOLD) and (rel_delta <= V3_AREA_DELTA_THRESHOLD)
        checks.append(_check("v3-reexecution-agreement", "pass" if ok else "fail", detail))
        return checks

    def _final_rd_geometry(self, final_zone: Mapping[str, Any]):
        payload = (final_zone.get("geometry") or {}).get("payload")
        geom = shape(payload)
        if geom.is_empty:
            return geom
        from pyproj import Transformer
        from shapely.ops import transform as _t
        from shapely.validation import make_valid

        tr = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
        rd = _t(lambda x, y, z=None: tr.transform(x, y), geom)
        # the WGS84 round-trip (and payload coordinate rounding) can create
        # micro-invalidities; repair before overlay comparisons so the check
        # measures semantic disagreement, not rounding artifacts
        if not rd.is_valid:
            rd = make_valid(rd)
            rd, _ = engine.polygonal(rd)
        return rd

    # ------------------------------------------------------------------ #
    # report assembly
    # ------------------------------------------------------------------ #

    def build_report(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        levels: Mapping[str, Mapping[str, Any]],
        degradations: Sequence[Mapping[str, Any]] = (),
        evidence: Optional[Sequence[Mapping[str, Any]]] = None,
        report_id: Optional[str] = None,
        evaluated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        for name in ("V0", "V1", "V2", "V3"):
            if name not in levels:
                levels = dict(levels)
                levels[name] = _level("not_applicable", [], f"{name} not evaluated for this artifact")
        levels = dict(levels)
        levels.setdefault("V4", _level("pending", [], "V4 human-expert validation (HITL) is pending by design; the deterministic PoC cannot sign it."))
        report = {
            "id": report_id or f"VR-{artifact_type}-{int(_dt.datetime.now(_dt.timezone.utc).timestamp())}",
            "artifactId": artifact_id,
            "artifactType": artifact_type,
            "levels": levels,
            "verdict": _verdict(levels, degradations),
            "evaluatorRun": self.run_ref,
            "evaluatedAt": evaluated_at or _utcnow_iso(),
        }
        if evidence:
            report["evidence"] = [dict(e) for e in evidence]
        contracts.validate(report, "validation-report")
        return report

    def evaluate_run(
        self,
        *,
        request: Mapping[str, Any],
        normcards: Sequence[Mapping[str, Any]],
        formalrules: Sequence[Mapping[str, Any]],
        zones: Sequence[Mapping[str, Any]],
        decision_table: Optional[Mapping[str, Any]],
        layers: Mapping[str, Mapping[str, Any]],
        aoi,
        engine_rules: Sequence[Mapping[str, Any]],
        final_zone: Mapping[str, Any],
        inclusion_area_m2: Optional[float] = None,
        degradations: Sequence[Mapping[str, Any]] = (),
        run_id: str = "run",
        evaluated_at: Optional[str] = None,
        track: str = "wind",
    ) -> List[Dict[str, Any]]:
        """Evaluate the full artifact set; returns schema-valid ValidationReports.

        One report per artifact set (request, norm-card-set, formal-rule-set,
        zone-result-set, decision-table) plus the pipeline-run report that
        carries V1/V3 over the whole computation.
        """
        v0 = self.v0_checks(
            {
                "opportunity-map-request": ("opportunity-map-request", [request]),
                "norm-card": ("norm-card", list(normcards)),
                "formal-rule": ("formal-rule", list(formalrules)),
                "zone-result": ("zone-result", list(zones)),
                "decision-table": ("decision-table", [decision_table] if decision_table else []),
            }
        )
        v1 = self.v1_checks(zones, layers, aoi, inclusion_area_m2)
        v2 = self.v2_checks(normcards, formalrules, zones, decision_table)
        v3 = self.v3_checks(engine_rules, layers, aoi, final_zone)

        reports = [
            self.build_report(
                artifact_id=str(request.get("id", "request")),
                artifact_type="opportunity-map-request",
                levels={"V0": _level(_rollup_level([v0[0]]), [v0[0]])},
                degradations=degradations,
                report_id=f"VR-{run_id}-request",
                evaluated_at=evaluated_at,
            ),
            self.build_report(
                artifact_id=f"normcards-{track}",
                artifact_type="norm-card-set",
                levels={"V0": _level(_rollup_level([v0[1]]), [v0[1]]), "V2": _level(_rollup_level(v2[1:2]), v2[1:2])},
                degradations=degradations,
                report_id=f"VR-{run_id}-normcards",
                evaluated_at=evaluated_at,
            ),
            self.build_report(
                artifact_id=f"formalrules-{track}",
                artifact_type="formal-rule-set",
                levels={
                    "V0": _level(_rollup_level([v0[2]]), [v0[2]]),
                    "V2": _level(_rollup_level(v2[0:1] + v2[4:5]), v2[0:1] + v2[4:5]),
                },
                degradations=degradations,
                report_id=f"VR-{run_id}-formalrules",
                evaluated_at=evaluated_at,
            ),
            self.build_report(
                artifact_id="zones",
                artifact_type="zone-result-set",
                levels={"V0": _level(_rollup_level([v0[3]]), [v0[3]]), "V1": _level(_rollup_level(v1), v1)},
                degradations=degradations,
                report_id=f"VR-{run_id}-zones",
                evaluated_at=evaluated_at,
            ),
            self.build_report(
                artifact_id=str(decision_table.get("id", "decision-table")) if decision_table else "decision-table",
                artifact_type="decision-table",
                levels={
                    "V0": _level(_rollup_level([v0[4]]), [v0[4]]) if decision_table
                    else _level("not_applicable", [], "no decision table produced"),
                    "V2": _level(_rollup_level(v2[3:4]), v2[3:4]) if decision_table
                    else _level("not_applicable", [], "no decision table produced"),
                },
                degradations=degradations,
                report_id=f"VR-{run_id}-decisiontable",
                evaluated_at=evaluated_at,
            ),
            self.build_report(
                artifact_id=run_id,
                artifact_type="pipeline-run",
                levels={
                    "V0": _level(_rollup_level(v0), v0),
                    "V1": _level(_rollup_level(v1), v1),
                    "V2": _level(_rollup_level(v2), v2),
                    "V3": _level(_rollup_level(v3), v3),
                },
                degradations=degradations,
                evidence=[
                    {"ref": str(request.get("id", "request")), "note": "OpportunityMapRequest"},
                    {"ref": f"normcards-{track}", "note": f"{len(normcards)} NormCards"},
                    {"ref": f"formalrules-{track}", "note": f"{len(formalrules)} FormalRules"},
                    {"ref": "zones", "note": f"{len(zones)} ZoneResults"},
                ]
                + ([{"ref": str(decision_table.get("id")), "note": "DecisionTable"}] if decision_table else []),
                report_id=f"VR-{run_id}-pipeline",
                evaluated_at=evaluated_at,
            ),
        ]
        return reports
