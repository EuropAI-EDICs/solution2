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


from reference_engine import EngineError, evaluate  # noqa: E402

UTRECHT_EXECUTION = {
    "parameters": [
        {"name": "ashoogte_m", "type": "number"},
        {"name": "op_of_in_aansluiting_op_bestaand_bouwperceel", "type": "boolean"},
    ],
    "input": [{"name": "in_gebied_kleine_windturbine", "type": "boolean"}],
    "output": [{"name": "toegestaan_kleine_windturbine", "type": "boolean"}],
    "actions": [
        {
            "output": "toegestaan_kleine_windturbine",
            "value": {
                "operation": "AND",
                "conditions": [
                    {"operation": "LESS_THAN_OR_EQUAL", "subject": "$ashoogte_m", "value": 20},
                    {"operation": "EQUALS", "subject": "$op_of_in_aansluiting_op_bestaand_bouwperceel", "value": True},
                    {"operation": "EQUALS", "subject": "$in_gebied_kleine_windturbine", "value": True},
                ],
            },
        }
    ],
}

EINDHOVEN_EXECUTION = {
    "parameters": [{"name": "voorschriften_verbonden_voor_iwt", "type": "boolean"}],
    "input": [{"name": "strijd_met_tijdelijk_deel", "type": "boolean"}],
    "output": [{"name": "regels_hoofdstuk_van_toepassing", "type": "boolean"}],
    "actions": [
        {
            "output": "regels_hoofdstuk_van_toepassing",
            "value": {
                "operation": "IF",
                "cases": [
                    {"when": {"operation": "EQUALS", "subject": "$strijd_met_tijdelijk_deel", "value": True}, "then": False},
                    {"when": {"operation": "EQUALS", "subject": "$voorschriften_verbonden_voor_iwt", "value": True}, "then": False},
                ],
                "default": True,
            },
        }
    ],
}


class TestReferenceEngine(unittest.TestCase):
    def test_utrecht_and_all_true(self):
        r = evaluate(UTRECHT_EXECUTION, {"ashoogte_m": 19, "op_of_in_aansluiting_op_bestaand_bouwperceel": True, "in_gebied_kleine_windturbine": True})
        self.assertIs(r["outputs"]["toegestaan_kleine_windturbine"], True)
        self.assertEqual(len(r["trace"]), 4)  # 3 condities + 1 AND

    def test_utrecht_boundary_exactly_20_passes(self):
        r = evaluate(UTRECHT_EXECUTION, {"ashoogte_m": 20, "op_of_in_aansluiting_op_bestaand_bouwperceel": True, "in_gebied_kleine_windturbine": True})
        self.assertIs(r["outputs"]["toegestaan_kleine_windturbine"], True)

    def test_utrecht_21_fails(self):
        r = evaluate(UTRECHT_EXECUTION, {"ashoogte_m": 21, "op_of_in_aansluiting_op_bestaand_bouwperceel": True, "in_gebied_kleine_windturbine": True})
        self.assertIs(r["outputs"]["toegestaan_kleine_windturbine"], False)

    def test_trace_entry_shape(self):
        r = evaluate(UTRECHT_EXECUTION, {"ashoogte_m": 19, "op_of_in_aansluiting_op_bestaand_bouwperceel": False, "in_gebied_kleine_windturbine": True})
        entry = r["trace"][-1]
        self.assertEqual(entry["action"], "toegestaan_kleine_windturbine")
        self.assertEqual(entry["operation"], "AND")
        self.assertIs(entry["result"], False)
        self.assertEqual(entry["operands"]["conditions"][0]["subject"], "$ashoogte_m")

    def test_eindhoven_if_first_case_wins(self):
        r = evaluate(EINDHOVEN_EXECUTION, {"strijd_met_tijdelijk_deel": True, "voorschriften_verbonden_voor_iwt": True})
        self.assertIs(r["outputs"]["regels_hoofdstuk_van_toepassing"], False)

    def test_eindhoven_default(self):
        r = evaluate(EINDHOVEN_EXECUTION, {"strijd_met_tijdelijk_deel": False, "voorschriften_verbonden_voor_iwt": False})
        self.assertIs(r["outputs"]["regels_hoofdstuk_van_toepassing"], True)

    def test_unknown_operation_raises(self):
        with self.assertRaises(EngineError):
            evaluate({"output": [{"name": "x"}], "actions": [{"output": "x", "value": {"operation": "XOR", "conditions": []}}]}, {})

    def test_unknown_reference_raises(self):
        with self.assertRaises(EngineError):
            evaluate(UTRECHT_EXECUTION, {"ashoogte_m": 19})

    def test_literal_action_value_becomes_output(self):
        execution = {
            "output": [{"name": "max_hoogte"}],
            "actions": [{"output": "max_hoogte", "value": 20}],
        }
        r = evaluate(execution, {})
        self.assertEqual(r["outputs"]["max_hoogte"], 20)
        self.assertEqual(r["trace"], [])

    def test_reference_action_value_resolves(self):
        execution = {
            "output": [{"name": "afgeleide"}],
            "actions": [{"output": "afgeleide", "value": "$bron"}],
        }
        r = evaluate(execution, {"bron": 7})
        self.assertEqual(r["outputs"]["afgeleide"], 7)


