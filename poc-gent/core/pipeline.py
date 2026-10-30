"""Replay-pipeline: intake → intake-gate-vragen → GIS → H1 → routing (fase-1),
daarna H2-gegevensgebruik/authenticatie, Magda-prefill, validatie en H3 (fase-2).
IAM: H2 authenticeert standaard via de EUDI-wallet-mock (nldt/16-doctrine);
zonder wallet valt de run terug op ACM/IDM (vrije uitweg), en `auth_methode`
forceert een route.

Replay-modus: de uitslagen van seam S1 (intentie-extractie) en S2
(vraagformulering) komen deterministisch uit de persona-fixture; de
LLM-poot komt in een latere fase (ontwerp §5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from adapters import acm_idm_mock, eudi_wallet, magda_mock
from core import catalog, context, gates, rules, runs
from core import events as events_mod
from core import prefill, validate


def load_personas(poc_root: Path) -> dict:
    data = json.loads((poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["personas"]}


def _acm_authenticatie_stap(poc_root: Path, persona_id: str) -> tuple[dict, dict]:
    identiteit = acm_idm_mock.authenticate(poc_root, persona_id)
    stap = {"stepId": "acm-authenticatie", "title": "Je bevestigt wie je bent (ACM/IDM)",
            "actor": "partij", "genAiTestPoint": "—",
            "dataUsed": [identiteit["pseudoniem"]], "consent": "n.v.t.", "handover": None,
            "kpiEvents": [], "prov": {"sources": ["ACM/IDM (mock v1)"]}}
    return identiteit, stap


def run_replay(poc_root: Path, package_id: str, persona_id: str,
               override_slots: dict | None = None, auth_methode: str = "eudi") -> tuple[dict, list]:
    if auth_methode not in ("eudi", "acmidm"):
        raise ValueError(f"onbekende auth_methode: {auth_methode!r} (eudi|acmidm)")
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
         "prov": {"sources": [(herkomst.get(c["output"]) or {}).get("bron", f"gis:{c['layer']}")
                              for c in pkg.manifest.get("gisChecks", [])]}},
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

    transacties = routing["paths"]["transactions"]
    vereist_auth = [sv for sv in transacties if pkg.manifest["services"][sv].get("vereistAuth")]
    auth_blok = {"authenticatie": "niet-uitgevoerd", "toestemming": "n.v.t.", "mandaten": []}
    prefill_blok = {"transacties": []}
    validatie_blok = {"transacties": []}
    status = "gereed"
    h3_blok = {"verdict": "n.v.t.", "correcties": {}}

    if routing["outcome"] == "escalatie":
        status = "escalatie"
    elif vereist_auth:
        uitleg_h2 = gates.h2_uitleg(pkg.manifest, vereist_auth)
        events_mod.emit(events, "gate_request", {"gate": "H2", "uitleg": uitleg_h2})
        toestemming = persona.get("gebruikGegevens", "gegeven")
        if toestemming == "geweigerd":
            status = "geweigerd"
            auth_blok["toestemming"] = "geweigerd"
            events_mod.emit(events, "gate_verdict", {"gate": "H2", "verdict": "geweigerd"})
            steps.append({"stepId": "h2-gegevensgebruik", "title": "Je beslist of we je gegevens mogen gebruiken",
                          "actor": "mens", "genAiTestPoint": "—",
                          "dataUsed": [b["tool"] + " — " + b["purpose"] for b in uitleg_h2["bronnen"]],
                          "consent": "geweigerd", "handover": None, "kpiEvents": [],
                          "prov": {"sources": ["H2-weigering door gebruiker"]}})
        else:
            if auth_methode == "eudi":
                try:
                    identiteit = eudi_wallet.authenticate(poc_root, persona_id, uitleg_h2["bronnen"])
                    events_mod.emit(events, "wallet_presentatie",
                                    {"loa": identiteit["loa"], "onthuld": identiteit["onthuldeClaims"]})
                    auth_stap = {"stepId": "eudi-authenticatie",
                                 "title": "Je bevestigt wie je bent (EUDI-wallet)",
                                 "actor": "partij", "genAiTestPoint": "—",
                                 "dataUsed": [f"claim: {c}" for c in identiteit["onthuldeClaims"]]
                                            + [f"loa={identiteit['loa']}"],
                                 "consent": "n.v.t.", "handover": None, "kpiEvents": [],
                                 "prov": {"sources": ["EUDI-wallet (mock, ARF-shaped — nldt/16)"]}}
                except eudi_wallet.GeenWallet as err:
                    events_mod.emit(events, "auth_fallback",
                                    {"van": "eudi-wallet", "naar": "acm-idm", "reden": str(err)})
                    identiteit, auth_stap = _acm_authenticatie_stap(poc_root, persona_id)
            else:
                identiteit, auth_stap = _acm_authenticatie_stap(poc_root, persona_id)
            besluit = gates.decide_h2(pkg.manifest, ctx, identiteit, vereist_auth)
            steps.append({"stepId": "h2-gegevensgebruik", "title": "Je geeft toestemming om je gegevens op te halen",
                          "actor": "mens", "genAiTestPoint": "—",
                          "dataUsed": [b["tool"] + " — " + b["purpose"] for b in uitleg_h2["bronnen"]],
                          "consent": "gegeven", "handover": None, "kpiEvents": [],
                          "prov": {"sources": ["H2-toestemming door gebruiker"]}})
            steps.append(auth_stap)
            events_mod.emit(events, "gate_verdict", {"gate": "H2", "verdict": "gegeven"})
            auth_blok = {"authenticatie": "uitgevoerd", "toestemming": "gegeven",
                         "mandaten": identiteit["mandaten"],
                         "methode": identiteit.get("methode", "acm-idm")}
            if "loa" in identiteit:
                auth_blok["loa"] = identiteit["loa"]
                auth_blok["onthuldeClaims"] = identiteit["onthuldeClaims"]
            if not besluit["doorgang"]:
                status = "blokkade"
                stap_ids = {"loa": "h2-loa-blokkade", "mandaat": "h2-mandaatblokkade"}
                blokkade_titel = ("Je wallet geeft te weinig waarborg — een medewerker helpt verder"
                                  if besluit["oorzaak"] == "loa"
                                  else "Een medewerker controleert het mandaat")
                steps.append({"stepId": stap_ids[besluit["oorzaak"]], "title": blokkade_titel,
                              "actor": "mens", "genAiTestPoint": "G5", "dataUsed": [besluit["reden"]],
                              "consent": "gevraagd", "handover": {"reason": besluit["reden"], "to": "Gentinfo"},
                              "kpiEvents": [], "prov": {"sources": []}})
                events_mod.emit(events, "handover", {"gate": "H2", "naar": "Gentinfo", "reden": besluit["reden"]})
            else:
                records: dict = {}
                for bron in uitleg_h2["bronnen"]:
                    try:
                        records[bron["tool"]] = magda_mock.raadpleeg(pkg.manifest, bron["tool"], bron["purpose"],
                                                                    poc_root, persona_id)
                    except KeyError:
                        continue
                    events_mod.emit(events, "bron_raadpleging",
                                    {"tool": bron["tool"], "purpose": bron["purpose"],
                                     "sleutels": sorted(records[bron["tool"]].keys())})
                ergste = {"gereed": 0, "gereed-met-waarschuwing": 1, "blokkade": 2}
                for service_id in transacties:
                    formulier = prefill.bouw(pkg.manifest, service_id, ctx, herkomst, records)
                    uitslag = {"service": service_id, **validate.valideer(pkg.manifest, service_id, formulier)}
                    prefill_blok["transacties"].append(formulier)
                    validatie_blok["transacties"].append(uitslag)
                    events_mod.emit(events, "prefill", {"service": service_id, "ontbrekend": formulier["ontbrekend"]})
                    events_mod.emit(events, "validatie", {"service": service_id, "status": uitslag["status"]})
                status = max((u["status"] for u in validatie_blok["transacties"]),
                             key=lambda s: ergste[s], default="gereed")
                h3_blok = {"verdict": "gegeven", "correcties": {}}
                steps.append({"stepId": "h3-conceptbeoordeling", "title": "Je beoordeelt het concept van je aanvraag",
                              "actor": "mens", "genAiTestPoint": "—",
                              "dataUsed": [f"{pkg.manifest['services'][u['service']]['titel']} — {u['status']}"
                                           for u in validatie_blok["transacties"]],
                              "consent": "gegeven", "handover": None, "kpiEvents": [],
                              "prov": {"sources": ["H3-beoordeling door gebruiker"]}})
                events_mod.emit(events, "gate_request", {"gate": "H3", "concept": [
                    {"service": u["service"], "status": u["status"]} for u in validatie_blok["transacties"]]})
                events_mod.emit(events, "gate_verdict", {"gate": "H3", "verdict": "gegeven", "correcties": {}})

    run = {
        "schemaVersion": "1.1", "runId": runs.new_run_id(persona_id),
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recipeId": package_id, "processId": "gent-transactional-run", "mode": "replay",
        "scenario": persona_id, "steps": steps, "stopConditions": [], "kpiSnapshot": [],
        "transaction": {"context": context.summary(pkg.manifest, ctx, herkomst),
                        "routing": routing,
                        "h1": {"verdict": "gegeven", "correcties": corrections},
                        "status": status,
                        "auth": auth_blok,
                        "prefill": prefill_blok,
                        "validatie": validatie_blok,
                        "h3": h3_blok},
    }
    return run, events
