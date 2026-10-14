# nldt/tests/test_simulation_regelrecht_full.py
"""Tests volle RegelRecht-instrument-export (spec 2026-10-14)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FULL = ROOT / "nldt" / "simulation" / "regelrecht" / "full_export"
sys.path.insert(0, str(FULL))

from split_cvdr_html import split_instrument, write_articles_json  # noqa: E402
import paths  # noqa: E402


class TestArticleSplitter(unittest.TestCase):
    def test_utrecht_contains_art_5_3(self):
        arts = split_instrument("utrecht")
        by_num = {a["number"]: a for a in arts}
        self.assertIn("5.3", by_num)
        self.assertIn("kleine windturbine", by_num["5.3"]["text"].lower())
        self.assertGreater(len(arts), 100)

    def test_eindhoven_contains_art_10_2_and_22_1(self):
        arts = split_instrument("eindhoven")
        nums = {a["number"] for a in arts}
        self.assertIn("10.2", nums)
        self.assertIn("22.1", nums)
        self.assertGreater(len(arts), 500)

    def test_articles_json_roundtrip_sha(self):
        arts = split_instrument("utrecht")[:3]
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "u.json"
            write_articles_json("utrecht", arts, out)
            data = json.loads(out.read_text())
            self.assertEqual(data["poc"], "utrecht")
            self.assertEqual(
                data["sourceSha256"],
                hashlib.sha256(paths.HTML_UTRECHT.read_bytes()).hexdigest(),
            )
            self.assertEqual(len(data["articles"]), 3)


if __name__ == "__main__":
    unittest.main()
