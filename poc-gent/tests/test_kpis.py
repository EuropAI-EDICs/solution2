"""KPI-harness (F4): drempels en meetlogica achter de go/no-go-criteria uit de
baseline (KPI-01/02/03/04/06, H-event-controle) — ontwerp §8.1/§8.3."""

from core import kpis

MANIFEST = {"contextSchema": {"slots": {
    "address": {"authenticSource": None},
    "activity": {"authenticSource": None},
    "vehicle": {"authenticSource": "magda:kenteken"},
}}}


def _run(outcome="paden", status="gereed", transactions=("ontheffing-lez",), info=("info-lez",),
         uitleg_bronnen=("LEZ-reglement",), ontvangst_status="geaccepteerd",
         context_bronnen=("gesprek", "gesprek"), prefill_bronnen=("magda:kenteken.kenteken",)):
    return {"transaction": {
        "status": status,
        "context": {"regels": [{"feit": f, "waarde": "x", "label": "gebruiker", "bron": b}
                               for f, b in zip(("address", "activity"), context_bronnen)]},
        "routing": {"outcome": outcome,
                    "paths": {"transactions": list(transactions), "info": list(info)},
                    "uitleg": [{"regelId": "R1", "tekst": "uitleg", "bron": b} for b in uitleg_bronnen]},
        "prefill": {"transacties": [{"service": "ontheffing-lez",
                                     "velden": [{"veld": "kenteken", "waarde": "1-ABC-123",
                                                 "label": "authentiek", "bron": b}
                                                for b in prefill_bronnen],
                                     "ontbrekend": []}]},
        "submission": {"ontvangst": {"transacties": [
            {"service": sv, "referentie": "GENT-X", "status": ontvangst_status}
            for sv in transactions]}},
    }}


def _expect(status="gereed", transactions=("ontheffing-lez",)):
    return {"outcome": "paden", "transactions": list(transactions), "info": ["info-lez"], "status": status}


def _event(kind, payload):
    return {"seq": 0, "ts": "-", "kind": kind, "payload": payload, "prevHash": "", "hash": ""}


EVENTS = [
    _event("context_vraag", {"slot": "address", "vraag": "adres?", "bron": "intake-gate"}),
    _event("context_vraag", {"slot": "activity", "vraag": "werk?", "bron": "intake-gate"}),
    _event("gate_request", {"gate": "H1", "feitnamen": ["address"]}),
    _event("gate_verdict", {"gate": "H1", "verdict": "gegeven"}),
    _event("gate_request", {"gate": "H2", "uitleg": {}}),
    _event("gate_verdict", {"gate": "H2", "verdict": "gegeven"}),
    _event("gate_request", {"gate": "H3", "concept": []}),
    _event("gate_verdict", {"gate": "H3", "verdict": "gegeven"}),
    _event("gate_request", {"gate": "H4", "transacties": ["ontheffing-lez"]}),
    _event("gate_verdict", {"gate": "H4", "verdict": "gegeven"}),
]


def test_routing_juist_keurt_paden():
    assert kpis.routing_juist(_run(), _expect()) is True
    assert kpis.routing_juist(_run(transactions=("ontheffing-lez", "ontheffing-autovrij")), _expect()) is False
    assert kpis.routing_juist(_run(info=()), _expect()) is False


def test_besluit_juist_keurt_status_en_outcome():
    assert kpis.besluit_juist(_run(), _expect()) is True
    assert kpis.besluit_juist(_run(status="blokkade"), _expect()) is False
    assert kpis.besluit_juist(_run(outcome="escalatie", info=()), _expect()) is False


def test_brontraceerbaarheid_telt_context_prefill_en_uitleg():
    met, totaal = kpis.brontraceerbaarheid(_run())
    assert (met, totaal) == (4, 4)  # 2 context-regels + 1 prefill-veld + 1 uitleg
    met, totaal = kpis.brontraceerbaarheid(_run(uitleg_bronnen=("",)))
    assert (met, totaal) == (3, 4)  # uitleg zonder bron = faal (baseline-tekst)


