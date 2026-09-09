from __future__ import annotations

import h3
import pytest
from shapely.geometry import Point, shape

from services.common import h3kit

#: ~3.3 x 2.7 km square over Utrecht city centre (RFC 7946: [lng, lat])
SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}


def test_polygon_to_cells_polyfill_semantics():
    cov = h3kit.polygon_to_cells(SQUARE, 9)
    assert cov["resolution"] == 9
    assert cov["cellCount"] == len(cov["cells"]) > 0
    assert cov["crs"] == "cells-EPSG:4326-areas-EPSG:28992"
    for row in cov["cells"]:
        lat, lng = h3.cell_to_latlng(row["cell"])
        assert 52.08 <= lat <= 52.11 and 5.10 <= lng <= 5.14  # centre-in-polygon
        assert 0.0 <= row["coverageFraction"] <= 1.0
        assert 80_000 < row["cellAreaM2"] < 140_000  # res 9 ≈ 0.10 km² avg


def test_coverage_weighted_area_close_to_planar_area():
    cov = h3kit.polygon_to_cells(SQUARE, 9)
    total_km2 = sum(r["coverageFraction"] * r["cellAreaM2"]
                    for r in cov["cells"]) / 1e6
    assert 8.0 < total_km2 < 10.0  # square is ≈ 9.1 km² in RD


def test_restrict_cells_reports_overlap_only_for_given_cells():
    base = h3kit.polygon_to_cells(SQUARE, 8)
    subset = [r["cell"] for r in base["cells"]][:3]
    cov = h3kit.polygon_to_cells(SQUARE, 8, restrict_cells=subset)
    assert [r["cell"] for r in cov["cells"]] == sorted(subset)
    assert cov["cellCount"] == 3


def test_restrict_cells_rejects_resolution_mismatch():
    base = h3kit.polygon_to_cells(SQUARE, 8)
    cell = base["cells"][0]["cell"]
    with pytest.raises(h3kit.H3KitError):
        h3kit.polygon_to_cells(SQUARE, 9, restrict_cells=[cell])


def test_determinism_sorted_output():
    a = h3kit.polygon_to_cells(SQUARE, 8)
    b = h3kit.polygon_to_cells(SQUARE, 8)
    assert a == b
    assert [r["cell"] for r in a["cells"]] == sorted(r["cell"] for r in a["cells"])


def test_compact_option_adds_compacted_list():
    cov = h3kit.polygon_to_cells(SQUARE, 9, compact=True)
    assert len(cov["compactedCells"]) <= cov["cellCount"]
    assert all(h3.is_valid_cell(c) for c in cov["compactedCells"])
    # mixed resolutions allowed (that IS compaction)
    assert any(h3.get_resolution(c) < 9 for c in cov["compactedCells"])


def test_invalid_resolution_raises():
    with pytest.raises(h3kit.H3KitError):
        h3kit.polygon_to_cells(SQUARE, 16)


def test_feature_collection_input_is_unioned():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": SQUARE}]}
    assert h3kit.polygon_to_cells(fc, 9) == h3kit.polygon_to_cells(SQUARE, 9)


POINTS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"id": "a"},
         "geometry": {"type": "Point", "coordinates": [5.11, 52.09]}},
        {"type": "Feature", "properties": {"id": "b"},
         "geometry": {"type": "Point", "coordinates": [5.12, 52.095]}},
        {"type": "Feature", "properties": {"id": "far"},
         "geometry": {"type": "Point", "coordinates": [4.90, 52.00]}},
    ],
}


def test_cells_to_geojson_roundtrip_contains_centres():
    cov = h3kit.polygon_to_cells(SQUARE, 9)
    fc = h3kit.cells_to_geojson([r["cell"] for r in cov["cells"]])
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == cov["cellCount"]
    for feat in fc["features"]:
        cell = feat["properties"]["cell"]
        lat, lng = h3.cell_to_latlng(cell)
        assert shape(feat["geometry"]).buffer(1e-7).contains(Point(lng, lat))


def test_cells_to_geojson_rejects_garbage():
    with pytest.raises(h3kit.H3KitError):
        h3kit.cells_to_geojson(["nonsense"])


def test_join_points_counts_per_cell():
    cov = h3kit.polygon_to_cells(SQUARE, 9)
    cells = [r["cell"] for r in cov["cells"]]
    join = h3kit.join_points_to_cells(POINTS, cells)
    assert join["pointCount"] == 3
    assert join["cellCount"] == len(cells)
    inside = sum(1 for r in join["perPoint"] if r["inCells"])
    assert inside == 2  # a and b inside the square, far outside
    assert sum(r["count"] for r in join["perCell"]) == inside


