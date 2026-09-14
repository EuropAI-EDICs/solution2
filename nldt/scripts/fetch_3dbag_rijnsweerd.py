#!/usr/bin/env python3
"""Fetch 3D BAG buildings for Rijnsweerd (Utrecht) study area."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

# Rijnsweerd, Utrecht (Wikidata 52°5'21.8"N 5°9'16.6"E → RD New)
# ~200×200 m study area
CENTER_RD = (139059.3, 455706.5)
CENTER_WGS84 = (5.154611, 52.089389)  # lon, lat
HALF = 100.0
BBOX = (
    CENTER_RD[0] - HALF,
    CENTER_RD[1] - HALF,
    CENTER_RD[0] + HALF,
    CENTER_RD[1] + HALF,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "examples" / "rijnsweerd"


def fetch_all_buildings(bbox: tuple[float, float, float, float]) -> list[dict]:
    bbox_str = ",".join(str(v) for v in bbox)
    url: str | None = f"https://api.3dbag.nl/collections/pand/items?bbox={bbox_str}&limit=50"
    features: list[dict] = []
    with httpx.Client(timeout=120.0) as client:
        while url:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            features.extend(data.get("features", []))
            url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "next"), None)
    return features


def footprint_from_feature(feature: dict) -> dict | None:
    """Extract ground footprint polygon from CityJSONFeature (lod 0)."""
    vertices = feature.get("vertices") or []
    for _obj_id, obj in feature.get("CityObjects", {}).items():
        for geom in obj.get("geometry") or []:
            if geom.get("lod") != "0":
                continue
            boundaries = geom.get("boundaries") or []
            if not boundaries:
                continue
            ring = boundaries[0][0]
            coords = [[vertices[i][0], vertices[i][1]] for i in ring if i < len(vertices)]
            if len(coords) >= 4:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                attrs = obj.get("attributes") or {}
                return {
                    "type": "Feature",
                    "properties": {
                        "bagId": _obj_id,
                        "b3_h_maaiveld": attrs.get("b3_h_maaiveld"),
                        "b3_volume_lod22": attrs.get("b3_volume_lod22"),
                    },
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                }
    return None


def write_geojson_examples(out: Path) -> None:
    xmin, ymin, xmax, ymax = BBOX
    mid_x = CENTER_RD[0]
    overlap = 50.0

    aoi = {
        "type": "Polygon",
        "coordinates": [[[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]],
    }
    layer_a = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "rijnsweerd-zone-a", "description": "West deel Rijnsweerd"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[xmin, ymin], [mid_x, ymin], [mid_x, ymax], [xmin, ymax], [xmin, ymin]]],
            },
        }],
    }
    layer_b = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "rijnsweerd-zone-b", "description": "Oost deel Rijnsweerd"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[mid_x - overlap, ymin], [xmax, ymin], [xmax, ymax], [mid_x - overlap, ymax], [mid_x - overlap, ymin]]],
            },
        }],
    }

    (out / "aoi.geojson").write_text(json.dumps(aoi, indent=2), encoding="utf-8")
    (out / "layer-a.geojson").write_text(json.dumps(layer_a, indent=2), encoding="utf-8")
    (out / "layer-b.geojson").write_text(json.dumps(layer_b, indent=2), encoding="utf-8")


def main() -> int:
    out = OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    print(f"Fetching 3D BAG buildings for Rijnsweerd bbox {BBOX}…")
    features = fetch_all_buildings(BBOX)
    print(f"  → {len(features)} buildings")

    cityjsonl = out / "buildings.city.jsonl"
    with cityjsonl.open("w", encoding="utf-8") as f:
        for feat in features:
            f.write(json.dumps(feat) + "\n")

    footprints = [fp for fp in (footprint_from_feature(f) for f in features) if fp]
    fc = {"type": "FeatureCollection", "features": footprints}
    (out / "buildings-footprints.geojson").write_text(json.dumps(fc, indent=2), encoding="utf-8")

    write_geojson_examples(out)

    xmin, ymin, xmax, ymax = BBOX
    mid_x = CENTER_RD[0]
    overlap = 50.0

    try:
        from pyproj import Transformer

        to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
        lon, lat = to_wgs.transform(CENTER_RD[0], CENTER_RD[1])

        def rd_ring(ring: list[list[float]]) -> list[list[float]]:
            out = []
            for x, y in ring:
                lo, la = to_wgs.transform(x, y)
                out.append([lo, la])
            return out

        ix0, iy0 = mid_x - overlap, ymin
        layers_wgs84 = {
            "aoi": rd_ring([[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]),
            "layerA": rd_ring([[xmin, ymin], [mid_x, ymin], [mid_x, ymax], [xmin, ymax], [xmin, ymin]]),
            "layerB": rd_ring([[mid_x - overlap, ymin], [xmax, ymin], [xmax, ymax], [mid_x - overlap, ymax], [mid_x - overlap, ymin]]),
            "intersect": rd_ring([[mid_x - overlap, ymin], [mid_x, ymin], [mid_x, ymax], [mid_x - overlap, ymax], [mid_x - overlap, ymin]]),
        }
        center_wgs84 = {"lon": lon, "lat": lat}
        intersection_m2 = overlap * (ymax - ymin)
    except ImportError:
        layers_wgs84 = {}
        center_wgs84 = {"lon": CENTER_WGS84[0], "lat": CENTER_WGS84[1]}
        intersection_m2 = 10000.0

    meta = {
        "area": "Rijnsweerd, Utrecht",
        "postcode": "3584",
        "bbox_rd": list(BBOX),
        "center_rd": list(CENTER_RD),
        "center_wgs84": center_wgs84,
        "layers_wgs84": layers_wgs84,
        "buildingCount": len(features),
        "footprintCount": len(footprints),
        "source": "https://api.3dbag.nl/collections/pand/items",
        "tiles_lod22": "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json",
        "overlayIntersectionAreaM2": intersection_m2,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    sim_meta = Path(__file__).resolve().parents[1] / "simulation" / "rijnsweerd-meta.json"
    sim_meta.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Sync root examples for CLI / orchestrator defaults
    root = out.parent
    for name in ("aoi.geojson", "layer-a.geojson", "layer-b.geojson"):
        src = out / name if name != "aoi.geojson" else out / name
        if name == "aoi.geojson":
            (root / "aoi.geojson").write_text((out / "aoi.geojson").read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (root / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Saved to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
