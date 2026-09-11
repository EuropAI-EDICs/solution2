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
for p in (str(ROOT), str(POC_ROOT)):
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
