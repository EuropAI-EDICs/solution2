# nldt/tests/test_simulation_regelrecht.py
"""Tests voor de RegelRecht-simulaties (spec 2026-09-29-simulation-regelrecht-design)."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGELRECHT_DIR = ROOT / "nldt" / "simulation" / "regelrecht"
sys.path.insert(0, str(REGELRECHT_DIR))

from jsonschema import Draft202012Validator  # noqa: E402


def _schema():
    return Draft202012Validator(
        json.loads((REGELRECHT_DIR / "simulation-run.schema.json").read_text())
    )


def _minimal_run():
    return {
        "schemaVersion": "1",
        "runId": "deadbeef",
        "generatedAt": "2026-09-29T00:00:00Z",
        "poc": "utrecht",
        "instrument": {
            "title": "Omgevingsverordening provincie Utrecht",
            "cvdr": "CVDR704250",
            "regulatoryLayer": "PROVINCIALE_VERORDENING",
            "article": "5.3",
        },
        "sourceArtifacts": [
            {"path": "poc/corpus/normcards-wind.json", "role": "normcard", "sha256": "00" * 32}
        ],
        "machineReadable": {"endpoint": "e", "execution": {}},
        "articleQuote": (
            "Een omgevingsplan dat betrekking heeft op locaties binnen het Gebied kleine "
            "windturbine kan regels bevatten die de realisatie van een windturbine tot een "
            "ashoogte van 20 meter toestaat onder de voorwaarde dat de windturbine wordt "
            "geplaatst op of in aansluiting op bestaand bouwperceel."
        ),
        "demoCases": [
            {
                "id": "utrecht-01",
                "inputs": {"ashoogte_m": 19, "op_of_in_aansluiting_op_bestaand_bouwperceel": True,
                           "in_gebied_kleine_windturbine": True},
                "expectedOutputs": {"toegestaan_kleine_windturbine": True},
                "trace": [],
            }
        ],
        "abstentions": {"count": 13, "label": "ambigue FormalRules", "source": "poc/corpus/formalrules-wind.json"},
        "humanOnTheButtons": "v4_pending",
        "validations": [{"level": "V0", "verdict": "pass", "evidence": "simulation-run.schema.json"}],
    }


class TestRunContract(unittest.TestCase):
    def test_minimal_run_is_valid(self):
        _schema().validate(_minimal_run())

    def test_human_on_the_buttons_is_pinned_enum(self):
        run = _minimal_run()
        run["humanOnTheButtons"] = "v4_pass"
        with self.assertRaises(Exception):
            _schema().validate(run)

    def test_missing_artifact_sha_fails(self):
        run = _minimal_run()
        del run["sourceArtifacts"][0]["sha256"]
        with self.assertRaises(Exception):
            _schema().validate(run)


if __name__ == "__main__":
    unittest.main()
