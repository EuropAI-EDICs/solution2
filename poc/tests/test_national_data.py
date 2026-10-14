"""National-data fetchers — offline, via fixtures en fake transport.

Live-pinning (plan-2 task 4, stap 1): de CBS OData-tabellen voor het
100m-grid bestaan niet meer; de opvolger is de PDOK OGC API
'vierkantstatistieken100m' (collectie vierkant100) met celkolom
``crs28992res100m`` ("E1300N4400" = RD-hoek 130000/440000, cel 100m).
Landgebruik is via PDOK 'existinglanduse' gepind (zie module-docstring).
"""

from __future__ import annotations

import sys
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
