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
NARRATOR_LLM_RUN = "llm-narrator"

#: default exploration distance (m) for hypothetical setbacks on un-buffered
#: exclusion rules — mirrors the demo sets; recorded in every proposal
HYPOTHETICAL_SETBACK_M = 500.0

DETERMINISTIC_AUTHOR_RUN = AUTHOR_DETERMINISTIC


def _llm_timeout(default: float = 180.0) -> float:
    try:
        return float(os.environ.get("LDT_SCENARIO_LLM_TIMEOUT", default))
    except ValueError:
        return default


def strip_reasoning(text: str) -> str:
    """Remove ``<think>…</think>`` blocks some open models emit before the
    answer (e.g. Qwen3 reasoning mode); harmless when absent."""
    return re.sub(r"<think>.*?</think>", "", str(text), flags=re.S).strip()


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

#: benign field aliases some models emit despite the vocabulary in the prompt;
#: normalized transparently at the seam BEFORE validation — every other key
#: must match the schema exactly or the proposal is ledgered as invalid
_SPEC_ALIASES = {"scenarioId": "id", "title": "name", "specId": "id"}
_MUTATION_ALIASES = {"type": "action", "distance": "bufferDistanceM",
                     "distanceM": "bufferDistanceM"}
#: keys a flat basis form leaves at the top level
_BASIS_BODY_KEYS = ("normCardId", "variedAspect", "rationale")


