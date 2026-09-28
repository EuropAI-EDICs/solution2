from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import agents, contracts, norm_llm  # noqa: E402
from pipeline.llm_transport import extract_json_object, model_slug  # noqa: E402


def _fake_llm(response_json):
    def call(endpoint, model, system, user, timeout):
        return response_json
    return call


# --------------------------------------------------------------------------- #
# S1 — LLMNormAnalystHook
# --------------------------------------------------------------------------- #

EVIDENCE = {
    "id": "T-01",
    "sourceId": "S01",
    "article": "art. 9.99 lid 1",
    "instrument": "artikeltekst",
    "theme": "energy:test",
    "quote_nl": "Binnen het zoekgebied geldt een aanhoudingsplicht voor nieuwe natuur.",
    "url": "https://example.test/cvdr",
    "verified": True,
}
SOURCE = {"id": "S01", "version": "CVDR704250 geldend 13-10-2025",
          "retrieved_at": "2026-08-30", "url": "https://example.test/cvdr"}

GOOD_CLAIM = "The instrument imposes a compensation duty for new nature inside the search area."


class AnalystHookTests(unittest.TestCase):
    def _hook(self, response):
        return norm_llm.LLMNormAnalystHook(
            endpoint="http://x/v1", model="Test-Model", llm_call=_fake_llm(response))

    def test_accepted_proposal_shape(self):
        hook = self._hook(json.dumps({"claim": GOOD_CLAIM, "confidence": 0.8}))
        out = hook(EVIDENCE, SOURCE)
        self.assertEqual(out, {"claim": GOOD_CLAIM, "confidence": 0.8})
        self.assertEqual(hook.accepted, 1)
        self.assertEqual(hook.stamp, "llm-proposal.test-model")

    def test_confidence_clamped_with_note(self):
        hook = self._hook(json.dumps({"claim": GOOD_CLAIM, "confidence": 1.7}))
        out = hook(EVIDENCE, SOURCE)
        self.assertEqual(out["confidence"], 1.0)
        self.assertIn("clamped", out["notes"])
        hook2 = self._hook(json.dumps({"claim": GOOD_CLAIM, "confidence": -0.2}))
        self.assertEqual(hook2(EVIDENCE, SOURCE)["confidence"], 0.0)

    def test_malformed_claim_rejected_with_fallback_none(self):
        hook = self._hook(json.dumps({"claim": "too short", "confidence": 0.5}))
        self.assertIsNone(hook(EVIDENCE, SOURCE))
        self.assertEqual(hook.rejected[0]["kind"], "claim-invalid")
        self.assertEqual(hook.rejected[0]["evidenceId"], "T-01")

    def test_non_numeric_confidence_rejected(self):
        hook = self._hook(json.dumps({"claim": GOOD_CLAIM, "confidence": "high"}))
        self.assertIsNone(hook(EVIDENCE, SOURCE))
        self.assertEqual(hook.rejected[0]["kind"], "confidence-invalid")

    def test_no_json_rejected_not_raised(self):
        hook = self._hook("no json here at all")
        self.assertIsNone(hook(EVIDENCE, SOURCE))
        self.assertTrue(hook.rejected)

    def test_fenced_json_accepted(self):
        hook = self._hook("```json\n{" + f'"claim": "{GOOD_CLAIM}", "confidence": 0.5' + "}\n```")
        out = hook(EVIDENCE, SOURCE)
        self.assertEqual(out["claim"], GOOD_CLAIM)

    def test_reasoning_stripped(self):
        hook = self._hook("<think>reasoning…</think>" + json.dumps({"claim": GOOD_CLAIM, "confidence": 0.5}))
        self.assertEqual(hook(EVIDENCE, SOURCE)["claim"], GOOD_CLAIM)


class AnalystStampingTests(unittest.TestCase):
    """S1 end-to-end through NormAnalyst: stamping + notes + citation freeze."""

    def _analyst(self, hook):
        analyst = agents.NormAnalyst(llm_hook=hook)
        analyst._load_sources = lambda: {"S01": SOURCE}
        return analyst

    def test_card_stamp_and_notes(self):
        hook = norm_llm.LLMNormAnalystHook(
            endpoint="http://x/v1", model="Test-Model",
            llm_call=_fake_llm(json.dumps({"claim": GOOD_CLAIM, "confidence": 0.9})))
        analyst = self._analyst(hook)
        cards = analyst.read([EVIDENCE])
        self.assertEqual(len(cards), 1)
        card = cards[0].to_dict()
        self.assertEqual(card["extractedBy"], "legal-recon-agent#llm-proposal.test-model")
        self.assertIn("S1 seam: llm hook answered", card["notes"])
        self.assertEqual(card["claim"], GOOD_CLAIM)
        # citation untouched by construction
        self.assertEqual(card["source"]["quote"], EVIDENCE["quote_nl"])
        self.assertEqual(card["source"]["article"], EVIDENCE["article"])

    def test_declined_hook_keeps_deterministic_card(self):
        hook = norm_llm.LLMNormAnalystHook(
            endpoint="http://x/v1", model="Test-Model",
            llm_call=_fake_llm(json.dumps({"claim": "nope"})))
        analyst = self._analyst(hook)
        card = analyst.read([EVIDENCE])[0].to_dict()
        self.assertEqual(card["extractedBy"], agents.ANALYST_RUN)
        self.assertIn("S1 seam: llm hook declined", card["notes"])
        self.assertIn("Deterministic fallback claim", card["claim"])


