"""National-data fetchers — offline, via fixtures en fake transport.

Live-pinning (plan-2 task 4, stap 1): de CBS OData-tabellen voor het
100m-grid bestaan niet meer; de opvolger is de PDOK OGC API
'vierkantstatistieken100m' (collectie vierkant100) met celkolom
``crs28992res100m`` ("E1300N4400" = RD-hoek 130000/440000, cel 100m).
Landgebruik is via PDOK 'existinglanduse' gepind (zie module-docstring).
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import national_data as nd  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "national"


def test_record_in_utrecht_bbox():
    # live celkolom crs28992res100m: 'E' + x/100 + 'N' + y/100 (RD-meters)
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "E1300N4400"}) is True
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "E1400N4550"}) is True
    # net buiten de bbox: middenpunt x > 160000 resp. y < 440000
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "E1604N4699"}) is False
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "E0900N0300"}) is False
    # legacy CBS-code 'b' + x-m/100 + y-m/100 blijft leesbaar (oude caches)
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "b13004400"}) is True
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "b09030000"}) is False
    assert nd.record_in_utrecht_bbox({}) is False
    assert nd.record_in_utrecht_bbox({"crs28992res100m": "geen-cel"}) is False


def test_cell_rd_formaat():
    assert nd._cell_rd("E1300N4400") == (130050.0, 440050.0)
    assert nd._cell_rd("E1307N4699") == (130750.0, 469950.0)
    assert nd._cell_rd("b13004400") == (130050.0, 440050.0)
    assert nd._cell_rd("") is None
    assert nd._cell_rd("X1300N4400") is None


def test_fetch_cbs_dataset_pages_en_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    calls = []
    fixture = nd.json.loads((FIXTURES / "cbs_grid_sample.json").read_text())
    page2 = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "crs28992res100m": "E1400N4550",
                    "jaarcode": 2024,
                    "aantal_inwoners": 7,
                    "aantal_woningen": 4,
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "crs28992res100m": "geen-cel",
                    "jaarcode": 2024,
                    "aantal_inwoners": 1,
                    "aantal_woningen": 1,
                },
            },
        ],
        "links": [],
    }

    def transport(url: str) -> dict:
        calls.append(url)
        return page2 if "offset=" in url else fixture

    out = nd.fetch_cbs_dataset(
        dataset_id=nd.CBS_GRID_DATASET,
        cache_name="test-grid.json",
        refresh=True,
        transport=transport,
        cql_filter=nd.CBS_GRID_FILTER,
    )
    assert out["sourceId"] == "cbs-grid-kerncijfers-100m"
    assert len(out["records"]) == 2          # alleen Utrecht-bbox-cellen
    assert out["records"][0]["crs28992res100m"] == "E1300N4400"
    assert "filter=jaarcode%3D2024" in calls[0]
    assert "bbox=130000" in calls[0]
    assert len(calls) == 2                   # paging: pagina 1 + next-link
    # cache-hit: tweede call raakt de transport niet meer
    calls.clear()
    out2 = nd.fetch_cbs_dataset(
        dataset_id=nd.CBS_GRID_DATASET,
        cache_name="test-grid.json",
        refresh=False,
        transport=transport,
    )
    assert calls == []
    assert out2["records"] == out["records"]


def test_fetch_landgebruik_wrapper(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    calls = []
    page = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "BBG2017_15",
                    "description": "Railroad",
                    "specificlanduse_title": "Spoorterrein_Spoorterrein",
                },
            },
        ],
        "links": [],
    }

    def transport(url: str) -> dict:
        calls.append(url)
        return page

    out = nd.fetch_landgebruik(refresh=True, transport=transport)
    assert out["sourceId"] == "cbs-landgebruik-100m"
    assert "/cbs/landuse/ogc/v1/collections/existinglanduse/items" in calls[0]
    # geen celcode in deze bron: records vallen samen met de properties
    assert out["records"] == [page["features"][0]["properties"]]


def test_fetch_wfs_filtert_bbox_en_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    payload = nd.json.loads((FIXTURES / "wfs_sample.json").read_text())

    def transport(url: str) -> dict:
        assert "bbox=" in url
        return payload

    out = nd.fetch_wfs(
        service_url="https://example/wfs", type_name="test:laag",
        bbox_rd=nd.UTRECHT_BBOX_RD, cache_name="test-wfs.json",
        refresh=True, transport=transport,
        source_id="rce-monumenten")
    assert out["sourceId"] == "rce-monumenten"
    assert out["records"]["type"] == "FeatureCollection"
    calls = []

    def transport2(url: str) -> dict:
        calls.append(url)
        return payload

    nd.fetch_wfs(service_url="https://example/wfs", type_name="test:laag",
                 bbox_rd=nd.UTRECHT_BBOX_RD, cache_name="test-wfs.json",
                 refresh=False, transport=transport2, source_id="rce-monumenten")
    assert calls == []


def test_fetch_wfs_url_vorm(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    payload = nd.json.loads((FIXTURES / "wfs_sample.json").read_text())
    calls = []

    def transport(url: str) -> dict:
        calls.append(url)
        return payload

    nd.fetch_wfs(service_url="https://example/wfs", type_name="test:laag",
                 bbox_rd=nd.UTRECHT_BBOX_RD, cache_name="url-vorm.json",
                 refresh=True, transport=transport, source_id="test-bron")
    url = calls[0]
    assert url.startswith("https://example/wfs?")
    assert "service=WFS" in url
    assert "version=2.0.0" in url
    assert "request=GetFeature" in url
    assert "typeNames=test%3Alaag" in url
    assert "outputFormat=application/json" in url
    assert "bbox=130000.0%2C440000.0%2C160000.0%2C470000.0%2Curn%3Aogc%3Adef%3Acrs%3AEPSG%3A%3A28992" in url


def test_wrappers_gebruiken_gepinde_lagen(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    payload = nd.json.loads((FIXTURES / "wfs_sample.json").read_text())
    calls = []

    def transport(url: str) -> dict:
        calls.append(url)
        return payload

    rce = nd.fetch_rce_erfgoed(refresh=True, transport=transport)
    assert sorted(rce) == ["iam-archeologie", "monumenten"]
    assert rce["monumenten"]["sourceId"] == "rce-monumenten"
    assert rce["iam-archeologie"]["sourceId"] == "rce-iam-archeologie"
    assert nd.RCE_WFS in calls[0] and nd.RCE_WFS in calls[1]
    assert "typeNames=" + urllib.parse.quote(nd.RCE_MONUMENTEN_TYPENAME, safe="") in calls[0]
    assert "typeNames=" + urllib.parse.quote(nd.RCE_ARCHEOLOGIE_TYPENAME, safe="") in calls[1]

    calls.clear()
    infra = nd.fetch_infra(refresh=True, transport=transport)
    assert sorted(infra) == ["spoor", "wegen"]
    assert infra["wegen"]["sourceId"] == "rws-nwb-wegen"
    assert infra["spoor"]["sourceId"] == "prorail-spoor"
    assert nd.NWB_WFS in calls[0] and nd.PRORAIL_WFS in calls[1]


def test_fetch_dino_ondergrond_faalt_luid_zonder_gepind_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    if nd.DINO_WFS and nd.DINO_TYPENAME:
        # endpoint wel gepind: alleen de normale cache-route testen
        payload = nd.json.loads((FIXTURES / "wfs_sample.json").read_text())
        out = nd.fetch_dino_ondergrond(refresh=True, transport=lambda url: payload)
        assert out["sourceId"] == "dino-bro-ondergrond"
        return
    import pytest
    with pytest.raises(RuntimeError, match="dino"):
        nd.fetch_dino_ondergrond()


def test_load_netcongestie_leest_cache(tmp_path, monkeypatch):
    cache = tmp_path / "netcongestie" / "netcongestie.geojson"
    cache.parent.mkdir(parents=True)
    cache.write_text((FIXTURES / "netcongestie_sample.json").read_text())
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    out = nd.load_netcongestie()
    assert out["sourceId"] == "netbeheerder-netcongestie"
    assert out["records"]["features"][0]["properties"]["netgebied"] == "Utrecht-Stad"
    # retrieved afgeleid van de cache-mtime, ISO met timezone
    assert out["retrieved"].endswith("+00:00")
