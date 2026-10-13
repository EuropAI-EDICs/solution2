from fixtures import make_gemalen, make_loggers  # noqa: F401
from gwt import triggers


def test_evaluate_boundaries():
    kw = {"ingress": 0.4, "drought": 1.2}
    assert triggers.evaluate(0.30, **kw)["event"] == "WaterpumpON"
    assert triggers.evaluate(0.40, **kw)["event"] == "WaterpumpON"
    assert triggers.evaluate(0.80, **kw)["event"] == "Monitor"
    assert triggers.evaluate(1.20, **kw)["event"] == "WaterpumpOFF"
    assert triggers.evaluate(1.20, **kw)["retain"] is True
    assert triggers.evaluate(None, **kw)["event"] == "Monitor"


def test_nearest_gemaal_radius():
    gemalen = make_gemalen()
    g, dist = triggers.nearest_gemaal(95100.0, 460100.0, gemalen,
                                      radius_m=2500)
    assert g["code"] == "GAL-A" and dist == 0.0
    g, dist = triggers.nearest_gemaal(105000.0, 465000.0, gemalen,
                                      radius_m=2500)
    assert g is None  # far outside radius → gap


def test_build_commands_and_gaps():
    loggers = {lg["code"]: {"name": lg["name"], "polder": lg["polder"],
                            "x": lg["x"], "y": lg["y"]}
               for lg in make_loggers(3)}
    # a logger far outside every gemaal radius → action gap
    loggers["GWT-FAR"] = {"name": "Far logger", "polder": "Polder 9",
                          "x": 105000.0, "y": 465000.0}
    forecasts = {
        "GWT-000": {"forecast": [{"date": "2026-10-13", "depth": 0.3},
                                 {"date": "2026-10-14", "depth": 0.9}]},
        "GWT-001": {"forecast": [{"date": "2026-10-13", "depth": 1.5}]},
        "GWT-FAR": {"forecast": [{"date": "2026-10-13", "depth": 2.6}]},
    }
    rows, summary = triggers.build_commands(
        forecasts, loggers, make_gemalen(), ingress=0.4, drought=1.2,
        radius_m=2500)
    events = {(r["date"], r["loggerCode"]): r for r in rows}
    assert events[("2026-10-13", "GWT-000")]["event"] == "WaterpumpON"
    assert events[("2026-10-13", "GWT-000")]["gemaal"]["code"] == "GAL-A"
    assert events[("2026-10-13", "GWT-001")]["event"] == "WaterpumpOFF"
    # GWT-FAR sits ~10 km away → command with gap=True
    r2 = events[("2026-10-13", "GWT-FAR")]
    assert r2["event"] == "WaterpumpOFF" and r2["gap"] is True
    assert summary["totalGaps"] == 1
    assert summary["totalCommands"] == 3
