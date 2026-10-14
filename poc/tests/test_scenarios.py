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
from unittest import mock

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


class EmptyFinalOutcomeTests(unittest.TestCase):
    """A deliberately empty final zone is a measured 0 km2 / -100% outcome.

    When the rule set executes cleanly and the emptiness follows from pure
    exclusion semantics (e.g. the energietoets SC-ET-TOETS-HARD: a whole-AOI
    scope executed as exclusion — "the toets has no spatial differentiation"),
    the outcome row is valid (`geometryValid`: the geometry is absent, not
    false) and `status` ok. When the scenario's execution degraded (broken
    layer, dropped rules), the old safety semantics hold: scenario-empty
    degradation, `geometryValid` False, `status` degraded.
    """

    def _sweep_empty_final(self, extra_degradations=None):
        """Sweep one scenario whose execution yields an empty final zone.

        FR-T-01 is the inclusion covering the whole AOI (INCL_BOX == AOI_BOX),
        so executing that scope as exclusion leaves exactly 0 opportunity km2.
        """
        spec = _spec(
            "SC-T-EMPTY",
            {"type": "policy_variant", "normCardId": "NC-01", "provenanceNote": "n"},
            [{"ruleId": "FR-T-01", "action": "set_semantics",
              "zoneSemantics": "exclusion"}])
        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS, specs=[spec],
            scenario_set_id="SSET-empty", report_id="SR-empty-0001",
            degradations=list(extra_degradations or []))
        validation = report.pop("_validation")
        report.pop("_control_rich")
        return report, validation

    def _sweep_null_final(self, extra_degradations=None):
        """Sweep one scenario whose execution produces NO final zone at all.

        Both executable rules are dropped so the engine receives an empty rule
        set; a stub returns no zones for that (the defensive `final is None`
        branch the real engine cannot reach — it always emits a final).
        """
        spec = _spec(
            "SC-T-NULL",
            {"type": "hypothetical", "rationale": "parameter exploration",
             "provenanceNote": "n"},
            [{"ruleId": "FR-T-01", "action": "drop"},
             {"ruleId": "FR-T-02", "action": "drop"}])
        real_execute = scenarios.engine.execute_rules

        def no_zones_for_empty_ruleset(rules, *args, **kwargs):
            if not rules:
                return []
            return real_execute(rules, *args, **kwargs)

        with mock.patch.object(scenarios.engine, "execute_rules",
                               new=no_zones_for_empty_ruleset):
            report = scenarios.run_scenario_set(
                baseline=_baseline(), layers=LAYERS, specs=[spec],
                scenario_set_id="SSET-null", report_id="SR-null-0001",
                degradations=list(extra_degradations or []))
        validation = report.pop("_validation")
        report.pop("_control_rich")
        return report, validation

    def test_measured_empty_final_is_a_valid_outcome(self):
        report, _ = self._sweep_empty_final()
        row = report["scenarios"][0]
        self.assertAlmostEqual(row["finalAreaKm2"], 0.0, places=9)
        self.assertAlmostEqual(row["deltaVsControlKm2"], -CONTROL_KM2, places=6)
        self.assertAlmostEqual(row["deltaVsControlPct"], -100.0, places=6)
        self.assertTrue(row["geometryValid"])
        self.assertEqual(row["status"], "ok")
        self.assertEqual(report["degradations"], [])
        self.assertEqual(report["verdict"], "pass")
        contracts.validate(report, "scenario-report")

    def test_null_final_without_degradations_is_measured_outcome(self):
        report, validation = self._sweep_null_final()
        row = report["scenarios"][0]
        self.assertEqual(row["finalAreaKm2"], 0.0)
        self.assertAlmostEqual(row["deltaVsControlKm2"], -CONTROL_KM2, places=6)
        self.assertAlmostEqual(row["deltaVsControlPct"], -100.0, places=6)
        self.assertTrue(row["geometryValid"])
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["geometryFile"], "")
        self.assertEqual(report["degradations"], [])  # no scenario-empty record
        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(validation["levels"]["V1"]["status"], "pass")
        contracts.validate(report, "scenario-report")

    def test_null_final_with_execution_degradation_stays_degraded(self):
        seeded = [{"kind": "layer-cache-missing", "scenarioId": "SC-T-NULL",
                   "error": "zone 'incl': cache file absent"}]
        report, validation = self._sweep_null_final(extra_degradations=seeded)
        row = report["scenarios"][0]
        self.assertEqual(row["status"], "degraded")
        self.assertFalse(row["geometryValid"])
        self.assertTrue(any(d["kind"] == "scenario-empty"
                            and d.get("scenarioId") == "SC-T-NULL"
                            for d in report["degradations"]))
        self.assertEqual(report["verdict"], "fail")
        self.assertEqual(validation["levels"]["V1"]["status"], "fail")

    def test_surviving_final_with_execution_degradation_stays_degraded(self):
        """Safety semantics on the non-None-final branch (characterisation).

        The `final is None` branch above has its own test; this pins the
        sibling path: a scenario whose execution degraded but that still
        yields a final zone keeps `status` degraded and `geometryValid`
        False (the engine flags the measured-empty geometry invalid, and a
        degraded run may never launder that into a valid outcome), and the
        report verdict is not pass.
        """
        seeded = [{"kind": "layer-cache-missing", "scenarioId": "SC-T-EMPTY",
                   "error": "zone 'excl': cache file absent"}]
        report, _ = self._sweep_empty_final(extra_degradations=seeded)
        row = report["scenarios"][0]
        self.assertEqual(row["status"], "degraded")
        self.assertFalse(row["geometryValid"])
        self.assertNotEqual(report["verdict"], "pass")
        contracts.validate(report, "scenario-report")


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


