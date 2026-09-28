"""Registry-tests: schema's, dekking en ILS-consistentie."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jsonschema  # noqa: E402

from minigim.registry import MiniGimRegistry  # noqa: E402


class TestRegistries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = MiniGimRegistry()

    def test_lijst_schema_valid(self):
        schema = json.loads((ROOT / "schemas" / "minigim-lijst.schema.json").read_text())
        jsonschema.validate(self.reg.lijst, schema)

    def test_ils_schema_valid(self):
        schema = json.loads((ROOT / "schemas" / "minigim-ils.schema.json").read_text())
        jsonschema.validate(self.reg.ils, schema)

    def test_bindings_schema_valid(self):
        schema = json.loads((ROOT / "schemas" / "lijst-binding.schema.json").read_text())
        jsonschema.validate(self.reg.bindings, schema)

    def test_binding_coverage_complete(self):
        """V2-voorwaarde: elk lijst-item exact één binding (74/74)."""
        self.assertEqual(len(self.reg.bindings["bindings"]), len(self.reg.items))
        self.assertEqual(set(self.reg.bindings_by_id), set(self.reg.items))

    def test_item_counts_stable(self):
        """v0.91-structuur: 74 items over 5 thema's, 11 met prioriteit hoog."""
        self.assertEqual(len(self.reg.items), 74)
        self.assertEqual(len({s["thema"] for s in self.reg.lijst["sections"]}), 5)
        self.assertEqual(sum(1 for i in self.reg.items.values() if i["prioriteit"] == "hoog"), 11)

    def test_ils_tree_consistency(self):
        ids = [n["id"] for n in self.reg.ils["nodes"]]
        self.assertEqual(len(ids), len(set(ids)), "ils-node ids uniek")
        idset = set(ids)
        for n in self.reg.ils["nodes"]:
            if n["level"] == 0:
                self.assertIsNone(n["parent"])
            else:
                self.assertIn(n["parent"], idset, f"{n['id']} hangt aan onbekende ouder")

    def test_ils_path_labels(self):
        path = self.reg.ils_path_labels("n3.bebouwd")
        self.assertEqual(path, ["Uitgeefbaar", "Uitgeefbaar", "Percelen", "Bebouwd"])
        self.assertEqual(self.reg.ils_ifc("n3.bebouwd"), "IFCBuilding")

    def test_ils_ifc_inheritance(self):
        # kolk heeft zelf '?'/null; erft IFCSITE van n2.water
        self.assertEqual(self.reg.ils_ifc("n3.kolk"), "IFCSITE")

    def test_manual_bindings_have_pointer(self):
        for b in self.reg.bindings["bindings"]:
            if b["status"] == "manual":
                self.assertTrue(b.get("manualPointer"), f"{b['lijstItemId']} mist manualPointer")

    def test_partial_bindings_have_proxynote(self):
        for b in self.reg.bindings["bindings"]:
            if b["status"] == "partial":
                self.assertTrue(b.get("proxyNote"), f"{b['lijstItemId']} mist proxyNote")


if __name__ == "__main__":
    unittest.main()
