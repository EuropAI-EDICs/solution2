"""Projecteer ontlede STTR-decisiontables op de reference-engine.

De engine kent precies AND, EQUALS, LESS_THAN_OR_EQUAL en IF — dus alleen
cellen die daar letterlijk in passen worden geprojecteerd; alles buiten de
subset levert een expliciete ``reden``, nooit een gissing. Rij-volgorde blijft
behouden: single-hit tabellen worden een IF met cases in documentvolgorde en
als default de eerste alles-mogelijke rij (of ``null`` als die ontbreekt).
"""
from __future__ import annotations

import itertools
import re
from typing import Any

from nldt.simulation.regelrecht import reference_engine

# Single-hit policies (één uitkomst per evaluatie); COLLECT e.d. zijn multi-hit.
_SINGLE_HIT = {"UNIQUE", "FIRST", "ANY", "PRIORITY", "RULE ORDER"}

_VERGELIJKING = re.compile(r"^(<=|>=|<|>)\s*(-?\d+(?:[.,]\d+)?)$")
_GEQUOTE = re.compile(r'^"([^"]*)"$')
_GETAL = re.compile(r"^-?\d+(?:[.,]\d+)?$")

_OPS = {"<=": "LESS_THAN_OR_EQUAL"}


def _cel_conditie(tekst: str, invoernaam: str) -> dict[str, Any] | None | str:
    """Eén FEEL-cel → engine-conditie; None = don't care ('-'); str = reden bij onmogelijk."""
    t = tekst.strip()
    if t in ("-", ""):
        return None
    if t == "true":
        return {"operation": "EQUALS", "subject": f"${invoernaam}", "value": True}
    if t == "false":
        return {"operation": "EQUALS", "subject": f"${invoernaam}", "value": False}
    m = _GEQUOTE.match(t)
    if m:
        return {"operation": "EQUALS", "subject": f"${invoernaam}", "value": m.group(1)}
    m = _VERGELIJKING.match(t)
    if m:
        if m.group(1) == "<=":
            return {
                "operation": "LESS_THAN_OR_EQUAL",
                "subject": f"${invoernaam}",
                "value": float(m.group(2).replace(",", ".")),
            }
        return f"vergelijking '{m.group(1)}' buiten engine-subset"
    if _GETAL.match(t):
        return {
            "operation": "EQUALS",
            "subject": f"${invoernaam}",
            "value": float(t.replace(",", ".")),
        }
    return f"cel-expressie buiten engine-subset: {t!r}"


def _uitgang_letterlijk(tekst: str) -> Any:
    t = tekst.strip()
    if t == "true":
        return True
    if t == "false":
        return False
    m = _GEQUOTE.match(t)
    if m:
        return m.group(1)
    try:
        return float(t.replace(",", "."))
    except ValueError:
        return t or None


def _invoernaam(kolom: dict[str, Any], index: int) -> str:
    return kolom.get("label") or kolom.get("naam") or f"invoer_{index + 1}"


