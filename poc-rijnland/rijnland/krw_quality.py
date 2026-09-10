"""KRW water-quality monitoring coverage × peil conflict (PoC-3 fase 2).

The Rijnland ArcGIS stack exposes no measured water-quality values and
the KRW-status water-body layers are published empty; what is live is
the measurement-location layer (``WS_TYPEMETING`` discriminated). This
module therefore answers the phase-2 question the data can honestly
support: *where does practical peil deviation coincide with routine
water-quality monitoring — and where is it a blind spot?*

All H3 work goes through the nldt bridge (``h3-spatial-join-points``,
``h3-grid-disk``, ``h3-morans-i``); polygon peil figures remain
authoritative.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from shapely.geometry import shape

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover
    Transformer = None  # type: ignore

from rijnland.peil_conflict import PEIL_CONFLICT_VERSION

KRW_VERSION = "poc-rijnland-krw-monitoring/0.1"

__all__ = ["KRW_VERSION", "attach_krw_monitoring", "points_fc_to_wgs84"]

_TO_WGS84 = None


def _transformer():
    global _TO_WGS84
    if _TO_WGS84 is None:
        if Transformer is None:
            raise RuntimeError("pyproj is required for KRW CRS transform")
        _TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    return _TO_WGS84


def points_fc_to_wgs84(fc_rd: Mapping[str, Any]) -> Dict[str, Any]:
    """Point FeatureCollection RD → WGS84 (RFC 7946), 6 dp."""
    tr = _transformer()
    feats = []
    for feat in fc_rd.get("features") or []:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            g = shape(geom)
            lng, lat = g.centroid.x, g.centroid.y
        else:
            lng, lat = geom["coordinates"][:2]
        lng_w, lat_w = tr.transform(float(lng), float(lat))
        feats.append({
            "type": "Feature",
            "properties": dict(feat.get("properties") or {}),
            "geometry": {"type": "Point",
                         "coordinates": [round(lng_w, 6), round(lat_w, 6)]},
        })
    return {"type": "FeatureCollection", "features": feats}


def attach_krw_monitoring(
    report: Dict[str, Any],
    *,
    peil_cells: List[Mapping[str, Any]],
    meet_fc_rd: Mapping[str, Any],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Attach per-cell routine-WQ monitoring coverage on the peil grid.

    ``peil_cells``: rows of the peil h3 artifact (cell, inZoneFraction,
    conflictFraction, cellAreaM2). Blind spot = conflict cell with zero
    routine monitoring in the cell AND its grid_disk(1) neighbourhood.
    Returns the ``h3-krw-monitoring.json`` artifact or None when the
    bridge is unavailable (degradation recorded).
    """
    if call is None:
        report.setdefault("degradations", []).append({
            "kind": "krw-unavailable",
            "error": "no H3 process client provided (offline run)",
        })
        return None
    cells = sorted(str(r["cell"]) for r in peil_cells)
    conflict = {str(r["cell"]): float(r.get("conflictFraction") or 0.0)
                for r in peil_cells}

    points = points_fc_to_wgs84(meet_fc_rd)
    join = call("h3-spatial-join-points",
                {"points": points, "cells": cells,
                 "resolution": resolution})["join"]
    counts = {r["cell"]: int(r["count"]) for r in join.get("perCell", [])}
    monitored = {c for c, n in counts.items() if n > 0}
    routine_total = sum(counts.values())

    # coverage in the ring-1 neighbourhood of unmonitored cells
    zero_cells = [c for c in cells if c not in monitored]
    nearby: Dict[str, bool] = {c: False for c in zero_cells}
    if zero_cells:
        disks = call("h3-grid-disk",
                     {"cells": zero_cells, "ring": 1})["disk"]["disks"]
        for c, disk in disks.items():
            nearby[c] = any(nbr in monitored for nbr in disk if nbr != c)

    rows = []
    for c in cells:
        n = counts.get(c, 0)
        blind = (conflict.get(c, 0.0) > 0.0 and n == 0 and not nearby.get(c, False))
        rows.append({
            "cell": c,
            "conflictFraction": conflict.get(c, 0.0),
            "monitoringCount": n,
            "monitoringNearby": nearby.get(c, None) if n == 0 else None,
            "blindSpot": blind,
            "blindSpotScore": round(conflict.get(c, 0.0), 6) if blind else 0.0,
        })

    stats = call("h3-morans-i",
                 {"values": {c: counts.get(c, 0) for c in cells}})["statistics"]
    conflict_cells = sum(1 for r in rows if r["conflictFraction"] > 0)
    blind_cells = sum(1 for r in rows if r["blindSpot"])

    report["krw"] = {
        "meetpuntenRoutine": routine_total,
        "cellsWithMonitoring": len(monitored),
        "moransI": stats.get("moransI"),
        "pValue": stats.get("pValue"),
        "conflictCells": conflict_cells,
        "blindSpotCells": blind_cells,
        "blindSpotShareOfConflictPct": (
            round(100.0 * blind_cells / conflict_cells, 3)
            if conflict_cells else None),
    }
    return {
        "resolution": resolution,
        "computedBy": KRW_VERSION,
        "rows": rows,
        "summary": dict(report["krw"]),
        "notes": [
            "monitoringCount = routine waterkwaliteits-meetlocaties "
            "(WS_TYPEMETING = 'routine meetnet waterkwaliteit') per peilgebied-"
            "cel; blindSpot = conflictcel zonder routine monitoring in de cel "
            "of haar grid_disk(1)-buurt. KRW-statuswaterlichamen zijn leeg in "
            "de service en meetwaarden worden niet via ArcGIS ontsloten — "
            "dit is monitoringdekking, geen gemeten waterkwaliteit.",
        ],
    }
