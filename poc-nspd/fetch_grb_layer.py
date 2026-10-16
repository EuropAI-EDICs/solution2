"""GRB-percelenlaag voor de viewer — GRB:ADP via Geopunt WFS, Lambert72 → WGS84.

NB (2026-10-16): GRB:ADP = *administratieve percelen* (kadastrale percelen,
attributen CAPAKEY/CANU), géén gebouwen — fase 1 noemde deze laag ten onrechte
"gebouwen". Gebouwen in de viewer komen uit de referentielaag "3D Gebouwen
België" (Zeeland-config); GRB-gebouwvoetafdrukken zouden GRB:GBG zijn.

Fase 2, task 1E (eindreview-voorbereiding). De viewer-config verwijst naar
``layers/grb-percelen-be.geojson`` (laag ``grb-percelen`` in
``make_viewer_config.py``; taak-12-besluit "vlak": ``GRB:ADP`` heeft geen
hoogteveld, DHM-extrusie is buiten POC-scope). Dit script genereert dat
bestand:

- bron: ``geopunt-grb-wfs`` uit ``data/sources.json`` (live-gepind
  2026-10-14, zie ``data/probe_2026-10-14.json``: GetFeature ``GRB:ADP``
  count=3 binnen de NSPD-bbox, EPSG::31370);
- fetch: ``pipeline.national_data.fetch_geopunt_wfs`` — cache-first onder
  ``data/cache/be/``, WFS 2.0 GetFeature met ``srsName``/``bbox`` in
  Lambert72, begrensd op ``bbox.nspd_bbox_l72()``;
- transformatie: alle feature-geometrieën Lambert72 (EPSG:31370) → WGS84
  (EPSG:4326) via pyproj (``always_xy``: x/oost, y/noord);
- uitvoer: FeatureCollection (properties blijft 1-op-1) naar
  ``<out_dir>/layers/grb-percelen-be.geojson`` (default ``viewer-data/``,
  git-ignored zoals alle viewer-data).

Run: ``python3 fetch_grb_layer.py [--out-dir <dir>] [--refresh]``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pyproj import Transformer  # noqa: E402

from bbox import nspd_bbox_l72  # noqa: E402
from pipeline import geodata, national_data  # noqa: E402

SOURCE_ID = "geopunt-grb-wfs"
TYPE_NAME = "GRB:ADP"
CACHE_NAME = "grb-adp-be.geojson"
LAAG_BESTAND = "grb-percelen-be.geojson"

_L72_NAAR_WGS84 = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)


def _wgs84_positie(pos: list) -> list:
    lon, lat = _L72_NAAR_WGS84.transform(pos[0], pos[1])
    return [lon, lat, *pos[2:]]  # eventuele z-waarden ongemoeid laten


def _wgs84_ring(ring: list) -> list:
    return [_wgs84_positie(p) for p in ring]


def _wgs84_geometrie(geom: dict) -> dict:
    """Lambert72-GeoJSON-geometrie → WGS84 (zelfde type, getransformeerde coords)."""
    soort = geom.get("type")
    coords = geom["coordinates"]
    if soort == "Point":
        coords = _wgs84_positie(coords)
    elif soort == "MultiPoint" or soort == "LineString":
        coords = [_wgs84_positie(p) for p in coords]
    elif soort == "MultiLineString":
        coords = [_wgs84_ring(r) for r in coords]
    elif soort == "Polygon":
        coords = [_wgs84_ring(r) for r in coords]
    elif soort == "MultiPolygon":
        coords = [[_wgs84_ring(r) for r in poly] for poly in coords]
    else:
        raise ValueError(f"onbekend geometrietype in GRB-ADP-antwoord: {soort!r}")
    return {"type": soort, "coordinates": coords}


def main(out_dir: Path | str | None = None, refresh: bool = False,
         transport: national_data.Transport | None = None) -> Path:
    """Fetch GRB:ADP (cache-first) en schrijf de WGS84-viewerlaag; geeft het pad."""
    bron = geodata.load_sources().get(SOURCE_ID)
    if bron is None:
        raise geodata.GeoDataError(
            f"bron {SOURCE_ID!r} ontbreekt in de registry (data/sources.json)")
    payload = national_data.fetch_geopunt_wfs(
        service_url=bron.get("serviceUrl", ""),
        type_name=TYPE_NAME,
        bbox_l72=nspd_bbox_l72(),
        cache_name=CACHE_NAME,
        source_id=SOURCE_ID,
        refresh=refresh,
        transport=transport,
    )
    fc = payload.get("records") or {}
    features = []
    for f in fc.get("features") or []:
        geom = f.get("geometry")
        if geom is None:  # geometrielose features hebben in de viewer niets te zoeken
            continue
        features.append({
            "type": "Feature",
            "id": f.get("id"),
            "properties": f.get("properties") or {},
            "geometry": _wgs84_geometrie(geom),
        })
    uit_fc = {
        "type": "FeatureCollection",
        "name": f"GRB ADP percelen ({SOURCE_ID}, NSPD-bbox)",
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
    n = len(json.loads(_pad.read_text(encoding="utf-8"))["features"])
    print(f"OK {_pad} ({n} perceelfeatures, WGS84)")
