"""NGSI-LD als geobron voor de PoC-pijplijn — offline, zonder netwerk.

geodata.fetch_layer dispatcht op ``serviceUrl: ngsi-ld://<EntityType>`` naar
de nldt data-platform adapter. Deze tests stubben die adapter (cache- en
provenance-gedrag) en gebruiken één keer de échte adapter-mock om het
import-pad (nldt op sys.path) te bewijzen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geodata  # noqa: E402

SRC_ID = "ngsi-ld-dpl-airquality"

ENTITIES = [
    {
        "id": "urn:ngsi-ld:AirQualityObserved:ut-001",
        "type": "AirQualityObserved",
        "location": {
            "type": "GeoProperty",
            "value": {"type": "Point", "coordinates": [5.1215, 52.0907]},
        },
        "NO2": {"type": "Property", "value": 12.5},
        "refDevice": {"type": "Relationship", "object": "urn:ngsi-ld:Device:ut-001"},
    },
    {  # geen locatie -> geen feature (geobron-semantiek)
        "id": "urn:ngsi-ld:AirQualityObserved:geen-geo",
        "type": "AirQualityObserved",
        "NO2": {"type": "Property", "value": 3.0},
    },
]


class _StubDataPlatform:
    """Minimale stand-in voor services.adapters.data_platform."""

    MOCK = True

    def __init__(self, entities):
        self.entities = entities
        self.calls = []

    def list_entities(self, *, entity_type, limit=100, **kwargs):
        self.calls.append({"entity_type": entity_type, "limit": limit})
        return self.entities


@pytest.fixture()
def stub_dp(monkeypatch):
    stub = _StubDataPlatform(ENTITIES)
    monkeypatch.setattr(geodata, "_load_data_platform", lambda: stub)
    return stub


def test_ngsi_entities_to_features_flattens():
    feats = geodata.ngsi_entities_to_features(ENTITIES)
    assert len(feats) == 1
    f = feats[0]
    assert f["id"] == "urn:ngsi-ld:AirQualityObserved:ut-001"
    assert f["properties"]["entityId"] == f["id"]
    assert f["properties"]["entityType"] == "AirQualityObserved"
    assert f["properties"]["NO2"] == 12.5
    # Relationship blijft bewaard als JSON-string
    assert "urn:ngsi-ld:Device:ut-001" in f["properties"]["refDevice"]
    # geometrie is de GeoProperty-waarde, niet de GeoProperty-wrapper
    # (shapely mapping levert tuples)
    assert f["geometry"]["type"] == "Point"
    assert f["geometry"]["coordinates"] == (5.1215, 52.0907)
    # locatie staat niet dubbel in de attributen
    assert "location" not in f["properties"]


def test_fetch_layer_ngsi_writes_twins_and_provenance(tmp_path, stub_dp):
    fc = geodata.fetch_layer(SRC_ID, sources=None, cache_dir=tmp_path)
    p = fc["properties"]

    assert stub_dp.calls == [
        {"entity_type": "AirQualityObserved", "limit": 100}
    ]
    assert fc["crs"]["properties"]["name"] == "EPSG:28992"
    assert p["protocol"] == "ngsi-ld"
    assert p["entityType"] == "AirQualityObserved"
    assert p["dataPlatformMock"] is True
    assert p["featureCount"] == 1

    # RD-twin: geometrie gereprojecteerd (round-trip terug naar WGS84 klopt)
    rd_x, rd_y = fc["features"][0]["geometry"]["coordinates"]
    wgs = geodata._to_wgs84(Point(rd_x, rd_y))
    assert (wgs.x, wgs.y) == pytest.approx((5.1215, 52.0907), abs=1e-6)
    assert rd_x > 100_000 and 400_000 < rd_y < 500_000  # RD-bereik Utrecht

    # beide cache-twins geschreven; schijf == geheugen (via JSON-round-trip,
    # want shapely levert tuples en schrijf/lees levert lijsten)
    fc_rd_disk = json.loads((tmp_path / f"{SRC_ID}.28992.geojson").read_text())
    fc_wgs_disk = json.loads((tmp_path / f"{SRC_ID}.4326.geojson").read_text())
    assert fc_rd_disk == json.loads(json.dumps(fc))
    assert fc_wgs_disk["features"][0]["geometry"]["coordinates"] == pytest.approx(
        [5.1215, 52.0907], abs=1e-6
    )


def test_fetch_layer_ngsi_cache_first_en_refresh(tmp_path, stub_dp):
    geodata.fetch_layer(SRC_ID, cache_dir=tmp_path)
    assert len(stub_dp.calls) == 1
    # tweede call zonder refresh: cache-hit, geen adapter-call
    geodata.fetch_layer(SRC_ID, cache_dir=tmp_path)
    assert len(stub_dp.calls) == 1
    # refresh=True: opnieuw gefetcht
    geodata.fetch_layer(SRC_ID, cache_dir=tmp_path, refresh=True)
    assert len(stub_dp.calls) == 2


def test_fetch_layer_ngsi_bbox_filter_clientzijde(tmp_path, stub_dp):
    # bbox rond Utrecht (RD) houdt de feature
    fc_in = geodata.fetch_layer(SRC_ID, bbox="120000,440000,160000,470000", cache_dir=tmp_path)
    assert fc_in["properties"]["featureCount"] == 1
    # bbox ver van Utrecht filtert alles weg
    fc_out = geodata.fetch_layer(
        SRC_ID, bbox="10000,10000,10001,10001", cache_dir=tmp_path, refresh=True
    )
    assert fc_out["properties"]["featureCount"] == 0


def test_registerentry_is_ngsi_en_fetchable(tmp_path, stub_dp):
    """De echte registry-entry (poc/data/sources.json) vloeit door de dialect-tak."""
    sources = geodata.load_sources()
    src = sources[SRC_ID]
    assert src["serviceUrl"] == "ngsi-ld://AirQualityObserved"
    assert src["protocol"] == "ngsi-ld"
    assert src["entityType"] == "AirQualityObserved"
    assert src.get("note")

    fc = geodata.fetch_layer(SRC_ID, sources=sources, cache_dir=tmp_path)
    assert fc["properties"]["title"] == src["title"]
    assert fc["properties"]["protocol"] == "ngsi-ld"


def test_fetch_layer_via_echte_adapter_mock(tmp_path, monkeypatch):
    """Bewijs het nldt-import-pad: de echte adapter-mock levert 1 entity in Utrecht."""
    dp = geodata._load_data_platform()
    # deterministisch maken ook al staan er live-vars in de omgeving
    monkeypatch.setattr(dp, "NGSI_LD_URL", "")
    monkeypatch.setattr(dp, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(dp, "MOCK", True)

    fc = geodata.fetch_layer(SRC_ID, cache_dir=tmp_path)
    assert fc["properties"]["dataPlatformMock"] is True
    assert fc["properties"]["featureCount"] == 1
    f = fc["features"][0]
    assert f["properties"]["entityId"].startswith("urn:ngsi-ld:AirQualityObserved:")
    rd_x, rd_y = f["geometry"]["coordinates"]
    assert rd_x > 100_000 and 400_000 < rd_y < 500_000
