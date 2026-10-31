"""Golden-set: routing-uitkomsten per scenario + determinisme (KPI-01/02/04-basis)."""

import json

import eval as eval_mod


def test_golden_set_is_groen():
    assert eval_mod.evaluate("gent-mobiliteit-ondernemer") == 0


def test_rapport_wordt_geschreven_met_go(tmp_path):
    rapport_pad = tmp_path / "kpi" / "rapport.json"
    assert eval_mod.evaluate("gent-mobiliteit-ondernemer", str(rapport_pad)) == 0
    rapport = json.loads(rapport_pad.read_text(encoding="utf-8"))
    assert rapport["goNoGo"] == "GO"
    assert rapport["belemmeringen"] == []
    assert set(rapport["kpis"]) == {"KPI-01", "KPI-02", "KPI-03", "KPI-04", "KPI-06", "H-events"}
    assert all(info["ok"] for info in rapport["kpis"].values())
