"""Deterministische beslistabellen-engine met volledige trace (FR-06/07).

Het model speelt hier geen rol: dezelfde tabellen + context geven altijd
dezelfde uitkomst, en elke vurende regel draagt zijn uitleg en legalBasis.
Geen passende regel → escalatie (ontwerp unknownPolicy: escalate, AI-05)."""

from __future__ import annotations


def _matches(when: dict, context: dict) -> tuple[bool, str]:
    for key, expected in when.items():
        got = context.get(key)
        if got is None:
            return False, f"slot '{key}' ontbreekt"
        if got != expected:
            return False, f"{key}: '{got}' ≠ '{expected}'"
    return True, "alle voorwaarden voldaan"


def evaluate(tables: dict, context: dict) -> dict:
    trace: list[dict] = []
    uitleg: list[dict] = []
    transactions: list[str] = []
    info: list[str] = []
    for rule in tables["rules"]:
        fired, reden = _matches(rule["when"], context)
        trace.append({"ruleId": rule["id"], "fired": fired, "reden": reden})
        if not fired:
            continue
        for sv in rule["then"].get("transactions", []):
            if sv not in transactions:
                transactions.append(sv)
        for sv in rule["then"].get("info", []):
            if sv not in info:
                info.append(sv)
        uitleg.append({"regelId": rule["id"], "tekst": rule["uitleg"], "bron": rule["legalBasis"]})
    outcome = "paden" if any(t["fired"] for t in trace) else "escalatie"
    return {"outcome": outcome, "paths": {"transactions": transactions, "info": info},
            "trace": trace, "uitleg": uitleg}
