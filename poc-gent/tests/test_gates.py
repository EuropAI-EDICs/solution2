"""H1: context bevestigen of corrigeren; correcties zijn transactie-input en
overschrijven nooit een authentieke bron (FR-05, DATA-06, FR-08-groei)."""

from pathlib import Path

import pytest

from core import catalog, context, gates

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def _build(address):
    slots = {"applicantType": "ondernemer", "address": address, "activity": "herstelwerken"}
    return context.build(MANIFEST, slots, POC_ROOT)


def test_adrescorrectie_herberekent_zones_zonder_geconfirmeerde_feiten_te_verliezen():
    ctx, herkomst = _build("Koningin Maria Hendrikaplein 1, Gent")
    assert ctx["zoneLez"] == "niet-in"
    ctx2, herkomst2 = gates.confirm_h1(MANIFEST, ctx, herkomst, {"address": "Korenmarkt 1, Gent"}, POC_ROOT)
    assert ctx2["address"] == "Korenmarkt 1, Gent"
    assert ctx2["zoneLez"] == "in"
    assert ctx2["zoneAutovrij"] == "in"
    assert herkomst2["address"] == {"label": "correctie", "bron": "gebruiker (H1)"}
    assert ctx2["applicantType"] == "ondernemer"  # eerder bevestigd feit blijft geldig


def test_correctie_op_authentiek_slot_wordt_geweigerd():
    ctx, herkomst = _build("Korenmarkt 1, Gent")
    with pytest.raises(ValueError, match="authentiek"):
        gates.confirm_h1(MANIFEST, ctx, herkomst, {"vehicle": "1-ABC-123"}, POC_ROOT)
