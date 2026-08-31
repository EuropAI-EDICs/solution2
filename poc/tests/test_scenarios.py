"""Offline tests for the Phase A scenario engine (docs/GENAI_SEAMS.md).

Run from the workspace root:

    python3 -m unittest discover -s poc/tests

All tests are offline and deterministic. The real-cache end-to-end test
replays the canonical zon run from poc/data/cache (no network) in ~6 s.
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

from pipeline import contracts, scenarios  # noqa: E402


def _fc(square_km_box, name):
    """Tiny EPSG:28992 FeatureCollection with one rectangular polygon."""
    x0, y0, x1, y1 = square_km_box
    poly = {
        "type": "Polygon",
        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
    }
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [{"type": "Feature", "id": 1, "properties": {}, "geometry": poly}],
        "properties": {"sourceId": name},
    }


# 10 x 10 km AOI / inclusion layer, 2 x 2 km exclusion layer inside it
AOI_BOX = (150000, 455000, 160000, 465000)
INCL_BOX = (150000, 455000, 160000, 465000)
EXCL_BOX = (152000, 457000, 154000, 459000)

CONTROL_KM2 = 100.0 - 4.0  # inclusion minus the exclusion
DROP_KM2 = 100.0           # exclusion dropped
BUFFER_KM2 = 100.0 - 16.0  # exclusion buffered by 1 km (4 km2 -> 16 km2)
MARKER_KM2 = 100.0         # exclusion reclassified as attention marker


def _rule(rid, semantics, zone_ids, buffer_m=None, status="formalized", nc=None):
    zs = {"zoneIds": zone_ids, "geometrySource": "province_source"}
    if buffer_m is not None:
        zs["bufferDistanceM"] = buffer_m
    return {
        "id": rid,
        "normCardId": nc or f"NC-{rid.split('-', 1)[-1]}",
        "status": status,
        "ruleType": "designation_rule",
        "zoneSemantics": semantics,
        "appliesTo": {"objectType": "wind_turbine"},
        "executableRef": f"engine.zone.{semantics}@poc-v1",
        "formalizedBy": "test",
        "formalizedAt": "2026-08-31",
        "zoneSelector": zs,
    }


RULES = [
    _rule("FR-T-01", "inclusion", ["incl"]),
    _rule("FR-T-02", "exclusion", ["excl"]),
    _rule("FR-T-03", "attention", ["excl"], status="ambiguous"),
]

LAYERS = {"incl": _fc(INCL_BOX, "incl"), "excl": _fc(EXCL_BOX, "excl")}


def _spec(sid, basis, mutations):
    payload = {
        "id": sid,
        "name": f"test {sid}",
        "objectType": "wind_turbine",
        "basis": basis,
        "mutations": mutations,
        "proposedBy": "deterministic-scenario-author#poc-v0",
    }
    return contracts.ScenarioSpec.from_dict(payload).to_dict()


def _baseline(final_km2=CONTROL_KM2):
    request = {
        "id": "0d9f61aa-4b8e-4f2f-9f6a-6f21cb53d002",
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
        "normcards": [{"id": "NC-01"}, {"id": "NC-02"}, {"id": "NC-03"},
                      {"id": "NC-W-10"}],
        "runSummary": {"runId": "20260831T000000Z-test",
                       "headline": {"finalOpportunityKm2": final_km2,
                                    "inclusionIntersectAoiKm2": 100.0}},
        "manifest": {},
        "inputSimplifyM": 0.0,  # tiny fixtures: no simplification
    }


class ScenarioSchemaTests(unittest.TestCase):
    """V0 gate: the three new schemas + conditional basis/mutation rules."""

    def test_new_schemas_meta_validate(self):
        for name in ("scenario-spec", "scenario-set", "scenario-report"):
            schema = contracts.load_schema(name)
            self.assertEqual(schema["$schema"],
                             "https://json-schema.org/draft/2020-12/schema")

    def test_hypothetical_requires_rationale(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "hypothetical", "provenanceNote": "n"},
                 "mutations": [], "proposedBy": "a#b"},
                "scenario-spec")

    def test_norm_variance_requires_normcard_and_aspect(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "norm_variance", "provenanceNote": "n"},
                 "mutations": [], "proposedBy": "a#b"},
                "scenario-spec")

    def test_policy_variant_requires_normcard(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "policy_variant", "provenanceNote": "n"},
                 "mutations": [], "proposedBy": "a#b"},
                "scenario-spec")

    def test_set_semantics_mutation_requires_value(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "hypothetical", "rationale": "r",
                           "provenanceNote": "n"},
                 "mutations": [{"ruleId": "FR-T-02", "action": "set_semantics"}],
                 "proposedBy": "a#b"},
                "scenario-spec")

    def test_set_buffer_mutation_requires_value(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "hypothetical", "rationale": "r",
                           "provenanceNote": "n"},
                 "mutations": [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m"}],
                 "proposedBy": "a#b"},
                "scenario-spec")

    def test_proposed_by_must_be_agent_run_form(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate(
                {"id": "SC-X", "name": "x", "objectType": "wind_turbine",
                 "basis": {"type": "hypothetical", "rationale": "r",
                           "provenanceNote": "n"},
                 "mutations": [], "proposedBy": "not a valid agent ref!"},
                "scenario-spec")

    def test_spec_dataclass_round_trip(self):
        spec = contracts.ScenarioSpec.from_dict(_spec(
            "SC-T-01",
            {"type": "norm_variance", "normCardId": "NC-02",
             "variedAspect": "buffer 0->1000", "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m",
              "bufferDistanceM": 1000}]))
        self.assertEqual(spec.basis.normCardId, "NC-02")
        contracts.validate(spec.to_dict(), "scenario-spec")


class MutationTests(unittest.TestCase):
    """apply_mutations: applied / skipped / unknown, never guessed."""

    def test_drop_marks_rule_rejected(self):
        new, applied, skipped, unknown = scenarios.apply_mutations(
            RULES, [{"ruleId": "FR-T-02", "action": "drop"}])
        rule = next(r for r in new if r["id"] == "FR-T-02")
        self.assertEqual(rule["status"], "rejected")
        self.assertEqual(len(applied), 1)
        self.assertEqual(skipped, [])
        self.assertEqual(unknown, [])

    def test_set_semantics_and_buffer(self):
        new, applied, _, _ = scenarios.apply_mutations(RULES, [
            {"ruleId": "FR-T-02", "action": "set_semantics", "zoneSemantics": "attention"},
            {"ruleId": "FR-T-01", "action": "set_buffer_distance_m", "bufferDistanceM": 250},
        ])
        r2 = next(r for r in new if r["id"] == "FR-T-02")
        r1 = next(r for r in new if r["id"] == "FR-T-01")
        self.assertEqual(r2["zoneSemantics"], "attention")
        self.assertEqual(r1["zoneSelector"]["bufferDistanceM"], 250)
        self.assertEqual(len(applied), 2)

    def test_ambiguous_rule_is_skipped_with_reason(self):
        _, applied, skipped, unknown = scenarios.apply_mutations(
            RULES, [{"ruleId": "FR-T-03", "action": "drop"}])
        self.assertEqual(applied, [])
        self.assertEqual(len(skipped), 1)
        self.assertIn("ambiguous", skipped[0]["reason"])
        self.assertEqual(unknown, [])

    def test_unknown_rule_id_is_an_authoring_error(self):
        _, applied, skipped, unknown = scenarios.apply_mutations(
            RULES, [{"ruleId": "FR-GHOST", "action": "drop"}])
        self.assertEqual(applied, [])
        self.assertEqual(unknown, ["FR-GHOST"])
        self.assertIn("unknown rule id", skipped[0]["reason"])

    def test_original_rules_are_never_mutated_in_place(self):
        before = copy.deepcopy(RULES)
        scenarios.apply_mutations(RULES, [
            {"ruleId": "FR-T-02", "action": "set_buffer_distance_m", "bufferDistanceM": 10}])
        self.assertEqual(RULES, before)

    def test_buffer_without_zoneselector_skipped(self):
        rules = [_rule("FR-T-09", "exclusion", ["excl"])]
        rules[0].pop("zoneSelector")
        _, applied, skipped, _ = scenarios.apply_mutations(
            rules, [{"ruleId": "FR-T-09", "action": "set_buffer_distance_m",
                     "bufferDistanceM": 10}])
        self.assertEqual(applied, [])
        self.assertIn("no zoneSelector", skipped[0]["reason"])


class ScenarioSweepTests(unittest.TestCase):
    """Synthetic end-to-end sweep over tiny square layers (offline)."""

    def _run(self, specs, **kw):
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=specs,
            scenario_set_id="SSET-test", report_id="SR-test-0001", **kw)
        # consume the internal transport keys exactly like the CLI does
        self.last_validation = report.pop("_validation")
        report.pop("_control_rich")
        return report

    def test_control_reproduces_baseline(self):
        report = self._run([])
        self.assertAlmostEqual(report["control"]["finalAreaKm2"], CONTROL_KM2, places=6)
        self.assertTrue(report["control"]["reproductionWithinTolerance"])
        self.assertEqual(report["verdict"], "pass")
        contracts.validate(report, "scenario-report")

    def test_drop_exclusion_grows_zone(self):
        report = self._run([_spec(
            "SC-T-DROP",
            {"type": "policy_variant", "normCardId": "NC-02",
             "provenanceNote": "discretionary exception granted"},
            [{"ruleId": "FR-T-02", "action": "drop"}])])
        row = report["scenarios"][0]
        self.assertAlmostEqual(row["finalAreaKm2"], DROP_KM2, places=6)
        self.assertAlmostEqual(row["deltaVsControlKm2"], DROP_KM2 - CONTROL_KM2, places=6)
        self.assertAlmostEqual(row["iouVsControl"], CONTROL_KM2 / DROP_KM2, places=6)
        self.assertEqual(row["status"], "ok")

    def test_buffered_exclusion_shrinks_zone(self):
        report = self._run([_spec(
            "SC-T-BUF",
            {"type": "norm_variance", "normCardId": "NC-02",
             "variedAspect": "buffer 0 -> 1000 m", "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m",
              "bufferDistanceM": 1000}])])
        row = report["scenarios"][0]
        # engine buffers are polygonal approximations (quad_segs=16): the
        # exact 16 km2 ring lands at ~15.14 km2 on this fixture
        self.assertAlmostEqual(row["finalAreaKm2"], BUFFER_KM2, delta=1.0)
        self.assertLess(row["finalAreaKm2"], CONTROL_KM2)

    def test_marker_reclassification_restores_full_inclusion(self):
        report = self._run([_spec(
            "SC-T-MARK",
            {"type": "policy_variant", "normCardId": "NC-02", "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "set_semantics",
              "zoneSemantics": "attention"}])])
        row = report["scenarios"][0]
        self.assertAlmostEqual(row["finalAreaKm2"], MARKER_KM2, places=6)

    def test_unknown_rule_id_fails_v2_and_verdict(self):
        report = self._run([_spec(
            "SC-T-GHOST",
            {"type": "hypothetical", "rationale": "r", "provenanceNote": "n"},
            [{"ruleId": "FR-GHOST", "action": "drop"}])])
        self.assertEqual(report["verdict"], "fail")
        v2 = self.last_validation["levels"]["V2"]
        self.assertEqual(v2["status"], "fail")
        self.assertIn("FR-GHOST", json.dumps(v2))

    def test_unresolved_normcard_fails_v2(self):
        report = self._run([_spec(
            "SC-T-NC",
            {"type": "policy_variant", "normCardId": "NC-GHOST",
             "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "drop"}])])
        self.assertEqual(report["verdict"], "fail")
        self.assertIn("NC-GHOST",
                      json.dumps(self.last_validation["levels"]["V2"]))

    def test_baseline_basis_in_set_file_is_refused(self):
        with self.assertRaises(scenarios.ScenarioError):
            self._run([_spec(
                "SC-T-BASE",
                {"type": "baseline", "provenanceNote": "n"}, [])])

    def test_geojson_callback_recorded(self):
        seen = {}

        def writer(sid, rich):
            seen[sid] = True
            return f"scenarios/{sid}.geojson"

        report = self._run([_spec(
            "SC-T-DROP",
            {"type": "policy_variant", "normCardId": "NC-02", "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "drop"}])],
            on_scenario_geojson=writer)
        self.assertIn("SC-T-DROP", seen)
        self.assertEqual(report["scenarios"][0]["geometryFile"],
                         "scenarios/SC-T-DROP.geojson")

    def test_markdown_renders_rows_and_hypothetical_flag(self):
        report = self._run([_spec(
            "SC-T-H",
            {"type": "hypothetical", "rationale": "no citation exists",
             "provenanceNote": "n"},
            [{"ruleId": "FR-T-02", "action": "set_buffer_distance_m",
              "bufferDistanceM": 500}])])
        md = scenarios.report_markdown(report)
        self.assertIn("SC-T-H", md)
        self.assertIn("not legally grounded", md)
        self.assertIn("control", md.lower())


class ShippedSetTests(unittest.TestCase):
    """The shipped demo sets must ground in the canonical runs' artifacts."""

    CANONICAL = {
        "wind": "20260830T113234Z-wind",
        "zon": "20260830T142439Z-zon",
        "bos": "20260830T142446Z-bos",
    }

    def test_sets_valid_and_grounded(self):
        for use_case, run_name in self.CANONICAL.items():
            with self.subTest(use_case=use_case):
                set_path = POC_ROOT / "scenarios" / f"{use_case}.json"
                data = json.loads(set_path.read_text(encoding="utf-8"))
                contracts.validate(data, "scenario-set")
                run_dir = POC_ROOT / "runs" / run_name
                rules = json.loads((run_dir / "formalrules.json").read_text(encoding="utf-8"))
                rule_ids = {r["id"] for r in rules}
                cards = json.loads((run_dir / "normcards.json").read_text(encoding="utf-8"))
                card_ids = {c["id"] for c in cards}
                request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
                for spec in data["scenarios"]:
                    contracts.validate(spec, "scenario-spec")
                    self.assertEqual(spec["objectType"], request["objectType"])
                    for m in spec["mutations"]:
                        self.assertIn(m["ruleId"], rule_ids,
                                      f"{spec['id']}: unknown rule id")
                        self.assertIn(rules[[r["id"] for r in rules].index(m["ruleId"])]["status"],
                                      ("formalized", "ambiguous", "rejected"))
                    nc = spec["basis"].get("normCardId")
                    if nc:
                        self.assertIn(nc, card_ids, f"{spec['id']}: unknown normCardId")
                    # mutations must target rules the baseline actually executes
                    # (or explicitly hit the skip path for non-executable rules)
                self.assertGreaterEqual(len(data["scenarios"]), 2)


