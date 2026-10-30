"""ACM/IDM-mock (F2): authenticatie en mandaten via Digital Vlaanderen-
dienstvorm, in replay vormgegeven door een identiteiten-fixture per persona.
Productie vervangt dit door de echte ACM/IDM-integratie (INT-01)."""

from __future__ import annotations

import json
from pathlib import Path


def _laad(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "identiteiten.json").read_text(encoding="utf-8"))["personas"]


def authenticate(poc_root: Path, persona_id: str) -> dict:
    personas = _laad(poc_root)
    if persona_id not in personas:
        raise KeyError(f"onbekende persona voor authenticatie: {persona_id}")
    return personas[persona_id]


def geldig_mandaat(identiteit: dict, context: dict) -> bool:
    rollen = {m["rol"] for m in identiteit.get("mandaten", [])}
    if not rollen:
        return True
    return context.get("mandate") in rollen
