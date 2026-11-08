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


DRIFT = Path(__file__).parent / "fixtures" / "dso_kb" / "drift"


def _drift(naam: str) -> dict:
    return json.loads((DRIFT / naam).read_text(encoding="utf-8"))


def test_drift_volgorde_en_datumecho_is_geen_drift():
    uit = dso_kb.canonieke_drift(_drift("oud.json"), _drift("nieuw_gelijk.json"))
    assert uit["inhoudelijkeDrift"] == "geen"
    assert uit["categorieen"] == {}


def test_drift_gewijzigde_activiteit_wordt_precies_benoemd():
    uit = dso_kb.canonieke_drift(_drift("oud.json"), _drift("nieuw_gewijzigd.json"))
    assert uit["inhoudelijkeDrift"] == "wel"
    regels = uit["categorieen"]["regels"]
    assert regels["gewijzigd"] == ["nl.imow-gm9999.jr.002"]


def test_drift_nieuwe_en_vervallen_wids():
    nieuw = _drift("nieuw_gewijzigd.json")
    nieuw["regelteksten"].append({"wId": "gm9999_a1__chp_1__art_5.1__para_1"})
    nieuw["regelteksten"] = [r for r in nieuw["regelteksten"] if "3.1" not in r["wId"]]
    uit = dso_kb.canonieke_drift(_drift("oud.json"), nieuw)
    teksten = uit["categorieen"]["regelteksten"]
    assert teksten["erbij"] == ["gm9999_a1__chp_1__art_5.1__para_1"]
    assert teksten["weg"] == ["gm9999_a1__chp_1__art_3.1__para_1"]


def test_normaliseer_stript_datumecho_uit_hrefs():
    url = "https://example/api?geldigOp=2026-10-20&inWerkingOp=2026-10-20&beschikbaarOp=2026-10-20T14%3A17%3A05Z&id=7"
    assert (
        dso_kb._normaliseer(url)
        == "https://example/api?id=7"
    )
    # niet-URL-strings en URLs zonder datum-parameters passeren ongewijzigd
    assert dso_kb._normaliseer("geldigOp=2026-10-20") == "geldigOp=2026-10-20"
    assert dso_kb._normaliseer("https://example/api?id=7") == "https://example/api?id=7"


def test_ververs_weigert_in_offline_modus(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    with pytest.raises(dso_kb.DsoKbFout, match="NLDT_OFFLINE"):
        dso_kb.ververs("testgm", out_dir=FIX, instrumenten=INSTR, locaties=LOCS)


def _kopieer_fixtures(tmp_path: Path) -> Path:
    for bron in FIX.glob("testgm__test-loc.*.json"):
        (tmp_path / bron.name).write_text(bron.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_ververs_rapporteert_drift_via_runner(tmp_path, monkeypatch):
    monkeypatch.delenv("NLDT_OFFLINE", raising=False)  # hermetisch t.o.v. ambient env
    out = _kopieer_fixtures(tmp_path)
    # gesimuleerde oude cache: ververs leest de annotaties vóór de runner draait,
    # dus drift/oud.json moet er al liggen (nieuwe_gewijzigd volgt pas uit de runner).
    # Met gewijzigde runner-output discrimineert de test échte drift: als ververs
    # zou regresseren naar ná-de-runner lezen, zouden oud==nieuw zijn.
    (out / "testgm__test-loc.annotaties.json").write_text(
        (DRIFT / "oud.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    nieuw_gewijzigd = json.loads((DRIFT / "nieuw_gewijzigd.json").read_text(encoding="utf-8"))
    aanroepen: list[list[str]] = []

    def nep_runner(args: list[str]) -> None:
        aanroepen.append(args)
        # simulatie: compare schrijft verse annotaties (regeling jr.002 gewijzigd)
        (out / "testgm__test-loc.annotaties.json").write_text(
            json.dumps(nieuw_gewijzigd, ensure_ascii=False), encoding="utf-8"
        )

    uit = dso_kb.ververs(
        "testgm", met_tpod=False, out_dir=out, runner=nep_runner,
        instrumenten=INSTR, locaties=LOCS,
    )
    assert uit["drift"]["inhoudelijkeDrift"] == "wel"
    assert uit["drift"]["categorieen"]["regels"]["gewijzigd"] == ["nl.imow-gm9999.jr.002"]
    assert uit["tpod"]["herbouwd"] is False
    assert aanroepen and "--instruments" in aanroepen[0] and "testgm" in aanroepen[0]


def test_ververs_bouwt_tpod_herbouw_in(tmp_path, monkeypatch):
    monkeypatch.delenv("NLDT_OFFLINE", raising=False)  # hermetisch t.o.v. ambient env
    out = _kopieer_fixtures(tmp_path)
    aanroepen: list[list[str]] = []

    def nep_runner(args: list[str]) -> None:
        aanroepen.append(args)

    dso_kb.ververs(
        "testgm", met_tpod=True, out_dir=out, runner=nep_runner,
        instrumenten=INSTR, locaties=LOCS,
    )
    tpod_aanroepen = [a for a in aanroepen if "regelrecht.tpod" in a[2]]
    assert tpod_aanroepen and "--toets" in tpod_aanroepen[0] and "--geo" in tpod_aanroepen[0]
