# nldt/tests/test_laya_werklijst.py
"""Tests voor de laya-werklijst (Inzet A): artefact-only, fail-soft, geen laya-import."""
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from nldt.simulation.regelrecht.full_export import laya_werklijst  # noqa: E402


def _schrijf_cache(pad: pathlib.Path, *, met_hints: bool, onder_gate: bool = False) -> None:
    report = {
        "schemaVersion": "1", "poc": "eindhoven", "generatedAt": "t",
        "sourceSha256": "0" * 64,
        "counts": {"formalized": 1, "ambiguous": 0, "rejected": 0, "unmatched": 1},
        "articles": [
            {"number": "1.1", "status": "formalized", "reason": "template"},
            {"number": "2.2", "status": "unmatched", "reason": "no_template"},
        ],
        "orphanedFormalRules": [],
    }
    (pad / "eindhoven-formalization-report.json").write_text(json.dumps(report), "utf-8")
    if not met_hints:
        return
    hints = {
        "contract": "laya-hints/v1", "instrument": "eindhoven", "gegenereerdOp": "t",
        "model": {"checkpoint": "x", "checkpointSha256": "0" * 64,
                  "datasetSha256": "0" * 64, "gate": 0.55},
        "artikelen": [{
            "number": "2.2", "voorspeldeStatus": "formalized",
            "confidence": 0.4 if onder_gate else 0.8,
            "door": not onder_gate, "heeftEvidence": 0.9,
        }],
    }
    (pad / "eindhoven-laya-hints.json").write_text(json.dumps(hints), "utf-8")


class WerklijstTest(unittest.TestCase):
    def test_template_gap_kandidaat(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=True)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertTrue(wl["beschikbaar"])
            self.assertEqual([r["number"] for r in wl["rijen"]], ["2.2"])
            self.assertEqual(wl["rijen"][0]["categorie"], "template_gap_kandidaat")

    def test_onder_gate_is_verwachte_onthouding(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=True, onder_gate=True)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertEqual(wl["rijen"][0]["categorie"], "verwacht_onthouding")

    def test_fail_soft_zonder_hints(self):
        with tempfile.TemporaryDirectory() as d:
            pad = pathlib.Path(d)
            _schrijf_cache(pad, met_hints=False)
            wl = laya_werklijst.bouw_werklijst("eindhoven", out_dir=pad)
            self.assertFalse(wl["beschikbaar"])
            self.assertIn("predict_export", wl["oorzaak"])


if __name__ == "__main__":
    unittest.main()
