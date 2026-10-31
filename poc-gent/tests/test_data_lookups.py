"""dataChecks (F1-burger): dataset-lookups naast GIS-zonechecks, met
fallback/escalate-beleid en herkomstlabels (DATA-01)."""

import json
import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POC_ROOT))

from adapters import data_lookups  # noqa: E402

CHECK = {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
         "outputs": ["afvalRest", "afvalPmd"], "unknownPolicy": "fallback"}


def _cache(tmp_path: Path, straten: dict | None = None) -> None:
    (tmp_path / "fixtures" / "source").mkdir(parents=True, exist_ok=True)
    document = {"dataset": "ivago-ophaalkalender", "versie": "test (2026-2027)",
                "straten": straten if straten is not None else
                {"veldstraat": {"afvalRest": {"dag": "woensdag", "aantal": 52,
                                              "dagen": ["woensdag"], "eerste": "2026-10-07"},
                                 "afvalPmd": {"dag": "dinsdag", "aantal": 52,
                                              "dagen": ["dinsdag"], "eerste": "2026-10-06"}}}}
    (tmp_path / "fixtures" / "source" / "afvalkalender.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8")


def test_bekende_straat_vult_outputs_met_herkomst(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {"address": "Veldstraat 1, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert ctx["afvalPmd"] == "dinsdag"
    assert ctx["afvalRest"] == "woensdag"
    assert herkomst["afvalPmd"] == {"label": "afgeleid",
                                    "bron": "dataset:ivago-ophaalkalender (test (2026-2027))"}


def test_onbekende_straat_fallback(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {"address": "Onbekendelaan 9, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert ctx["afvalRest"] == "onbekend"
    assert "straat niet in cache" in herkomst["afvalRest"]["bron"]
    assert herkomst["afvalRest"]["label"] == "afgeleid"


def test_onbekende_straat_escalate_waarde(tmp_path):
    _cache(tmp_path)
    check = {**CHECK, "unknownPolicy": "escalate"}
    ctx, herkomst = {"address": "Onbekendelaan 9, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [check]}, ctx, herkomst, tmp_path)
    assert ctx["afvalPmd"] == "onbekend-straat"


def test_zonder_input_slot_geen_uitvoer(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert "afvalRest" not in ctx and "afvalPmd" not in ctx


def test_correctie_suffix_in_herkomst(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {"address": "Veldstraat 1, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path,
                              suffix=", na correctie")
    assert herkomst["afvalPmd"]["bron"].endswith("), na correctie)")
