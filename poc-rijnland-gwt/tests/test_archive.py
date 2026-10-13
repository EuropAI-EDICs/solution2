import json

from fixtures import make_dates, make_loggers, make_rain  # noqa: F401
from gwt import archive


def test_seed_deterministic(tmp_path):
    dates = make_dates(40)
    rain = make_rain(dates)
    loggers = make_loggers(4)
    a = archive.load_or_seed(tmp_path / "a.json", loggers, rain, dates)
    b = archive.load_or_seed(tmp_path / "b.json", loggers, rain, dates)
    assert a["loggers"].keys() == b["loggers"].keys()
    for code in a["loggers"]:
        assert a["loggers"][code]["days"] == b["loggers"][code]["days"]
    assert a["syntheticSeed"] is True
    assert a["seedReason"]


def test_seed_bounds_and_formula(tmp_path):
    dates = make_dates(60)
    rain = make_rain(dates)
    doc = archive.load_or_seed(tmp_path / "g.json", make_loggers(6), rain,
                               dates)
    for entry in doc["loggers"].values():
        for day in entry["days"].values():
            assert archive.DEPTH_MIN <= day["depth"] <= archive.DEPTH_MAX


def test_rain_raises_water_table(tmp_path):
    """Wet spell → shallower (lower) depths during it than the dry tail."""
    dates = make_dates(60)
    rain = make_rain(dates)
    lg = make_loggers(1)
    doc = archive.load_or_seed(tmp_path / "g.json", lg, rain, dates)
    days = doc["loggers"]["GWT-000"]["days"]
    rain3 = {d: sum(rain[w] for w in dates[max(0, i - 2):i + 1])
             for i, d in enumerate(dates)}
    shallow = min(days[d]["depth"] for d in dates if rain3[d] > 0)
    deep = max(days[d]["depth"] for d in dates if rain3[d] == 0)
    assert shallow < deep


def test_incremental_days_kept(tmp_path):
    dates = make_dates(40)
    rain = make_rain(dates)
    path = tmp_path / "g.json"
    archive.load_or_seed(path, make_loggers(2), rain, dates)
    first = json.loads(path.read_text())
    more = dates + [max(dates)[:8] + "13"]  # extend one day
    archive.load_or_seed(path, make_loggers(2), rain, more)
    second = json.loads(path.read_text())
    old = first["loggers"]["GWT-000"]["days"]
    new = second["loggers"]["GWT-000"]["days"]
    for d, v in old.items():
        assert new[d] == v


def test_merge_real_overwrites_seed(tmp_path):
    dates = make_dates(30)
    rain = make_rain(dates)
    doc = archive.load_or_seed(tmp_path / "g.json", make_loggers(2), rain,
                               dates)
    series = {"GWT-000": {"measured": True,
                          "days": {dates[0]: {"depth": 1.234}}}}
    archive.merge_real(doc, series)
    assert doc["loggers"]["GWT-000"]["days"][dates[0]]["depth"] == 1.234
    assert doc["loggers"]["GWT-000"]["measured"] is True
