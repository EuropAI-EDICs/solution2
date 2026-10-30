"""Beslistabellen-engine: deterministisch, met volledige trace (FR-06/07)."""

from core import rules

ONDERNEMER_LEZ = {"applicantType": "ondernemer", "zoneLez": "in", "zoneAutovrij": "in"}
ONDERNEMER_BUITEN = {"applicantType": "ondernemer", "zoneLez": "niet-in", "zoneAutovrij": "niet-in"}
ORGANISATIE_LEZ = {"applicantType": "organisatie", "zoneLez": "in", "zoneAutovrij": "in"}


def _tables():
    return {
        "id": "R-toegang", "version": "2026.10",
        "rules": [
            {"id": "R1", "when": {"zoneLez": "in", "applicantType": "ondernemer"},
             "then": {"transactions": ["ontheffing-lez"], "info": ["info-lez"]},
             "legalBasis": "LEZ-reglement (illustratief)", "uitleg": "lez-uitleg"},
            {"id": "R2", "when": {"zoneAutovrij": "in", "applicantType": "ondernemer"},
             "then": {"transactions": ["ontheffing-autovrij"]},
             "legalBasis": "verkeersplan (illustratief)", "uitleg": "autovrij-uitleg"},
            {"id": "R3", "when": {"zoneLez": "niet-in", "zoneAutovrij": "niet-in"},
             "then": {"transactions": [], "info": ["info-lez"]},
             "legalBasis": "—", "uitleg": "buiten-zones-uitleg"},
        ],
        "unknownPolicy": "escalate",
    }


def test_r1_en_r2_vuren_voor_ondernemer_in_beide_zones():
    result = rules.evaluate(_tables(), ONDERNEMER_LEZ)
    assert result["outcome"] == "paden"
    assert result["paths"]["transactions"] == ["ontheffing-lez", "ontheffing-autovrij"]
    assert result["paths"]["info"] == ["info-lez"]


def test_r3_vuurt_buiten_beide_zones():
    result = rules.evaluate(_tables(), ONDERNEMER_BUITEN)
    assert result["outcome"] == "paden"
    assert result["paths"]["transactions"] == []


def test_geen_passende_regel_escalatie():
    result = rules.evaluate(_tables(), ORGANISATIE_LEZ)
    assert result["outcome"] == "escalatie"
    assert result["paths"]["transactions"] == []
    assert result["uitleg"] == []


def test_trace_vermeldt_niet_gevuurde_regels_met_reden():
    result = rules.evaluate(_tables(), ORGANISATIE_LEZ)
    trace = {t["ruleId"]: t for t in result["trace"]}
    assert trace["R3"]["fired"] is False
    assert "zoneLez" in trace["R3"]["reden"]


def test_uitleg_draagt_legalbasis():
    result = rules.evaluate(_tables(), ONDERNEMER_LEZ)
    bronnen = {u["regelId"]: u["bron"] for u in result["uitleg"]}
    assert bronnen["R1"] == "LEZ-reglement (illustratief)"
