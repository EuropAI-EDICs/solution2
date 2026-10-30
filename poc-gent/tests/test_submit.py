"""Backoffice-mock + submit: idempotent, deterministisch ontvangstbewijs (FR-16, INT-03/06, NFR-04)."""

import pytest

from adapters import backoffice_mock
from core import submit


def test_referentie_is_deterministisch_en_idempotent():
    eerste = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    tweede = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    assert eerste == tweede
    assert eerste["referentie"] == "GENT-" + "abc123"[:12].upper()
    assert eerste["status"] in ("geaccepteerd", "in-wachtrij")


def test_andere_sleutel_andere_referentie():
    a = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    b = backoffice_mock.dien_in("district09-vergunningen", {"x": 2}, "def456")
    assert a["referentie"] != b["referentie"]


def test_onbekend_contract_faalt():
    with pytest.raises(KeyError):
        backoffice_mock.dien_in("bestaat-niet", {}, "x")


def test_submit_een_transactie():
    formulieren = [{"service": "ontheffing-lez", "velden": [{"veld": "k", "waarde": "1-ABC-123"}], "ontbrekend": []}]
    resultaat = submit.dien_in("gent-mobiliteit-ondernemer", "sanne", formulieren)
    assert len(resultaat) == 1
    assert resultaat[0]["service"] == "ontheffing-lez"
    assert resultaat[0]["referentie"].startswith("GENT-")
    opnieuw = submit.dien_in("gent-mobiliteit-ondernemer", "sanne", formulieren)
    assert opnieuw == resultaat
