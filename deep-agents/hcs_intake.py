"""HCS-LLM-intake (fase 3, benadering C-aanzet) — spec
2026-10-09-hcs-recipes-pocs-design §6.

De LLM stelt intake-vragen voor een persona uit de THK-08-fixture; een
deterministische gate toetst de poort-3-regels uit de Human-Centred Services-
blueprint: alleen vragen wat niet in de BRP staat, gewone taal, en overname
door een medewerker bij edge-cases. De HCS-demo's blijven deterministische
replays — dit levert artefacts in ``runs/hcs-intake/``.

CLI: ``python hcs_intake.py --persona sanne [--model gemma4:31b] [--all]``
(llm-marker in de tests: ``pytest -m llm`` met LDT_DEEP_AGENTS_ENDPOINT).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEEP_AGENTS_ROOT = Path(__file__).resolve().parent
NLDT_ROOT = DEEP_AGENTS_ROOT.parent / "nldt"
FIXTURE = NLDT_ROOT / "simulation" / "hcs" / "fixtures" / "life-events" / "thk-08-move-home.json"
RUNS_DIR = DEEP_AGENTS_ROOT / "runs" / "hcs-intake"

SYSTEM_PROMPT = """Je bent de intake-assistent van de gemeente voor mensen die gaan verhuizen (THK-08).
Regels:
- Stel ALLEEN vragen die je niet uit de basisregistratie (BRP) kunt opmaken. Naam, BSN en adressen ken je al.
- Gebruik gewone, korte zinnen zonder overheidsjargon.
- Twijfel over het adres of de persoonlijke situatie? Stel dan geen extra vragen meer, maar beveel aan dat een medewerker het overneemt.
- Antwoord ALLEEN met geldige JSON, in precies dit formaat:
  {"asks": ["vraag 1", "vraag 2"], "handover": null}
  of met overname: {"asks": [], "handover": {"reason": "korte reden"}}"""

# Vragen die deze sleutelwoorden raken, vragen naar bekende BRP-gegevens.
KNOWN_BRP_KEYS = ["naam", "heet", "heten", "bsn", "burgerservicenummer",
                  "adres", "woonplaats", "straat", "huisnummer", "postcode"]
JARGON_KEYS = ["bsn", "burgerservencenummer", "brp", "zaak", "api",
               "attestatie", "decentraal", "persoonsgegeven"]
MAX_QUESTION_LENGTH = 120


def load_thk08_personas() -> list[dict]:
    """Projecteer de THK-08-fixture op intake-persona's: id, edge, bekende
    BRP-velden en de verwachte handover-trigger uit de intake-stap."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    intake = fixture["steps"][0]
    per_persona = intake.get("perPersona", {})
    personas = []
    for p in fixture["personas"]:
        handover = (per_persona.get(p["id"], {}).get("handover"))
        personas.append({
            "id": p["id"], "edge": p["edge"], "label": p["label"],
            "known_brp": ["naam", "bsn", "huidig adres", "nieuw adres"],
            "expected_handover_reason": (handover or {}).get("reason"),
        })
    return personas


def _mentions(question: str, keys: list[str]) -> bool:
    q = question.lower()
    return any(k in q for k in keys)


def gate_intake(result: dict, persona: dict) -> dict:
    """Deterministische poort-3-toets over het LLM-voorstel (pure functie)."""
    asks = result.get("asks", [])
    checks = []

    overlap = [q for q in asks if _mentions(q, KNOWN_BRP_KEYS)]
    checks.append({
        "check": "only-new-questions", "passed": not overlap,
        "reason": ("vraagt naar bekende BRP-gegevens: " + "; ".join(overlap)) if overlap
        else "alleen vragen die niet uit de BRP te beantwoorden zijn",
    })

    jargon = [q for q in asks if _mentions(q, JARGON_KEYS) or len(q) > MAX_QUESTION_LENGTH]
    checks.append({
        "check": "plain-language", "passed": not jargon,
        "reason": ("jargon of te lang: " + "; ".join(jargon)) if jargon
        else "gewone taal, korte vragen",
    })

    needs_handover = bool(persona.get("expected_handover_reason"))
    handover = result.get("handover")
    if needs_handover:
        checks.append({
            "check": "edge-handover", "passed": bool(handover),
            "reason": "overname aanwezig" if handover
            else f"verplichte overname ontbreekt (edge: {persona.get('edge')})",
        })
    else:
        checks.append({
            "check": "edge-handover", "passed": handover is None,
            "reason": "geen overname nodig en geen overname voorgesteld" if handover is None
            else "onverwachte overname voorgesteld",
        })

    return {"persona": persona["id"], "passed": all(c["passed"] for c in checks), "checks": checks}


def _parse_json(raw: str) -> dict | None:
    """Eerste JSON-object uit het antwoord; None bij onparseerbaar (abstain)."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("asks", []), list):
        return None
    return parsed


def run_intake(persona_id: str, model: str | None = None) -> dict:
    """Vraag het LLM om intake-vragen voor de persona en toets de gate."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from models import ollama_model

    personas = {p["id"]: p for p in load_thk08_personas()}
    if persona_id not in personas:
        raise KeyError(f"onbekende persona: {persona_id}")
    persona = personas[persona_id]

    llm = ollama_model(model)
    # De context naar het LLM bevat níet de verwachte gate-uitslag — anders
    # lekt het model-antwoord door de toets heen.
    context = {k: persona[k] for k in ("id", "edge", "label", "known_brp")}
    user = ("Persona: " + json.dumps(context, ensure_ascii=False) +
            "\nStel de intake-vragen op volgens de regels.")
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)])
    raw = response.content if isinstance(response.content, str) else str(response.content)

    parsed = _parse_json(raw)
    result: dict = {
        "persona": persona_id, "edge": persona["edge"],
        "model": model or "default", "asks": [], "handover": None,
        "abstained": parsed is None,
    }
    if parsed is None:
        result["raw"] = raw
    else:
        result["asks"] = [str(a) for a in parsed.get("asks", [])]
        result["handover"] = parsed.get("handover")
    result["gate"] = gate_intake(result, persona)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    artifact = RUNS_DIR / f"{stamp}-{persona_id}.json"
    artifact.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    result["artifact"] = str(artifact)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persona", help="persona-id uit de THK-08-fixture")
    parser.add_argument("--all", action="store_true", help="alle persona's draaien")
    parser.add_argument("--model", default=None, help="modelspec (default: orchestrator-default)")
    args = parser.parse_args()
    if not args.all and not args.persona:
        parser.error("--persona of --all verplicht")
    persona_ids = [p["id"] for p in load_thk08_personas()] if args.all else [args.persona]
    failures = 0
    for pid in persona_ids:
        result = run_intake(pid, model=args.model)
        status = "GO" if result["gate"]["passed"] else "GEEN GO"
        print(f"{pid}: {status} — {len(result['asks'])} vraag(en), "
              f"handover={bool(result['handover'])}, abstained={result['abstained']}")
        for check in result["gate"]["checks"]:
            if not check["passed"]:
                print(f"  ✗ {check['check']}: {check['reason']}")
                failures += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