class RealCacheEndToEnd(unittest.TestCase):
    """Full sweep replaying the canonical zon run from the layer cache (~6 s)."""

    def test_zon_sweep_from_cache(self):
        run_dir = POC_ROOT / "runs" / "20260830T142439Z-zon"
        if not (run_dir / "run_summary.json").is_file():
            self.skipTest("canonical zon run not present")
        baseline = scenarios.load_baseline(run_dir)
        layers, degrades = scenarios.load_layers(
            baseline["manifest"], simplify_m=baseline["inputSimplifyM"])
        self.assertEqual(degrades, [])
        set_data = json.loads((POC_ROOT / "scenarios" / "zon.json").read_text(encoding="utf-8"))
        report = scenarios.run_scenario_set(
            baseline=baseline, layers=layers, specs=set_data["scenarios"],
            scenario_set_id=set_data["id"], report_id="SR-test-zon")
        validation = report.pop("_validation")
        report.pop("_control_rich")
        self.assertEqual(report["verdict"], "pass")
        self.assertTrue(report["control"]["reproductionWithinTolerance"])
        self.assertAlmostEqual(report["control"]["finalAreaKm2"],
                               report["control"]["baselineFinalAreaKm2"], delta=1.0)
        by_id = {r["scenarioId"]: r for r in report["scenarios"]}
        self.assertLess(by_id["SC-Z-GROENE-CONTOUR-HARD"]["deltaVsControlKm2"], 0.0)
        self.assertGreater(by_id["SC-Z-GEEN-NATURA-CARVE"]["deltaVsControlKm2"], 0.0)
        contracts.validate(report, "scenario-report")
        contracts.validate(validation, "validation-report")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
