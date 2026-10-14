import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402

_MIN_NORMCARD = {
    "id": "NC-WIND-01",
    "evidenceId": "EVW-01",
    "claim": "Windturbines zijn opgijkrachtig toegelaten binnen de door de provincie aangewezen windgebieden.",
    "source": {"documentUrl": "https://lokaleregelgeving.overheid.nl/CVDR709135", "locator": "art. 1"},
    "instrument": "Omgevingsverordening Zeeland (CVDR709135)",
    "instrumentType": "omgevingsverordening-nl",
    "jurisdictie": "nl",
    "legalForce": "binding",
    "theme": "energy:wind",
    "confidence": 0.95,
    "verified": True,
    "extractedBy": {"agent": "curator", "session": "poc-nspd-task6"},
    "extractedAt": "2026-10-14T00:00:00Z",
    "appliesTo": {"track": "wind"},
}


def test_normcard_jurisdictie_verplicht():
    contracts.validate(_MIN_NORMCARD, "norm-card")


def test_normcard_zonder_jurisdictie_faalt():
    bad = dict(_MIN_NORMCARD)
    del bad["jurisdictie"]
    try:
        contracts.validate(bad, "norm-card")
    except Exception as exc:
        assert "jurisdictie" in str(exc)
    else:
        raise AssertionError("jurisdictie-mismatch moet falen")


def test_normcard_verkeerde_instrumenttype_faalt():
    bad = dict(_MIN_NORMCARD)
    bad["instrumentType"] = "rup-be"  # NL-kaart met BE-instrument
    try:
        contracts.validate(bad, "norm-card")
    except Exception:
        pass
    else:
        raise AssertionError("nl-kaart met rup-be moet door jurisdictie-check falen")
