"""Unit tests for PoC-4 Breda embed helpers in build_simulation.py."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
sys.path.insert(0, str(SIM))


class TestBredaQaGate(unittest.TestCase):
    def test_unknown_buurt_raises(self):
        from build_simulation import validate_breda_qa

        with self.assertRaises(ValueError):
            validate_breda_qa(
                [{"id": "x", "question": "q", "answer": "a", "buurtnaam": "Nergenshuizen"}],
                {"Belcrum", "Ginneken"},
            )

    def test_known_buurt_ok(self):
        from build_simulation import validate_breda_qa

        validate_breda_qa(
            [{"id": "x", "question": "q", "answer": "a", "buurtnaam": "Belcrum"}],
            {"Belcrum", "Ginneken"},
        )


class TestBuildBreda(unittest.TestCase):
    def test_build_breda_shape(self):
        from build_simulation import build_breda

        p = build_breda()
        self.assertEqual(p["runId"], "20260913T192628Z-breda-scan")
        self.assertEqual(p["nBuurten"], 56)
        self.assertEqual(len(p["buurten"]), 56)
        self.assertIn("BU07580100", p["geo"])
        self.assertGreaterEqual(len(p["qa"]), 8)
        self.assertEqual(len(p["stages"]), 6)
        b0 = p["buurten"][0]
        for k in ("democratic", "spatial", "economic", "social"):
            self.assertIn(k, b0["scores"])


if __name__ == "__main__":
    unittest.main()
