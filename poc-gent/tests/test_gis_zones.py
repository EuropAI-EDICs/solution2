"""GIS-zonecheck: adres → punt → in/niet-in per zone-laag (FR-23)."""

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


def test_sleepstraat_allen_in_lez():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Sleepstraat 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_sintpietersplein_buiten_beide_zones():
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Sint-Pietersplein 1, Gent")
    assert gis_zones.zone_result(_zones(), "gent-lez", lon, lat) == "niet-in"
    assert gis_zones.zone_result(_zones(), "gent-autovrij", lon, lat) == "niet-in"


def test_onbekend_adres_faalt_duidelijk():
    with pytest.raises(gis_zones.AddressError):
        gis_zones.lookup_address(POC_ROOT, "Bestaatniet 1, Gent")