def test_transactiesucces_drie_takken():
    assert kpis.transactiesucces(_run(), _expect()) is True
    assert kpis.transactiesucces(_run(ontvangst_status="niet-ingediend"), _expect()) is False
    assert kpis.transactiesucces(_run(status="blokkade"), _expect()) is False
    assert kpis.transactiesucces(_run(transactions=()), _expect(status="gereed", transactions=())) is None
    assert kpis.transactiesucces(_run(), _expect(status="blokkade")) is None  # buiten E2E-populatie


def test_once_only_vragen_tegen_authentieke_slots():
    assert kpis.once_only_vragen(EVENTS, MANIFEST) == {"authentieke_slot_vragen": 0, "vragen_totaal": 2}
    met_vehicle = EVENTS + [_event("context_vraag", {"slot": "vehicle", "vraag": "kenteken?", "bron": "x"})]
    assert kpis.once_only_vragen(met_vehicle, MANIFEST)["authentieke_slot_vragen"] == 1


def test_h_events_consistent_vereist_verdict_per_gate():
    correct, totaal = kpis.h_events_consistent(EVENTS)
    assert (correct, totaal) == (4, 4)
    zonder_h4 = [e for e in EVENTS if not (e["kind"] == "gate_verdict" and e["payload"]["gate"] == "H4")]
    assert kpis.h_events_consistent(zonder_h4) == (3, 4)
    ongeldig = [_event("gate_verdict", {"gate": "H4", "verdict": "misschien"})]
    assert kpis.h_events_consistent(EVENTS + ongeldig)[0] < kpis.h_events_consistent(EVENTS + ongeldig)[1]


def test_h_events_handover_moet_naar_en_reden_hebben():
    compleet = EVENTS + [_event("handover", {"gate": "H5", "naar": "Gentinfo", "reden": "onbekend"})]
    assert kpis.h_events_consistent(compleet)[0] == 5
    incompleet = EVENTS + [_event("handover", {"gate": "H5", "naar": "Gentinfo"})]
    assert kpis.h_events_consistent(incompleet) == (4, 5)


def test_rapport_geeft_go_als_alle_drempels_haalen():
    rap = kpis.rapport([(_run(), EVENTS, _expect())], MANIFEST)
    assert rap["goNoGo"] == "GO"
    assert rap["kpis"]["KPI-01"]["ok"] and rap["kpis"]["KPI-04"]["ok"]


def test_rapport_geeft_nogo_met_bevindingen_bij_schendingen():
    slecht = (_run(uitleg_bronnen=("",), status="blokkade", ontvangst_status="niet-ingediend"), EVENTS, _expect())
    rap = kpis.rapport([slecht], MANIFEST)
    assert rap["goNoGo"] == "NO-GO"
    assert rap["kpis"]["KPI-02"]["ok"] is False
    assert rap["kpis"]["KPI-03"]["ok"] is False
    assert rap["belemmeringen"]


def test_rapport_once_only_schending_is_nogo():
    events_met_authentieke_vraag = EVENTS + [
        _event("context_vraag", {"slot": "vehicle", "vraag": "kenteken?", "bron": "x"})]
    rap = kpis.rapport([(_run(), events_met_authentieke_vraag, _expect())], MANIFEST)
    assert rap["goNoGo"] == "NO-GO"
    assert any("once-only" in b or "authentiek" in b for b in rap["belemmeringen"])


def test_drempels_per_pakket_configureerbaar():
    manifest = {"kpiDrempels": {"kpi01_min": 80.0}}
    d = kpis.drempels(manifest)
    assert d["kpi01_min"] == 80.0 and d["kpi02_min"] == 100.0
    assert kpis.drempels({}) == kpis.DREMPELS
