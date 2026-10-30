"""ACM/IDM-mock: authenticatie levert identiteit en mandaten (FR-09, INT-01)."""

from pathlib import Path

import pytest

from adapters import acm_idm_mock

POC_ROOT = Path(__file__).resolve().parents[1]


def test_authenticate_levert_identiteit_met_pseudoniem():
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "sanne")
    assert identiteit["pseudoniem"] == "rrn-••••481"
    assert identiteit["type"] == "ondernemer"
    assert identiteit["mandaten"] == []


def test_onbekende_persona_faalt_duidelijk():
    with pytest.raises(KeyError):
        acm_idm_mock.authenticate(POC_ROOT, "bestaatniet")


def test_geldig_mandaat_controleert_rol_tegen_context():
    identiteit = acm_idm_mock.authenticate(POC_ROOT, "ellen")
    assert acm_idm_mock.geldig_mandaat(identiteit, {"mandate": "bewindvoering"}) is True
    assert acm_idm_mock.geldig_mandaat(identiteit, {"mandate": "iets-anders"}) is False
    assert acm_idm_mock.geldig_mandaat(identiteit, {}) is False
