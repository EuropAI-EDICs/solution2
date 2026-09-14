from __future__ import annotations

import json
from typing import Any

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid


def validate_geojson_geometry(geom: dict[str, Any]) -> bool:
    try:
        shape(geom)
        return True
    except Exception:
        return False


def validate_feature_collection(fc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if fc.get("type") != "FeatureCollection":
        errors.append("expected FeatureCollection")
        return errors
    for i, feat in enumerate(fc.get("features", [])):
        geom = feat.get("geometry")
        if geom and not validate_geojson_geometry(geom):
            errors.append(f"feature[{i}] invalid geometry")
    return errors


def intersect_feature_collections(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    geoms_a = [_feature_geom(f) for f in a.get("features", []) if _feature_geom(f)]
    geoms_b = [_feature_geom(f) for f in b.get("features", []) if _feature_geom(f)]
    if not geoms_a or not geoms_b:
        return {"type": "FeatureCollection", "features": []}
    ua = unary_union(geoms_a)
    ub = unary_union(geoms_b)
    result = make_valid(ua.intersection(ub))
    if result.is_empty:
        return {"type": "FeatureCollection", "features": []}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"operation": "intersection"},
                "geometry": mapping(result),
            }
        ],
    }


def area_statistics(fc: dict[str, Any]) -> dict[str, Any]:
    areas: list[dict[str, Any]] = []
    total = 0.0
    for i, feat in enumerate(fc.get("features", [])):
        geom = _feature_geom(feat)
        if not geom:
            continue
        area = float(geom.area)
        areas.append({"featureIndex": i, "areaM2": round(area, 2)})
        total += area
    return {
        "featureCount": len(areas),
        "areasM2": areas,
        "totalAreaM2": round(total, 2),
        "crs": "EPSG:28992-assumed-planar",
    }


def _feature_geom(feat: dict[str, Any]):
    geom = feat.get("geometry")
    if not geom:
        return None
    return shape(geom)


def parse_geojson_input(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    raise TypeError("expected geojson dict or JSON string")