# --------------------------------------------------------------------------- #
# S2 — LLMFormalizerHook + NormFormalizer wiring
# --------------------------------------------------------------------------- #

CARD = {
    "id": "NC-T-09",
    "evidenceId": "T-09",
    "claim": GOOD_CLAIM,
    "source": {
        "docId": "S01", "article": "art. 9.99 lid 1",
        "version": "CVDR704250 geldend 13-10-2025",
        "quote": "Binnen de gevoelige zone geldt een afstand van 300 meter tot geluidgevoelige objecten.",
        "quoteLanguage": "nl", "uri": "https://example.test/cvdr",
    },
    "instrument": "artikeltekst",
    "legalForce": "binding",
    "theme": "energy:test",
    "confidence": 0.8,
    "verified": True,
    "extractedBy": "legal-recon-agent#test",
    "extractedAt": "2026-08-30",
    "appliesTo": {"objectType": "wind_turbine", "contextTags": ["test"]},
    "geoBinding": {
        "zoneIds": ["gevoelige_zone"],
        "geometrySource": "provincial_gio",
        "gioJoinId": "/join/id/regdata/pv26/2025/gio00000000-0000-0000-0000-000000000000/nld@2025-08-18;1",
    },
}

GOOD_PROPOSAL = {
    "kind": "attention",
    "zoneIds": ["gevoelige_zone"],
    "bufferDistanceM": 300,
    "conditions": [],
    "rationale": "The quoted article fixes a 300 m attention distance to noise-sensitive objects inside the zone.",
}


def _formalizer_hook(response, allowed=("gevoelige_zone", "other_zone")):
    return norm_llm.LLMFormalizerHook(
        allowed, endpoint="http://x/v1", model="Test-Model", llm_call=_fake_llm(response))


class FormalizerHookGatingTests(unittest.TestCase):
    def test_grounded_proposal_accepted(self):
        hook = _formalizer_hook(json.dumps(GOOD_PROPOSAL))
        out = hook(CARD)
        self.assertEqual(out["kind"], "attention")
        self.assertEqual(out["bufferDistanceM"], 300)
        self.assertEqual(hook.accepted, 1)

    def test_fabricated_zone_rejected(self):
        proposal = {**GOOD_PROPOSAL, "zoneIds": ["made_up_zone"]}
        hook = _formalizer_hook(json.dumps(proposal))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected[0]["kind"], "zone-not-grounded")

    def test_number_not_in_quote_rejected(self):
        proposal = {**GOOD_PROPOSAL, "bufferDistanceM": 500}
        hook = _formalizer_hook(json.dumps(proposal))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected[0]["kind"], "number-not-in-quote")

    def test_condition_number_not_in_quote_rejected(self):
        proposal = {
            "kind": "inclusion", "zoneIds": ["gevoelige_zone"],
            "conditions": [{"parameter": "capacity", "operator": ">=", "value": 7, "unit": "MW"}],
            "rationale": "The quoted article supports a capacity threshold for the inclusion zone.",
        }
        hook = _formalizer_hook(json.dumps(proposal))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected[0]["kind"], "number-not-in-quote")

    def test_bad_kind_rejected(self):
        proposal = {**GOOD_PROPOSAL, "kind": "wild-guess"}
        hook = _formalizer_hook(json.dumps(proposal))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected[0]["kind"], "kind-invalid")

    def test_decline_propose_false_returns_none(self):
        hook = _formalizer_hook(json.dumps({"propose": False}))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected, [])

    def test_buffer_only_for_attention(self):
        proposal = {**GOOD_PROPOSAL, "kind": "inclusion", "conditions": []}
        hook = _formalizer_hook(json.dumps(proposal))
        self.assertIsNone(hook(CARD))
        self.assertEqual(hook.rejected[0]["kind"], "buffer-invalid")

    def test_dutch_decimal_comma_grounding(self):
        card = json.loads(json.dumps(CARD))
        card["source"]["quote"] = "De afstand bedraagt 1,5 kilometer tot het beschermd gebied."
        proposal = {
            "kind": "attention", "zoneIds": ["gevoelige_zone"], "bufferDistanceM": 1500,
            "conditions": [],
            "rationale": "The quoted article fixes a 1,5 km attention distance to the protected area.",
        }
        hook = _formalizer_hook(json.dumps(proposal))
        # 1500 m == 1,5 km spelled differently: NOT verbatim in the quote -> rejected
        self.assertIsNone(hook(CARD))

        card2 = json.loads(json.dumps(CARD))
        card2["source"]["quote"] = "De afstand bedraagt 1500 meter tot het beschermd gebied."
        hook2 = _formalizer_hook(json.dumps(proposal))
        self.assertIsNotNone(hook2(card2))


