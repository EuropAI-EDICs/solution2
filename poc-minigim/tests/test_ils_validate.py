"""ILS-draft en validatie V0–V3 (offline)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jsonschema  # noqa: E402

import minigim.checklist as clmod  # noqa: E402
import minigim.ils as ilsmod  # noqa: E402
import minigim.validate as valmod  # noqa: E402
from minigim.registry import MiniGimRegistry  # noqa: E402

from tests import fixtures  # noqa: E402


class TestIlsDraft(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls.tmp.name)
        fake = fixtures.fake_fetch_layer_factory()
        with mock.patch.object(clmod, "fetch_layer", fake):
            reg = MiniGimRegistry()
            runner = clmod.ChecklistRunner(reg, fixtures.AOI_FC, cls.tmpdir)
            runner.run()  # laagn cache vullen
            builder = ilsmod.IlsDraftBuilder(reg, runner)
            cls.draft, cls.geoms = builder.build()
        cls.by_node = {f["ilsNodeId"]: f for f in cls.draft["features"]}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_schema_valideert(self):
        schema = json.loads((ROOT / "schemas" / "minigim-ils-draft.schema.json").read_text())
        jsonschema.validate(self.draft, schema)

    def test_kernnodes_aanwezig(self):
        for node in ("n2.wegen", "n2.water", "n1.groen", "n2.percelen", "n3.bebouwd"):
            self.assertIn(node, self.by_node, node)

    def test_ifc_mapping(self):
        self.assertEqual(self.by_node["n2.wegen"]["ifcExportAs"], "IFCROAD")
        self.assertEqual(self.by_node["n3.bebouwd"]["ifcExportAs"], "IFCBuilding")
        self.assertEqual(self.by_node["n1.groen"]["ifcExportAs"], "IFCSITE")

    def test_nodepad_loopt_tot_niveau0(self):
        self.assertEqual(self.by_node["n3.bebouwd"]["nodePath"], "Uitgeefbaar > Uitgeefbaar > Percelen > Bebouwd")

    def test_draft_en_v4_stempels(self):
        self.assertTrue(self.draft["draft"])
        self.assertEqual(self.draft["v4"], "pending")

    def test_verhard_onverhard_correct_gesplitst(self):
        """'gesloten verharding'/'verhard' → n1.verhard; 'onverhard' → unassigned."""
        self.assertIn("n1.verhard", self.by_node)
        self.assertEqual(self.by_node["n1.verhard"]["count"], 2)  # gesloten verharding + functie=verhard
        self.assertIn("onbegroeidterreindeel:verhard!=match", self.draft["unassigned"])
        self.assertEqual(self.draft["unassigned"]["onbegroeidterreindeel:verhard!=match"]["count"], 1)

    def test_feature_props(self):
        g = self.geoms[0]
        self.assertIn("ilsNodeId", g["properties"])
        self.assertIn("epsetMinigim", g["properties"])
        ep = g["properties"]["epsetMinigim"]
        self.assertIsNotNone(ep["watBenJe"])
        self.assertIsNone(ep["vanWieWasJe"], "eigendom is geen open data")


class TestValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls.tmp.name)
        fake = fixtures.fake_fetch_layer_factory()
        with mock.patch.object(clmod, "fetch_layer", fake):
            cls.reg = MiniGimRegistry()
            cls.runner = clmod.ChecklistRunner(cls.reg, fixtures.AOI_FC, cls.tmpdir)
            cls.records = cls.runner.run()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_v2_vangt_lege_prov(self):
        records = json.loads(json.dumps(self.records))
        records[0]["prov"] = None
        records[0]["deliveredStatus"] = "delivered"
        records[0]["bindingStatus"] = "auto"
        checks = []
        valmod.validate_v2(records, self.reg, checks)
        self.assertFalse(checks[-1]["ok"])

    def test_v2_vangt_bronmismatch(self):
        records = json.loads(json.dumps(self.records))
        r = next(x for x in records if x["deliveredStatus"] == "delivered"
                 and x["prov"]["protocol"] not in ("derived", "input"))
        item = self.reg.item(r["lijstItemId"])
        if not item.get("bronRegistratie"):
            self.skipTest("geen geschikt item met bronRegistratie")
        # prov claimt een ándere bron dan de binding-serveertitel bevat
        r["prov"]["bronRegistratie"] = "Helemaal Andere Bron"
        binding = self.reg.binding(r["lijstItemId"])
        original_refs = list(binding["serviceRefs"])
        binding["serviceRefs"] = ["breda-milieuzones"]  # titel zonder 'BAG'
        try:
            checks = []
            valmod.validate_v2(records, self.reg, checks)
            self.assertFalse(checks[-1]["ok"], checks[-1]["detail"])
        finally:
            binding["serviceRefs"] = original_refs  # geen besmetting van latere tests

    def test_v2_pass_op_schone_run(self):
        checks = []
        valmod.validate_v2(self.records, self.reg, checks)
        self.assertTrue(checks[-1]["ok"])

    def test_v3_vangt_drift(self):
        records = json.loads(json.dumps(self.records))
        r = next(x for x in records if x["deliveredStatus"] == "delivered"
                 and (self.reg.binding(x["lijstItemId"]).get("derivation") or {}).get("op", "") not in
                 ("echo_input", "representative_point", "none"))
        r["values"]["featureCount"] = 999999
        checks = []
        valmod.validate_v3(records, self.runner, self.reg, checks)
        self.assertFalse(checks[-1]["ok"])

    def test_v3_pass_op_schone_run(self):
        checks = []
        valmod.validate_v3(self.records, self.runner, self.reg, checks)
        self.assertTrue(checks[-1]["ok"], checks[-1]["detail"])

    def test_verdict(self):
        checks = [{"level": "V0", "artifact": "x", "ok": True, "detail": ""}]
        self.assertEqual(valmod.verdict(checks)["verdict"], "pass")
        checks.append({"level": "V1", "artifact": "x", "ok": False, "detail": ""})
        self.assertEqual(valmod.verdict(checks)["verdict"], "fail")


if __name__ == "__main__":
    unittest.main()
