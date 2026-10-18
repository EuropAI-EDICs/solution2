"""Manifest-loader: valide tegen schema; ongeldige manifesten falen luid."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.manifest import ManifestError, load_manifest  # noqa: E402

MINIMAL = {
    "poc": "test-poc",
    "methodiek": "test-v1",
    "phases": [
        {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse",
         "agent": {"role": "poc-specialist"},
         "tasks": [
             {"id": "t1", "binding": "auto",
              "tool": {"class": "retrieval", "ref": "bron:x", "transport": "in-process"}},
             {"id": "t2", "binding": "manual", "manualPointer": "KLIC"},
         ],
         "gate": {"validate": ["V0", "V2"]}},
    ],
}


class TestManifest(unittest.TestCase):
    def test_minimaal_manifest_valideert(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(MINIMAL), encoding="utf-8")
            m = load_manifest(p)
            self.assertEqual(m["poc"], "test-poc")
            self.assertEqual(len(m["phases"]), 1)

    def test_manual_zonder_pointer_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][1].pop("manualPointer")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)

    def test_onbekende_toolklasse_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][0]["tool"]["class"] = "magische-berekening"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)

    def test_auto_zonder_tool_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][0].pop("tool")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)


if __name__ == "__main__":
    unittest.main()
