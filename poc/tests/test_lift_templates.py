"""Lift of legacy zone/conditions templates to RegelRecht execution + zoneBinding."""
from __future__ import annotations

import copy
import json
import unittest

from pipeline import track_config
from pipeline.lift_templates_to_execution import FORMALIZED_KINDS, lift_template
from pipeline.zone_projector import project_zone

ZONE = {
    "zoneIds": ["gebied_windenergie"],
    "selection": "within",
    "geometrySource": "provincial_gio",
    "gioJoinId": "/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846",
    "caveat": "GIO-versie overgenomen uit Bijlage II van CVDR704250",
}
LEGACY = {
    "kind": "inclusion",
    "zone": ZONE,
    "conditions": [{"parameter": "capacity", "operator": ">=", "value": 3, "unit": "MW"}],
    "extra_tags": ["x"],
    "rationale": "CORE WIND RULE. Art. 5.4 lid 1 permits turbines of at least 3 MW.",
    "executable_ref": "engine.zone.within@poc-v1",
}


class LiftTemplateTests(unittest.TestCase):
    def test_lift_replaces_zone_and_conditions(self):
        out = lift_template(copy.deepcopy(LEGACY), key="W-05")
        self.assertNotIn("zone", out)
        self.assertNotIn("conditions", out)
        self.assertEqual(out["kind"], "inclusion")
        self.assertEqual(out["extra_tags"], ["x"])
        ex = out["execution"]
        self.assertEqual(ex["parameters"][0]["unit"], "MW")
        self.assertEqual([i["name"] for i in ex["input"]], ["in_gebied_windenergie"])
        self.assertEqual(ex["output"][0]["name"], "result_w_05")
        ops = ex["actions"][0]["value"]["conditions"]
        self.assertEqual(ops[0]["operation"], "GREATER_THAN_OR_EQUAL")
        self.assertEqual(out["zoneBinding"]["inputs"]["in_gebied_windenergie"], ZONE)

    def test_projection_roundtrips_legacy_fields(self):
        out = lift_template(copy.deepcopy(LEGACY), key="W-05")
        proj = project_zone(out["execution"], out["zoneBinding"],
                            zone_semantics="inclusion", rule_type="zone_inclusion")
        self.assertEqual(proj["zoneSelector"], ZONE)
        self.assertEqual(proj["conditions"], LEGACY["conditions"])

    def test_exclusion_asserts_input_false_multi_zone_single_binding(self):
        spec = {
            "kind": "exclusion",
            "zone": {**ZONE, "zoneIds": ["natura_2000", "ganzenrustgebied"],
                     "geometrySource": "national_source"},
            "conditions": [],
            "rationale": "x" * 30,
        }
        spec["zone"].pop("gioJoinId")
        out = lift_template(spec, key="W-08")
        value = out["execution"]["actions"][0]["value"]
        self.assertEqual(value["value"], False)
        (binding,) = out["zoneBinding"]["inputs"].values()
        self.assertEqual(binding["zoneIds"], ["natura_2000", "ganzenrustgebied"])

    def test_execution_present_returns_unchanged(self):
        spec = {"kind": "inclusion", "execution": {"output": [], "actions": []}, "zoneBinding": {}}
        self.assertIs(lift_template(spec), spec)

    def test_ambiguous_and_reject_unchanged(self):
        for kind in ("ambiguous", "reject"):
            spec = {"kind": kind, "rule_type": "procedural_condition", "reason": "r", "rationale": "x"}
            self.assertIs(lift_template(spec), spec)

    def test_all_committed_templates_are_lifted(self):
        for key, spec in track_config.load_templates().items():
            if spec["kind"] in FORMALIZED_KINDS:
                self.assertIn("execution", spec, key)
                self.assertIn("zoneBinding", spec, key)
                self.assertNotIn("zone", spec, key)
                self.assertNotIn("conditions", spec, key)
            else:
                self.assertNotIn("execution", spec, key)
                json.dumps(spec)


if __name__ == "__main__":
    unittest.main()
