from __future__ import annotations
import unittest
from pipeline.zone_projector import ProjectionError, project_zone

EXEC_53 = {
    "produces": {"legal_character": "TOETS"},
    "parameters": [
        {"name": "ashoogte_m", "type": "number", "description": "As m"},
        {"name": "op_of_in_aansluiting_op_bestaand_bouwperceel", "type": "boolean", "description": "bouwperceel"},
    ],
    "input": [
        {
            "name": "in_gebied_kleine_windturbine",
            "type": "boolean",
            "description": "Geo-feit",
            "source": {"description": "buiten wet-YAML"},
        }
    ],
    "output": [{"name": "toegestaan_kleine_windturbine", "type": "boolean", "description": "uitkomst"}],
    "actions": [{
        "output": "toegestaan_kleine_windturbine",
        "value": {
            "operation": "AND",
            "conditions": [
                {"operation": "LESS_THAN_OR_EQUAL", "subject": "$ashoogte_m", "value": 20},
                {"operation": "EQUALS", "subject": "$op_of_in_aansluiting_op_bestaand_bouwperceel", "value": True},
                {"operation": "EQUALS", "subject": "$in_gebied_kleine_windturbine", "value": True},
            ],
        },
    }],
}

BINDING_53 = {
    "inputs": {
        "in_gebied_kleine_windturbine": {
            "zoneIds": ["gebied_kleine_windturbine"],
            "selection": "within",
            "geometrySource": "provincial_gio",
            "gioJoinId": "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822",
            "caveat": "GIO uit Bijlage II CVDR704250",
        }
    }
}

class ZoneProjectorTests(unittest.TestCase):
    def test_art53_projects_zone_and_conditions(self):
        out = project_zone(EXEC_53, BINDING_53, zone_semantics="inclusion", rule_type="zone_inclusion")
        self.assertEqual(out["zoneSelector"]["zoneIds"], ["gebied_kleine_windturbine"])
        self.assertEqual(out["zoneSelector"]["selection"], "within")
        params = {c["parameter"]: c for c in out["conditions"]}
        self.assertEqual(params["ashoogte_m"]["operator"], "<=")
        self.assertEqual(params["ashoogte_m"]["value"], 20)
        self.assertEqual(params["op_of_in_aansluiting_op_bestaand_bouwperceel"]["value"], True)
        self.assertNotIn("in_gebied_kleine_windturbine", params)  # geo zit in zoneSelector

    def test_missing_binding_raises(self):
        with self.assertRaises(ProjectionError):
            project_zone(EXEC_53, None, zone_semantics="inclusion", rule_type="zone_inclusion")

    def test_unknown_operation_raises(self):
        bad = {"actions": [{"output": "x", "value": {"operation": "NOT_A_REAL_OP", "subject": "$a", "value": 1}}],
               "parameters": [{"name": "a", "type": "number"}], "input": [], "output": [{"name": "x", "type": "boolean"}]}
        with self.assertRaises(ProjectionError):
            project_zone(bad, {}, zone_semantics="none", rule_type="procedural_condition")

if __name__ == "__main__":
    unittest.main()
