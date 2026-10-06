"""DEPRECATED (M1, harness-unificatie): vervangen door de nldt-MCP-tools
(catalog :8090 / data :8092 / poc :8093). Nog aanwezig als expliciete
fallback voor het geval er geen MCP-stack draait; verwijderd in de
M2-cleanup zodra het MCP-pad standaard is.

Geo-specialist tools: inspect and compare the GeoJSON layers of built
world-scene runs (pure python, no cloud, no extra deps).

Areas are spherical (WGS84, turf-style spherical excess) — good enough for
delta analysis; legal surfaces come from the engine, not from here.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import journal
from tools.utrecht import normalize_run_id

HERE = Path(__file__).resolve().parents[1]
RUNS_DIR = HERE / "runs"
R_EARTH = 6378137.0


def _ring_area_m2(ring: list[list[float]]) -> float:
    if len(ring) < 3:
        return 0.0
    total = 0.0
    n = len(ring)
    for i in range(n):
        p1, p2, p3 = ring[i], ring[(i + 1) % n], ring[(i - 1) % n]
        total += (math.radians(p3[0]) - math.radians(p1[0])) * math.sin(math.radians(p2[1]))
    return total * R_EARTH * R_EARTH / 2.0


def _polygon_area_m2(rings: list[list[list[float]]]) -> float:
    if not rings:
        return 0.0
    outer = abs(_ring_area_m2(rings[0]))
    holes = sum(abs(_ring_area_m2(r)) for r in rings[1:])
    return max(outer - holes, 0.0)


def geojson_area_km2(geom: dict[str, Any]) -> float:
    t = geom.get("type")
    if t == "Polygon":
        return _polygon_area_m2(geom.get("coordinates", [])) / 1e6
    if t == "MultiPolygon":
        return sum(_polygon_area_m2(p) for p in geom.get("coordinates", [])) / 1e6
    if t == "Feature":
        return geojson_area_km2(geom.get("geometry", {}) or {})
    if t in ("FeatureCollection", "GeometryCollection"):
        key = "features" if t == "FeatureCollection" else "geometries"
        return sum(geojson_area_km2(g) for g in geom.get(key, []))
    return 0.0


def _count_features(geom: dict[str, Any]) -> int:
    t = geom.get("type")
    if t == "FeatureCollection":
        return len(geom.get("features", []))
    return 1


def _bbox(geom: dict[str, Any]) -> list[float]:
    lats, lons = [], []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)):
            return
        if isinstance(node, list) and len(node) >= 2 and all(isinstance(v, (int, float)) for v in node[:2]):
            lons.append(node[0])
            lats.append(node[1])
            return
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            walk(node.get("coordinates", node.get("geometry", {}).get("coordinates", []) if node.get("geometry") else []))

    walk(geom.get("features", geom.get("coordinates", geom)))
    return [round(min(lons), 4), round(min(lats), 4), round(max(lons), 4), round(max(lats), 4)] if lons else []


def _layer_path(scenario_run_id: str, layer: str) -> Path:
    work = RUNS_DIR / f"{normalize_run_id(scenario_run_id)}-worldscene" / "scenarios"
    name = "CONTROL.geojson" if layer in ("control", "CONTROL") else f"{layer.removeprefix('WSS-')}.geojson"
    return work / name


def _layer(scenario_run_id: str, layer: str) -> dict[str, Any] | None:
    """Load a layer's GeoJSON; on a miss return an error payload instead of raising."""
    path = _layer_path(scenario_run_id, layer)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    clean = layer.removeprefix("WSS-")
    journal.append("error", "geospecialist", f"laag '{layer}' niet gevonden (bedoel je '{clean}'?)")
    return None


def inspect_geo_layer(scenario_run_id: str, layer: str) -> dict[str, Any]:
    """Inspect one GeoJSON layer of a built world-scene run: feature count, bounding box and total (spherical) area in km2. layer='control' or a scenario id (a WSS-<spec> id is accepted too — the prefix is stripped)."""
    path = _layer_path(scenario_run_id, layer)
    if not path.is_file():
        miss = _layer(scenario_run_id, layer)
        return {"error": f"Layer '{layer}' not found — use the scenario id "
                f"(e.g. '{layer.removeprefix('WSS-')}', not the WSS- spec id) or 'control'."}
    geom = json.loads(path.read_text(encoding="utf-8"))
    area = geojson_area_km2(geom)
    result = {
        "layer": layer,
        "file": str(path),
        "features": _count_features(geom),
        "areaKm2": round(area, 3),
        "bbox": _bbox(geom),
    }
    journal.append(
        "tool_call", "geospecialist", f"inspect_geo_layer('{layer}') → {result['areaKm2']} km²"
    )
    return result


def compare_layers(scenario_run_id: str, scenario_id: str) -> dict[str, Any]:
    """Compare a scenario layer against the control layer of a built world-scene run: areas, delta in km2 and percent, feature counts."""
    control = _layer(scenario_run_id, "control")
    scenario = _layer(scenario_run_id, scenario_id.removeprefix("WSS-"))
    if control is None or scenario is None:
        missing = "control" if control is None else scenario_id
        return {"error": f"Layer '{missing}' not found — use the scenario id (strip any "
                "'WSS-' prefix) and run run_world_scene first."}
    a_ctrl = geojson_area_km2(control)
    a_scen = geojson_area_km2(scenario)
    delta = a_scen - a_ctrl
    result = {
        "scenarioRunId": scenario_run_id,
        "scenarioId": scenario_id,
        "controlAreaKm2": round(a_ctrl, 3),
        "scenarioAreaKm2": round(a_scen, 3),
        "deltaKm2": round(delta, 3),
        "deltaPct": round(delta / a_ctrl * 100, 3) if a_ctrl else None,
        "controlFeatures": _count_features(control),
        "scenarioFeatures": _count_features(scenario),
    }
    journal.append(
        "tool_call",
        "geospecialist",
        f"compare_layers('{scenario_id}') → Δ {result['deltaKm2']:+.2f} km² ({result['deltaPct']:+.2f}%)",
    )
    return result
