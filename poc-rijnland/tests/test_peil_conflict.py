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
from shapely.geometry import box, mapping  # noqa: E402

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
