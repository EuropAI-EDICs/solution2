#!/usr/bin/env python3
"""Cartographer serialization for the opportunity-map PoC (track B, file 3/4).

Turns the engine's ``ZoneResult[]`` into deliverables:

* ``zones.geojson`` — WGS84 (RFC 7946) FeatureCollection, one Feature per
  ZoneResult with rule/operation/area/provenance properties;
* ``zones.gml`` — GML via the ``ogr2ogr`` CLI (``-f "GML"``), with graceful
  degradation when ogr2ogr is missing or fails (returns ``{"ok": False, ...}``
  instead of raising; paper B's GML interop goal B2);
* a self-contained HTML-report input dict — layer metadata (from the source
  registry), zone statistics, provenance steps and output paths — ready for
  a Jinja2 template (the Explainer/HTML report owns the template itself).

CLI::

    python3 poc/pipeline/cartographer.py poc/output/zones.json \
        [--out-dir poc/output]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = [
    "zones_to_feature_collection",
    "write_geojson",
    "write_gml",
    "build_report_input",
    "main",
]

CARTOGRAPHER_VERSION = "poc-cartographer/0.1"
OGR2OGR_CANDIDATES = (
    "/opt/homebrew/bin/ogr2ogr",
    "/usr/local/bin/ogr2ogr",
    "/usr/bin/ogr2ogr",
)


def _utcnow_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_ogr2ogr():
    env = os.environ.get("OGR2OGR_PATH")
    if env and Path(env).exists():
        return env
    for cand in OGR2OGR_CANDIDATES:
        if Path(cand).exists():
            return cand
    return shutil.which("ogr2ogr")


# --------------------------------------------------------------------------- #
# GeoJSON
# --------------------------------------------------------------------------- #

def zones_to_feature_collection(zones):
    """ZoneResult[] -> WGS84 GeoJSON FeatureCollection (provenance preserved
    as feature properties; geometry payloads already carry EPSG:4326)."""
    features = []
    for i, z in enumerate(zones):
        props = {
            k: v for k, v in z.items()
            if k not in ("geometry",) and isinstance(v, (str, int, float, bool, list, type(None)))
        }
        props.setdefault("id", z.get("id", f"zone-{i}"))
        features.append(
            {
                "type": "Feature",
                "id": props["id"],
                "properties": props,
                "geometry": (z.get("geometry") or {}).get("payload")
                or {"type": "GeometryCollection", "geometries": []},
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "zones",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
        "properties": {
            "generatedBy": CARTOGRAPHER_VERSION,
            "generatedAt": _utcnow_iso(),
            "zoneCount": len(features),
        },
    }


def write_geojson(zones, path):
    """Write ZoneResult[] to a WGS84 zones.geojson; returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fc = zones_to_feature_collection(zones)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


# --------------------------------------------------------------------------- #
# GML (ogr2ogr subprocess, graceful degradation)
# --------------------------------------------------------------------------- #

def write_gml(geojson_path, gml_path=None, ogr2ogr_path=None):
    """Convert a WGS84 zones.geojson to GML via ogr2ogr.

    Graceful degradation: returns a result dict and never raises when the
    binary is missing or the conversion fails — the pipeline continues with
    GeoJSON only and records the reason.
    """
    geojson_path = Path(geojson_path)
    if gml_path is None:
        gml_path = geojson_path.with_suffix(".gml")
    else:
        gml_path = Path(gml_path)
    binary = ogr2ogr_path or _find_ogr2ogr()
    result = {
        "ok": False,
        "path": str(gml_path),
        "tool": binary,
        "error": None,
        "command": None,
    }
    if binary is None:
        result["error"] = (
            "ogr2ogr not found (checked OGR2OGR_PATH, "
            + ", ".join(OGR2OGR_CANDIDATES)
            + ", PATH) — GML export skipped, GeoJSON output remains authoritative"
        )
        return result
    if not geojson_path.exists():
        result["error"] = f"input GeoJSON not found: {geojson_path}"
        return result
    gml_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(binary), "-f", "GML", str(gml_path), str(geojson_path)]
    result["command"] = " ".join(cmd)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        result["error"] = "ogr2ogr timed out after 300 s"
        return result
    except OSError as exc:
        result["error"] = f"ogr2ogr could not be executed: {exc}"
        return result
    if proc.returncode != 0:
        result["error"] = (
            f"ogr2ogr exited {proc.returncode}: {proc.stderr[:500].strip()}"
        )
        return result
    if not gml_path.exists():
        result["error"] = "ogr2ogr reported success but wrote no GML file"
        return result
    result["ok"] = True
    return result


