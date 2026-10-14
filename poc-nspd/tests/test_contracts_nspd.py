import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import contracts  # noqa: E402

_MIN_NORMCARD = {
    "id": "NC-WIND-01",
    "evidenceId": "EVW-01",
    "claim": "Windturbines zijn opgijkrachtig toegelaten binnen de door de provincie aangewezen windgebieden.",
    "source": {
        "docId": "S01",
        "article": "Artikel 18.17",
        "version": "CVDR709135, geldend van 02-06-2026 t/m heden",
        "quote": "Een omgevingsplan kan voorzien in de realisatie van een nieuwe windturbine, met een hogere tiphoogte dan 21 meter, binnen een globaal aangegeven windenergie concentratielocatie",
        "quoteLanguage": "nl",
        "uri": "https://lokaleregelgeving.overheid.nl/CVDR709135",
        "retrievedAt": "2026-10-14",
    },
    "instrument": "Omgevingsverordening Zeeland (CVDR709135)",
    "instrumentType": "omgevingsverordening-nl",
    "jurisdictie": "nl",
    "legalForce": "binding",
    "theme": "energy:wind",
    "confidence": 0.95,
    "verified": True,
    "extractedBy": "curator#poc-nspd-task4",
    "extractedAt": "2026-10-14",
    "appliesTo": {"objectType": "wind_turbine"},
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


_SOURCES = json.loads((ROOT / "corpus" / "sources.json").read_text(encoding="utf-8"))


def test_voorbeeld_docids_bestaan_in_register():
    def _doc_ids(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "docId":
                    yield value
                else:
                    yield from _doc_ids(value)
        elif isinstance(node, list):
            for item in node:
                yield from _doc_ids(item)

    ids = set(_doc_ids(_MIN_NORMCARD))
    assert ids, "voorbeeld bevat geen docId's"
    for doc_id in ids:
        assert doc_id in _SOURCES, f"docId {doc_id} ontbreekt in corpus/sources.json"
