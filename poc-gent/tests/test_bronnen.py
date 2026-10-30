"""Bronnenlaag F3: VKBO-normalisatie, GIPOD-mockfallback en meta-volledigheid."""

import json
from pathlib import Path

import fetch_sources

POC_ROOT = Path(__file__).resolve().parents[1]


def test_vkbo_normalisatie_werkt_op_waren():
    features = [{"type": "Feature", "properties": {
        "Commerciele_naam": "BVBA Testbouw", "Afgekorte_naam": "Testbouw",
        "AR_straat": "Korenmarkt", "AR_huisnr": "1", "AR_postcode": "9000",
        "Datum_inschrijving": "2015-03-02"}}]
    rijen = fetch_sources.normaliseer_vkbo(features)
    assert rijen == [{"naam": "BVBA Testbouw", "straat": "Korenmarkt",
                      "huisnr": "1", "postcode": "9000", "inschrijving": "2015-03-02"}]


def test_gipod_mockfallback_levert_testdata_en_mode():
    pad = POC_ROOT / "fixtures" / "source" / "gipod-gent.json"
    data = json.loads(pad.read_text(encoding="utf-8"))
    assert data["mode"] == "mock"
    assert data["innames"], "mock-innames mogen niet leeg zijn"
    for inn in data["innames"]:
        assert {"id", "straat", "type", "van", "tot"} <= set(inn)


def test_best_address_productiepad_geregistreerd():
    assert "bestinabox" in fetch_sources.BEST_ADDRESS_PAD.lower()
