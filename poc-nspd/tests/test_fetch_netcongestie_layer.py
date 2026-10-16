"""Netcongestie-viewerlaag: ArcGIS Capaciteitskaart 'afname' → geclipt+gesimplificeerd.

``fetch_netcongestie_layer.main`` haalt (cache-first) de voedingsgebieden via de
gepinde bron ``netbeheerder-netcongestie``, schrijft de cache op het pad dat
``pipeline.national_data.load_netcongestie`` leest, en clipt/simplificeert de
features op de NSPD-bbox naar ``<out_dir>/layers/netcongestie-afname-nl.geojson``.
Tests met fake-transport (geen netwerk).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fetch_netcongestie_layer  # noqa: E402
from bbox import NSPD_BBOX_WGS84  # noqa: E402
from pipeline import national_data  # noqa: E402


def _fc_twee_gebieden() -> dict:
    """Eén gebied half in de NSPD-bbox (steekt noordelijk uit), één ver buiten."""
    x0, y0, x1, y1 = NSPD_BBOX_WGS84
    binnen = [[x0 + 0.1, y1 - 0.1], [x0 + 0.3, y1 - 0.1], [x0 + 0.3, y1 + 0.2],
              [x0 + 0.1, y1 + 0.2], [x0 + 0.1, y1 - 0.1]]
    buiten = [[6.0, 52.0], [6.1, 52.0], [6.1, 52.1], [6.0, 52.1], [6.0, 52.0]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": 1,
         "properties": {"afname": 1, "opwek": 0, "voedingsgebied_naam": "Westdorpe"},
         "geometry": {"type": "Polygon", "coordinates": [binnen]}},
        {"type": "Feature", "id": 2,
         "properties": {"afname": 3, "opwek": 3, "voedingsgebied_naam": "Elders"},
         "geometry": {"type": "Polygon", "coordinates": [buiten]}},
    ]}


def test_main_clipt_op_bbox_en_schrijft_cache_op_loaderpad(tmp_path, monkeypatch):
    monkeypatch.setattr(national_data, "CACHE", tmp_path / "cache")
    urls: list[str] = []

    def fake_transport(url: str) -> dict:
        urls.append(url)
        return _fc_twee_gebieden()

    uit = fetch_netcongestie_layer.main(out_dir=tmp_path / "vd", transport=fake_transport)

    assert uit == tmp_path / "vd" / "layers" / "netcongestie-afname-nl.geojson"
    assert len(urls) == 1
    assert "f=geojson" in urls[0] and "outSR=4326" in urls[0]
    assert "geometry=3.45%2C51.02%2C3.88%2C51.48" in urls[0]
    assert urls[0].startswith("https://services.arcgis.com/")
    # cache op het pad van load_netcongestie → de pipeline leest dezelfde download
    cache = tmp_path / "cache" / "national" / "netcongestie" / "netcongestie.geojson"
    assert cache.is_file()
    assert national_data.load_netcongestie()["records"]["features"][1]["id"] == 2
    doc = json.loads(uit.read_text(encoding="utf-8"))
    assert doc["sourceId"] == "netbeheerder-netcongestie"
    assert len(doc["features"]) == 1, "gebied buiten de bbox moet wegvallen"
    f = doc["features"][0]
    assert f["properties"]["voedingsgebied_naam"] == "Westdorpe"
    assert f["properties"]["afname_label"] == "beperkt"
    x0, y0, x1, y1 = NSPD_BBOX_WGS84
    for ring in f["geometry"]["coordinates"]:
        for lon, lat in ring:
            assert x0 - 1e-9 <= lon <= x1 + 1e-9 and y0 - 1e-9 <= lat <= y1 + 1e-9, (lon, lat)


def test_cache_hit_slaat_transport_over(tmp_path, monkeypatch):
    monkeypatch.setattr(national_data, "CACHE", tmp_path / "cache")
    cache = tmp_path / "cache" / "national" / "netcongestie" / "netcongestie.geojson"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(_fc_twee_gebieden()), encoding="utf-8")

    def boem(url: str) -> dict:
        raise AssertionError(f"netwerk geraakt ondanks geldige cache: {url}")

    uit = fetch_netcongestie_layer.main(out_dir=tmp_path / "vd", transport=boem)
    assert len(json.loads(uit.read_text(encoding="utf-8"))["features"]) == 1
