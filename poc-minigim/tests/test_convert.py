"""Converter-hulpfuncties (puur) + end-to-end conversie indien openpyxl beschikbaar."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
OPENPYXL = importlib.util.find_spec("openpyxl") is not None


@unittest.skipUnless(OPENPYXL, "converter-import vereist openpyxl (systeem-python3); de pure helper-tests draaien dan mee")
class TestHelpers(unittest.TestCase):
    def _mod(self):
        sys.path.insert(0, str(TOOLS))
        import convert_minigim_xlsx as conv
        return conv

    def test_slug(self):
        conv = self._mod()
        self.assertEqual(conv._slug("Bodemdaling/draagkracht grond"), "bodemdaling-draagkracht-grond")
        self.assertEqual(conv._slug("m² en ¹"), "m2-en-1")

    def test_norm_samenvouwen_witruimte(self):
        conv = self._mod()
        self.assertEqual(conv._norm("regel\neind  en   spaties"), "regel eind en spaties")

    def test_split_data_komma_regels(self):
        conv = self._mod()
        self.assertEqual(conv._split_data("x-, y-coördinaat RD (EPSG:28992)"),
                         ["x-, y-coördinaat RD (EPSG:28992)"])
        self.assertEqual(conv._split_data("eigendom, sectienummer, perceelnummer"),
                         ["eigendom", "sectienummer", "perceelnummer"])

    def test_split_multi(self):
        conv = self._mod()
        self.assertEqual(conv._split_multi("ontwerp/financieel/proces"),
                         ["ontwerp", "financieel", "proces"])


@unittest.skipUnless(OPENPYXL, "openpyxl niet beschikbaar (systeem-python3 heeft het; run evt. met python3 -m unittest)")
class TestConverterEndToEnd(unittest.TestCase):
    def test_converteer_pinned_bronnen(self):
        """De converter reproduceert de gecommitte registries byte-voor-byte
        (op tijdstipvelden na) uit de gepinde xlsx-bronnen."""
        result = subprocess.run(
            [sys.executable, str(TOOLS / "convert_minigim_xlsx.py")],
            capture_output=True, text=True, cwd=str(ROOT.parent),
        )
        if result.returncode != 0 and "openpyxl" in result.stderr:
            self.skipTest("openpyxl niet beschikbaar in deze interpreter")
        self.assertEqual(result.returncode, 0, result.stderr)

        lijst = json.loads((ROOT / "registry" / "minigim-lijst.json").read_text())
        ils = json.loads((ROOT / "registry" / "minigim-ils.json").read_text())
        self.assertEqual(len(lijst["items"]), 74)
        self.assertEqual(len(ils["nodes"]), 49)
        # ids stabiel
        self.assertIn("topografie.materialisatie.bebouwing-3d-bag", {i["id"] for i in lijst["items"]})
        self.assertIn("n3.bebouwd", {n["id"] for n in ils["nodes"]})


if __name__ == "__main__":
    unittest.main()
