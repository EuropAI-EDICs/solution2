"""OGC API Features-tak in geodata.fetch_layer — PDOK-catalogus (2026-10-16).

fetch_ogc_api_features volgt ``links[rel=next]`` (GoKoala-cursor), draait voor
``axisOrder: "latlon"``-diensten (REV/Seveso) bbox én coördinaten om, geeft
elke pagina als-ontvangen aan ``raw_sink`` (lake-bronze) en weigert een
truncated antwoord (numberMatched > ontvangen zonder next-link).
Tests met een fake session (geen netwerk).
"""
import json
import sys
from pathlib import Path

import pytest
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geodata  # noqa: E402

RD_BBOX = (20500.0, 403000.0, 54500.0, 438000.0)
_WGS_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)


def _pt(lon: float, lat: float, latlon: bool = False) -> dict:
    coords = [lat, lon] if latlon else [lon, lat]
    return {"type": "Feature", "id": f"p-{lon}-{lat}", "properties": {"naam": "x"},
            "geometry": {"type": "Point", "coordinates": coords}}


def _page(feats, next_href=None, matched=None) -> dict:
    body = {"type": "FeatureCollection", "features": feats, "numberReturned": len(feats),
            "links": [{"rel": "self", "href": "x"}]}
    if next_href:
        body["links"].append({"rel": "next", "href": next_href})
    if matched is not None:
        body["numberMatched"] = matched
    return body


class _Resp:
    def __init__(self, body, url=""):
        self._body = body
        self.status_code = 200
        self.url = url
        self.text = json.dumps(body)
        self.content = self.text.encode("utf-8")

    def json(self):
        return self._body


class _FakeSession:
    headers: dict = {}

    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        return _Resp(self.bodies.pop(0), url=url)


def _src(sid="pdok-test", **extra):
    return {sid: {"id": sid, "endpointType": "ogc-api", "collection": "c1",
                  "serviceUrl": "https://api.pdok.nl/x/y/ogc/v1", "title": "t", **extra}}


def test_next_link_paging_en_cache(tmp_path):
    sess = _FakeSession([
        _page([_pt(3.6, 51.3)], next_href="https://api.pdok.nl/x/y/ogc/v1/collections/c1/items?cursor=abc&limit=1000"),
        _page([_pt(3.7, 51.4)]),
    ])
    sinks = []
    fc = geodata.fetch_layer("pdok-test", bbox=RD_BBOX, sources=_src(), cache_dir=tmp_path,
                             session=sess, raw_sink=lambda i, u, c: sinks.append((i, u, len(c))))
    assert fc["properties"]["featureCount"] == 2 and fc["properties"]["pages"] == 2
    # pagina 1: bbox in lon,lat + bbox-crs; pagina 2: next-href zónder extra params
    assert sess.calls[0]["params"]["bbox"].startswith("3.4") and "bbox-crs" in sess.calls[0]["params"]
    assert sess.calls[1]["params"] is None and "cursor=abc" in sess.calls[1]["url"]
    x, y = _WGS_TO_RD.transform(3.6, 51.3)
    gx, gy = fc["features"][0]["geometry"]["coordinates"]
    assert abs(gx - x) < 0.01 and abs(gy - y) < 0.01
    assert [s[0] for s in sinks] == [0, 1] and all(s[2] > 0 for s in sinks)
    assert (tmp_path / "pdok-test.28992.geojson").is_file()
    assert (tmp_path / "pdok-test.4326.geojson").is_file()
    assert fc["properties"]["collection"] == "c1" and fc["properties"]["axisOrder"] == "lonlat"


def test_axis_order_latlon_draait_bbox_en_coordinaten_om(tmp_path):
    sess = _FakeSession([_page([_pt(3.6, 51.3, latlon=True)])])
    fc = geodata.fetch_layer("pdok-rev", bbox=RD_BBOX, sources=_src("pdok-rev", axisOrder="latlon"),
                             cache_dir=tmp_path, session=sess)
    bbox = sess.calls[0]["params"]["bbox"].split(",")
    assert float(bbox[0]) > 50 and float(bbox[1]) < 5, "bbox moet lat,lon zijn"
    assert "bbox-crs" not in sess.calls[0]["params"]
    x, y = _WGS_TO_RD.transform(3.6, 51.3)
    gx, gy = fc["features"][0]["geometry"]["coordinates"]
    assert abs(gx - x) < 0.01 and abs(gy - y) < 0.01
    assert fc["properties"]["axisOrder"] == "latlon"


def test_truncatie_zonder_next_link_faalt_luid(tmp_path):
    sess = _FakeSession([_page([_pt(3.6, 51.3)], matched=5)])
    with pytest.raises(geodata.GeoDataError, match="numberMatched"):
        geodata.fetch_layer("pdok-test", bbox=RD_BBOX, sources=_src(), cache_dir=tmp_path, session=sess)
    assert not (tmp_path / "pdok-test.28992.geojson").exists()


def test_volle_laatste_pagina_zonder_next_is_compleet(tmp_path):
    feats = [_pt(3.6 + i * 0.001, 51.3) for i in range(3)]
    sess = _FakeSession([_page(feats)])
    fc = geodata.fetch_layer("pdok-test", bbox=RD_BBOX, sources=_src("pdok-test", pageLimit=3),
                             cache_dir=tmp_path, session=sess)
    assert fc["properties"]["featureCount"] == 3 and sess.calls[0]["params"]["limit"] == 3


def test_cqlfilter_client_side_in_ogc_pad(tmp_path):
    sess = _FakeSession([_page([_pt(3.60, 51.30), _pt(3.65, 51.35), _pt(3.70, 51.40)])])
    src = _src("pdok-ge75", queryTemplateParams={"cqlFilter": "klasse = '5'"})
    # features krijgen de gefilterde property mee in de fake-antwort; filter op props
    sess.bodies = [{"type": "FeatureCollection", "numberReturned": 3, "features": [
        {"type": "Feature", "id": f"k{i}", "properties": {"klasse": k},
         "geometry": {"type": "Point", "coordinates": [3.6 + i * 0.01, 51.3]}}
        for i, k in enumerate((3, 5, 5))]}]
    fc = geodata.fetch_layer("pdok-ge75", bbox=RD_BBOX, sources=src, cache_dir=tmp_path, session=sess)
    assert [f["properties"]["klasse"] for f in fc["features"]] == [5, 5]
    assert fc["properties"]["featureCount"] == 2
