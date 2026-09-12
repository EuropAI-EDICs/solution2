"""Offline tests for PoC-3 peil-conflict H3 overlay."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
POC_ROOT = ROOT.parent / "poc"
for p in (str(ROOT), str(ROOT / "scripts"), str(POC_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from rijnland import peil_conflict  # noqa: E402
from shapely.geometry import Point, box, mapping  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "fixtures"


def _fc(*geoms):
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": mapping(g)}
            for g in geoms
        ],
    }


class TestPeilConflict(unittest.TestCase):

    def test_union_and_payload(self):
        fc = _fc(box(90000, 460000, 91000, 461000))
        u = peil_conflict.union_layer_rd(fc)
        self.assertAlmostEqual(u.area, 1e6, delta=1.0)
        payload = peil_conflict.to_wgs84_payload(u)
        self.assertEqual(payload["type"], "Polygon")
        # Leiden area roughly
        ring = payload["coordinates"][0]
        lngs = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        self.assertTrue(4.4 < min(lngs) < 5.0)
        self.assertTrue(52.0 < min(lats) < 52.4)

    def test_attach_peil_h3_overlay_weights(self):
        peil = _fc(box(90000, 460000, 92000, 462000))
        afwijk = _fc(box(90000, 460000, 91000, 461000))  # 25% of peil
        calls = {"n": 0}

        def call(process_id, inputs):
            self.assertEqual(process_id, "h3-polygon-to-cells")
            calls["n"] += 1
            if inputs.get("restrictCells") is not None:
                return {"coverage": {
                    "resolution": inputs["resolution"],
                    "cellCount": len(inputs["restrictCells"]),
                    "cells": [
                        {"cell": c, "coverageFraction": 0.25, "cellAreaM2": 740000.0}
                        for c in inputs["restrictCells"]
                    ],
                    "crs": "cells-EPSG:4326-areas-EPSG:28992",
                    "h3Version": "test",
                }}
            return {"coverage": {
                "resolution": inputs["resolution"], "cellCount": 2,
                "cells": [
                    {"cell": "c1", "coverageFraction": 0.8, "cellAreaM2": 740000.0},
                    {"cell": "c2", "coverageFraction": 0.8, "cellAreaM2": 740000.0},
                ],
                "crs": "cells-EPSG:4326-areas-EPSG:28992",
                "h3Version": "test",
            }}

        report = peil_conflict.empty_report(run_id="T-1")
        art = peil_conflict.attach_peil_h3_overlay(
            report, peil_fc_rd=peil, afwijk_fc_rd=afwijk, call=call)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(report["h3Overlay"]["cells"], 2)
        self.assertEqual(report["h3Overlay"]["conflictCells"], 2)
        self.assertEqual(report["h3Overlay"]["weightedConflictSharePct"], 25.0)
        self.assertEqual(art["cells"][0]["conflictFraction"], 0.25)
        self.assertIn("peilgebiedAreaKm2", report["peil"])

    def test_attach_degrades_without_client(self):
        report = peil_conflict.empty_report(run_id="T-2")
        self.assertIsNone(peil_conflict.attach_peil_h3_overlay(
            report, peil_fc_rd=_fc(box(0, 0, 1, 1)),
            afwijk_fc_rd=_fc(box(0, 0, 1, 1))))
        self.assertEqual(report["degradations"][0]["kind"], "h3-unavailable")

    def test_markdown_renders_sections(self):
        report = peil_conflict.empty_report(run_id="T-3")
        report["peil"] = {
            "peilgebiedAreaKm2": 10.0,
            "peilafwijkingAreaKm2": 2.0,
            "overlapAreaKm2": 1.5,
            "overlapShareOfPeilPct": 15.0,
        }
        report["h3Overlay"] = {
            "zoneId": "peilgebied-vigerend", "resolution": 8,
            "cells": 10, "conflictCells": 4,
            "weightedConflictSharePct": 12.5,
            "artifactFile": "h3-peil-conflict.json",
        }
        md = peil_conflict.conflict_markdown(report)
        self.assertIn("Peil-conflict Rijnland", md)
        self.assertIn("H3 overlay", md)
        self.assertIn("4 of 10 cells", md)


class TestOfflineEnv(unittest.TestCase):
    def setUp(self):
        self._p = mock.patch.dict(os.environ, {"POC_H3_OFFLINE": "1"})
        self._p.start()
        self.addCleanup(self._p.stop)

    def test_sources_registry_loads(self):
        from pipeline import geodata

        sources = geodata.load_sources(ROOT / "data" / "sources.json")
        self.assertIn("rijnland-peilgebied-vigerend", sources)
        self.assertIn("rijnland-peilafwijking-praktijk", sources)
        self.assertTrue(sources["rijnland-peilgebied-vigerend"]["geojsonFormatSupported"])


if __name__ == "__main__":
    unittest.main()


class TestKrwMonitoring(unittest.TestCase):

    def test_points_fc_to_wgs84(self):
        from rijnland import krw_quality

        fc = _fc(Point(95000, 462000))
        out = krw_quality.points_fc_to_wgs84(fc)
        lng, lat = out["features"][0]["geometry"]["coordinates"]
        self.assertTrue(4.3 < lng < 4.6)   # Leiden area
        self.assertTrue(52.0 < lat < 52.3)

    def test_attach_krw_monitoring_blind_spots(self):
        from rijnland import krw_quality

        peil_cells = [
            {"cell": "c1", "inZoneFraction": 0.9, "conflictFraction": 0.8,
             "cellAreaM2": 740000.0},
            {"cell": "c2", "inZoneFraction": 0.9, "conflictFraction": 0.5,
             "cellAreaM2": 740000.0},
            {"cell": "c3", "inZoneFraction": 0.9, "conflictFraction": 0.0,
             "cellAreaM2": 740000.0},
        ]

        def call(process_id, inputs):
            if process_id == "h3-spatial-join-points":
                self.assertEqual(sorted(inputs["cells"]), ["c1", "c2", "c3"])
                return {"join": {"pointCount": 4, "cellCount": 3,
                                 "resolution": inputs["resolution"],
                                 "perPoint": [],
                                 "perCell": [{"cell": "c1", "count": 3},
                                             {"cell": "c3", "count": 1}]}}
            if process_id == "h3-grid-disk":
                # c2 is unmonitored; its neighbour c1 IS monitored
                self.assertEqual(inputs["cells"], ["c2"])
                return {"disk": {"ring": 1,
                                 "disks": {"c2": ["c1", "c2", "c9"]}}}
            assert process_id == "h3-morans-i"
            self.assertEqual(inputs["values"], {"c1": 3, "c2": 0, "c3": 1})
            return {"statistics": {"n": 3, "permutations": 199,
                                   "moransI": None, "expectedI": None,
                                   "pValue": None, "notes": ["too few cells"]}}

        report = {"degradations": [], "notes": []}
        art = krw_quality.attach_krw_monitoring(
            report, peil_cells=peil_cells, meet_fc_rd=_fc(), call=call)
        by = {r["cell"]: r for r in art["rows"]}
        # c1: monitored conflict -> not blind
        self.assertFalse(by["c1"]["blindSpot"])
        self.assertEqual(by["c1"]["monitoringCount"], 3)
        # c2: conflict, 0 in cell, but monitored neighbour -> covered
        self.assertFalse(by["c2"]["blindSpot"])
        self.assertTrue(by["c2"]["monitoringNearby"])
        # c3: unmonitored but no conflict -> not blind
        self.assertFalse(by["c3"]["blindSpot"])
        k = report["krw"]
        self.assertEqual(k["meetpuntenRoutine"], 4)
        self.assertEqual(k["cellsWithMonitoring"], 2)
        self.assertEqual(k["blindSpotCells"], 0)
        self.assertEqual(k["conflictCells"], 2)

    def test_attach_krw_monitoring_true_blind_spot(self):
        from rijnland import krw_quality

        peil_cells = [{"cell": "c1", "inZoneFraction": 0.9,
                       "conflictFraction": 0.7, "cellAreaM2": 740000.0}]

        def call(process_id, inputs):
            if process_id == "h3-spatial-join-points":
                return {"join": {"pointCount": 0, "cellCount": 1,
                                 "resolution": 8, "perPoint": [],
                                 "perCell": []}}
            if process_id == "h3-grid-disk":
                return {"disk": {"ring": 1, "disks": {"c1": ["c1", "c8"]}}}
            assert process_id == "h3-morans-i"
            return {"statistics": {"moransI": 0.0, "pValue": 1.0}}

        report = {"degradations": []}
        art = krw_quality.attach_krw_monitoring(
            report, peil_cells=peil_cells, meet_fc_rd=_fc(), call=call)
        row = art["rows"][0]
        self.assertTrue(row["blindSpot"])
        self.assertEqual(row["blindSpotScore"], 0.7)
        self.assertFalse(row["monitoringNearby"])
        self.assertEqual(report["krw"]["blindSpotCells"], 1)
        self.assertEqual(report["krw"]["blindSpotShareOfConflictPct"], 100.0)

    def test_attach_krw_monitoring_degrades_without_client(self):
        from rijnland import krw_quality

        report = {"degradations": []}
        self.assertIsNone(krw_quality.attach_krw_monitoring(
            report, peil_cells=[], meet_fc_rd=_fc()))
        self.assertEqual(report["degradations"][0]["kind"], "krw-unavailable")


class TestWaterQuality(unittest.TestCase):

    FIXTURE = {
        "year": 2025,
        "source": "test",
        "locations": {
            "L1": {"x": 95000.0, "y": 462000.0, "params": {
                "CONCTTE|chloride|mg/l": {"n": 12, "median": 100.0,
                                          "min": 50.0, "max": 150.0}}},
            "L2": {"x": 95100.0, "y": 462100.0, "params": {
                "CONCTTE|chloride|mg/l": {"n": 12, "median": 200.0,
                                          "min": 80.0, "max": 260.0}}},
            "L3": {"x": 95200.0, "y": 462200.0, "params": {
                "CONCTTE|chloride|mg/l": {"n": 6, "median": 300.0,
                                          "min": 100.0, "max": 400.0}}},
        },
    }

    PEIL_CELLS = [
        {"cell": "c1", "inZoneFraction": 0.9, "conflictFraction": 0.8,
         "cellAreaM2": 740000.0},
        {"cell": "c2", "inZoneFraction": 0.9, "conflictFraction": 0.0,
         "cellAreaM2": 740000.0},
    ]

    @staticmethod
    def _call(points_in=None):
        """points_in: list of (index, cell) membership for the join."""
        points_in = points_in or [(0, "c1"), (1, "c1"), (2, "c2")]

        def call(process_id, inputs):
            if process_id == "h3-spatial-join-points":
                assert inputs["cells"] == ["c1", "c2"]
                return {"join": {
                    "pointCount": 3, "cellCount": 2,
                    "resolution": inputs["resolution"],
                    "perPoint": [{"index": i, "cell": c, "inCells": True}
                                 for i, c in points_in],
                    "perCell": []}}
            assert process_id == "h3-morans-i"
            return {"statistics": {"moransI": 0.3, "pValue": 0.02}}

        return call

    def test_attach_water_quality_median_and_scale(self):
        from rijnland import water_quality

        report = {"degradations": []}
        art = water_quality.attach_water_quality(
            report, fixture=self.FIXTURE,
            parameter_key="CONCTTE|chloride|mg/l",
            peil_cells=self.PEIL_CELLS, call=self._call())
        by = {r["cell"]: r for r in art["rows"]}
        self.assertEqual(by["c1"]["value"], 150.0)  # median(100, 200)
        self.assertEqual(by["c1"]["nLocations"], 2)
        self.assertEqual(by["c1"]["nMeasurements"], 24)
        self.assertEqual(by["c1"]["conflictFraction"], 0.8)
        # chloride: high is worse; c2 (300, the max) must outrank c1
        self.assertGreater(by["c2"]["value01"], by["c1"]["value01"])
        w = report["waterkwaliteit"]
        self.assertEqual(w["locationsWithParameter"], 3)
        self.assertEqual(w["locationsInCells"], 3)
        self.assertEqual(w["moransI"], 0.3)
        self.assertEqual(art["label"], "Chloride (mg/l)")

    def test_attach_water_quality_low_is_worse_inverts(self):
        from rijnland import water_quality

        fixture = {
            "year": 2025, "source": "test",
            "locations": {
                code: {"x": 95000.0 + i * 100, "y": 462000.0, "params": {
                    "VERZDGGD|zuurstof|%": {"n": 4, "median": med,
                                            "min": med, "max": med}}}
                for i, (code, med) in enumerate(
                    (("L1", 40.0), ("L2", 70.0), ("L3", 95.0)))
            },
        }
        report = {"degradations": []}
        art = water_quality.attach_water_quality(
            report, fixture=fixture, parameter_key="VERZDGGD|zuurstof|%",
            peil_cells=self.PEIL_CELLS,
            call=self._call(points_in=[(0, "c1"), (1, "c2"), (2, "c2")]))
        by = {r["cell"]: r for r in art["rows"]}
        # zuurstof: low is worse -> the 40% cell must have the HIGHEST score
        self.assertEqual(by["c1"]["value"], 40.0)
        self.assertEqual(by["c2"]["value"], 82.5)  # median(70, 95)
        self.assertGreater(by["c1"]["value01"], by["c2"]["value01"])

    def test_attach_water_quality_degrades(self):
        from rijnland import water_quality

        report = {"degradations": []}
        self.assertIsNone(water_quality.attach_water_quality(
            report, fixture=self.FIXTURE, parameter_key="CONCTTE|chloride|mg/l",
            peil_cells=self.PEIL_CELLS))
        self.assertEqual(report["degradations"][0]["kind"], "wq-unavailable")
        with self.assertRaises(ValueError):
            water_quality.attach_water_quality(
                report, fixture=self.FIXTURE, parameter_key="nope",
                peil_cells=self.PEIL_CELLS, call=self._call())


class TestTimeseries(unittest.TestCase):

    FIXTURE = {
        "source": "test", "subject": "Meetgegevens",
        "areaName": "Rijnland", "fetchedAt": "2026-09-11T00:00:00Z",
        "rawRowsPerYear": {"2020": 10, "2026": 6},
        "series": {
            "CONCTTE|chloride|mg/l": [
                {"ym": f"2020-{m:02d}", "n": 30, "nLocations": 25,
                 "median": 100.0 + m, "p25": 80.0, "p75": 130.0}
                for m in range(1, 13)
            ] + [
                {"ym": f"2021-{m:02d}", "n": 30, "nLocations": 25,
                 "median": 110.0 + m, "p25": 90.0, "p75": 140.0}
                for m in range(1, 13)
            ],
        },
    }

    def test_climatology_per_month_of_year(self):
        from rijnland import timeseries_report as ts

        clim = ts.climatology(self.FIXTURE["series"]
                              ["CONCTTE|chloride|mg/l"])
        self.assertEqual(len(clim), 12)
        self.assertEqual(clim[0], 106.0)  # median(101, 111)
        self.assertEqual(clim[11], 117.0)  # median(112, 122)

    def test_rolling_median_edges_are_none(self):
        from rijnland import timeseries_report as ts

        roll = ts.rolling_median(self.FIXTURE["series"]
                                 ["CONCTTE|chloride|mg/l"])
        self.assertEqual(len(roll), 24)
        self.assertIsNone(roll[0])
        self.assertIsNone(roll[-1])
        self.assertIsNotNone(roll[6])  # first full centered window

    def test_render_timeseries_html(self):
        from rijnland import timeseries_report as ts

        html = ts.render_timeseries(self.FIXTURE,
                                    default_parameter="CONCTTE|chloride|mg/l")
        self.assertIn("chloride", html)
        self.assertIn("Seizoenscyclus", html)
        self.assertIn("Afspelen", html)
        self.assertIn("2020\u20132026", html)
        self.assertNotIn("</script>x", html.split("ts-data")[1][:100000])

    def test_render_rejects_empty_fixture(self):
        from rijnland import timeseries_report as ts

        with self.assertRaises(ValueError):
            ts.render_timeseries({"series": {}})


class TestPeilen(unittest.TestCase):

    CHART = ('series": [{"name": "WNS test", "data": ['
             '{"y": -5.5, "x": 1787914058000.0}, '
             '{"y": -5.4, "x": 1788000458000.0}]}')

    ARCHIVE = {
        "lastFetchedAt": "2026-09-11T00:00:00Z",
        "stations": {
            "a_polder": {"name": "Polder A", "layer": "polders",
                         "days": {"2026-09-01": {"n": 24, "median": -5.5,
                                                 "min": -5.6, "max": -5.4},
                                  "2026-09-02": {"n": 24, "median": -5.4,
                                                 "min": -5.5, "max": -5.3}}},
            "b_polder": {"name": "Polder B", "layer": "polders",
                         "days": {"2026-09-01": {"n": 24, "median": -5.0,
                                                 "min": -5.1, "max": -4.9}}},
            "c_boezem": {"name": "Boezem C", "layer": "boezem",
                         "days": {"2026-09-01": {"n": 24, "median": -0.4,
                                                 "min": -0.5, "max": -0.3}}},
        },
    }

    def test_parse_and_daily(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "fetch_peilen",
            Path(__file__).resolve().parents[1] / "scripts" / "fetch_peilen.py")
        fp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fp)
        pts = fp.parse_chart_series(self.CHART)
        self.assertEqual(len(pts), 2)
        self.assertEqual(pts[0]["y"], -5.5)
        days = fp.daily_stats(pts)
        self.assertEqual(list(days), ["2026-08-28", "2026-08-29"])
        self.assertEqual(days["2026-08-28"]["n"], 1)

    def test_build_fixture_aggregates(self):
        import run_peilen as rp
        fx = rp.build_fixture(self.ARCHIVE)
        # aggregate needs >=5 stations/day -> none here
        self.assertNotIn(rp.AGG_POLDERS, fx["series"])
        self.assertEqual(len(fx["series"]), 3)
        self.assertIn("a_polder", fx["labels"])
        self.assertEqual(fx["series"]["a_polder"][0]["ym"], "2026-09-01")
        self.assertEqual(fx["series"]["a_polder"][0]["p25"], -5.6)  # min as band


class TestHexmapTime(unittest.TestCase):

    def _call(self):
        # two locations: index 0 -> cell A (both months), index 1 -> cell B
        def call(process_id, inputs):
            if process_id == "h3-spatial-join-points":
                return {"join": {
                    "pointCount": 2, "cellCount": 2, "resolution": 8,
                    "perPoint": [
                        {"index": 0, "cell": "aaa", "inCells": True},
                        {"index": 1, "cell": "bbb", "inCells": True}],
                    "perCell": []}}
            assert process_id == "h3-cells-to-geojson", process_id
            ring = [[[0, 0], [1, 0], [1, 1], [0, 0]]]
            return {"features": {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"cell": "aaa",
                                                   "resolution": 8},
                 "geometry": {"type": "Polygon", "coordinates": ring}},
                {"type": "Feature", "properties": {"cell": "bbb",
                                                   "resolution": 8},
                 "geometry": {"type": "Polygon", "coordinates": ring}}]}}
        return call

    def test_build_cell_steps_median_and_gaps(self):
        from rijnland import hexmap_time

        locs = [
            {"x": 95000.0, "y": 462000.0,
             "values": [100.0, 200.0]},          # in cell aaa both steps
            {"x": 96100.0, "y": 463100.0,
             "values": [None, 40.0]},            # cell bbb: gap then value
        ]
        bundle = hexmap_time.build_cell_steps(
            locations=locs, resolution=8, call=self._call())
        self.assertEqual(bundle["nSteps"], 2)
        self.assertEqual(bundle["values"]["aaa"], [100.0, 200.0])
        self.assertEqual(bundle["values"]["bbb"], [None, 40.0])
        self.assertEqual(len(bundle["cells_fc"]["features"]), 2)

    def test_build_cell_steps_without_call_returns_none(self):
        from rijnland import hexmap_time

        self.assertIsNone(hexmap_time.build_cell_steps(
            locations=[{"x": 1, "y": 2, "values": [1.0]}], call=None))

    def test_render_hexmap_time_html(self):
        from rijnland import hexmap_time

        bundle = {"cells_fc": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"cell": "aaa"},
             "geometry": None}]},
            "values": {"aaa": [1.0, 2.0]}, "nSteps": 2}
        html = hexmap_time.render_hexmap_time(
            bundle, steps=["jan 2020", "feb 2020"], title="T",
            value_label="Chloride", unit="mg/l", vmin=0.0, vmax=2.0,
            stops=[(0.0, "laag"), (1.0, "hoog")])
        self.assertIn("leaflet@1.9.4", html)
        self.assertIn('type="range"', html)
        self.assertIn("Afspelen", html)
        self.assertIn("jan 2020", html)
        self.assertIn("Chloride", html)
        import json as _json
        import re as _re
        blocks = _re.findall(
            r'<script type="application/json"[^>]*>(.*?)</script>',
            html, _re.S)
        for b in blocks:
            _json.loads(b)  # still valid JSON after < escaping


class TestHexmapTimeMulti(unittest.TestCase):

    def test_render_multi_switcher(self):
        from rijnland import hexmap_time

        fc = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"cell": "aaa"},
             "geometry": None}]}
        bundles = {
            "A|x|mg/l": {"cells_fc": fc, "values": {"aaa": [1.0, 2.0]},
                         "nSteps": 2},
            "B|y|%": {"cells_fc": fc, "values": {"aaa": [50.0, 10.0]},
                      "nSteps": 2},
        }
        metas = {
            "A|x|mg/l": {"label": "Stof A", "unit": "mg/l",
                         "vmin": 0.0, "vmax": 2.0},
            "B|y|%": {"label": "Stof B", "unit": "%",
                      "vmin": 0.0, "vmax": 50.0, "invert": True},
        }
        html = hexmap_time.render_hexmap_time_multi(
            bundles, steps=["jan", "feb"], metas=metas, default="A|x|mg/l",
            title="T", stops=[(0.0, "laag"), (1.0, "hoog")])
        self.assertIn('<select id="param"', html)
        # de dropdown-opties bouwt de JS runtime; labels staan in de payload
        import json as _json
        import re as _re
        block = _re.search(r'id="anim-data">(\{.*?\})</script>', html, _re.S)
        data = _json.loads(block.group(1))
        self.assertEqual(set(data["params"]), {"A|x|mg/l", "B|y|%"})
        self.assertEqual(data["params"]["A|x|mg/l"]["label"], "Stof A")
        self.assertEqual(data["params"]["B|y|%"]["unit"], "%")
        self.assertTrue(data["params"]["B|y|%"]["invert"])
        self.assertEqual(data["default"], "A|x|mg/l")
        # stof-geadapterede legenda: stops meegaven in de payload
        stops_b = data["params"]["B|y|%"]["stops"]
        self.assertEqual(stops_b[0]["label"], "Gunstig")
        self.assertEqual(stops_b[0]["value"], "50")  # hoog = gunstig (gespiegeld)
        self.assertEqual(stops_b[-1]["value"], "0")
        self.assertEqual(data["params"]["A|x|mg/l"]["stops"][-1]["value"], "2")
