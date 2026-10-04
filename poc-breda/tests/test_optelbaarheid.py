"""Offline tests: ZN-2 optelbaarheid over twee fixture-gebieden."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from breda import optelbaarheid
from tests import fixtures


class TestOptelbaarheid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = fixtures.layers_dict()
        cls.b = optelbaarheid.second_city_layers(
            cls.base, gemeente="DemoStad", code="city-b", gm="GM0999"
        )

    def test_fingerprints_stable(self):
        a = optelbaarheid.formula_fingerprint()
        b = optelbaarheid.formula_fingerprint()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_two_areas_pass(self):
        report = optelbaarheid.run_optelbaarheid(
            [
                (
                    "city-a",
                    self.base,
                    {"gemeente": "Breda", "gemeenteCode": "GM0758"},
                ),
                (
                    self.b["meta"]["areaId"],
                    self.b["layers"],
                    self.b["meta"],
                ),
            ],
            generated_at="2026-10-04T16:00:00Z",
        )
        self.assertEqual(optelbaarheid.validate_report(report), [])
        self.assertTrue(report["definitions"]["identical"])
        self.assertEqual(report["validation"]["verdict"], "pass")
        self.assertEqual(report["combined"]["nAreas"], 2)
        self.assertNotEqual(
            report["areas"][0]["gemeenteCode"],
            report["areas"][1]["gemeenteCode"],
        )
        # Absolute middelen divergeren (DemoStad input-shift); percentile-means ~50
        self.assertNotEqual(
            report["areas"][0]["absoluteMeans"]["onbenut_dakpotentieel"],
            report["areas"][1]["absoluteMeans"]["onbenut_dakpotentieel"],
        )
        self.assertIsNotNone(report["combined"]["absoluteMeans"]["onbenut_dakpotentieel"])

    def test_combined_reconstructible(self):
        report = optelbaarheid.run_optelbaarheid(
            [
                ("a", self.base, {"gemeente": "Breda", "gemeenteCode": "GM0758"}),
                (
                    "b",
                    self.b["layers"],
                    {"gemeente": "DemoStad", "gemeenteCode": "GM0999"},
                ),
            ]
        )
        for v in optelbaarheid.SCORE_WAARDEN:
            num = sum(
                a["means"][v] * a["weights"][v]
                for a in report["areas"]
                if a["means"][v] is not None
            )
            den = sum(
                a["weights"][v]
                for a in report["areas"]
                if a["means"][v] is not None
            )
            expected = round(num / den, 2) if den else None
            self.assertEqual(report["combined"]["means"][v], expected)

    def test_cli(self):
        import optelbaarheid_run

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "zn2"
            rc = optelbaarheid_run.run(["--offline-fixtures", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "optelbaarheid-report.json").is_file())
            self.assertTrue((out / "optelbaarheid-report.md").is_file())


if __name__ == "__main__":
    unittest.main()
