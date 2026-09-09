# H3 Methodology Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved H3 design (spec: `docs/superpowers/specs/2026-09-09-h3-integration-design.md`): a deterministic H3 kernel exposed as five `h3-*` OGC API Processes in `nldt/`, consumed by `poc/` through a cache-first process client, with crosstrack hex-conflict overlay, scenario Moran's-I metrics, buildings join, and a Leaflet hex map.

**Architecture:** Single H3 implementation in `nldt/services/common/h3kit.py` (h3-py v4 + shapely + pyproj, areas planar in EPSG:28992), wired as processes in `process_adapter/handlers.py` (PROV/catalog/MCP/recipe for free). `poc/pipeline/h3step.py` is the only bridge: cache-first (`poc/data/cache/h3/<sha256>.json`), on miss invokes `nldt/services/cli.py run-process` as a subprocess, all poc tests run offline against committed fixtures (`POC_H3_OFFLINE=1`).

**Tech Stack:** Python 3.14 (`nldt/.venv`), h3-py ≥ 4.1 (v4 API), shapely, pyproj, pytest (nldt), unittest (poc), Leaflet via CDN (runtime only, in HTML).

## Global Constraints

- **Interpreter:** every `python`/`pytest`/`unittest` command runs as `/Users/marc/Projecten/ldttoolbox/nldt/.venv/bin/python` (below: `$PY`). It is the only interpreter on this machine with shapely/pyproj/jsonschema. System `python3` (3.14, homebrew) has none of these.
- **Offline determinism:** poc tests must pass with `POC_H3_OFFLINE=1` and must never spawn a subprocess; nldt tests need no network. All cell lists sorted; permutation tests seeded `random.Random(0)`; cached artifacts byte-stable (no timestamps inside `outputs`).
- **h3-py v4 API names only:** `latlng_to_cell`, `polygon_to_cells`, `cell_to_boundary(cell, geo_json=True)`, `cell_to_latlng`, `grid_disk`, `grid_distance`, `compact_cells`, `cell_to_children`, `is_valid_cell`, `get_resolution`. Never v3 names (`geo_to_h3`, `polyfill`, `hex_ring`, …).
- **CRS:** H3 cells are WGS84-native; every area/coverage number is computed planar in EPSG:28992 via pyproj (`always_xy=True`); serialized geometry is EPSG:4326 (RFC 7946).
- **Schemas:** JSON Schema draft 2020-12, self-contained (no cross-file `$refs`). New report fields are *optional* properties; existing artifacts must keep validating (`additionalProperties: false` schemas gain explicit optional keys).
- **No legal-claim changes:** H3 blocks are decision-support additions; failures degrade (recorded in `degradations`), never flip a run verdict.
- Commit style: match repo history (`"H3 ...: ..."` imperative, lowercase-ish). Commit only files a task created/modified — never `nldt/` (untracked by design), never `poc/crosstrack-runs/`, `poc/data/cache/h3/req/`, `__pycache__`, `.pytest_cache`.

---

### Task 1: Environment + `h3kit` coverage core

**Files:**
- Create: `nldt/services/common/h3kit.py`
- Create: `nldt/tests/test_h3kit.py`
- Modify: `nldt/requirements.txt`

**Interfaces:**
- Consumes: `services.common.geo` conventions (shapely, `make_valid`), nothing else.
- Produces (later tasks rely on these exact names):
  - `h3kit.H3KitError(ValueError)`
  - `h3kit.resolve_geojson(value) -> dict` (inline dict / JSON string / `file://` URI)
  - `h3kit.DEFAULT_RESOLUTION = 8`
  - `h3kit.polygon_to_cells(polygon, resolution=8, *, restrict_cells=None, compact=False) -> dict` returning `{"resolution", "cellCount", "cells": [{"cell", "coverageFraction", "cellAreaM2"}], "crs": "cells-EPSG:4326-areas-EPSG:28992", "h3Version", ["notes"], ["compactedCells"]}`

- [ ] **Step 1: Install dependencies into the venv (h3 new; geopandas restores the poc V3 suite broken on this machine)**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/pip install 'h3>=4.1' 'geopandas>=1.0'
.venv/bin/python -c "import h3; print(h3.__version__)"   # expect 4.x
.venv/bin/python -m pytest tests -q                      # expect: 29 passed (unchanged)
```

- [ ] **Step 2: Add to `nldt/requirements.txt`** (after the `shapely>=2.0.0` line):

```
h3>=4.1.0
pyproj>=3.7.0
```

(geopandas is *not* added — it is a poc-stack repair, not an nldt dependency.)

- [ ] **Step 3: Write the failing kernel test** — create `nldt/tests/test_h3kit.py`:

```python
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
    assert set(cov["compactedCells"]) <= {r["cell"] for r in cov["cells"]}
    assert len(cov["compactedCells"]) <= cov["cellCount"]


def test_invalid_resolution_raises():
    with pytest.raises(h3kit.H3KitError):
        h3kit.polygon_to_cells(SQUARE, 16)


def test_feature_collection_input_is_unioned():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": SQUARE}]}
    assert h3kit.polygon_to_cells(fc, 9) == h3kit.polygon_to_cells(SQUARE, 9)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.common.h3kit'`

- [ ] **Step 5: Implement the kernel core** — create `nldt/services/common/h3kit.py`:

```python
"""Deterministic H3 kernel for the nLDT process adapter.

Ports the H3 urban-analytics patterns (uber/h3-py-notebooks
urban_analytics.ipynb) to the h3-py v4 API: polygon-to-cell coverage
(the notebook's ``polyfill``), cell-boundary GeoJSON, point joins + KNN,
parent/children drill-down and a from-scratch global Moran's I over
grid_disk neighbourhoods.

CRS discipline: H3 cells are WGS84-native; every area / coverage number
is computed planar in EPSG:28992 (pyproj), matching the 28992 assumption
of services/common/geo.py. Cell lists are always sorted, so outputs are
byte-stable across replays.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import h3
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform as sh_transform, unary_union
from shapely.validation import make_valid

__all__ = [
    "DEFAULT_RESOLUTION",
    "H3KitError",
    "resolve_geojson",
    "polygon_to_cells",
]

_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
DEFAULT_RESOLUTION = 8


class H3KitError(ValueError):
    """Raised for inputs the kernel refuses to guess about."""


def _h3_version() -> str:
    try:
        from importlib.metadata import version

        return version("h3")
    except Exception:  # pragma: no cover
        return "unknown"


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def resolve_geojson(value: Any) -> dict[str, Any]:
    """Accept inline GeoJSON (dict or JSON string) or a ``file://`` URI."""
    if isinstance(value, str):
        if value.startswith("file://"):
            with Path(urlparse(value).path).open(encoding="utf-8") as f:
                return json.load(f)
        return json.loads(value)
    if isinstance(value, dict):
        return value
    raise H3KitError("expected GeoJSON dict, JSON string or file:// URI")


def _cell_polygon_rd(cell: str):
    boundary = h3.cell_to_boundary(cell, geo_json=True)  # GeoJSON [lng, lat] ring
    return sh_transform(_TO_RD.transform, shape(boundary))


def polygon_to_cells(
    polygon: Any,
    resolution: Any = DEFAULT_RESOLUTION,
    *,
    restrict_cells: Any = None,
    compact: Any = False,
) -> dict[str, Any]:
    """Cell set + per-cell coverage fraction for one polygon layer.

    Selection semantics: cells whose centre lies in the polygon (the
    notebook's polyfill behaviour), unless ``restrict_cells`` is given —
    then coverage is computed for exactly those cells (cross-track
    overlay mode). ``coverageFraction`` is area(cell ∩ polygon) /
    area(cell), both planar EPSG:28992. Invalid input geometry is
    repaired with ``make_valid`` and recorded in ``notes``.
    """
    res = _as_int(resolution, DEFAULT_RESOLUTION)
    if not 0 <= res <= 15:
        raise H3KitError(f"resolution {res} out of range 0..15")

    doc = resolve_geojson(polygon)
    feats = (doc.get("features") if doc.get("type") == "FeatureCollection"
             else [{"geometry": doc}])
    notes: set[str] = set()
    geoms = []
    for feat in feats or []:
        g = shape(feat["geometry"])
        if not g.is_valid:
            g = make_valid(g)
            notes.add("input-geometry-made-valid")
        geoms.append(g)
    if not geoms:
        raise H3KitError("no geometry found in polygon input")
    u4326 = unary_union(geoms)
    poly_rd = sh_transform(_TO_RD.transform, u4326)

    if restrict_cells is not None:
        cells: set[str] = set()
        for c in restrict_cells:
            c = str(c)
            if not h3.is_valid_cell(c):
                raise H3KitError(f"not an H3 cell: {c!r}")
            if h3.get_resolution(c) != res:
                raise H3KitError(f"cell {c} at resolution "
                                 f"{h3.get_resolution(c)} != requested {res}")
            cells.add(c)
    else:
        cells = set(h3.polygon_to_cells(mapping(u4326), res))

    rows = []
    for cell in sorted(cells):
        cell_rd = _cell_polygon_rd(cell)
        inter = poly_rd.intersection(cell_rd)
        if not inter.is_valid:
            inter = make_valid(inter)
        area = cell_rd.area
        rows.append({
            "cell": cell,
            "coverageFraction": round(inter.area / area, 6) if area else 0.0,
            "cellAreaM2": round(area, 1),
        })

    result: dict[str, Any] = {
        "resolution": res,
        "cellCount": len(rows),
        "cells": rows,
        "crs": "cells-EPSG:4326-areas-EPSG:28992",
        "h3Version": _h3_version(),
    }
    if notes:
        result["notes"] = sorted(notes)
    if _as_bool(compact) and restrict_cells is None:
        selected = {r["cell"] for r in rows if r["coverageFraction"] >= 0.5}
        result["compactedCells"] = sorted(h3.compact_cells(selected))
    return result
```

- [ ] **Step 6: Run kernel tests**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: PASS (8 tests). If `h3.polygon_to_cells` rejects the mapped geometry with holes, pass `mapping(u4326.buffer(0))` — do not change semantics.

