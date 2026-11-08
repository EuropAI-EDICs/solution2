from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import dso_kb

FIX = Path(__file__).parent / "fixtures" / "dso_kb" / "out"
INSTR = {"testgm": {"label": "Testplan", "default_location_id": "test-loc"}}
LOCS = {"test-loc": {"id": "test-loc", "label": "Testlocatie", "instrument": "testgm"}}


def _lees_annotaties(**kwargs):
    return dso_kb.lees_annotaties(
        out_dir=FIX, instrumenten=INSTR, locaties=LOCS, **kwargs
    )


def test_onbekend_instrument_noemt_geldige_lijst():
    with pytest.raises(dso_kb.DsoKbFout, match="geldig"):
        _lees_annotaties(instrument="bestaatniet")


def test_onbekende_locatie_noemt_geldige_lijst():
    with pytest.raises(dso_kb.DsoKbFout, match="geldig"):
        _lees_annotaties(instrument="testgm", locatie="nergens")


def test_annotaties_groepeer_per_artikel():
    uit = _lees_annotaties(instrument="testgm")
    artikelen = {a["artikel"]: a for a in uit["artikelen"]}
    assert set(artikelen) == {"2.1", "3.1", "10.1"}
    assert artikelen["2.1"]["regelteksten"] == 2
    assert artikelen["2.1"]["activiteiten"] == ["Bouwen"]
    assert uit["totaalArtikelen"] == 3
    assert uit["counts"]["regelteksten"] == 4


def test_annotaties_filter_artikel():
    uit = _lees_annotaties(instrument="testgm", artikel="3.1")
    assert [a["artikel"] for a in uit["artikelen"]] == ["3.1"]


def test_annotaties_filter_onbekend_artikel_noemt_geldige():
    with pytest.raises(dso_kb.DsoKbFout, match="geldig"):
        _lees_annotaties(instrument="testgm", artikel="9.9")


def test_annotaties_detail_geeft_regelteksten():
    uit = _lees_annotaties(instrument="testgm", artikel="2.1", detail=True)
    assert {rt["wId"] for rt in uit["regelteksten"]} == {
        "gm9999_a1__chp_1__art_2.1__para_1",
        "gm9999_a1__chp_1__art_2.1__para_2",
    }


def test_annotaties_begrenzing():
    uit = _lees_annotaties(instrument="testgm", limiet=1)
    assert len(uit["artikelen"]) == 1
    assert uit["vervolg"]["maxLimiet"] == dso_kb.LIMIT_MAX


def test_annotaties_nummer_sortering():
    # "10.1" moet ná "2.1" komen (lexicografisch zou het ervoor staan)
    uit = _lees_annotaties(instrument="testgm")
    nummers = [a["artikel"] for a in uit["artikelen"]]
    assert nummers == sorted(nummers, key=dso_kb._artikel_sleutel)


def test_ontbrekend_artefact_verwijst_naar_refresh(tmp_path):
    with pytest.raises(dso_kb.DsoKbFout, match="dso-kb-refresh"):
        dso_kb.lees_annotaties(
            "testgm", out_dir=tmp_path, instrumenten=INSTR, locaties=LOCS
        )


def test_documentstructuur_vlak_en_begrensd():
    uit = dso_kb.lees_documentstructuur(
        "testgm", out_dir=FIX, instrumenten=INSTR, locaties=LOCS
    )
    assert uit["totaalComponenten"] == 3
    assert uit["componenten"][0]["diepte"] == 0
    assert uit["componenten"][1]["diepte"] == 1


def test_documentstructuur_prefix_filter():
    uit = dso_kb.lees_documentstructuur(
        "testgm", wId_prefix="gm9999_a1__chp_1__art_2", out_dir=FIX,
        instrumenten=INSTR, locaties=LOCS,
    )
    assert [c["wId"] for c in uit["componenten"]] == ["gm9999_a1__chp_1__art_2.1"]


def test_documentstructuur_limiet():
    uit = dso_kb.lees_documentstructuur(
        "testgm", limiet=2, out_dir=FIX, instrumenten=INSTR, locaties=LOCS
    )
    assert len(uit["componenten"]) == 2
    assert uit["vervolg"]["maxLimiet"] == dso_kb.LIMIT_MAX


def test_overzicht_toont_instrument_en_dekking():
    uit = dso_kb.instrumenten_overzicht(out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    (rij,) = uit["instrumenten"]
    assert rij["instrument"] == "testgm"
    assert rij["locatie"] == "test-loc"
    assert rij["dekking"]["coverageExecutable"] == 0.6667
    assert rij["annotatiesSha256"] == "abcdef0123456789"


def test_tpod_samenvatting():
    uit = dso_kb.lees_tpod("testgm", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert uit["hitCoverage"]["formalizedInHit"] == 2
    assert uit["geoFeiten"]["geselecteerdeLocatieRefs"] == ["nl.imow-gm9999.gebied.dorp"]
    assert uit["pons"]["beschikbaar"] is False


def test_toets_filter_artikel():
    uit = dso_kb.lees_toets("testgm", artikel="2.1", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert [a["artikel"] for a in uit["artikelen"]] == ["2.1"]
    assert uit["tellingen"]["getoetst"] == 1


def test_overlap_filter_en_pagina():
    uit = dso_kb.lees_overlap("testgm", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert uit["dekking"]["executableCount"] == 2
    assert len(uit["artikelen"]) == 3
    formaat = dso_kb.lees_overlap("testgm", status="unmatched", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert [a["number"] for a in formaat["artikelen"]] == ["4.1"]
    blad = dso_kb.lees_overlap("testgm", pagina=2, limiet=2, out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert [a["number"] for a in blad["artikelen"]] == ["4.1"]
    assert blad["vervolg"] is None


def test_gios_filter():
    uit = dso_kb.lijst_gios("testgm", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert uit["aantal"] == 2
    één = dso_kb.lijst_gios("testgm", identificatie="nl.imow-gm9999.gebied.dorp", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)
    assert [g["locatieIdentificatie"] for g in één["gios"]] == ["nl.imow-gm9999.gebied.dorp"]


def test_gios_onbekende_identificatie_noemt_geldige_lijst():
    with pytest.raises(dso_kb.DsoKbFout, match="geldig"):
        dso_kb.lijst_gios(
            "testgm", identificatie="nl.imow-gm9999.gebied.nergens",
            out_dir=FIX, instrumenten=INSTR, locaties=LOCS,
        )


def test_punt_in_gio_zonder_pakket_geeft_fout(tmp_path):
    with pytest.raises(dso_kb.DsoKbFout, match="pakket"):
        dso_kb.punt_in_gio("testgm", 1.0, 2.0, out_dir=tmp_path, instrumenten=INSTR, locaties=LOCS)
