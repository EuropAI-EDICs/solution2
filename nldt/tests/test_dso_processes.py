from __future__ import annotations

from pathlib import Path

import pytest

from services import dso_kb
from services.process_adapter.handlers import (
    PROCESS_DEFINITIONS,
    describe_process,
    execute_local,
)

FIX = Path(__file__).parent / "fixtures" / "dso_kb" / "out"
INSTR = {"testgm": {"label": "Testplan", "default_location_id": "test-loc"}}
LOCS = {"test-loc": {"id": "test-loc", "label": "Testlocatie", "instrument": "testgm"}}

VERWACHTE_PROCESSEN = {
    "dso-kb-overview",
    "dso-kb-annotations",
    "dso-kb-document-structure",
    "dso-kb-tpod",
    "dso-kb-toets",
    "dso-kb-overlap",
    "dso-kb-gios",
    "dso-kb-point-in-gio",
    "dso-kb-refresh",
}


def test_negen_processen_geregistreerd():
    assert VERWACHTE_PROCESSEN <= set(PROCESS_DEFINITIONS)
    for pid in VERWACHTE_PROCESSEN:
        assert describe_process(pid)["id"] == pid


def test_refresh_gemarkeerd_als_side_effect():
    assert describe_process("dso-kb-refresh").get("sideEffect") is True
    for pid in VERWACHTE_PROCESSEN - {"dso-kb-refresh"}:
        assert describe_process(pid).get("sideEffect") in (None, False)


def test_leesproces_lokaal_uitgevoerd(monkeypatch):
    monkeypatch.setattr(dso_kb, "DEFAULT_OUT", FIX)
    # Brief-afwijking: testgm bestaat niet in dso_overlap/instruments.py; via de
    # lazy-loader-seam injecteren we het testpaar (zelfde INSTR/LOCS als de brief).
    monkeypatch.setattr(dso_kb, "_laat_instrumenten", lambda: (INSTR, LOCS))
    result = execute_local("dso-kb-annotations", {"instrument": "testgm"})
    outputs = result["outputs"] if "outputs" in result else result
    assert "artikelen" in str(outputs)


def test_leesproces_fout_wordt_resultaat_niet_exceptie(monkeypatch):
    monkeypatch.setattr(dso_kb, "DEFAULT_OUT", FIX)
    result = execute_local("dso-kb-annotations", {"instrument": "bestaatniet"})
    outputs = result["outputs"] if "outputs" in result else result
    assert "onbekend instrument" in str(outputs)


def test_refresh_weigert_offline(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    result = execute_local("dso-kb-refresh", {"instrument": "testgm"})
    outputs = result["outputs"] if "outputs" in result else result
    assert "NLDT_OFFLINE" in str(outputs)


@pytest.mark.parametrize(
    "process_id, inputs",
    [
        ("dso-kb-overview", {}),
        ("dso-kb-annotations", {"instrument": "testgm"}),
        ("dso-kb-document-structure", {"instrument": "testgm", "wIdPrefix": "gm9999_a1__chp_1__art_2"}),
        ("dso-kb-tpod", {"instrument": "testgm"}),
        ("dso-kb-toets", {"instrument": "testgm"}),
        ("dso-kb-overlap", {"instrument": "testgm"}),
        ("dso-kb-gios", {"instrument": "testgm"}),
        ("dso-kb-point-in-gio", {"instrument": "testgm", "x": 1.0, "y": 2.0}),
        ("dso-kb-refresh", {"instrument": "testgm"}),
    ],
)
def test_alle_negen_processen_leveren_resultaat_of_fout(process_id, inputs, monkeypatch):
    """Elke executor draait tegen de fixtures en levert resultaat óf een fout-resultaat — nooit een crash."""
    monkeypatch.setattr(dso_kb, "DEFAULT_OUT", FIX)
    monkeypatch.setattr(dso_kb, "_laat_instrumenten", lambda: (INSTR, LOCS))
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    result = execute_local(process_id, dict(inputs))
    outputs = result.get("outputs", result)
    tekst = str(outputs)
    assert "result" in tekst or "error" in tekst, tekst[:300]
