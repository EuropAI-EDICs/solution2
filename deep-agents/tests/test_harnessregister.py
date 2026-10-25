"""Harnessregister-conformance: het register claimt niets wat de repo niet
waarmaakt (patroon: poc-minigim/tests/test_modelregister.py).

Bewezen wordt: prompt-bestanden bestaan en de sha256 klopt, prompt-targets
op disk == geregistreerde targets (niets ongepind), model-pinnen gelijk aan
de model_config-defaults, en de harness-lab-voorbeelden (varianten en
tasksets) zijn schema-geldig. Geen netwerk, geen model.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "poc-fundament"))

from fundament import harnesslab as hl  # noqa: E402

# model_config-defaults (nldt/services/common/model_config.py) — wijzigt de
# default daar, dan hoort het register opnieuw gescaffold te worden.
VERWACHTE_PINS = {
    "orchestrator": {"DEEP_AGENT_MODEL": "gemma4:31b-mlx"},
    "subagent": {"DEEP_AGENT_SUBMODEL": "gemma4:12b-mlx"},
}


class TestHarnessRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = hl.load_harness_register(ROOT / "harnessregister.json")
        cls.by_target = {(h["component"], h["target"]): h
                         for h in cls.reg["harnesses"]
                         if h.get("status", "actief") == "actief"}

    def test_promptfiles_bestaan_en_sha_klopt(self):
        for h in self.reg["harnesses"]:
            if h["component"] != "prompt":
                continue
            pad = ROOT / h["artifact"]["path"]
            self.assertTrue(pad.is_file(), h["id"])
            self.assertEqual(
                h["artifact"]["sha256"], hl.sha256_file(pad),
                f"{h['id']}: {h['artifact']['path']} is gewijzigd — "
                "her-scaffold het register (harness_lab.py scaffold)")

    def test_alle_prompts_op_disk_zijn_gepind(self):
        from harness_lab_adapter import PROMPT_TARGETS  # noqa: E402  (deep-agents root op sys.path via tests-package)

        targets = {t for (c, t) in self.by_target if c == "prompt"}
        self.assertEqual(targets, set(PROMPT_TARGETS),
                         "prompts op disk en geregistreerde prompt-targets wijken af")

    def test_modelpinnen_gelijk_aan_defaults(self):
        for target, verwacht in VERWACHTE_PINS.items():
            entry = self.by_target[("modelPin", target)]
            self.assertEqual(entry["artifact"]["env"], verwacht, target)

    def test_adopties_dragen_llm_of_expliciet_fake_bewijs(self):
        for h in self.reg["harnesses"]:
            if h.get("status") != "actief" or "adoptedFrom" not in h:
                continue
            self.assertTrue(h.get("probeEvidence"), h["id"])
            for ev in h["probeEvidence"]:
                self.assertEqual(ev["verdict"], "pass", h["id"])
                self.assertEqual(ev["mode"], "llm", h["id"])

    def test_harness_lab_voorbeelden_zijn_schema_geldig(self):
        lab = ROOT / "harness-lab"
        varianten = sorted((lab / "variants").glob("*.json"))
        tasksets = sorted((lab / "tasksets").glob("*.json"))
        self.assertTrue(varianten and tasksets, "harness-lab-voorbeelden ontbreken")
        for v in varianten:
            hl.load_variant(v)
        for t in tasksets:
            hl.load_taskset(t)


if __name__ == "__main__":
    unittest.main()