- [ ] **Step 7: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/common/h3kit.py nldt/tests/test_h3kit.py nldt/requirements.txt
git commit -m "H3 kernel: h3kit polygon-to-cells coverage core (planar EPSG:28992, v4 API)"
```

---

### Task 2: `h3kit` — cells-to-GeoJSON, point join, KNN, hierarchy

**Files:**
- Modify: `nldt/services/common/h3kit.py` (append functions + imports)
- Modify: `nldt/tests/test_h3kit.py` (append tests)

**Interfaces:**
- Consumes: `h3kit.polygon_to_cells`, `_as_int`, `resolve_geojson` (Task 1).
- Produces:
  - `h3kit.cells_to_geojson(cells) -> dict` (FeatureCollection, one Feature per cell, `properties: {cell, resolution}`)
  - `h3kit.join_points_to_cells(points, cells=None, *, polygon=None, resolution=8) -> dict` → `{"pointCount", "cellCount", "resolution", "perPoint": [{"index","cell","inCells"}], "perCell": [{"cell","count"}], "h3Version"}` — non-Point geometries use their centroid (building footprints)
  - `h3kit.knn(point, candidates, k=1, resolution=8) -> dict` → `{"originCell","resolution","candidateCount","neighbors":[{"index","cell","gridDistance","distanceKm"}]}`; `point`/candidates are `{"lat","lng"}` or `(lat, lng)`
  - `h3kit.children_of(cells, resolution) -> dict` → `{"childResolution", "children": {parent: [children]}, "h3Version"}`

- [ ] **Step 1: Write failing tests** — append to `nldt/tests/test_h3kit.py`:

```python
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
        assert shape(feat["geometry"]).buffer(1e-7).contains(
            __import__("shapely.geometry", fromlist=["Point"]).Point(lng, lat))


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
```

Add to the import block at the top of the test file:

```python
from shapely.geometry import Point, shape
```

and simplify the roundtrip test's containment check to use `Point` directly.

- [ ] **Step 2: Run to verify failure**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: FAIL — `AttributeError: ... no attribute 'cells_to_geojson'`

- [ ] **Step 3: Implement** — append to `nldt/services/common/h3kit.py` (and extend `__all__`):

```python
import math

__all__ += ["cells_to_geojson", "join_points_to_cells", "knn", "children_of"]


def cells_to_geojson(cells: Any) -> dict[str, Any]:
    """Cell-boundary FeatureCollection (RFC 7946), one feature per cell."""
    feats = []
    for cell in sorted({str(c) for c in cells}):
        if not h3.is_valid_cell(cell):
            raise H3KitError(f"not an H3 cell: {cell!r}")
        feats.append({
            "type": "Feature",
            "properties": {"cell": cell, "resolution": h3.get_resolution(cell)},
            "geometry": h3.cell_to_boundary(cell, geo_json=True),
        })
    return {"type": "FeatureCollection", "features": feats,
            "properties": {"computedBy": "nldt-h3kit/1.0",
                           "h3Version": _h3_version()}}


def _point_latlng(point: Any) -> tuple[float, float]:
    if isinstance(point, dict):
        return float(point["lat"]), float(point["lng"])
    lat, lng = point
    return float(lat), float(lng)


