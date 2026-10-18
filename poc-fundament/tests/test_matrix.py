"""Matrix-renderer: deterministische markdown, fase × agent × tools."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.matrix import render_matrix, render_run_matrix  # noqa: E402

MANIFEST = {
    "poc": "test-poc",
    "methodiek": "test-v1",
    "phases": [
        {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse",
         "agent": {"role": "poc-specialist"},
         "tasks": [
             {"id": "t1", "binding": "auto", "tool": {"class": "retrieval", "ref": "bron:x"}},
             {"id": "t2", "binding": "manual", "manualPointer": "KLIC"},
         ],
         "gate": {"validate": ["V0", "V2"]}},
        {"id": "F3-doorrekening", "title": "Doorrekening",
         "agent": {"role": "poc-specialist"},
         "tasks": [{"id": "t3", "binding": "partial",
                    "tool": {"class": "computation", "ref": "model:mix", "transport": "in-process"}}]},
    ],
}


class TestMatrix(unittest.TestCase):
    def test_bevat_fasen_agenten_en_gates(self):
        md = render_matrix(MANIFEST)
        self.assertIn("F1-omgevingsanalyse", md)
        self.assertIn("poc-specialist", md)
        self.assertIn("retrieval", md)
        self.assertIn("computation", md)
        self.assertIn("V0, V2", md)
        self.assertIn("| 2 |", md)  # taken-aantal F1

    def test_bewijsbindingen_tellen_op(self):
        md = render_matrix(MANIFEST)
        self.assertIn("1 auto", md)
        self.assertIn("1 manual", md)
        self.assertIn("1 partial", md)

    def test_run_matrix_toont_delivered_status(self):
        records = [
            {"lijstItemId": "t1", "deliveredStatus": "delivered"},
            {"lijstItemId": "t2", "deliveredStatus": "manual-action"},
            {"lijstItemId": "t3", "deliveredStatus": "delivered"},
        ]
        md = render_run_matrix(MANIFEST, records)
        self.assertIn("delivered", md)
        self.assertIn("manual-action", md)


if __name__ == "__main__":
    unittest.main()
