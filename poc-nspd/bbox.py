"""NSPD-werkkader: één WGS84-bbox, afgeleide RD- en Lambert72-kaders.

Spec: docs/superpowers/specs/2026-10-14-poc-nspd-design.md §4.3.
Gepind in taak 1 van plan 2026-10-14-poc-nspd.
"""
from __future__ import annotations

from functools import lru_cache
from pyproj import Transformer

NSPD_BBOX_WGS84: tuple[float, float, float, float] = (3.45, 51.02, 3.88, 51.48)
# kader: Vlissingen/Borsele (NW) → haven Gent/Zelzate (ZO)


def _transform(bbox: tuple[float, float, float, float], to_epsg: int) -> tuple:
    x0, y0, x1, y1 = bbox
    t = Transformer.from_crs("EPSG:4326", f"EPSG:{to_epsg}", always_xy=True)
    corners = [t.transform(x, y) for x in (x0, x1) for y in (y0, y1)]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return (min(xs), min(ys), max(xs), max(ys))


@lru_cache(maxsize=1)
def nspd_bbox_rd() -> tuple[float, float, float, float]:
    return _transform(NSPD_BBOX_WGS84, 28992)


@lru_cache(maxsize=1)
def nspd_bbox_l72() -> tuple[float, float, float, float]:
    return _transform(NSPD_BBOX_WGS84, 31370)
