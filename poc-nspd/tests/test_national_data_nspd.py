import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import national_data as nd  # noqa: E402
from bbox import nspd_bbox_l72  # noqa: E402


def test_fetch_geopunt_wfs_bouwt_l72_url_en_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    calls = []

    def transport(url: str) -> dict:
        calls.append(url)
        return {"type": "FeatureCollection", "features": []}

    out = nd.fetch_geopunt_wfs(
        service_url="https://geo.api.vlaanderen.be/GRB/wfs",
        type_name="GRB_ADP",
        bbox_l72=nspd_bbox_l72(),
        cache_name="test-grb.json",
        source_id="geopunt-grb-wfs",
        transport=transport,
    )
    assert out["sourceId"] == "geopunt-grb-wfs"
    assert "retrieved" in out
    url = calls[0]
    assert "version=2.0.0" in url and "typeNames=GRB_ADP" in url
    assert "EPSG::31370" in urllib.parse.unquote(url)
    # tweede aanroep komt uit de cache (geen tweede call)
    nd.fetch_geopunt_wfs(
        service_url="https://geo.api.vlaanderen.be/GRB/wfs",
        type_name="GRB_ADP",
        bbox_l72=nspd_bbox_l72(),
        cache_name="test-grb.json",
        source_id="geopunt-grb-wfs",
        transport=transport,
    )
    assert len(calls) == 1


def test_fetch_geopunt_wfs_niet_gepind_faalt_luid(tmp_path, monkeypatch):
    monkeypatch.setattr(nd, "CACHE", tmp_path)
    try:
        nd.fetch_geopunt_wfs(
            service_url="", type_name="", bbox_l72=(0, 0, 1, 1),
            cache_name="x.json", source_id="mercator-ruimtelijk-beleid",
        )
    except ValueError as exc:
        assert "niet gepind" in str(exc)
    else:
        raise AssertionError("ongeplinde WFS moet luid falen")
