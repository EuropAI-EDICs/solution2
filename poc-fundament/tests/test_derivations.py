"""Pure derivaties + fetch-contract (offline: cache_dir is verplicht)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.derivations import (  # noqa: E402
    CBS_SENTINELS,
    _area_m2,
    _breakdown,
    _clip,
    _current_only,
    _entropy_norm,
    _geom,
    _histogram,
    _length_km,
    _slugify,
    summarize,
)
from fundament.fetch import fetch_layer, load_aoi  # noqa: E402

AOI_POLY = [[100000.0, 400000.0], [100500.0, 400000.0], [100500.0, 400500.0],
            [100000.0, 400500.0], [100000.0, 400000.0]]


def _poly(x, y, w=50.0, h=50.0):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]]}


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


class TestDerivations(unittest.TestCase):
    def test_punten_overleven_de_clip(self):
        fc = _fc([
            {"type": "Feature", "properties": {"a": 1}, "geometry": {"type": "Point", "coordinates": [100100, 400100]}},
            {"type": "Feature", "properties": {"a": 2}, "geometry": {"type": "Point", "coordinates": [99000, 39000]}},
        ])
        import shapely.geometry as sg
        clipped, n = _clip(fc, sg.Polygon(AOI_POLY))
        self.assertEqual(len(clipped), 1)
        self.assertEqual(n, 2)

    def test_current_only_filtert_historie_allen_bgt(self):
        fc = _fc([
            {"type": "Feature", "properties": {"eind_registratie": "2020-01-01"}, "geometry": _poly(100000, 400000)},
            {"type": "Feature", "properties": {}, "geometry": _poly(100100, 400000)},
        ])
        out, dropped = _current_only(fc, "pdok-bgt-ogc-api")
        self.assertEqual(dropped, 1)
        self.assertEqual(len(out["features"]), 1)
        out2, dropped2 = _current_only(fc, "pdok-bag-wfs")  # andere bron: onaangetast
        self.assertEqual((dropped2, len(out2["features"])), (0, 2))

    def test_area_length_breakdown_entropy(self):
        feats = [
            {"type": "Feature", "properties": {"functie": "rijbaan"}, "geometry": _poly(100000, 400000, 100, 100)},
            {"type": "Feature", "properties": {"functie": "voetpad"}, "geometry": _poly(100000, 400000, 100, 100)},
            {"type": "Feature", "properties": {"functie": "voetpad"}, "geometry": _poly(100000, 400000, 100, 100)},
        ]
        self.assertEqual(_area_m2(feats), 30000.0)
        self.assertEqual(_entropy_norm(feats, "functie"), 0.9183)  # genormaliseerde entropy 1:2-verhouding, 4 dp
        self.assertEqual(list(_breakdown(feats, "functie")), ["voetpad", "rijbaan"])

    def test_summarize_telt_statussen(self):
        recs = [
            {"bindingStatus": "auto", "deliveredStatus": "delivered", "prioriteit": "hoog", "lijstItemId": "a"},
            {"bindingStatus": "manual", "deliveredStatus": "manual-action", "prioriteit": "hoog", "lijstItemId": "b"},
            {"bindingStatus": "partial", "deliveredStatus": "not-delivered", "prioriteit": "laag", "lijstItemId": "c"},
        ]
        s = summarize(recs)
        self.assertEqual(s["itemCount"], 3)
        self.assertEqual(s["autoCoverageOfHoog"]["delivered"], 1)
        self.assertEqual(s["hoogPrioriteitNotDelivered"], ["b"])

    def test_slugify(self):
        self.assertEqual(_slugify("topografie.hoogte.hoogte-maaiveld"), "topografie-hoogte-hoogte-maaiveld")

    def test_fetch_layer_zonder_cache_dir_is_fout(self):
        with self.assertRaises(TypeError):
            fetch_layer({"id": "x", "protocol": "ogc-api-features", "baseUrl": "https://example.test", "collections": ["c"]})

    def test_cbs_sentinels_bestaan(self):
        self.assertIn(-99999, CBS_SENTINELS)


if __name__ == "__main__":
    unittest.main()
