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

    def test_scenario_metrics_from_fixtures(self):
        inputs = json.loads((FIXDIR / "square-res8-input.json").read_text())
        out = h3step.call("h3-polygon-to-cells", inputs)
        self.assertGreater(out["coverage"]["cellCount"], 0)


if __name__ == "__main__":
    unittest.main()
