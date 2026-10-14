"""Tests voor de indicator-referentielens (tools/indicator_refs.py).

Additieve tool: leest uitsluitend de globale planning_indicators-datasect;
de canonieke MiniGIM-run-artefacten worden niet aangeraakt.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = POC_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(POC_ROOT / "tools"))

import indicator_refs  # noqa: E402
import planning_indicators as pi  # noqa: E402


class CollectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = indicator_refs.collect("heat")

    def test_structuur_en_sectorfilter(self):
        self.assertEqual(self.payload["artifact"], "minigim-indicator-refs")
        self.assertEqual(self.payload["sector"], {"key": "heat", "id": 2})
        self.assertEqual(self.payload["count"], len(self.payload["indicators"]))
        self.assertTrue(self.payload["indicators"])
        joined = {ind["id"] for ind in pi.indicators() if ind["sector_id"] == 2}
        self.assertEqual({ind["id"] for ind in self.payload["indicators"]}, joined)

    def test_provenance_blok_compleet(self):
        ds = self.payload["dataset"]
        self.assertEqual(ds["version"], "1.2")
        self.assertEqual(ds["doi"], "10.5281/zenodo.17464468")
        self.assertEqual(ds["license"], "CC-BY-NC-SA-4.0")
        self.assertEqual(ds["upstreamCommit"], pi.UPSTREAM_COMMIT)
        self.assertIn("Cardenas-Leon", ds["citation"])
        for name in indicator_refs.USED_TABLES:
            entry = ds["files"][name]
            self.assertTrue(entry["sha256"], name)
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertGreater(entry["rows"], 0)

    def test_papers_gestript_en_gesorteerd(self):
        with_papers = [ind for ind in self.payload["indicators"] if ind["papers"]]
        self.assertTrue(with_papers, "heat-sector moet literatuur-koppels hebben")
        for ind in with_papers:
            years = [p["year"] for p in ind["papers"]]
            self.assertEqual(years, sorted(years))
            for paper in ind["papers"]:
                self.assertNotIn("<", paper["title"])

    def test_deterministisch(self):
        again = indicator_refs.collect("heat")
        a, b = dict(self.payload), dict(again)
        a.pop("generatedAt"), b.pop("generatedAt")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_query_filter(self):
        scoped = indicator_refs.collect("heat", query="temperature")
        self.assertTrue(scoped["indicators"])
        self.assertTrue(
            all(
                "temperature" in (ind["name"] or "").lower()
                or "temperature" in (ind["definition"] or "").lower()
                for ind in scoped["indicators"]
            )
        )
        self.assertLessEqual(scoped["count"], self.payload["count"])

    def test_onbekende_sector_faalt(self):
        with self.assertRaises(SystemExit):
            indicator_refs.collect("wind")


class WriteArtifactTest(unittest.TestCase):
    def test_schrijft_leesbaar_json_met_sector_en_query_in_naam(self):
        payload = indicator_refs.collect("housing", query="dwelling")
        with tempfile.TemporaryDirectory() as tmp:
            path = indicator_refs.write_artifact(payload, Path(tmp))
            self.assertTrue(path.name.startswith("indicator-refs-housing-dwelling"))
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["count"], payload["count"])
        self.assertEqual(len(loaded["indicators"]), payload["count"])


if __name__ == "__main__":
    unittest.main()
