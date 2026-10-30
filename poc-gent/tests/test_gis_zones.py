"""GIS-zonecheck: adres → punt → in/niet-in per zone-laag (FR-23)."""

import json
from pathlib import Path

import pytest

from adapters import gis_zones

POC_ROOT = Path(__file__).resolve().parents[1]


def _zones():
    return gis_zones.load_zones(POC_ROOT)


def test_korenmarkt_in_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Korenmarkt 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "in"


def test_sintpietersplein_allen_in_lez():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Sint-Pietersplein 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_veldstraat_in_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Veldstraat 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "in"


def test_stationsplein_buiten_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Koningin Maria Hendrikaplein 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "niet-in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_onbekend_adres_faalt_duidelijk():
    with pytest.raises(gis_zones.AddressError):
        gis_zones.lookup_address(POC_ROOT, "Bestaatniet 1, Gent")


def test_load_layer_versies_leest_versie_per_laag():
    versies = gis_zones.load_layer_versies(POC_ROOT)
    assert set(versies) == {"gent-lez", "gent-autovrij"}
    assert all(isinstance(v, str) and v for v in versies.values())


def test_load_zones_accepteert_multipolygon(tmp_path):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"layer": "gent-lez", "versie": "test"},
         "geometry": {"type": "MultiPolygon", "coordinates": [
             [[[3.70, 51.05], [3.72, 51.05], [3.72, 51.06], [3.70, 51.06], [3.70, 51.05]]],
             [[[3.73, 51.05], [3.75, 51.05], [3.75, 51.06], [3.73, 51.06], [3.73, 51.05]]],
         ]}}]}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "gis-zones.geojson").write_text(json.dumps(fc), encoding="utf-8")
    zones = gis_zones.load_zones(tmp_path)
    assert len(zones["gent-lez"]) == 2
    assert gis_zones.zone_result(zones, "gent-lez", 3.74, 51.055) == "in"
