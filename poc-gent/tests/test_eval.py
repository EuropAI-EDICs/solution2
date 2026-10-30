"""Golden-set: routing-uitkomsten per scenario + determinisme (KPI-01/02/04-basis)."""

import eval as eval_mod


def test_golden_set_is_groen():
    assert eval_mod.evaluate("gent-mobiliteit-ondernemer") == 0
