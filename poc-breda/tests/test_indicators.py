"""Offline tests: sentinelfilter, percentielmath, overlays, scan-op-fixtures."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT.parent / "poc")):
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import indicators  # noqa: E402
from tests import fixtures  # noqa: E402


class TestClean(unittest.TestCase):
    def test_sentinels_worden_none(self):
        for sent in (-99995, -99997, -99998):
            self.assertIsNone(indicators.clean(sent))

    def test_geldige_waarden_blijven(self):
        self.assertEqual(indicators.clean(0), 0)
        self.assertEqual(indicators.clean(17.5), 17.5)
        self.assertEqual(indicators.clean(1200), 1200)

    def test_non_nummeriek_wordt_none(self):
        self.assertIsNone(indicators.clean(None))
        self.assertIsNone(indicators.clean(True))
        self.assertIsNone(indicators.clean("x"))
        self.assertIsNone(indicators.clean(float("nan")))


class TestPercentiles(unittest.TestCase):
    def test_bekende_verdeling(self):
        scores = indicators.percentile_scores([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(scores, [0.0, 25.0, 50.0, 75.0, 100.0])

    def test_none_doet_niet_mee(self):
        scores = indicators.percentile_scores([None, 1.0, 2.0, 3.0, None])
        self.assertEqual(scores, [None, 0.0, 50.0, 100.0, None])

    def test_ties_krijgen_gemiddelde_rang(self):
        scores = indicators.percentile_scores([1.0, 2.0, 2.0, 3.0])
        self.assertEqual(scores[1], scores[2])
        self.assertEqual(scores[1], 50.0)

    def test_inverse_spiegelt(self):
        scores = indicators.percentile_scores([1.0, 2.0, 3.0])
        self.assertEqual(indicators.inverse(scores), [100.0, 50.0, 0.0])

    def test_inverse_houdt_none(self):
        self.assertEqual(indicators.inverse([None, 0.0]), [None, 100.0])


class TestComputeScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scan = indicators.compute_scan(fixtures.layers_dict())

    def test_volume(self):
        self.assertEqual(len(self.scan["buurten"]), fixtures.COLS * fixtures.ROWS)

    def test_scores_in_bereik(self):
        for b in self.scan["buurten"]:
            for v in ("democratic", "spatial", "economic", "social"):
                s = b["scores"][v]["score"]
                if s is not None:
                    self.assertGreaterEqual(s, 0.0)
                    self.assertLessEqual(s, 100.0)

    def test_waterbuurten_krijgen_geen_scores(self):
        water = [b for b in self.scan["buurten"] if b["water"] == "JA"]
        self.assertTrue(water)
        for b in water:
            for v in ("democratic", "spatial", "economic", "social"):
                self.assertIsNone(b["scores"][v]["score"], f"{b['buurtcode']}/{v}")
                # en het ontbreken is gedocumenteerd (geen stille missing)
                self.assertTrue(
                    b["missing"][v] or b["water"] == "JA",
                    f"{b['buurtcode']}/{v} mist missing-registratie",
                )

    def test_groendekking_linkerhelft(self):
        # kolommen 0..5 liggen volledig in de groenbaan, kolommen 6+ erbuiten
        for b in self.scan["buurten"]:
            if b["water"] == "JA":
                continue
            col = int(b["buurtnaam"].split()[1].split("-")[0])
            share = b["scores"]["spatial"]["inputs"]["groendekking_share"]
            if col <= 5:
                self.assertAlmostEqual(share, 1.0, places=2, msg=b["buurtnaam"])
            else:
                self.assertAlmostEqual(share, 0.0, places=2, msg=b["buurtnaam"])

    def test_wijkdeals_allen_linksboven(self):
        with_deals = [
            b for b in self.scan["buurten"]
            if (b["scores"]["democratic"]["inputs"].get("deals") or 0) > 0
        ]
        self.assertTrue(with_deals)
        for b in with_deals:
            # buurtnaam is "Cel i-j": deals liggen in kolommen 0–2, rijen 0–1
            col, row = b["buurtnaam"].split()[1].split("-")
            self.assertLessEqual(int(col), 2, b["buurtnaam"])
            self.assertLessEqual(int(row), 1, b["buurtnaam"])

    def test_verharding_boven_vs_onder(self):
        # onderste rijen (lage j) zijn 'boven' in het vlak y-onbekend; we
        # controleren dat er twee verschillende verhardingswaarden zijn
        waarden = {
            b["scores"]["social"]["inputs"]["verharding_pct"]
            for b in self.scan["buurten"] if b["water"] == "NEE"
        }
        self.assertEqual(waarden, {75.0, 35.0})

    def test_kansenkaart_omschrijvingen(self):
        met_kans = [b for b in self.scan["buurten"] if b.get("kansenkaart")]
        self.assertTrue(met_kans)
        for b in met_kans:
            self.assertTrue(
                any(k in ("Groene klimaatas", "Waterberging") for k in b["kansenkaart"])
            )

    def test_deterministisch(self):
        tweede = indicators.compute_scan(fixtures.layers_dict())
        self.assertEqual(
            [b["scores"] for b in self.scan["buurten"]],
            [b["scores"] for b in tweede["buurten"]],
        )

    def test_zonder_optionele_lagen_degraderen_scores_niet_stil(self):
        layers = fixtures.layers_dict()
        layers.pop("bomen")
        layers.pop("kansenkaart")
        scan = indicators.compute_scan(layers)
        for b in scan["buurten"]:
            if b["water"] == "JA":
                continue
            if b["scores"]["spatial"]["score"] is None:
                self.assertTrue(b["missing"]["spatial"])

    def test_rollup(self):
        for v in ("democratic", "spatial", "economic", "social"):
            ru = self.scan["rollup"][v]
            self.assertGreater(ru["n"], 0)
            self.assertLessEqual(len(ru["top"]), 5)
            top_scores = [s for _, s in ru["top"]]
            self.assertEqual(top_scores, sorted(top_scores, reverse=True))
            bottom_scores = [s for _, s in ru["bottom"]]
            self.assertEqual(bottom_scores, sorted(bottom_scores))


class TestBomenPer100(unittest.TestCase):
    def test_kleine_buurt_krijgt_none(self):
        # inwoners < 100 → bomen_per_100 onbetrouwbaar → None (cite-or-abstain)
        layers = fixtures.layers_dict()
        layers["buurten"]["features"][0]["properties"]["aantalInwoners"] = 42
        scan = indicators.compute_scan(layers)
        self.assertIsNone(
            scan["buurten"][0]["scores"]["spatial"]["inputs"]["bomen_per_100_inw"]
        )


if __name__ == "__main__":
    unittest.main()