class FormalizerWiringTests(unittest.TestCase):
    def test_templateless_card_formalized_via_hook(self):
        hook = _formalizer_hook(json.dumps(GOOD_PROPOSAL))
        formalizer = agents.NormFormalizer(llm_hook=hook)
        card = contracts.NormCard.from_dict(CARD)
        self.assertNotIn("T-09", agents.TEMPLATE_SPECS)  # genuinely template-less
        rules = formalizer.formalize([card])
        rule = rules[0].to_dict()
        self.assertEqual(rule["status"], "formalized")
        self.assertEqual(rule["ruleType"], "zone_attention")
        self.assertEqual(rule["zoneSelector"]["bufferDistanceM"], 300)
        self.assertEqual(rule["zoneSelector"]["geometrySource"], "provincial_gio")
        self.assertEqual(rule["zoneSelector"]["gioJoinId"],
                         CARD["geoBinding"]["gioJoinId"])  # join id never came from the model
        self.assertEqual(rule["formalizedBy"], "norm-formalizer#llm-proposal.test-model")
        self.assertIn("llm_proposed", rule["appliesTo"]["contextTags"])
        self.assertIn("gated LLM proposal", rule["rationale"])
        contracts.validate(rule, "formal-rule")
        self.assertEqual(formalizer.last_coverage["llm_proposed"], 1)

    def test_rejected_proposal_stays_ambiguous(self):
        hook = _formalizer_hook(json.dumps({**GOOD_PROPOSAL, "zoneIds": ["made_up_zone"]}))
        formalizer = agents.NormFormalizer(llm_hook=hook)
        card = contracts.NormCard.from_dict(CARD)
        rule = formalizer.formalize([card])[0].to_dict()
        self.assertEqual(rule["status"], "ambiguous")
        self.assertEqual(rule["ruleType"], "unsupported_claim")
        self.assertEqual(formalizer.last_coverage["llm_rejected"], 1)
        self.assertEqual(hook.rejected[0]["kind"], "zone-not-grounded")

    def test_templated_cards_never_consult_hook(self):
        # W-01 has a curated 'reject' template: the hook must not be consulted
        calls = []

        def spy(card):
            calls.append(card.get("id"))
            return dict(GOOD_PROPOSAL)

        hook = norm_llm.LLMFormalizerHook(
            ("gevoelige_zone",), endpoint="http://x/v1", model="Test-Model", llm_call=spy)
        formalizer = agents.NormFormalizer(llm_hook=hook)
        ev = {"id": "W-01", "sourceId": "S01", "article": "art. 5.1",
              "instrument": "artikeltekst", "theme": "energy:wind",
              "quote_nl": "Afdeling 5.1 bevat regels voor windenergie, zonnevelden en biomassa.",
              "url": "https://x", "verified": True}
        analyst = agents.NormAnalyst()
        analyst._load_sources = lambda: {"S01": SOURCE}
        w01 = analyst.read([ev])[0]
        rule = formalizer.formalize([w01])[0].to_dict()
        self.assertEqual(rule["status"], "rejected")  # curated template outcome preserved
        self.assertEqual(calls, [])  # hook never consulted for a templated card

    def test_no_hook_default_unchanged(self):
        formalizer = agents.NormFormalizer()
        card = contracts.NormCard.from_dict(CARD)
        rule = formalizer.formalize([card])[0].to_dict()
        self.assertEqual(rule["status"], "ambiguous")
        self.assertEqual(rule["formalizedBy"], agents.FORMALIZER_RUN)
        self.assertEqual(formalizer.last_coverage["llm_proposed"], 0)
        self.assertEqual(formalizer.last_coverage["llm_rejected"], 0)


# --------------------------------------------------------------------------- #
# transport helpers
# --------------------------------------------------------------------------- #

class TransportHelperTests(unittest.TestCase):
    def test_model_slug(self):
        self.assertEqual(model_slug("Qwen3.6:27B-MLX"), "qwen3-6-27b-mlx")

    def test_extract_json_object_variants(self):
        self.assertEqual(extract_json_object('{"a": 1}'), {"a": 1})
        self.assertEqual(extract_json_object('```json\n{"a": 2}\n```'), {"a": 2})
        self.assertEqual(extract_json_object('prose {"a": 3} trailing'), {"a": 3})
        with self.assertRaises(ValueError):
            extract_json_object("no braces")


if __name__ == "__main__":
    unittest.main()
