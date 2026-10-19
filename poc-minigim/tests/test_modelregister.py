"""Modelregister (M4): registratie + transport-bestaanbewijs (offline).

Het register claimt transports; deze suite bewijst ze tegen de repo:
processId letterlijk in de process-adapter, agent-id/recipes/port in de
a2a-catalogus, riskLevel gelijk aan het recipe. Geen netwerk.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import minigim  # noqa: E402,F401  (bootstrap: zet poc-fundament op sys.path)
from fundament.models import load_model_registry, model_by_id  # noqa: E402


class TestModelRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = load_model_registry(ROOT / "modelregister.json")

    def test_modelrefs_uit_het_manifest_resolven(self):
        manifest = json.loads((ROOT / "fase-manifest.json").read_text(encoding="utf-8"))
        gevonden = 0
        for ph in manifest["phases"]:
            for t in (ph.get("tasks") or []):
                ref = (t.get("tool") or {}).get("ref") or ""
                if ref.startswith("model:"):
                    model_by_id(self.reg, ref[len("model:"):])
                    gevonden += 1
        self.assertEqual(gevonden, 6, "manifest koppelt niet exact 6 model-refs")

    def test_processes_transport_bestaat_in_de_process_adapter(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        handler_src = (REPO / "nldt" / "services" / "process_adapter" / "poc_handlers.py"
                       ).read_text(encoding="utf-8")
        for t in (t for t in m["transports"] if t["type"] == "processes"):
            self.assertIn(f'"{t["processId"]}"', handler_src, t["processId"])

    def test_a2a_transport_bestaat_in_de_catalog(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        cat = json.loads((REPO / "a2a-simulation" / "catalog" / "poc-agents.json").read_text(encoding="utf-8"))
        by_id = {a["id"]: a for a in cat["agents"]}
        for t in (t for t in m["transports"] if t["type"] == "a2a"):
            self.assertIn(t["agentId"], by_id, t["agentId"])
            agent = by_id[t["agentId"]]
            self.assertEqual(agent["port"], t["port"])
            self.assertIn(t["agentSkill"], agent["recipes"])

    def test_risklevel_komt_overeen_met_het_recipe(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        recipe = json.loads((REPO / "nldt" / "recipes" / "minigim-gebiedscheck.json").read_text(encoding="utf-8"))
        self.assertEqual(m["riskLevel"], recipe["riskLevel"])

    def test_fase2haak_entries_zijn_gemarkeerd_en_vrijgesteld(self):
        for m in self.reg["models"]:
            if m.get("status") == "fase-2-haak":
                self.assertIn("fase-2", m["prov"]["note"], m["id"])
        haak_ids = {m["id"] for m in self.reg["models"] if m.get("status") == "fase-2-haak"}
        self.assertEqual(haak_ids, {"grex-financien", "ifc-export"})

    def test_actieve_entries_blijven_bewezen(self):
        actief = [m for m in self.reg["models"] if m.get("status", "actief") == "actief"]
        self.assertIn("minigim-gebiedscheck-run", [m["id"] for m in actief])


if __name__ == "__main__":
    unittest.main()
