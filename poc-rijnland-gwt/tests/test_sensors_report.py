from fixtures import (make_feature_collection, make_gemalen, make_loggers,
                      make_dates, make_rain)  # noqa: F401
from gwt import report, sensors


def test_parse_loggers_sorted_and_complete():
    fc = make_feature_collection(make_loggers(4))
    loggers = sensors.parse_loggers(fc)
    assert [lg["code"] for lg in loggers] == [
        "GWT-000", "GWT-001", "GWT-002", "GWT-003"]
    assert loggers[0]["x"] == 95000.0 and loggers[0]["y"] == 460000.0
    assert loggers[0]["polder"] == "Polder 0"


def test_parse_loggers_attribute_only_esri_features():
    """The Meetlocatie service returns NULL geometry — attributes only."""
    fc = {"type": "FeatureCollection", "features": [
        {"attributes": {"CODE": "246-105-00013_SHGT1",
                        "NAAM": "HBpb-Noord3", "LIZARDID": "l13",
                        "SOORTOBJECT": "Meetopstelling: Logger grondwater",
                        "XCOORDINAAT": 108025.59, "YCOORDINAAT": 452818.52,
                        "NAAMPOLDER": "Polder X"},
         "geometry": None}]}
    loggers = sensors.parse_loggers(fc)
    assert len(loggers) == 1
    assert loggers[0]["code"] == "246-105-00013_SHGT1"
    assert loggers[0]["x"] == 108025.59 and loggers[0]["y"] == 452818.52


def test_parse_points_gemaal():
    gemalen = sensors.parse_points({
        "type": "FeatureCollection", "features": [
            {"type": "Feature",
             "properties": {"CODE": "GAL-A", "NAAM": "Gemaal A",
                            "ONTWERPCAPACITEIT": 1.5,
                            "XCOORDINAAT": 95100.0, "YCOORDINAAT": 460100.0},
             "geometry": {"type": "Point", "coordinates": [95100.0,
                                                           460100.0]}}]})
    assert gemalen == [{"code": "GAL-A", "name": "Gemaal A", "x": 95100.0,
                        "y": 460100.0, "capaciteit": 1.5}]


def test_render_report_contains_artifacts():
    run = {
        "runId": "20261013T000000Z-gwt-twin",
        "mvpQuestion": "test question?",
        "nLoggers": 6,
        "nGemalen": 2,
        "forecastDates": ["2026-10-13"],
        "forecastSummary": {"days": [
            {"date": "2026-10-13", "meanDepth": 1.1, "Monitor": 4,
             "WaterpumpON": 1, "WaterpumpOFF": 1, "gaps": 0}]},
        "commandSummary": {"totalCommands": 2, "totalGaps": 0},
        "backtests": [{"code": "GWT-000", "available": True, "nTest": 8,
                       "mse": 0.01, "mae": 0.08,
                       "persistenceMse": 0.02,
                       "skillVsPersistence": 0.5}],
        "commands": [{"date": "2026-10-13", "event": "WaterpumpON",
                      "retain": False, "reason": "test",
                      "loggerCode": "GWT-000", "loggerName": "L",
                      "polder": "Polder 0", "depth": 0.3,
                      "gemaal": {"code": "GAL-A", "name": "Gemaal A"},
                      "distanceM": 50.0, "gap": False}],
        "hexmapName": "gwt-twin-hexmap.html",
        "seedFormula": "test formula",
    }
    html = report.render_report(run)
    assert "gwt-twin-hexmap.html" in html
    assert "WaterpumpON" in html
    assert "PROVENANCE" in html
    assert "Morales Ortega" in html
    assert "0.01" in html  # backtest MSE visible


def test_render_report_without_h3():
    run = {"runId": "x", "mvpQuestion": "q", "nLoggers": 0,
           "forecastSummary": {"days": []}, "commandSummary": {},
           "backtests": [], "commands": [], "hexmapName": None,
           "seedFormula": "f"}
    html = report.render_report(run)
    assert "Hex map skipped" in html
