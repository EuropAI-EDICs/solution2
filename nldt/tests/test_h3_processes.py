from __future__ import annotations

import pytest

from services.common import h3kit
from services.process_adapter.handlers import (
    PROCESS_DEFINITIONS,
    describe_process,
    execute_local,
)
from services.process_adapter.router import route_execute

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}
POINTS = [
    {"lat": 52.09, "lng": 5.11},
    {"lat": 52.095, "lng": 5.12},
    {"lat": 52.00, "lng": 4.90},
]


def test_five_h3_processes_listed_and_described():
    expected = {"h3-polygon-to-cells", "h3-cells-to-geojson",
                "h3-spatial-join-points", "h3-knn", "h3-morans-i"}
    assert expected <= set(PROCESS_DEFINITIONS)
    for pid in expected:
        assert describe_process(pid)["id"] == pid


def test_h3_polygon_to_cells_roundtrip_through_process():
    out = execute_local("h3-polygon-to-cells",
                        {"polygon": SQUARE, "resolution": 9})
    cov = out["coverage"]
    assert cov["cellCount"] > 0
    geo = execute_local("h3-cells-to-geojson",
                        {"cells": [r["cell"] for r in cov["cells"]]})
    assert len(geo["features"]["features"]) == cov["cellCount"]


def test_h3_polygon_to_cells_via_file_uri():
    import json as _json
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as f:
        _json.dump(SQUARE, f)
        path = f.name
    try:
        out = execute_local("h3-polygon-to-cells",
                            {"polygon": f"file://{path}", "resolution": 9})
        assert out["coverage"]["cellCount"] > 0
    finally:
        Path(path).unlink()


def test_h3_spatial_join_points_process():
    zone_fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": SQUARE}]}
    out = execute_local("h3-spatial-join-points",
                        {"points": {"type": "FeatureCollection", "features": [
                            {"type": "Feature", "properties": {},
                             "geometry": {"type": "Point",
                                          "coordinates": [5.11, 52.09]}}]},
                         "polygon": zone_fc, "resolution": 9})
    assert out["join"]["pointCount"] == 1
    assert sum(1 for r in out["join"]["perPoint"] if r["inCells"]) == 1


def test_h3_knn_process():
    out = execute_local("h3-knn",
                        {"point": POINTS[0], "candidates": POINTS, "k": 2})
    assert len(out["neighbors"]["neighbors"]) == 2


def test_h3_morans_i_process():
    import h3

    centre = h3.latlng_to_cell(52.09, 5.11, 9)
    # h3-py 4.5: grid_disk returns a list; wrap in set for difference
    values = {c: 10.0 for c in set(h3.grid_disk(centre, 1))}
    values.update({c: 1.0 for c in
                   set(h3.grid_disk(centre, 2)) - set(h3.grid_disk(centre, 1))})
    out = execute_local("h3-morans-i", {"values": values})
    assert out["statistics"]["n"] == 19
    # Same 7-core/12-ring pattern as test_h3kit.py: I ≈ 0.228
    assert out["statistics"]["moransI"] > 0.2


def test_route_execute_wraps_h3_with_prov():
    _job_id, outputs, prov = route_execute(
        "h3-polygon-to-cells", {"polygon": SQUARE, "resolution": 9})
    assert outputs["coverage"]["cellCount"] > 0
    assert prov["activity"] == "nldt:ProcessExecution/h3-polygon-to-cells"


def test_unknown_cell_input_raises():
    with pytest.raises(h3kit.H3KitError):
        execute_local("h3-cells-to-geojson", {"cells": ["garbage"]})
