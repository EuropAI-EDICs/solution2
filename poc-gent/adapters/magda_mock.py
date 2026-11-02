"""Magda-mock in MCP-vorm (F2): het manifest declareert het toolregister met
doelbinding; raadpleging zonder exact die doelbinding wordt geweigerd (FR-10).
Records zijn persona-gekoppelde fixtures — productie vervangt dit door de
Magda-diensten van Digital Vlaanderen (INT-02). Tool-bronnen mét een
cache-backing (bijv. gent:kotregister uit de publieke kotenzoeker) vallen
terug op de cache wanneer de persona-fixture geen record heeft; de context
(het adres) is dan de sleutel in plaats van de persona."""

from __future__ import annotations

import json
from pathlib import Path

from adapters import kotregister


class MagdaPurposeError(Exception):
    """Raadpleging buiten de gedeclareerde doelbinding."""


# Cache-backed tool-bronnen: functie(poc_root, context) -> record.
_CACHE_BRONNEN = {
    "gent:kotregister": lambda poc_root, context: kotregister.status_voor(
        poc_root, context.get("address")),
}


def beschikbare_tools(manifest: dict) -> list[dict]:
    return [{"tool": bron["source"], "purpose": bron["purpose"]}
            for bron in manifest.get("authenticSources", [])]


def raadpleeg(manifest: dict, tool: str, purpose: str, poc_root: Path, persona_id: str,
              context: dict | None = None) -> dict:
    declaratie = {bron["source"]: bron["purpose"] for bron in manifest.get("authenticSources", [])}
    if tool not in declaratie:
        raise KeyError(f"onbekende magda-tool: {tool}")
    if declaratie[tool] != purpose:
        raise MagdaPurposeError(f"doelbinding schiet tekort voor {tool}: '{purpose}' ≠ gedeclareerde doelbinding")
    personas = json.loads((poc_root / "fixtures" / "magda.json").read_text(encoding="utf-8"))["personas"]
    if persona_id in personas and tool in personas[persona_id]:
        return personas[persona_id][tool]
    if tool in _CACHE_BRONNEN and context and context.get("address"):
        return _CACHE_BRONNEN[tool](poc_root, context)
    raise KeyError(f"geen {tool}-record voor persona: {persona_id}")
