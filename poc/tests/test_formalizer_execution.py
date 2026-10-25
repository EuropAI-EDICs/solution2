from __future__ import annotations

import unittest
from pathlib import Path

from pipeline.agents import NormAnalyst, NormFormalizer
from pipeline.zone_projector import project_zone

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


class _Hook:
    """Minimal S2 hook returning a fixed zone proposal without execution."""

    rejected: list = []
    stamp = "test"

    def __init__(self, proposal):
        self.proposal = proposal

    def __call__(self, card):
        return self.proposal


class FormalizerExecutionTests(unittest.TestCase):
    def _w03(self):
        cards = NormAnalyst().read(CORPUS / "evidence-wind.json")
        by_id = {c.id: c for c in cards}
        self.assertIn("NC-W-03", by_id)
        return by_id["NC-W-03"]

    def test_w03_execution_is_sot_and_projects(self):
        rules = NormFormalizer().formalize([self._w03()])
        rule = rules[0].to_dict()
        self.assertEqual(rule["status"], "formalized")
        self.assertIn("execution", rule)
        self.assertIn("zoneBinding", rule)
        projected = project_zone(
            rule["execution"], rule["zoneBinding"],
            zone_semantics=rule["zoneSemantics"], rule_type=rule["ruleType"],
        )
        self.assertEqual(projected["zoneSelector"], rule["zoneSelector"])
        self.assertEqual(projected["conditions"], rule["conditions"])

    def test_w03_conditions_are_projected_not_handwritten(self):
        rule = NormFormalizer().formalize([self._w03()])[0].to_dict()
        params = {c["parameter"] for c in rule["conditions"]}
        self.assertEqual(params, {"ashoogte_m", "op_of_in_aansluiting_op_bestaand_bouwperceel"})
        self.assertEqual(rule["zoneSelector"]["zoneIds"], ["gebied_kleine_windturbine"])

    def test_integrity_detects_zone_drift(self):
        formalizer = NormFormalizer()
        card = self._w03()
        rules = formalizer.formalize([card])
        rules[0].zoneSelector.zoneIds = ["something_else"]
        with self.assertRaises(RuntimeError):
            formalizer._check_integrity([card], rules)

    def test_llm_proposal_without_execution_is_ambiguous(self):
        card = self._w03()
        import pipeline.agents as agents

        saved = agents.TEMPLATE_SPECS.pop(card.evidenceId)
        try:
            hook = _Hook({
                "kind": "inclusion", "zoneIds": ["gebied_windenergie"],
                "rationale": "x", "conditions": [],
            })
            rule = NormFormalizer(llm_hook=hook).formalize([card])[0]
        finally:
            agents.TEMPLATE_SPECS[card.evidenceId] = saved
        self.assertEqual(rule.status, "ambiguous")
        self.assertIn("RegelRecht SoT", rule.reason)
        self.assertIn("lacks execution", rule.reason)


if __name__ == "__main__":
    unittest.main()
