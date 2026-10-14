#!/usr/bin/env python3
"""Explainer for the opportunity-map PoC (plan section 3.2, agent #8).

Produces the trace-back artifacts that make the map contestable:

* **DecisionTable** (JSON, schema-validated, plus a Markdown rendering) —
  one row per FormalRule/NormCard with columns criterion / norm / source /
  zone effect (+ rule, condition, note). Every row links its normCardId so
  each cell remains legally contestable (paper A/B explainability).
* **prov.json** — a PROV-O-flavoured JSON bundle: agents (name+version),
  entities (artifacts with sha256 where already on disk), activities (one
  per pipeline stage with start/end timestamps), wasGeneratedBy /
  wasDerivedFrom links, and the geo sources with their ``lastChecked``
  timestamps (primary-source style records for the open-data layer aliases
  of the GIO join-ids).

Deterministic given the inputs and the stage log collected by the
orchestrator; no LLM at runtime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from pipeline import contracts
except ImportError:  # pragma: no cover - direct execution inside poc/pipeline
    import contracts as contracts  # type: ignore[no-redef]

__all__ = ["Explainer", "EXPLAINER_VERSION"]

EXPLAINER_VERSION = "explainer#deterministic-poc1"

_ZONE_EFFECT = {
    "inclusion": "included",
    "exclusion": "excluded",
    "conditional": "conditional",
    "attention": "attention",
    "compensation": "compensation",
}


def _shorten(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"


def _first_sentence(claim: str, limit: int = 170) -> str:
    claim = " ".join(str(claim or "").split())
    for sep in (". ", "; "):
        head = claim.split(sep)[0]
        if len(head) > 40:
            claim = head + "."
            break
    return _shorten(claim, limit)


class Explainer:
    agent_name = "explainer"

    def __init__(self, run_ref: str = EXPLAINER_VERSION) -> None:
        self.run_ref = run_ref

    # ------------------------------------------------------------------ #
    # decision table
    # ------------------------------------------------------------------ #

    def build_decision_table(
        self,
        *,
        request: Mapping[str, Any],
        normcards: Sequence[Mapping[str, Any]],
        formalrules: Sequence[Mapping[str, Any]],
        generated_at: str,
        prov_narrative: str,
        table_id: str = "DT-wind-utrecht-poc1",
        title: str = "Where can wind turbines be sited in province Utrecht? "
                     "Decision table (programming stage)",
    ) -> Dict[str, Any]:
        cards_by_id = {c["id"]: c for c in normcards}
        rows: List[Dict[str, Any]] = []
        for rule in formalrules:
            card = cards_by_id.get(rule.get("normCardId")) or {}
            src = card.get("source") or {}
            sem = rule.get("zoneSemantics")
            if rule.get("status") == "formalized":
                effect = _ZONE_EFFECT.get(sem, "conditional")
            elif rule.get("status") == "rejected":
                effect = "not_applicable"
            else:
                effect = "ambiguous"
            conditions = "; ".join(
                f"{c.get('parameter')} {c.get('operator')} {c.get('value')}{(' ' + c['unit']) if c.get('unit') else ''}"
                for c in (rule.get("conditions") or [])
            )
            note = rule.get("reason") or rule.get("rationale") or ""
            geo = card.get("geoBinding") or {}
            if geo.get("zoneIds"):
                note = (note + " | zones: " + ", ".join(geo["zoneIds"])).strip(" |")
            if geo.get("gioJoinId"):
                note = (note + " | GIO: " + geo["gioJoinId"]).strip(" |")
            row: Dict[str, Any] = {
                "criterion": _first_sentence(card.get("claim", rule.get("id", "criterion"))),
                "norm": f"{src.get('article', '?')} \u2014 {card.get('instrument', '?')} [{card.get('legalForce', '?')}]",
                "source": f"{src.get('docId', '?')}: {src.get('uri', '?')}",
                "zone effect": effect,
                "normCardId": rule.get("normCardId", "?"),
                "ruleId": rule.get("id", "?"),
            }
            if conditions:
                row["condition"] = conditions
            if note:
                row["note"] = _shorten(note, 400)
            rows.append(row)

        dt = {
            "id": table_id,
            "requestId": str(request.get("id", "request")),
            "title": title,
            "columns": [
                "criterion", "norm", "source", "zone effect",
                "ruleId", "normCardId", "condition", "note",
            ],
            "rows": rows,
            "generatedBy": self.run_ref,
            "generatedAt": generated_at,
            "provenance": prov_narrative,
        }
        contracts.validate(dt, "decision-table")
        return dt

    @staticmethod
    def decision_table_markdown(dt: Mapping[str, Any]) -> str:
        cols = list(dt["columns"])

        def cell(row: Mapping[str, Any], col: str) -> str:
            return str(row.get(col, "")).replace("|", "\\|").replace("\n", " ")

        lines = [
            f"# {dt['title']}",
            "",
            f"*Generated by `{dt['generatedBy']}` at {dt['generatedAt']}; request `{dt.get('requestId', '?')}`.*",
            "",
            "| " + " | ".join(cols) + " |",
            "|" + "|".join("---" for _ in cols) + "|",
        ]
        for row in dt["rows"]:
            lines.append("| " + " | ".join(cell(row, c) for c in cols) + " |")
        lines += [
            "",
            f"*{len(dt['rows'])} rows \u2014 every row links normCardId \u2192 NormCard (verbatim quote + article + "
            f"instrument version + URL in the run's normcards.json); zone effect 'ambiguous' rows require the "
            f"V4 human-expert checkpoint before they may steer siting decisions.*",
            "",
            f"*Provenance: {dt['provenance']}*",
            "",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # PROV-O-flavoured bundle
    # ------------------------------------------------------------------ #

    def build_prov(
        self,
        *,
        run_id: str,
        generated_at: str,
        request_id: str,
        agents: Sequence[Mapping[str, Any]],
        activities: Sequence[Mapping[str, Any]],
        entities: Sequence[Mapping[str, Any]],
        derivations: Sequence[Mapping[str, Any]] = (),
        sources: Sequence[Mapping[str, Any]] = (),
        namespace: str = "ldttoolbox:poc:wind:",
    ) -> Dict[str, Any]:
        """Assemble the PROV bundle. ``activities`` carry used/generated ids.

        Keys deliberately follow W3C PROV-O class/property names
        (agent/entity/activity/wasGeneratedBy/wasDerivedFrom) but the
        serialisation is plain JSON, not RDF.
        """
        ent_ids = {e["id"] for e in entities}
        for act in activities:
            for used in act.get("used", []):
                if used not in ent_ids:
                    entities = list(entities) + [
                        {"id": used, "type": "entity", "note": "referenced but not hashed at build time"}
                    ]
                    ent_ids.add(used)
        generated = []
        for act in activities:
            for out in act.get("generated", []):
                generated.append({"entity": out, "activity": act["id"], "time": act.get("endedAt")})
        prov = {
            "flavour": "W3C PROV-O terms (agent/entity/activity/wasGeneratedBy/wasDerivedFrom) serialised as plain JSON",
            "namespace": namespace,
            "runId": run_id,
            "requestId": request_id,
            "generatedAt": generated_at,
            "generatedBy": self.run_ref,
            "agent": [dict(a) for a in agents],
            "entity": [dict(e) for e in entities],
            "activity": [dict(a) for a in activities],
            "wasGeneratedBy": generated,
            "wasDerivedFrom": [dict(d) for d in derivations],
            "hadPrimarySource": [dict(s) for s in sources],
        }
        return prov


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def entity_for(path: Path, etype: str, extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    ent: Dict[str, Any] = {
        "id": path.name,
        "type": etype,
        "path": str(path),
    }
    if path.exists():
        ent["sha256"] = sha256_of(path)
    if extra:
        ent.update(extra)
    return ent
