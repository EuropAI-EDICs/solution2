"""Sensor + pump locations from Rijnland's open ArcGIS.

run.py fetches the groundwater loggers with ``fetch_layer_attrs`` — the
Meetlocatie service returns those points with NULL geometry (coordinates
in XCOORDINAAT/YCOORDINAAT attributes), which ``pipeline.geodata``
(untouched, shared with the other PoCs) drops. Gemalen come through the
normal geodata path and are parsed here.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import requests

SEED_REASON = (
    "No open groundwater-depth series resolves for Rijnland (recon "
    "2026-10-13: BRO api.bro-data.nl DNS/auth-gated, rijnland.lizard.net "
    "auth-gated, grondwaterstanden.nl defunct). Series are seeded "
    "deterministically from open sensor metadata + measured open-meteo "
    "rain until a BRO/Lizard fetch lands real series (design §4)."
)


def fetch_layer_attrs(source_id: str, *, sources: Mapping[str, Any],
                      cache_dir: Path, bbox: Optional[List[float]] = None,
                      where: Optional[str] = None, timeout: int = 180,
                      refresh: bool = False,
                      session: Optional[requests.Session] = None) -> dict:
    """Cache-first ArcGIS query for attribute-only point layers.

    Mirrors ``pipeline.geodata`` conventions (cache under the PoC's
    data/cache, provenance properties) but keeps features whose geometry
    the service leaves null — coordinates stay in the attributes.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    src = sources.get(source_id)  # geodata.load_sources: {id: meta}
    if src is None:
        raise KeyError(f"{source_id} not in the sources registry")
    fp = hashlib.sha1(json.dumps(
        [source_id, bbox, where], separators=(",", ":")
    ).encode("utf-8")).hexdigest()[:12]
    path = cache_dir / f"{source_id}.attr-{fp}.json"
    if path.exists() and not refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cached.get("properties", {}).get("queryFingerprint") == fp:
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    url = f"{src['serviceUrl']}/{src['layerId']}/query"
    effective_where = where or (src.get("queryTemplateParams") or {}).get(
        "where", "1=1")
    page_size = int(src.get("maxRecordCount") or 2000)
    params: Dict[str, Any] = {
        "where": effective_where, "outFields": "*", "f": "json",
        "resultRecordCount": page_size, "resultOffset": 0,
    }
    if src.get("oidField"):
        params["orderByFields"] = src["oidField"]
    if bbox:
        params.update({
            "geometry": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "geometryType": "esriGeometryEnvelope", "inSR": 28992,
            "spatialRel": "esriSpatialRelIntersects",
        })
    session = session or requests.Session()
    feats: List[dict] = []
    while True:
        resp = session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        page = body.get("features") or []
        feats.extend(page)
        got = len(page)
        exceeded = bool(body.get("exceededTransferLimit"))
        params["resultOffset"] += got
        if got == 0 or (not exceeded and got < page_size):
            break
        time.sleep(0.2)

    doc = {
        "type": "FeatureCollection",
        "properties": {
            "sourceId": source_id, "where": effective_where,
            "bbox": bbox, "featureCount": len(feats),
            "attributeGeometryOnly": True,
            "fetchedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(
                timespec="seconds"),
            "queryFingerprint": fp,
        },
        # esri features kept raw; parse_* below reads .attributes
        "features": feats,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return doc


def _attr(f: Mapping[str, Any]) -> Dict[str, Any]:
    """Attributes of an esri-json or geojson feature, with x/y resolved."""
    a = dict(f.get("attributes") or f.get("properties") or {})
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates") or [None, None]
    # EPSG:28992 geometry, attribute X/Y columns as fallback (logger
    # points carry NULL geometry and only attribute coordinates)
    a["x"] = a.get("XCOORDINAAT") or (coords[0] if coords else None)
    a["y"] = a.get("YCOORDINAAT") or (coords[1] if coords else None)
    return a


def parse_loggers(fc: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Meetlocatie features → logger dicts (code, name, polder, peil, x/y)."""
    loggers = []
    for f in fc.get("features", []):
        a = _attr(f)
        if not a.get("CODE") or a.get("x") is None:
            continue
        loggers.append({
            "code": str(a["CODE"]),
            "name": a.get("NAAM") or a["CODE"],
            "lizardId": a.get("LIZARDID") or None,
            "soortObject": a.get("SOORTOBJECT"),
            "polder": a.get("NAAMPOLDER") or None,
            "peilgebied": a.get("NAAMPEILGEBIED") or None,
            "soortPeilgebied": a.get("SOORTPEILGEBIED") or None,
            "zomerpeil": a.get("ZOMERPEIL"),
            "winterpeil": a.get("WINTERPEIL"),
            "x": round(float(a["x"]), 2),
            "y": round(float(a["y"]), 2),
        })
    loggers.sort(key=lambda l: l["code"])
    return loggers


def parse_points(fc: Mapping[str, Any], with_polder: bool = False
                 ) -> List[Dict[str, Any]]:
    """Generic point parse (meteo gauges, gemalen) → dicts with code + x/y."""
    out = []
    for f in fc.get("features", []):
        a = _attr(f)
        code = a.get("CODE")
        if not code or a.get("x") is None:
            continue
        rec = {
            "code": str(code),
            "name": a.get("NAAM") or str(code),
            "x": round(float(a["x"]), 2),
            "y": round(float(a["y"]), 2),
        }
        if a.get("ONTWERPCAPACITEIT") is not None:
            rec["capaciteit"] = a["ONTWERPCAPACITEIT"]
        if with_polder and a.get("NAAMPOLDER"):
            rec["polder"] = a["NAAMPOLDER"]
        out.append(rec)
    out.sort(key=lambda r: r["code"])
    return out