def _normalize_aliases(item: Dict[str, Any], baseline_object_type: str = "") -> Dict[str, Any]:
    item = dict((_SPEC_ALIASES.get(k, k), v) for k, v in item.items())
    fixes: List[str] = []
    # flat basis form: "basis": "policy_variant", "normCardId": "NC-Z-03", …
    if isinstance(item.get("basis"), str):
        basis = {"type": item["basis"]}
        for k in _BASIS_BODY_KEYS:
            if k in item:
                basis[k] = item.pop(k)
                fixes.append(f"basis.{k} folded from flat form")
        item["basis"] = basis
    # mutation action aliases
    if isinstance(item.get("mutations"), list):
        fixed = []
        for m in item["mutations"]:
            if isinstance(m, dict):
                fixed.append(dict((_MUTATION_ALIASES.get(k, k), v) for k, v in m.items()))
            else:
                fixed.append(m)
        item["mutations"] = fixed
    # benignly-missing form fields the seam completes deterministically (no
    # legal content is invented — objectType is the baseline's, provenanceNote
    # is the seam's own disclosure, name is derived from the id)
    if "name" not in item and item.get("id"):
        item["name"] = f"Model proposal {item['id']}"
        fixes.append("name synthesized from id")
    if not item.get("objectType") and baseline_object_type:
        item["objectType"] = baseline_object_type
        fixes.append("objectType defaulted to the baseline request's")
    if isinstance(item.get("basis"), dict) and not item["basis"].get("provenanceNote"):
        btype = item["basis"].get("type", "")
        item["basis"]["provenanceNote"] = (
            ("NOT legally grounded: model-proposed hypothetical (no normCardId cited); "
             "analytical variation only" if btype == "hypothetical" else
             f"model-proposed {btype or 'variant'} on the cited norm card; the "
             "deterministic critic re-grounds every id against the baseline run")
        )
        fixes.append("basis.provenanceNote synthesized by the seam")
    if fixes and "notes" in item and isinstance(item["notes"], str):
        item["notes"] = (item["notes"].rstrip(". ") + ". "
                         + " Seam normalized: " + "; ".join(fixes) + ".")
    return item


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
                 timeout: Optional[float] = None) -> None:
        self.endpoint = endpoint if endpoint is not None else os.environ.get("LDT_SCENARIO_LLM_ENDPOINT", "")
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or self._resolve_transport()
        self.timeout = timeout if timeout is not None else _llm_timeout()

    @staticmethod
    def _resolve_transport() -> Callable[..., str]:
        """``LDT_SCENARIO_LLM_API`` selects the wire format: ``openai``
        (default, any OpenAI-compatible server) or ``ollama`` (native
        /api/chat — the ONLY way to reliably disable thinking mode on
        qwen3-style models served by Ollama; their /v1 layer ignores
        ``think: false`` and burns the whole completion budget on <think>)."""
        if os.environ.get("LDT_SCENARIO_LLM_API", "openai").lower() == "ollama":
            return LLMScenarioAuthor._ollama_chat
        return LLMScenarioAuthor._http_chat_completions

    # -- transport -----------------------------------------------------------

    @staticmethod
    def _http_chat_completions(endpoint: str, model: str, system: str, user: str,
                               timeout: float) -> str:
        import requests  # toolchain dependency; only imported when actually used

        # Ollama's OpenAI-compat layer honours "think": false to disable
        # reasoning mode (qwen3-style models otherwise emit very long <think>
        # chains that can occupy the single-generation server for many
        # minutes); unknown fields are ignored by vLLM/LM Studio. Set
        # LDT_SCENARIO_LLM_DISABLE_THINK=0 to omit the flag. max_tokens bounds
        # runaway generations client-independently.
        payload: Dict[str, Any] = {
            "model": model, "temperature": 0, "max_tokens": 4096,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if os.environ.get("LDT_SCENARIO_LLM_DISABLE_THINK", "1") != "0":
            payload["think"] = False
        resp = requests.post(
            f"{endpoint.rstrip('/')}/chat/completions",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _ollama_chat(endpoint: str, model: str, system: str, user: str,
                     timeout: float) -> str:
        import requests  # toolchain dependency; only imported when actually used

        base = endpoint.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        payload: Dict[str, Any] = {
            "model": model, "stream": False,
            "options": {"temperature": 0, "num_predict": 4096},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        if os.environ.get("LDT_SCENARIO_LLM_DISABLE_THINK", "1") != "0":
            payload["think"] = False  # native API honours this (the /v1 layer does not)
        resp = requests.post(f"{base}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("done", True):
            raise ScenarioAuthorError(f"ollama chat not done: {str(body)[:200]}")
        return (body.get("message") or {}).get("content") or ""

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
            "(6) do not exceed the given maximum number of scenarios; (7) every "
            "object must have EXACTLY this shape (fill name/objectType yourself; "
            "provenanceNote is your own one-sentence provenance disclosure):\n"
            '{"id": "SC-…-SHORT-SLUG", "name": "human-readable variant name", '
            '"objectType": "<the digest objectType>", '
            '"basis": {"type": "policy_variant", "normCardId": "NC-…", '
            '"provenanceNote": "one sentence"}, '
            '"mutations": [{"ruleId": "FR-…", "action": "set_buffer_distance_m", '
            '"bufferDistanceM": 300}]}'
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
        # identity stamp must satisfy the schema pattern (lowercase slug); the
        # raw model tag (e.g. "Qwen3.6:27B-MLX") is sanitized deterministically
        model_slug = re.sub(r"[^a-z0-9]+", "-", self.model.lower()).strip("-")
        proposed_by = f"{AUTHOR_LLM}#{model_slug}"
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
            base_otype = str(baseline.get("objectType")
                             or (baseline.get("request") or {}).get("objectType", ""))
            item = _normalize_aliases(item, base_otype)
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
        text = strip_reasoning(raw)
        candidates: List[str] = [text]
        # fenced ```json blocks first (models often wrap arrays), then the
        # whole (reasoning-stripped) text, then a bracket slice of each
        for m in re.finditer(r"```(?:json)?\s*(.*?)```", text, flags=re.S):
            candidates.append(m.group(1).strip())
        parsed = None
        for cand in candidates:
            for attempt in (cand,):
                try:
                    parsed = json.loads(attempt)
                    break
                except json.JSONDecodeError:
                    lo, hi = attempt.find("["), attempt.rfind("]")
                    if lo != -1 and hi > lo:
                        try:
                            parsed = json.loads(attempt[lo:hi + 1])
                            break
                        except json.JSONDecodeError:
                            continue
            if parsed is not None:
                break
        if parsed is None:
            raise ScenarioAuthorError(
                f"LLM response contains no JSON array (first 200 chars: {text[:200]!r})"
            )
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


# --------------------------------------------------------------------------- #
# LLM narrator (seam S8 — prose over the report, numeric-grounding gated)
# --------------------------------------------------------------------------- #

class LLMScenarioNarrator:
    """Narrates a finished ScenarioReport through the same transport as the
    LLM author. Callable interface: ``narrator(report) -> str``.

    The output is NEVER trusted directly: the deterministic numeric-grounding
    check (``scenarios.check_narrative_grounding``) gates it — every number in
    the prose must resolve to the report, every scenario id must exist. Wrap
    with :func:`make_fallback_narrator` to fall back (loudly) to the
    deterministic narration when the gate rejects the model's prose.
    """

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None,
                 llm_call: Optional[Callable[..., str]] = None,
                 timeout: Optional[float] = None) -> None:
        self.endpoint = (endpoint if endpoint is not None
                         else os.environ.get("LDT_SCENARIO_LLM_ENDPOINT", ""))
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or LLMScenarioAuthor._resolve_transport()
        self.timeout = timeout if timeout is not None else _llm_timeout()

    @staticmethod
    def system_prompt() -> str:
        return (
            "You narrate scenario reports of a regulatory opportunity-zone "
            "pipeline for provincial policy makers. STRICT RULES: (1) use ONLY "
            "numbers that appear in the provided report JSON — you may reformat "
            "them (1181.982 as 1,181.98 or as 'roughly 1,180' is fine ONLY if "
            "you also give the exact figure), never round differently without "
            "the exact number present, never compute new numbers (no sums, "
            "averages or comparisons the report does not state); you may state "
            "a negative delta as its magnitude ('afname van 64.675 km2' for "
            "-64.675) — copy the digits exactly; (2) mention "
            "scenario ids exactly as given (SC-…); (3) no new claims, no legal "
            "advice, no numbers from memory; (4) do NOT characterize the "
            "validation outcome in your own words — you may state the report's "
            "verdict field verbatim, but never use the words fail/failed "
            "unless the report verdict is exactly \"fail\"; (5) 5-8 sentences, "
            "plain text, Dutch policy register is welcome but keep the ids and "
            "units."
        )

    def __call__(self, report: Mapping[str, Any]) -> str:
        if not self.endpoint:
            raise ScenarioAuthorError(
                "LLMScenarioNarrator requires LDT_SCENARIO_LLM_ENDPOINT; "
                "refusing to guess"
            )
        compact = {k: v for k, v in report.items() if not k.startswith("_")}
        raw = self._llm_call(self.endpoint, self.model, self.system_prompt(),
                             json.dumps(compact, ensure_ascii=False), self.timeout)
        return strip_reasoning(raw)


def make_fallback_narrator(narrator: Callable[[Mapping[str, Any]], str],
                           fallback: Callable[[Mapping[str, Any]], str],
                           events: Optional[List[Dict[str, Any]]] = None):
    """Wrap ``narrator`` so a gate rejection falls back loudly, never silently.

    The wrapper runs the deterministic grounding check on the model's prose;
    on pass the prose is used as-is; on failure (or transport error) the
    ``fallback`` narration is published, and the rejection (reason + rejected
    prose) is appended to ``events`` so the CLI can persist it next to the
    artifacts — the rejection is a first-class, visible outcome.
    """
    from pipeline import scenarios  # local import keeps module deps one-way

    events = events if events is not None else []

    def wrapped(report: Mapping[str, Any]) -> str:
        try:
            prose = narrator(report)
        except Exception as exc:  # transport errors fall back too
            events.append({"kind": "narrator-error", "reason": f"{type(exc).__name__}: {exc}",
                           "prose": None})
            return fallback(report)
        check = scenarios.check_narrative_grounding(prose, report)
        if check["status"] == "pass":
            return prose
        events.append({"kind": "narrative-grounding-rejected",
                       "reason": check["detail"], "prose": prose})
        return fallback(report)

    return wrapped
