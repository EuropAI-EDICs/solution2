"""Offline tests: bbox-normalisatie en CBS-WFS-fetcher met nep-sessie."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT.parent / "poc")):
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import fetch  # noqa: E402


class TestBboxStr(unittest.TestCase):
    def test_string_bbox(self):
        self.assertEqual(
            fetch._bbox_str("106000.0,392000.0,133000.0,421000.0"),
            "106000.0,392000.0,133000.0,421000.0",
        )

    def test_list_bbox(self):
        out = fetch._bbox_str([106000, 392000, 133000, 421000])
        for part in ("106000", "392000", "133000", "421000"):
            self.assertIn(part, out)

    def test_ongeldige_bbox_faalt(self):
        with self.assertRaises(fetch.FetchError):
            fetch._bbox_str("1,2,3")  # te weinig onderdelen
        with self.assertRaises(fetch.FetchError):
            fetch._bbox_str([10, 20, 5, 30])  # xmax < xmin


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class _FakeSession:
    """Telt calls; pagina 1: 250 features (waarvan 2 Breda), pagina 2: rest."""

    headers: dict = {}

    def __init__(self, page2=None):
        breda1 = {
            "type": "Feature",
            "properties": {"buurtcode": "BU07580001", "buurtnaam": "A",
                           "gemeentenaam": "Breda"},
            "geometry": {"type": "Point", "coordinates": [1, 2]},
        }
        breda2 = {
            "type": "Feature",
            "properties": {"buurtcode": "BU07580002", "buurtnaam": "B",
                           "gemeentenaam": "Breda"},
            "geometry": {"type": "Point", "coordinates": [3, 4]},
        }
        ander = {
            "type": "Feature",
            "properties": {"buurtcode": "BU09990001", "buurtnaam": "X",
                           "gemeentenaam": "Anderen"},
            "geometry": {"type": "Point", "coordinates": [5, 6]},
        }
        self.pages = [
            {"type": "FeatureCollection", "features": [breda1, ander] * 125},
            {"type": "FeatureCollection", "features": (page2 or [breda2] * 100)},
        ]
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params or {}))
        idx = 0 if not self.calls or len(self.calls) == 1 else min(
            len(self.calls) - 1, len(self.pages) - 1
        )
        return _FakeResponse(self.pages[idx])


class TestOgcFilter(unittest.TestCase):
    def test_breda_filter(self):
        f = fetch.ogc_gemeente_filter("Breda")
        self.assertIn("<Literal>Breda</Literal>", f)
        self.assertEqual(f, fetch.OGC_FILTER)

    def test_tilburg_filter(self):
        f = fetch.ogc_gemeente_filter("Tilburg")
        self.assertIn("<Literal>Tilburg</Literal>", f)

    def test_ongeldige_naam(self):
        with self.assertRaises(fetch.FetchError):
            fetch.ogc_gemeente_filter("Foo<script>")


class TestCbsFetch(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_paging_en_filter(self):
        sess = _FakeSession()
        fc = fetch.fetch_cbs_buurten(
            "106000,392000,133000,421000", refresh=True,
            cache_dir=self.cache, session=sess,
        )
        # alleen Breda-features, van beide pagina's
        self.assertEqual(len(fc["features"]), 225)
        self.assertTrue(all(
            f["properties"]["gemeentenaam"] == "Breda" for f in fc["features"]
        ))
        self.assertEqual(sess.calls[0]["startIndex"], 0)
        self.assertEqual(sess.calls[1]["startIndex"], 250)
        self.assertIn("filter", sess.calls[0])
        self.assertIn("gemeentenaam", sess.calls[0]["filter"])
        self.assertIn("Breda", sess.calls[0]["filter"])
        # cache geschreven
        self.assertTrue((self.cache / "cbs-buurten-2024.28992.geojson").exists())
        self.assertTrue((self.cache / "cbs-buurten-2024.4326.geojson").exists())
        props = fc["properties"]
        self.assertEqual(props["featureCount"], 225)
        self.assertEqual(props["pages"], 2)
        self.assertEqual(props["gemeente"], "Breda")

    def test_andere_gemeente_eigen_cache(self):
        class _TilburgSession:
            headers: dict = {}

            def get(self, url, params=None, timeout=None):
                feat = {
                    "type": "Feature",
                    "properties": {
                        "buurtcode": "BU08550001",
                        "buurtnaam": "T",
                        "gemeentenaam": "Tilburg",
                        "gemeentecode": "GM0855",
                    },
                    "geometry": {"type": "Point", "coordinates": [1, 2]},
                }
                return _FakeResponse({"type": "FeatureCollection", "features": [feat]})

        fc = fetch.fetch_cbs_buurten(
            None, refresh=True, cache_dir=self.cache,
            session=_TilburgSession(), gemeente="Tilburg",
        )
        self.assertEqual(len(fc["features"]), 1)
        self.assertEqual(fc["properties"]["gemeente"], "Tilburg")
        self.assertEqual(fc["properties"]["gemeenteCode"], "GM0855")
        self.assertTrue(
            (self.cache / "cbs-buurten-2024-tilburg.28992.geojson").exists()
        )
        # Breda-cache onaangeroerd
        self.assertFalse((self.cache / "cbs-buurten-2024.28992.geojson").exists())

    def test_cache_first_zonder_netwerk(self):
        fetch.fetch_cbs_buurten(
            "106000,392000,133000,421000", refresh=True,
            cache_dir=self.cache, session=_FakeSession(),
        )
        no_network = _FakeSession()
        fc = fetch.fetch_cbs_buurten(
            "106000,392000,133000,421000",
            cache_dir=self.cache, session=no_network,
        )
        self.assertEqual(no_network.calls, [])
        self.assertEqual(len(fc["features"]), 225)

    def test_http_fout_faalt_expliciet(self):
        class _ErrSession:
            headers: dict = {}

            def get(self, url, params=None, timeout=None):
                return _FakeResponse({}, status=500)

        with self.assertRaises(fetch.FetchError):
            fetch.fetch_cbs_buurten(
                "106000,392000,133000,421000", refresh=True,
                cache_dir=self.cache, session=_ErrSession(),
            )


if __name__ == "__main__":
    unittest.main()
