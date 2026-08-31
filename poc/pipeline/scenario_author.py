#!/usr/bin/env python3
"""Scenario authors — the GenAI seam of the scenario plane (Phase B).

``docs/GENAI_SEAMS.md`` seam S7: a scenario author *proposes* ScenarioSpec
contracts; the deterministic engine executes them and the critic gates them.
Nothing else. Two authors implement the exact same interface:

* ``DeterministicScenarioAuthor`` — derives proposals from the baseline run's
  own artifacts (drop/hard-classify every executed rule, vary every cited
  buffer, hypothetical setbacks for abstained topics), with an effort budget
  that records what it cut. This is the reproducible analogue of what an LLM
  is asked to do, and the default offline demonstration of the seam.

* ``LLMScenarioAuthor`` — builds a compact digest of the baseline run
  (formalized rules, norm cards, abstention topics, rule footprints), calls an
  OpenAI-compatible endpoint (local open model per paper B's constraint,
  configured via ``LDT_SCENARIO_LLM_ENDPOINT`` / ``LDT_SCENARIO_LLM_MODEL``,
  temperature 0), and treats the response as *proposals only*: every item is
  schema-validated (``scenario-spec``), every ruleId/normCardId is resolved
  against the baseline run, the author stamps ``proposedBy`` itself, and
  anything unverifiable lands in the rejected-proposals ledger — never in the
  sweep. Hallucinated ids cannot fail the run; they are simply not executed.

Both ``.propose(baseline, max_scenarios)`` return
``(accepted_specs, rejected_ledger)`` where accepted specs are schema-valid
and grounded by construction — the critic's V2 check then verifies the same
invariants independently (gate at the critic, not just at the author).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from pipeline import contracts

__all__ = [
    "AUTHOR_DETERMINISTIC",
    "AUTHOR_LLM",
    "DETERMINISTIC_AUTHOR_RUN",
    "DeterministicScenarioAuthor",
    "LLMScenarioAuthor",
    "ScenarioAuthorError",
    "build_llm_digest",
]

AUTHOR_DETERMINISTIC = "deterministic-scenario-author#poc-v1-auto"
AUTHOR_LLM = "llm-proposal"

#: default exploration distance (m) for hypothetical setbacks on un-buffered
#: exclusion rules — mirrors the demo sets; recorded in every proposal
HYPOTHETICAL_SETBACK_M = 500.0

DETERMINISTIC_AUTHOR_RUN = AUTHOR_DETERMINISTIC


class ScenarioAuthorError(ValueError):
    """Raised for author-mode misuse (never for individual bad proposals —
    those go to the rejected ledger)."""


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_optional(baseline: Mapping[str, Any], name: str, default: Any) -> Any:
    p = Path(baseline.get("runDir", ".")) / name
    try:
        return _read_json(p) if p.is_file() else default
    except (OSError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# deterministic author (offline default for --author auto)
# --------------------------------------------------------------------------- #

class DeterministicScenarioAuthor:
    """Proposes scenarios derived mechanically from the baseline artifacts.

    Policy (rule-shape driven, applied in baseline rule order):

    * exclusion rule           -> ``drop`` (policy_variant citing its card)
                                  + ``set_buffer_distance_m`` 500 m
                                  (hypothetical setback, when un-buffered)
    * marker rule              -> ``set_semantics`` exclusion (policy_variant);
                                  when the rule carries a cited buffer, also
                                  half/double variants enforced as exclusion
                                  (norm_variance)
    * inclusion rule w/ buffer -> half/double buffer (norm_variance)

    Everything the author cannot ground (no card, no selector) is skipped and
    recorded; the effort budget cuts the tail and records that too.
    """

    def propose(
        self, baseline: Mapping[str, Any], max_scenarios: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        request = baseline["request"]
        rules: List[Dict[str, Any]] = baseline["formalrules"]
        object_type = request.get("objectType")
        abst_topics = self._abstention_topics(baseline)
        drafts: List[Dict[str, Any]] = []
        cuts: List[Dict[str, Any]] = []

        for r in rules:
            if r.get("status") != "formalized":
                continue
            rid = str(r.get("id"))
            nc = str(r.get("normCardId") or "")
            sem = str(r.get("zoneSemantics") or "")
            zs = r.get("zoneSelector") or {}
            buf = zs.get("bufferDistanceM")
            if not nc:
                cuts.append({"kind": "author-skip", "ruleId": rid,
                             "reason": "rule carries no normCardId to ground a basis"})
                continue

            if sem == "exclusion":
                drafts.append(self._spec(
                    f"SC-{rid}-DROP", f"Exclusion {rid} dropped (discretionary path)",
                    object_type,
                    {"type": "policy_variant", "normCardId": nc,
                     "provenanceNote": f"Flips the documented exclusion choice on "
                                       f"{nc} (rule {rid}): the clause is cited, the "
                                       f"province-wide drop is this scenario's policy assumption."},
                    [{"ruleId": rid, "action": "drop"}]))
                if not buf:
                    drafts.append(self._spec(
                        f"SC-{rid}-SETBACK500",
                        f"Hypothetical 500 m setback behind exclusion {rid}",
                        object_type,
                        {"type": "hypothetical",
                         "rationale": "Setback-like distances are abstained topics in the "
                                      "baseline run (no verified citation"
                                      + (f"; e.g. {', '.join(abst_topics[:2])}" if abst_topics else "")
                                      + f"), so a {HYPOTHETICAL_SETBACK_M:g} m buffer behind "
                                      f"rule {rid} is explored as a not-legally-grounded stress test.",
                         "provenanceNote": "NOT legally grounded: no citation exists for the "
                                           f"{HYPOTHETICAL_SETBACK_M:g} m distance; the underlying "
                                           f"exclusion zones are cited via {nc}."},
                        [{"ruleId": rid, "action": "set_buffer_distance_m",
                          "bufferDistanceM": HYPOTHETICAL_SETBACK_M}]))

            elif sem in ("conditional", "attention", "compensation"):
                label = {"conditional": "conditional overlay", "attention": "attention marker",
                         "compensation": "compensation marker"}[sem]
                drafts.append(self._spec(
                    f"SC-{rid}-HARD", f"{rid}: {label} enforced as hard exclusion",
                    object_type,
                    {"type": "policy_variant", "normCardId": nc,
                     "provenanceNote": f"{nc} carries a {label} on rule {rid} in the "
                                       f"baseline; this variant executes the strict reading "
                                       f"(hard exclusion) instead."},
                    [{"ruleId": rid, "action": "set_semantics", "zoneSemantics": "exclusion"}]))
                if buf:
                    for tag, factor in (("HALF", 0.5), ("DOUBLE", 2.0)):
                        new_d = round(float(buf) * factor, 3)
                        drafts.append(self._spec(
                            f"SC-{rid}-HARD-{tag}",
                            f"{rid}: enforced as exclusion at {new_d:g} m "
                            f"({factor:g}x the cited buffer)",
                            object_type,
                            {"type": "norm_variance", "normCardId": nc,
                             "variedAspect": f"buffer_distance {buf:g} m -> {new_d:g} m, "
                                             f"{label} -> hard exclusion",
                             "provenanceNote": f"{nc} cites the {buf:g} m figure; the "
                                               f"{new_d:g} m variant and the hard-exclusion "
                                               f"enforcement are this scenario's parameters."},
                            [{"ruleId": rid, "action": "set_semantics", "zoneSemantics": "exclusion"},
                             {"ruleId": rid, "action": "set_buffer_distance_m",
                              "bufferDistanceM": new_d}]))

            elif sem == "inclusion" and buf:
                for tag, factor in (("HALF", 0.5), ("DOUBLE", 2.0)):
                    new_d = round(float(buf) * factor, 3)
                    drafts.append(self._spec(
                        f"SC-{rid}-BUF-{tag}",
                        f"{rid}: inclusion buffer {buf:g} m -> {new_d:g} m",
                        object_type,
                        {"type": "norm_variance", "normCardId": nc,
                         "variedAspect": f"inclusion buffer_distance {buf:g} m -> {new_d:g} m",
                         "provenanceNote": f"{nc} cites the {buf:g} m figure; the {new_d:g} m "
                                           f"variant is this scenario's parameter."},
                        [{"ruleId": rid, "action": "set_buffer_distance_m",
                          "bufferDistanceM": new_d}]))

        accepted = drafts[:max_scenarios]
        for d in drafts[max_scenarios:]:
            cuts.append({"kind": "budget-cut", "specId": d["id"],
                         "reason": f"effort budget: max_scenarios={max_scenarios}"})
        # validate every accepted draft (V0 before the engine ever sees it)
        for spec in accepted:
            contracts.validate(spec, "scenario-spec")
        return accepted, cuts

    @staticmethod
    def _spec(sid: str, name: str, object_type: str, basis: Dict[str, Any],
              mutations: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"id": sid, "name": name, "objectType": object_type,
                "basis": basis, "mutations": mutations,
                "proposedBy": AUTHOR_DETERMINISTIC}

    @staticmethod
    def _abstention_topics(baseline: Mapping[str, Any]) -> List[str]:
        ledger = _load_optional(baseline, "normcards-rejected.json", {})
        topics = [str(a.get("topic") or a.get("onderwerp") or "")
                  for a in ledger.get("abstentions", [])]
        return [t for t in topics if t][:6]


# --------------------------------------------------------------------------- #
# LLM author (seam S7 — proposals only, gated before execution)
# --------------------------------------------------------------------------- #

class LLMScenarioAuthor:
    """Proposes ScenarioSpecs from an OpenAI-compatible chat endpoint.

    Configuration (both optional; the author refuses to run without an
    endpoint — it never falls back to guessing):

    * ``LDT_SCENARIO_LLM_ENDPOINT`` — e.g. ``http://localhost:8000/v1``
      (vLLM/Ollama serving an open model, per paper B's constraint)
    * ``LDT_SCENARIO_LLM_MODEL``    — model name (default ``open-model-local``)

    ``llm_call`` is injectable for offline tests: ``callable(endpoint, model,
    system, user, timeout) -> str``.
    """

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None,
                 llm_call: Optional[Callable[..., str]] = None,
                 timeout: float = 120.0) -> None:
        self.endpoint = endpoint if endpoint is not None else os.environ.get("LDT_SCENARIO_LLM_ENDPOINT", "")
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or self._http_chat_completions
        self.timeout = timeout

    # -- transport -----------------------------------------------------------

    @staticmethod
    def _http_chat_completions(endpoint: str, model: str, system: str, user: str,
                               timeout: float) -> str:
        import requests  # toolchain dependency; only imported when actually used

        resp = requests.post(
            f"{endpoint.rstrip('/')}/chat/completions",
            json={"model": model, "temperature": 0,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # -- prompt ---------------------------------------------------------------

    @staticmethod
    def system_prompt() -> str:
        return (
            "You are a scenario author for a regulatory opportunity-zone pipeline "
            "(Dutch omgevingswet). You PROPOSE what-if scenarios as JSON; a "
            "deterministic engine executes them and a critic validates them. You "
            "never decide. Rules: (1) emit a JSON array of scenario objects and "
            "nothing else; (2) copy every ruleId and normCardId VERBATIM from the "
            "provided digest — never invent ids; (3) mutations may only be "
            "drop | set_semantics | set_buffer_distance_m, each with its required "
            "fields; (4) every scenario declares its basis: norm_variance (varies "
            "a cited rule's parameter; requires normCardId + variedAspect), "
            "policy_variant (flips a documented discretionary choice; requires "
            "normCardId) or hypothetical (no legal grounding; requires rationale — "
            "use it only for topics the abstention list marks as uncited); (5) "
            "prefer scenarios a provincial policy maker would actually deliberate; "
            "(6) do not exceed the given maximum number of scenarios."
        )

    @staticmethod
    def user_prompt(digest: Mapping[str, Any]) -> str:
        return (
            "Baseline-run digest (the ONLY ids you may reference):\n"
            + json.dumps(digest, ensure_ascii=False, indent=1)
        )

    # -- proposal pipeline ------------------------------------------------------

    def propose(
        self, baseline: Mapping[str, Any], max_scenarios: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not self.endpoint:
            raise ScenarioAuthorError(
                "LLMScenarioAuthor requires LDT_SCENARIO_LLM_ENDPOINT (an "
                "OpenAI-compatible local/open-model endpoint); refusing to guess"
            )
        digest = build_llm_digest(baseline, max_scenarios)
        raw = self._llm_call(self.endpoint, self.model, self.system_prompt(),
                             self.user_prompt(digest), self.timeout)
        items = self._extract_json_array(raw)
        rule_ids = {str(r.get("id")) for r in baseline["formalrules"]}
        card_ids = {str(c.get("id")) for c in baseline["normcards"]}

        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        seen_ids = set()
        proposed_by = f"{AUTHOR_LLM}#{self.model}"
        for item in items:
            if not isinstance(item, dict):
                rejected.append({"kind": "not-an-object", "proposal": item,
                                 "reason": "array item is not a JSON object"})
                continue
            sid = str(item.get("id") or "")
            if sid in seen_ids:
                rejected.append({"kind": "duplicate-id", "specId": sid,
                                 "reason": "scenario id already accepted"})
                continue
            original_by = item.get("proposedBy")
            item = dict(item)
            item["proposedBy"] = proposed_by  # the seam owns identity, not the model
            try:
                contracts.validate(item, "scenario-spec")
            except contracts.ContractError as exc:
                rejected.append({"kind": "schema-invalid", "specId": sid or "(no id)",
                                 "reason": str(exc), "proposal": item,
                                 "modelProposedBy": original_by})
                continue
            bad_rules = [m["ruleId"] for m in item["mutations"]
                         if str(m.get("ruleId")) not in rule_ids]
            if bad_rules:
                rejected.append({"kind": "unknown-rule-id", "specId": sid,
                                 "reason": f"rule ids not in the baseline: {bad_rules}",
                                 "proposal": item})
                continue
            nc_ref = item["basis"].get("normCardId")
            if nc_ref and nc_ref not in card_ids:
                rejected.append({"kind": "unknown-normcard-id", "specId": sid,
                                 "reason": f"normCardId {nc_ref} not in the baseline",
                                 "proposal": item})
                continue
            if item["objectType"] != baseline["request"].get("objectType"):
                rejected.append({"kind": "object-type-mismatch", "specId": sid,
                                 "reason": "objectType does not match the baseline request",
                                 "proposal": item})
                continue
            if len(accepted) >= max_scenarios:
                rejected.append({"kind": "budget-cut", "specId": sid,
                                 "reason": f"effort budget: max_scenarios={max_scenarios}",
                                 "proposal": item})
                continue
            seen_ids.add(sid)
            note = {"modelProposedBy": original_by} if original_by else {}
            if note:
                item = {**item, "notes": json.dumps(note)}
            accepted.append(item)
        return accepted, rejected

    @staticmethod
    def _extract_json_array(raw: str) -> List[Any]:
        text = str(raw).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            lo, hi = text.find("["), text.rfind("]")
            if lo == -1 or hi <= lo:
                raise ScenarioAuthorError(
                    f"LLM response contains no JSON array (first 200 chars: {text[:200]!r})"
                )
            parsed = json.loads(text[lo:hi + 1])
        if isinstance(parsed, dict):
            parsed = parsed.get("scenarios") or [parsed]
        if not isinstance(parsed, list):
            raise ScenarioAuthorError("LLM response did not parse to a JSON array")
        return parsed


def build_llm_digest(baseline: Mapping[str, Any], max_scenarios: int) -> Dict[str, Any]:
    """Compact, id-complete digest of the baseline run for the LLM prompt."""
    rules = [r for r in baseline["formalrules"] if r.get("status") == "formalized"]
    cards = {str(c.get("id")): c for c in baseline["normcards"]}
    abst = _load_optional(baseline, "normcards-rejected.json", {})
    stats = {str(s.get("ruleId")): s for s in _load_optional(baseline, "rule-stats.json", [])}
    return {
        "objectType": baseline["request"].get("objectType"),
        "maxScenarios": max_scenarios,
        "formalizedRules": [
            {
                "ruleId": r["id"],
                "normCardId": r.get("normCardId"),
                "zoneSemantics": r.get("zoneSemantics"),
                "bufferDistanceM": (r.get("zoneSelector") or {}).get("bufferDistanceM"),
                "zoneIds": (r.get("zoneSelector") or {}).get("zoneIds"),
                "zoneFootprintKm2": (stats.get(str(r["id"])) or {}).get("zoneIntersectAoiKm2"),
                "article": (cards.get(str(r.get("normCardId"))) or {}).get("source", {}).get("article"),
            }
            for r in rules
        ],
        "ambiguousRuleCount": sum(1 for r in baseline["formalrules"]
                                  if r.get("status") == "ambiguous"),
        "abstentionTopics": [t for t in (str(a.get("topic") or a.get("onderwerp") or "")
                                         for a in abst.get("abstentions", [])) if t],
        "mutationVocabulary": {
            "drop": "remove the rule from execution",
            "set_semantics": "reclassify the rule (requires zoneSemantics)",
            "set_buffer_distance_m": "set/replace the rule's buffer (requires bufferDistanceM, metres)",
        },
        "basisVocabulary": {
            "norm_variance": "requires normCardId + variedAspect",
            "policy_variant": "requires normCardId",
            "hypothetical": "requires rationale; use ONLY for abstention topics",
        },
    }
