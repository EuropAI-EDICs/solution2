"""PoC-1 GenAI seams S1/S2: live LLM legs for Norm Analyst & Norm Formalizer.

Doctrine (docs/GENAI_SEAMS.md): the model *proposes*, deterministic gates
*dispose*, a human decides. Both hooks are strictly propose-only:

* **S1 — :class:`LLMNormAnalystHook`** implements the existing
  ``llm_hook(evidence, source) -> {"claim", "confidence"}`` contract of
  ``NormAnalyst``: the model may refine the English claim summary and the
  confidence. The citation (docId/article/version/quote/uri), legal force,
  theme and geo binding are unreachable by construction — the hook's return
  value is merged into exactly two fields, and the card is still
  schema-validated (V0).
* **S2 — :class:`LLMFormalizerHook`** proposes formalizations for cards the
  deterministic template table deliberately leaves ``ambiguous`` *for lack of
  a template*. Curated abstentions (templates with kind ``ambiguous`` /
  ``reject``) are never re-proposed — the model cannot talk a curated
  abstention out of its reason. A proposal becomes ``formalized`` only after
  the deterministic gates below; anything else stays ``ambiguous`` with a
  ledger entry (never guessed, never silent).

S2 dispose-gates (all deterministic, in :meth:`LLMFormalizerHook.__call__`
plus the FormalRule schema/V0 in ``NormFormalizer``):

1. proposal shape: ``kind`` ∈ inclusion|exclusion|attention|conditional,
   ``zoneIds`` non-empty, ``conditions`` well-formed, ``rationale`` ≥ 25 chars;
2. zone grounding: proposed ``zoneIds`` ⊆ the card's own ``geoBinding``
   zoneIds when the card carries one, else ⊆ the run's allowed zone ids
   (registry aliases ∪ template zones) — a fabricated zone key can never
   reach the zone engine;
3. quote grounding: every numeric condition ``value`` occurs verbatim in the
   card's Dutch quote (plain and integer spellings; sign folded) — the S7
   buffer-distance lesson applied at formalization time;
4. identity stamping: the seam stamps ``llm-proposal.<model-slug>`` into
   ``extractedBy`` / ``formalizedBy`` (schema ``agent#version`` pattern); the
   model never names itself.

Config (env, prefix ``LDT_NORM_LLM``): ``_ENDPOINT`` (required at call
time), ``_MODEL``, ``_API`` = ``openai``|``ollama``, ``_TIMEOUT``,
``_DISABLE_THINK``. Unconfigured/unreachable → :class:`NormLLMError`; the
caller (``poc/run.py``) falls back loudly to the deterministic path and
records the reason in ``norm-llm-ledger.json``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from pipeline.llm_transport import (
    LLMTransport,
    LLMTransportError,
    extract_json_object,
    model_slug,
)

NORM_ENV_PREFIX = "LDT_NORM_LLM"

#: schema band for NormCard.claim (minLength) and a sane upper bound
CLAIM_MIN_CHARS = 25
CLAIM_MAX_CHARS = 600

#: allowed proposal kinds → (rule_type, zone_semantics, selection, executable_ref)
KIND_MAP: Dict[str, Dict[str, str]] = {
    "inclusion": {
        "rule_type": "zone_inclusion",
        "zone_semantics": "inclusion",
        "selection": "within",
        "executable_ref": "engine.zone.within@poc-v1",
    },
    "exclusion": {
        "rule_type": "zone_exclusion",
        "zone_semantics": "exclusion",
        "selection": "outside",
        "executable_ref": "engine.zone.exclude_within@poc-v1",
    },
    "attention": {
        "rule_type": "zone_attention",
        "zone_semantics": "attention",
        "selection": "within",
        "executable_ref": "engine.zone.buffer@poc-v1",
    },
    "conditional": {
        "rule_type": "zone_conditional",
        "zone_semantics": "conditional",
        "selection": "within",
        "executable_ref": "engine.zone.within@poc-v1",
    },
}

_ALLOWED_OPERATORS = {">=", "<=", ">", "<", "==", "!=", "within", "outside"}


class NormLLMError(ValueError):
    """Mode misuse or unavailable transport (never for a single bad proposal —
    those land in the hook's rejection ledger)."""


def _number_in_quote(value: Any, quote: str) -> bool:
    """Verbatim-numeral grounding: every accepted spelling of the value must
    appear in the quote (one is enough); sign folded; Dutch decimal comma and
    thousands dot both tolerated."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return True  # non-numeric values are grounded by V2 card linkage
    spellings = {str(value)}
    if isinstance(value, float) and value.is_integer():
        spellings.add(str(int(value)))
    if isinstance(value, (int, float)):
        dec = re.sub(r"[-+]", "", f"{value:g}")
        spellings.add(dec.replace(".", ","))  # Dutch decimal comma
        if abs(value) >= 1000:
            whole = int(abs(value))
            spellings.add(f"{whole:,}".replace(",", "."))  # Dutch thousands dot
    folded = quote.replace("−", "-")
    return any(sp and sp in folded for sp in spellings)


class _BaseHook:
    def __init__(self, *, llm_call=None, endpoint: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None,
                 max_tokens: int = 2048) -> None:
        self.transport = LLMTransport(
            NORM_ENV_PREFIX, endpoint=endpoint, model=model,
            timeout=timeout, llm_call=llm_call, max_tokens=max_tokens,
        )
        self.rejected: List[Dict[str, Any]] = []
        self.accepted = 0

    # -- shared plumbing --------------------------------------------------------

    @property
    def stamp(self) -> str:
        """Identity stamp for the agentRun fields (the seam stamps, not the model)."""
        return f"llm-proposal.{model_slug(self.transport.model)}"

    def _chat_raw(self, system: str, user: str) -> str:
        """Transport-level call; every wire/config failure is a loud
        :class:`NormLLMError` (run.py falls back to the deterministic leg).
        Parsing the response stays with the caller so a *single* unparseable
        answer is a per-item ledger rejection, not a leg failure."""
        try:
            return self.transport.chat(system, user)
        except LLMTransportError as exc:
            raise NormLLMError(str(exc)) from exc
        except Exception as exc:  # requests errors (HTTP 5xx, connection refused…)
            raise NormLLMError(f"transport failure: {exc}") from exc

    def _parse_object(self, raw: str, *, card_id: str) -> Optional[Dict[str, Any]]:
        """Parse one JSON object; ledger-reject (return None) when unparseable."""
        try:
            return extract_json_object(raw)
        except LLMTransportError as exc:
            self.rejected.append({
                "kind": "unparseable-response", "cardId": card_id, "reason": str(exc),
                "rawHead": raw[:200],
            })
            return None


class LLMNormAnalystHook(_BaseHook):
    """S1: ``callable(evidence, source) -> {"claim", "confidence"} | None``.

    Gates: claim is a string within ``[CLAIM_MIN_CHARS, CLAIM_MAX_CHARS]``;
    confidence clamped into the schema band ``[0, 1]`` (clamping recorded in
    the ledger). Malformed output → ledger entry + ``None`` (deterministic
    fallback claim stays). Transport-level failures raise
    :class:`NormLLMError` — run.py turns those into a loud deterministic
    fallback for the whole leg.
    """

    def __call__(self, evidence: Mapping[str, Any],
                 source: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        ev_id = evidence.get("id", "?")
        raw = self._chat_raw(self._system_prompt(), self._user_prompt(evidence, source))
        proposal = self._parse_object(raw, card_id=ev_id)
        if proposal is None:
            return None

        claim = proposal.get("claim")
        if not isinstance(claim, str) or not (CLAIM_MIN_CHARS <= len(claim.strip()) <= CLAIM_MAX_CHARS):
            self.rejected.append({
                "kind": "claim-invalid", "evidenceId": ev_id,
                "reason": f"claim must be a {CLAIM_MIN_CHARS}-{CLAIM_MAX_CHARS} char string",
                "proposal": proposal,
            })
            return None
        claim = claim.strip()
        confidence = proposal.get("confidence")
        clamped = None
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            self.rejected.append({
                "kind": "confidence-invalid", "evidenceId": ev_id,
                "reason": "confidence must be a number in [0, 1]",
                "proposal": proposal,
            })
            return None
        if not (0.0 <= float(confidence) <= 1.0):
            clamped = min(1.0, max(0.0, float(confidence)))
        self.accepted += 1
        out: Dict[str, Any] = {"claim": claim, "confidence": clamped if clamped is not None else float(confidence)}
        if clamped is not None:
            out["notes"] = f"confidence clamped to schema band [0,1] (was {confidence})"
        return out

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a legal-recon assistant for a Dutch omgevingswet pipeline. "
            "You PROPOSE an English summary (claim) and a confidence for one "
            "evidence record; a deterministic critic validates it. You never "
            "decide. Rules: (1) answer with a single JSON object and nothing "
            "else; (2) the claim summarizes what the quoted article/toelichting "
            "actually says about the spatial activity — never add obligations, "
            "distances or zones that are not in the verbatim Dutch quote; (3) "
            f"the claim is English, {CLAIM_MIN_CHARS}-{CLAIM_MAX_CHARS} "
            "characters; (4) confidence is a number between 0 and 1 reflecting "
            "how directly the quote supports the claim. Shape: "
            '{"claim": "...", "confidence": 0.9}'
        )

    @staticmethod
    def _user_prompt(evidence: Mapping[str, Any], source: Mapping[str, Any]) -> str:
        import json as _json

        digest = {
            "evidenceId": evidence.get("id"),
            "article": evidence.get("article"),
            "instrument": evidence.get("instrument"),
            "theme": evidence.get("theme"),
            "quote_nl": evidence.get("quote_nl"),
            "notes": evidence.get("notes"),
            "source": {
                "docId": evidence.get("sourceId"),
                "version": source.get("version"),
                "url": evidence.get("url") or source.get("url"),
            },
        }
        return (
            "Evidence record (the ONLY basis for your claim — the quote is "
            "verbatim and authoritative):\n"
            + _json.dumps(digest, ensure_ascii=False, indent=1)
        )


class LLMFormalizerHook(_BaseHook):
    """S2: ``callable(card: dict) -> template-spec-shaped proposal | None``.

    Consulted by ``NormFormalizer`` only for cards without a deterministic
    template. The returned proposal is a *validated* dict::

        {"kind": "inclusion|exclusion|attention|conditional",
         "zoneIds": ["gebied_..."],
         "bufferDistanceM": 300,            # attention only, optional
         "conditions": [{"parameter": "...", "operator": ">=", "value": 3, "unit": "MW"}],
         "rationale": "why this reading follows from the quote"}

    ``NormFormalizer`` (not the model) assembles the FormalRule from it,
    reusing the card's own geoBinding for geometrySource/gioJoinId — the
    model can never inject a geometry source or GIO join id.
    """

    def __init__(self, allowed_zone_ids: Sequence[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.allowed_zone_ids = set(allowed_zone_ids)

    def __call__(self, card: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        card_id = card.get("evidenceId") or (card.get("id") or "?")
        quote = ((card.get("source") or {}).get("quote")) or ""
        raw = self._chat_raw(self._system_prompt(quote), self._user_prompt(card))
        proposal = self._parse_object(raw, card_id=card_id)
        if proposal is None:
            return None
        if proposal.get("propose") is False:
            return None  # explicit decline — not a rejection

        def reject(kind: str, reason: str) -> None:
            self.rejected.append({"kind": kind, "cardId": card_id,
                                  "reason": reason, "proposal": proposal})

        kind = proposal.get("kind")
        if kind not in KIND_MAP:
            reject("kind-invalid", f"kind must be one of {sorted(KIND_MAP)}")
            return None

        zone_ids = proposal.get("zoneIds")
        if not isinstance(zone_ids, list) or not zone_ids or not all(isinstance(z, str) for z in zone_ids):
            reject("zoneids-invalid", "zoneIds must be a non-empty array of strings")
            return None
        card_zones = set(((card.get("geoBinding") or {}).get("zoneIds")) or [])
        allowed = card_zones if card_zones else self.allowed_zone_ids
        unknown = [z for z in zone_ids if z not in allowed]
        if unknown:
            reject(
                "zone-not-grounded",
                f"zone ids not available for this card (unknown: {unknown}); "
                "a fabricated zone key can never reach the zone engine",
            )
            return None

        conditions = proposal.get("conditions", [])
        if not isinstance(conditions, list):
            reject("conditions-invalid", "conditions must be an array")
            return None
        for cond in conditions:
            if not isinstance(cond, dict) or not cond.get("parameter") or cond.get("operator") not in _ALLOWED_OPERATORS or "value" not in cond:
                reject("condition-invalid", f"malformed condition: {cond!r}")
                return None
            if not _number_in_quote(cond.get("value"), quote):
                reject(
                    "number-not-in-quote",
                    f"numeric value {cond.get('value')!r} does not occur verbatim "
                    "in the card's quote (quote grounding)",
                )
                return None

        buffer_m = proposal.get("bufferDistanceM")
        if buffer_m is not None:
            if kind != "attention" or not isinstance(buffer_m, (int, float)):
                reject("buffer-invalid", "bufferDistanceM only allowed (as a number) for kind=attention")
                return None
            if not _number_in_quote(buffer_m, quote):
                reject("number-not-in-quote",
                       f"bufferDistanceM {buffer_m!r} does not occur verbatim in the card's quote")
                return None

        rationale = proposal.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < CLAIM_MIN_CHARS:
            reject("rationale-invalid", f"rationale must be ≥ {CLAIM_MIN_CHARS} chars")
            return None

        self.accepted += 1
        return {
            "kind": kind,
            "zoneIds": zone_ids,
            **({"bufferDistanceM": buffer_m} if buffer_m is not None else {}),
            "conditions": conditions,
            "rationale": rationale.strip(),
        }

    @staticmethod
    def _system_prompt(quote: str) -> str:
        return (
            "You are a norm-formalization assistant for a Dutch omgevingswet "
            "pipeline. A deterministic template table has NO entry for the card "
            "below, so it stays 'ambiguous'. You may PROPOSE a formalization; a "
            "deterministic critic gates it and a human decides. You never "
            "decide. Rules: (1) answer with a single JSON object and nothing "
            "else; (2) propose ONLY what the verbatim Dutch quote supports — "
            "every numeric value you use must literally appear in the quote; "
            "(3) zoneIds must come from the allowed list in the input; (4) if "
            "the quote is procedural or you cannot ground a zone, decline by "
            "returning {\"propose\": false}. Shape: "
            '{"kind": "inclusion|exclusion|attention|conditional", '
            '"zoneIds": ["..."], "bufferDistanceM": 300, '
            '"conditions": [{"parameter": "...", "operator": ">=", "value": 3, "unit": "MW"}], '
            '"rationale": "why this reading follows from the quote"} '
            "(omit bufferDistanceM unless kind=attention; omit conditions when empty)"
        )

    def _user_prompt(self, card: Mapping[str, Any]) -> str:
        import json as _json

        gb = card.get("geoBinding") or {}
        digest = {
            "cardId": card.get("id"),
            "evidenceId": card.get("evidenceId"),
            "claim": card.get("claim"),
            "theme": card.get("theme"),
            "instrument": card.get("instrument"),
            "quote": (card.get("source") or {}).get("quote"),
            "objectType": (card.get("appliesTo") or {}).get("objectType"),
            "geoBindingZoneIds": gb.get("zoneIds") or "(none)",
        }
        # The model must see the exact allowed set: the card's own geo binding
        # when present, otherwise the run's zone registry aliases. Anything
        # else is deterministic-rejected below — but the prompt should make
        # the right answer reachable.
        card_zones = gb.get("zoneIds") or []
        allowed = sorted(set(card_zones) | (set() if card_zones else self.allowed_zone_ids))
        return (
            "NormCard without a deterministic template (the quote is verbatim "
            "and authoritative):\n"
            + _json.dumps(digest, ensure_ascii=False, indent=1)
            + "\nallowedZoneIds (you MUST pick from these; anything else is "
            "rejected by the deterministic gate): "
            + _json.dumps(allowed, ensure_ascii=False)
        )


def build_analyst_hook(**kwargs) -> LLMNormAnalystHook:
    hook = LLMNormAnalystHook(**kwargs)
    if not hook.transport.available:
        raise NormLLMError(
            f"{NORM_ENV_PREFIX}_ENDPOINT is not configured; the S1 LLM leg "
            "refuses to run without a local open-model endpoint"
        )
    return hook


def build_formalizer_hook(allowed_zone_ids: Sequence[str], **kwargs) -> LLMFormalizerHook:
    hook = LLMFormalizerHook(allowed_zone_ids, **kwargs)
    if not hook.transport.available:
        raise NormLLMError(
            f"{NORM_ENV_PREFIX}_ENDPOINT is not configured; the S2 LLM leg "
            "refuses to run without a local open-model endpoint"
        )
    return hook
