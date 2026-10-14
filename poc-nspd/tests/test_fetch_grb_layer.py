"""GRB-laagfetch (fase 2, task 1E): GRB:ADP via Geopunt WFS → WGS84-viewerlaag.

``fetch_grb_layer.main`` haalt de GRB-gebouwvoetafdrukken via
``pipeline.national_data.fetch_geopunt_wfs`` (cache-first, bron
``geopunt-grb-wfs`` uit ``data/sources.json``, typeName ``GRB:ADP``,
bbox = ``nspd_bbox_l72()``) en herschrijft alle feature-geometrieën
Lambert72 (EPSG:31370) → WGS84 (EPSG:4326) naar
``<out_dir>/layers/grb-gebouwen-be.geojson``. Tests met fake-transport
(geen netwerk): transformatie-controle op een mini-polygoon plus
cache-hit-gedrag.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fetch_grb_layer  # noqa: E402
from bbox import nspd_bbox_l72  # noqa: E402
from pipeline import national_data  # noqa: E402


def _mini_fc_l72() -> dict:
    """Mini-GRB:ADP-antwoord: één vierkant pand rond Lambert72 (104000, 192000)."""
    ring = [[104000.0, 192000.0], [104100.0, 192000.0],
            [104100.0, 192100.0], [104000.0, 192100.0], [104000.0, 192000.0]]
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "id": "GRB-ADP-1",
            "properties": {"OIDN": 424242},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }],
    }


def test_main_schrijft_wgs84_laag_uit_fake_transport(tmp_path, monkeypatch):
    """Fake-transport → laagbestand geschreven; geometrie in EPSG:4326;
    WFS-wiring: gepinde typeName GRB:ADP + Lambert72-NSPD-bbox in de URL."""
    monkeypatch.setattr(national_data, "CACHE", tmp_path / "cache")
    urls: list[str] = []

    def fake_transport(url: str) -> dict:
        urls.append(url)
        return _mini_fc_l72()

    uit = fetch_grb_layer.main(out_dir=tmp_path / "viewer-data", transport=fake_transport)

    assert uit == tmp_path / "viewer-data" / "layers" / "grb-gebouwen-be.geojson"
    assert uit.is_file()
    # cache-first-weg raakt het netwerk precies eenmaal, met de juiste WFS-query
    assert len(urls) == 1
    assert "typeNames=GRB%3AADP" in urls[0]
    assert "srsName=urn:ogc:def:crs:EPSG::31370" in urls[0]
    x0, y0, x1, y1 = nspd_bbox_l72()
    for waarde in (x0, y0, x1, y1):
        assert str(waarde) in urls[0], \
            f"bbox-waarde {waarde} niet in WFS-URL: {urls[0]}"
    # geometrie omgezet naar WGS84: L72 (104000, 192000) → ≈ (3.713, 51.036)
    doc = json.loads(uit.read_text(encoding="utf-8"))
    assert doc["type"] == "FeatureCollection"
    assert doc["crs"]["properties"]["name"] == "urn:ogc:def:crs:EPSG::4326"
    assert doc["sourceId"] == "geopunt-grb-wfs"
    ring = doc["features"][0]["geometry"]["coordinates"][0]
    assert doc["features"][0]["geometry"]["type"] == "Polygon"
    assert doc["features"][0]["properties"] == {"OIDN": 424242}
    for lon, lat in ring:
        assert 3.70 <= lon <= 3.73 and 51.02 <= lat <= 51.05, (lon, lat)
    lon0, lat0 = ring[0]
    assert abs(lon0 - 3.713) <= 0.01 and abs(lat0 - 51.036) <= 0.01, (lon0, lat0)
    # het 100 m-vierkant blijft klein in graden (geen coördinaatverwisseling)
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    assert max(lons) - min(lons) < 0.005 and max(lats) - min(lats) < 0.005


def test_cache_hit_slaat_transport_over(tmp_path, monkeypatch):
    """Geldige cache (data/cache/be/<cache_name>) → geen transport-aanroep;
    de laag wordt uit de cache geschreven (cache-first, geen netwerk)."""
    monkeypatch.setattr(national_data, "CACHE", tmp_path / "cache")
    cache = tmp_path / "cache" / "be" / fetch_grb_layer.CACHE_NAME
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "sourceId": "geopunt-grb-wfs",
        "retrieved": "2026-10-14T00:00:00+00:00",
        "records": _mini_fc_l72(),
    }), encoding="utf-8")

    def boem(url: str) -> dict:
        raise AssertionError(f"netwerk geraakt ondanks geldige cache: {url}")

    uit = fetch_grb_layer.main(out_dir=tmp_path / "viewer-data", transport=boem)
    doc = json.loads(uit.read_text(encoding="utf-8"))
    assert len(doc["features"]) == 1
    assert doc["retrieved"] == "2026-10-14T00:00:00+00:00"  # uit de cache, niet nu()
