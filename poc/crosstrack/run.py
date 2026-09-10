#!/usr/bin/env python3
"""CLI orchestrator for the cross-track conflict overlay.

Re- executes each track's unmutated control from its baseline pipeline run
(offline, cached layers) and overlays the opportunity zones: pairwise
conflicts plus each zone's claim on shared instrument zones — most notably
the Groene contour, where the zon compensation duty (art. 6.5a lid 3) meets
the bos zoekgebied nieuwe natuur (art. 6.4). Deterministic; alters no legal
claim (V2 not_applicable); V3 verifies every control reproduces its baseline.

Usage (from the workspace root, fully offline):

    python3 poc/crosstrack/run.py                        # wind,zon,bos
    python3 poc/crosstrack/run.py --tracks zon,bos       # just the contour pair
    python3 poc/crosstrack/run.py --out /tmp/xtrack

Output: poc/crosstrack-runs/<ts>/ with crosstrack-report.json/.md,
conflicts/*.geojson, shared/<zone>/<track>.geojson, controls/<track>.geojson,
validation.json, prov.json, run_summary.json. Exit 0 only on verdict pass.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

POC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = POC_ROOT.parent
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import cartographer, crosstrack, engine, explainer, scenarios  # noqa: E402

RUN_VERSION = "poc-crosstrack-run/1.0"
OUT_ROOT = POC_ROOT / "crosstrack-runs"

#: shared instrument zones overlaid on every track's final zone
SHARED_ZONES = [
    ("groene_contour",
     "Groene contour: the bos track's zoekgebied nieuwe natuur (art. 6.4 lid 1) "
     "and simultaneously a compensation marker for zon (art. 6.5a lid 3: new "
     "nature within 25 years of panel placement) and wind (art. 6.5 lid 2 "
     "onder d: >=1:1 compensation ratio) — the verordening's own energy-vs-"
     "nature conflict zone."),
]


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump_json(path: Path, obj: Any, indent: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    return path


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_baseline_run(use_case: str) -> Path:
    runs = sorted((POC_ROOT / "runs").glob(f"*-{use_case}"))
    dirs = [p for p in runs if (p / "run_summary.json").is_file()]
    if not dirs:
        raise SystemExit(f"no pipeline run found for {use_case!r} under poc/runs/ — "
                         f"run `python3 poc/run.py --use-case {use_case}` first")
    return dirs[-1]


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tracks", default="wind,zon,bos",
                    help="comma-separated track ids (default: wind,zon,bos; "
                         "at least two)")
    ap.add_argument("--baseline", action="append", default=None, metavar="DIR",
                    help="explicit baseline run dir per track (repeatable, in "
                         "--tracks order; default: latest poc/runs/*-<track>)")
    ap.add_argument("--out", default=None,
                    help="output directory (default: poc/crosstrack-runs/<ts>)")
    ap.add_argument("--no-h3", action="store_true",
                    help="skip the H3 per-cell overlay (default: run it, "
                         "degrading gracefully when offline without cache)")
    ap.add_argument("--refresh-h3", action="store_true",
                    help="force live re-invocation of the nldt H3 processes "
                         "(ignore the poc/data/cache/h3 cache)")
    ap.add_argument("--h3-resolution", type=int, default=8,
                    help="H3 resolution for the overlay (default: 8)")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()
    tracks_arg = [t.strip() for t in args.tracks.split(",") if t.strip()]
    if len(tracks_arg) < 2:
        raise SystemExit("--tracks needs at least two track ids")
    run_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{run_ts}-{''.join(t[0] for t in tracks_arg)}-xtrack"
    out_dir = Path(args.out) if args.out else OUT_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[crosstrack] {run_id} -> {out_dir}")

    baselines_arg = args.baseline or []
    track_baselines = []
    activities: List[Dict[str, Any]] = []
    for i, uc in enumerate(tracks_arg):
        bdir = Path(baselines_arg[i]) if i < len(baselines_arg) else latest_baseline_run(uc)
        t0 = time.time()
        baseline = scenarios.load_baseline(bdir)
        layers, degrades = scenarios.load_layers(
            baseline["manifest"], simplify_m=baseline["inputSimplifyM"])
        if degrades:
            print(f"[crosstrack] WARNING {uc}: {len(degrades)} layer degradation(s)")
        track_baselines.append((uc, baseline, layers))
        activities.append({
            "id": f"control-{uc}", "label": f"Control re-execution: {uc}",
            "type": "control", "agent": crosstrack.CROSSTRACK_VERSION,
            "startedAt": utcnow(), "endedAt": utcnow(),
            "durationS": round(time.time() - t0, 3),
            "used": [str(bdir / n) for n in ("request.json", "formalrules.json",
                                             "layers.json")],
            "generated": [f"controls/{uc}.geojson"],
        })
        print(f"[crosstrack] control {uc}: baseline {bdir.name}")

    written: List[str] = []

    def on_geometry(name: str, geom, props: Dict[str, Any]) -> str:
        rel = f"{name}.geojson"
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        fc = {
            "type": "FeatureCollection",
            "name": str(props.get("name", name)),
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [{"type": "Feature", "properties": dict(props),
                          "geometry": None}],
            "properties": {"computedBy": crosstrack.CROSSTRACK_VERSION},
        }
        payload = engine.to_zone_geometry(geom, round_dp=6)[0]["payload"]
        fc["features"][0]["geometry"] = payload
        path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        written.append(rel)
        return rel

    t0 = time.time()
    report = crosstrack.run_crosstrack(
        track_baselines=track_baselines,
        shared_zones=SHARED_ZONES,
        report_id=f"XR-{run_ts}",
        on_geometry=on_geometry,
    )
    validation = report.pop("_validation")
    tracks_internal = report.pop("_tracks")
    # per-track control geojson (the inputs the conflicts were computed from)
    for t in tracks_internal:
        rel = f"controls/{t['useCase']}.geojson"
        cartographer.write_geojson(t["rich_zones"], out_dir / rel)
        written.append(rel)
    activities.append({
        "id": "overlay", "label": "Pairwise conflicts + shared-zone overlays",
        "type": "overlay", "agent": crosstrack.CROSSTRACK_VERSION,
        "startedAt": utcnow(), "endedAt": utcnow(),
        "durationS": round(time.time() - t0, 3),
        "used": [f"controls/{t['useCase']}.geojson" for t in tracks_internal],
        "generated": written,
    })

    h3_artifact = None
    if not args.no_h3:
        from pipeline import h3step

        def _h3_call(process_id, inputs):
            return h3step.call(process_id, inputs, refresh=args.refresh_h3)

        try:
            h3_artifact = crosstrack.attach_h3_overlay(
                report, tracks_internal,
                zone_id=SHARED_ZONES[0][0],
                layers=track_baselines[0][2],
                resolution=args.h3_resolution, call=_h3_call)
        except Exception as exc:  # decision support only: never fail the run
            report.setdefault("degradations", []).append(
                {"kind": "h3-error", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[crosstrack] WARNING h3 overlay degraded: {exc}")
    if h3_artifact is not None:
        dump_json(out_dir / "h3-crosstrack.json", h3_artifact, indent=1)
        written.append("h3-crosstrack.json")

    dump_json(out_dir / "crosstrack-report.json", report, indent=1)
    dump_json(out_dir / "validation.json", validation, indent=1)
    (out_dir / "crosstrack-report.md").write_text(
        crosstrack.conflict_markdown(report), encoding="utf-8")
    verdict = validation["verdict"]

    # PROV
    expl = explainer.Explainer()
    entities = []
    for uc, baseline, _layers in track_baselines:
        for n in ("request.json", "formalrules.json", "run_summary.json", "layers.json"):
            entities.append(explainer.entity_for(
                Path(baseline["runDir"]) / n, f"baseline run artifact ({uc}/{n})",
                {"useCase": uc}))
    entities.append(explainer.entity_for(out_dir / "crosstrack-report.json",
                                         "CrossTrackReport"))
    entities.append(explainer.entity_for(out_dir / "validation.json", "ValidationReport"))
    entities.append(explainer.entity_for(out_dir / "crosstrack-report.md",
                                         "CrossTrackReport (markdown)"))
    for rel in written:
        entities.append(explainer.entity_for(out_dir / rel, "overlay geometry GeoJSON"))
    prov = expl.build_prov(
        run_id=run_id, generated_at=utcnow(),
        request_id=str(track_baselines[0][1]["request"].get("id")),
        namespace="ldttoolbox:poc:crosstrack:",
        agents=[
            {"id": "orchestrator", "name": "crosstrack/run.py orchestrator",
             "version": RUN_VERSION, "role": "load tracks, dispatch overlay, gate"},
            {"id": "crosstrack-engine", "name": "Cross-track conflict overlay",
             "version": crosstrack.CROSSTRACK_VERSION,
             "role": "control replays + pairwise/shared-zone intersections "
                     "(docs/GENAI_SEAMS.md phase C base)"},
            {"id": "explainer", "name": "Explainer (PROV)",
             "version": explainer.EXPLAINER_VERSION, "role": "PROV bundle"},
        ],
        activities=activities,
        entities=entities,
        derivations=[
            {"generatedEntity": "crosstrack-report.json",
             "usedEntity": "formalrules.json",
             "note": "each track's unmutated control re-executed over cached layers"},
            {"generatedEntity": "validation.json",
             "usedEntity": "crosstrack-report.json",
             "note": "V0/V1/V3 checks; V2 not_applicable; V4 pending"},
        ],
    )
    dump_json(out_dir / "prov.json", prov, indent=1)

    artifacts = sorted(p for p in out_dir.rglob("*") if p.is_file())
    summary = {
        "runId": run_id,
        "tracks": tracks_arg,
        "generatedAt": utcnow(),
        "durationS": round(time.time() - started, 1),
        "orchestrator": RUN_VERSION,
        "engine": crosstrack.CROSSTRACK_VERSION,
        "verdict": verdict,
        "levels": {k: v["status"] for k, v in validation["levels"].items()},
        "conflicts": [{"pair": c["pair"], "areaKm2": c["areaKm2"]}
                      for c in report["conflicts"]],
        "sharedZones": report["sharedZones"],
        "degradations": report["degradations"],
        "artifacts": [{"name": str(p.relative_to(out_dir)), "path": str(p),
                       "sha256": sha256_of(p), "bytes": p.stat().st_size}
                      for p in artifacts],
    }
    dump_json(out_dir / "run_summary.json", summary, indent=1)

    print()
    print("=" * 78)
    print(f"CROSSTRACK RUN {run_id} — verdict: {verdict.upper()}")
    print("=" * 78)
    for t in report["tracks"]:
        print(f"  {t['useCase']:<6} final {t['finalAreaKm2']:>12,.3f} km2 "
              f"(reproduction rel {t['reproductionRelDelta']:.6f})")
    for c in report["conflicts"]:
        a, b = c["pair"]
        s = c["shareOfTrackFinal"]
        print(f"  conflict {a} x {b}: {c['areaKm2']:>10,.3f} km2 "
              f"({s.get(a):.2f}% of {a}, {s.get(b):.2f}% of {b})")
    for z in report["sharedZones"]:
        print(f"  shared {z['zoneId']} ({z['areaKm2']:,.3f} km2): " +
              ", ".join(f"{p['useCase']} {p['shareOfZone']:.1f}%"
                        for p in z["perTrack"]))
    print(f"  Duration {summary['durationS']}s; report: "
          f"{out_dir / 'crosstrack-report.md'}")
    print("=" * 78)
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        traceback.print_exc()
        print(f"[crosstrack] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
