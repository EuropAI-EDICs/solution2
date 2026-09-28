"""Fetch-hulpfuncties: bbox-formattering, cache-sleutels, AOI-normalisatie."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from minigim import fetch  # noqa: E402


class TestBboxStr(unittest.TestCase):
    def test_integer_formatting(self):
        self.assertEqual(fetch._bbox_str([114768.4, 401044.9, 116769.7, 403815.2]),
                         "114768,401045,116770,403815")


class TestCacheKey(unittest.TestCase):
    def test_filter_wordt_gehasht_niet_uitgeschreven(self):
        path = fetch._cache_key("pdok-cbs-wijkenbuurten-2024", "wfs2;wijkenbuurten:buurten;<Filter>x</Filter>")
        name = path.name
        self.assertIn("pdok-cbs-wijkenbuurten-2024__", name)
        self.assertNotIn("<", name)
        self.assertIn("-", name)

    def test_verschillende_bboxes_verschillende_keys(self):
        a = fetch._cache_key("s", "ogc-api-features;wegdeel;1,2,3,4")
        b = fetch._cache_key("s", "ogc-api-features;wegdeel;5,6,7,8")
        self.assertNotEqual(a, b)


class TestLoadAoi(unittest.TestCase):
    def test_rd_fc_ongewijzigd(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "aoi.geojson"
            p.write_text(json.dumps(
                {"type": "FeatureCollection",
                 "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
                 "features": [{"type": "Feature", "properties": {},
                               "geometry": {"type": "Polygon", "coordinates": [[[100000, 400000], [100100, 400000], [100100, 400100], [100000, 400100], [100000, 400000]]]}}]}
            ))
            fc, sha = fetch.load_aoi(p)
            self.assertEqual(fc["features"][0]["geometry"]["coordinates"][0][0][0], 100000)
            self.assertEqual(len(sha), 64)

    def test_wgs84_wordt_rd(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "aoi.geojson"
            p.write_text(json.dumps(
                {"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [4.819252, 51.609687]}}
            ))
            fc, _ = fetch.load_aoi(p)
            x, y = fc["features"][0]["geometry"]["coordinates"]
            self.assertGreater(x, 110000)   # RD rond Teteringen/Breda-noord
            self.assertGreater(y, 395000)
            self.assertLess(x, 120000)


if __name__ == "__main__":
    unittest.main()