class H3MetricsTests(unittest.TestCase):
    """Optional h3_metrics seam: attached when the callable works,
    degraded when it errors, absent by default."""

    def test_h3_metrics_attached_and_control_cells_popped(self):
        seen = []

        def fake_metrics(payload, control_cells):
            seen.append(control_cells)
            if control_cells is None:  # control call first
                return {"resolution": 8, "cellCount": 3, "moransI": 0.5,
                        "pValue": 0.01, "cells": ["a", "b", "c"],
                        "cellsGainedVsControl": None,
                        "cellsLostVsControl": None}
            return {"resolution": 8, "cellCount": 4, "moransI": 0.2,
                    "pValue": 0.2, "cellsGainedVsControl": 1,
                    "cellsLostVsControl": 0}

        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=[_spec("SC-H3",
                         {"type": "policy_variant", "normCardId": "NC-02",
                          "provenanceNote": "n"},
                         [{"ruleId": "FR-T-02", "action": "drop"}])],
            scenario_set_id="SSET-h3", report_id="SR-h3-0001",
            h3_metrics=fake_metrics)
        report.pop("_validation")
        report.pop("_control_rich")
        self.assertIn("h3", report["control"])
        self.assertNotIn("cells", report["control"]["h3"])  # runner pops it
        row = report["scenarios"][0]
        self.assertEqual(row["status"], "ok")
        self.assertIn("h3", row)
        self.assertNotIn("cells", row["h3"])
        self.assertEqual(row["h3"]["cellsGainedVsControl"], 1)
        contracts.validate(report, "scenario-report")
        self.assertIsNone(seen[0])                    # control: control_cells None
        self.assertEqual(seen[1], {"a", "b", "c"})    # scenario: the popped set

    def test_h3_metrics_error_degrades_but_keeps_verdict(self):
        def boom(payload, control_cells):
            raise RuntimeError("h3 offline")

        report = scenarios.run_scenario_set(
            baseline=_baseline(), layers=LAYERS,
            specs=[_spec("SC-H3-E",
                         {"type": "policy_variant", "normCardId": "NC-02",
                          "provenanceNote": "n"},
                         [{"ruleId": "FR-T-02", "action": "drop"}])],
            scenario_set_id="SSET-h3e", report_id="SR-h3e-0001",
            h3_metrics=boom)
        report.pop("_validation")
        report.pop("_control_rich")
        self.assertNotIn("h3", report["control"])
        self.assertTrue(any(d["kind"] == "h3-metrics-error"
                            for d in report["degradations"]))
        self.assertEqual(report["verdict"], "pass")  # decision support only
        contracts.validate(report, "scenario-report")


class DataGroundingSchemaTests(unittest.TestCase):
    """V0 gate: optional basis.dataGrounding — non-legal data grounding.

    The validator only sees the shape: sourceId + retrieved required, no
    extra keys. Whether dataGrounding is appropriate for a given basis.type
    is the pipeline's business (V2 check, kalibratie plan 2 task 2), not the
    schema's.
    """

    def test_data_grounding_is_toegestaan_op_hypothetical_basis(self):
        spec = {
            "id": "SC-T-DG", "name": "test", "objectType": "energy_storage",
            "basis": {
                "type": "hypothetical",
                "rationale": "data-grounded variant",
                "provenanceNote": "NOT legally grounded: data-grounded only.",
                "dataGrounding": {"sourceId": "netbeheerder-netcongestie",
                                  "retrieved": "2026-10-13"},
            },
            "mutations": [{"ruleId": "FR-ET-01", "action": "drop"}],
            "proposedBy": "a#b",
        }
        contracts.validate(spec, "scenario-spec")  # moet door de V0-gate

    def test_data_grounding_verplicht_retrieved(self):
        spec = {
            "id": "SC-T-DG2", "name": "test", "objectType": "energy_storage",
            "basis": {
                "type": "hypothetical",
                "rationale": "data-grounded variant",
                "provenanceNote": "NOT legally grounded.",
                "dataGrounding": {"sourceId": "netbeheerder-netcongestie"},
            },
            "mutations": [{"ruleId": "FR-ET-01", "action": "drop"}],
            "proposedBy": "a#b",
        }
        with self.assertRaises(contracts.ContractError):
            contracts.validate(spec, "scenario-spec")


