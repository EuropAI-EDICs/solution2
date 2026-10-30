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


def test_vkbo_witruimte_commerciele_naam_valt_terug_op_afgekorte():
    features = [{"type": "Feature", "properties": {
        "Commerciele_naam": "  ", "Afgekorte_naam": "Testbouw",
        "AR_straat": "Korenmarkt", "AR_huisnr": "1", "AR_postcode": "9000",
        "Datum_inschrijving": "2015-03-02"}}]
    rijen = fetch_sources.normaliseer_vkbo(features)
    assert rijen[0]["naam"] == "Testbouw"


def test_vkbo_witruimte_busnr_wordt_niet_opgenomen():
    features = [{"type": "Feature", "properties": {
        "Commerciele_naam": "BVBA Testbouw", "AR_straat": "Korenmarkt",
        "AR_huisnr": "3", "AR_busnr": "   ", "AR_postcode": "9040",
        "Datum_inschrijving": "2003-01-18"}}]
    rijen = fetch_sources.normaliseer_vkbo(features)
    assert rijen[0]["huisnr"] == "3"


def test_gipod_mock_wordt_nooit_herschreven(tmp_path, monkeypatch):
    (tmp_path / "source").mkdir()
    import shutil
    mock = POC_ROOT / "fixtures" / "source" / "gipod-gent.json"
    doel = tmp_path / "source" / "gipod-gent.json"
    shutil.copy(mock, doel)
    foraf = doel.read_text(encoding="utf-8")
    monkeypatch.setattr(fetch_sources, "SOURCE_DIR", tmp_path / "source")
    monkeypatch.setattr(fetch_sources, "GIPOD_SWAGGER", "https://onbereikbaar.voor.test/swagger.json")
    uitslag = fetch_sources.haal_gipod(POC_ROOT)
    assert uitslag["mode"] == "mock"
    assert doel.read_text(encoding="utf-8") == foraf
