#!/usr/bin/env python3
"""Cross-track conflict overlay for the opportunity-map PoC (deterministic).

docs/GENAI_SEAMS.md phase C named "cross-track conflict discovery (zon
compensation vs bos zoekgebied overlap)" — this module is its deterministic
base, built entirely on the scenario plane's replay machinery:

* for every track, re-execute the **unmutated control** from its baseline run
  (cached layers, recorded tunings, offline — the exact path the scenario
  sweep uses for its V3 reproduction check);
* intersect the tracks' final opportunity zones **pairwise** (where do two
  land-use claims stand open on the same ground?);
* intersect each final zone with **shared instrument zones** — most notably
  the Groene contour, which the zon track carries as an art. 6.5a lid 3
  compensation marker while the bos track *is* the contour (zoekgebied nieuwe
  natuur, art. 6.4): the energy-vs-nature conflict is a property of the
  verordening itself, and this overlay quantifies it.

No legal claim is added, dropped or mutated: every input is a validated
artifact of a canonical pipeline run, so V2 (legal grounding) is
``not_applicable`` by design and V3 verifies each control reproduces its
baseline. The emitted conflicts are decision support: they show where the
programming stage must arbitrate between open claims, not what is allowed.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from pipeline import contracts, engine, scenarios

__all__ = [
    "CROSSTRACK_VERSION",
    "CROSSTRACK_RUN",
    "CrossTrackError",
    "attach_h3_overlay",
    "conflict_markdown",
    "run_crosstrack",
    "track_control",
    "union_zone",
]

CROSSTRACK_VERSION = "poc-crosstrack-engine/0.1"
CROSSTRACK_RUN = "crosstrack-orchestrator#poc-v0.1"


class CrossTrackError(ValueError):
    """Raised for crosstrack inputs the overlay refuses to guess about."""


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# per-track control replay (same path as the scenario sweep's control)
# --------------------------------------------------------------------------- #

def track_control(
    baseline: Mapping[str, Any],
    layers: Mapping[str, Any],
    *,
    degradations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Re-execute one track's unmutated rule set; returns final geometry (RD)
    plus the reproduction numbers the V3 check needs."""
    request = baseline["request"]
    aoi = scenarios.aoi_from_baseline(baseline)
    sources = scenarios.sources_prov_from_manifest(baseline["manifest"])
    eligible = scenarios.eligible_rules(baseline["formalrules"])
    rich, executed = scenarios.execute_rule_set(
        eligible, layers, aoi, sources, scenario_id="CROSS-CONTROL",
        degradations=degradations)
    final, incl = scenarios.final_and_inclusion(rich)
    if final is None:
        raise CrossTrackError(
            f"track {baseline.get('runId')!r}: control execution produced no "
            f"final zone — baseline unusable for the overlay"
        )
    geom = scenarios.final_geometry_rd(rich)
    summary = baseline["runSummary"]
    base_final = float(summary.get("headline", {}).get("finalOpportunityKm2") or 0.0)
    rel = (abs(float(final["areaKm2"]) - base_final) / base_final) if base_final else 0.0
    return {
        "useCase": summary.get("useCase") or str(baseline.get("runId", "")).rsplit("-", 1)[-1],
        "runId": str(baseline.get("runId")),
        "requestId": str(request.get("id")),
        "objectType": request.get("objectType"),
        "finalAreaKm2": round(float(final["areaKm2"]), 9),
        "inclusionIntersectAoiKm2": (round(float(incl["areaKm2"]), 9) if incl else None),
        "baselineFinalAreaKm2": base_final,
        "reproductionRelDelta": round(rel, 12),
        "reproductionWithinTolerance": rel <= scenarios.CONTROL_REPRODUCTION_REL_TOLERANCE,
        "geometry": geom,
        "rulesExecuted": len(executed),
        "rich_zones": rich,
    }


def union_zone(layers: Mapping[str, Any], zone_id: str):
    """Union of one fetched zone layer's features (EPSG:28992), validity-repaired."""
    fc = layers.get(zone_id)
    if fc is None:
        raise CrossTrackError(f"shared zone {zone_id!r} was not fetched in any track")
    geoms = []
    for f in fc.get("features", []):
        g = f.get("geometry")
        if g is None:
            continue
        g = shape(g)
        if not g.is_valid:
            g = make_valid(g)
        g, _dropped = engine.polygonal(g)
        geoms.append(g)
    if not geoms:
        raise CrossTrackError(f"shared zone {zone_id!r} carries no features")
    u = unary_union(geoms)
    if not u.is_valid:
        u = make_valid(u)
    u, _dropped = engine.polygonal(u)
    return u


