"""F1-replay: intake → intake-gate-vragen → GIS → H1 → routing.

Replay-modus: de uitslagen van seam S1 (intentie-extractie) en S2
(vraagformulering) komen deterministisch uit de persona-fixture; de
LLM-poot komt in een latere fase (ontwerp §5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core import catalog, context, gates, rules, runs
from core import events as events_mod


def load_personas(poc_root: Path) -> dict:
    data = json.loads((poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["personas"]}


def run_replay(poc_root: Path, package_id: str, persona_id: str,
               override_slots: dict | None = None) -> tuple[dict, list]:
    pkg = catalog.load_package(poc_root, package_id)
    persona = load_personas(poc_root)[persona_id]
    events: list = []

    slots = dict(persona["intentSlots"])
    if override_slots:
        slots.update(override_slots)
    events_mod.emit(events, "intake_genomen",
                    {"situatieschets": persona["situatieschets"], "slots_uit_intentie": sorted(slots)})

    vragen = context.open_questions(pkg.manifest, slots)
    antwoorden = persona.get("antwoorden", {})
    for v in vragen:
        if v["slot"] in antwoorden:
            slots[v["slot"]] = antwoorden[v["slot"]]
        events_mod.emit(events, "context_vraag", {"slot": v["slot"], "vraag": v["vraag"],
                                                  "bron": "intake-gate (once-only)"})

    ctx, herkomst = context.build(pkg.manifest, slots, poc_root)
    for check in pkg.manifest.get("gisChecks", []):
        events_mod.emit(events, "gis_check",
                        {"id": check["id"], "layer": check["layer"], "resultaat": ctx.get(check["output"])})

    events_mod.emit(events, "gate_request",
                    {"gate": "H1", "voorstel": context.summary(pkg.manifest, ctx, herkomst)})
    corrections = persona.get("corrections", {})
    if corrections:
        ctx, herkomst = gates.confirm_h1(pkg.manifest, ctx, herkomst, corrections, poc_root)
    events_mod.emit(events, "gate_verdict", {"gate": "H1", "verdict": "gegeven", "correcties": corrections})

    routing = rules.evaluate(pkg.tables, ctx)
    events_mod.emit(events, "routing",
                    {"outcome": routing["outcome"], "transactions": routing["paths"]["transactions"]})

    steps = [
        {"stepId": "intake", "title": "Je vertelt wat je gaat doen", "actor": "agent", "genAiTestPoint": "G1",
         "dataUsed": [persona["situatieschets"]], "consent": "n.v.t.", "handover": None, "kpiEvents": [],
         "prov": {"sources": ["persona-fixture (replay stand-in voor seam S1)"]}},
        {"stepId": "context-vragen", "title": "We vragen alleen wat nog niet bekend is", "actor": "agent",
         "genAiTestPoint": "G1", "dataUsed": [v["vraag"] for v in vragen], "consent": "n.v.t.", "handover": None,
         "kpiEvents": [], "prov": {"sources": ["intake-gate: once-only — authentieke slots worden niet gevraagd"]}},
        {"stepId": "gis-zonecheck", "title": "We checken de zone van je adres", "actor": "agent", "genAiTestPoint": "—",
         "dataUsed": [f"{c['output']}={ctx.get(c['output'])}" for c in pkg.manifest.get("gisChecks", [])],
         "consent": "n.v.t.", "handover": None, "kpiEvents": [],
         "prov": {"sources": [f"gis:{c['layer']} (fixture v1)" for c in pkg.manifest.get("gisChecks", [])]}},
        {"stepId": "h1-contextbevestiging", "title": "Je checkt de verzamelde feiten", "actor": "mens",
         "genAiTestPoint": "—",
         "dataUsed": [f"{r['feit']}={r['waarde']}" for r in context.summary(pkg.manifest, ctx, herkomst)["regels"]],
         "consent": "gegeven", "handover": None, "kpiEvents": [],
         "prov": {"sources": ["H1-bevestiging door gebruiker"]}},
        {"stepId": "routing", "title": "We zeggen welke vergunningen je nodig hebt — en waarom", "actor": "agent",
         "genAiTestPoint": "G2", "dataUsed": [u["tekst"] for u in routing["uitleg"]] or ["geen regel van toepassing"],
         "consent": "n.v.t.", "handover": None, "kpiEvents": [{"kpi": "routingnauwkeurigheid", "effect": routing["outcome"]}],
         "prov": {"sources": [u["bron"] for u in routing["uitleg"]] or ["geen"]}},
    ]
    if routing["outcome"] == "escalatie":
        steps.append({"stepId": "escalatie", "title": "We leggen het voor aan een medewerker", "actor": "mens",
                      "genAiTestPoint": "G5", "dataUsed": [], "consent": "gevraagd",
                      "handover": {"reason": "geen regel van toepassing (unknownPolicy: escalate)", "to": "Gentinfo"},
                      "kpiEvents": [], "prov": {"sources": []}})
        events_mod.emit(events, "handover", {"gate": "H5", "naar": "Gentinfo", "reden": "geen regel van toepassing"})

    run = {
        "schemaVersion": "1.0", "runId": runs.new_run_id(persona_id),
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recipeId": package_id, "processId": "gent-transactional-run", "mode": "replay",
        "scenario": persona_id, "steps": steps, "stopConditions": [], "kpiSnapshot": [],
        "transaction": {"context": context.summary(pkg.manifest, ctx, herkomst),
                        "routing": routing,
                        "h1": {"verdict": "gegeven", "correcties": corrections}},
    }
    return run, events
