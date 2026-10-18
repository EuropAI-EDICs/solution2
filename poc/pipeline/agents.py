"""Deterministic PoC implementations of the planning-plane norm agents.

Implements MULTI_AGENT_PLAN.md section 3.2 agents #3 and #4:

* ``NormAnalyst``     — harvests NormCards from a corpus shard (evidence +
  sources). Deterministic by default; an optional ``llm_hook`` (callable)
  can be plugged in by a future deployment to refine English claims. With
  the default ``None`` the agent is fully deterministic, which is what the
  V3 semantic re-execution check relies on.
* ``NormFormalizer``  — converts NormCards into typed FormalRules using
  explicit deterministic templates per theme/card (zone inclusion in
  'Gebied windenergie', exclusion of Natura 2000/ganzenrustgebieden,
  1500 m stiltegebied attention buffer, Groene contour compensation, ...).
  Cards without a deterministic template are flagged ``ambiguous`` (or
  ``rejected``) with a reason — never guessed (cite-or-abstain).

There is NO callable LLM at PoC runtime: every step is a deterministic
implementation behind the agent interface, and every agent boundary emits
JSON validated against poc/schemas/*.schema.json (V0 gate).

Run ``python3 -m pipeline.agents`` (from poc/) to (re)generate the per-track
corpora poc/corpus/normcards-<track>.json and formalrules-<track>.json for
all 13 canonieke tracks (declaratieve bron: pipeline.track_config).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

try:  # normal import when poc/ is on sys.path (tests, python3 -m pipeline.agents)
    from pipeline import contracts, track_config
    from pipeline.contracts import FormalRule, NormCard
except ImportError:  # pragma: no cover - direct script execution inside poc/pipeline
    import contracts as contracts  # type: ignore[no-redef]
    import track_config as track_config  # type: ignore[no-redef]
    from contracts import FormalRule, NormCard  # type: ignore[no-redef]

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus"
SOURCES_PATH = CORPUS_DIR / "sources.json"

#: a complete GIO JOIN-id as used in Bijlage II of CVDR704250
GIO_JOIN_RE = re.compile(
    r"/join/id/regdata/pv26/\d{4}/gio"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"/nld@\d{4}-\d{2}-\d{2};\d+"
)

ANALYST_RUN = "legal-recon-agent#cvdr704250-geldend-2025-10-13"
FORMALIZER_RUN = "norm-formalizer#deterministic-templates-v1"
RUN_DATE = "2026-08-30"

CAVEAT_GIO_ACCESS = (
    "GIO-versie overgenomen uit Bijlage II van CVDR704250 (geldend 13-10-2025); "
    "DSO Omgevingsdocumenten Downloaden API gaf HTTP 401 zonder API-key, dus de "
    "join-id is geciteerd uit de geconsolideerde regelingtekst (S07)"
)
CAVEAT_GIO_TRUNCATED = (
    "GIO staat in Bijlage II van CVDR704250 maar de join-id is slechts afgekapt "
    "overgenomen in de recon-notities; her-verifieer tegen Bijlage II voor V3"
)
#: water-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 2.14-2.16 quote no join-id),
#: so no gioJoinId may be claimed; geometry is served by the agrest IMOW
#: open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
CAVEAT_GIO_WATER = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json)"
)
#: bodem-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 3.7-3.10 and 3.108 quote no
#: join-id), so no gioJoinId may be claimed; geometry is served by the agrest
#: IMOW open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
#: The umbrella alias 'Grondwaterbeschermingszone' was live-verified (task 8)
#: as the exact union of the seven literal designation areas of art. 3.7/3.9/3.10.
CAVEAT_GIO_BODEM = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json): "
    "umbrella 'Grondwaterbeschermingszone', live geverifieerd als de vereniging van "
    "de zeven letterlijke aanwijzingsgebieden van art. 3.7/3.9/3.10 (taak-8-verslag)"
)
#: mobiliteit-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 4.7, 4.47, 4.48, 4.65 and 4.71
#: quote no join-id), so no gioJoinId may be claimed; geometry is served by the
#: agrest IMOW open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
#: The umbrella alias 'Beperkingengebied lokale spoorweg' was live-verified
#: (fase-2 taak 3) as the exact union of Kernzone and Beschermingszone lokale
#: spoorweg (art. 4.46), symmetric difference 0.0000 km2.
CAVEAT_GIO_MOBILITEIT = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json): "
    "umbrella 'Beperkingengebied lokale spoorweg', live geverifieerd als de vereniging "
    "van Kernzone en Beschermingszone lokale spoorweg (art. 4.46, symdiff 0,0000 km2)"
)
#: landschap-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 7.3, 7.3a, 7.4, 7.9, 7.11a and
#: 7.12 quote no join-id), so no gioJoinId may be claimed; geometry is served by
#: the agrest IMOW open-data alias (see run.py::ZONE_SOURCES and layers.json
#: aliasNote). The umbrella aliases 'Gebied cultuurhistorische hoofdstructuur'
#: (art. 7.8, vijf gebieden) and 'Landschap' (art. 7.11, vijf landschappen) were
#: live-verified (fase-2 taak 6) as the exact unions of their constituents
#: (symdiff 0.000004 respectively 0.0000 km2).
CAVEAT_GIO_LANDSCHAP = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json): "
    "umbrella's 'Gebied cultuurhistorische hoofdstructuur' en 'Landschap', live "
    "geverifieerd als de verenigingen van de vijf art.-7.8-gebieden respectievelijk "
    "de vijf art.-7.11-landschappen (symdiff 0,000004 / 0,0000 km2)"
)
#: landbouw-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 8.1-8.7 quote no join-id), so no
#: gioJoinId may be claimed; geometry is served by the agrest IMOW open-data
#: alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
CAVEAT_GIO_LANDBOUW = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json)"
)
#: wonen-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 9.3-9.29 quote no join-id), so
#: no gioJoinId may be claimed; geometry is served by the agrest IMOW open-data
#: alias (see run.py::ZONE_SOURCES and layers.json aliasNote). The
#: Landelijk-gebied, Stiltegebied and Aandachtsgebied-stiltegebied aliases are
#: REUSED from the fase-1 wind track (fase-1 dedup rule: same service+layer).
CAVEAT_GIO_WONEN = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json); "
    "Landelijk gebied / Stiltegebied / Aandachtsgebied stiltegebied hergebruikt uit "
    "de fase-1-wind-track (zelfde service+laag)"
)
#: werken-track zones: werkingsgebieden of the verordening whose GIO join-id is
#: NOT carried by the cited article text (arts. 9.9-9.20 quote no join-id), so
#: no gioJoinId may be claimed; geometry is served by the agrest IMOW open-data
#: alias (see run.py::ZONE_SOURCES and layers.json aliasNote). The
#: Landelijk-gebied and Stedelijk-gebied aliases are REUSED from the fase-3
#: wonen track (fase-1 dedup rule: same service+layer).
CAVEAT_GIO_WERKEN = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json); "
    "Landelijk gebied / Stedelijk gebied hergebruikt uit de fase-3-wonen-track "
    "(zelfde service+laag)"
)
#: recreatie-track zones: werkingsgebieden of the verordening whose GIO join-id
#: is NOT carried by the cited article text (arts. 9.22/9.23 quote no join-id),
#: so no gioJoinId may be claimed; geometry is served by the agrest IMOW
#: open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
CAVEAT_GIO_RECREATIE = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json)"
)
#: biomassa-track zones: werkingsgebieden of the verordening whose GIO join-id
#: is NOT carried by the cited article text (arts. 5.6/5.7 quote no join-id),
#: so no gioJoinId may be claimed; geometry is served by the agrest IMOW
#: open-data alias (see run.py::ZONE_SOURCES and layers.json aliasNote).
CAVEAT_GIO_BIOMASSA = (
    "Werkingsgebied-GIO van CVDR704250 (geldend 13-10-2025); de join-id is niet "
    "overgenomen in de geciteerde artikelttekst en de DSO Omgevingsdocumenten "
    "Downloaden API gaf HTTP 401 zonder API-key, dus geen gioJoinId citeerbaar; "
    "geometrie komt uit de agrest IMOW-open-data-alias (aliasNote in layers.json)"
)
#: energietoets-track (arts. 5.10/5.11): Afdeling 5.3 has NO gebiedsaanwijzing /
#: GIO. Marker geometry is the request AOI (province-wide scope); never a
#: invented net-infrastructure layer or EnergyCast surrogaat.
CAVEAT_AOI_ENERGIETOETS = (
    "Afdeling 5.3 Energietoets (art. 5.10/5.11) kent geen gebiedsaanwijzing/GIO; "
    "marker-geometrie is de request-AOI (provinciebreed toepassingsbereik). Geen "
    "netmodel- of EnergyCast-surrogaat in de PoC — aansluitbaarheid/energieparagraaf "
    "blijven V4-/EnergyCast-seam (SOLUTIONS_ARCHITECTURE §4 B congestion)"
)

# ---------------------------------------------------------------------------
# Deterministic engine operations referenced by FormalRule.executableRef.
# Track B (zone engine) implements these; V3 re-executes them independently.
# ---------------------------------------------------------------------------

ENGINE_OPERATIONS: Dict[str, Dict[str, Any]] = {
    "engine.zone.within@poc-v1": {
        "deterministic": True,
        "description": "Select the part of the area of interest within the zone(s) named by the rule's zoneSelector.",
    },
    "engine.zone.exclude_within@poc-v1": {
        "deterministic": True,
        "description": "Remove from the area of interest everything within the zone(s) named by the rule's zoneSelector (difference).",
    },
    "engine.zone.buffer@poc-v1": {
        "deterministic": True,
        "description": "Buffer the derivedFrom zone by bufferDistanceM metres (EPSG:28992 metric) and select within it.",
    },
    "engine.compensation.ratio@poc-v1": {
        "deterministic": True,
        "description": "Do not eliminate area; attach a compensation requirement (ratio + within-zone) to affected parcels.",
    },
    "engine.procedural.human_review@poc-v1": {
        "deterministic": True,
        "description": "Mark the rule as requiring procedural/human assessment; contributes no geometry by itself.",
    },
    "engine.scope.none@poc-v1": {
        "deterministic": True,
        "description": "No-op: the card is declarative scope or a non-executable duplicate; contributes no geometry.",
    },
}

_REVIEW_REF = "engine.procedural.human_review@poc-v1"
_NOOP_REF = "engine.scope.none@poc-v1"

# ---------------------------------------------------------------------------
# Curated enrichment for the evidence shards (English claims, confidence,
# context tags, geo bindings). Keyed by evidence id; declaratief geladen uit
# poc/tracks/_enrichment/<track>.json. De deterministische replay ervan landt
# in poc/corpus/normcards-<track>.json (see main() and test_contracts.py).
# ---------------------------------------------------------------------------

EVIDENCE_ENRICHMENT: Dict[str, Dict[str, Any]] = track_config.load_enrichment()


def _detect_legal_force(instrument: str) -> str:
    """Deterministically derive legal force from the instrument description."""
    lowered = (instrument or "").lower()
    if "niet-bindende" in lowered or "niet bindende" in lowered:
        return "non_binding"
    if "toelichting" in lowered and "artikeltekst" not in lowered:
        return "interpretive"
    return "binding"


def _default_confidence(legal_force: str) -> float:
    return {"binding": 0.9, "interpretive": 0.8, "non_binding": 0.7}[legal_force]


# ---------------------------------------------------------------------------
# Norm Analyst (plan section 3.2, agent #3)
# ---------------------------------------------------------------------------

class NormAnalyst:
    """Reads a corpus shard (evidence + sources) and emits schema-validated NormCards.

    Deterministic mode (default, ``llm_hook=None``): cards are built from the
    evidence records plus the curated EVIDENCE_ENRICHMENT table; cite-or-abstain
    is enforced by dropping every evidence item whose ``verified`` flag is not
    true (recorded in ``self.rejected`` with a reason).

    ``llm_hook`` (optional): ``callable(evidence: dict, source: dict) -> dict``
    returning e.g. ``{"claim": ..., "confidence": 0.9}``. Proposals are only
    allowed to refine the English claim/confidence — never the citation, legal
    force or geo binding — and the resulting card is still schema-validated.
    """

    agent_name = "legal-recon-agent"

    def __init__(
        self,
        corpus_dir: Optional[Path] = None,
        llm_hook: Optional[Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]] = None,
        run_ref: str = ANALYST_RUN,
    ) -> None:
        self.corpus_dir = Path(corpus_dir) if corpus_dir else CORPUS_DIR
        self.llm_hook = llm_hook
        self.run_ref = run_ref
        self.rejected: List[Dict[str, Any]] = []

    # -- shard loading ------------------------------------------------------

    def _load_sources(self) -> Dict[str, Dict[str, Any]]:
        with (self.corpus_dir / "sources.json").open(encoding="utf-8") as fh:
            return {src["id"]: src for src in json.load(fh)}

    def _load_shard(
        self, shard: Union[str, Path, Sequence[Mapping[str, Any]], Mapping[str, Any]]
    ) -> List[Dict[str, Any]]:
        if isinstance(shard, (str, Path)):
            path = Path(shard)
            if not path.is_absolute():
                path = self.corpus_dir / path
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = shard
        if isinstance(data, Mapping):
            return list(data.get("evidence", []))
        if isinstance(data, Sequence):
            return [dict(item) for item in data]
        raise ValueError(f"unsupported shard type: {type(data).__name__}")

    # -- card building ------------------------------------------------------

    def _fallback_claim(self, ev: Mapping[str, Any]) -> str:
        return (
            f"Deterministic fallback claim: article '{ev.get('article', '?')}' of "
            f"{ev.get('instrument', 'the instrument')} — see the verbatim Dutch quote "
            f"and recon notes; no curated English summary is registered for this evidence id."
        )

    def _to_card(self, ev: Mapping[str, Any], src: Mapping[str, Any]) -> NormCard:
        ev_id = ev["id"]
        enrichment = EVIDENCE_ENRICHMENT.get(ev_id, {})
        instrument = ev.get("instrument", "")
        legal_force = enrichment.get("legalForce") or _detect_legal_force(instrument)
        confidence = float(enrichment.get("confidence", _default_confidence(legal_force)))
        claim = enrichment.get("claim") or self._fallback_claim(ev)
        notes = ev.get("notes")
        extracted_by = self.run_ref

        if self.llm_hook is not None:
            proposal = self.llm_hook(ev, src) or {}
            if proposal.get("claim"):
                claim = str(proposal["claim"])
            if "confidence" in proposal:
                confidence = float(proposal["confidence"])
            # S1 seam stamps identity; the deterministic citation/legal-force/
            # geo-binding fields above are unreachable for the hook by design.
            stamp = getattr(self.llm_hook, "stamp", None)
            if proposal and stamp:
                agent, _, _version = self.run_ref.partition("#")
                extracted_by = f"{agent}#{stamp}"
            seam_bits = []
            if proposal.get("notes"):
                seam_bits.append(str(proposal["notes"]))
            seam_bits.append(
                "llm hook answered (claim/confidence refined)"
                if proposal else "llm hook declined; deterministic replay used"
            )
            notes = ((notes.rstrip(". ") + ". ") if notes else "") + " S1 seam: " + "; ".join(seam_bits) + "."

        card_payload: Dict[str, Any] = {
            "id": f"NC-{ev_id}",
            "evidenceId": ev_id,
            "claim": claim,
            "source": {
                "docId": ev.get("sourceId"),
                "article": ev.get("article"),
                "version": src.get("version"),
                "quote": ev.get("quote_nl"),
                "quoteLanguage": "nl",
                "uri": ev.get("url") or src.get("url"),
                "retrievedAt": src.get("retrieved_at"),
            },
            "instrument": instrument,
            "legalForce": legal_force,
            "theme": ev.get("theme"),
            "confidence": confidence,
            "verified": True,
            "extractedBy": extracted_by,
            "extractedAt": RUN_DATE,
            "appliesTo": {
                "objectType": enrichment.get("objectType", "wind_turbine"),
                "contextTags": enrichment.get("contextTags"),
            },
            "geoBinding": enrichment.get("geoBinding"),
            "notes": notes,
        }
        return NormCard.from_dict(card_payload)  # validates against norm-card.schema.json

    # -- public interface ----------------------------------------------------

    def read(
        self,
        shard: Union[str, Path, Sequence[Mapping[str, Any]], Mapping[str, Any]],
    ) -> List[NormCard]:
        """Harvest NormCards from ``shard``.

        ``shard`` may be: a path to an evidence-*.json file (relative paths
        resolve against the corpus dir), a list of evidence dicts, or a dict
        ``{"evidence": [...], "sources": {...}}``.
        """
        self.rejected = []
        evidence_list = self._load_shard(shard)
        sources = self._load_sources()
        if isinstance(shard, Mapping) and shard.get("sources"):
            extra_sources = shard["sources"]
            if isinstance(extra_sources, Mapping):
                sources.update(dict(extra_sources))
            else:
                sources.update({s["id"]: s for s in extra_sources})

        cards: List[NormCard] = []
        for ev in evidence_list:
            if ev.get("verified") is not True:
                self.rejected.append(
                    {
                        "evidenceId": ev.get("id"),
                        "theme": ev.get("theme"),
                        "article": ev.get("article"),
                        "reason": (
                            "evidence.verified is not true — cite-or-abstain: no NormCard "
                            "without a verified, verbatim citation (docId+article+version+quote+uri)"
                        ),
                    }
                )
                continue
            src = sources.get(ev.get("sourceId", ""), {})
            cards.append(self._to_card(ev, src))
        return cards


# ---------------------------------------------------------------------------
# Norm Formalizer (plan section 3.2, agent #4) — deterministic templates
# ---------------------------------------------------------------------------

def _base_rule(
    card: NormCard,
    *,
    status: str,
    rule_type: str,
    zone_semantics: str,
    executable_ref: str,
    extra_tags: Sequence[str] = (),
    reason: Optional[str] = None,
    rationale: Optional[str] = None,
    zone_selector: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    related: Optional[List[str]] = None,
) -> Dict[str, Any]:
    tags = list(card.appliesTo.contextTags or [])
    for tag in extra_tags:
        if tag not in tags:
            tags.append(tag)
    rule: Dict[str, Any] = {
        "id": f"FR-{card.evidenceId}",
        "normCardId": card.id,
        "status": status,
        "ruleType": rule_type,
        "zoneSemantics": zone_semantics,
        "appliesTo": {"objectType": card.appliesTo.objectType, "contextTags": tags},
        "executableRef": executable_ref,
        "formalizedBy": FORMALIZER_RUN,
        "formalizedAt": RUN_DATE,
    }
    if zone_selector is not None:
        rule["zoneSelector"] = zone_selector
    if conditions is not None:
        rule["conditions"] = conditions
    if related:
        rule["relatedNormCardIds"] = related
    if reason is not None:
        rule["reason"] = reason
    if rationale is not None:
        rule["rationale"] = rationale
    return rule


_NNN_GIO = "/join/id/regdata/pv26/2025/gio3111b509-00cb-46c0-9967-b8102f81c85f/nld@2025-08-18;803"
_GROENE_CONTOUR_GIO = "/join/id/regdata/pv26/2025/gioee37db62-22b1-4334-bf89-7ddf4e5812c6/nld@2025-08-18;798"
_GEBIED_WINDENERGIE_GIO = "/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846"
_GEBIED_KLEINE_WIND_GIO = "/join/id/regdata/pv26/2025/gio73f71441-6b83-4be5-9fef-293714578255/nld@2025-10-10;822"
_LANDELIJK_GEBIED_GIO = "/join/id/regdata/pv26/2025/gio17d47ef4-f140-45b7-8809-c5068d74698f/nld@2025-10-10;843"
_GEBIED_ZONNEVELD_GIO = "/join/id/regdata/pv26/2025/gioa748cb8c-4f7f-4bbb-83d4-54becd3e0d1d/nld@2025-10-10;849"
_OUDE_BOSGROEIPLAATSEN_GIO = "/join/id/regdata/pv26/2025/gio3940cf76-bee0-4a1a-8d51-aa0d49be7153/nld@2025-10-10;842"

#: deterministic templates, keyed by evidence id. kind:
#: inclusion | exclusion | attention | conditional | compensation | ambiguous | reject
TEMPLATE_SPECS: Dict[str, Dict[str, Any]] = track_config.load_templates()


class NormFormalizer:
    """Converts NormCards into typed FormalRules via deterministic templates.

    Every card yields exactly one FormalRule (total coverage by construction):
    status ``formalized`` when a template with zone semantics exists, otherwise
    ``ambiguous`` or ``rejected`` with a mandatory reason — never a guess.
    """

    agent_name = "norm-formalizer"

    def __init__(self, run_ref: str = FORMALIZER_RUN,
                 llm_hook: Optional[Callable[[Mapping[str, Any]], Optional[Mapping[str, Any]]]] = None) -> None:
        self.run_ref = run_ref
        self.llm_hook = llm_hook
        self.last_coverage: Dict[str, int] = {}
        self._llm_proposed = 0

    def formalize(
        self, normcards: Sequence[Union[NormCard, Mapping[str, Any]]]
    ) -> List[FormalRule]:
        cards: List[NormCard] = [
            card if isinstance(card, NormCard) else NormCard.from_dict(card)
            for card in normcards
        ]
        rules = [self._formalize_card(card) for card in cards]
        self._check_integrity(cards, rules)
        counts = {"formalized": 0, "ambiguous": 0, "rejected": 0}
        for rule in rules:
            counts[rule.status] += 1
        self.last_coverage = {
            "input_cards": len(cards),
            "output_rules": len(rules),
            **counts,
            "llm_proposed": self._llm_proposed,
            "llm_rejected": len(self.llm_hook.rejected) if self.llm_hook is not None else 0,
        }
        return rules

    # -- internals ------------------------------------------------------------

    def _llm_rule(self, card: NormCard, proposal: Mapping[str, Any]) -> Dict[str, Any]:
        """Assemble a FormalRule from a *gated* S2 proposal.

        The hook has already validated kind/zone grounding/quote grounding;
        this builder remains deterministic: geometrySource/gioJoinId/caveat
        come from the card's own geoBinding (never from the model), the
        kind→ruleType/zoneSemantics/executableRef mapping is a fixed table,
        and the seam stamps identity into ``formalizedBy``.
        """
        from pipeline.norm_llm import KIND_MAP

        meta = KIND_MAP[proposal["kind"]]
        gb_obj = getattr(card, "geoBinding", None)
        gb: Dict[str, Any] = {}
        if gb_obj is not None:
            import dataclasses

            gb = dataclasses.asdict(gb_obj) if dataclasses.is_dataclass(gb_obj) else dict(gb_obj)
        zone_selector: Dict[str, Any] = {
            "zoneIds": list(proposal["zoneIds"]),
            "selection": meta["selection"],
            "geometrySource": gb.get("geometrySource") or "national_source",
        }
        if gb.get("gioJoinId"):
            zone_selector["gioJoinId"] = gb.get("gioJoinId")
        if gb.get("caveat"):
            zone_selector["caveat"] = gb.get("caveat")
        if proposal.get("bufferDistanceM") is not None:
            zone_selector["bufferDistanceM"] = proposal["bufferDistanceM"]
        rule = _base_rule(
            card,
            status="formalized",
            rule_type=meta["rule_type"],
            zone_semantics=meta["zone_semantics"],
            executable_ref=meta["executable_ref"],
            extra_tags=("llm_proposed",),
            rationale=(
                str(proposal["rationale"]).rstrip(". ")
                + ". [gated LLM proposal (S2); deterministic gates passed; human review required]"
            ),
            zone_selector=zone_selector,
            conditions=list(proposal.get("conditions") or []),
        )
        stamp = getattr(self.llm_hook, "stamp", None)
        if stamp:
            agent, _, _version = self.run_ref.partition("#")
            rule["formalizedBy"] = f"{agent}#{stamp}"
        self._llm_proposed += 1
        return rule

    def _formalize_card(self, card: NormCard) -> FormalRule:
        spec = TEMPLATE_SPECS.get(card.evidenceId)
        if spec is None:
            # S2 seam: only template-less cards consult the hook. Curated
            # abstentions (template kind ambiguous/reject) are never
            # re-proposed — the model cannot override a curated reason.
            if self.llm_hook is not None:
                proposal = self.llm_hook(card.to_dict())
                if proposal is not None:
                    return FormalRule.from_dict(self._llm_rule(card, proposal))
            rule = _base_rule(
                card,
                status="ambiguous",
                rule_type="unsupported_claim",
                zone_semantics="none",
                executable_ref=_REVIEW_REF,
                reason=(
                    f"no deterministic template registered for evidence {card.evidenceId} "
                    f"(theme {card.theme}); refusing to guess"
                ),
                rationale=(
                    f"cite-or-abstain: without a registered template the formalizer must not "
                    f"invent predicates for theme '{card.theme}'."
                ),
            )
            return FormalRule.from_dict(rule)

        kind = spec["kind"]
        if kind == "inclusion":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_inclusion",
                zone_semantics="inclusion",
                executable_ref=spec.get("executable_ref", "engine.zone.within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "exclusion":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_exclusion",
                zone_semantics="exclusion",
                executable_ref=spec.get("executable_ref", "engine.zone.exclude_within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "attention":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_attention",
                zone_semantics="attention",
                executable_ref=spec.get("executable_ref", "engine.zone.buffer@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "conditional":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="zone_conditional",
                zone_semantics="conditional",
                executable_ref=spec.get("executable_ref", "engine.zone.within@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "compensation":
            rule = _base_rule(
                card,
                status="formalized",
                rule_type="compensation_requirement",
                zone_semantics="compensation",
                executable_ref=spec.get("executable_ref", "engine.compensation.ratio@poc-v1"),
                extra_tags=spec.get("extra_tags", ()),
                rationale=spec["rationale"],
                zone_selector=dict(spec["zone"]),
                conditions=list(spec.get("conditions", [])),
                related=spec.get("related"),
            )
        elif kind == "ambiguous":
            rule = _base_rule(
                card,
                status="ambiguous",
                rule_type=spec["rule_type"],
                zone_semantics="none",
                executable_ref=spec.get("executable_ref", _REVIEW_REF),
                extra_tags=spec.get("extra_tags", ()),
                reason=spec["reason"],
                rationale=spec["rationale"],
            )
        elif kind == "reject":
            rule = _base_rule(
                card,
                status="rejected",
                rule_type=spec["rule_type"],
                zone_semantics="none",
                executable_ref=spec.get("executable_ref", _NOOP_REF),
                extra_tags=spec.get("extra_tags", ()),
                reason=spec["reason"],
                rationale=spec["rationale"],
            )
        else:  # pragma: no cover - authoring guard
            raise ValueError(f"unknown template kind {kind!r} for {card.evidenceId}")
        return FormalRule.from_dict(rule)  # validates against formal-rule.schema.json

    def _check_integrity(self, cards: List[NormCard], rules: List[FormalRule]) -> None:
        card_ids = {card.id for card in cards}
        covered = {rule.normCardId for rule in rules} | {
            rel for rule in rules for rel in (rule.relatedNormCardIds or [])
        }
        missing = card_ids - {rule.normCardId for rule in rules}
        if missing:
            raise RuntimeError(f"formalizer coverage failure: cards without a rule: {sorted(missing)}")
        unknown_related = covered - card_ids
        if unknown_related:
            raise RuntimeError(f"formalizer references unknown NormCards: {sorted(unknown_related)}")
        for rule in rules:
            if rule.executableRef not in ENGINE_OPERATIONS:
                raise RuntimeError(
                    f"rule {rule.id} references unregistered engine operation {rule.executableRef}"
                )
            if rule.status == "formalized" and (rule.zoneSelector is None or rule.conditions is None):
                raise RuntimeError(f"formalized rule {rule.id} lacks zoneSelector/conditions")
            if rule.status != "formalized" and (rule.conditions or rule.zoneSelector):
                raise RuntimeError(
                    f"non-formalized rule {rule.id} must not carry executable predicates"
                )


# ---------------------------------------------------------------------------
# corpus (re)generation — python3 -m pipeline.agents
# ---------------------------------------------------------------------------

def generate_corpus() -> Dict[str, Path]:
    """Deterministically (re)generate the per-track normcard/formalrule corpora.

    Tracks: alle 13 canonieke tracks uit pipeline.track_config — per track
    evidence-<track>.json → normcards-<track>.json + formalrules-<track>.json."""
    out: Dict[str, Path] = {}
    analyst = NormAnalyst()
    formalizer = NormFormalizer()
    for track in sorted(track_config.load_all_tracks()):
        shard = CORPUS_DIR / f"evidence-{track}.json"
        cards = analyst.read(shard)
        if analyst.rejected:
            raise RuntimeError(
                f"verified-only invariant broken by: {[r['evidenceId'] for r in analyst.rejected]}"
            )
        cards_path = CORPUS_DIR / f"normcards-{track}.json"
        cards_path.write_text(
            json.dumps([card.to_dict() for card in cards], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rules = formalizer.formalize(cards)
        rules_path = CORPUS_DIR / f"formalrules-{track}.json"
        rules_path.write_text(
            json.dumps([rule.to_dict() for rule in rules], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        out[track] = rules_path
    return out


def main() -> None:
    generate_corpus()
    analyst = NormAnalyst()
    formalizer = NormFormalizer()
    for track in sorted(track_config.load_all_tracks()):
        cards = analyst.read(CORPUS_DIR / f"evidence-{track}.json")
        formalizer.formalize(cards)
        print(f"wrote corpus/normcards-{track}.json ({len(cards)} cards) and "
              f"corpus/formalrules-{track}.json {formalizer.last_coverage}")


if __name__ == "__main__":  # pragma: no cover
    main()
