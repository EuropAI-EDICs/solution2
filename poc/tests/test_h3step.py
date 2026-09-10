"""Offline tests for the poc H3 bridge (cache-first, no subprocess ever).

Fixtures under poc/data/cache/h3/ are generated once (live) by
poc/tests/make_h3_fixtures.py and committed; POC_H3_OFFLINE=1 makes any
cache miss an error instead of a subprocess invocation.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, h3step  # noqa: E402

FIXDIR = Path(__file__).resolve().parent / "h3_fixtures"

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[5.10, 52.08], [5.14, 52.08], [5.14, 52.11],
                     [5.10, 52.11], [5.10, 52.08]]],
}


def _fc(geom):
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": geom}]}


class OfflineEnv(unittest.TestCase):
    def setUp(self):
        self._patcher = mock.patch.dict(os.environ, {"POC_H3_OFFLINE": "1"})
        self._patcher.start()
        self.addCleanup(self._patcher.stop)


class TestCacheFirstBridge(OfflineEnv):

    def test_cached_call_never_spawns_subprocess(self):
        inputs = json.loads((FIXDIR / "square-res9-input.json").read_text())
        with mock.patch.object(h3step.subprocess, "run",
                               side_effect=AssertionError("subprocess invoked")):
            out = h3step.call("h3-polygon-to-cells", inputs)
        contracts.validate(out["coverage"], "h3coverage")
        self.assertEqual(out, h3step.call("h3-polygon-to-cells", inputs))

    def test_offline_cache_miss_raises(self):
        with self.assertRaises(h3step.H3UnavailableError):
            h3step.call("h3-polygon-to-cells",
                        {"polygon": _fc(SQUARE), "resolution": 7})

    def test_fingerprint_is_order_insensitive(self):
        a = h3step.fingerprint("p", {"x": 1, "y": [1, 2]})
        b = h3step.fingerprint("p", {"y": [1, 2], "x": 1})
        self.assertEqual(a, b)

    def test_coverage_fixture_replays(self):
        inputs = json.loads((FIXDIR / "square-res8-input.json").read_text())
        out = h3step.call("h3-polygon-to-cells", inputs)
        self.assertGreater(out["coverage"]["cellCount"], 0)

    def test_scenario_metrics_control_and_delta_paths(self):
        """Real offline coverage of the scenario_metrics bridge path (the
        exact seam where the CLI dict/string bugs lived): mock h3step.call
        with a fixture-shaped coverage + canned Moran stats."""
        cov_rows = [
            {"cell": c, "coverageFraction": f, "cellAreaM2": 740000.0}
            for c, f in (("a", 0.9), ("b", 0.8), ("c", 0.4), ("d", 1.0))
        ]
        stats = {"n": 4, "permutations": 199, "moransI": 0.42,
                 "expectedI": -1 / 3, "pValue": 0.05, "notes": []}

        def fake_call(process_id, inputs, **_kw):
            if process_id == "h3-polygon-to-cells":
                assert inputs["resolution"] == 8
                return {"coverage": {"resolution": 8, "cellCount": len(cov_rows),
                                     "cells": cov_rows,
                                     "crs": "cells-EPSG:4326-areas-EPSG:28992",
                                     "h3Version": "test"}}
            assert process_id == "h3-morans-i", process_id
            return {"statistics": stats}

        with mock.patch.object(h3step, "call", side_effect=fake_call):
            control = h3step.scenario_metrics({"type": "Polygon", "coordinates": []})
            delta = h3step.scenario_metrics(
                {"type": "Polygon", "coordinates": []}, control_cells={"a", "b"})
        # control path: cells listed (runner pops it), deltas null
        self.assertEqual(control["cellCount"], 3)  # a, b, d pass >= 0.5
        self.assertEqual(control["cells"], ["a", "b", "d"])
        self.assertIsNone(control["cellsGainedVsControl"])
        self.assertIsNone(control["cellsLostVsControl"])
        self.assertEqual(control["moransI"], 0.42)
        self.assertEqual(control["pValue"], 0.05)
        # delta path: no cells key; gained/lost vs the control set
        self.assertNotIn("cells", delta)
        self.assertEqual(delta["cellCount"], 3)
        self.assertEqual(delta["cellsGainedVsControl"], 1)  # d
        self.assertEqual(delta["cellsLostVsControl"], 0)


if __name__ == "__main__":
    unittest.main()