def test_join_points_from_polygon_derives_cells():
    join = h3kit.join_points_to_cells(POINTS, polygon=SQUARE, resolution=9)
    assert join["pointCount"] == 3
    assert sum(1 for r in join["perPoint"] if r["inCells"]) == 2


def test_join_points_needs_cells_or_polygon():
    with pytest.raises(h3kit.H3KitError):
        h3kit.join_points_to_cells(POINTS)


def test_join_points_uses_centroid_for_footprints():
    footprint = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {},
         "geometry": {"type": "Polygon", "coordinates": [
             [[5.10, 52.08], [5.13, 52.08], [5.13, 52.10], [5.10, 52.10],
              [5.10, 52.08]]]}}]}
    join = h3kit.join_points_to_cells(footprint, polygon=SQUARE, resolution=9)
    assert join["pointCount"] == 1
    assert join["perPoint"][0]["inCells"] is True  # centroid ≈ (5.115, 52.09)


def test_knn_orders_by_grid_distance_then_haversine():
    origin = {"lat": 52.09, "lng": 5.11}
    cands = [{"lat": 52.00, "lng": 4.90}, {"lat": 52.0901, "lng": 5.1101},
             {"lat": 52.0902, "lng": 5.1102}]
    out = h3kit.knn(origin, cands, k=2)
    assert out["originCell"].startswith("88")
    assert len(out["neighbors"]) == 2
    assert out["neighbors"][0]["gridDistance"] <= out["neighbors"][1]["gridDistance"]
    assert out["neighbors"][0]["distanceKm"] < 1.0


def test_children_of_drills_down():
    base = h3kit.polygon_to_cells(SQUARE, 8)
    parent = base["cells"][0]["cell"]
    kids = h3kit.children_of([parent], 9)["children"][parent]
    assert len(kids) == 7  # hex parent → 7 children
    assert all(h3.get_resolution(k) == 9 for k in kids)


def test_children_of_rejects_non_child_resolution():
    base = h3kit.polygon_to_cells(SQUARE, 8)
    with pytest.raises(h3kit.H3KitError):
        h3kit.children_of([base["cells"][0]["cell"]], 8)


def _disk_values(res=9):
    centre = h3.latlng_to_cell(52.09, 5.11, res)
    clustered = {centre: 10.0}
    # h3-py 4.5: grid_disk returns a list; wrap in set for difference
    for c in set(h3.grid_disk(centre, 1)) - {centre}:
        clustered[c] = 10.0
    for c in set(h3.grid_disk(centre, 2)) - set(h3.grid_disk(centre, 1)):
        clustered[c] = 1.0
    return clustered


def test_morans_i_clustered_is_strongly_positive():
    stat = h3kit.morans_i(_disk_values())
    assert stat["n"] == 19
    # binary grid_disk(1) weights give I ≈ 0.228 for this 7-core/12-ring
    # pattern (verified against an independent matrix implementation);
    # E[I] = -1/18, so 0.228 is strongly positive
    assert stat["moransI"] > 0.2
    assert stat["pValue"] <= 0.05
    assert stat["expectedI"] == round(-1 / 18, 9)


def test_morans_i_checkerboard_is_negative():
    centre = h3.latlng_to_cell(52.09, 5.11, 9)
    # sorted() order is lexicographic, not spatial (it gives I > 0);
    # walk the ring so values alternate between truly adjacent cells
    ring = []
    cur = min(set(h3.grid_disk(centre, 1)) - {centre})
    ring.append(cur)
    while len(ring) < 6:
        cur = min((set(h3.grid_disk(cur, 1)) - {centre}) - set(ring))
        ring.append(cur)
    values = {c: (10.0 if i % 2 == 0 else 1.0) for i, c in enumerate(ring)}
    values[centre] = 10.0
    assert h3kit.morans_i(values)["moransI"] < 0


def test_morans_i_accepts_join_rows():
    rows = [{"cell": c, "count": v} for c, v in _disk_values().items()]
    assert h3kit.morans_i(rows) == h3kit.morans_i(_disk_values())


def test_morans_i_deterministic():
    assert h3kit.morans_i(_disk_values()) == h3kit.morans_i(_disk_values())


def test_morans_i_degrades_gracefully():
    assert h3kit.morans_i({"a": 1.0})["moransI"] is None
    flat = h3kit.morans_i({c: 5.0 for c in _disk_values()})
    assert flat["moransI"] is None and "no variance" in flat["notes"][0]