def projecteer_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Beslistabel → engine-executie; altijd met expliciet projecteerbaar/reden-oordeel."""
    tabel = decision.get("tabel")
    basaal = {
        "naam": decision.get("naam"),
        "hitPolicy": (tabel or {}).get("hitPolicy"),
        "aantalRijen": len(((tabel or {}).get("rijen")) or []),
    }
    if tabel is None:
        return {**basaal, "projecteerbaar": False, "reden": "geen decisionTable"}
    if tabel.get("hitPolicy") not in _SINGLE_HIT:
        return {
            **basaal,
            "projecteerbaar": False,
            "reden": f"hitPolicy {tabel.get('hitPolicy')} is multi-hit",
        }
    if len(tabel.get("uitgangen") or []) != 1:
        return {
            **basaal,
            "projecteerbaar": False,
            "reden": f"{len(tabel.get('uitgangen') or [])} uitgangskolommen (verwacht 1)",
        }
    invoer = [
        {"name": _invoernaam(kol, i), "type": kol.get("type"), "label": kol.get("label")}
        for i, kol in enumerate(tabel.get("invoer") or [])
    ]

    cases: list[dict[str, Any]] = []
    default: Any = None
    heeft_default_rij = False
    for rij in tabel.get("rijen") or []:
        condities: list[dict[str, Any]] = []
        for kol_i, cel in enumerate(rij.get("cellen") or []):
            if kol_i >= len(invoer):
                return {
                    **basaal,
                    "projecteerbaar": False,
                    "reden": "meer celkolommen dan invoerkolommen",
                }
            gevolg = _cel_conditie(cel, invoer[kol_i]["name"])
            if isinstance(gevolg, str):
                return {**basaal, "projecteerbaar": False, "reden": gevolg}
            if gevolg is not None:
                condities.append(gevolg)
        uitgangen = rij.get("uitgangen") or []
        if not uitgangen:
            return {**basaal, "projecteerbaar": False, "reden": "rij zonder uitgang"}
        then = _uitgang_letterlijk(uitgangen[0])
        if not condities:
            # alles-'-' rij: vangnet; bij FIRST wint de eerste zo'n rij (latere niet meer)
            if not heeft_default_rij:
                heeft_default_rij = True
                default = then
            continue
        when = condities[0] if len(condities) == 1 else {
            "operation": "AND", "conditions": condities
        }
        cases.append({"when": when, "then": then})

    uitgang_type = tabel.get("type") or "string"
    execution = {
        "produces": {"legal_character": "TOETS"},
        "parameters": [],
        "input": [
            {
                "name": iv["name"],
                "type": iv["type"] or "string",
                "description": iv.get("label") or "",
                "source": {"description": "STTR-vraag (RTR-bestand); geen vertaalde annotatie."},
            }
            for iv in invoer
        ],
        "output": [{"name": decision.get("naam") or "conclusie", "type": uitgang_type}],
        "actions": [
            {
                "output": decision.get("naam") or "conclusie",
                "value": {
                    "operation": "IF",
                    "cases": cases,
                    "default": default,
                },
            }
        ],
    }
    return {
        **basaal,
        "inputs": invoer,
        "uitgang": tabel.get("outputLabel"),
        "defaultRij": heeft_default_rij,
        "projecteerbaar": True,
        "reden": None,
        "execution": execution,
    }


def scenario_run(projectie: dict[str, Any], *, max_invoer: int = 6) -> dict[str, Any]:
    """Alle polariteitscombinaties over boolean-invoer door de reference-engine."""
    if not projectie.get("projecteerbaar"):
        return {"status": "niet-projecteerbaar", "reden": projectie.get("reden")}
    invoer = (projectie.get("execution") or {}).get("input") or []
    if not invoer or len(invoer) > max_invoer:
        return {"status": "onthouding", "reden": f"{len(invoer)} invoer (max {max_invoer})"}
    niet_boolean = [iv["name"] for iv in invoer if iv.get("type") != "boolean"]
    if niet_boolean:
        return {
            "status": "onthouding",
            "reden": "niet-boolean invoer (cijfer/tekst) vraagt een voorstel",
            "invoer": niet_boolean,
        }
    namen = [iv["name"] for iv in invoer]
    uitkomsten: dict[str, int] = {}
    fouten = 0
    for combinatie in itertools.product((True, False), repeat=len(namen)):
        try:
            resultaat = reference_engine.evaluate(
                projectie["execution"], dict(zip(namen, combinatie))
            )
            waarde = next(iter(resultaat["outputs"].values()))
            sleutel = "null" if waarde is None else str(waarde)
        except reference_engine.EngineError:
            fouten += 1
            continue
        uitkomsten[sleutel] = uitkomsten.get(sleutel, 0) + 1
    return {
        "status": "uitgevoerd",
        "combinaties": 2 ** len(namen),
        "engineFouten": fouten,
        "uitkomsten": uitkomsten,
    }
