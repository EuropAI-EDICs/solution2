"""Magda-mock in MCP-vorm (F2): het manifest declareert het toolregister met
doelbinding; raadpleging zonder exact die doelbinding wordt geweigerd (FR-10).
Records zijn persona-gekoppelde fixtures — productie vervangt dit door de
Magda-diensten van Digital Vlaanderen (INT-02)."""

from __future__ import annotations

import json
from pathlib import Path


class MagdaPurposeError(Exception):
    """Raadpleging buiten de gedeclareerde doelbinding."""


def beschikbare_tools(manifest: dict) -> list[dict]:
    return [{"tool": bron["source"], "purpose": bron["purpose"]}
            for bron in manifest.get("authenticSources", [])]


def raadpleeg(manifest: dict, tool: str, purpose: str, poc_root: Path, persona_id: str) -> dict:
    declaratie = {bron["source"]: bron["purpose"] for bron in manifest.get("authenticSources", [])}
    if tool not in declaratie:
        raise KeyError(f"onbekende magda-tool: {tool}")
    if declaratie[tool] != purpose:
        raise MagdaPurposeError(f"doelbinding schiet tekort voor {tool}: '{purpose}' ≠ gedeclareerde doelbinding")
    personas = json.loads((poc_root / "fixtures" / "magda.json").read_text(encoding="utf-8"))["personas"]
    if persona_id not in personas or tool not in personas[persona_id]:
        raise KeyError(f"geen {tool}-record voor persona: {persona_id}")
    return personas[persona_id][tool]
