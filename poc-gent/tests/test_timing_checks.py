"""timingChecks (GT-EVT-01): aanlooptijd-klasse t.o.v. een vaste referentie —
deterministisch, mét herkomst; verleden en onleesbare datums krijgen eigen
waarden zodat beslistabellen erop kunnen matchen."""
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters import timing_checks  # noqa: E402

CHECK = {"id": "aanlooptijd", "input": "datum", "output": "aanlooptijd", "referentie": "2026-11-02",
         "klassen": [{"naam": "te-laat", "maxDagen": 30},
                     {"naam": "kort-op-tijd", "maxDagen": 90},
                     {"naam": "ruim-op-tijd"}]}


def test_klassen_volgen_de_drempels():
    assert timing_checks.klasse_voor(10, CHECK["klassen"]) == "te-laat"
    assert timing_checks.klasse_voor(30, CHECK["klassen"]) == "te-laat"
    assert timing_checks.klasse_voor(31, CHECK["klassen"]) == "kort-op-tijd"
    assert timing_checks.klasse_voor(90, CHECK["klassen"]) == "kort-op-tijd"
    assert timing_checks.klasse_voor(300, CHECK["klassen"]) == "ruim-op-tijd"


def test_apply_checks_schrijft_klasse_met_herkomst():
    ctx, herkomst = {"datum": "2027-09-11"}, {}
    timing_checks.apply_checks({"timingChecks": [CHECK]}, ctx, herkomst, None)
    assert ctx["aanlooptijd"] == "ruim-op-tijd"
    assert herkomst["aanlooptijd"]["bron"] == "timing:aanlooptijd (referentie 2026-11-02)"


def test_verleden_en_onbekende_datum():
    ctx = {"datum": "20/11/2026"}
    timing_checks.apply_checks({"timingChecks": [CHECK]}, ctx, {}, None)
    assert ctx["aanlooptijd"] == "te-laat"          # 18 dagen, dd/mm/jjjj leest ook
    ctx = {"datum": "2025-01-01"}
    timing_checks.apply_checks({"timingChecks": [CHECK]}, ctx, {}, None)
    assert ctx["aanlooptijd"] == "verleden"
    ctx = {"datum": "ooit"}
    timing_checks.apply_checks({"timingChecks": [CHECK]}, ctx, {}, None)
    assert ctx["aanlooptijd"] == "onbekende-datum"


def test_zonder_input_geen_uitvoer():
    ctx = {}
    timing_checks.apply_checks({"timingChecks": [CHECK]}, ctx, {}, None)
    assert "aanlooptijd" not in ctx
