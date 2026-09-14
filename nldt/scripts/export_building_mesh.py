#!/usr/bin/env python3
"""Export LoD2.2 mesh triangles (WGS84 + ellipsoidal height) for building-agent-demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from pyproj import Transformer

BAG_ID = "NL.IMBAG.Pand.0344100000039220"
PAND_ID = BAG_ID.split(".")[-1]
BBOX = "139325,455475,139390,455515"
SCALE = (0.01, 0.01, 0.001)
OUT = Path(__file__).resolve().parents[1] / "simulation" / "building-mesh.json"


def fan_triangles(indices: list[int]) -> list[tuple[int, int, int]]:
    if len(indices) < 3:
        return []
    return [(indices[0], indices[i], indices[i + 1]) for i in range(1, len(indices) - 1)]


def main() -> int:
    wfs = (
        "https://service.pdok.nl/lv/bag/wfs/v2_0?service=WFS&version=2.0.0"
        f"&request=GetFeature&typeName=bag:pand&bbox={BBOX},EPSG:28992"
        "&outputFormat=application/json&count=20"
    )
    bag_feat = next(
        f for f in httpx.get(wfs, timeout=60).json()["features"]
        if f["properties"]["identificatie"] == PAND_ID
    )
    rd0 = bag_feat["geometry"]["coordinates"][0][0]

    feat3d = None
    with httpx.Client(timeout=120) as client:
        data = client.get(
            f"https://api.3dbag.nl/collections/pand/items?bbox={BBOX}&limit=50"
        ).json()
    for feature in data.get("features", []):
        if BAG_ID in feature.get("CityObjects", {}):
            feat3d = feature
            break
    if feat3d is None:
        raise RuntimeError(f"3D BAG feature {BAG_ID} niet gevonden")

    vertices = feat3d["vertices"]
    building = feat3d["CityObjects"][BAG_ID]
    footprint_ring = building["geometry"][0]["boundaries"][0][0]
    anchor = vertices[footprint_ring[0]]
    translate = (rd0[0] - anchor[0] * SCALE[0], rd0[1] - anchor[1] * SCALE[1], 0.0)
    to_wgs3d = Transformer.from_crs("EPSG:28992", "EPSG:4979", always_xy=True)

    part = feat3d["CityObjects"][f"{BAG_ID}-0"]
    def vertex_wgs(index: int) -> tuple[float, float, float]:
        v = vertices[index]
        x = v[0] * SCALE[0] + translate[0]
        y = v[1] * SCALE[1] + translate[1]
        z = v[2] * SCALE[2] + translate[2]
        lon, lat, height = to_wgs3d.transform(x, y, z)
        return lon, lat, height

    bag_wgs = [to_wgs3d.transform(x, y, 0)[:2] for x, y in bag_feat["geometry"]["coordinates"][0]]
    from shapely.geometry import Point, Polygon

    footprint_poly = Polygon(bag_wgs).buffer(0.00008)

    triangles: list[list[float]] = []
    for geom in part["geometry"]:
        if geom.get("lod") != "2.2" or geom.get("type") != "Solid":
            continue
        for shell in geom["boundaries"]:
            for face in shell:
                ring = face[0]
                for a, b, c in fan_triangles(ring):
                    va, vb, vc = vertex_wgs(a), vertex_wgs(b), vertex_wgs(c)
                    cx = (va[0] + vb[0] + vc[0]) / 3
                    cy = (va[1] + vb[1] + vc[1]) / 3
                    if not footprint_poly.contains(Point(cx, cy)):
                        continue
                    triangles.append(
                        [round(va[0], 8), round(va[1], 8), round(va[2], 3)]
                        + [round(vb[0], 8), round(vb[1], 8), round(vb[2], 3)]
                        + [round(vc[0], 8), round(vc[1], 8), round(vc[2], 3)]
                    )

    OUT.write_text(
        json.dumps({"bagId": BAG_ID, "lod": "2.2", "triangleCount": len(triangles), "triangles": triangles}),
        encoding="utf-8",
    )
    print(f"Geschreven: {OUT} ({len(triangles)} driehoeken)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