def join_points_to_cells(
    points: Any,
    cells: Any = None,
    *,
    polygon: Any = None,
    resolution: Any = DEFAULT_RESOLUTION,
) -> dict[str, Any]:
    """Index points into cells (notebook §II.4); non-Point geometries join
    by centroid (building footprints). Either ``cells`` or ``polygon``."""
    if cells is None and polygon is None:
        raise H3KitError("join needs either cells or polygon")
    if cells is None:
        cells = [r["cell"] for r in polygon_to_cells(polygon, resolution)["cells"]]
    cell_set = {str(c) for c in cells}
    res = (h3.get_resolution(next(iter(sorted(cell_set))))
           if cell_set else _as_int(resolution, DEFAULT_RESOLUTION))

    doc = resolve_geojson(points)
    feats = (doc.get("features") if doc.get("type") == "FeatureCollection"
             else [{"geometry": doc, "properties": {}}])
    per_point, counts = [], {}
    for i, feat in enumerate(feats or []):
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Point":
            lng, lat = geom["coordinates"][:2]
        else:  # footprint → centroid (notebook §II.4 bus-stop analog)
            lng, lat = shape(geom).centroid.x, shape(geom).centroid.y
        cell = h3.latlng_to_cell(float(lat), float(lng), res)
        per_point.append({"index": i, "cell": cell, "inCells": cell in cell_set})
        if cell in cell_set:
            counts[cell] = counts.get(cell, 0) + 1
    return {
        "pointCount": len(per_point),
        "cellCount": len(cell_set),
        "resolution": res,
        "perPoint": per_point,
        "perCell": [{"cell": c, "count": counts[c]} for c in sorted(counts)],
        "h3Version": _h3_version(),
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def knn(point: Any, candidates: Any, k: Any = 1,
        resolution: Any = DEFAULT_RESOLUTION) -> dict[str, Any]:
    """K nearest candidates by (grid_distance, haversine) — notebook §II.3."""
    lat0, lng0 = _point_latlng(point)
    res = _as_int(resolution, DEFAULT_RESOLUTION)
    origin = h3.latlng_to_cell(lat0, lng0, res)
    rows = []
    for i, cand in enumerate(candidates):
        lat, lng = _point_latlng(cand)
        cell = h3.latlng_to_cell(lat, lng, res)
        try:
            dist = int(h3.grid_distance(origin, cell))
        except Exception:  # pentagon-distortion: not reachable by grid
            dist = 10 ** 6
        rows.append({"index": i, "cell": cell, "gridDistance": dist,
                     "distanceKm": round(_haversine_km(lat0, lng0, lat, lng), 4)})
    rows.sort(key=lambda r: (r["gridDistance"], r["distanceKm"], r["index"]))
    return {"originCell": origin, "resolution": res,
            "candidateCount": len(rows),
            "neighbors": rows[:max(1, _as_int(k, 1))],
            "h3Version": _h3_version()}


def children_of(cells: Any, resolution: Any) -> dict[str, Any]:
    """Parent → children drill-down (notebook §I.2 hierarchy)."""
    res = _as_int(resolution, DEFAULT_RESOLUTION)
    out: dict[str, list[str]] = {}
    for cell in sorted({str(c) for c in cells}):
        if not h3.is_valid_cell(cell):
            raise H3KitError(f"not an H3 cell: {cell!r}")
        if h3.get_resolution(cell) >= res:
            raise H3KitError(f"cell {cell}: child resolution {res} must "
                             "exceed the parent's")
        out[cell] = sorted(h3.cell_to_children(cell, res))
    return {"childResolution": res, "children": out, "h3Version": _h3_version()}
```

- [ ] **Step 4: Run tests**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: PASS (17 tests)

- [ ] **Step 5: Commit**

```bash
git add nldt/services/common/h3kit.py nldt/tests/test_h3kit.py
git commit -m "H3 kernel: cells-to-geojson, point join (centroid footprints), KNN, hierarchy"
```

---

### Task 3: `h3kit` — global Moran's I

**Files:**
- Modify: `nldt/services/common/h3kit.py` (append)
- Modify: `nldt/tests/test_h3kit.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `h3kit.morans_i(values, permutations=199) -> dict` → `{"n", "permutations", "moransI" (number|null), "expectedI" (number|null), "pValue" (number|null), "notes": [...]}`. `values` accepts a `{cell: value}` map, `[{"cell", "value"|"count"|"coverageFraction"}]` rows, or a join output `{"perCell": [...]}`. Weights: binary `grid_disk(cell, 1)` neighbours present in the set. Permutations seeded `random.Random(0)`.

- [ ] **Step 1: Write failing tests** — append to `nldt/tests/test_h3kit.py`:

```python
def _disk_values(res=9):
    centre = h3.latlng_to_cell(52.09, 5.11, res)
    clustered = {centre: 10.0}
    for c in h3.grid_disk(centre, 1) - {centre}:
        clustered[c] = 10.0
    for c in h3.grid_disk(centre, 2) - h3.grid_disk(centre, 1):
        clustered[c] = 1.0
    return clustered


def test_morans_i_clustered_is_strongly_positive():
    stat = h3kit.morans_i(_disk_values())
    assert stat["n"] == 19
    assert stat["moransI"] > 0.3
    assert stat["pValue"] <= 0.05
    assert stat["expectedI"] == round(-1 / 18, 9)


def test_morans_i_checkerboard_is_negative():
    centre = h3.latlng_to_cell(52.09, 5.11, 9)
    ring = [centre] + sorted(h3.grid_disk(centre, 1) - {centre})
    values = {c: (10.0 if i % 2 == 0 else 1.0) for i, c in enumerate(ring)}
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q -k morans`
Expected: FAIL — no attribute `morans_i`

- [ ] **Step 3: Implement** — append to `nldt/services/common/h3kit.py` (extend `__all__` with `"morans_i"`, add `import random` and `from typing import Mapping` at the top):

```python
def _normalise_values(values: Any) -> dict[str, float]:
    if isinstance(values, Mapping):
        if "perCell" in values:  # a h3-spatial-join-points output
            values = values["perCell"]
        else:
            return {str(k): float(v) for k, v in values.items()}
    out: dict[str, float] = {}
    for row in values:
        cell = str(row["cell"])
        if "value" in row:
            out[cell] = float(row["value"])
        elif "count" in row:
            out[cell] = float(row["count"])
        else:
            out[cell] = float(row["coverageFraction"])
    return out


def morans_i(values: Any, permutations: Any = 199) -> dict[str, Any]:
    """Global Moran's I from scratch over grid_disk(1) neighbourhoods
    (notebook §IV.3, no PySAL). One-sided p-value via seeded permutations."""
    import random as _random

    vals = _normalise_values(values)
    n = len(vals)
    perms = _as_int(permutations, 199)
    empty = {"moransI": None, "expectedI": None, "pValue": None}
    if n < 3:
        return {"n": n, "permutations": perms, **empty,
                "notes": ["too few cells for Moran's I"]}
    cells = sorted(vals)
    idx = {c: i for i, c in enumerate(cells)}
    mean = sum(vals.values()) / n
    z = [vals[c] - mean for c in cells]
    den = sum(v * v for v in z)
    cell_set = set(cells)
    nbr_idx = {i: sorted(idx[c2] for c2 in (h3.grid_disk(c, 1) - {c})
                         if c2 in cell_set)
               for i, c in enumerate(cells)}
    s0 = sum(len(v) for v in nbr_idx.values())
    if s0 == 0:
        return {"n": n, "permutations": perms, **empty,
                "notes": ["no adjacent cells in the value set"]}
    if den == 0:
        return {"n": n, "permutations": perms, **empty,
                "notes": ["no variance in values"]}

    def stat(zvals: list[float]) -> float:
        num = sum(zvals[i] * zvals[j]
                  for i in range(n) for j in nbr_idx[i])
        return (n / s0) * (num / den)

    observed = stat(z)
    rng = _random.Random(0)
    perm_z = list(z)
    ge = 0
    for _ in range(perms):
        rng.shuffle(perm_z)
        if stat(perm_z) >= observed:
            ge += 1
    return {"n": n, "permutations": perms,
            "moransI": round(observed, 9),
            "expectedI": round(-1.0 / (n - 1), 9),
            "pValue": round((ge + 1) / (perms + 1), 6),
            "notes": []}
```

- [ ] **Step 4: Run tests**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: PASS (22 tests)

- [ ] **Step 5: Commit**

```bash
git add nldt/services/common/h3kit.py nldt/tests/test_h3kit.py
git commit -m "H3 kernel: deterministic global Moran's I (grid_disk neighbourhoods, seeded permutations)"
```

---

### Task 4: `h3coverage` output contract (nldt schema)

**Files:**
- Create: `nldt/schemas/h3coverage.schema.json`
- Modify: `nldt/tests/test_h3kit.py` (one validation test)

**Interfaces:**
- Consumes: `h3kit.polygon_to_cells` output shape (Tasks 1–2).
- Produces: `h3coverage.schema.json` — validated via the existing `services.common.schema.validate_instance(instance, "h3coverage.schema.json")`. Mirrored byte-identical into `poc/schemas/` in Task 7.

- [ ] **Step 1: Write the failing test** — append to `nldt/tests/test_h3kit.py`:

```python
def test_coverage_output_validates_against_contract():
    from services.common.schema import validate_instance

    validate_instance(h3kit.polygon_to_cells(SQUARE, 8), "h3coverage.schema.json")
    validate_instance(h3kit.polygon_to_cells(SQUARE, 9, compact=True),
                      "h3coverage.schema.json")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q -k contract`
Expected: FAIL — schema file not found

- [ ] **Step 3: Create `nldt/schemas/h3coverage.schema.json`:**

```json
{
  "$schema": "http://json-schema.org/draft/2020-12/schema#",
  "$id": "https://nldt.local/schemas/h3coverage.schema.json",
  "title": "H3Coverage",
  "description": "Output contract of the h3-polygon-to-cells process: cell set with planar EPSG:28992 coverage fractions. Mirrored into poc/schemas/ for the PoC bridge; keep both copies byte-identical.",
  "type": "object",
  "additionalProperties": false,
  "required": ["resolution", "cellCount", "cells", "crs", "h3Version"],
  "properties": {
    "resolution": {"type": "integer", "minimum": 0, "maximum": 15},
    "cellCount": {"type": "integer", "minimum": 0},
    "cells": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["cell", "coverageFraction", "cellAreaM2"],
        "properties": {
          "cell": {"type": "string", "pattern": "^[0-9a-f]{15,16}$"},
          "coverageFraction": {"type": "number", "minimum": 0, "maximum": 1},
          "cellAreaM2": {"type": "number", "exclusiveMinimum": 0}
        }
      }
    },
    "crs": {"const": "cells-EPSG:4326-areas-EPSG:28992"},
    "h3Version": {"type": "string"},
    "notes": {"type": "array", "items": {"type": "string"}},
    "compactedCells": {"type": "array", "items": {"type": "string", "pattern": "^[0-9a-f]{15,16}$"}}
  }
}
```

- [ ] **Step 4: Run tests**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3kit.py -q`
Expected: PASS (23 tests)

- [ ] **Step 5: Commit**

```bash
git add nldt/schemas/h3coverage.schema.json nldt/tests/test_h3kit.py
git commit -m "H3 contract: h3coverage.schema.json output schema (nldt)"
```

---

### Task 5: Process wiring — five `h3-*` OGC API Processes

**Files:**
- Modify: `nldt/services/process_adapter/handlers.py` (`PROCESS_DEFINITIONS` + `execute_local`)
- Modify: `nldt/services/catalog_adapter/seed.py` (seed tuples)
- Create: `nldt/tests/test_h3_processes.py`

**Interfaces:**
- Consumes: `h3kit` functions (Tasks 1–3); existing `execute_local` dispatch pattern (`handlers.py:88-99`).
- Produces: `execute_local("h3-polygon-to-cells", {...}) -> {"coverage": <H3Coverage>}`, `h3-cells-to-geojson -> {"features": FC}`, `h3-spatial-join-points -> {"join": ...}`, `h3-knn -> {"neighbors": ...}`, `h3-morans-i -> {"statistics": ...}`. PROV comes free via `route_execute`.

- [ ] **Step 1: Write failing process tests** — create `nldt/tests/test_h3_processes.py`:

```python
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
    values = {c: 10.0 for c in h3.grid_disk(centre, 1)}
    values.update({c: 1.0 for c in
                   h3.grid_disk(centre, 2) - h3.grid_disk(centre, 1)})
    out = execute_local("h3-morans-i", {"values": values})
    assert out["statistics"]["n"] == 19
    assert out["statistics"]["moransI"] > 0.3


def test_route_execute_wraps_h3_with_prov():
    _job_id, outputs, prov = route_execute(
        "h3-polygon-to-cells", {"polygon": SQUARE, "resolution": 9})
    assert outputs["coverage"]["cellCount"] > 0
    assert prov["activity"] == "nldt:ProcessExecution/h3-polygon-to-cells"


def test_unknown_cell_input_raises():
    with pytest.raises(h3kit.H3KitError):
        execute_local("h3-cells-to-geojson", {"cells": ["garbage"]})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3_processes.py -q`
Expected: FAIL — `h3-polygon-to-cells` not in `PROCESS_DEFINITIONS` / KeyError

- [ ] **Step 3: Wire the processes** — in `nldt/services/process_adapter/handlers.py`:

Add import after the existing `services.common.geo` import:

```python
from services.common import h3kit
```

Append five entries inside `PROCESS_DEFINITIONS` (after `"compute-area-statistics"`):

```python
    "h3-polygon-to-cells": {
        "id": "h3-polygon-to-cells",
        "title": "H3 polygon to cells",
        "description": "Discretise a GeoJSON polygon layer into H3 cells with planar EPSG:28992 coverage fractions; optional restrictCells / compact",
        "version": "1.0.0",
        "inputs": {
            "polygon": {"title": "Polygon (GeoJSON or file:// URI)",
                        "schema": {"type": ["object", "string"]}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
            "restrictCells": {"title": "Compute coverage for exactly these cells",
                              "schema": {"type": "array",
                                         "items": {"type": "string"}}},
            "compact": {"title": "Also emit a compacted cell set",
                        "schema": {"type": "boolean"}},
        },
        "outputs": {
            "coverage": {"title": "H3Coverage", "schema": {"type": "object"}},
        },
    },
    "h3-cells-to-geojson": {
        "id": "h3-cells-to-geojson",
        "title": "H3 cells to GeoJSON",
        "description": "Cell boundaries as a GeoJSON FeatureCollection",
        "version": "1.0.0",
        "inputs": {
            "cells": {"title": "H3 cell indexes",
                      "schema": {"type": "array", "items": {"type": "string"}}},
        },
        "outputs": {
            "features": {"title": "FeatureCollection", "schema": {"type": "object"}},
        },
    },
    "h3-spatial-join-points": {
        "id": "h3-spatial-join-points",
        "title": "H3 spatial join (points)",
        "description": "Index points (or footprint centroids) into cells; counts per cell",
        "version": "1.0.0",
        "inputs": {
            "points": {"title": "Points (GeoJSON or file:// URI)",
                       "schema": {"type": ["object", "string"]}},
            "cells": {"title": "Cell set (else polygon+resolution)",
                      "schema": {"type": "array", "items": {"type": "string"}}},
            "polygon": {"title": "Polygon to derive cells from",
                        "schema": {"type": ["object", "string"]}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
        },
        "outputs": {
            "join": {"title": "Join result", "schema": {"type": "object"}},
        },
    },
    "h3-knn": {
        "id": "h3-knn",
        "title": "H3 K nearest neighbours",
        "description": "Nearest candidates by H3 grid distance with haversine tie-break",
        "version": "1.0.0",
        "inputs": {
            "point": {"title": "Origin {lat, lng}", "schema": {"type": "object"}},
            "candidates": {"title": "Candidate points",
                           "schema": {"type": "array"}},
            "k": {"title": "K (default 1)", "schema": {"type": "integer"}},
            "resolution": {"title": "H3 resolution (default 8)",
                           "schema": {"type": "integer"}},
        },
        "outputs": {
            "neighbors": {"title": "Ranked neighbours", "schema": {"type": "object"}},
        },
    },
    "h3-morans-i": {
        "id": "h3-morans-i",
        "title": "Global Moran's I (H3)",
        "description": "Spatial autocorrelation over grid_disk neighbourhoods; seeded permutation p-value",
        "version": "1.0.0",
        "inputs": {
            "values": {"title": "Cell values (map, rows, or join perCell)",
                       "schema": {"type": ["object", "array"]}},
            "permutations": {"title": "Permutations (default 199)",
                             "schema": {"type": "integer"}},
        },
        "outputs": {
            "statistics": {"title": "Moran's I statistics", "schema": {"type": "object"}},
        },
    },
```

Extend `execute_local` (before the final `raise KeyError`):

```python
    if process_id == "h3-polygon-to-cells":
        return {"coverage": h3kit.polygon_to_cells(
            inputs["polygon"], inputs.get("resolution", 8),
            restrict_cells=inputs.get("restrictCells"),
            compact=inputs.get("compact", False))}
    if process_id == "h3-cells-to-geojson":
        return {"features": h3kit.cells_to_geojson(list(inputs["cells"]))}
    if process_id == "h3-spatial-join-points":
        return {"join": h3kit.join_points_to_cells(
            inputs["points"], inputs.get("cells"),
            polygon=inputs.get("polygon"),
            resolution=inputs.get("resolution", 8))}
    if process_id == "h3-knn":
        return {"neighbors": h3kit.knn(
            inputs["point"], inputs["candidates"],
            inputs.get("k", 1), inputs.get("resolution", 8))}
    if process_id == "h3-morans-i":
        return {"statistics": h3kit.morans_i(
            inputs["values"], inputs.get("permutations", 199))}
```

- [ ] **Step 4: Add catalog seed records** — in `nldt/services/catalog_adapter/seed.py`, extend the `processes` list:

```python
    processes = [
        ("fetch-features", "Fetch GeoJSON features from URI"),
        ("spatial-intersection", "Intersect two feature collections"),
        ("compute-area-statistics", "Compute area statistics"),
        ("h3-polygon-to-cells", "H3 hex coverage of a polygon layer"),
        ("h3-cells-to-geojson", "H3 cell boundaries as GeoJSON"),
        ("h3-spatial-join-points", "Join points to H3 cells (counts per cell)"),
        ("h3-knn", "K nearest points by H3 grid distance"),
        ("h3-morans-i", "Global Moran's I over H3 cell values"),
    ]
```

- [ ] **Step 5: Run tests**

Run: `cd nldt && .venv/bin/python -m pytest tests -q`
Expected: PASS (29 existing + 23 kernel + 8 process = 60)

- [ ] **Step 6: Commit**

```bash
git add nldt/services/process_adapter/handlers.py nldt/services/catalog_adapter/seed.py nldt/tests/test_h3_processes.py
git commit -m "H3 processes: five h3-* OGC processes wired (kernel dispatch, catalog seeds, PROV via router)"
```

---

### Task 6: `hex-overlay-analysis` recipe + points fixture

**Files:**
- Create: `nldt/examples/hex-points.geojson` (generated)
- Create: `nldt/recipes/hex-overlay-analysis.json`
- Modify: `nldt/tests/test_h3_processes.py` (append recipe test)

**Interfaces:**
- Consumes: `fetch-features` + the five h3 processes; `run_recipe` step-reference syntax (`${recipe.inputs.X}`, `${steps.<id>.outputs.<key>}`) exactly as in `recipes/spatial-overlay-analysis.json`.
- Produces: recipe id `hex-overlay-analysis` with outputs `coverage`, `join`, `autocorrelation` (used by Task 7's fixture generator and by agents/MCP automatically).

- [ ] **Step 1: Generate the points fixture inside/near the AOI** — run once:

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python - <<'EOF'
import json
from pathlib import Path
from shapely.geometry import shape, mapping, Point

aoi = json.loads(Path("examples/aoi.geojson").read_text())
geom = (aoi["features"][0]["geometry"] if aoi.get("type") == "FeatureCollection"
        else aoi)
g = shape(geom)
c = g.centroid
coords = [[c.x, c.y], [c.x + 0.001, c.y + 0.001], [c.x - 0.001, c.y + 0.001],
          [4.9000, 52.0000]]  # last one deliberately far outside
fc = {"type": "FeatureCollection", "name": "hex-points",
      "features": [{"type": "Feature", "properties": {"id": f"p{i}"},
                    "geometry": mapping(Point(x, y))} for i, (x, y)
                   in enumerate(coords)]}
Path("examples/hex-points.geojson").write_text(json.dumps(fc, indent=1) + "\n")
print("centroid:", c.x, c.y, "| wrote examples/hex-points.geojson")
EOF
```

- [ ] **Step 2: Write the failing recipe test** — append to `nldt/tests/test_h3_processes.py`:

```python
def test_hex_overlay_recipe_end_to_end():
    import json
    from pathlib import Path

    from services.recipe_runner import run_recipe

    examples = Path(__file__).resolve().parents[1] / "examples"
    with (examples / "aoi.geojson").open() as f:
        aoi = json.load(f)
    result = run_recipe("hex-overlay-analysis", {
        "aoi": aoi,
        "zoneUri": f"file://{examples / 'aoi.geojson'}",
        "pointsUri": f"file://{examples / 'hex-points.geojson'}",
        "resolution": 8,
    })
    assert result["coverage"]["cellCount"] > 0
    assert result["join"]["pointCount"] == 4
    assert sum(1 for r in result["join"]["perPoint"] if r["inCells"]) == 3
    assert result["autocorrelation"]["n"] >= 1
```

- [ ] **Step 3: Run to verify failure**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_h3_processes.py -q -k recipe`
Expected: FAIL — recipe not found

- [ ] **Step 4: Create `nldt/recipes/hex-overlay-analysis.json`:**

```json
{
  "id": "hex-overlay-analysis",
  "title": "Hex Overlay Analysis (H3)",
  "description": "nLDT reference recipe: discretise a zone layer into H3 cells, join point data per cell, and measure spatial autocorrelation — the h3-py urban-analytics pattern on Dutch data (spec 2026-09-09-h3-integration, example 7.6).",
  "version": "1.0.0",
  "tags": ["spatial", "h3", "hex", "aggregation", "autocorrelation"],
  "requiredData": [
    { "id": "zone", "role": "reference_layer", "format": "geojson" },
    { "id": "points", "role": "context_layer", "format": "geojson" }
  ],
  "requiredProcesses": ["fetch-features", "h3-polygon-to-cells", "h3-spatial-join-points", "h3-morans-i"],
  "inputs": {
    "aoi": { "type": "geojson", "description": "Area of interest", "required": false },
    "zoneUri": { "type": "uri", "description": "URI to zone GeoJSON", "required": true },
    "pointsUri": { "type": "uri", "description": "URI to points GeoJSON", "required": true },
    "resolution": { "type": "integer", "description": "H3 resolution (default 8)", "required": false }
  },
  "outputs": {
    "coverage": { "type": "json", "description": "H3Coverage" },
    "join": { "type": "json", "description": "points-per-cell join" },
    "autocorrelation": { "type": "json", "description": "Moran's I statistics" }
  },
  "steps": [
    {
      "id": "fetch-zone",
      "processId": "fetch-features",
      "title": "Fetch zone layer",
      "inputs": { "source": "${recipe.inputs.zoneUri}", "aoi": "${recipe.inputs.aoi}" },
      "outputs": { "features": "zoneFeatures" },
      "backend": "local"
    },
    {
      "id": "fetch-points",
      "processId": "fetch-features",
      "title": "Fetch points layer",
      "inputs": { "source": "${recipe.inputs.pointsUri}", "aoi": "${recipe.inputs.aoi}" },
      "outputs": { "features": "pointsFeatures" },
      "backend": "local"
    },
    {
      "id": "cells",
      "processId": "h3-polygon-to-cells",
      "title": "Discretise zone into H3 cells",
      "inputs": { "polygon": "${steps.fetch-zone.outputs.features}", "resolution": "${recipe.inputs.resolution}" },
      "outputs": { "coverage": "coverage" },
      "backend": "local"
    },
    {
      "id": "join",
      "processId": "h3-spatial-join-points",
      "title": "Join points per cell",
      "inputs": { "points": "${steps.fetch-points.outputs.features}", "polygon": "${steps.fetch-zone.outputs.features}", "resolution": "${recipe.inputs.resolution}" },
      "outputs": { "join": "join" },
      "backend": "local"
    },
    {
      "id": "autocorrelation",
      "processId": "h3-morans-i",
      "title": "Moran's I over cell counts",
      "inputs": { "values": "${steps.join.outputs.join}" },
      "outputs": { "statistics": "autocorrelation" },
      "backend": "local"
    }
  ],
  "visualizationHint": { "preferredFormat": "geojson", "layerTitle": "H3 coverage" },
  "riskLevel": "low",
  "cookbookUri": "http://localhost:8081/recipes/hex-overlay-analysis"
}
```

- [ ] **Step 5: Run tests** — `cd nldt && .venv/bin/python -m pytest tests -q`
Expected: PASS (61). If `run_recipe` rejects a missing optional `resolution`, pass it in the test (it already does).

- [ ] **Step 6: Commit**

```bash
git add nldt/recipes/hex-overlay-analysis.json nldt/examples/hex-points.geojson nldt/tests/test_h3_processes.py
git commit -m "H3 recipe: hex-overlay-analysis (fetch → cells → join → Moran's I) + points fixture"
```

---

### Task 7: poc bridge — `h3step` cache-first client + mirror schema + fixtures

**Files:**
- Create: `poc/pipeline/h3step.py`
- Create: `poc/schemas/h3coverage.schema.json` (byte-identical copy)
- Create: `poc/tests/make_h3_fixtures.py` (manual generator, not a test)
- Create: `poc/tests/test_h3step.py`
- Modify: `poc/pipeline/contracts.py` (`SCHEMA_NAMES` tuple, line ~37)

**Interfaces:**
- Consumes: `nldt/services/cli.py run-process <pid> --input key=value` (JSON-valued inputs via `file://` URIs; scalar inputs as plain strings — the CLI keeps non-`{`-prefixed values as strings, the kernel `_as_int`/`_as_bool`-parses them).
- Produces:
  - `h3step.H3UnavailableError(RuntimeError)`
  - `h3step.call(process_id: str, inputs: dict, *, refresh: bool = False) -> dict` (the process **outputs** dict, e.g. `{"coverage": ...}`)
  - `h3step.fingerprint(process_id, inputs) -> str` (sha256 over canonical JSON)
  - `h3step.scenario_metrics(geometry_payload_4326, control_cells=None, resolution=8, *, refresh=False) -> dict` → `{"resolution", "cellCount", "moransI", "pValue", "cellsGainedVsControl", "cellsLostVsControl", ["cells": sorted list — present when control_cells is None, popped by the caller]}` (used by Task 9)
  - cache files `poc/data/cache/h3/<fingerprint>.json` → `{"processId", "fingerprint", "outputs", "cachedAt"}`
  - env `POC_H3_OFFLINE=1` ⇒ cache miss raises instead of invoking the subprocess

- [ ] **Step 1: Mirror the schema and register the contract name**

```bash
cd /Users/marc/Projecten/ldttoolbox
cp nldt/schemas/h3coverage.schema.json poc/schemas/h3coverage.schema.json
```

In `poc/pipeline/contracts.py`, extend `SCHEMA_NAMES` (add after `"crosstrack-report",`):

```python
    "h3coverage",
```

- [ ] **Step 2: Write the failing tests** — create `poc/tests/test_h3step.py`:

```python
"""Offline tests for the poc H3 bridge (cache-first, no subprocess ever).

Fixtures under poc/data/cache/h3/ are generated once (live) by
poc/tests/make_h3_fixtures.py and committed; POC_H3_OFFLINE=1 makes any
cache miss an error instead of a subprocess invocation.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, h3step  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "h3_fixtures"

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}


def _fc(geom):
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": geom}]}


class OfflineEnv(unittest.TestCase):
    def setUp(self):
        self._patcher = mock.patch.dict(os.environ, {"POC_H3_OFFLINE": "1"})
        self._patcher.start()
        self.addCleanup(self._patcher.stop)


class TestCacheFirstBridge(OfflineEnv):

    def test_cached_call_never_spawns_subprocess(self):
        inputs = json.loads((FIXDIR / "square-res9-input.json").read_text())
        with mock.patch.object(h3step.subprocess, "run",
                               side_effect=AssertionError("subprocess invoked")):
            out = h3step.call("h3-polygon-to-cells", inputs)
        contracts.validate(out["coverage"], "h3coverage")
        self.assertEqual(out, h3step.call("h3-polygon-to-cells", inputs))

    def test_offline_cache_miss_raises(self):
        with self.assertRaises(h3step.H3UnavailableError):
            h3step.call("h3-polygon-to-cells",
                        {"polygon": _fc(SQUARE), "resolution": 7})

    def test_fingerprint_is_order_insensitive(self):
        a = h3step.fingerprint("p", {"x": 1, "y": [1, 2]})
        b = h3step.fingerprint("p", {"y": [1, 2], "x": 1})
        self.assertEqual(a, b)

    def test_scenario_metrics_from_fixtures(self):
        inputs = json.loads((FIXDIR / "square-res8-input.json").read_text())
        out = h3step.call("h3-polygon-to-cells", inputs)
        self.assertGreater(out["coverage"]["cellCount"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `cd poc && ../nldt/.venv/bin/python -m unittest tests.test_h3step -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.h3step`

- [ ] **Step 4: Implement `poc/pipeline/h3step.py`:**

```python
"""Cache-first bridge from the poc pipeline to the nldt H3 processes.

The H3 kernel lives once, in nldt (spec 2026-09-09-h3-integration,
architecture C). This module is the only poc-side coupling:

* cache-first — ``poc/data/cache/h3/<sha256>.json`` makes every replay
  offline and byte-stable (same pattern as the geodata dual-CRS cache);
* on miss, the nldt CLI runs the process as a subprocess (no service, no
  python-path coupling — the process boundary IS the architecture);
* ``POC_H3_OFFLINE=1`` turns a cache miss into an error, so unittest
  runs can never spawn a subprocess or touch the network.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

POC_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = POC_ROOT.parent
NLDT_ROOT = WORKSPACE / "nldt"
NLDT_CLI = NLDT_ROOT / "services" / "cli.py"
CACHE_DIR = POC_ROOT / "data" / "cache" / "h3"
REQ_DIR = CACHE_DIR / "req"


class H3UnavailableError(RuntimeError):
    """No cached H3 response and offline mode forbids invoking nldt."""


def fingerprint(process_id: str, inputs: Dict[str, Any]) -> str:
    payload = json.dumps({"processId": process_id, "inputs": inputs},
                         sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def call(process_id: str, inputs: Dict[str, Any], *,
         refresh: bool = False) -> Dict[str, Any]:
    """Invoke one nldt h3-* process; returns its ``outputs`` dict."""
    fp = fingerprint(process_id, inputs)
    cache = CACHE_DIR / f"{fp}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))["outputs"]

    if os.environ.get("POC_H3_OFFLINE") == "1":
        raise H3UnavailableError(
            f"H3 process {process_id!r} not in cache ({cache.name}) and "
            "POC_H3_OFFLINE=1 forbids invocation — regenerate fixtures with "
            "poc/tests/make_h3_fixtures.py")

    REQ_DIR.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(NLDT_CLI), "run-process", process_id]
    for key, value in sorted(inputs.items()):
        if isinstance(value, (dict, list)):
            req = REQ_DIR / f"{fp}-{key}.json"
            req.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            argv += ["--input", f"{key}=file://{req}"]
        else:
            argv += ["--input", f"{key}={value}"]
    proc = subprocess.run(argv, cwd=str(NLDT_ROOT), capture_output=True,
                          text=True, check=True)
    job = json.loads(proc.stdout)
    outputs = job["outputs"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    record = {"processId": process_id, "fingerprint": fp, "outputs": outputs,
              "prov": job.get("prov")}
    cache.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return outputs


def scenario_metrics(geometry_payload_4326: Dict[str, Any],
                     control_cells: Optional[set] = None,
                     resolution: int = 8, *,
                     refresh: bool = False) -> Dict[str, Any]:
    """Hex summary for one scenario zone (Task 9 wiring): cell set (centre
    + ≥50% coverage), Moran's I over coverage fractions, and cell deltas
    vs the control when ``control_cells`` is given."""
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": geometry_payload_4326}]}
    cov = call("h3-polygon-to-cells",
               {"polygon": fc, "resolution": resolution}, refresh=refresh)["coverage"]
    cells = {r["cell"] for r in cov["cells"] if r["coverageFraction"] >= 0.5}
    stats = call("h3-morans-i",
                 {"values": {"perCell": cov["cells"]}}, refresh=refresh)["statistics"]
    out: Dict[str, Any] = {
        "resolution": resolution,
        "cellCount": len(cells),
        "moransI": stats["moransI"],
        "pValue": stats.get("pValue"),
    }
    if control_cells is None:
        out["cells"] = sorted(cells)
        out["cellsGainedVsControl"] = None
        out["cellsLostVsControl"] = None
    else:
        out["cellsGainedVsControl"] = len(cells - control_cells)
        out["cellsLostVsControl"] = len(control_cells - cells)
    return out
```

- [ ] **Step 5: Create the fixture generator `poc/tests/make_h3_fixtures.py`** (manual utility — run with `POC_H3_OFFLINE` *unset*):

```python
"""Regenerate the committed H3 cache fixtures for test_h3step.

Usage (live, needs nldt/.venv with h3 installed):

    cd poc && POC_H3_OFFLINE= ../nldt/.venv/bin/python tests/make_h3_fixtures.py

Writes input copies next to the fixtures so tests construct byte-identical
request dicts. Commit poc/data/cache/h3/<fp>.json + tests/h3_fixtures/*.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC_ROOT))

from pipeline import h3step  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "h3_fixtures"

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}


def fc(geom):
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": geom}]}


def main() -> int:
    FIXDIR.mkdir(parents=True, exist_ok=True)
    cases = {
        "square-res9-input.json": ("h3-polygon-to-cells",
                                   {"polygon": fc(SQUARE), "resolution": 9}),
        "square-res8-input.json": ("h3-polygon-to-cells",
                                   {"polygon": fc(SQUARE), "resolution": 8}),
    }
    for name, (pid, inputs) in sorted(cases.items()):
        out = h3step.call(pid, inputs)  # live: writes the cache entry
        (FIXDIR / name).write_text(json.dumps(inputs, sort_keys=True) + "\n")
        print(f"[fixture] {name} -> {h3step.fingerprint(pid, inputs)}.json "
              f"(coverage cells: {out['coverage']['cellCount']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it, then re-run the tests:

```bash
cd /Users/marc/Projecten/ldttoolbox/poc
POC_H3_OFFLINE= ../nldt/.venv/bin/python tests/make_h3_fixtures.py
POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_h3step -v
```

Expected: 4 tests PASS with no subprocess.

- [ ] **Step 6: Run the full poc suite offline**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests`
Expected: 154 baseline (now green incl. the 4 former geopandas errors → 158) + 4 new = 162, all pass, 0 errors.

- [ ] **Step 7: Commit**

```bash
git add poc/pipeline/h3step.py poc/pipeline/contracts.py poc/schemas/h3coverage.schema.json poc/tests/test_h3step.py poc/tests/make_h3_fixtures.py poc/tests/h3_fixtures/ poc/data/cache/h3/
git commit -m "H3 bridge: cache-first poc h3step client (POC_H3_OFFLINE, file:// inputs), mirror contract, committed fixtures"
```

(Note: `poc/data/cache/h3/req/` is scratch — do not commit it; commit only `<fp>.json` entries.)

---

### Task 8: Crosstrack per-cell conflict overlay

**Files:**
- Modify: `poc/pipeline/crosstrack.py` (add `attach_h3_overlay`, extend `conflict_markdown`)
- Modify: `poc/schemas/crosstrack-report.schema.json` (optional `h3Overlay`)
- Modify: `poc/crosstrack/run.py` (flags + wiring + artifact + PROV entity)
- Modify: `poc/tests/test_crosstrack.py` (append tests)

**Interfaces:**
- Consumes: `h3step.call` (Task 7); `crosstrack.union_zone`, `engine.to_zone_geometry(geom_rd, round_dp=6)[0]["payload"]`, `contracts.validate` (existing).
- Produces:
  - `crosstrack.attach_h3_overlay(report, tracks, *, zone_id, layers, resolution=8, call=None) -> dict | None` — mutates `report["h3Overlay"]` (+ degradations when unavailable), re-validates the report, returns the artifact for `h3-crosstrack.json`: `{"zoneId", "resolution", "computedBy", "weightedConflictSharePct", "notes", "cells": [{"cell", "inZoneFraction", "conflictFraction", "cellAreaM2"}]}`
  - report block `h3Overlay`: `{"zoneId", "resolution", "cells", "conflictCells", "weightedConflictSharePct", "artifactFile"}` (all required when present; `weightedConflictSharePct` nullable)

- [ ] **Step 1: Extend the schema** — in `poc/schemas/crosstrack-report.schema.json`, add to `properties` (alongside `sharedZones`; root stays `additionalProperties: false`, so this key must exist even when absent from instances — optional = not in `required`):

```json
    "h3Overlay": {
      "type": "object",
      "additionalProperties": false,
      "required": ["zoneId", "resolution", "cells", "conflictCells", "weightedConflictSharePct", "artifactFile"],
      "properties": {
        "zoneId": {"type": "string"},
        "resolution": {"type": "integer"},
        "cells": {"type": "integer", "minimum": 0},
        "conflictCells": {"type": "integer", "minimum": 0},
        "weightedConflictSharePct": {"type": ["number", "null"]},
        "artifactFile": {"type": "string"}
      }
    },
```

- [ ] **Step 2: Write failing tests** — append to `poc/tests/test_crosstrack.py` (it already imports `crosstrack`, `contracts`; add `from shapely.geometry import box, mapping` to the module imports if absent):

```python
class TestH3Overlay(unittest.TestCase):

    def _report(self):
        return {
            "id": "XR-T", "generatedAt": "2026-01-01T00:00:00Z",
            "generatedBy": "t", "tracks": [], "conflicts": [],
            "sharedZones": [], "verdict": "pass",
            "validationReportFile": "validation.json",
            "degradations": [], "notes": [],
        }

    def _fake_call(self):
        calls = {"n": 0}

        def call(process_id, inputs):
            assert process_id == "h3-polygon-to-cells"
            calls["n"] += 1
            if inputs.get("restrictCells") is not None:
                return {"coverage": {
                    "resolution": inputs["resolution"],
                    "cellCount": len(inputs["restrictCells"]),
                    "cells": [{"cell": c, "coverageFraction": 0.5,
                               "cellAreaM2": 740000.0}
                              for c in inputs["restrictCells"]],
                    "crs": "cells-EPSG:4326-areas-EPSG:28992",
                    "h3Version": "test"}}
            return {"coverage": {
                "resolution": inputs["resolution"], "cellCount": 2,
                "cells": [{"cell": "c1", "coverageFraction": 0.8,
                           "cellAreaM2": 740000.0},
                          {"cell": "c2", "coverageFraction": 0.8,
                           "cellAreaM2": 740000.0}],
                "crs": "cells-EPSG:4326-areas-EPSG:28992",
                "h3Version": "test"}}

        return call, calls

    def test_attach_h3_overlay_weights_and_revalidates(self):
        layers = {"groene_contour": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": mapping(box(155000, 456000, 165000, 464000))}]}}
        tracks = [{"useCase": "zon", "geometry": box(156000, 457000, 164000, 463000)}]
        call, calls = self._fake_call()
        report = self._report()
        artifact = crosstrack.attach_h3_overlay(
            report, tracks, zone_id="groene_contour", layers=layers, call=call)
        self.assertEqual(calls["n"], 2)  # contour cells + restricted zon coverage
        self.assertEqual(report["h3Overlay"]["cells"], 2)
        self.assertEqual(report["h3Overlay"]["conflictCells"], 2)
        self.assertEqual(report["h3Overlay"]["weightedConflictSharePct"], 50.0)
        self.assertEqual(artifact["cells"][0]["conflictFraction"], 0.5)
        contracts.validate(report, "crosstrack-report")  # attach already did

    def test_attach_h3_overlay_degrades_without_client(self):
        report = self._report()
        self.assertIsNone(
            crosstrack.attach_h3_overlay(report, [], zone_id="z", layers={}))
        self.assertNotIn("h3Overlay", report)
        self.assertEqual(report["degradations"][0]["kind"], "h3-unavailable")
        contracts.validate(report, "crosstrack-report")

    def test_markdown_renders_h3_section(self):
        report = self._report()
        report["h3Overlay"] = {
            "zoneId": "groene_contour", "resolution": 8, "cells": 10,
            "conflictCells": 7, "weightedConflictSharePct": 94.7,
            "artifactFile": "h3-crosstrack.json"}
        md = crosstrack.conflict_markdown(report)
        self.assertIn("H3 overlay", md)
        self.assertIn("7 of 10 cells", md)
```

- [ ] **Step 3: Run to verify failure**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_crosstrack -v`
Expected: FAIL — no attribute `attach_h3_overlay`

- [ ] **Step 4: Implement in `poc/pipeline/crosstrack.py`** — extend `__all__` with `"attach_h3_overlay"` and add:

```python
def attach_h3_overlay(
    report: Dict[str, Any],
    tracks: Sequence[Mapping[str, Any]],
    *,
    zone_id: str,
    layers: Mapping[str, Any],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Attach the per-cell H3 conflict overlay (spec example 7.1).

    ``call(process_id, inputs) -> outputs`` is the poc h3step bridge; when
    None (offline, no fixtures) the overlay degrades to a recorded
    degradation and the report stays valid. Returns the artifact dict for
    ``h3-crosstrack.json`` or None. Polygon headline numbers remain
    authoritative — this layer only localises them.
    """
    if call is None:
        report.setdefault("degradations", []).append(
            {"kind": "h3-unavailable", "zoneId": zone_id,
             "error": "no H3 process client provided (offline run)"})
        return None
    contour = union_zone(layers, zone_id)
    contour_payload = engine.to_zone_geometry(contour, round_dp=6)[0]["payload"]

    def _fc(payload):
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": payload}]}

    cov = call("h3-polygon-to-cells",
               {"polygon": _fc(contour_payload), "resolution": resolution}
               )["coverage"]
    cover = {r["cell"]: r["coverageFraction"] for r in cov["cells"]}
    area = {r["cell"]: r["cellAreaM2"] for r in cov["cells"]}

    conflict: Dict[str, float] = {}
    zon = next((t for t in tracks if t.get("useCase") == "zon"), None)
    if zon is not None:
        zon_payload = engine.to_zone_geometry(zon["geometry"],
                                              round_dp=6)[0]["payload"]
        zcov = call("h3-polygon-to-cells",
                    {"polygon": _fc(zon_payload), "resolution": resolution,
                     "restrictCells": sorted(cover)})["coverage"]
        conflict = {r["cell"]: r["coverageFraction"] for r in zcov["cells"]}

    rows = [{"cell": c, "inZoneFraction": cover[c],
             "conflictFraction": round(conflict.get(c, 0.0), 6),
             "cellAreaM2": area[c]} for c in sorted(cover)]
    num = sum(r["inZoneFraction"] * r["conflictFraction"] * r["cellAreaM2"]
              for r in rows)
    den = sum(r["inZoneFraction"] * r["cellAreaM2"] for r in rows)
    weighted = round(num / den * 100.0, 3) if den else None

    artifact = {
        "zoneId": zone_id, "resolution": resolution, "cells": rows,
        "weightedConflictSharePct": weighted,
        "computedBy": CROSSTRACK_VERSION,
        "notes": [
            "conflictFraction = share of each contour cell's area that is "
            "simultaneously open to the zon track's final zone (planar "
            "EPSG:28992); polygon headline numbers remain authoritative.",
        ],
    }
    report["h3Overlay"] = {
        "zoneId": zone_id, "resolution": resolution, "cells": len(rows),
        "conflictCells": sum(1 for r in rows if r["conflictFraction"] > 0),
        "weightedConflictSharePct": weighted,
        "artifactFile": "h3-crosstrack.json",
    }
    contracts.validate(report, "crosstrack-report")
    return artifact
```

Extend `conflict_markdown` — insert before the final `lines += [""]` / notes loop:

```python
    if report.get("h3Overlay"):
        h = report["h3Overlay"]
        lines += ["", f"## H3 overlay: `{h['zoneId']}` at resolution {h['resolution']}", "",
                  f"{h['conflictCells']} of {h['cells']} cells carry zon conflict; "
                  f"coverage-weighted conflict share {h['weightedConflictSharePct']}%. "
                  f"Per-cell detail: `{h['artifactFile']}` (decision support; "
                  "polygon headline numbers remain authoritative)."]
```

- [ ] **Step 5: Wire `poc/crosstrack/run.py`** — add arguments in `build_parser()` (after `--out`):

```python
    ap.add_argument("--no-h3", action="store_true",
                    help="skip the H3 per-cell overlay (default: run it, "
                         "degrading gracefully when offline without cache)")
    ap.add_argument("--refresh-h3", action="store_true",
                    help="force live re-invocation of the nldt H3 processes "
                         "(ignore the poc/data/cache/h3 cache)")
    ap.add_argument("--h3-resolution", type=int, default=8,
                    help="H3 resolution for the overlay (default: 8)")
```

Insert this block after `tracks_internal = report.pop("_tracks")` and **before** `dump_json(out_dir / "crosstrack-report.json", report, indent=1)`:

```python
    h3_artifact = None
    if not args.no_h3:
        from pipeline import h3step

        def _h3_call(process_id, inputs):
            return h3step.call(process_id, inputs, refresh=args.refresh_h3)

        try:
            h3_artifact = crosstrack.attach_h3_overlay(
                report, tracks_internal,
                zone_id=SHARED_ZONES[0][0],
                layers=track_baselines[0][2],
                resolution=args.h3_resolution, call=_h3_call)
        except Exception as exc:  # decision support only: never fail the run
            report.setdefault("degradations", []).append(
                {"kind": "h3-error", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[crosstrack] WARNING h3 overlay degraded: {exc}")
    if h3_artifact is not None:
        dump_json(out_dir / "h3-crosstrack.json", h3_artifact, indent=1)
        written.append("h3-crosstrack.json")
```

- [ ] **Step 6: Run tests**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_crosstrack -v`
Expected: PASS (existing + 3 new). Then the full suite: `POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests` → 165 pass.

- [ ] **Step 7: Commit**

```bash
git add poc/pipeline/crosstrack.py poc/schemas/crosstrack-report.schema.json poc/crosstrack/run.py poc/tests/test_crosstrack.py
git commit -m "H3 crosstrack overlay: per-cell zon-bos conflict on the Groene contour, degradable, re-validated"
```

---

### Task 9: Scenario hex metrics (Moran's I + cell deltas)

**Files:**
- Modify: `poc/pipeline/scenarios.py` (`run_scenario_set` gains `h3_metrics=None`)
- Modify: `poc/schemas/scenario-report.schema.json` (optional `h3` on scenario rows and control)
- Modify: `poc/scenarios/run.py` (flags + wiring at the `run_scenario_set(...)` call, line ~303)
- Modify: `poc/tests/test_scenarios.py` (append test)

**Interfaces:**
- Consumes: `h3step.scenario_metrics` (Task 7) with contract: control call `fn(payload, None)` may return `"cells"` (list) which the runner pops; scenario call `fn(payload, control_cells_set)` returns deltas.
- Produces: `run_scenario_set(..., h3_metrics=None)` — when provided, `control["h3"]` and each successful scenario row `"h3"` = `{"resolution", "cellCount", "moransI", "pValue", "cellsGainedVsControl", "cellsLostVsControl"}` (nullable numbers, nullable moransI/pValue). Exceptions → `degradations` entries `{"kind": "h3-metrics-error", "scenarioId", "error"}`; report verdict unchanged.

- [ ] **Step 1: Extend the schema** — in `poc/schemas/scenario-report.schema.json`:

Add to the `scenarios` **items** `properties` (and mirror the same definition into the `control` object's `properties`; both stay non-required):

```json
          "h3": {
            "type": "object",
            "additionalProperties": false,
            "required": ["resolution", "cellCount", "moransI", "pValue", "cellsGainedVsControl", "cellsLostVsControl"],
            "properties": {
              "resolution": {"type": "integer"},
              "cellCount": {"type": "integer", "minimum": 0},
              "moransI": {"type": ["number", "null"]},
              "pValue": {"type": ["number", "null"]},
              "cellsGainedVsControl": {"type": ["integer", "null"]},
              "cellsLostVsControl": {"type": ["integer", "null"]}
            }
          }
```

- [ ] **Step 2: Write the failing test** — append to `poc/tests/test_scenarios.py`, reusing the module's existing fixture helpers `_baseline()`, `LAYERS` and `_spec(...)` (module-level, see `ScenarioSweepTests._run` for the calling convention):

```python
class H3MetricsTests(unittest.TestCase):
    """Optional h3_metrics seam: attached when the callable works,
    degraded when it errors, absent by default."""

    def test_h3_metrics_attached_and_control_cells_popped(self):
        seen = []

        def fake_metrics(payload, control_cells):
            seen.append(control_cells)
            if control_cells is None:  # control call first
                return {"resolution": 8, "cellCount": 3, "moransI": 0.5,
                        "pValue": 0.01, "cells": ["a", "b", "c"],
                        "cellsGainedVsControl": None,
                        "cellsLostVsControl": None}
            return {"resolution": 8, "cellCount": 4, "moransI": 0.2,
                    "pValue": 0.2, "cellsGainedVsControl": 1,
                    "cellsLostVsControl": 0}

        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=[_spec("SC-H3",
                         {"type": "policy_variant", "normCardId": "NC-02",
                          "provenanceNote": "n"},
                         [{"ruleId": "FR-T-02", "action": "drop"}])],
            scenario_set_id="SSET-h3", report_id="SR-h3-0001",
            h3_metrics=fake_metrics)
        report.pop("_validation")
        report.pop("_control_rich")
        self.assertIn("h3", report["control"])
        self.assertNotIn("cells", report["control"]["h3"])  # runner pops it
        row = report["scenarios"][0]
        self.assertEqual(row["status"], "ok")
        self.assertIn("h3", row)
        self.assertNotIn("cells", row["h3"])
        self.assertEqual(row["h3"]["cellsGainedVsControl"], 1)
        contracts.validate(report, "scenario-report")
        self.assertIsNone(seen[0])                    # control: control_cells None
        self.assertEqual(seen[1], {"a", "b", "c"})    # scenario: the popped set

    def test_h3_metrics_error_degrades_but_keeps_verdict(self):
        def boom(payload, control_cells):
            raise RuntimeError("h3 offline")

        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=[_spec("SC-H3-E",
                         {"type": "policy_variant", "normCardId": "NC-02",
                          "provenanceNote": "n"},
                         [{"ruleId": "FR-T-02", "action": "drop"}])],
            scenario_set_id="SSET-h3e", report_id="SR-h3e-0001",
            h3_metrics=boom)
        report.pop("_validation")
        report.pop("_control_rich")
        self.assertNotIn("h3", report["control"])
        self.assertTrue(any(d["kind"] == "h3-metrics-error"
                            for d in report["degradations"]))
        self.assertEqual(report["verdict"], "pass")  # decision support only
        contracts.validate(report, "scenario-report")
```

- [ ] **Step 3: Run to verify failure**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_scenarios -v`
Expected: FAIL — `run_scenario_set() got an unexpected keyword argument 'h3_metrics'`

- [ ] **Step 4: Implement in `poc/pipeline/scenarios.py`:**

Add parameter to `run_scenario_set` signature (after `narrator=None`):

```python
    h3_metrics=None,
```

Document it in the docstring (append one paragraph):

```python
    ``h3_metrics(payload_4326, control_cells) -> dict | None`` (optional)
    computes the H3 hex summary per zone — the poc h3step bridge. The
    control call receives ``control_cells=None`` and may include a
    ``"cells"`` list (popped by the runner, never emitted); scenario calls
    receive the control's cell set and return gained/lost deltas. Any
    error degrades to a ``h3-metrics-error`` degradation — verdicts and
    deltas measured in km²/IoU are unaffected.
```

After the `control_block = {...}` assignment (before `report = {`), insert:

```python
    control_cells = None
    if h3_metrics is not None:
        try:
            control_h3 = h3_metrics(control_final["geometry"]["payload"], None)
            if control_h3 is not None:
                control_cells = set(control_h3.pop("cells", []))
                control_block["h3"] = control_h3
        except Exception as exc:
            degradations.append({"kind": "h3-metrics-error",
                                 "scenarioId": "CONTROL",
                                 "error": f"{type(exc).__name__}: {exc}"})
```

In the success branch of the per-spec loop — after the `geom_file = ...` / `scen_degraded = ...` lines, immediately before the `outcomes.append({...})` that ends the branch — insert:

```python
        if h3_metrics is not None:
            try:
                m = h3_metrics(final["geometry"]["payload"], control_cells)
                if m is not None:
                    m.pop("cells", None)
                    outcome_h3 = m
                else:
                    outcome_h3 = None
            except Exception as exc:
                outcome_h3 = None
                degradations.append({"kind": "h3-metrics-error",
                                     "scenarioId": sid,
                                     "error": f"{type(exc).__name__}: {exc}"})
        else:
            outcome_h3 = None
```

and add to the `outcomes.append({...})` dict literal:

```python
                **({"h3": outcome_h3} if outcome_h3 is not None else {}),
```

- [ ] **Step 5: Wire `poc/scenarios/run.py`** — add flags in `build_parser()` (next to `--narrator`):

```python
    ap.add_argument("--no-h3", action="store_true",
                    help="skip per-scenario H3 hex metrics (default: attach "
                         "them, degrading gracefully when offline)")
    ap.add_argument("--h3-resolution", type=int, default=8)
    ap.add_argument("--refresh-h3", action="store_true")
```

At the `report = scenarios.run_scenario_set(` call site (line ~303), define before it:

```python
    h3_metrics_fn = None
    if not args.no_h3:
        from pipeline import h3step

        def h3_metrics_fn(payload, control_cells):  # noqa: F811
            return h3step.scenario_metrics(
                payload, control_cells, resolution=args.h3_resolution,
                refresh=args.refresh_h3)
```

and add the keyword argument to the call:

```python
            h3_metrics=h3_metrics_fn,
```

(If the nested def-after-assignment form trips linters, bind it as
`h3_metrics_fn = (lambda payload, control_cells: h3step.scenario_metrics(
payload, control_cells, resolution=args.h3_resolution, refresh=args.refresh_h3))
if not args.no_h3 else None` — same behaviour.)

- [ ] **Step 6: Run tests**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_scenarios -v`, then the full suite.
Expected: PASS (165 + 2 new = 167; the existing 25 scenario tests unaffected — default `h3_metrics=None`).

- [ ] **Step 7: Commit**

```bash
git add poc/pipeline/scenarios.py poc/schemas/scenario-report.schema.json poc/scenarios/run.py poc/tests/test_scenarios.py
git commit -m "H3 scenario metrics: per-scenario Moran's I + cell deltas vs control (optional, degradable)"
```

---

### Task 10: Buildings-per-zone join (`--buildings`)

**Files:**
- Modify: `poc/pipeline/crosstrack.py` (add `attach_buildings_join`)
- Modify: `poc/crosstrack/run.py` (`--buildings` flag + wiring)
- Modify: `poc/tests/test_crosstrack.py` (append test)

**Interfaces:**
- Consumes: `h3-spatial-join-points` process via the injected `call` (Task 7/8 pattern); `engine.to_zone_geometry`.
- Produces: `crosstrack.attach_buildings_join(tracks, points, *, resolution=8, call=None) -> dict | None` → `{"resolution", "computedBy", "tracks": [{"useCase", "buildingsInZoneCells", "perCell": [{"cell", "count"}]}]}` (artifact for `h3-buildings.json`).

- [ ] **Step 1: Write the failing test** — append inside `TestH3Overlay` in `poc/tests/test_crosstrack.py`:

```python
    def test_attach_buildings_join_counts_per_track(self):
        def call(process_id, inputs):
            assert process_id == "h3-spatial-join-points"
            return {"join": {"pointCount": 3, "cellCount": 2, "resolution": 8,
                             "perPoint": [], "perCell": [
                                 {"cell": "c1", "count": 2},
                                 {"cell": "c2", "count": 1}],
                             "h3Version": "test"}}

        tracks = [{"useCase": "zon", "geometry": box(156000, 457000, 164000, 463000)},
                  {"useCase": "bos", "geometry": box(150000, 450000, 160000, 460000)}]
        points = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Point", "coordinates": [5.11, 52.09]}}]}
        art = crosstrack.attach_buildings_join(tracks, points, call=call)
        self.assertEqual([t["buildingsInZoneCells"] for t in art["tracks"]],
                         [3, 3])
        self.assertEqual(art["resolution"], 8)

    def test_attach_buildings_join_without_client_returns_none(self):
        self.assertIsNone(crosstrack.attach_buildings_join([], {}))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_crosstrack.TestH3Overlay -v`
Expected: FAIL — no attribute `attach_buildings_join`

- [ ] **Step 3: Implement** — in `poc/pipeline/crosstrack.py` (extend `__all__`):

```python
def attach_buildings_join(
    tracks: Sequence[Mapping[str, Any]],
    points: Mapping[str, Any],
    *,
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Per-track building counts per zone cell via h3-spatial-join-points
    (spec example 7.2). ``points``: GeoJSON FeatureCollection of points
    or footprints (joined by centroid). Returns the ``h3-buildings.json``
    artifact or None when no client."""
    if call is None:
        return None
    rows = []
    for t in tracks:
        payload = engine.to_zone_geometry(t["geometry"], round_dp=6)[0]["payload"]
        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": payload}]}
        join = call("h3-spatial-join-points",
                    {"points": points, "polygon": fc,
                     "resolution": resolution})["join"]
        rows.append({
            "useCase": t["useCase"],
            "buildingsInZoneCells": sum(r["count"] for r in join["perCell"]),
            "perCell": join["perCell"],
        })
    return {"resolution": resolution, "computedBy": CROSSTRACK_VERSION,
            "tracks": rows,
            "notes": ["buildings per zone cell via the nldt h3-spatial-join "
                      "process; footprints join by centroid (decision "
                      "support, not a zoning verdict)"]}
```

- [ ] **Step 4: Wire `poc/crosstrack/run.py`** — add argument (next to `--no-h3`):

```python
    ap.add_argument("--buildings", default=None, metavar="GEOJSON",
                    help="GeoJSON points/footprints: buildings-per-zone-cell "
                         "join artifact h3-buildings.json (e.g. a BAG extract)")
```

Insert after the h3-overlay block (still before the report dump):

```python
    buildings_artifact = None
    if args.buildings is not None:
        from pipeline import h3step

        try:
            points_doc = json.loads(Path(args.buildings).read_text(encoding="utf-8"))
            call_b = (lambda pid, inputs: h3step.call(pid, inputs,
                                                      refresh=args.refresh_h3))
            buildings_artifact = crosstrack.attach_buildings_join(
                tracks_internal, points_doc,
                resolution=args.h3_resolution, call=call_b)
        except Exception as exc:  # decision support only
            report.setdefault("degradations", []).append(
                {"kind": "h3-buildings-error",
                 "error": f"{type(exc).__name__}: {exc}"})
            print(f"[crosstrack] WARNING buildings join degraded: {exc}")
    if buildings_artifact is not None:
        dump_json(out_dir / "h3-buildings.json", buildings_artifact, indent=1)
        written.append("h3-buildings.json")
```

(`Path` and `json` are already imported at the top of run.py.)

- [ ] **Step 5: Run tests + full suite**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests`
Expected: PASS (169)

- [ ] **Step 6: Commit**

```bash
git add poc/pipeline/crosstrack.py poc/crosstrack/run.py poc/tests/test_crosstrack.py
git commit -m "H3 buildings join: per-track buildings-per-zone-cell via --buildings (degradable)"
```

---

### Task 11: Leaflet hex map (`h3-crosstrack.html`)

**Files:**
- Create: `poc/pipeline/h3report.py`
- Modify: `poc/crosstrack/run.py` (emit the HTML after the artifact)
- Modify: `poc/tests/test_crosstrack.py` (append test)

**Interfaces:**
- Consumes: the `h3-crosstrack.json` artifact rows (Task 8) + `h3-cells-to-geojson` via `h3step.call` for boundaries.
- Produces: `h3report.render_hex_map(cells_fc, *, title, value_property="conflictFraction", value_label=None, out_path=None) -> str` — single-file offline Leaflet HTML (same CDN + integrity attributes as `pipeline/report_template.html`), choropleth ramp green→red over `value_property`, popup per cell; degrades to a text note when the CDN is unreachable.

- [ ] **Step 1: Write the failing test** — append to `poc/tests/test_crosstrack.py`:

```python
class TestHexMapReport(unittest.TestCase):

    def test_render_hex_map_html(self):
        from pipeline import h3report

        fc = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {"cell": "deadbeefdeadbee", "resolution": 8,
                           "conflictFraction": 0.83},
            "geometry": {"type": "Polygon", "coordinates": [
                [[5.10, 52.08], [5.11, 52.08], [5.11, 52.09],
                 [5.10, 52.09], [5.10, 52.08]]]}}]}
        html = h3report.render_hex_map(fc, title="XR-T hex overlay")
        self.assertIn("leaflet@1.9.4", html)
        self.assertIn("XR-T hex overlay", html)
        self.assertIn("deadbeefdeadbee", html)
        self.assertIn("conflictFraction", html)
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "h3.html"
            h3report.render_hex_map(fc, title="t", out_path=out)
            self.assertTrue(out.exists())
```

- [ ] **Step 2: Run to verify failure**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest tests.test_crosstrack.TestHexMapReport -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.h3report`

- [ ] **Step 3: Implement `poc/pipeline/h3report.py`:**

```python
"""Single-file offline Leaflet hex map for H3 overlay artifacts.

Same idiom as pipeline/report_template.html (Leaflet via CDN with a text
fallback when offline): choropleth over one numeric property per cell,
popup with the cell id and value. No build step, no jinja — the geojson
is embedded as a JSON script block.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  body {{ margin: 0; font: 14px/1.4 system-ui, sans-serif; }}
  #map {{ height: 100vh; }}
  .legend {{ background: #fff; padding: 8px 10px; border-radius: 6px;
             box-shadow: 0 1px 4px rgba(0,0,0,.3); }}
  .legend .swatch {{ display: inline-block; width: 14px; height: 14px;
                     margin-right: 6px; border-radius: 3px; vertical-align: -2px; }}
</style>
</head>
<body>
<div id="map"></div>
<script type="application/json" id="cells-data">{payload}</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
(function () {{
  var mapEl = document.getElementById('map');
  if (typeof L === 'undefined') {{
    mapEl.innerHTML = '<div style="padding:24px;color:#5b6472;font-size:14px">' +
      'Leaflet could not be loaded (CDN unreachable). The per-cell table in ' +
      'h3-crosstrack.json carries the same information.</div>';
    mapEl.style.height = 'auto';
    return;
  }}
  var cells = JSON.parse(document.getElementById('cells-data').textContent);
  var prop = {value_property_json};
  function ramp(v) {{
    v = Math.max(0, Math.min(1, v));
    return 'hsl(' + Math.round(110 * (1 - v)) + ', 72%, 48%)';
  }}
  var layer = L.geoJSON(cells, {{
    style: function (f) {{
      var v = Number(f.properties[prop] || 0);
      return {{color: '#37474f', weight: 0.8, fillColor: ramp(v),
              fillOpacity: 0.75}};
    }},
    onEachFeature: function (f, lyr) {{
      var p = f.properties;
      lyr.bindPopup('<b>' + p.cell + '</b><br>' +
        prop + ': ' + (p[prop] !== undefined ? p[prop] : 'n/a') +
        (p.inZoneFraction !== undefined
          ? '<br>in zone: ' + p.inZoneFraction : ''));
    }}
  }}).addTo(map);
  map.fitBounds(layer.getBounds().pad(0.06));
  var legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function () {{
    var d = L.DomUtil.create('div', 'legend');
    var html = '<b>{value_label}</b><br>';
    for (var i = 0; i <= 4; i++) {{
      var v = i / 4;
      html += '<span class="swatch" style="background:' + ramp(v) + '"></span>' +
              (v).toFixed(2) + (i < 4 ? '<br>' : '');
    }}
    d.innerHTML = html;
    return d;
  }};
  legend.addTo(map);
}})();
</script>
</body>
</html>
"""


def render_hex_map(
    cells_fc: Dict[str, Any],
    *,
    title: str,
    value_property: str = "conflictFraction",
    value_label: Optional[str] = None,
    out_path: Optional[Path] = None,
) -> str:
    """Render a cell FeatureCollection to a standalone hex-choropleth map."""
    html = _TEMPLATE.format(
        title=title,
        payload=json.dumps(cells_fc, ensure_ascii=False),
        value_property_json=json.dumps(value_property),
        value_label=value_label or value_property,
    )
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    return html
```

- [ ] **Step 4: Wire `poc/crosstrack/run.py`** — right after `dump_json(out_dir / "h3-crosstrack.json", h3_artifact, indent=1)` / `written.append("h3-crosstrack.json")`, inside the same `if h3_artifact is not None:` block:

```python
        try:
            from pipeline import h3report, h3step

            cells_fc = h3step.call(
                "h3-cells-to-geojson",
                {"cells": [r["cell"] for r in h3_artifact["cells"]]},
                refresh=args.refresh_h3)["features"]
            by_cell = {r["cell"]: r for r in h3_artifact["cells"]}
            for feat in cells_fc["features"]:
                feat["properties"].update(by_cell[feat["properties"]["cell"]])
            (out_dir / "h3-crosstrack.html").write_text(
                h3report.render_hex_map(
                    cells_fc,
                    title=f"H3 conflict overlay — {report['id']} "
                          f"(res {h3_artifact['resolution']})"),
                encoding="utf-8")
            written.append("h3-crosstrack.html")
        except Exception as exc:  # map is a convenience; artifact stands alone
            report.setdefault("degradations", []).append(
                {"kind": "h3-map-error", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[crosstrack] WARNING hex map degraded: {exc}")
```

- [ ] **Step 5: Run tests + full suite**

Run: `cd poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests`
Expected: PASS (170)

- [ ] **Step 6: Commit**

```bash
git add poc/pipeline/h3report.py poc/crosstrack/run.py poc/tests/test_crosstrack.py
git commit -m "H3 hex map: single-file Leaflet choropleth of the crosstrack overlay (h3-crosstrack.html)"
```

---

### Task 12: End-to-end verification + docs touch-up

**Files:**
- Modify: `poc/README.md` (short H3 section)
- Modify: `nldt/04-recipes-and-processes.md` (one-line process listing addition)

**Interfaces:** none — verification gate.

- [ ] **Step 1: Full offline suites, both sides**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q
# expect: all pass (61 = 29 existing + 23 kernel + 9 process/recipe)
cd ../poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests
# expect: OK, 170 tests, 0 errors, 0 failures
```

- [ ] **Step 2: Live crosstrack smoke (subprocess bridge, cache writes)**

```bash
cd /Users/marc/Projecten/ldttoolbox
nldt/.venv/bin/python poc/crosstrack/run.py --tracks zon,bos --out /tmp/xtrack-h3
# expect: exit 0, verdict PASS, h3-crosstrack.json + h3-crosstrack.html present,
#         h3Overlay block in crosstrack-report.json, no 'h3-error' degradation
ls /tmp/xtrack-h3/h3-crosstrack.json /tmp/xtrack-h3/h3-crosstrack.html
```

Then prove the offline replay property:

```bash
rm -rf /tmp/xtrack-h3-off
POC_H3_OFFLINE=1 nldt/.venv/bin/python poc/crosstrack/run.py --tracks zon,bos --out /tmp/xtrack-h3-off
# expect: exit 0 — the cache written by the live run satisfies every call
python3 -c "import json;d=json.load(open('/tmp/xtrack-h3-off/crosstrack-report.json'));print(d.get('h3Overlay'))"
```

- [ ] **Step 3: Live scenario smoke (one sweep)**

```bash
nldt/.venv/bin/python poc/scenarios/run.py --use-case zon --max-scenarios 3 --out /tmp/scen-h3
# expect: exit 0; control.h3 + per-row h3 blocks present in scenario-report.json
python3 -c "import json,glob;d=json.load(open(glob.glob('/tmp/scen-h3/scenario-report.json')[0]));print(d['control'].get('h3'))"
```

- [ ] **Step 4: Docs**

In `poc/README.md`, append a short section:

```markdown
## H3 hex overlays (nldt bridge)

Zone truth stays polygon-based; H3 is a reporting layer computed by the
`nldt` h3-* OGC processes via `pipeline/h3step.py` (cache-first under
`poc/data/cache/h3/`, offline replays via `POC_H3_OFFLINE=1`).

- `python3 poc/crosstrack/run.py` — per-cell zon×bos conflict on the
  Groene contour (`h3-crosstrack.json` + Leaflet `h3-crosstrack.html`)
- `python3 poc/crosstrack/run.py --buildings bag-points.geojson` —
  buildings-per-zone-cell join (`h3-buildings.json`)
- `python3 poc/scenarios/run.py` — per-scenario Moran's I + cell deltas
  (`control.h3`, scenario-row `h3`); `--no-h3` disables all of the above
- fixtures: `POC_H3_OFFLINE= python3 tests/make_h3_fixtures.py` (in `poc/`)
```

In `nldt/04-recipes-and-processes.md`, add the five process ids + `hex-overlay-analysis` recipe to its process/recipe listing (match the file's existing list format; one line each).

- [ ] **Step 5: Commit + final verification**

```bash
git add poc/README.md nldt/04-recipes-and-processes.md
git commit -m "H3 docs: poc bridge usage + nldt process/recipe listing"
cd nldt && .venv/bin/python -m pytest tests -q && cd ../poc && POC_H3_OFFLINE=1 ../nldt/.venv/bin/python -m unittest discover -s tests
```

Expected: both suites green. Report the live-run numbers (weighted conflict share vs the 94.7% polygon headline) in the task summary.

---

## Deferred (explicitly out of this plan)

- Simulation-viewer hex panels (`simulation/build_simulation.py` consumes canonical pipeline runs, not crosstrack artifacts — separate feature once hex artifacts are staple).
- jinja `report_template.html` `h3Layers` block (no producer today).
- BAG registry fetch (needs a WFS or ArcGIS-compatible source entry in `poc/data/sources.json`).
- deck.gl `H3Hexagon` in `context3d`; `grid_path` corridor analysis; PostGIS/H3 SQL.
