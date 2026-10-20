"""Offline tests voor DSO↔RegelRecht-overlap (geen netwerk)."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
OVERLAP = ROOT / "nldt" / "simulation" / "regelrecht" / "dso_overlap"
sys.path.insert(0, str(OVERLAP))

from overlap import article_numbers_from_annotaties, build_overlap  # noqa: E402


class TestArticleExtraction(unittest.TestCase):
    def test_wid_article_numbers_unique_order(self):
        payload = {
            "regelteksten": [
                {"wId": "x__art_5.3__para_1"},
                {"wId": "x__art_5.3__para_2"},
                {"wId": "x__art_10.2"},
                {"wId": "geen-artikel"},
            ]
        }
        self.assertEqual(
            article_numbers_from_annotaties(payload),
            ["5.3", "10.2"],
        )


class TestBuildOverlap(unittest.TestCase):
    def test_executable_vs_abstain(self):
        annotaties = {
            "regelteksten": [
                {"wId": "a__art_5.3"},
                {"wId": "a__art_1.1"},
                {"wId": "a__art_99.9"},
            ],
            "activiteiten": [],
            "locaties": [],
            "gebiedsaanwijzingen": [],
            "regelsVoorIedereen": [],
        }
        report = {
            "generatedAt": "2026-10-14T00:00:00Z",
            "counts": {"formalized": 1, "unmatched": 1},
            "articles": [
                {"number": "5.3", "status": "formalized", "reason": "ok", "source": "t"},
                {"number": "1.1", "status": "unmatched", "reason": "no_template", "source": "n"},
            ],
        }
        loc = {
            "id": "t",
            "label": "test",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }
        result = build_overlap(
            instrument_id="utrecht",
            location=loc,
            regeling={"identificatie": "/akn/test", "officieleTitel": "T"},
            annotaties=annotaties,
            annotaties_sha256="abc",
            report=report,
        )
        self.assertEqual(result["overlap"]["executableArticles"], ["5.3"])
        self.assertEqual(
            set(result["overlap"]["abstainArticles"]),
            {"1.1", "99.9"},
        )
        self.assertEqual(result["overlap"]["statusCounts"]["formalized"], 1)
        self.assertEqual(result["overlap"]["statusCounts"]["unmatched"], 1)
        self.assertEqual(result["overlap"]["statusCounts"]["missing_in_report"], 1)
        self.assertEqual(result["overlap"]["coverageExecutable"], 0.3333)


class TestOfflineCompare(unittest.TestCase):
    def test_compare_reads_cache(self):
        from compare import compare_instrument

        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td)
            stem = "utrecht__utrecht-domplein"
            (out / f"{stem}.regeling.json").write_text(
                json.dumps({"identificatie": "/akn/nl/act/pv26/2022/omgevingsverordening"}),
                encoding="utf-8",
            )
            (out / f"{stem}.annotaties.json").write_text(
                json.dumps(
                    {
                        "regelteksten": [{"wId": "x__art_5.3"}],
                        "activiteiten": [],
                        "locaties": [],
                    }
                ),
                encoding="utf-8",
            )
            (out / f"{stem}.annotaties.meta.json").write_text(
                json.dumps({"sha256": "deadbeef"}),
                encoding="utf-8",
            )
            result = compare_instrument(
                "utrecht",
                location_id="utrecht-domplein",
                out_dir=out,
                offline=True,
                skip_rp=True,
            )
            self.assertEqual(result["instrument"], "utrecht")
            self.assertIn("5.3", result["overlap"]["executableArticles"]
                + result["overlap"]["abstainArticles"])
            self.assertTrue((out / f"{stem}.overlap.json").is_file())


if __name__ == "__main__":
    unittest.main()
