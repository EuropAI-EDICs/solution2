"""Checklist-runner met synthetische lagen (offline, geen netwerk)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "poc"))  # pipeline-hergebruik zoals poc-breda

import jsonschema  # noqa: E402

import minigim.checklist as clmod  # noqa: E402
from minigim.registry import MiniGimRegistry  # noqa: E402

from tests import fixtures  # noqa: E402


def _runner(tmpdir: Path):
    reg = MiniGimRegistry()
    fake = fixtures.fake_fetch_layer_factory()
    with mock.patch.object(clmod, "fetch_layer", fake):
        runner = clmod.ChecklistRunner(reg, fixtures.AOI_FC, tmpdir)
        yield runner


class TestClip(unittest.TestCase):
    def test_punten_overleven_de_clip(self):
        """buffer(0)-reparatie mag punten niet leegmaken (shapely-semantiek)."""
        fc = fixtures._fc([
            {"type": "Feature", "properties": {"a": 1}, "geometry": fixtures._point(100100, 400100)},
            {"type": "Feature", "properties": {"a": 2}, "geometry": fixtures._point(99900, 399900)},
        ])
        import shapely.geometry as sg

        aoi = sg.Polygon(fixtures.AOI_POLY)
        clipped, n = clmod._clip(fc, aoi)
        self.assertEqual(len(clipped), 1)
        self.assertEqual(n, 2)

    def test_lijnen_overleven_de_clip(self):
        fc = fixtures._fc([
            {"type": "Feature", "properties": {}, "geometry": fixtures._line(100000, 400100, 100500, 400100)},
        ])
        import shapely.geometry as sg

        aoi = sg.Polygon(fixtures.AOI_POLY)
        clipped, _ = clmod._clip(fc, aoi)
        self.assertEqual(len(clipped), 1)
        self.assertEqual(round(clipped[0]["geometry"]["coordinates"][1][0] - clipped[0]["geometry"]["coordinates"][0][0]), 500)


class TestCurrentOnly(unittest.TestCase):
    def test_bgt_historisch_weggefilterd(self):
        fc = fixtures.layers()["pdok-bgt-ogc-api::wegdeel"]
        kept, dropped = clmod._current_only(fc, "pdok-bgt-ogc-api")
        self.assertEqual(len(kept["features"]), 2)
        self.assertEqual(dropped, 1)

    def test_niet_bgt_ongewijzigd(self):
        fc = fixtures.layers()["pdok-bag-wfs::bag:verblijfsobject"]
        out, dropped = clmod._current_only(fc, "pdok-bag-wfs")
        self.assertEqual(len(out["features"]), 3)
        self.assertEqual(dropped, 0)


class TestRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile

        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls.tmp.name)
        fake = fixtures.fake_fetch_layer_factory()
        with mock.patch.object(clmod, "fetch_layer", fake):
            reg = MiniGimRegistry()
            cls.runner = clmod.ChecklistRunner(reg, fixtures.AOI_FC, cls.tmpdir)
            cls.records = cls.runner.run()
        cls.by_id = {r["lijstItemId"]: r for r in cls.records}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_alle_items_uitgevoerd(self):
        self.assertEqual(len(self.records), 74)

    def test_auto_items_geleverd(self):
        for rid in ("locatie.plangrens", "locatie.adres", "topografie.materialisatie.wegdeel",
                    "topografie.materialisatie.waterdeel", "topografie.materialisatie.bebouwing-bag",
                    "ruimtelijke-ordening.kadaster.percelen", "identiteit.bouwjaar",
                    "statistiek.aantal-eenheden", "identiteit.voorzieningen.verblijfsobject-gebruiksfunctie",
                    "topografie.mobiliteit.verkeerswegen"):
            self.assertEqual(self.by_id[rid]["deliveredStatus"], "delivered", rid)

    def test_adres_is_verblijfsobject_niet_pand(self):
        # 2 vbo's binnen plangrens, 1 erbuiten
        self.assertEqual(self.by_id["locatie.adres"]["values"]["count"], 2)

    def test_historische_bgt_objecten_geteld_als_gefilterd(self):
        vals = self.by_id["topografie.materialisatie.wegdeel"]["values"]
        self.assertEqual(vals["historicalObjectsFiltered"], 1)
        self.assertEqual(vals["featureCount"], 2)

    def test_natura2000_afstand(self):
        vals = self.by_id["ruimtelijke-ordening.natuur.natura2000"]["values"]
        self.assertFalse(vals["presence"])
        self.assertAlmostEqual(vals["distanceToNearestKm"], 2.5, delta=0.1)

    def test_cbs_schattingen(self):
        inw = self.by_id["statistiek.aantal-inwoners"]["values"]["estimate"]
        self.assertGreater(inw, 0)
        woz = self.by_id["statistiek.woz"]["values"]["estimate"]
        self.assertEqual(woz, 350)

    def test_proxies(self):
        self.assertAlmostEqual(self.by_id["statistiek.fsi"]["values"]["fsiProxy"],
                               (120 + 80) / 250000, places=4)
        self.assertGreater(self.by_id["statistiek.gsi"]["values"]["gsiProxy"], 0)
        # woon + kantoor → genormaliseerde entropy 1.0
        self.assertAlmostEqual(self.by_id["statistiek.mxi"]["values"]["mxiProxy"], 1.0, places=3)

    def test_risicovlag_hoog_niet_geleverd(self):
        r = self.by_id["topografie.hoogte.hoogte-maaiveld"]  # manual + prioriteit hoog
        self.assertEqual(r["deliveredStatus"], "manual-action")
        self.assertIn("hoog-prioriteit niet automatisch geleverd", r["riskFlags"])

    def test_prov_aanwezig_voor_delivered(self):
        for r in self.records:
            if r["deliveredStatus"] == "delivered" and r["bindingStatus"] in ("auto", "partial"):
                self.assertIsNotNone(r["prov"], r["lijstItemId"])

    def test_summary(self):
        s = clmod.summarize(self.records)
        self.assertEqual(s["itemCount"], 74)
        self.assertEqual(s["deliveredStatus"]["manual-action"], 45)

    def test_artifact_schema_valideert(self):
        schema = json.loads((ROOT / "schemas" / "minigim-omgevingsanalyse.schema.json").read_text())
        doc = {
            "runId": "test", "generatedAt": "2026-09-21T00:00:00Z",
            "miniGimVersions": {"lijst": "v0.91", "ils": "v0.8"},
            "aoi": {"file": "test.geojson", "btoM2": self.runner.bto_m2,
                    "bbox28992": list(self.runner.bbox)},
            "items": self.records,
            "summary": clmod.summarize(self.records),
        }
        jsonschema.validate(doc, schema)


if __name__ == "__main__":
    unittest.main()
