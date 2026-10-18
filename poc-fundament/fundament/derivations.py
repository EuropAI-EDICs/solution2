"""Pure derivatie-helpers: clippen, filteren, statistiek — geen I/O.

Verplaatst (byte-verbatim) uit poc-minigim/minigim/checklist.py; PoC-5
importeert ze terug via de compat-re-exports in minigim/checklist.py.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter

import shapely.geometry as sg


def _geom(feature) -> sg.base.BaseGeometry:
    return sg.shape(feature["geometry"])


def _clip(fc: dict, aoi_geom) -> tuple[list, int]:
    """Clip features op de plangrens; geeft (geclipte features, bron-aantal).

    Reparatie uitsluitend voor vlakken: buffer(0) op punten/lijnen geeft
    lege geometrieën (shapely-semantiek).
    """
    out = []
    src = fc.get("features", [])
    for f in src:
        if f.get("geometry") is None:
            continue
        g = _geom(f)
        if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_valid:
            g = g.buffer(0)
        inter = g.intersection(aoi_geom)
        if inter.is_empty:
            continue
        out.append({**f, "geometry": json.loads(json.dumps(inter.__geo_interface__))})
    return out, len(src)


def _current_only(fc: dict, sid: str) -> tuple[dict, int]:
    """BGT levert ook historische objecten (eind_registratie gevuld); alleen
    de actuele stand tellen. Andere bronnen onaangetast."""
    if sid != "pdok-bgt-ogc-api":
        return fc, 0
    kept, dropped = [], 0
    for f in fc.get("features", []):
        if (f.get("properties") or {}).get("eind_registratie"):
            dropped += 1
        else:
            kept.append(f)
    return {**fc, "features": kept}, dropped


def _area_m2(features) -> float:
    tot = 0.0
    for f in features:
        g = _geom(f)
        if g.geom_type in ("Polygon", "MultiPolygon"):
            tot += g.area
    return tot


def _length_km(features) -> float:
    tot = 0.0
    for f in features:
        g = _geom(f)
        if g.geom_type in ("LineString", "MultiLineString"):
            tot += g.length
    return tot / 1000.0


def _breakdown(features, field: str, top: int = 12) -> dict:
    counts: dict[str, int] = {}
    for f in features:
        v = (f.get("properties") or {}).get(field)
        v = "(onbekend)" if v in (None, "") else str(v)
        counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1])[:top])


def _histogram(features, field: str) -> dict:
    bins = {}
    for f in features:
        v = (f.get("properties") or {}).get(field)
        if isinstance(v, (int, float)) and 1500 < float(v) < 2100:
            bins[f"{int(v) // 10 * 10}s"] = bins.get(f"{int(v) // 10 * 10}s", 0) + 1
    return dict(sorted(bins.items()))


def _entropy_norm(features, field: str) -> float:
    counts = _breakdown(features, field, top=10_000)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        p = c / total
        ent -= p * math.log(p)
    max_ent = math.log(len(counts)) if len(counts) > 1 else 1.0
    return round(ent / max_ent, 4) if max_ent > 0 else 0.0


CBS_SENTINELS = (-99995, -99997, -99998, -99999)


def summarize(records: list[dict]) -> dict:
    by_status = Counter(r["bindingStatus"] for r in records)
    by_delivered = Counter(r["deliveredStatus"] for r in records)
    hoog = [r for r in records if r.get("prioriteit") == "hoog"]
    d = sum(1 for r in hoog if r["deliveredStatus"] == "delivered")
    return {
        "itemCount": len(records),
        "bindingStatus": dict(by_status),
        "deliveredStatus": dict(by_delivered),
        "autoCoverageOfHoog": {"hoog": len(hoog), "delivered": d,
                               "pct": round(100 * d / len(hoog), 1) if hoog else None},
        "hoogPrioriteitNotDelivered": [r["lijstItemId"] for r in hoog
                                       if r["deliveredStatus"] != "delivered"],
    }


def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")
