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
import math
import random
from pathlib import Path
from typing import Any, Mapping
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
    "cells_to_geojson",
    "join_points_to_cells",
    "knn",
    "children_of",
    "morans_i",
    "grid_disk_cells",
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
            try:
                with Path(urlparse(value).path).open(encoding="utf-8") as f:
                    return json.load(f)
            except OSError as exc:
                raise H3KitError(f"cannot read geojson file:// URI: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise H3KitError(f"invalid JSON in file:// URI: {exc}") from exc
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise H3KitError(f"invalid GeoJSON JSON string: {exc}") from exc
    if isinstance(value, dict):
        return value
    raise H3KitError("expected GeoJSON dict, JSON string or file:// URI")


def _cell_polygon_rd(cell: str):
    # h3-py v4.5: cell_to_boundary returns (lat, lng) pairs; build the
    # GeoJSON [lng, lat] ring ourselves (shapely auto-closes the ring).
    ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(cell)]
    return sh_transform(
        _TO_RD.transform,
        shape({"type": "Polygon", "coordinates": [ring]}),
    )


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
    minx, miny, maxx, maxy = u4326.bounds
    if not (-180.0 <= minx and maxx <= 180.0 and -90.0 <= miny and maxy <= 90.0):
        # degree-out-of-range coords (e.g. EPSG:28992 input): H3 silently
        # returns zero cells — flag it instead of a misleading empty result
        notes.add("input-bounds-outside-wgs84-check-crs")
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
        # h3-py v4: geo_to_cells is the GeoJSON-dict entry point
        # (polygon_to_cells takes an H3Shape, not a dict).
        cells = set(h3.geo_to_cells(mapping(u4326), res))

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
    if _as_bool(compact):
        if restrict_cells is not None:
            notes.add("compact-ignored-with-restrict-cells")
            result["notes"] = sorted(notes)
        else:
            selected = {r["cell"] for r in rows if r["coverageFraction"] >= 0.5}
            # Real H3 compaction: complete child groups are replaced by
            # coarser parent cells, so this list mixes resolutions.
            result["compactedCells"] = sorted(h3.compact_cells(selected))
    return result


def cells_to_geojson(cells: Any) -> dict[str, Any]:
    """Cell-boundary FeatureCollection (RFC 7946), one feature per cell."""
    feats = []
    for cell in sorted({str(c) for c in cells}):
        if not h3.is_valid_cell(cell):
            raise H3KitError(f"not an H3 cell: {cell!r}")
        # h3-py v4.5: cell_to_boundary returns (lat, lng) pairs; build
        # the GeoJSON [lng, lat] ring ourselves and close it formally.
        ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(cell)]
        ring.append(ring[0])
        feats.append({
            "type": "Feature",
            "properties": {"cell": cell, "resolution": h3.get_resolution(cell)},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
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
    cell_set = set()
    for c in cells:
        c = str(c)
        if not h3.is_valid_cell(c):
            raise H3KitError(f"not an H3 cell: {c!r}")
        cell_set.add(c)
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
    if not 0 <= res <= 15:
        raise H3KitError(f"resolution {res} out of range 0..15")
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
    if not 0 <= res <= 15:
        raise H3KitError(f"resolution {res} out of range 0..15")
    out: dict[str, list[str]] = {}
    for cell in sorted({str(c) for c in cells}):
        if not h3.is_valid_cell(cell):
            raise H3KitError(f"not an H3 cell: {cell!r}")
        if h3.get_resolution(cell) >= res:
            raise H3KitError(f"cell {cell}: child resolution {res} must "
                             "exceed the parent's")
        out[cell] = sorted(h3.cell_to_children(cell, res))
    return {"childResolution": res, "children": out, "h3Version": _h3_version()}


def _normalise_values(values: Any) -> dict[str, float]:
    if isinstance(values, Mapping):
        if "perCell" in values:  # a h3-spatial-join-points output
            values = values["perCell"]
        else:
            return {str(k): float(v) for k, v in values.items()}
    if not isinstance(values, (list, tuple)):
        raise H3KitError("values must be a cell→value map, rows list, or "
                         "a join output with perCell")
    out: dict[str, float] = {}
    for row in values:
        if not isinstance(row, Mapping) or "cell" not in row:
            raise H3KitError(f"malformed values row: {row!r}")
        cell = str(row["cell"])
        if "value" in row:
            out[cell] = float(row["value"])
        elif "count" in row:
            out[cell] = float(row["count"])
        elif "coverageFraction" in row:
            out[cell] = float(row["coverageFraction"])
        else:
            raise H3KitError(f"row {cell!r} lacks value/count/coverageFraction")
    return out


def morans_i(values: Any, permutations: Any = 199) -> dict[str, Any]:
    """Global Moran's I from scratch over grid_disk(1) neighbourhoods
    (notebook §IV.3, no PySAL). One-sided p-value via seeded permutations."""
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
    nbr_idx = {i: sorted(idx[c2] for c2 in set(h3.grid_disk(c, 1)) - {c}
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
    rng = random.Random(0)
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


def grid_disk_cells(cells: Any, ring: Any = 1) -> dict[str, Any]:
    """grid_disk neighbourhood per cell (notebook §I.3 arrangement):
    the origin plus all cells within ``ring`` steps, sorted."""
    k = _as_int(ring, 1)
    if k < 1:
        raise H3KitError(f"ring {k} must be >= 1")
    disks: dict[str, list[str]] = {}
    for cell in sorted({str(c) for c in cells}):
        if not h3.is_valid_cell(cell):
            raise H3KitError(f"not an H3 cell: {cell!r}")
        disks[cell] = sorted(set(h3.grid_disk(cell, k)))
    return {"ring": k, "disks": disks, "h3Version": _h3_version()}
