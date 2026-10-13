import math

from fixtures import make_dates, make_rain  # noqa: F401
from gwt import predict


def _spiky_rains(n: int) -> list:
    """Isolated 20 mm spikes — rain3 jumps, persistence lags a day."""
    return [20.0 if (i % 7 == 3) else 0.0 for i in range(n)]


def _synthetic_series(dates, rains, *, rain_response=0.04, base=1.0):
    """Depth with a strong, learnable same-day rain response + tiny noise."""
    depths = []
    rain3 = [sum(rains[max(0, i - 2):i + 1]) for i in range(len(rains))]
    for i, d in enumerate(dates):
        depth = base - rain_response * rain3[i] \
            + 0.005 * math.sin(i)
        depths.append(round(depth, 4))
    return depths


def test_tree_beats_persistence_on_rain_response():
    dates = make_dates(80)
    rains = _spiky_rains(len(dates))
    depths = _synthetic_series(dates, rains)
    bt = predict.backtest_logger(dates, depths, rains)
    assert bt["available"]
    assert bt["mse"] < bt["persistenceMse"]
    assert bt["skillVsPersistence"] > 0


def test_forecast_length_and_dates():
    dates = make_dates(80)
    rains = [make_rain(dates)[d] for d in dates]
    depths = _synthetic_series(dates, rains)
    fc_dates = ["2026-10-13", "2026-10-14", "2026-10-15"]
    fc = predict.forecast_logger(dates, depths, rains, fc_dates,
                                 [1.0, 0.0, 3.0])
    assert fc["method"] == "cart"
    assert [s["date"] for s in fc["forecast"]] == fc_dates
    assert all(s["depth"] is not None for s in fc["forecast"])


def test_scenario_cloudburst_raises_table():
    """More rain on day +1 → shallower (lower) predicted depth than base."""
    dates = make_dates(80)
    rains = [make_rain(dates)[d] for d in dates]
    depths = _synthetic_series(dates, rains)
    fc_dates = ["2026-10-13"]
    base = predict.forecast_logger(dates, depths, rains, fc_dates, [1.0])
    storm = predict.forecast_logger(dates, depths, rains, fc_dates, [1.0],
                                    scenario_mm=30.0)
    assert storm["forecast"][0]["depth"] < base["forecast"][0]["depth"]


def test_persistence_fallback_short_series():
    dates = make_dates(20)
    rains = [make_rain(dates)[d] for d in dates]
    depths = _synthetic_series(dates, rains)
    fc = predict.forecast_logger(dates, depths, rains, ["2026-10-13"], [2.0])
    assert fc["method"] == "persistence"
    assert abs(fc["forecast"][0]["depth"] - depths[-1]) < 1e-3


def test_backtest_too_short_is_flagged():
    dates = make_dates(12)
    rains = [make_rain(dates)[d] for d in dates]
    depths = _synthetic_series(dates, rains)
    bt = predict.backtest_logger(dates, depths, rains)
    assert bt["available"] is False
