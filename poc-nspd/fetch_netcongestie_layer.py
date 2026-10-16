"""Netcongestie-laag voor de viewer — Landelijke Capaciteitskaart 'afname' → WGS84.

Scenario-bronlaag (energie-infrastructuur, spec §4.5; scenario-basis voor de
track energietoets). Bron ``netbeheerder-netcongestie`` uit ``data/sources.json``
(ArcGIS FeatureServer van Netbeheer Nederland, gepind 2026-10-16: 13
voedingsgebieden binnen de NSPD-bbox).

- cache: ``data/cache/national/netcongestie/netcongestie.geojson`` — hetzelfde
  pad dat ``pipeline.national_data.load_netcongestie`` leest, dus één download
  voedt pipeline én viewer; cache-first, ``--refresh`` haalt opnieuw op;
- viewer-laag: ``<out_dir>/layers/netcongestie-afname-nl.geojson`` — de ruwe
  export is 31,7 MB / 885k vertices (één landelijke restpolygoon van 832k), dus
  elke feature wordt geclipt op ``NSPD_BBOX_WGS84`` en gesimplificeerd
  (``SIMPLIFY_DEG`` ≈ 30 m); resultaat ≈ 55 KB. Properties blijven 1-op-1,
  plus ``afname_label`` (code → tekst, zie bron-note).

Run: ``python3 fetch_netcongestie_layer.py [--out-dir <dir>] [--refresh]``.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import box, mapping, shape  # noqa: E402
from shapely.validation import make_valid  # noqa: E402

from bbox import NSPD_BBOX_WGS84  # noqa: E402
from pipeline import geodata, national_data  # noqa: E402

SOURCE_ID = "netbeheerder-netcongestie"
LAAG_BESTAND = "netcongestie-afname-nl.geojson"
SIMPLIFY_DEG = 0.0003
OUT_FIELDS = ("afname,opwek,voedingsgebied_id,voedingsgebied_naam,wachtrij_afname,"
              "wachtrij_invoeding,unieke_verzoeken_afname,unieke_verzoeken_invoeding,RNB")
AFNAME_LABEL = {0: "beschikbaar", 1: "beperkt", 2: "in onderzoek", 3: "tekort (wachtrij)"}


def query_url(service_url: str, bbox_wgs84: tuple[float, float, float, float]) -> str:
    """ArcGIS REST query: alle voedingsgebieden die de bbox snijden, als GeoJSON in WGS84."""
    x0, y0, x1, y1 = bbox_wgs84
    params = {
        "where": "1=1",
        "geometry": f"{x0},{y0},{x1},{y1}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": OUT_FIELDS,
        "outSR": "4326",
        "f": "geojson",
    }
    return service_url.rstrip("/") + "/query?" + urllib.parse.urlencode(params)


def _cache_pad() -> Path:
    return national_data.CACHE / "national" / "netcongestie" / "netcongestie.geojson"


def main(out_dir: Path | str | None = None, refresh: bool = False,
         transport: national_data.Transport | None = None) -> Path:
    """Fetch (cache-first) en schrijf de geclipte, gesimplificeerde viewerlaag; geeft het pad."""
    bron = geodata.load_sources().get(SOURCE_ID)
    if bron is None:
        raise geodata.GeoDataError(
            f"bron {SOURCE_ID!r} ontbreekt in de registry (data/sources.json)")
    cache = _cache_pad()
    if not cache.is_file() or refresh:
        haal = transport or national_data._default_transport
        fc = haal(query_url(bron.get("serviceUrl", ""), NSPD_BBOX_WGS84))
        if fc.get("type") != "FeatureCollection":
            raise geodata.GeoDataError(
                f"onverwacht antwoord van {SOURCE_ID}: {json.dumps(fc)[:200]}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    payload = national_data.load_netcongestie()
    venster = box(*NSPD_BBOX_WGS84)
    features = []
    for f in (payload.get("records") or {}).get("features") or []:
        geom = f.get("geometry")
        if geom is None:
            continue
        g = make_valid(shape(geom)).intersection(venster)
        if g.is_empty:
            continue
        g = g.simplify(SIMPLIFY_DEG, preserve_topology=True)
        props = dict(f.get("properties") or {})
        props["afname_label"] = AFNAME_LABEL.get(props.get("afname"), "onbekend")
        features.append({"type": "Feature", "id": f.get("id"),
                         "properties": props, "geometry": mapping(g)})
    uit_fc = {
        "type": "FeatureCollection",
        "name": f"Netcongestie afname NL ({SOURCE_ID}, geclipt op NSPD-bbox, simplify {SIMPLIFY_DEG}°)",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "sourceId": SOURCE_ID,
        "retrieved": payload.get("retrieved"),
        "features": features,
    }
    basis = Path(out_dir) if out_dir is not None else ROOT / "viewer-data"
    pad = basis / "layers" / LAAG_BESTAND
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(json.dumps(uit_fc, ensure_ascii=False), encoding="utf-8")
    return pad


if __name__ == "__main__":
    _p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    _p.add_argument("--out-dir", default=str(ROOT / "viewer-data"),
                    help="doelmap (default: viewer-data/)")
    _p.add_argument("--refresh", action="store_true",
                    help="cache negeren en opnieuw fetchen")
    _a = _p.parse_args()
    _pad = main(out_dir=_a.out_dir, refresh=_a.refresh)
    _n = len(json.loads(_pad.read_text(encoding="utf-8"))["features"])
    print(f"OK {_pad} ({_n} voedingsgebieden, geclipt+gesimplificeerd, WGS84)")