class DataGroundingV2CheckTests(unittest.TestCase):
    """V2: elk basis.dataGrounding-blok moet resolvend zijn — de sourceId
    bestaat in de sources-registry met role 'scenario-basis' en retrieved
    is een ISO-datum. (Kalibratie plan 2 task 2.)"""

    def test_v2_data_grounding_berekent_fouten(self):
        from pipeline.scenarios import _data_grounding_errors
        src = {"netbeheerder-netcongestie": {"id": "netbeheerder-netcongestie",
                                             "role": "scenario-basis"}}
        assert _data_grounding_errors(src, {"sourceId": "netbeheerder-netcongestie",
                                            "retrieved": "2026-10-13"}) == []
        # geen dataGrounding-blok -> geen fouten (sets zonder grounding
        # moeten de V2-check op pass houden)
        assert _data_grounding_errors(src, {}) == []
        assert _data_grounding_errors(src, None) == []
        assert "onbekende sourceId" in _data_grounding_errors(
            src, {"sourceId": "bestaat-niet", "retrieved": "2026-10-13"})[0]
        # verkeerde registry-role -> "role"-fout (de brief-assert gaf hier
        # een IndexError op een lege foutenlijst; de context-role-variant
        # hieronder is de werkende bedoeling)
        assert "role" in _data_grounding_errors(
            {"netbeheerder-netcongestie": {"id": "x", "role": "context"}},
            {"sourceId": "netbeheerder-netcongestie",
             "retrieved": "2026-10-13"})[0]
        assert "ISO" in _data_grounding_errors(
            src, {"sourceId": "netbeheerder-netcongestie", "retrieved": "gisteren"})[0]


class DataGroundingWiringTests(unittest.TestCase):
    """E2e wiring (kalibratie plan 2 task 3): een grounded hypothetical-spec
    doorloopt de hele sweep — de basis-echo (incl. dataGrounding) haalt de
    V0-report-gate op het ScenarioReport en de V2-check ``v2-data-grounding``
    resolveert de sourceId via ``geodata.load_sources`` (hier een stub-registry
    met de rol uit task 3's registry-entries).
    """

    def _sweep_grounding(self, source_id="netbeheerder-netcongestie"):
        spec = _spec(
            "SC-T-DGE",
            {"type": "hypothetical", "rationale": "data-grounded variant",
             "provenanceNote": "NOT legally grounded: data-grounded only.",
             "dataGrounding": {"sourceId": source_id,
                               "retrieved": "2026-10-13"}},
            [{"ruleId": "FR-T-02", "action": "drop"}])
        stub_registry = {"netbeheerder-netcongestie": {
            "id": "netbeheerder-netcongestie", "role": "scenario-basis"}}
        with mock.patch.object(scenarios.geodata, "load_sources",
                               return_value=stub_registry):
            report = scenarios.run_scenario_set(
                baseline=_baseline(), layers=LAYERS, specs=[spec],
                scenario_set_id="SSET-dge", report_id="SR-dge-0001")
        validation = report.pop("_validation")
        report.pop("_control_rich")
        return report, validation

    @staticmethod
    def _grounding_check(validation):
        checks = validation["levels"]["V2"]["checks"]
        found = [c for c in checks if c.get("id") == "v2-data-grounding"]
        assert len(found) == 1, found
        return found[0]

    def test_grounded_spec_haalt_v0_report_gate_en_v2_pass(self):
        report, validation = self._sweep_grounding()
        self.assertEqual(report["verdict"], "pass")
        # V0-report-gate: de basis-echo incl. dataGrounding is schema-valid
        contracts.validate(report, "scenario-report")
        # de typed echo dropt het datablok niet
        basis = report["scenarios"][0]["basis"]
        self.assertEqual(basis["dataGrounding"]["sourceId"],
                         "netbeheerder-netcongestie")
        self.assertEqual(basis["dataGrounding"]["retrieved"], "2026-10-13")
        check = self._grounding_check(validation)
        self.assertEqual(check["status"], "pass")
        self.assertEqual(validation["verdict"], "pass")

    def test_onbekende_sourceId_faalt_de_v2_check(self):
        report, validation = self._sweep_grounding(
            source_id="bestaat-niet-in-registry")
        self.assertEqual(report["verdict"], "fail")
        check = self._grounding_check(validation)
        self.assertEqual(check["status"], "fail")
        self.assertIn("onbekende sourceId", check["detail"])
        # V0 blijft groen: het rapport zelf is schema-valid; de fail zit
        # uitsluitend in de V2-grounding-resolutie
        contracts.validate(report, "scenario-report")
