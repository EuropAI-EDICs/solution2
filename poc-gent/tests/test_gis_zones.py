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
    assert set(versies) == {"gent-lez", "gent-autovrij", "gent-bewonerszone",
                            "gent-parkeertariefzone", "gent-kotzone"}
    assert all(isinstance(v, str) and v for v in versies.values())


def test_nieuwe_burgerlagen_bestaan_en_dekken_adressen():
    zones = _zones()
    assert zones["gent-bewonerszone"]       # bewonerszones-gent: 20 features
    assert zones["gent-parkeertariefzone"]  # parkeertariefzones-gent: 81 features
    # gepind tegen het --check-rapport (echte lagen, F1.5-doctrine):
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Veldstraat 1, Gent")
    assert gis_zones.zone_result(zones, "gent-bewonerszone", lon, lat) == "in"
    assert gis_zones.zone_result(zones, "gent-parkeertariefzone", lon, lat) == "in"
    assert gis_zones.zone_result(zones, "gent-lez", lon, lat) == "in"


def test_burgergolden_tomas_adres_pinning():
    """Buiten-zone-adres voor het burgerpakket (Ottergemsesteenweg-Zuid,
    Gentbrugge): niet in bewoners-, tarief- of LEZ-zone."""
    zones = _zones()
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Ottergemsesteenweg-Zuid 1, Gent")
    for laag in ("gent-bewonerszone", "gent-parkeertariefzone", "gent-lez"):
        assert gis_zones.zone_result(zones, laag, lon, lat) == "niet-in", laag


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


def test_attribuut_lookup_geeft_zonenaam(tmp_path):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Ledeganck"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.70, 51.05], [3.72, 51.05], [3.72, 51.06], [3.70, 51.06], [3.70, 51.05]]]}},
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Haven"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.73, 51.05], [3.75, 51.05], [3.75, 51.06], [3.73, 51.06], [3.73, 51.05]]]}}]}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "gis-zones.geojson").write_text(json.dumps(fc), encoding="utf-8")
    zones = gis_zones.load_zones(tmp_path)
    attributen = gis_zones.load_ring_attributen(tmp_path)
    assert attributen["gent-kotzone"] == ["Ledeganck", "Haven"]
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.71, 51.055) == "Ledeganck"
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.74, 51.055) == "Haven"
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.60, 51.00) == "niet-in"


def test_apply_checks_attribuut_schrijft_naam(tmp_path):
    from unittest.mock import patch
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Ledeganck"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.70, 51.05], [3.72, 51.05], [3.72, 51.06], [3.70, 51.06], [3.70, 51.05]]]}}]}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "gis-zones.geojson").write_text(json.dumps(fc), encoding="utf-8")
    manifest = {"gisChecks": [{"id": "kotzone", "layer": "gent-kotzone", "input": "address",
                               "output": "kotzone", "attribuut": "kotzone_na"}]}
    ctx, herkomst = {"address": "Teststraat 1, Gent"}, {}
    with patch("adapters.gis_zones.lookup_address", return_value=(3.71, 51.055)):
        gis_zones.apply_checks(manifest, ctx, herkomst, tmp_path)
    assert ctx["kotzone"] == "Ledeganck"
    assert herkomst["kotzone"]["bron"].startswith("gis:gent-kotzone (v")


def test_kotzone_pinning_fixture_adressen():
    zones = gis_zones.load_zones(POC_ROOT)
    attributen = gis_zones.load_ring_attributen(POC_ROOT)
    assert len(attributen["gent-kotzone"]) == len(zones["gent-kotzone"])  # ring-dekking
    for adres in ("Veldstraat 1, Gent", "Overpoortstraat 1, Gent"):
        lon, lat = gis_zones.lookup_address(POC_ROOT, adres)
        naam = gis_zones.attribuut_result(zones, attributen, "gent-kotzone", lon, lat)
        assert naam not in ("niet-in", "in"), adres
