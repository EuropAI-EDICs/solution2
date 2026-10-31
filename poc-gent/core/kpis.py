"""KPI-harness (F4): meetlogica als pure functies over run-artefact en events.
Drempels volgen de go/no-go-criteria uit de function-baseline
(nldt/recipes/baselines/gent-mobiliteit-ondernemer.baseline.json) en ontwerp
§8.1: KPI-01 ≥90 (doel ≥95) · KPI-02 100 · KPI-03 100 · KPI-04 ≥90% (≈≥18/20)
· KPI-06: geen vragen om authentieke slots · elk H-event correct gelogd."""

from __future__ import annotations

DREMPELS = {
    "kpi01_min": 90.0,
    "kpi01_doel": 95.0,
    "kpi02_min": 100.0,
    "kpi03_min": 100.0,
    "kpi04_min": 90.0,
}


def drempels(manifest: dict) -> dict:
    """Per pakket configureerbaar (manifest.kpiDrempels); default = de
    mobiliteitsbaseline. Onbekende keys blijven ongebruikt (fail-safe)."""
    return {**DREMPELS, **(manifest or {}).get("kpiDrempels", {})}


def routing_juist(run: dict, expect: dict) -> bool:
    """KPI-01-granulariteit: de juiste diensten (transacties + informatie)."""
    paths = run["transaction"]["routing"]["paths"]
    return (paths["transactions"] == expect["transactions"]
            and paths["info"] == expect["info"])


def besluit_juist(run: dict, expect: dict) -> bool:
    """KPI-02-granulariteit: outcome, status én paden samen (volledig juist besluit)."""
    routing = run["transaction"]["routing"]
    return (routing["outcome"] == expect["outcome"]
            and run["transaction"]["status"] == expect.get("status", "gereed")
            and routing_juist(run, expect))


def brontraceerbaarheid(run: dict) -> tuple[int, int]:
    """KPI-03: elke context-regel, elk prefill-veld en elke routing-uitleg
    draagt een niet-lege bronverwijzing (uitleg zonder bron = faal)."""
    transactie = run["transaction"]
    controles: list[dict] = list(transactie["context"]["regels"])
    for tr in transactie["prefill"]["transacties"]:
        controles += tr["velden"]
    controles += transactie["routing"]["uitleg"]
    met_bron = sum(1 for item in controles if str(item.get("bron", "")).strip())
    return met_bron, len(controles)


def transactiesucces(run: dict, expect: dict) -> bool | None:
    """KPI-04: intake→ontvangstbewijs zonder tussentijdse fout. None = scenario
    valt buiten de E2E-populatie (verwacht géén successtatus of géén transacties)."""
    if not str(expect.get("status", "gereed")).startswith("gereed") or not expect.get("transactions"):
        return None
    if not str(run["transaction"]["status"]).startswith("gereed"):
        return False
    ontvangst = {r["service"]: r["status"]
                 for r in run["transaction"]["submission"]["ontvangst"]["transacties"]}
    return all(ontvangst.get(sv) == "geaccepteerd" for sv in expect["transactions"])


def once_only_vragen(events: list, manifest: dict) -> dict:
    """KPI-06 (proxy retourvragen): de intake-gate vraagt nooit om slots die uit
    authentieke bronnen komen (once-only, FR-11-geest)."""
    authentiek = {slot for slot, spec in manifest["contextSchema"]["slots"].items()
                  if spec.get("authenticSource")}
    vragen = [e["payload"]["slot"] for e in events if e["kind"] == "context_vraag"]
    return {"authentieke_slot_vragen": sum(1 for s in vragen if s in authentiek),
            "vragen_totaal": len(vragen)}


