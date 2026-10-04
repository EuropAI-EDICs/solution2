"""Offline tests: Plane D — spatial claims + gebiedsafweging runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from breda import claims, indicators
from tests import fixtures

ROOT = Path(__file__).resolve().parent.parent
DEMO_CLAIMS = ROOT / "claims" / "demo-breda.json"


class TestClaimSchema(unittest.TestCase):
    def test_demo_claims_validate(self):
        specs = claims.load_claims_file(DEMO_CLAIMS)
        self.assertEqual(len(specs), 2)
        for spec in specs:
            self.assertEqual(claims.validate_claim(spec), [])

    def test_hypothetical_needs_rationale(self):
        bad = {
            "claimId": "CL-BAD",
            "name": "Bad claim",
            "kind": "woningverdichting",
            "buurtcodes": ["BU07580000"],
            "magnitude": 2,
            "basis": {"type": "hypothetical"},
        }
        errs = claims.validate_claim(bad)
        self.assertTrue(errs)


class TestImpactRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = fixtures.layers_dict()
        cls.scan = indicators.compute_scan(cls.layers)
        cls.land = next(b for b in cls.scan["buurten"] if b["water"] == "NEE")

    def test_dak_pv_raises_economic(self):
        base = claims._score_map(self.land)
        scenario, flags, cap = claims.apply_claim_to_buurt(
            self.land, "dak_pv_maximalisatie", 4
        )
        self.assertIsNone(cap)
        self.assertIn("economic_up", flags)
        if base["economic"] is not None:
            self.assertGreater(scenario["economic"], base["economic"])

    def test_woning_pressure_and_tradeoffs(self):
        base = claims._score_map(self.land)
        scenario, flags, cap = claims.apply_claim_to_buurt(
            self.land, "woningverdichting", 3
        )
        self.assertEqual(cap, 30.0)
        self.assertIn("capacity_pressure", flags)
        self.assertIn("spatial_down", flags)
        self.assertIn("social_up_heat_attention", flags)
        if base["spatial"] is not None:
            self.assertLess(scenario["spatial"], base["spatial"])
        if base["social"] is not None:
            self.assertGreater(scenario["social"], base["social"])

    def test_deterministic(self):
        a, _, _ = claims.apply_claim_to_buurt(self.land, "woningverdichting", 2)
        b, _, _ = claims.apply_claim_to_buurt(self.land, "woningverdichting", 2)
        self.assertEqual(a, b)


class TestAfwegingRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = fixtures.layers_dict()
        cls.baseline = {
            "scan": {"scanId": "fixture"},
            "buurten": indicators.compute_scan(cls.layers)["buurten"],
        }
        cls.specs = claims.load_claims_file(DEMO_CLAIMS)

    def test_control_and_report_schema(self):
        report = claims.run_afweging(
            self.baseline,
            self.layers,
            self.specs,
            baseline_source="fixtures",
            generated_at="2026-10-04T12:00:00Z",
        )
        self.assertEqual(report["plane"], "D")
        self.assertEqual(report["decision"]["winnerClaimId"], None)
        self.assertEqual(report["validation"]["levels"]["V4"], "pending")
        self.assertEqual(report["validation"]["verdict"], "needs_human")
        self.assertEqual(claims.validate_report(report), [])
        ctrl = next(c for c in report["checks"] if c["id"] == "V3-control-identiteit")
        self.assertTrue(ctrl["ok"])

    def test_deltas_present_for_demo_claims(self):
        report = claims.run_afweging(
            self.baseline, self.layers, self.specs, baseline_source="fixtures"
        )
        accepted = [c for c in report["claims"] if not c.get("rejected")]
        self.assertEqual(len(accepted), 2)
        for claim in accepted:
            self.assertGreater(len(claim["buurten"]), 0)
            touched = [
                b for b in claim["buurten"] if "skipped_water" not in b["flags"]
            ]
            self.assertGreater(len(touched), 0)
            for b in touched:
                d = b["delta"]
                if claim["kind"] == "dak_pv_maximalisatie":
                    self.assertIsNotNone(d["economic"])
                    self.assertGreater(d["economic"], 0)
                if claim["kind"] == "woningverdichting":
                    self.assertIsNotNone(d["spatial"])
                    self.assertLess(d["spatial"], 0)
                    self.assertEqual(b["capacityPressure"], 30.0)

    def test_cli_offline_fixtures(self):
        import afweging_run

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "afw"
            rc = afweging_run.run(
                ["--offline-fixtures", "--claims", str(DEMO_CLAIMS), "--out", str(out)]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out / "gebiedsafweging-report.json").is_file())
            self.assertTrue((out / "gebiedsafweging.html").is_file())
            html = (out / "gebiedsafweging.html").read_text(encoding="utf-8")
            self.assertIn("Plane D", html)
            self.assertIn("CL-WONEN-NOORD", html)
            report = json.loads(
                (out / "gebiedsafweging-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["validation"]["levels"]["V4"], "pending")


if __name__ == "__main__":
    unittest.main()