# --------------------------------------------------------------------------- #
# HTML report input
# --------------------------------------------------------------------------- #

def build_report_input(zones, sources=None, outputs=None, title=None):
    """Self-contained input dict for the HTML report (Jinja2-renderable).

    Aggregates layer metadata from the source registry for every layer the
    zones reference, per-zone stats + provenance, and global statistics.
    """
    sources = sources or {}
    used_layer_ids = sorted({lid for z in zones for lid in (z.get("layers") or [])})
    layers_meta = []
    for lid in used_layer_ids:
        src = sources.get(lid) or {}
        meta = {
            "id": lid,
            "title": src.get("title") or lid,
            "serviceUrl": src.get("serviceUrl"),
            "layerId": src.get("layerId"),
            "role": src.get("role"),
            "authoritative": src.get("authoritative"),
            "licenseNote": src.get("licenseNote"),
            "lastChecked": src.get("lastChecked"),
            "featureCount": src.get("featureCount"),
        }
        layers_meta.append({k: v for k, v in meta.items() if v is not None})

    final = next((z for z in zones if z.get("operation") == "final"), None)
    per_op = []
    for z in zones:
        per_op.append(
            {
                "id": z.get("id"),
                "operation": z.get("operation"),
                "ruleIds": z.get("ruleIds", []),
                "areaKm2": z.get("areaKm2"),
                "layers": z.get("layers", []),
                "provSteps": z.get("provSteps", [])
                or ([z.get("prov")] if z.get("prov") else []),
            }
        )
    # count repairs from the FINAL zone's aggregated provenance only, so the
    # per-operation snapshots (subsets of the same step list) are not counted twice
    prov_source = next((z for z in zones if z.get("operation") == "final"), zones[-1] if zones else None)
    steps_all = []
    if prov_source is not None:
        steps_all = (
            prov_source.get("provSteps")
            or ([prov_source["provenance"]] if prov_source.get("provenance") else [])
            or ([prov_source["prov"]] if prov_source.get("prov") else [])
        )
    total_repairs = sum(
        int(m.group(1))
        for step in steps_all
        for m in re.finditer(r"make_valid_repairs=(\d+)", step)
    )
    return {
        "title": title or "Wind-turbine opportunity map — province Utrecht (PoC)",
        "generatedAt": _utcnow_iso(),
        "generatedBy": CARTOGRAPHER_VERSION,
        "crs": "EPSG:4326 (computation in EPSG:28992, areas in km\u00b2)",
        "stats": {
            "zoneCount": len(zones),
            "finalAreaKm2": (final or {}).get("areaKm2"),
            "finalRuleIds": (final or {}).get("ruleIds", []),
            "geometryRepairsRecorded": total_repairs,
        },
        "layers": layers_meta,
        "zones": per_op,
        "outputs": dict(outputs or {}),
        "notes": [
            "cite-or-abstain: every exclusion/inclusion references a registry "
            "layer with lastChecked provenance; see per-zone provSteps.",
            "Areas computed in EPSG:28992 (RD New, metre); geometries "
            "validity-checked with make_valid repairs recorded in provenance.",
        ],
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description="Serialize ZoneResult[] to GeoJSON/GML/report input.")
    ap.add_argument("zones_json", help="JSON file containing a ZoneResult[] list")
    ap.add_argument("--out-dir", default="poc/output", help="output directory")
    ap.add_argument(
        "--sources", default=None, help="optional sources.json for layer metadata"
    )
    args = ap.parse_args(argv)

    with open(args.zones_json, "r", encoding="utf-8") as fh:
        zones = json.load(fh)
    sources = {}
    if args.sources:
        with open(args.sources, "r", encoding="utf-8") as fh:
            sources = {s["id"]: s for s in json.load(fh).get("sources", []) if "id" in s}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gj = write_geojson(zones, out_dir / "zones.geojson")
    gml = write_gml(gj)
    report = build_report_input(
        zones,
        sources=sources,
        outputs={"geojson": str(gj), "gml": gml["path"] if gml["ok"] else None, "gmlStatus": gml},
    )
    rp = out_dir / "report_input.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK  geojson -> {gj}")
    print(f"{'OK ' if gml['ok'] else 'WARN'} gml     -> {gml['path']}"
          + ("" if gml["ok"] else f" ({gml['error']})"))
    print(f"OK  report  -> {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