# --------------------------------------------------------------------------- #
# H3 per-cell conflict overlay (spec example 7.1; degradable decision support)
# --------------------------------------------------------------------------- #

def attach_h3_overlay(
    report: Dict[str, Any],
    tracks: Sequence[Mapping[str, Any]],
    *,
    zone_id: str,
    layers: Mapping[str, Any],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Attach the per-cell H3 conflict overlay (spec example 7.1).

    ``call(process_id, inputs) -> outputs`` is the poc h3step bridge; when
    None (offline, no fixtures) the overlay degrades to a recorded
    degradation and the report stays valid. Returns the artifact dict for
    ``h3-crosstrack.json`` or None. Polygon headline numbers remain
    authoritative — this layer only localises them.
    """
    if call is None:
        report.setdefault("degradations", []).append(
            {"kind": "h3-unavailable", "zoneId": zone_id,
             "error": "no H3 process client provided (offline run)"})
        return None
    contour = union_zone(layers, zone_id)
    contour_payload = engine.to_zone_geometry(contour, round_dp=6)[0]["payload"]

    def _fc(payload):
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": payload}]}

    cov = call("h3-polygon-to-cells",
               {"polygon": _fc(contour_payload), "resolution": resolution}
               )["coverage"]
    cover = {r["cell"]: r["coverageFraction"] for r in cov["cells"]}
    area = {r["cell"]: r["cellAreaM2"] for r in cov["cells"]}

    conflict: Dict[str, float] = {}
    zon = next((t for t in tracks if t.get("useCase") == "zon"), None)
    if zon is not None:
        zon_payload = engine.to_zone_geometry(zon["geometry"],
                                              round_dp=6)[0]["payload"]
        zcov = call("h3-polygon-to-cells",
                    {"polygon": _fc(zon_payload), "resolution": resolution,
                     "restrictCells": sorted(cover)})["coverage"]
        conflict = {r["cell"]: r["coverageFraction"] for r in zcov["cells"]}

    rows = [{"cell": c, "inZoneFraction": cover[c],
             "conflictFraction": round(conflict.get(c, 0.0), 6),
             "cellAreaM2": area[c]} for c in sorted(cover)]
    num = sum(r["inZoneFraction"] * r["conflictFraction"] * r["cellAreaM2"]
              for r in rows)
    den = sum(r["inZoneFraction"] * r["cellAreaM2"] for r in rows)
    weighted = round(num / den * 100.0, 3) if den else None

    artifact = {
        "zoneId": zone_id, "resolution": resolution, "cells": rows,
        "weightedConflictSharePct": weighted,
        "computedBy": CROSSTRACK_VERSION,
        "notes": [
            "conflictFraction = share of each contour cell's area that is "
            "simultaneously open to the zon track's final zone (planar "
            "EPSG:28992); polygon headline numbers remain authoritative.",
        ],
    }
    report["h3Overlay"] = {
        "zoneId": zone_id, "resolution": resolution, "cells": len(rows),
        "conflictCells": sum(1 for r in rows if r["conflictFraction"] > 0),
        "weightedConflictSharePct": weighted,
        "artifactFile": "h3-crosstrack.json",
    }
    contracts.validate(report, "crosstrack-report")
    return artifact


# --------------------------------------------------------------------------- #
# the overlay
# --------------------------------------------------------------------------- #

def _geojson_fc(geom_rd, properties: Mapping[str, Any]) -> Dict[str, Any]:
    payload = engine.to_zone_geometry(geom_rd, round_dp=6)[0]["payload"]
    return {
        "type": "FeatureCollection",
        "name": str(properties.get("name", "crosstrack")),
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [{"type": "Feature", "properties": dict(properties),
                      "geometry": payload}],
        "properties": {"computedBy": CROSSTRACK_VERSION},
    }


def run_crosstrack(
    *,
    track_baselines: Sequence[Tuple[str, Mapping[str, Any], Mapping[str, Any]]],
    shared_zones: Sequence[Tuple[str, str]],
    report_id: str,
    on_geometry=None,
) -> Dict[str, Any]:
    """Run the cross-track overlay.

    ``track_baselines``: ``(useCase, baseline, layers)`` per track (layers as
    rebuilt from the baseline manifest). ``shared_zones``:
    ``(zoneId, note)`` instrument zones present in the tracks' fetched layers.
    ``on_geometry(name, geometry, properties) -> str`` writes each emitted
    geometry and returns its relative path for the report.
    """
    if len(track_baselines) < 2:
        raise CrossTrackError("crosstrack needs at least two tracks")
    degradations: List[Dict[str, Any]] = []
    tracks: List[Dict[str, Any]] = []

    def _emit(name: str, geom, props: Dict[str, Any]) -> str:
        if on_geometry is not None:
            return on_geometry(name, geom, props)
        return ""

    for use_case, baseline, layers in track_baselines:
        ctl = track_control(baseline, layers, degradations=degradations)
        ctl["useCase"] = use_case
        tracks.append(ctl)

    by_uc = {t["useCase"]: t for t in tracks}
    if len(by_uc) != len(tracks):
        raise CrossTrackError("duplicate use cases in the track list")

    # -- pairwise conflicts ---------------------------------------------------
    conflicts: List[Dict[str, Any]] = []
    ordered = [t for t in tracks]
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            a, b = ordered[i], ordered[j]
            inter = a["geometry"].intersection(b["geometry"])
            if not inter.is_valid:
                inter = make_valid(inter)
            inter, _dropped = engine.polygonal(inter)
            area = inter.area / 1e6
            share = {
                a["useCase"]: (round(area / a["finalAreaKm2"] * 100, 6)
                               if a["finalAreaKm2"] else None),
                b["useCase"]: (round(area / b["finalAreaKm2"] * 100, 6)
                               if b["finalAreaKm2"] else None),
            }
            gfile = _emit(
                f"conflicts/{a['useCase']}-x-{b['useCase']}", inter,
                {"name": f"{a['useCase']} x {b['useCase']} conflict",
                 "pair": [a["useCase"], b["useCase"]],
                 "areaKm2": round(area, 9), "crs": "EPSG:4326"})
            conflicts.append({
                "pair": [a["useCase"], b["useCase"]],
                "areaKm2": round(area, 9),
                "shareOfTrackFinal": share,
                "geometryFile": gfile,
            })

    # -- shared instrument zones ----------------------------------------------
    shared_blocks: List[Dict[str, Any]] = []
    first_layers = track_baselines[0][2]
    for zone_id, note in shared_zones:
        try:
            zone_geom = union_zone(first_layers, zone_id)
        except CrossTrackError:
            # fall back to any track's layers that fetched it
            for _uc, _b, layers in track_baselines[1:]:
                if zone_id in layers:
                    zone_geom = union_zone(layers, zone_id)
                    break
            else:
                degradations.append({"kind": "shared-zone-missing", "zoneId": zone_id,
                                     "error": "zone not fetched by any track"})
                continue
        zone_area = zone_geom.area / 1e6
        per_track = []
        for t in tracks:
            overlap = t["geometry"].intersection(zone_geom)
            if not overlap.is_valid:
                overlap = make_valid(overlap)
            overlap, _dropped = engine.polygonal(overlap)
            o_area = overlap.area / 1e6
            gfile = _emit(
                f"shared/{zone_id}/{t['useCase']}", overlap,
                {"name": f"{t['useCase']} final \u2229 {zone_id}",
                 "useCase": t["useCase"], "zoneId": zone_id,
                 "overlapKm2": round(o_area, 9), "crs": "EPSG:4326"})
            per_track.append({
                "useCase": t["useCase"],
                "overlapKm2": round(o_area, 9),
                "shareOfZone": (round(o_area / zone_area * 100, 6) if zone_area else None),
                "shareOfTrackFinal": (round(o_area / t["finalAreaKm2"] * 100, 6)
                                      if t["finalAreaKm2"] else None),
                "geometryFile": gfile,
            })
        shared_blocks.append({
            "zoneId": zone_id,
            "areaKm2": round(zone_area, 9),
            "perTrack": per_track,
            "note": note,
        })

    report = {
        "id": report_id,
        "generatedAt": utcnow(),
        "generatedBy": CROSSTRACK_RUN,
        "tracks": [
            {k: v for k, v in t.items()
             if k not in ("geometry", "rich_zones", "runId", "rulesExecuted")}
            | {"baselineRunId": t["runId"]}
            for t in tracks
        ],
        "conflicts": conflicts,
        "sharedZones": shared_blocks,
        "verdict": "fail",  # placeholder; set below after validation
        "validationReportFile": "validation.json",
        "degradations": degradations,
        "notes": [
            "Deterministic cross-track overlay (docs/GENAI_SEAMS.md phase C base): "
            "each track's unmutated control re-executed from its baseline run; no "
            "legal claim is added, dropped or mutated (V2 not_applicable by design).",
            "A conflict area is ground on which two tracks' opportunity zones are "
            "both open under the current verordening — the programming stage must "
            "arbitrate; this overlay quantifies, never decides.",
        ],
    }
    validation = _evaluate(report, tracks)
    report["verdict"] = "pass" if validation["verdict"] == "pass" else "fail"
    contracts.validate(report, "crosstrack-report")
    contracts.validate(validation, "validation-report")
    report["_validation"] = validation
    report["_tracks"] = tracks  # for the CLI (PROV / control geojson); popped
    return report


def _evaluate(report: Mapping[str, Any], tracks: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    checks_v0 = [{
        "id": "v0-crosstrack-report-schema", "status": "pass",
        "detail": "report validated against crosstrack-report.schema.json",
    }]
    checks_v1 = [{
        "id": "v1-geometry-validity", "status": "pass",
        "detail": f"{len(report['conflicts'])} conflict(s) + "
                  f"{sum(len(z['perTrack']) for z in report['sharedZones'])} "
                  f"shared-zone overlap(s) emitted as valid WGS84 payloads",
    }]
    checks_v3 = []
    for t in tracks:
        ok = bool(t["reproductionWithinTolerance"])
        checks_v3.append({
            "id": f"v3-control-reproduction-{t['useCase']}",
            "status": "pass" if ok else "fail",
            "detail": (f"{t['useCase']}: control final {t['finalAreaKm2']} km2 vs "
                       f"baseline {t['baselineFinalAreaKm2']} km2 (rel "
                       f"{t['reproductionRelDelta']}, tolerance "
                       f"{scenarios.CONTROL_REPRODUCTION_REL_TOLERANCE})"),
        })

    def _level(checks, note=None):
        lvl = {"status": "fail" if any(c["status"] == "fail" for c in checks) else "pass",
               "checks": checks}
        if note:
            lvl["notes"] = note
        return lvl

    levels = {
        "V0": _level(checks_v0),
        "V1": _level(checks_v1),
        "V2": {"status": "not_applicable",
               "notes": "the overlay alters no legal claims: every input is a "
                        "validated artifact of a canonical pipeline run"},
        "V3": _level(checks_v3),
        "V4": {"status": "pending",
               "notes": "arbitrating between open claims on conflicting ground is "
                        "a human programming-stage decision"},
    }
    hard_fail = any(levels[k]["status"] == "fail" for k in ("V0", "V1", "V3"))
    return {
        "id": "VR-crosstrack-run",
        "artifactId": str(report.get("id", "crosstrack-report")),
        "artifactType": "scenario-report",
        "levels": levels,
        "verdict": "fail" if hard_fail else "pass",
        "evidence": [{"ref": "crosstrack-report.json",
                      "note": "the overlay report this verdict gates"}],
        "evaluatorRun": CROSSTRACK_RUN,
        "evaluatedAt": utcnow(),
    }


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def conflict_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Cross-track conflict report — {report['id']}",
        "",
        "| track | baseline run | final km² | reproduction rel Δ |",
        "|---|---|---:|---:|",
    ]
    for t in report["tracks"]:
        lines.append(f"| {t['useCase']} | {t['baselineRunId']} | "
                     f"{t['finalAreaKm2']:,.3f} | {t['reproductionRelDelta']:.6f} |")
    if report["conflicts"]:
        lines += ["", "## Pairwise conflicts (open on the same ground)", "",
                  "| pair | conflict km² | share of each track's zone |",
                  "|---|---:|---|"]
        for c in report["conflicts"]:
            a, b = c["pair"]
            share = c["shareOfTrackFinal"]
            lines.append(f"| {a} × {b} | {c['areaKm2']:,.3f} | "
                         f"{a} {share.get(a):.2f}% · {b} {share.get(b):.2f}% |")
    for z in report["sharedZones"]:
        lines += ["", f"## Shared zone: `{z['zoneId']}` ({z['areaKm2']:,.3f} km²)",
                  "", f"> {z['note']}", "",
                  "| track | overlap km² | share of zone | share of track zone |",
                  "|---|---:|---:|---:|"]
        for pt in z["perTrack"]:
            lines.append(
                f"| {pt['useCase']} | {pt['overlapKm2']:,.3f} | "
                f"{pt['shareOfZone']:.2f}% | {pt['shareOfTrackFinal']:.2f}% |")
    if report.get("degradations"):
        lines += ["", "## Degradations", ""]
        for d in report["degradations"]:
            lines.append(f"- `{d['kind']}` {d.get('zoneId') or d.get('useCase') or ''}: "
                         f"{d['error']}")
    if report.get("h3Overlay"):
        h = report["h3Overlay"]
        lines += ["", f"## H3 overlay: `{h['zoneId']}` at resolution {h['resolution']}", "",
                  f"{h['conflictCells']} of {h['cells']} cells carry zon conflict; "
                  f"coverage-weighted conflict share {h['weightedConflictSharePct']}%. "
                  f"Per-cell detail: `{h['artifactFile']}` (decision support; "
                  "polygon headline numbers remain authoritative)."]
    lines.append("")
    for note in report.get("notes", []):
        lines.append(f"> {note}")
    lines.append("")
    return "\n".join(lines)
