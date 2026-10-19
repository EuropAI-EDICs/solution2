"""Het manifest beschrijft de werkelijkheid: taak-dekking en binding-gelijkheid."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from minigim.registry import MiniGimRegistry  # noqa: E402  (bootstrap: zet poc-fundament op sys.path)
from fundament.manifest import load_manifest  # noqa: E402
from fundament.models import load_model_registry, model_by_id  # noqa: E402

COMPUTATION_OPS = {"proxy_ratio", "proxy_entropy"}


class TestManifestConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest(ROOT / "fase-manifest.json")
        cls.reg = MiniGimRegistry()

    def test_taakdekking_exact_de_lijst(self):
        ids = [t["id"] for ph in self.manifest["phases"]
               for t in (ph.get("tasks") or []) if t.get("from") == "register:minigim-lijst"]
        self.assertEqual(sorted(ids), sorted(self.reg.items), "lijst-taken kloppen niet")

    def test_bindings_komen_overeen_met_het_register(self):
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t.get("from") != "register:minigim-lijst":
                    continue
                b = self.reg.binding(t["id"])
                self.assertEqual(t["binding"], b["status"], t["id"])
                if t["binding"] in ("auto", "partial"):
                    op = (b.get("derivation") or {}).get("op")
                    self.assertEqual(t["tool"]["derive"], [op] if op else [], t["id"])
                    verwacht = "computation" if op in COMPUTATION_OPS else "retrieval"
                    self.assertEqual(t["tool"]["class"], verwacht, t["id"])

    def test_tool_ref_komt_overeen_met_binding_en_modelregister(self):
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t.get("from") != "register:minigim-lijst" or "tool" not in t:
                    continue
                b = self.reg.binding(t["id"])
                if t["tool"]["class"] == "computation":
                    self.assertEqual(t["tool"]["ref"], "model:minigim-proxy-derivaties", t["id"])
                else:
                    verwacht_ref = ",".join(b.get("serviceRefs") or []) or "run-input"
                    self.assertEqual(t["tool"]["ref"], verwacht_ref, t["id"])
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t["id"] == "ils-classificatie":
                    self.assertEqual(t["tool"]["ref"], "model:minigim-ils-classificatie", t["id"])

    def test_alle_modelrefs_resolven_in_het_modelregister(self):
        models = load_model_registry(ROOT / "modelregister.json")
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                ref = (t.get("tool") or {}).get("ref") or ""
                if ref.startswith("model:"):
                    model_by_id(models, ref[len("model:"):])

    def test_manual_heeft_altijd_pointer(self):
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t["binding"] == "manual":
                    self.assertTrue(t.get("manualPointer"), t["id"])

    def test_vijf_fasen_met_gate(self):
        self.assertEqual([p["id"] for p in self.manifest["phases"]],
                         ["F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
                          "F3-doorrekening", "F4-synthese"])
        for p in self.manifest["phases"]:
            self.assertIn("gate", p)


if __name__ == "__main__":
    unittest.main()
