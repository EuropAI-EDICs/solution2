"""Offline tests for the Phase B GenAI seams (docs/GENAI_SEAMS.md S7/S8).

Run from the workspace root:

    python3 -m unittest poc.tests.test_scenario_author

The LLM author is tested through an injected fake transport — no network,
no endpoint. The deterministic author and the narration grounding gate are
exercised on synthetic fixtures plus the canonical run directories.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts, scenario_author, scenarios  # noqa: E402


def _fc(box, name):
    x0, y0, x1, y1 = box
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [{
            "type": "Feature", "id": 1, "properties": {},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]},
        }],
        "properties": {"sourceId": name},
    }


AOI_BOX = (150000, 455000, 160000, 465000)
EXCL_BOX = (152000, 457000, 154000, 459000)
CONTROL_KM2 = 96.0

LAYERS = {"incl": _fc(AOI_BOX, "incl"), "excl": _fc(EXCL_BOX, "excl"),
          "mark": _fc(EXCL_BOX, "mark")}


def _rule(rid, semantics, zone_ids, buffer_m=None, status="formalized", nc=None):
    zs = {"zoneIds": zone_ids, "geometrySource": "province_source"}
    if buffer_m is not None:
        zs["bufferDistanceM"] = buffer_m
    return {
        "id": rid, "normCardId": nc or f"NC-{rid.split('-', 1)[-1]}", "status": status,
        "ruleType": "designation_rule", "zoneSemantics": semantics,
        "appliesTo": {"objectType": "wind_turbine"},
        "executableRef": f"engine.zone.{semantics}@poc-v1",
        "formalizedBy": "test", "formalizedAt": "2026-08-31", "zoneSelector": zs,
    }


RULES = [
    _rule("FR-T-01", "inclusion", ["incl"]),
    _rule("FR-T-02", "exclusion", ["excl"]),
    _rule("FR-T-04", "attention", ["mark"], buffer_m=1500),
    _rule("FR-T-05", "conditional", ["mark"]),
    _rule("FR-T-06", "exclusion", ["excl"], status="ambiguous"),
    _rule("FR-T-07", "inclusion", ["incl"], buffer_m=1000),
]


def _baseline():
    request = {
        "id": "0d9f61aa-4b8e-4f2f-9f6a-6f21cb53d003",
        "objectType": "wind_turbine",
        "areaOfInterest": {"geometry": _fc(AOI_BOX, "aoi")["features"][0]["geometry"],
                           "crs": "EPSG:28992"},
        "policyStage": "programming",
        "effortBudget": {"maxSubagents": 1},
        "requestedAt": "2026-08-31T00:00:00Z",
    }
    contracts.validate(request, "opportunity-map-request")
    return {
        "runDir": Path("/tmp/unused"),
        "runId": "20260831T000000Z-test",
        "request": request,
        "formalrules": copy.deepcopy(RULES),
        "normcards": [{"id": "NC-T-01"}, {"id": "NC-T-02"}, {"id": "NC-T-04"},
                      {"id": "NC-T-05"}, {"id": "NC-T-06"}, {"id": "NC-T-07"}],
        "runSummary": {"runId": "20260831T000000Z-test",
                       "headline": {"finalOpportunityKm2": CONTROL_KM2}},
        "manifest": {},
        "inputSimplifyM": 0.0,
    }


# --------------------------------------------------------------------------- #
# deterministic author
# --------------------------------------------------------------------------- #

class DeterministicAuthorTests(unittest.TestCase):

    def setUp(self):
        self.author = scenario_author.DeterministicScenarioAuthor()
        self.baseline = _baseline()

    def test_proposal_shapes_follow_rule_shapes(self):
        specs, rejected = self.author.propose(self.baseline, max_scenarios=50)
        ids = {s["id"] for s in specs}
        # exclusion -> drop + hypothetical setback
        self.assertIn("SC-FR-T-02-DROP", ids)
        self.assertIn("SC-FR-T-02-SETBACK500", ids)
        # buffered marker -> hard + half/double enforced
        self.assertIn("SC-FR-T-04-HARD", ids)
        self.assertIn("SC-FR-T-04-HARD-HALF", ids)
        self.assertIn("SC-FR-T-04-HARD-DOUBLE", ids)
        # unbuffered marker -> hard only
        self.assertIn("SC-FR-T-05-HARD", ids)
        self.assertNotIn("SC-FR-T-05-HARD-HALF", ids)
        # buffered inclusion -> half/double
        self.assertIn("SC-FR-T-07-BUF-HALF", ids)
        self.assertIn("SC-FR-T-07-BUF-DOUBLE", ids)
        # ambiguous rule never proposed
        self.assertFalse([i for i in ids if "FR-T-06" in i])
        self.assertEqual(rejected, [])

    def test_all_proposals_schema_valid_and_grounded(self):
        specs, _ = self.author.propose(self.baseline, max_scenarios=50)
        rule_ids = {r["id"] for r in RULES}
        card_ids = {c["id"] for c in self.baseline["normcards"]}
        seen = set()
        for s in specs:
            contracts.validate(s, "scenario-spec")
            self.assertEqual(s["objectType"], "wind_turbine")
            self.assertEqual(s["proposedBy"], scenario_author.DETERMINISTIC_AUTHOR_RUN)
            self.assertNotIn(s["id"], seen)
            seen.add(s["id"])
            for m in s["mutations"]:
                self.assertIn(m["ruleId"], rule_ids)
            nc = s["basis"].get("normCardId")
            if nc:
                self.assertIn(nc, card_ids)

    def test_budget_cut_recorded(self):
        specs, rejected = self.author.propose(self.baseline, max_scenarios=2)
        self.assertEqual(len(specs), 2)
        self.assertTrue(all(r["kind"] == "budget-cut" for r in rejected))
        self.assertGreater(len(rejected), 0)

    def test_hypothetical_proposals_declare_their_lack_of_grounding(self):
        specs, _ = self.author.propose(self.baseline, max_scenarios=50)
        setback = next(s for s in specs if s["id"] == "SC-FR-T-02-SETBACK500")
        self.assertEqual(setback["basis"]["type"], "hypothetical")
        self.assertTrue(setback["basis"]["rationale"])
        self.assertIn("NOT legally grounded", setback["basis"]["provenanceNote"])

    def test_canonical_baselines_author_cleanly(self):
        for use_case, run_name in (("wind", "20260830T113234Z-wind"),
                                   ("zon", "20260830T142439Z-zon"),
                                   ("bos", "20260830T142446Z-bos")):
            with self.subTest(use_case=use_case):
                run_dir = POC_ROOT / "runs" / run_name
                if not (run_dir / "run_summary.json").is_file():
                    self.skipTest(f"canonical {use_case} run not present")
                baseline = scenarios.load_baseline(run_dir)
                specs, _ = self.author.propose(baseline, max_scenarios=25)
                self.assertGreaterEqual(len(specs), 2)
                for s in specs:
                    contracts.validate(s, "scenario-spec")


# --------------------------------------------------------------------------- #
# LLM author (fake transport; the seam contract)
# --------------------------------------------------------------------------- #

VALID_PROPOSAL = {
    "id": "SC-LLM-01",
    "name": "drop the exclusion",
    "objectType": "wind_turbine",
    "basis": {"type": "policy_variant", "normCardId": "NC-T-02",
              "provenanceNote": "flips the cited exclusion"},
    "mutations": [{"ruleId": "FR-T-02", "action": "drop"}],
}


def _fake_llm(response_json):
    def call(endpoint, model, system, user, timeout):
        return response_json
    return call


class LLMAuthorTests(unittest.TestCase):

    def setUp(self):
        self.baseline = _baseline()

    def _author(self, response):
        return scenario_author.LLMScenarioAuthor(
            endpoint="http://localhost:9999/v1", model="test-model",
            llm_call=_fake_llm(response))

    def test_endpoint_required(self):
        author = scenario_author.LLMScenarioAuthor(endpoint=None, model="m")
        # ensure env var does not leak from the host
        import os
        os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
        with self.assertRaises(scenario_author.ScenarioAuthorError):
            author.propose(self.baseline)

    def test_valid_proposal_accepted_and_identity_stamped(self):
        author = self._author(json.dumps([VALID_PROPOSAL]))
        specs, rejected = author.propose(self.baseline)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["proposedBy"], "llm-proposal#test-model")
        self.assertEqual(rejected, [])
        contracts.validate(specs[0], "scenario-spec")

    def test_model_supplied_identity_is_overwritten_and_recorded(self):
        proposal = dict(VALID_PROPOSAL, proposedBy="some-model-self-claim")
        author = self._author(json.dumps([proposal]))
        specs, _ = author.propose(self.baseline)
        self.assertEqual(specs[0]["proposedBy"], "llm-proposal#test-model")
        self.assertIn("some-model-self-claim", specs[0].get("notes", ""))

    def test_prose_wrapped_json_array_parses(self):
        author = self._author(
            "Here are my scenarios:\n```json\n" + json.dumps([VALID_PROPOSAL])
            + "\n```\nHope this helps!")
        specs, _ = author.propose(self.baseline)
        self.assertEqual(len(specs), 1)

    def test_schema_invalid_proposal_rejected_not_executed(self):
        bad = dict(VALID_PROPOSAL, basis={"type": "hypothetical",
                                          "provenanceNote": "no rationale given"})
        author = self._author(json.dumps([bad, VALID_PROPOSAL]))
        specs, rejected = author.propose(self.baseline)
        self.assertEqual(len(specs), 1)
        self.assertEqual(rejected[0]["kind"], "schema-invalid")

    def test_unknown_rule_and_normcard_rejected(self):
        ghost_rule = copy.deepcopy(VALID_PROPOSAL)
        ghost_rule["mutations"] = [{"ruleId": "FR-GHOST", "action": "drop"}]
        ghost_card = copy.deepcopy(VALID_PROPOSAL)
        ghost_card["id"] = "SC-LLM-02"
        ghost_card["basis"] = {"type": "policy_variant", "normCardId": "NC-GHOST",
                               "provenanceNote": "x"}
        author = self._author(json.dumps([ghost_rule, ghost_card]))
        specs, rejected = author.propose(self.baseline)
        self.assertEqual(specs, [])
        kinds = {r["kind"] for r in rejected}
        self.assertEqual(kinds, {"unknown-rule-id", "unknown-normcard-id"})

    def test_duplicate_ids_and_object_type_mismatch_rejected(self):
        dup = dict(VALID_PROPOSAL, id="SC-LLM-DUP")
        mismatch = dict(VALID_PROPOSAL, id="SC-LLM-03", objectType="solar_field")
        author = self._author(json.dumps([dup, dict(dup, name="second"), mismatch]))
        specs, rejected = author.propose(self.baseline)
        self.assertEqual([s["id"] for s in specs], ["SC-LLM-DUP"])
        kinds = [r["kind"] for r in rejected]
        self.assertIn("duplicate-id", kinds)
        self.assertIn("object-type-mismatch", kinds)

    def test_budget_cut_applies_to_llm_too(self):
        extra = [dict(VALID_PROPOSAL, id=f"SC-LLM-{i}") for i in range(2, 6)]
        author = self._author(json.dumps([VALID_PROPOSAL] + extra))
        specs, rejected = author.propose(self.baseline, max_scenarios=2)
        self.assertEqual(len(specs), 2)
        self.assertTrue(all(r["kind"] == "budget-cut" for r in rejected))

    def test_llm_authored_specs_run_end_to_end(self):
        author = self._author(json.dumps([VALID_PROPOSAL]))
        specs, _ = author.propose(self.baseline)
        report = scenarios.run_scenario_set(
            baseline=self.baseline, layers=LAYERS, specs=specs,
            scenario_set_id="SSET-llm-test", report_id="SR-llm-test")
        report.pop("_validation")
        report.pop("_control_rich")
        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["scenarios"][0]["proposedBy"], "llm-proposal#test-model")
        self.assertAlmostEqual(report["scenarios"][0]["finalAreaKm2"], 100.0, places=6)

    def test_digest_contains_only_verbatim_ids(self):
        digest = scenario_author.build_llm_digest(self.baseline, 5)
        self.assertEqual(digest["objectType"], "wind_turbine")
        self.assertEqual(digest["maxScenarios"], 5)
        digested_rules = {r["ruleId"] for r in digest["formalizedRules"]}
        self.assertEqual(digested_rules, {"FR-T-01", "FR-T-02", "FR-T-04", "FR-T-05",
                                          "FR-T-07"})


# --------------------------------------------------------------------------- #
# narration seam (S8)
# --------------------------------------------------------------------------- #

class NarrationTests(unittest.TestCase):

    def _report(self):
        specs = [scenario_author.DeterministicScenarioAuthor().propose(_baseline(), 1)[0][0]]
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=specs,
            scenario_set_id="SSET-test", report_id="SR-narr-test")
        report.pop("_validation")
        report.pop("_control_rich")
        return report

    def test_deterministic_narrative_passes_its_own_gate(self):
        report = self._report()
        narrative = scenarios.deterministic_narrative(report)
        check = scenarios.check_narrative_grounding(narrative, report)
        self.assertEqual(check["status"], "pass", check["detail"])

    def test_fabricated_number_fails_the_gate(self):
        report = self._report()
        bad = scenarios.deterministic_narrative(report)
        bad = bad.replace(f"{report['scenarios'][0]['finalAreaKm2']:,.3f}", "999.999")
        check = scenarios.check_narrative_grounding(bad, report)
        self.assertEqual(check["status"], "fail")
        self.assertIn("999.999", check["detail"])

    def test_fabricated_scenario_id_fails_the_gate(self):
        report = self._report()
        bad = scenarios.deterministic_narrative(report).replace(
            report["scenarios"][0]["scenarioId"], "SC-FABRICATED-99")
        check = scenarios.check_narrative_grounding(bad, report)
        self.assertEqual(check["status"], "fail")
        self.assertIn("SC-FABRICATED-99", check["detail"])

    def test_narrator_runs_inside_the_sweep_and_gates_v2(self):
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=scenario_author.DeterministicScenarioAuthor().propose(_baseline(), 1)[0],
            scenario_set_id="SSET-test", report_id="SR-narr-in",
            narrator=scenarios.deterministic_narrative)
        validation = report.pop("_validation")
        report.pop("_control_rich")
        narrative = report.pop("_narrative")
        self.assertTrue(narrative)
        v2 = validation["levels"]["V2"]
        self.assertEqual(v2["status"], "pass")
        self.assertIn("v2-narrative-grounding",
                      [c["id"] for c in v2["checks"]])

    def test_rejected_narration_fails_the_verdict(self):
        report_holder = {}

        def lying_narrator(report):
            report_holder["report"] = {k: v for k, v in report.items()}
            return (scenarios.deterministic_narrative(report)
                    + "\n\nActually the zone is 12345.678 km2.")

        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=scenario_author.DeterministicScenarioAuthor().propose(_baseline(), 1)[0],
            scenario_set_id="SSET-test", report_id="SR-narr-bad",
            narrator=lying_narrator)
        validation = report.pop("_validation")
        self.assertEqual(report["verdict"], "fail")
        self.assertEqual(validation["levels"]["V2"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
# B2 additions: robust extraction, LLM narrator, loud fallback
# --------------------------------------------------------------------------- #

class RobustExtractionTests(unittest.TestCase):

    def test_think_block_stripped_before_parsing(self):
        raw = ("<think>The user wants scenarios. I will pick rule FR-T-02.</think>\n"
               + json.dumps([VALID_PROPOSAL]))
        author = scenario_author.LLMScenarioAuthor(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(raw))
        specs, _ = author.propose(_baseline())
        self.assertEqual(len(specs), 1)

    def test_fenced_json_block_preferred(self):
        raw = ("Sure! Here you go:\n```json\n" + json.dumps([VALID_PROPOSAL])
               + "\n```\nAnything else?")
        author = scenario_author.LLMScenarioAuthor(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(raw))
        specs, _ = author.propose(_baseline())
        self.assertEqual(len(specs), 1)

    def test_think_block_with_brackets_does_not_confuse_extraction(self):
        raw = ("<think>maybe [a, list, here]?</think>" + json.dumps([VALID_PROPOSAL]))
        author = scenario_author.LLMScenarioAuthor(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(raw))
        specs, _ = author.propose(_baseline())
        self.assertEqual(len(specs), 1)

    def test_garbage_raises_author_error(self):
        author = scenario_author.LLMScenarioAuthor(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm("no json here at all"))
        with self.assertRaises(scenario_author.ScenarioAuthorError):
            author.propose(_baseline())


class LLMNarratorTests(unittest.TestCase):

    def _report(self):
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=[{**VALID_PROPOSAL, "proposedBy": "llm-proposal#test-model"}],
            scenario_set_id="SSET-test", report_id="SR-nar")
        report.pop("_validation")
        report.pop("_control_rich")
        return report

    def test_narrator_requires_endpoint(self):
        import os
        os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
        narrator = scenario_author.LLMScenarioNarrator()
        with self.assertRaises(scenario_author.ScenarioAuthorError):
            narrator(self._report())

    def test_grounded_llm_prose_passes_the_gate(self):
        report = self._report()
        row = report["scenarios"][0]
        prose = (f"Scenario {row['scenarioId']} moves the zone to "
                 f"{row['finalAreaKm2']:,.3f} km2, a change of "
                 f"{row['deltaVsControlKm2']:+,.3f} km2 "
                 f"({row['deltaVsControlPct']:+.2f}%).")
        narrator = scenario_author.LLMScenarioNarrator(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(prose))
        text = narrator(report)
        check = scenarios.check_narrative_grounding(text, report)
        self.assertEqual(check["status"], "pass", check["detail"])

    def test_fallback_wrapper_publishes_deterministic_on_rejection(self):
        report = self._report()
        lying = "The zone becomes 99999.5 km2 under SC-FABRICATED-1, clearly."
        narrator = scenario_author.LLMScenarioNarrator(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(lying))
        events: list = []
        wrapped = scenario_author.make_fallback_narrator(
            narrator, scenarios.deterministic_narrative, events)
        text = wrapped(report)
        # published prose is the deterministic fallback (grounded by construction)
        self.assertEqual(text, scenarios.deterministic_narrative(report))
        self.assertEqual(len(events), 1)
        self.assertIn("99999.5", events[0]["reason"])
        self.assertEqual(events[0]["kind"], "narrative-grounding-rejected")
        self.assertIn(lying, events[0]["prose"])

    def test_fallback_wrapper_publishes_model_prose_when_grounded(self):
        report = self._report()
        row = report["scenarios"][0]
        good = (f"Scenario {row['scenarioId']} shifts the zone by "
                f"{row['deltaVsControlKm2']:+,.3f} km2 to {row['finalAreaKm2']:,.3f} km2.")
        narrator = scenario_author.LLMScenarioNarrator(
            endpoint="http://x/v1", model="m", llm_call=_fake_llm(good))
        events: list = []
        wrapped = scenario_author.make_fallback_narrator(
            narrator, scenarios.deterministic_narrative, events)
        self.assertEqual(wrapped(report), good)
        self.assertEqual(events, [])

    def test_transport_error_falls_back_with_event(self):
        def boom(endpoint, model, system, user, timeout):
            raise RuntimeError("connection refused")
        narrator = scenario_author.LLMScenarioNarrator(
            endpoint="http://x/v1", model="m", llm_call=boom)
        events: list = []
        wrapped = scenario_author.make_fallback_narrator(
            narrator, scenarios.deterministic_narrative, events)
        text = wrapped(self._report())
        self.assertTrue(text)
        self.assertEqual(events[0]["kind"], "narrator-error")
        self.assertIsNone(events[0]["prose"])


# --------------------------------------------------------------------------- #
# hybrid author (det floor + LLM explorer)
# --------------------------------------------------------------------------- #

class HybridAuthorTests(unittest.TestCase):

    def setUp(self):
        self.baseline = _baseline()

    def _hybrid(self, response, endpoint="http://localhost:9999/v1"):
        return scenario_author.HybridScenarioAuthor(
            endpoint=endpoint, model="test-model",
            llm_call=_fake_llm(response))

    def test_dedupe_key_stable_for_same_mutations(self):
        a = dict(VALID_PROPOSAL)
        b = dict(VALID_PROPOSAL, id="other", name="x")
        self.assertEqual(
            scenario_author.mutation_dedupe_key(a),
            scenario_author.mutation_dedupe_key(b))

    def test_floor_then_explorer_respects_budget(self):
        novel = {
            "id": "SC-LLM-NOVEL",
            "name": "novel buffer",
            "objectType": "wind_turbine",
            "basis": {"type": "norm_variance", "normCardId": "NC-T-07",
                      "variedAspect": "buffer 1000->750",
                      "provenanceNote": "explorer"},
            "mutations": [{"ruleId": "FR-T-07", "action": "set_buffer_distance_m",
                           "bufferDistanceM": 750}],
        }
        author = self._hybrid(json.dumps([VALID_PROPOSAL, novel]))
        specs, rejected = author.propose(self.baseline, max_scenarios=3)
        self.assertEqual(len(specs), 3)
        self.assertTrue(all(
            s["proposedBy"] == scenario_author.AUTHOR_DETERMINISTIC for s in specs))
        specs2, rej2 = author.propose(self.baseline, max_scenarios=50)
        ids = {s["id"] for s in specs2}
        self.assertIn("SC-LLM-NOVEL", ids)
        supersede = [r for r in rej2 if r.get("kind") == "superseded-by-deterministic"]
        self.assertTrue(any(r.get("specId") == "SC-LLM-01" for r in supersede))

    def test_hybrid_without_endpoint_falls_back_to_det(self):
        import os
        os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
        author = scenario_author.HybridScenarioAuthor(
            endpoint="", model="m", llm_call=_fake_llm("[]"))
        specs, rejected = author.propose(self.baseline, max_scenarios=5)
        det_specs, _ = scenario_author.DeterministicScenarioAuthor().propose(
            self.baseline, max_scenarios=5)
        self.assertEqual([s["id"] for s in specs], [s["id"] for s in det_specs])
        self.assertTrue(any(r.get("kind") == "llm-unavailable" for r in rejected))

    def test_floor_invariant_rule_ids(self):
        novel = {
            "id": "SC-LLM-NOVEL2",
            "name": "novel",
            "objectType": "wind_turbine",
            "basis": {"type": "hypothetical", "rationale": "stress",
                      "provenanceNote": "x"},
            "mutations": [{"ruleId": "FR-T-05", "action": "set_buffer_distance_m",
                           "bufferDistanceM": 42}],
        }
        author = self._hybrid(json.dumps([novel]))
        hyb, _ = author.propose(self.baseline, max_scenarios=20)
        det, _ = scenario_author.DeterministicScenarioAuthor().propose(
            self.baseline, max_scenarios=20)
        det_rules = {m["ruleId"] for s in det for m in s["mutations"]}
        hyb_rules = {m["ruleId"] for s in hyb for m in s["mutations"]}
        self.assertTrue(det_rules <= hyb_rules)
