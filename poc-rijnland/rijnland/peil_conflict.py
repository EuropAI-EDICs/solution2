"""Peilgebied × peilafwijking H3 conflict overlay for PoC-3 Rijnland.

Mirrors the PoC-1 crosstrack H3 pattern: discretise the formal peilgebied,
then measure peilafwijking coverage on exactly those cells. Polygon areas
remain authoritative; H3 localises the conflict for decision support.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Mapping, Optional

from shapely.geometry import mapping, shape
from shapely.ops import transform as sh_transform, unary_union
from shapely.validation import make_valid

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover
    Transformer = None  # type: ignore

PEIL_CONFLICT_VERSION = "poc-rijnland-peil-conflict/0.1"

__all__ = [
    "PEIL_CONFLICT_VERSION",
    "attach_peil_h3_overlay",
    "union_layer_rd",
    "to_wgs84_payload",
]


_TO_WGS84 = None


def _transformer():
    global _TO_WGS84
    if _TO_WGS84 is None:
        if Transformer is None:
            raise RuntimeError("pyproj is required for peil conflict CRS transform")
        _TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    return _TO_WGS84


def union_layer_rd(fc: Mapping[str, Any]):
    """Unary union of a FeatureCollection in EPSG:28992 (repaired)."""
    geoms = []
    for feat in fc.get("features") or []:
        g = feat.get("geometry")
        if not g:
            continue
        geom = shape(g)
        if not geom.is_valid:
            geom = make_valid(geom)
        if not geom.is_empty:
            geoms.append(geom)
    if not geoms:
        raise ValueError("layer has no usable geometry")
    u = unary_union(geoms)
    if not u.is_valid:
        u = make_valid(u)
    return u


def to_wgs84_payload(geom_rd, *, round_dp: int = 6) -> dict:
    """GeoJSON geometry dict in EPSG:4326 (RFC 7946)."""
    tr = _transformer()
    geom = sh_transform(tr.transform, geom_rd)
    payload = mapping(geom)

    def _round(obj):
        if isinstance(obj, (float, int)):
            return round(float(obj), round_dp)
        if isinstance(obj, (list, tuple)):
            return [_round(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _round(v) for k, v in obj.items()}
        return obj

    return _round(payload)


def _fc(payload: dict) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": payload}],
    }


def attach_peil_h3_overlay(
    report: Dict[str, Any],
    *,
    peil_fc_rd: Mapping[str, Any],
    afwijk_fc_rd: Mapping[str, Any],
    resolution: int = 8,
    call=None,
) -> Optional[Dict[str, Any]]:
    """Attach H3 peil-conflict overlay; returns artifact or None when degraded."""
    if call is None:
        report.setdefault("degradations", []).append({
            "kind": "h3-unavailable",
            "error": "no H3 process client provided (offline run)",
        })
        return None

    peil_rd = union_layer_rd(peil_fc_rd)
    afwijk_rd = union_layer_rd(afwijk_fc_rd)
    peil_payload = to_wgs84_payload(peil_rd)
    afwijk_payload = to_wgs84_payload(afwijk_rd)

    peil_area_km2 = round(peil_rd.area / 1e6, 3)
    afwijk_area_km2 = round(afwijk_rd.area / 1e6, 3)
    overlap_rd = peil_rd.intersection(afwijk_rd)
    if not overlap_rd.is_valid:
        overlap_rd = make_valid(overlap_rd)
    overlap_km2 = round(overlap_rd.area / 1e6, 3)
    overlap_pct = round(100.0 * overlap_rd.area / peil_rd.area, 3) if peil_rd.area else None

    report["peil"] = {
        "peilgebiedAreaKm2": peil_area_km2,
        "peilafwijkingAreaKm2": afwijk_area_km2,
        "overlapAreaKm2": overlap_km2,
        "overlapShareOfPeilPct": overlap_pct,
    }

    cov = call(
        "h3-polygon-to-cells",
        {"polygon": _fc(peil_payload), "resolution": resolution},
    )["coverage"]
    cover = {r["cell"]: r["coverageFraction"] for r in cov["cells"]}
    area = {r["cell"]: r["cellAreaM2"] for r in cov["cells"]}

    zcov = call(
        "h3-polygon-to-cells",
        {
            "polygon": _fc(afwijk_payload),
            "resolution": resolution,
            "restrictCells": sorted(cover),
        },
    )["coverage"]
    conflict = {r["cell"]: r["coverageFraction"] for r in zcov["cells"]}

    rows = [
        {
            "cell": c,
            "inZoneFraction": cover[c],
            "conflictFraction": round(conflict.get(c, 0.0), 6),
            "cellAreaM2": area[c],
        }
        for c in sorted(cover)
    ]
    num = sum(r["inZoneFraction"] * r["conflictFraction"] * r["cellAreaM2"] for r in rows)
    den = sum(r["inZoneFraction"] * r["cellAreaM2"] for r in rows)
    weighted = round(num / den * 100.0, 3) if den else None

    artifact = {
        "zoneId": "peilgebied-vigerend",
        "resolution": resolution,
        "cells": rows,
        "weightedConflictSharePct": weighted,
        "h3Version": cov.get("h3Version"),
        "computedBy": PEIL_CONFLICT_VERSION,
        "notes": [
            "conflictFraction = share of each peilgebied cell that also "
            "intersects peilafwijking (praktijk), planar EPSG:28992; "
            "polygon overlap figures remain authoritative.",
        ],
    }
    report["h3Overlay"] = {
        "zoneId": "peilgebied-vigerend",
        "resolution": resolution,
        "cells": len(rows),
        "conflictCells": sum(1 for r in rows if r["conflictFraction"] > 0),
        "weightedConflictSharePct": weighted,
        "artifactFile": "h3-peil-conflict.json",
    }
    return artifact


def empty_report(*, run_id: str) -> Dict[str, Any]:
    return {
        "id": run_id,
        "generatedAt": _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "generatedBy": PEIL_CONFLICT_VERSION,
        "verdict": "pass",
        "degradations": [],
        "notes": [
            "PoC-3 MVP: peilgebied (vigerend) × peilafwijking (praktijk) "
            "via nldt H3; decision support only.",
        ],
    }


def conflict_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# Peil-conflict Rijnland — `{report['id']}`",
        "",
        f"- generated: `{report.get('generatedAt')}` · `{report.get('generatedBy')}`",
        f"- verdict: **{report.get('verdict', 'pass')}**",
        "",
    ]
    peil = report.get("peil") or {}
    if peil:
        lines += [
            "## Polygon headline (authoritative)",
            "",
            f"- Peilgebied (vigerend): **{peil.get('peilgebiedAreaKm2')} km²**",
            f"- Peilafwijking (praktijk): **{peil.get('peilafwijkingAreaKm2')} km²**",
            f"- Overlap: **{peil.get('overlapAreaKm2')} km²** "
            f"({peil.get('overlapShareOfPeilPct')}% of peilgebied)",
            "",
        ]
    h = report.get("h3Overlay")
    if h:
        lines += [
            f"## H3 overlay: `{h['zoneId']}` at resolution {h['resolution']}",
            "",
            f"{h['conflictCells']} of {h['cells']} cells carry peilafwijking; "
            f"coverage-weighted conflict share {h['weightedConflictSharePct']}%. "
            f"Per-cell detail: `{h['artifactFile']}` "
            "(decision support; polygon headline numbers remain authoritative).",
            "",
        ]
    k = report.get("krw")
    if k:
        lines += [
            "## KRW-monitoringdekking (fase 2)",
            "",
            f"- Routine waterkwaliteits-meetpunten in peilgebied-cellen: **{k['meetpuntenRoutine']}**",
            f"- Cellen met monitoring: **{k['cellsWithMonitoring']}**",
            f"- Moran's I op meetdichtheid: **{k['moransI']}** (p = {k['pValue']})",
            f"- Conflictcellen zonder monitoring in cel of buurt: **{k['blindSpotCells']}/{k['conflictCells']}** "
            f"({k['blindSpotShareOfConflictPct']}%) — blinde vlekken",
            "",
        ]
    if report.get("degradations"):
        lines += ["## Degradations", ""]
        for d in report["degradations"]:
            lines.append(f"- `{d.get('kind')}`: {d.get('error', d)}")
        lines.append("")
    for note in report.get("notes") or []:
        lines.append(f"> {note}")
    lines.append("")
    return "\n".join(lines)