import build_runs  # noqa: E402

STAMP = "2026-09-29T00:00:00Z"


class TestGeneratorUtrecht(unittest.TestCase):
    # NB: attribuut heet run_data (niet run) — `run` shadowed unittest.TestCase.run.
    @classmethod
    def setUpClass(cls):
        cls.run_data = build_runs.build_utrecht_run(build_runs.load_artifacts("utrecht"), STAMP)

    def test_instrument_fields(self):
        self.assertEqual(self.run_data["instrument"]["cvdr"], "CVDR704250")
        self.assertEqual(self.run_data["instrument"]["article"], "5.3")
        self.assertEqual(self.run_data["poc"], "utrecht")

    def test_quote_is_verbatim_from_normcard(self):
        cards = json.loads((ROOT / "poc/corpus/normcards-wind.json").read_text())
        quote = next(c for c in cards if c["id"] == "NC-W-03")["source"]["quote"]
        self.assertEqual(" ".join(self.run_data["articleQuote"].split()), " ".join(quote.split()))

    def test_twelve_cases(self):
        self.assertEqual(len(self.run_data["demoCases"]), 12)
        ids = [c["id"] for c in self.run_data["demoCases"]]
        self.assertEqual(len(set(ids)), 12)

    def test_boundary_case_outputs(self):
        by_id = {c["id"]: c for c in self.run_data["demoCases"]}
        self.assertIs(by_id["utrecht-h19-p1-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], True)
        self.assertIs(by_id["utrecht-h21-p1-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], False)
        self.assertIs(by_id["utrecht-h20-p0-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], False)

    def test_abstentions_thirteen_ambiguous(self):
        rules = json.loads((ROOT / "poc/corpus/formalrules-wind.json").read_text())
        self.assertEqual(self.run_data["abstentions"]["count"], sum(1 for r in rules if r["status"] == "ambiguous"))
        self.assertEqual(self.run_data["abstentions"]["count"], 13)

    def test_run_schema_valid(self):
        _schema().validate(self.run_data)

    def test_artifact_shas_match_disk(self):
        for a in self.run_data["sourceArtifacts"]:
            self.assertEqual(a["sha256"], build_runs.sha256_of(ROOT / a["path"]))

    def test_yaml_revalidation_evidence(self):
        v0 = [v for v in self.run_data["validations"] if v["level"] == "V0"]
        self.assertTrue(any("v0.7.1" in v["evidence"] for v in v0))


if __name__ == "__main__":
    unittest.main()
