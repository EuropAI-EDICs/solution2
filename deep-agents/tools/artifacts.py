"""Artifact submission gates: agents don't just draft JSON, they SUBMIT it.

submit_* tools validate (schema gates from intake/formalize), persist the
artifact under runs/live/artifacts/ and journal the verdict — so the chain
and the dashboard can see whether every stage actually passed its gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import journal
from tools.formalize import validate_formal_rule
from tools.intake import validate_request

HERE = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = HERE / "runs" / "live" / "artifacts"


def _persist(name: str, payload: Any) -> str:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return str(path)


def submitted_request() -> dict[str, Any] | None:
    """The persisted intake request if one exists and still passes the schema gate, else None."""
    path = ARTIFACTS_DIR / "request.json"
    if not path.is_file():
        return None
    verdict = validate_request(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8")) if verdict["passed"] else None


def submit_request(request_json: str) -> dict[str, Any]:
    """Validate an OpportunityMapRequest (JSON string) and SUBMIT it as the run's intake artifact. Submission is mandatory: the world-scene build refuses to run in chain mode without a submitted, schema-valid request. Fix listed errors and re-submit until PASS."""
    verdict = validate_request(request_json)
    out = dict(verdict)
    if verdict["passed"]:
        out["artifactPath"] = _persist("request.json", json.loads(request_json))
        out["submitted"] = True
        journal.append("tool_result", "intake", f"submit_request → PASS, artifact: {out['artifactPath']}")
    else:
        out["submitted"] = False
        journal.append("tool_result", "intake", f"submit_request → FAIL ({len(verdict['errors'])} error(s))")
    return out


def submit_norm_cards(cards_json: str) -> dict[str, Any]:
    """Submit the selected norm cards (JSON array or {\"normCards\": [...]}) as the run's norms artifact. Every card must carry an NC-* id and a claim. Submission is mandatory for the norm stage of the chain."""
    try:
        data = json.loads(cards_json)
    except json.JSONDecodeError as exc:
        journal.append("tool_result", "normspecialist", f"submit_norm_cards → FAIL (invalid JSON: {exc})")
        return {"submitted": False, "errors": [f"invalid JSON: {exc}"]}
    cards = data if isinstance(data, list) else data.get("normCards", [])
    bad = [c.get("id", "?") for c in cards if not (isinstance(c, dict) and str(c.get("id", "")).startswith("NC-") and c.get("claim"))]
    if not cards or bad:
        journal.append("tool_result", "normspecialist", f"submit_norm_cards → FAIL ({len(bad)} invalid card(s))")
        return {"submitted": False, "errors": [f"invalid or incomplete cards: {bad}"] if bad else ["no cards submitted"]}
    out = {"submitted": True, "count": len(cards), "ids": [c["id"] for c in cards], "artifactPath": _persist("normcards.json", cards)}
    journal.append("tool_result", "normspecialist", f"submit_norm_cards → PASS ({len(cards)} kaart(en)): {', '.join(out['ids'])}")
    return out


def submit_formal_rule(rule_json: str) -> dict[str, Any]:
    """Validate a FormalRule (JSON string) against the POC schema and SUBMIT it as the run's formalization artifact. Submission is mandatory; fix listed errors and re-submit until PASS."""
    verdict = validate_formal_rule(rule_json)
    out = dict(verdict)
    if verdict["passed"]:
        out["artifactPath"] = _persist("formal-rule.json", json.loads(rule_json))
        out["submitted"] = True
        journal.append("tool_result", "formalizer", f"submit_formal_rule('{verdict['ruleId']}') → PASS, artifact: {out['artifactPath']}")
    else:
        out["submitted"] = False
        journal.append("tool_result", "formalizer", f"submit_formal_rule → FAIL ({len(verdict['errors'])} error(s))")
    return out