# verdict-assertion gate (qwen3.8 fabricated "eindstatus van de validatie is
# 'fail'" on a PASSING report; numbers and ids were grounded, the claim was not)
# --------------------------------------------------------------------------- #

class VerdictAssertionGateTests(unittest.TestCase):

    def _report(self):
        spec = _spec("SC-GATE-DROP",
                     {"type": "policy_variant", "normCardId": "NC-02",
                      "provenanceNote": "test"},
                     [{"ruleId": "FR-T-02", "action": "drop"}])
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=[spec],
            scenario_set_id="SSET-gate", report_id="SR-gate")
        report.pop("_validation")
        report.pop("_control_rich")
        return report

    def test_fabricated_fail_claim_on_passing_report_is_rejected(self):
        report = self._report()
        prose = (scenarios.deterministic_narrative(report)
                 + " De eindstatus van de validatie is 'fail'.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "fail")
        self.assertIn("verdict word", check["detail"])

    def test_passing_report_prose_may_say_pass(self):
        report = self._report()
        row = report["scenarios"][0]
        prose = (f"Scenario {row['scenarioId']} shifts the zone by "
                 f"{row['deltaVsControlKm2']:+.3f} km2; overall verdict pass.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "pass", check["detail"])

    def test_fail_report_prose_may_say_fail(self):
        report = self._report()
        report["verdict"] = "fail"
        row = report["scenarios"][0]
        prose = (f"Scenario {row['scenarioId']} shifts the zone by "
                 f"{row['deltaVsControlKm2']:+.3f} km2; the run failed.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "pass", check["detail"])

    def test_fail_report_prose_may_not_claim_pass(self):
        report = self._report()
        report["verdict"] = "fail"
        row = report["scenarios"][0]
        prose = (f"Scenario {row['scenarioId']} shifts the zone by "
                 f"{row['deltaVsControlKm2']:+.3f} km2; overall pass.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "fail")


class NarrationSeesFinalVerdictTests(unittest.TestCase):
    """Regression: the narrator must never see the placeholder verdict."""

    def test_narrator_receives_report_with_final_verdict(self):
        seen = []

        def spy(report):
            seen.append(report.get("verdict"))
            row = report["scenarios"][0]
            return (f"Scenario {row['scenarioId']} shifts the zone by "
                    f"{row['deltaVsControlKm2']:+.3f} km2.")

        spec = _spec("SC-GATE-DROP",
                     {"type": "policy_variant", "normCardId": "NC-02",
                      "provenanceNote": "test"},
                     [{"ruleId": "FR-T-02", "action": "drop"}])
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=[spec],
            scenario_set_id="SSET-gate", report_id="SR-gate", narrator=spy)
        self.assertEqual(seen, [report["verdict"]])
        self.assertEqual(report["verdict"], "pass")


class MagnitudeFoldTests(unittest.TestCase):
    """Narrations may state a negative delta as its magnitude (afname van X)."""

    def test_magnitude_of_reported_negative_resolves(self):
        spec = _spec("SC-GATE-DROP",
                     {"type": "policy_variant", "normCardId": "NC-02",
                      "provenanceNote": "test"},
                     [{"ruleId": "FR-T-02", "action": "drop"}])
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=[spec],
            scenario_set_id="SSET-gate", report_id="SR-gate")
        report.pop("_validation"); report.pop("_control_rich")
        row = report["scenarios"][0]
        delta = abs(float(row["deltaVsControlKm2"]))
        self.assertGreater(delta, 0.0)
        prose = (f"Scenario {row['scenarioId']} geeft een afname van "
                 f"{delta:.6f} km2 ten opzichte van de controle.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "pass", check["detail"])

    def test_unreported_magnitude_still_rejected(self):
        spec = _spec("SC-GATE-DROP",
                     {"type": "policy_variant", "normCardId": "NC-02",
                      "provenanceNote": "test"},
                     [{"ruleId": "FR-T-02", "action": "drop"}])
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=[spec],
            scenario_set_id="SSET-gate", report_id="SR-gate")
        report.pop("_validation"); report.pop("_control_rich")
        row = report["scenarios"][0]
        fake = abs(float(row["deltaVsControlKm2"])) + 111.111
        prose = (f"Scenario {row['scenarioId']} geeft een afname van "
                 f"{fake:.3f} km2.")
        check = scenarios.check_narrative_grounding(prose, report)
        self.assertEqual(check["status"], "fail")
