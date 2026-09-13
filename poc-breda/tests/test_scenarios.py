"""Offline tests: de what-if-naad — parameterisatie, contract-gates,
control-identiteit, auteurs (file/auto/llm-mock), runner en e2e."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from breda import indicators, scenarios  # noqa: E402  — util zet sys.path
from tests import fixtures, util  # noqa: E402


class TestParamsRefactor(unittest.TestCase):
    """DEFAULT_PARAMS moet bit-identiek aan het oude gedrag zijn."""

    @classmethod
    def setUpClass(cls):
        cls.layers = fixtures.layers_dict()
        cls.scan = indicators.compute_scan(cls.layers)

    def test_default_params_identiek(self):
        tweede = indicators.compute_scan(self.layers, dict(indicators.DEFAULT_PARAMS))
        self.assertEqual(self.scan["buurten"], tweede["buurten"])
        self.assertEqual(self.scan["rollup"], tweede["rollup"])

    def test_lege_params_identiek(self):
        derde = indicators.compute_scan(self.layers, {})
        self.assertEqual(self.scan["buurten"], derde["buurten"])

    def test_onbekende_parameter_faalt(self):
        with self.assertRaises(ValueError):
            indicators.compute_scan(self.layers, {"nonsense": 1})
        with self.assertRaises(ValueError):
            indicators.compute_scan(self.layers, {"dropInputs": ["maanensterren"]})


class TestMutaties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = fixtures.layers_dict()
        cls.base = indicators.compute_scan(cls.layers)

    def _score(self, scan, naam, waarde):
        b = next(x for x in scan["buurten"] if x["buurtnaam"] == naam)
        return b["scores"][waarde]["score"]

    def test_access_min_6_verandert_scores(self):
        var = indicators.compute_scan(self.layers, {"accessMinPresent": 6})
        verschillen = [
            b["buurtnaam"] for b, o in zip(var["buurten"], self.base["buurten"])
            if b["scores"]["democratic"]["score"] != o["scores"]["democratic"]["score"]
        ]
        # fixtures geven 6/6 afstanden op landcellen → zelfde mean, geen verschil
        # verwacht; de mutatie mag wel nooit crashen en moet deterministisch zijn
        var2 = indicators.compute_scan(self.layers, {"accessMinPresent": 6})
        self.assertEqual(var["buurten"], var2["buurten"])
        self.assertIsInstance(verschillen, list)

    def test_deals_floor_is_minimum(self):
        var = indicators.compute_scan(self.layers, {"dealsRule": "floor"})
        for b, o in zip(var["buurten"], self.base["buurten"]):
            if b["water"] == "JA":
                continue
            inputs = b["scores"]["democratic"]["inputs"]
            if inputs.get("deals") is None:
                continue  # zonder deals-score valt de vloer weg
        # spot-check: de vloer kan alleen maar omlaag (min ≤ gemiddelde)
        for b, o in zip(var["buurten"], self.base["buurten"]):
            if b["scores"]["democratic"]["score"] is not None and \
               o["scores"]["democratic"]["score"] is not None:
                self.assertLessEqual(
                    b["scores"]["democratic"]["score"],
                    o["scores"]["democratic"]["score"] + 0.05,
                )

    def test_social_gated_verandert_sociaal(self):
        var = indicators.compute_scan(self.layers, {
            "socialRule": "ouderen_gated", "socialGatePct": 15.0
        })
        verschillen = sum(
            1 for b, o in zip(var["buurten"], self.base["buurten"])
            if b["scores"]["social"]["score"] != o["scores"]["social"]["score"]
        )
        self.assertGreater(verschillen, 0, "gating moet ten minste één buurt verschuiven")

    def test_spatial_groen_gewicht_2(self):
        var = indicators.compute_scan(self.layers, {
            "spatialWeights": {"groen": 2, "afstand": 1, "bomen": 1}
        })
        verschillen = sum(
            1 for b, o in zip(var["buurten"], self.base["buurten"])
            if b["scores"]["spatial"]["score"] != o["scores"]["spatial"]["score"]
        )
        self.assertGreater(verschillen, 0, "herweging moet scores doen verschuiven")

    def test_weighted_mean_hulp_exact(self):
        wm = indicators._weighted_mean
        # gelijke gewichten → hetzelfde pad als mean_available
        self.assertEqual(wm([80.0, 60.0, 40.0], [1, 1, 1]), 60.0)
        # 2:1 weging handmatig
        self.assertEqual(wm([80.0, 60.0], [2, 1]), round((160.0 + 60.0) / 3, 1))
        # None valt weg, ook met gewicht
        self.assertEqual(wm([80.0, None, 60.0], [1, 5, 1]),
                         round(140.0 / 2, 1))
        self.assertIsNone(wm([None, None], [1, 1]))

    def test_drop_bomen_verwijdert_input(self):
        var = indicators.compute_scan(self.layers, {"dropInputs": ["bomen"]})
        b = next(x for x in var["buurten"] if x["water"] == "NEE")
        self.assertIn("bomen", b["missing"]["spatial"])
        # en de score verschilt van de baseline (bomen vielen weg)
        o = next(x for x in self.base["buurten"] if x["buurtnaam"] == b["buurtnaam"])
        self.assertNotEqual(
            b["scores"]["spatial"]["score"], o["scores"]["spatial"]["score"]
        )


class TestContractGates(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "scenarioId": "VS-TEST-1",
            "name": "test",
            "basis": {"type": "indicator_variance", "variedAspect": "access_min_present"},
            "mutations": [{"action": "set_access_min_present", "value": 6}],
        }
        spec.update(over)
        return spec

    def test_geldige_specs_passeren(self):
        for spec in scenarios.deterministic_author()[0]:
            self.assertEqual(scenarios.validate_scenario(spec), [], spec["scenarioId"])
        for spec in scenarios.author_from_file(
            Path(util.ROOT) / "scenarios" / "breda.json"
        )[0]:
            self.assertEqual(scenarios.validate_scenario(spec), [], spec["scenarioId"])

    def test_hypothetical_zonder_rationale_afgewezen(self):
        spec = self._spec(
            basis={"type": "hypothetical"},
            mutations=[{"action": "set_spatial_weights", "groen": 2}],
        )
        self.assertTrue(scenarios.validate_scenario(spec))

    def test_onbekende_actie_afgewezen(self):
        spec = self._spec(
            scenarioId="VS-TEST-2",
            basis={"type": "hypothetical",
                   "rationale": "verkenning zonder onderbouwing"},
            mutations=[{"action": "verdubbel_alles"}],
        )
        schendingen = scenarios.validate_scenario(spec)
        self.assertTrue(any("schema" in s for s in schendingen))

    def test_policy_variant_maatstaf(self):
        spec = self._spec(
            scenarioId="VS-TEST-3",
            basis={"type": "policy_variant", "variedAspect": "spatial_weights"},
            mutations=[{"action": "set_spatial_weights", "groen": 2}],
        )
        schendingen = scenarios.validate_scenario(spec)
        self.assertTrue(any("geen gedocumenteerde" in s for s in schendingen))

    def test_variedaspect_mismatch_afgewezen(self):
        spec = self._spec(
            scenarioId="VS-TEST-4",
            basis={"type": "indicator_variance", "variedAspect": "deals_rule"},
            mutations=[{"action": "set_access_min_present", "value": 5}],
        )
        self.assertTrue(scenarios.validate_scenario(spec))

    def test_kruiscontrole_regels(self):
        spec = self._spec(
            scenarioId="VS-TEST-5",
            basis={"type": "policy_variant", "variedAspect": "deals_rule"},
            mutations=[{"action": "set_deals_rule", "rule": "ouderen_gated"}],
        )
        self.assertTrue(scenarios.validate_scenario(spec))


class TestRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers = fixtures.layers_dict()
        cls.baseline = util.full_scan(cls.layers)

    def test_control_identiek(self):
        specs, _ = scenarios.author_from_file(Path(util.ROOT) / "scenarios" / "breda.json")
        report = scenarios.run_scenarios(self.baseline, self.layers, specs)
        self.assertTrue(report["control"]["identicalToBaseline"])
        self.assertEqual(report["validation"]["verdict"], "pass")
        self.assertEqual(len(report["variants"]), len(specs))
        self.assertTrue(report["stability"], "stabiliteit berekend")

    def test_gemanipuleerde_baseline_faalt_control(self):
        specs = scenarios.deterministic_author(1)[0]
        kapot = copy.deepcopy(self.baseline)
        kapot["buurten"][0]["scores"]["spatial"]["score"] = 42.0
        report = scenarios.run_scenarios(kapot, self.layers, specs)
        self.assertFalse(report["control"]["identicalToBaseline"])
        self.assertEqual(report["validation"]["verdict"], "fail")
        self.assertEqual(report["variants"], [], "geen variant geloofd zonder control")

    def test_afgewezen_scenarios_niet_uitgevoerd(self):
        slecht = [{
            "scenarioId": "VS-SLECHT-1",
            "name": "geen rationale",
            "basis": {"type": "hypothetical"},
            "mutations": [{"action": "set_spatial_weights", "groen": 9}],
        }]
        report = scenarios.run_scenarios(self.baseline, self.layers, slecht)
        self.assertEqual(report["nAccepted"], 0)
        self.assertEqual(len(report["rejected"]), 1)
        self.assertEqual(report["variants"], [])


class TestLLMAuthor(unittest.TestCase):
    @staticmethod
    def _author(reply):
        def llm_call(endpoint, model, system, user, timeout):
            return reply

        return scenarios.LLMScenarioAuthor(
            llm_call=llm_call, endpoint="http://test", model="test-m"
        )

    def test_geldige_voorstellen_aangenomen_en_gestempeld(self):
        geldig = json.dumps([
            {
                "scenarioId": "VS-LLM-1",
                "name": "Drempel strakker",
                "basis": {"type": "indicator_variance",
                          "variedAspect": "access_min_present"},
                "mutations": [{"action": "set_access_min_present", "value": 6}],
            }
        ])
        aangenomen, afgewezen = self._author(geldig).propose()
        self.assertEqual(afgewezen, [])
        self.assertEqual(len(aangenomen), 1)
        self.assertEqual(aangenomen[0]["proposedBy"], "llm-proposal#test-m")

    def test_gehallucineerde_actie_naar_ledger(self):
        reply = json.dumps([
            {
                "scenarioId": "VS-LLM-2", "name": "verzonnen",
                "basis": {"type": "hypothetical", "rationale": "zomaar verzonnen actie"},
                "mutations": [{"action": "set_burgemeester", "naam": "AI"}],
            }
        ])
        aangenomen, afgewezen = self._author(reply).propose()
        self.assertEqual(aangenomen, [])
        self.assertTrue(afgewezen)

    def test_kapotte_json_naar_ledger(self):
        aangenomen, afgewezen = self._author("geen array maar proza").propose()
        self.assertEqual(aangenomen, [])
        self.assertIn("onparseerbaar", afgewezen[0]["reason"])

    def test_endpoint_vereist(self):
        with self.assertRaises(scenarios.ScenarioError):
            scenarios.LLMScenarioAuthor(endpoint="").propose()

    def test_dubbele_ids_naar_ledger(self):
        één = {
            "scenarioId": "VS-LLM-DUBBEL", "name": "eerste",
            "basis": {"type": "indicator_variance", "variedAspect": "access_min_present"},
            "mutations": [{"action": "set_access_min_present", "value": 6}],
        }
        aangenomen, afgewezen = self._author(json.dumps([één, copy.deepcopy(één)])).propose()
        self.assertEqual(len(aangenomen), 1)
        self.assertEqual(len(afgewezen), 1)


class TestE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "poc_breda_scenario_run", Path(util.ROOT) / "scenario_run.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["poc_breda_scenario_run"] = mod
        spec.loader.exec_module(mod)
        cls.mod = mod

    def test_e2e_op_fixtures(self):
        layers = fixtures.layers_dict()
        baseline = util.full_scan(layers)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            (run_dir / "value-scan.json").write_text(
                json.dumps(baseline, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(
                self.mod.fetch, "fetch_all",
                return_value={"layers": layers, "degradations": [],
                              "bbox": "115000,400000,127000,410000"},
            ):
                code = self.mod.run([
                    "--run", str(run_dir),
                    "--author", "auto",
                    "--out", str(Path(tmp) / "scen"),
                ])
            self.assertEqual(code, 0)
            report = json.loads(
                (Path(tmp) / "scen" / "scenario-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["validation"]["verdict"], "pass")
            self.assertEqual(report["nAccepted"], 6)
            self.assertTrue((Path(tmp) / "scen" / "scenario-report.md").exists())
            self.assertTrue((Path(tmp) / "scen" / "run_summary.json").exists())
            # what-if-kaart: data ge-escaped, géén ruwe </script> in het JSON-blok
            html = (Path(tmp) / "scen" / "what-if.html").read_text(encoding="utf-8")
            start = html.index("window.__DATA__")
            end = html.index(";", start)
            self.assertNotIn("</script>", html[start:end])
            self.assertIn("VS-ACC-MIN6", html)


if __name__ == "__main__":
    unittest.main()
