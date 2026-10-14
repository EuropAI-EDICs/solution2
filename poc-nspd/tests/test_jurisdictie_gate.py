import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.jurisdictie_gate import JurisdictieError, run_v2b  # noqa: E402

_KAART = {"id": "NC-WIND-01", "jurisdictie": "nl", "evidenceId": "EVW-01",
          "theme": "energy:wind", "verified": True}
_KAART_BE = {"id": "NC-WIND-02", "jurisdictie": "be", "evidenceId": "EVW-02",
             "theme": "energy:wind", "verified": True}
_FR = {"id": "FR-WIND-01", "normCardId": "NC-WIND-01", "jurisdictie": "nl"}
_REGISTRY = {"sources": [
    {"id": "cvdr709135-ov-zeeland", "jurisdictie": "nl"},
    {"id": "be-rup-corpus", "jurisdictie": "be"},
]}
_REG_DOCS = {"S01": {"jurisdictie": "nl"}, "S02": {"jurisdictie": "be"}}
_KAART_S02 = {"id": "NC-S02", "jurisdictie": "nl", "evidenceId": "EV-01",
              "theme": "energy:wind", "verified": True,
              "source": {"docId": "S02"}}


def test_v2b_pass_bij_schone_set():
    out = run_v2b(normcards=[_KAART], formal_rules=[_FR],
                  sources_registry=_REGISTRY, jurisdictie="nl")
    assert out["status"] == "pass"


def test_v2b_fail_bij_be_kaart_in_nl_run():
    out = run_v2b(normcards=[_KAART_BE], formal_rules=[],
                  sources_registry=_REGISTRY, jurisdictie="nl")
    assert out["status"] == "fail"
    assert any("NC-WIND-02" in c["detail"] for c in out["checks"])
    with pytest.raises(JurisdictieError):
        run_v2b(normcards=[_KAART_BE], formal_rules=[], sources_registry=_REGISTRY,
                jurisdictie="nl", strict=True)


def test_v2b_bron_fail_bij_be_bron_in_nl_run():
    out = run_v2b(normcards=[_KAART_S02], formal_rules=[],
                  sources_registry=_REGISTRY, jurisdictie="nl",
                  document_registry=_REG_DOCS)
    assert out["status"] == "fail"
    bron = [c for c in out["checks"] if c["id"] == "V2B-BRON"]
    assert bron and "NC-S02" in bron[0]["detail"] and "S02" in bron[0]["detail"]
    assert "be" in bron[0]["detail"]


def test_v2b_bron_overgeslagen_zonder_documentregister():
    out = run_v2b(normcards=[_KAART_S02], formal_rules=[],
                  sources_registry=_REGISTRY, jurisdictie="nl")
    assert out["status"] == "pass"
    assert not any(c["id"] == "V2B-BRON" for c in out["checks"])
