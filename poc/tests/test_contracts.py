"""Unit tests for the PoC contracts, norm corpus and formalizer (track A).

Run from the workspace root:

    python3 -m unittest discover -s poc/tests

All tests are offline and deterministic. The single network test is opt-in
via the environment variable LDT_POC_NETWORK=1 and is skipped by default.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import contracts  # noqa: E402
from pipeline.agents import (  # noqa: E402
    ANALYST_RUN,
    CORPUS_DIR,
    ENGINE_OPERATIONS,
    NormAnalyst,
    NormFormalizer,
)

CORPUS_DIR_ABS = Path(CORPUS_DIR)


def load_json(name: str):
    with (CORPUS_DIR_ABS / name).open(encoding="utf-8") as fh:
        return json.load(fh)


class SchemaFileTests(unittest.TestCase):
    """V0 gate: every published schema must itself be valid draft 2020-12."""

    def test_all_six_schemas_load_and_meta_validate(self):
        for name in contracts.SCHEMA_NAMES:
            schema = contracts.load_schema(name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn("$id", schema)

    def test_unknown_schema_name_rejected(self):
        with self.assertRaises(contracts.ContractError):
            contracts.validate({}, "no-such-schema")

    def test_missing_schema_file_raises(self):
        original = contracts.SCHEMA_DIR
        try:
            contracts.SCHEMA_DIR = original.parent / "does-not-exist"
            contracts.load_schema.cache_clear()
            contracts._validator.cache_clear()
            with self.assertRaises(contracts.ContractError):
                contracts.load_schema("norm-card")
        finally:
            contracts.SCHEMA_DIR = original
            contracts.load_schema.cache_clear()
            contracts._validator.cache_clear()


class NormCardCorpusTests(unittest.TestCase):
    """The shipped normcards-wind.json corpus validates against its schema."""

    @classmethod
    def setUpClass(cls):
        cls.cards = load_json("normcards-wind.json")
        cls.first = cls.cards[0]

    def test_corpus_file_validates_against_norm_card_schema(self):
        self.assertEqual(len(self.cards), 24)
        for card in self.cards:
            contracts.validate(card, "norm-card")

    def test_every_card_is_cite_complete(self):
        for card in self.cards:
            source = card["source"]
            self.assertTrue(source["quote"].strip(), card["id"])
            self.assertGreaterEqual(len(source["quote"]), 20)
            self.assertTrue(source["uri"].startswith("http"))
            self.assertTrue(source["version"])
            self.assertIs(card["verified"], True)

    def test_corpus_is_deterministic_replay_of_the_analyst(self):
        analyst = NormAnalyst()
        cards = analyst.read(CORPUS_DIR_ABS / "evidence-wind.json")
        self.assertEqual([c.to_dict() for c in cards], self.cards)

    def test_analyst_extracted_by_stamp(self):
        for card in self.cards:
            self.assertEqual(card["extractedBy"], ANALYST_RUN)
            self.assertEqual(card["appliesTo"]["objectType"], "wind_turbine")

    def test_dataclass_roundtrip(self):
        for payload in self.cards[:5]:
            card = contracts.NormCard.from_dict(payload)
            self.assertEqual(card.to_dict(), payload)

    def test_rejected_ledger_structure(self):
        ledger = load_json("normcards-rejected.json")
        for key in ("generatedBy", "generatedAt", "policy", "rejectedEvidence", "abstentions"):
            self.assertIn(key, ledger)
        for entry in ledger["rejectedEvidence"]:
            self.assertTrue(entry.get("reason"), "rejected evidence must carry a reason")
        for entry in ledger["abstentions"]:
            self.assertTrue(entry.get("topic"))
            self.assertTrue(entry.get("reason"))
            self.assertTrue(entry.get("checkedAt"))


class NormAnalystBehaviourTests(unittest.TestCase):
    """Cite-or-abstain: unverified evidence never becomes a NormCard."""

    def test_unverified_evidence_is_dropped_and_recorded(self):
        shard = {
            "evidence": [
                {
                    "id": "W-99",
                    "sourceId": "S07",
                    "instrument": "Omgevingsverordening provincie Utrecht (CVDR704250) - artikeltekst",
                    "article": "art. 99.9",
                    "quote_nl": "Quote die niet geverifieerd kon worden tegen de geconsolideerde tekst.",
                    "theme": "energy:wind-test",
                    "url": "https://lokaleregelgeving.overheid.nl/cvdr704250",
                    "verified": False,
                    "notes": "unverified",
                },
                {
                    "id": "W-98",
                    "sourceId": "S07",
                    "instrument": "Omgevingsverordening provincie Utrecht (CVDR704250) - artikeltekst",
                    "article": "art. 98.8",
                    "quote_nl": "Geverifieerde quote die ruim lang genoeg is voor de schema-minimum.",
                    "theme": "energy:wind-test",
                    "url": "https://lokaleregelgeving.overheid.nl/cvdr704250",
                    "verified": True,
                    "notes": "verified",
                },
            ],
            "sources": {
                "S07": {
                    "id": "S07",
                    "version": "CVDR704250, geldend van 13-10-2025 t/m heden",
                    "url": "https://lokaleregelgeving.overheid.nl/cvdr704250",
                    "retrieved_at": "2026-08-30",
                }
            },
        }
        analyst = NormAnalyst()
        cards = analyst.read(shard)
        self.assertEqual([card.evidenceId for card in cards], ["W-98"])
        self.assertEqual(len(analyst.rejected), 1)
        self.assertEqual(analyst.rejected[0]["evidenceId"], "W-99")
        self.assertIn("cite-or-abstain", analyst.rejected[0]["reason"])

    def test_optional_llm_hook_only_refines_claim_and_confidence(self):
        def hook(evidence, source):
            return {"claim": "Hook-refined English claim that is long enough for the schema.",
                    "confidence": 0.42}

        analyst = NormAnalyst(llm_hook=hook)
        cards = analyst.read([copy.deepcopy(ev) for ev in load_json("evidence-wind.json")[:2]])
        for card in cards:
            self.assertEqual(
                card.claim, "Hook-refined English claim that is long enough for the schema."
            )
            self.assertEqual(card.confidence, 0.42)
            card.validate()  # still schema-valid


class FormalizerTests(unittest.TestCase):
    """The deterministic formalizer: templates, ambiguity flags, coverage."""

    @classmethod
    def setUpClass(cls):
        cls.cards = NormAnalyst().read(CORPUS_DIR_ABS / "evidence-wind.json")
        cls.rules = NormFormalizer().formalize(cls.cards)
        cls.rule_dicts = [rule.to_dict() for rule in cls.rules]

    def test_formalizer_output_validates_against_formal_rule_schema(self):
        self.assertEqual(len(self.rules), len(self.cards))
        for rule in self.rule_dicts:
            contracts.validate(rule, "formal-rule")

    def test_shipped_formalrules_file_is_deterministic_replay(self):
        shipped = load_json("formalrules-wind.json")
        self.assertEqual(shipped, self.rule_dicts)

    def test_formalizer_is_deterministic(self):
        again = NormFormalizer().formalize(NormAnalyst().read(CORPUS_DIR_ABS / "evidence-wind.json"))
        self.assertEqual([r.to_dict() for r in again], self.rule_dicts)

    def test_total_coverage_one_rule_per_card(self):
        card_ids = {card.id for card in self.cards}
        rule_card_ids = [rule.normCardId for rule in self.rules]
        self.assertEqual(set(rule_card_ids), card_ids)
        self.assertEqual(len(rule_card_ids), len(set(rule_card_ids)))

    def test_status_distribution(self):
        statuses = [rule.status for rule in self.rules]
        self.assertEqual(statuses.count("formalized"), 9)
        self.assertEqual(statuses.count("ambiguous"), 13)
        self.assertEqual(statuses.count("rejected"), 2)

    def test_ambiguous_and_rejected_never_guess(self):
        for rule in self.rules:
            if rule.status != "formalized":
                self.assertTrue(rule.reason and len(rule.reason) >= 15, rule.id)
                self.assertFalse(rule.conditions, f"{rule.id} must not carry conditions")
                self.assertIsNone(rule.zoneSelector, f"{rule.id} must not carry a zoneSelector")
                self.assertNotEqual(rule.zoneSemantics, "inclusion")
                self.assertNotEqual(rule.zoneSemantics, "exclusion")

    def test_formalized_rules_carry_registered_engine_refs(self):
        formalized = [rule for rule in self.rules if rule.status == "formalized"]
        self.assertGreaterEqual(len(formalized), 9)
        for rule in formalized:
            self.assertIn(rule.executableRef, ENGINE_OPERATIONS)
            self.assertIsNotNone(rule.zoneSelector)
            self.assertIsNotNone(rule.conditions)
            self.assertTrue(rule.rationale)

    def test_core_wind_rule_shape(self):
        by_id = {rule.id: rule for rule in self.rules}
        core = by_id["FR-W-05"]
        self.assertEqual(core.zoneSemantics, "inclusion")
        self.assertEqual(core.zoneSelector.gioJoinId,
                         "/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846")
        cond = core.conditions[0]
        self.assertEqual((cond.parameter, cond.operator, cond.value, cond.unit),
                         ("capacity", ">=", 3, "MW"))

    def test_stiltegebied_buffer_is_1500m(self):
        by_id = {rule.id: rule for rule in self.rules}
        attention = by_id["FR-W-10"]
        self.assertEqual(attention.zoneSemantics, "attention")
        self.assertEqual(attention.zoneSelector.bufferDistanceM, 1500)
        self.assertEqual(attention.zoneSelector.derivedFrom, "stiltegebied")
        self.assertEqual(attention.executableRef, "engine.zone.buffer@poc-v1")

    def test_natura_2000_exclusion_uses_national_source(self):
        by_id = {rule.id: rule for rule in self.rules}
        exclusion = by_id["FR-W-08"]
        self.assertEqual(exclusion.zoneSemantics, "exclusion")
        self.assertEqual(exclusion.zoneSelector.geometrySource, "national_source")
        self.assertIn("NC-W-22", exclusion.relatedNormCardIds or [])

    def test_untemplated_cards_are_flagged_ambiguous(self):
        # the bos shard has no registered templates: every card must be flagged,
        # never guessed (deterministic cite-or-abstain at the formalizer boundary)
        bos_cards = NormAnalyst().read(CORPUS_DIR_ABS / "evidence-bos.json")
        rules = NormFormalizer().formalize(bos_cards)
        self.assertEqual(len(rules), len(bos_cards))
        for rule in rules:
            self.assertEqual(rule.status, "ambiguous", rule.id)
            self.assertIn("no deterministic template registered", rule.reason)


class NegativeValidationTests(unittest.TestCase):
    """An intentionally bad card (and other artifacts) must fail validation."""

    @classmethod
    def setUpClass(cls):
        cls.good = load_json("normcards-wind.json")[0]

    def test_bad_quote_too_short(self):
        bad = copy.deepcopy(self.good)
        bad["source"]["quote"] = "te kort"
        with self.assertRaises(contracts.ContractError) as ctx:
            contracts.validate(bad, "norm-card")
        self.assertIn("norm-card", str(ctx.exception))

    def test_bad_confidence_out_of_range(self):
        bad = copy.deepcopy(self.good)
        bad["confidence"] = 1.5
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "norm-card")

    def test_bad_theme(self):
        bad = copy.deepcopy(self.good)
        bad["theme"] = "wind"
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "norm-card")

    def test_unverified_card_rejected(self):
        bad = copy.deepcopy(self.good)
        bad["verified"] = False
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "norm-card")

    def test_formalized_rule_without_zoneselector_rejected(self):
        rules = load_json("formalrules-wind.json")
        formalized = next(r for r in rules if r["status"] == "formalized")
        bad = copy.deepcopy(formalized)
        del bad["zoneSelector"]
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "formal-rule")

    def test_ambiguous_rule_without_reason_rejected(self):
        rules = load_json("formalrules-wind.json")
        ambiguous = next(r for r in rules if r["status"] == "ambiguous")
        bad = copy.deepcopy(ambiguous)
        bad.pop("reason")
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "formal-rule")


class OtherContractTests(unittest.TestCase):
    """Minimal valid/invalid instances for the remaining four contracts."""

    def test_opportunity_map_request_valid_minimal(self):
        request = {
            "id": "3f2a8c1d-1b2e-4c5a-9d6f-7e8a9b0c1d2e",
            "objectType": "wind_turbine",
            "ambitions": ["energy"],
            "areaOfInterest": {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[135000, 455000], [150000, 455000], [150000, 465000], [135000, 455000]]],
                },
                "crs": "EPSG:28992",
            },
            "policyStage": "programming",
            "effortBudget": {"maxSubagents": 8, "maxCostEur": 2.0, "maxLatencyS": 900},
            "requestedAt": "2026-08-30T09:00:00Z",
        }
        contracts.validate(request, "opportunity-map-request")
        obj = contracts.OpportunityMapRequest.from_dict(request)
        self.assertEqual(obj.to_dict(), request)

    def test_opportunity_map_request_missing_stage_rejected(self):
        request = {
            "id": "3f2a8c1d-1b2e-4c5a-9d6f-7e8a9b0c1d2e",
            "objectType": "wind_turbine",
            "areaOfInterest": {"geometry": {"type": "Point", "coordinates": [150000, 460000]}, "crs": "EPSG:28992"},
            "effortBudget": {"maxSubagents": 4},
            "requestedAt": "2026-08-30T09:00:00Z",
        }
        with self.assertRaises(contracts.ContractError):
            contracts.validate(request, "opportunity-map-request")

    def test_zone_result_accepts_geojson_and_gml_string(self):
        base = {
            "ruleIds": ["FR-W-05"],
            "operation": "intersection",
            "geometryValid": True,
            "provenance": "geo-analyst#run-1 intersection(aoi, gebied_windenergie GIO ;846)",
            "computedBy": "geo-analyst#run-1",
            "computedAt": "2026-08-30T12:00:00Z",
        }
        geojson = dict(base, id="ZR-test-1", geometry={
            "format": "GeoJSON",
            "payload": {"type": "Polygon", "coordinates": [[[155000, 463000], [156000, 463000], [156000, 464000], [155000, 463000]]]},
            "crs": "EPSG:28992",
        })
        gml = dict(base, id="ZR-test-2", geometry={
            "format": "GML32",
            "payload": "<gml:Polygon srsName=\"EPSG:28992\"><gml:exterior><gml:LinearRing><gml:posList>155000 463000 156000 463000</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>",
            "crs": "EPSG:28992",
        })
        contracts.validate(geojson, "zone-result")
        contracts.validate(gml, "zone-result")

    def test_zone_result_rejects_numeric_payload(self):
        bad = {
            "id": "ZR-test-3",
            "ruleIds": ["FR-W-05"],
            "operation": "buffer",
            "geometry": {"format": "GeoJSON", "payload": 12345, "crs": "EPSG:28992"},
            "geometryValid": True,
            "provenance": "geo-analyst#run-1 buffer(stiltegebied, 1500)",
            "computedBy": "geo-analyst#run-1",
            "computedAt": "2026-08-30T12:00:00Z",
        }
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad, "zone-result")

    def test_validation_report_requires_all_five_levels(self):
        level = {"status": "pass", "checks": [{"id": "schema", "status": "pass"}]}
        report = {
            "id": "VR-test-1",
            "artifactId": "SET-wind-2026-08-30",
            "artifactType": "norm-card-set",
            "levels": {f"V{i}": dict(level, status="pending" if i == 4 else "pass") for i in range(5)},
            "verdict": "needs_human",
            "evidence": [{"ref": "normcards-wind.json", "note": "24/24 cards validated"}],
            "evaluatorRun": "critic-validator#run-1",
            "evaluatedAt": "2026-08-30T12:00:00Z",
        }
        contracts.validate(report, "validation-report")
        obj = contracts.ValidationReport.from_dict(report)
        self.assertEqual(obj.levels["V4"].status, "pending")

        broken = copy.deepcopy(report)
        del broken["levels"]["V3"]
        with self.assertRaises(contracts.ContractError):
            contracts.validate(broken, "validation-report")

    def test_decision_table_rows_must_link_a_norm_card(self):
        table = {
            "id": "DT-wind-1",
            "title": "Wind turbines in province Utrecht - where can I do what?",
            "columns": ["criterion", "norm", "source", "zone effect"],
            "rows": [
                {
                    "criterion": "capacity >= 3 MW inside Gebied windenergie",
                    "norm": "turbines of 3 MW or more allowed when clustered, with removal duty",
                    "source": "art. 5.4 CVDR704250 (geldend 13-10-2025)",
                    "zone effect": "included",
                    "normCardId": "NC-W-05",
                    "ruleId": "FR-W-05",
                }
            ],
            "generatedBy": "explainer#run-1",
            "generatedAt": "2026-08-30T12:00:00Z",
            "provenance": "derived from normcards-wind.json + formalrules-wind.json (agent runs stamped)",
        }
        contracts.validate(table, "decision-table")

        broken = copy.deepcopy(table)
        del broken["rows"][0]["normCardId"]
        with self.assertRaises(contracts.ContractError):
            contracts.validate(broken, "decision-table")

        bad_columns = copy.deepcopy(table)
        bad_columns["columns"] = ["criterion", "norm", "source"]
        with self.assertRaises(contracts.ContractError):
            contracts.validate(bad_columns, "decision-table")


@unittest.skipUnless(
    os.environ.get("LDT_POC_NETWORK") == "1",
    "network test is opt-in via LDT_POC_NETWORK=1 (skipped by default)",
)
class NetworkSourceTests(unittest.TestCase):
    """Opt-in: the primary legal source must remain reachable."""

    def test_cvdr704250_source_reachable(self):
        import urllib.request

        request = urllib.request.Request(
            "https://lokaleregelgeving.overheid.nl/cvdr704250", method="HEAD"
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            self.assertLess(response.status, 400)


if __name__ == "__main__":
    unittest.main()
