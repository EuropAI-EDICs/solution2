"""fetch-geo-layer proces: cache-first samenvatting, offline (geen netwerk).

agrest/ArcGIS-stappen draaien uit de gecommitte cache-twins; de NGSI-stap
gebruikt een gestubde data-platform adapter (patroon: poc/tests/test_geodata_ngsi.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
POC_ROOT = NLDT_ROOT.parent / "poc"
for _p in (str(NLDT_ROOT), str(POC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def test_fetch_geo_layer_cache_hit_uit_git_cache():
    out = execute_poc_process("fetch-geo-layer", {"source_id": "agrest-ov-gebied-windenergie"})
    s = out["summary"]
    assert s["sourceId"] == "agrest-ov-gebied-windenergie"
    assert s["featureCount"] == 44
    assert s["protocol"] is None  # ArcGIS-dialect zet geen protocol-veld
    assert s["fetchedAt"]  # provenance aanwezig uit de cache


def test_fetch_geo_layer_ngsi_mock(tmp_path, monkeypatch):
    from pipeline import geodata

    class _StubDP:
        MOCK = True

        def list_entities(self, *, entity_type, limit=100, **kwargs):
            return [
                {
                    "id": f"urn:ngsi-ld:{entity_type}:ut-001",
                    "type": entity_type,
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [5.12, 52.09]},
                    },
                    "NO2": {"type": "Property", "value": 12.5},
                }
            ]

    monkeypatch.setattr(geodata, "_load_data_platform", lambda: _StubDP())
    out = execute_poc_process(
        "fetch-geo-layer",
        {"source_id": "ngsi-ld-dpl-airquality", "cache_dir": str(tmp_path)},
    )
    s = out["summary"]
    assert s["protocol"] == "ngsi-ld"
    assert s["dataPlatformMock"] is True
    assert s["featureCount"] == 1
    assert (tmp_path / "ngsi-ld-dpl-airquality.4326.geojson").is_file()
    assert (tmp_path / "ngsi-ld-dpl-airquality.28992.geojson").is_file()


def test_fetch_geo_layer_ngsi_uri_afgewezen():
    try:
        execute_poc_process("fetch-geo-layer", {"source_id": "ngsi-ld://AirQualityObserved"})
    except ValueError as exc:
        assert "fetch-features" in str(exc)
    else:
        raise AssertionError("ngsi-ld:// URI moet worden afgewezen (gebruik fetch-features)")