def h_events_consistent(events: list) -> tuple[int, int]:
    """Elk H-gate-request heeft een passend verdict (gegeven|geweigerd) en elk
    handover-event draagt naar + reden (go/no-go-criterium uit de baseline)."""
    per_gate: dict[str, dict] = {}
    for e in events:
        if e["kind"] in ("gate_request", "gate_verdict"):
            gate = e["payload"].get("gate")
            if gate:
                per_gate.setdefault(gate, {"request": False, "geldig_verdict": False})
                if e["kind"] == "gate_request":
                    per_gate[gate]["request"] = True
                elif e["payload"].get("verdict") in ("gegeven", "geweigerd"):
                    per_gate[gate]["geldig_verdict"] = True
                else:
                    per_gate[gate]["ongeldig_verdict"] = True
    checks = [not info.get("ongeldig_verdict") and info["request"] and info["geldig_verdict"]
              for info in per_gate.values()]
    handovers = [e for e in events if e["kind"] == "handover"]
    checks += [bool(e["payload"].get("naar")) and bool(e["payload"].get("reden"))
               for e in handovers]
    return sum(1 for c in checks if c), len(checks)


def _pct( telling: tuple[int, int]) -> float | None:
    deel, totaal = telling
    return None if totaal == 0 else round(100.0 * deel / totaal, 1)


def rapport(golden_runs: list[tuple[dict, list, dict]], manifest: dict) -> dict:
    """Aggregeert de KPI's over (run, events, expect)-triples van de golden set
    tot een oordeel conform de baseline-goNoGo (zonder exit-test: die telt er
    pas bij zodra de export-herleiding meedraait, zie eval.py --exit)."""
    n = len(golden_runs)
    kpi01 = _pct((sum(1 for run, _e, expect in golden_runs if routing_juist(run, expect)), n))
    kpi02 = _pct((sum(1 for run, _e, expect in golden_runs if besluit_juist(run, expect)), n))
    bron = [brontraceerbaarheid(run) for run, _e, _x in golden_runs]
    kpi03 = _pct((sum(m for m, _t in bron), sum(t for _m, t in bron)))
    e2e = [transactiesucces(run, expect) for run, _e, expect in golden_runs]
    e2e = [u for u in e2e if u is not None]
    kpi04 = _pct((sum(1 for u in e2e if u), len(e2e)))
    vragen = [once_only_vragen(events, manifest) for _r, events, _x in golden_runs]
    authentieke_vragen = sum(v["authentieke_slot_vragen"] for v in vragen)
    vragen_totaal = sum(v["vragen_totaal"] for v in vragen)
    h_correct, h_totaal = (0, 0)
    for _r, events, _x in golden_runs:
        c, t = h_events_consistent(events)
        h_correct, h_totaal = h_correct + c, h_totaal + t
    kpi_h = _pct((h_correct, h_totaal))
    d = drempels(manifest)

    kpis_block = {
        "KPI-01": {"waarde": kpi01, "drempel": d["kpi01_min"], "doel": d["kpi01_doel"], "ok": (kpi01 or 0) >= d["kpi01_min"]},
        "KPI-02": {"waarde": kpi02, "drempel": d["kpi02_min"], "ok": kpi02 == d["kpi02_min"]},
        "KPI-03": {"waarde": kpi03, "drempel": d["kpi03_min"], "ok": kpi03 == d["kpi03_min"]},
        "KPI-04": {"waarde": kpi04, "drempel": d["kpi04_min"], "ok": kpi04 is None or kpi04 >= d["kpi04_min"]},
        "KPI-06": {"authentieke_slot_vragen": authentieke_vragen, "vragen_totaal": vragen_totaal,
                   "ok": authentieke_vragen == 0},
        "H-events": {"waarde": kpi_h, "correct": h_correct, "totaal": h_totaal, "ok": kpi_h == 100.0},
    }
    details = {
        "KPI-06": lambda info: (f"{info['authentieke_slot_vragen']} vragen om authentieke slots "
                                f"(once-only vereist 0)"),
        "H-events": lambda info: f"{info['correct']}/{info['totaal']} H-events correct gelogd (100 vereist)",
    }
    belemmeringen = []
    for naam, info in kpis_block.items():
        if not info["ok"]:
            detail = details.get(naam, lambda i: f"drempel {i.get('drempel')} niet gehaald ({i.get('waarde')})")(info)
            belemmeringen.append(f"{naam}: {detail}")
    return {"kpis": kpis_block, "goNoGo": "NO-GO" if belemmeringen else "GO", "belemmeringen": belemmeringen}
