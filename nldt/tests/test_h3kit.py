from __future__ import annotations

import h3
import pytest

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
