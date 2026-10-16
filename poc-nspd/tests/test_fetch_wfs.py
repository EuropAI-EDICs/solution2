"""WFS-fetchtak in geodata.fetch_layer — Zeeland OVZ-lagen (fase 3, task 1).

fetch_wfs_features haalt een WFS 2.0-typeName (GeoJSON-uitvoer in EPSG:28992 via
srsName, bbox als URN in RD, paging via startIndex) en fetch_layer cached die als
``<source_id>.28992.geojson`` + WGS84-tweeling, conform het ogc-api/arcgis-patroon.
Tests met een fake session (geen netwerk).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geodata  # noqa: E402

_FYS = {"service": "WFS", "version": "2.0.0", "request": "GetFeature"}
RD_BBOX = (20500.0, 403000.0, 54500.0, 438000.0)


def _fc(n: int, naam: str = "A") -> dict:
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": f"a.{i}",
         "properties": {"naam": naam},
         "geometry": {"type": "Polygon", "coordinates": [
             [[1000 + i, 400000], [2000 + i, 400000], [2000 + i, 401000],
              [1000 + i, 401000], [1000 + i, 400000]]]}}
        for i in range(n)]}


class _Resp:
    def __init__(self, body, url=""):
        self._body = body
        self.status = 200
        self.status_code = 200
        self.url = url
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("Expecting value")  # echte requests-gedrag op XML
        return self._body


class _FakeSession:
    headers: dict = {}

    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        body = self.bodies.pop(0)
        return _Resp(body, url=url)


_SRC = {
    "id": "zeeland-ovz-windconcl",
    "endpointType": "wfs",
    "serviceUrl": "https://opengeodata.zeeland.nl/geoserver/ows",
    "layerId": "dso:ext_ovz_windnrg_concloc",
}


def test_fetch_wfs_params_en_paging():
    """URL-params: typeNames, srsName RD, bbox-URN, count/startIndex; paging stopt
    zodra een pagina onder de paginagrootte blijft."""
    sess = _FakeSession([_fc(1000), _fc(3)])
    feats, pages = geodata.fetch_wfs_features(sess, dict(_SRC, maxRecordCount=1000), bbox=RD_BBOX)
    assert len(feats) == 1003 and pages == 2
    p1, p2 = sess.calls
    assert p1["params"]["service"] == "WFS" and p1["params"]["version"] == "2.0.0"
    assert p1["params"]["request"] == "GetFeature"
    assert p1["params"]["typeNames"] == "dso:ext_ovz_windnrg_concloc"
    assert p1["params"]["outputFormat"] == "application/json"
    assert p1["params"]["srsName"] == "urn:ogc:def:crs:EPSG::28992"
    assert p1["params"]["count"] == 1000 and p1["params"]["startIndex"] == 0
    assert p1["params"]["bbox"].endswith("urn:ogc:def:crs:EPSG::28992")
    assert p1["params"]["bbox"].startswith("20500.0,403000.0,54500.0,438000.0")
    assert p2["params"]["startIndex"] == 1000


def test_fetch_wfs_geen_layerid_faalt_luid():
    try:
        geodata.fetch_wfs_features(_FakeSession([]), {"id": "x", "endpointType": "wfs",
                                                      "serviceUrl": "https://x"})
        raise AssertionError("verwachte GeoDataError")
    except geodata.GeoDataError as exc:
        assert "layerId" in str(exc)


def test_fetch_wfs_niet_json_faalt_luid():
    sess = _FakeSession(["<?xml?><exceptionReport/>"])
    try:
        geodata.fetch_wfs_features(sess, dict(_SRC), bbox=RD_BBOX)
        raise AssertionError("verwachte GeoDataError")
    except geodata.GeoDataError as exc:
        assert "non-JSON" in str(exc)


def test_fetch_layer_wfs_cached_rd_en_wgs(tmp_path):
    sources = {s["id"]: s for s in [_SRC]}
    sess = _FakeSession([_fc(2)])
    fc = geodata.fetch_layer("zeeland-ovz-windconcl", bbox=RD_BBOX, sources=sources,
                             cache_dir=tmp_path, session=sess)
    assert len(fc["features"]) == 2
    assert fc["crs"]["properties"]["name"] == "EPSG:28992"
    assert fc["properties"]["sourceId"] == "zeeland-ovz-windconcl"
    assert fc["properties"]["layerId"] == "dso:ext_ovz_windnrg_concloc"
    rd = tmp_path / "zeeland-ovz-windconcl.28992.geojson"
    wgs = tmp_path / "zeeland-ovz-windconcl.4326.geojson"
    assert rd.is_file() and wgs.is_file()
    # tweede aanroep raakt de cache, niet het netwerk
    sess2 = _FakeSession([])
    fc2 = geodata.fetch_layer("zeeland-ovz-windconcl", bbox=RD_BBOX, sources=sources,
                              cache_dir=tmp_path, session=sess2)
    assert len(fc2["features"]) == 2 and sess2.calls == []


def test_fetch_layer_wfs_geometrieloze_features_geskipt():
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "b.1", "properties": {}, "geometry": None},
        _fc(1)["features"][0]]}
    sess = _FakeSession([fc])
    feats, pages = geodata.fetch_wfs_features(sess, dict(_SRC), bbox=RD_BBOX)
    assert len(feats) == 1 and pages == 1
