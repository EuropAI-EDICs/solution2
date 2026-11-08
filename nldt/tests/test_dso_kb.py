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
    assert set(artikelen) == {"2.1", "3.1"}
    assert artikelen["2.1"]["regelteksten"] == 2
    assert artikelen["2.1"]["activiteiten"] == ["Bouwen"]
    assert uit["totaalArtikelen"] == 2
    assert uit["counts"]["regelteksten"] == 3


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


def test_ontbrekend_artefact_verwijst_naar_refresh(tmp_path):
    with pytest.raises(dso_kb.DsoKbFout, match="dso-kb-refresh"):
        dso_kb.lees_annotaties(
            "testgm", out_dir=tmp_path, instrumenten=INSTR, locaties=LOCS
        )
