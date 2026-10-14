#!/usr/bin/env python3
"""Single-file HTML report renderer for the opportunity-map PoC.

Renders ``poc/pipeline/report_template.html`` (Jinja2) with the run's data:
Leaflet map from CDN with a layer switcher over the run's zones (geometry
embedded inline so the report works from ``file://`` without fetch), a
fallback zone/statistics table, the decision table, the validation report,
the norm cards with their verbatim quotes and links, the abstentions
ledger and the provenance summary.

Display geometry is simplified (Douglas-Peucker in EPSG:28992 metres) and
coordinate-rounded so the single file stays openable; the full-resolution
authoritative geometry remains ``zones.geojson`` / ``zones.gml`` in the run
directory, and the display tolerance is recorded in the run summary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from pipeline import engine
except ImportError:  # pragma: no cover - direct execution inside poc/pipeline
    import engine as engine  # type: ignore[no-redef]

__all__ = ["REPORT_VERSION", "simplify_payload_for_display", "build_map_data",
           "render_report_html", "write_report", "OPERATION_CATEGORY"]

REPORT_VERSION = "poc-report/1.0"
TEMPLATE_PATH = Path(__file__).resolve().parent / "report_template.html"
DEFAULT_DISPLAY_TOLERANCE_M = 25.0

OPERATION_CATEGORY = {
    "final": "final",
    "intersection": "inclusion",
    "inclusion_union": "inclusion",
    "union": "inclusion",
    "difference": "exclusion",
    "attention_mark": "marker",
    "conditional_mark": "marker",
    "compensation_mark": "marker",
}

_OPERATION_LABEL = {
    "final": "final",
    "inclusion_union": "union",
    "intersection": "intersection",
    "difference": "difference",
    "union": "union",
    "attention_mark": "attention_mark",
    "conditional_mark": "conditional_mark",
    "compensation_mark": "compensation_mark",
}


def simplify_payload_for_display(payload: Mapping[str, Any], tolerance_m: float) -> Dict[str, Any]:
    """WGS84 GeoJSON geometry -> simplified WGS84 geometry for display."""
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as _t
    from pyproj import Transformer

    to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    geom = shape(payload)
    if geom.is_empty:
        return {"type": "GeometryCollection", "geometries": []}
    rd = _t(lambda x, y, z=None: to_rd.transform(x, y), geom)
    rd = rd.simplify(tolerance_m, preserve_topology=True)
    wgs = _t(lambda x, y, z=None: to_wgs.transform(x, y), rd)

    def _round(obj):
        if isinstance(obj, (list, tuple)):
            return [_round(v) for v in obj]
        if isinstance(obj, float):
            return round(obj, 6)
        return obj

    out = mapping(wgs)
    if out.get("type") == "GeometryCollection":
        return {"type": "GeometryCollection", "geometries": [_round(g) for g in out["geometries"]]}
    return {"type": out["type"], "coordinates": _round(out["coordinates"])}


def build_map_data(
    zones: Sequence[Mapping[str, Any]],
    aoi_payload: Optional[Mapping[str, Any]],
    tolerance_m: float = DEFAULT_DISPLAY_TOLERANCE_M,
) -> Dict[str, Any]:
    """Build the template's ``map`` block from the engine's rich zones."""
    features = []
    for z in zones:
        op = str(z.get("operation", ""))
        if op == "final" and z.get("isReport") is None and not z.get("layers") and not z.get("ruleIds"):
            pass
        payload = (z.get("geometry") or {}).get("payload")
        if payload is None:
            continue
        simple = simplify_payload_for_display(payload, tolerance_m)
        if simple.get("type") == "GeometryCollection" and not simple.get("geometries"):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "__cat": OPERATION_CATEGORY.get(op, "marker"),
                    "id": z.get("id", "?"),
                    "operation": op,
                    "areaKm2": z.get("areaKm2"),
                    "ruleIds": z.get("ruleIds", []),
                    "layers": z.get("layers", []),
                },
                "geometry": simple,
            }
        )
    fc = {"type": "FeatureCollection", "features": features}

    aoi_simple = None
    if aoi_payload is not None:
        aoi_rd = None
        from shapely.geometry import shape

        aoi_rd = shape(aoi_payload)  # already EPSG:28992
        aoi_rd = aoi_rd.simplify(tolerance_m, preserve_topology=True)
        aoi_simple = engine.to_wgs84(aoi_rd)
        from shapely.geometry import mapping as _mapping

        aoi_simple = _mapping(aoi_simple)

    def _json_script(obj) -> str:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

    lons, lats = [], []

    def _collect(g):
        if isinstance(g, dict):
            if "coordinates" in g:
                def _c(coords):
                    if isinstance(coords[0], (int, float)):
                        lons.append(coords[0]); lats.append(coords[1])
                    else:
                        for c in coords: _c(c)
                _c(g["coordinates"])
            for g2 in g.get("geometries", []):
                _collect(g2)

    for f in features:
        _collect(f["geometry"])
    if aoi_simple:
        _collect(aoi_simple)
    bounds = [[min(lats), min(lons)], [max(lats), max(lons)]] if lons else [[51.8, 4.8], [52.3, 5.4]]
    return {
        "geojson": _json_script(fc),
        "aoi": _json_script(aoi_simple) if aoi_simple else "null",
        "bounds": bounds,
        "tolerance_m": tolerance_m,
    }


def render_report_html(data: Mapping[str, Any], template_path: Optional[Path] = None) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent if template_path else TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tpl = env.get_template((template_path or TEMPLATE_PATH).name)
    return tpl.render(**data)


def write_report(path: Path, data: Mapping[str, Any], template_path: Optional[Path] = None) -> Path:
    html = render_report_html(data, template_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
