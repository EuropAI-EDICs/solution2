"""Stiltegebied noise exceedance screening (art. 9.26 thresholds).

Pure kernel — no network. Point-in-polygon in planar EPSG:28992;
I/O geometries are GeoJSON EPSG:4326 (RFC 7946).

Thresholds (Omgevingsverordening provincie Utrecht art. 9.26):
  - Gebied stille kern: LAeq,24h ≤ 40 dB(A)
  - Bufferzone stiltegebied: LAeq,24h ≤ 45 dB(A) (preferably 40)
"""

from __future__ import annotations

import math
from typing import Any, Optional

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform as sh_transform, unary_union
from shapely.validation import make_valid

from services.common import urbanstrategy_client as us_client

_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)

DEFAULT_STILLE_KERN_DB = 40.0
DEFAULT_BUFFERZONE_DB = 45.0

DEFAULT_CAVEATS = [
    "SRM-2 traffic/industry noise field via Urban Strategy; not turbine-source specific",
    "Decision-support annex only — does not rewrite FR-W-11 / FormalRule status",
]


class UsStiltegebiedError(ValueError):
    """Invalid receptor or zone input."""


def _to_rd(geom):
    return sh_transform(_TO_RD.transform, geom)


def _union_polygons(fc: Optional[dict[str, Any]]):
    if not fc or not isinstance(fc, dict):
        return None
    geoms = []
    for feat in fc.get("features") or []:
        g = feat.get("geometry") if isinstance(feat, dict) else None
        if not g:
            continue
        try:
            geom = make_valid(shape(g))
        except Exception as exc:
            raise UsStiltegebiedError(f"invalid zone geometry: {exc}") from exc
        if not geom.is_empty:
            geoms.append(_to_rd(geom))
    if not geoms:
        return None
    return make_valid(unary_union(geoms))


def _percentile(sorted_vals: list[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def evaluate(
    receptors: dict[str, Any],
    stille_kern: Optional[dict[str, Any]] = None,
    bufferzone: Optional[dict[str, Any]] = None,
    *,
    stille_kern_db: float = DEFAULT_STILLE_KERN_DB,
    bufferzone_db: float = DEFAULT_BUFFERZONE_DB,
    caveats: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Classify receptors against stiltegebied zones and art. 9.26 thresholds.

    ``stille_kern`` / ``bufferzone`` are GeoJSON FeatureCollections (4326).
    When only a combined stiltegebied polygon is available, pass it as
    ``stille_kern`` (stricter 40 dB) and leave ``bufferzone`` empty — record
    that in ``caveats``.
    """
    if not isinstance(receptors, dict) or receptors.get("type") != "FeatureCollection":
        raise UsStiltegebiedError("receptors must be a GeoJSON FeatureCollection")

    # Ensure normalized property names
    receptors = us_client.normalize_receptors(receptors)

    kern_rd = _union_polygons(stille_kern)
    buf_rd = _union_polygons(bufferzone)

    notes = list(caveats) if caveats is not None else list(DEFAULT_CAVEATS)
    if kern_rd is not None and buf_rd is None:
        notes.append(
            "bufferzone empty — combined/stille-kern polygon screened at "
            f"{stille_kern_db:g} dB (art. 9.26 stille kern)"
        )

    classified: list[dict[str, Any]] = []
    exceedance_features: list[dict[str, Any]] = []
    zone_values: dict[str, list[float]] = {
        "stille_kern": [],
        "bufferzone": [],
        "outside": [],
    }

    for feat in receptors.get("features") or []:
        props = dict(feat.get("properties") or {})
        geom = feat.get("geometry")
        laeq = props.get("lAeq")
        if geom is None or laeq is None:
            continue
        try:
            pt = shape(geom)
            pt_rd = _to_rd(pt)
        except Exception as exc:
            raise UsStiltegebiedError(f"invalid receptor geometry: {exc}") from exc

        zone = "outside"
        threshold: Optional[float] = None
        if kern_rd is not None and (kern_rd.contains(pt_rd) or kern_rd.touches(pt_rd)):
            zone = "stille_kern"
            threshold = float(stille_kern_db)
        elif buf_rd is not None and (buf_rd.contains(pt_rd) or buf_rd.touches(pt_rd)):
            zone = "bufferzone"
            threshold = float(bufferzone_db)

        laeq_f = float(laeq)
        zone_values[zone].append(laeq_f)
        exceeds = threshold is not None and laeq_f > threshold
        row = {
            "id": props.get("id"),
            "lAeq": laeq_f,
            "zone": zone,
            "thresholdDb": threshold,
            "exceeds": exceeds,
        }
        if props.get("iLden") is not None:
            try:
                row["iLden"] = float(props["iLden"])
            except (TypeError, ValueError):
                pass
        classified.append(row)

        if exceeds:
            exceedance_features.append({
                "type": "Feature",
                "properties": {
                    "id": row["id"],
                    "lAeq": laeq_f,
                    "zone": zone,
                    "thresholdDb": threshold,
                    "exceeds": True,
                },
                "geometry": mapping(pt) if pt.geom_type == "Point" else geom,
            })

    def _zone_stats(vals: list[float]) -> dict[str, Any]:
        if not vals:
            return {"count": 0, "max": None, "p95": None}
        ordered = sorted(vals)
        return {
            "count": len(ordered),
            "max": ordered[-1],
            "p95": round(_percentile(ordered, 95), 3),
        }

    in_kern = zone_values["stille_kern"]
    in_buf = zone_values["bufferzone"]
    exceed_kern = sum(1 for r in classified if r["zone"] == "stille_kern" and r["exceeds"])
    exceed_buf = sum(1 for r in classified if r["zone"] == "bufferzone" and r["exceeds"])

    classified.sort(key=lambda r: str(r.get("id") or ""))
    exceedance_features.sort(
        key=lambda f: str((f.get("properties") or {}).get("id") or "")
    )

    return {
        "thresholds": {
            "stilleKernDb": float(stille_kern_db),
            "bufferzoneDb": float(bufferzone_db),
            "legalBasis": "Omgevingsverordening provincie Utrecht art. 9.26 (CVDR704250)",
        },
        "counts": {
            "receptorsTotal": len(classified),
            "inStilleKern": len(in_kern),
            "inBufferzone": len(in_buf),
            "outside": len(zone_values["outside"]),
            "exceedancesStilleKern": exceed_kern,
            "exceedancesBufferzone": exceed_buf,
            "exceedancesTotal": exceed_kern + exceed_buf,
        },
        "perZone": {
            "stille_kern": _zone_stats(in_kern),
            "bufferzone": _zone_stats(in_buf),
            "outside": _zone_stats(zone_values["outside"]),
        },
        "receptors": classified,
        "exceedances": {
            "type": "FeatureCollection",
            "features": exceedance_features,
        },
        "crs": "geometry-EPSG:4326-pip-EPSG:28992",
        "normCardId": "NC-W-11",
        "formalRuleId": "FR-W-11",
        "caveats": notes,
    }
