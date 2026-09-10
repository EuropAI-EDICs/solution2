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


def test_hex_overlay_recipe_end_to_end():
    import json
    from pathlib import Path

    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform as sh_transform

    from services.mcp_servers.client import ProcessClient
    from services.process_adapter import jobs as job_store
    from services.recipe_runner import run_recipe

    # In-process execution (repo pattern from test_nldt_core.py): the default
    # ProcessClient would POST to a live process service on :8082.
    class LocalClient(ProcessClient):
        def execute(self, process_id, inputs, backend="local"):
            return job_store.create_job(process_id, inputs, backend=backend)

    examples = Path(__file__).resolve().parents[1] / "examples"
    with (examples / "aoi.geojson").open() as f:
        aoi = json.load(f)
    # examples/aoi.geojson is EPSG:28992 (RD); the H3 kernel is WGS84-native,
    # so reproject the zone to lon/lat and pass it inline (fetch-features
    # accepts inline GeoJSON JSON strings as well as file:// URIs).
    to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    zone_wgs84 = json.dumps(mapping(sh_transform(to_wgs84.transform, shape(aoi))))
    # Res 8/9 leave no cell centre inside this 200 m AOI (verified: cellCount
    # 0); res 11 discretises it into 21 cells. Of the four fixture points
    # (centroid, +0.001°/+0.001°, -0.001°/+0.001°, far-away 4.9/52.0) the
    # first two index into polygon cells, the third lands just outside the
    # north edge (its cell centre misses the zone), the far one is excluded.
    result = run_recipe("hex-overlay-analysis", {
        "aoi": aoi,
        "zoneUri": zone_wgs84,
        "pointsUri": f"file://{examples / 'hex-points.geojson'}",
        "resolution": 11,
    }, process_client=LocalClient())
    outputs = result["outputs"]
    assert outputs["coverage"]["cellCount"] == 21
    assert outputs["join"]["pointCount"] == 4
    assert sum(1 for r in outputs["join"]["perPoint"] if r["inCells"]) == 2
    assert outputs["autocorrelation"]["n"] >= 1


def test_cli_file_uri_inputs_loaded_as_json():
    # Regression: poc/pipeline/h3step.py passes list/dict inputs as
    # file:// request paths; _parse_inputs must load them as JSON (a
    # plain string would make polygon_to_cells iterate characters and
    # raise H3KitError). Missing files pass through unchanged for
    # consumers like fetch-features that resolve file URIs themselves.
    import contextlib
    import io
    import json as _json
    import tempfile
    from pathlib import Path

    from services.cli import _parse_inputs, main

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cells_file = tmp / "cells.json"
        cells_file.write_text(_json.dumps(["cell-a", "cell-b"]))
        parsed = _parse_inputs([f"restrictCells=file://{cells_file}"])
        assert isinstance(parsed["restrictCells"], list)
        assert parsed["restrictCells"] == ["cell-a", "cell-b"]
        assert _parse_inputs(["source=file:///nonexistent/x.json"]) == {
            "source": "file:///nonexistent/x.json"}

        # End-to-end through the CLI: restrictCells arrives as a file URI
        # and the coverage must cover exactly the restricted cells.
        full = execute_local("h3-polygon-to-cells",
                             {"polygon": SQUARE, "resolution": 9})["coverage"]
        restrict = [r["cell"] for r in full["cells"][:3]]
        polygon_file = tmp / "polygon.geojson"
        polygon_file.write_text(_json.dumps(SQUARE))
        cells_file.write_text(_json.dumps(restrict))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["run-process", "h3-polygon-to-cells",
                       "--input", f"polygon=file://{polygon_file}",
                       "--input", "resolution=9",
                       "--input", f"restrictCells=file://{cells_file}"])
        assert rc == 0
        job = _json.loads(buf.getvalue())
        assert [r["cell"] for r in job["outputs"]["coverage"]["cells"]] == sorted(restrict)
        assert job["outputs"]["coverage"]["cellCount"] == 3


def test_cli_fetch_features_file_uri_source():
    # Regression (fix 2): _parse_inputs resolves file:// values as JSON,
    # so "source=file://..." arrives at execute_local's fetch-features
    # branch as a dict; _load_source must accept already-parsed GeoJSON
    # instead of str()-ing it into json.loads (JSONDecodeError).
    import contextlib
    import io
    import json as _json
    from pathlib import Path

    from services.cli import main

    examples = Path(__file__).resolve().parents[1] / "examples"
    source = examples / "hex-points.geojson"
    with source.open() as f:
        fc = _json.load(f)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["run-process", "fetch-features",
                   "--input", f"source=file://{source}"])
    assert rc == 0
    job = _json.loads(buf.getvalue())
    assert job["outputs"]["features"] == fc
