# RegelRecht-simulaties (fase 1: Utrecht + Eindhoven) — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De PoC-simulaties van Utrecht en Eindhoven herinrichten volgens het RegelRecht-principe: demo-data als versioned, gevalideerd contract, deterministisch gegenereerd uit echte PoC-artefacten, met een interactieve mini-engine die live rekent onder een golden set.

**Architecture:** Eén generator (`build_runs.py`) leest alleen-lezen de voorbeeld-YAML's en canonieke run-artefacten, her-valideert ze tegen het vastgepinde regelrecht-schema v0.7.1, berekent demo-cases met een Python-referentie-executor, schrijft run-JSON's (gevalideerd tegen een eigen run-contract) en vult een single-file HTML-template. De JS-mini-engine reproduceert de golden set bij elke paginalading (selftest-badge). Spec: `docs/superpowers/specs/2026-09-29-simulation-regelrecht-design.md`.

**Tech Stack:** Python 3 (nldt/.venv: stdlib + `pyyaml` + `jsonschema`), JavaScript (ESM-bestand, dual-mode CommonJS/browser), plain HTML/CSS (huisstijl nldt/simulation), Node ≥ 20 alleen voor de engine-selftest.

## Global Constraints

- Python draaien met `nldt/.venv/bin/python` (daar staan `pyyaml` en `jsonschema`); generator zelf gebruikt verder alléén stdlib.
- Alle JSON-schema's: `$schema` draft 2020-12, `additionalProperties: false` behalve waar de spec kopieën toestaat.
- Regelrecht-schema vastgepind op **v0.7.1**; byte-identieke kopie in `nldt/simulation/regelrecht/schema/` (EUPL-1.2, bron-URL in de README van die map).
- UI-tekst van de demo in het **Nederlands**; single-file, werkt vanaf `file://` — geen `fetch`, geen externe assets behalve de bestaande Google Fonts (graceful fallback).
- `poc/` en `poc-bp2op/` worden **alleen gelezen** — nooit geschreven.
- Golden set exact 16 gevallen: Utrecht 3 × 2 × 2 (ashoogte ∈ {19, 20, 21}; bouwperceel ∈ {aan, uit}; zone ∈ {binnen, buiten}), Eindhoven 2 × 2 (strijd tijdelijk deel ∈ {ja, nee}; IWT ∈ {ja, nee}).
- `humanOnTheButtons` is enum `["v4_pending"]` — geen andere waarde bestaat.
- Commits volgens repo-conventie: `feat(nldt): …` / `test(nldt): …` / `docs(nldt): …`.

---

### Task 1: Run-contract `simulation-run.schema.json`

**Files:**
- Create: `nldt/simulation/regelrecht/simulation-run.schema.json`
- Test: `nldt/tests/test_simulation_regelrecht.py`

**Interfaces:**
- Produces: JSON Schema (draft 2020-12) met `$id` `…/simulation-run/v1`; top-level verplicht: `schemaVersion, runId, generatedAt, poc, instrument, sourceArtifacts, machineReadable, articleQuote, demoCases, abstentions, humanOnTheButtons, validations`. Later taken valideren run-JSON's hier tegenaan via `Draft202012Validator`.

- [ ] **Step 1: Schrijf de falende test**

```python
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
        "articleQuote": "…",
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
```

- [ ] **Step 2: Draai de test — moet falen**

Run: `cd /Users/marc/Projecten/ldttoolbox && nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v`
Expected: ERROR — `FileNotFoundError` voor `simulation-run.schema.json`.

- [ ] **Step 3: Schrijf het schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.local/simulation-run/v1",
  "title": "RegelRecht simulation run",
  "type": "object",
  "additionalProperties": false,
  "required": ["schemaVersion", "runId", "generatedAt", "poc", "instrument", "sourceArtifacts", "machineReadable", "articleQuote", "demoCases", "abstentions", "humanOnTheButtons", "validations"],
  "properties": {
    "schemaVersion": {"const": "1"},
    "runId": {"type": "string", "pattern": "^[0-9a-f]{8}$"},
    "generatedAt": {"type": "string", "format": "date-time"},
    "poc": {"enum": ["utrecht", "eindhoven"]},
    "instrument": {
      "type": "object", "additionalProperties": false,
      "required": ["title", "cvdr", "regulatoryLayer", "article"],
      "properties": {
        "title": {"type": "string"},
        "cvdr": {"type": "string"},
        "regulatoryLayer": {"type": "string"},
        "article": {"type": "string"}
      }
    },
    "sourceArtifacts": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["path", "role", "sha256"],
        "properties": {
          "path": {"type": "string"},
          "role": {"type": "string"},
          "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
        }
      }
    },
    "machineReadable": {"type": "object"},
    "articleQuote": {"type": "string", "minLength": 20},
    "demoCases": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["id", "inputs", "expectedOutputs", "trace"],
        "properties": {
          "id": {"type": "string"},
          "inputs": {"type": "object"},
          "expectedOutputs": {"type": "object"},
          "trace": {
            "type": "array",
            "items": {
              "type": "object", "additionalProperties": false,
              "required": ["action", "operation", "operands", "result"],
              "properties": {
                "action": {"type": "string"},
                "operation": {"type": "string"},
                "operands": {},
                "result": {}
              }
            }
          }
        }
      }
    },
    "abstentions": {
      "type": "object", "additionalProperties": false,
      "required": ["count", "label", "source"],
      "properties": {"count": {"type": "integer", "minimum": 0}, "label": {"type": "string"}, "source": {"type": "string"}}
    },
    "humanOnTheButtons": {"const": "v4_pending"},
    "validations": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["level", "verdict", "evidence"],
        "properties": {
          "level": {"enum": ["V0", "V1", "V2", "V3", "V4"]},
          "verdict": {"type": "string"},
          "evidence": {"type": "string"}
        }
      }
    }
  }
}
```

- [ ] **Step 4: Draai de test — moet slagen**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v`
Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/simulation-run.schema.json nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): add versioned simulation-run contract for RegelRecht demos"
```

---

### Task 2: Python-referentie-executor `reference_engine.py`

**Files:**
- Create: `nldt/simulation/regelrecht/reference_engine.py`
- Test: `nldt/tests/test_simulation_regelrecht.py` (uitbreiden)

**Interfaces:**
- Produces: `evaluate(execution: dict, inputs: dict) -> {"outputs": dict, "trace": list}`; `EngineError(Exception)` bij constructies buiten de subset. Trace-entry: `{"action": str, "operation": str, "operands": object, "result": value}` — operanden zijn de **ruwe** (ongeëvalueerde) expressies, resultaat is de uitkomst. Task 3 en 5 bouwen hierop.

- [ ] **Step 1: Schrijf de falende tests (toevoegen vóór `if __name__`)**

```python
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
```

- [ ] **Step 2: Draai — moet falen**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v`
Expected: ERROR `ModuleNotFoundError: reference_engine`.

- [ ] **Step 3: Implementatie**

```python
# nldt/simulation/regelrecht/reference_engine.py  — definitieve versie
"""Deterministische referentie-executor voor machine_readable-secties (regelrecht-subset).

Ondersteunt precies de vier operaties die de voorbeeld-YAML's gebruiken
(AND, EQUALS, LESS_THAN_OR_EQUAL, IF) plus letterlijke waarden en
$-referenties. Alles buiten die subset is een EngineError: nooit gissen.
Deze module is de norm voor de golden set; mini-engine.js moet haar
uitkomsten exact reproduceren.
"""
from __future__ import annotations


class EngineError(Exception):
    pass


def evaluate(execution: dict, inputs: dict) -> dict:
    """Voer execution.actions uit over inputs; elke actie krijgt trace-stappen."""
    scope = dict(inputs)
    trace: list = []
    for action in execution.get("actions", []):
        _resolve(action["value"], scope, trace, action["output"])
        # de actie-output staat na _resolve als laatste scope-sleutel; zie _apply
    outputs = {o["name"]: scope.get(o["name"]) for o in execution.get("output", [])}
    return {"outputs": outputs, "trace": trace}


def _resolve(node, scope, trace, label):
    if isinstance(node, str) and node.startswith("$"):
        if node[1:] not in scope:
            raise EngineError(f"onbekende referentie: {node}")
        return scope[node[1:]]
    if isinstance(node, (bool, int, float)):
        return node
    if isinstance(node, dict) and "operation" in node:
        result = _apply(node, scope, trace, label)
        scope[label] = result  # actie-output (top-level aanroep)
        return result
    if isinstance(node, str):
        return node
    raise EngineError(f"niet-ondersteunde operand: {node!r}")


def _apply(op, scope, trace, label):
    name = op["operation"]
    if name == "AND":
        condition_results = []
        for cond in op["conditions"]:
            condition_results.append(bool(_eval_condition(cond, scope, trace, label)))
        result = all(condition_results)
        trace.append({"action": label, "operation": "AND",
                      "operands": {"conditions": op["conditions"]}, "result": result})
        return result
    if name in ("EQUALS", "LESS_THAN_OR_EQUAL"):
        subject = _operand(op["subject"], scope)
        value = _operand(op["value"], scope)
        result = (subject == value) if name == "EQUALS" else (subject <= value)
        trace.append({"action": label, "operation": name,
                      "operands": {"subject": op["subject"], "value": op["value"]}, "result": result})
        return result
    if name == "IF":
        for case in op.get("cases", []):
            if bool(_eval_condition(case["when"], scope, trace, label)):
                result = _operand(case["then"], scope)
                _trace_if(trace, label, op, result, fired=len(trace))
                return result
        if "default" not in op:
            raise EngineError("IF zonder passerende case en zonder default")
        result = _operand(op["default"], scope)
        _trace_if(trace, label, op, result, fired=0)
        return result
    raise EngineError(f"niet-ondersteunde operatie: {name}")


def _eval_condition(cond, scope, trace, label):
    return _apply(cond, scope, trace, label)


def _trace_if(trace, label, op, result, fired):
    trace.append({"action": label, "operation": "IF",
                  "operands": {"cases": len(op.get("cases", [])), "default": op.get("default"), "firedCase": fired},
                  "result": result})


def _operand(node, scope):
    if isinstance(node, str) and node.startswith("$"):
        if node[1:] not in scope:
            raise EngineError(f"onbekende referentie: {node}")
        return scope[node[1:]]
    return node
```

- [ ] **Step 4: Draai — moet slagen**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v`
Expected: 11 tests OK (3 contract + 8 engine). Let op `test_utrecht_and_all_true`: 3 conditie-stappen + 1 AND-stap = 4 trace-items — de definitieve versie levert precies dat.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/reference_engine.py nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): add deterministic reference executor (regelrecht subset)"
```

---

### Task 3: Generator-basis + Utrecht-run (incl. vastgepind regelrecht-schema)

**Files:**
- Create: `nldt/simulation/regelrecht/build_runs.py`
- Create: `nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json` (vastgepinde kopie)
- Create: `nldt/simulation/regelrecht/schema/README.md`
- Generated: `nldt/simulation/regelrecht/runs/utrecht-wind-art5.3.json`
- Test: `nldt/tests/test_simulation_regelrecht.py` (uitbreiden)

**Interfaces:**
- Consumes: `reference_engine.evaluate`, `simulation-run.schema.json`, regelrecht-schema v0.7.1.
- Produces: `python build_runs.py [--stamp ISO] [--outdir DIR]` (exit 0 bij succes); functies `build_utrecht_run(artifacts: dict, stamp: str) -> dict`, `sha256_of(path) -> str`, `POC_CONFIGS: dict`. Task 4 breidt uit met Eindhoven; Task 5 met golden set + template-vulling.

- [ ] **Step 1: Pin het regelrecht-schema**

```bash
mkdir -p nldt/simulation/regelrecht/schema
curl -sL https://raw.githubusercontent.com/MinBZK/regelrecht/main/schema/v0.7.1/schema.json \
  -o nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json
nldt/.venv/bin/python -c "import jsonschema, json; jsonschema.Draft202012Validator.check_schema(json.load(open('nldt/simulation/regelrecht/schema/regelrecht-v0.7.1.schema.json'))); print('schema ok')"
```
Expected: `schema ok`. Schrijf daarna `schema/README.md`:

```markdown
# Vastgepinde schema's

`regelrecht-v0.7.1.schema.json` — byte-identieke kopie van
https://raw.githubusercontent.com/MinBZK/regelrecht/main/schema/v0.7.1/schema.json
(EUPL-1.2, MinBZK). Vastgepind zodat `build_runs.py` offline en reproduceerbaar
kan her-valideren; een nieuwere versie bewust bijwerken = nieuw bestand + aanpassing
in `build_runs.py`.
```

- [ ] **Step 2: Schrijf de falende tests**

```python
# toevoegen aan nldt/tests/test_simulation_regelrecht.py
import build_runs  # noqa: E402

STAMP = "2026-09-29T00:00:00Z"


class TestGeneratorUtrecht(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run = build_runs.build_utrecht_run(build_runs.load_artifacts("utrecht"), STAMP)

    def test_instrument_fields(self):
        self.assertEqual(self.run["instrument"]["cvdr"], "CVDR704250")
        self.assertEqual(self.run["instrument"]["article"], "5.3")
        self.assertEqual(self.run["poc"], "utrecht")

    def test_quote_is_verbatim_from_normcard(self):
        cards = json.loads((ROOT / "poc/corpus/normcards-wind.json").read_text())
        quote = next(c for c in cards if c["id"] == "NC-W-03")["source"]["quote"]
        self.assertEqual(" ".join(self.run["articleQuote"].split()), " ".join(quote.split()))

    def test_twelve_cases(self):
        self.assertEqual(len(self.run["demoCases"]), 12)
        ids = [c["id"] for c in self.run["demoCases"]]
        self.assertEqual(len(set(ids)), 12)

    def test_boundary_case_outputs(self):
        by_id = {c["id"]: c for c in self.run["demoCases"]}
        self.assertIs(by_id["utrecht-h19-p1-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], True)
        self.assertIs(by_id["utrecht-h21-p1-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], False)
        self.assertIs(by_id["utrecht-h20-p0-z1"]["expectedOutputs"]["toegestaan_kleine_windturbine"], False)

    def test_abstentions_thirteen_ambiguous(self):
        rules = json.loads((ROOT / "poc/corpus/formalrules-wind.json").read_text())
        self.assertEqual(self.run["abstentions"]["count"], sum(1 for r in rules if r["status"] == "ambiguous"))
        self.assertEqual(self.run["abstentions"]["count"], 13)

    def test_run_schema_valid(self):
        _schema().validate(self.run)

    def test_artifact_shas_match_disk(self):
        for a in self.run["sourceArtifacts"]:
            self.assertEqual(a["sha256"], build_runs.sha256_of(ROOT / a["path"]))

    def test_yaml_revalidation_evidence(self):
        v0 = [v for v in self.run["validations"] if v["level"] == "V0"]
        self.assertTrue(any("v0.7.1" in v["evidence"] for v in v0))
```

- [ ] **Step 3: Draai — moet falen**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v`
Expected: ERROR `No module named 'build_runs'`.

- [ ] **Step 4: Implementatie `build_runs.py`**

```python
#!/usr/bin/env python3
"""Deterministische generator voor de RegelRecht-PoC-simulaties.

Leest alléén echte artefacten (voorbeeld-YAML's + canonieke PoC-runs),
her-valideert de YAML's tegen het vastgepinde regelrecht-schema v0.7.1,
berekent demo-cases met reference_engine (de norm), schrijft run-JSON's
gevalideerd tegen simulation-run.schema.json, de golden set, en de
single-file demo-pagina. Zie spec 2026-09-29-simulation-regelrecht-design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator

import reference_engine

DIR = pathlib.Path(__file__).resolve().parent
ROOT = DIR.parents[2]

REGELRECHT_SCHEMA_PATH = DIR / "schema" / "regelrecht-v0.7.1.schema.json"
RUN_SCHEMA_PATH = DIR / "simulation-run.schema.json"

POC_CONFIGS = {
    "utrecht": {
        "run_file": "utrecht-wind-art5.3.json",
        "example_yaml": "docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml",
        "article_number": "5.3",
        "artifacts": [
            ("docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml", "example-yaml"),
            ("poc/corpus/normcards-wind.json", "normcard"),
            ("poc/corpus/formalrules-wind.json", "formalrule"),
            ("poc/runs/20260830T113234Z-wind/run_summary.json", "run-summary"),
        ],
        "instrument": {
            "title": "Omgevingsverordening provincie Utrecht",
            "cvdr": "CVDR704250",
            "regulatoryLayer": "PROVINCIALE_VERORDENING",
            "article": "5.3",
        },
        "abstentions": {
            "label": "ambigue FormalRules (open normen → jurist)",
            "source": "poc/corpus/formalrules-wind.json",
        },
    },
    "eindhoven": {
        "run_file": "eindhoven-bp2op-art10.2.json",
        "example_yaml": "docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml",
        "article_number": "10.2",
        "artifacts": [
            ("docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml", "example-yaml"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/bronregels.json", "bronregel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/doelregels.json", "doelregel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/omzettabel.json", "omzettabel"),
            ("poc-bp2op/runs/20260830-124515-eindhoven/kennisbank.json", "kennisbank"),
        ],
        "instrument": {
            "title": "Omgevingsplan gemeente Eindhoven",
            "cvdr": "CVDR696400_4",
            "regulatoryLayer": "GEMEENTELIJKE_VERORDENING",
            "article": "10.2",
        },
        "abstentions": {
            "label": "omzettabel-rijen needs_human (jurist)",
            "source": "poc-bp2op/runs/20260830-124515-eindhoven/omzettabel.json",
        },
    },
}


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_artifacts(poc: str) -> dict:
    cfg = POC_CONFIGS[poc]
    out = {}
    for rel, role in cfg["artifacts"]:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"ontbrekend artefact: {rel}")
        out[role] = {"path": rel, "sha256": sha256_of(p), "data": _load(p)}
    return out


def _load(p: pathlib.Path):
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(p.read_text())
    return json.loads(p.read_text())


def _regelrecht_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(REGELRECHT_SCHEMA_PATH.read_text()))


def _example_article(artifacts: dict, article_number: str) -> tuple[dict, dict]:
    doc = artifacts["example-yaml"]["data"]
    validator = _regelrecht_validator()
    validator.validate(doc)  # her-validatie: faalt expliciet bij afwijking
    for art in doc["articles"]:
        if art["number"] == article_number:
            return doc, art
    raise SystemExit(f"artikel {article_number} niet in voorbeeld-YAML")


def _execution_of(article: dict) -> dict:
    return article["machine_readable"]["execution"]


def _run_id(source_artifacts: list[dict]) -> str:
    h = hashlib.sha256()
    for a in sorted(source_artifacts, key=lambda x: x["path"]):
        h.update(a["path"].encode())
        h.update(a["sha256"].encode())
    return h.hexdigest()[:8]


def utrecht_cases(execution: dict) -> list[dict]:
    cases = []
    n = 0
    for ashoogte in (19, 20, 21):
        for perceel in (True, False):
            for zone in (True, False):
                n += 1
                inputs = {
                    "ashoogte_m": ashoogte,
                    "op_of_in_aansluiting_op_bestaand_bouwperceel": perceel,
                    "in_gebied_kleine_windturbine": zone,
                }
                r = reference_engine.evaluate(execution, inputs)
                cases.append({
                    "id": f"utrecht-h{ashoogte}-p{int(perceel)}-z{int(zone)}",
                    "inputs": inputs,
                    "expectedOutputs": r["outputs"],
                    "trace": r["trace"],
                })
    return cases


def build_utrecht_run(artifacts: dict, stamp: str) -> dict:
    cfg = POC_CONFIGS["utrecht"]
    _, article = _example_article(artifacts, cfg["article_number"])
    cards = artifacts["normcard"]["data"]
    quote = next(c for c in cards if c["id"] == "NC-W-03")["source"]["quote"]
    rules = artifacts["formalrule"]["data"]
    ambiguous = sum(1 for r in rules if r["status"] == "ambiguous")
    source_artifacts = [
        {"path": v["path"], "role": role, "sha256": v["sha256"]}
        for role, v in artifacts.items()
    ]
    return {
        "schemaVersion": "1",
        "runId": _run_id(source_artifacts),
        "generatedAt": stamp,
        "poc": "utrecht",
        "instrument": cfg["instrument"],
        "sourceArtifacts": source_artifacts,
        "machineReadable": article["machine_readable"],
        "articleQuote": quote,
        "demoCases": utrecht_cases(_execution_of(article)),
        "abstentions": {"count": ambiguous, **cfg["abstentions"]},
        "humanOnTheButtons": "v4_pending",
        "validations": [
            {"level": "V0", "verdict": "pass",
             "evidence": "voorbeeld-YAML gevalideerd tegen regelrecht-schema v0.7.1"},
            {"level": "V2", "verdict": "pass",
             "evidence": "articleQuote letterlijk uit NC-W-03 (poc/corpus/normcards-wind.json)"},
            {"level": "V4", "verdict": "pending", "evidence": "jurittoets staat structureel open (MC-6)"},
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stamp", required=True, help="ISO-timestamp voor generatedAt (herhaalbaar maken)")
    ap.add_argument("--outdir", default=None, help="optionele alternatieve uitvoermap")
    args = ap.parse_args(argv)
    outdir = pathlib.Path(args.outdir) if args.outdir else DIR
    runs_dir = outdir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    run = build_utrecht_run(load_artifacts("utrecht"), args.stamp)
    Draft202012Validator(json.loads(RUN_SCHEMA_PATH.read_text())).validate(run)
    (runs_dir / POC_CONFIGS["utrecht"]["run_file"]).write_text(
        json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK utrecht runId={run['runId']} cases={len(run['demoCases'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Draai de tests en de generator**

Run: `nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v` → 19 tests OK.
Run: `nldt/.venv/bin/python nldt/simulation/regelrecht/build_runs.py --stamp 2026-09-29T00:00:00Z`
Expected: `OK utrecht runId=… cases=12`; bestand `runs/utrecht-wind-art5.3.json` aangemaakt.

- [ ] **Step 6: Commit**

```bash
git add nldt/simulation/regelrecht/build_runs.py nldt/simulation/regelrecht/schema/ nldt/simulation/regelrecht/runs/utrecht-wind-art5.3.json nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): generate validated Utrecht RegelRecht demo-run from real artifacts"
```

---

### Task 4: Eindhoven-run in de generator

**Files:**
- Modify: `nldt/simulation/regelrecht/build_runs.py`
- Generated: `nldt/simulation/regelrecht/runs/eindhoven-bp2op-art10.2.json`
- Test: `nldt/tests/test_simulation_regelrecht.py` (uitbreiden)

**Interfaces:**
- Consumes: Task 3 (`load_artifacts`, `POC_CONFIGS`, `_example_article`, `_run_id`).
- Produces: `build_eindhoven_run(artifacts, stamp) -> dict`; case-id's `eindhoven-s{0|1}-i{0|1}`.

- [ ] **Step 1: Falende tests**

```python
class TestGeneratorEindhoven(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run = build_runs.build_eindhoven_run(build_runs.load_artifacts("eindhoven"), STAMP)

    def test_instrument_fields(self):
        self.assertEqual(self.run["instrument"]["cvdr"], "CVDR696400_4")
        self.assertEqual(self.run["instrument"]["article"], "10.2")

    def test_four_cases(self):
        self.assertEqual(len(self.run["demoCases"]), 4)

    def test_case_outputs(self):
        by_id = {c["id"]: c for c in self.run["demoCases"]}
        self.assertIs(by_id["eindhoven-s1-i1"]["expectedOutputs"]["regels_hoofdstuk_van_toepassing"], False)
        self.assertIs(by_id["eindhoven-s0-i1"]["expectedOutputs"]["regels_hoofdstuk_van_toepassing"], False)
        self.assertIs(by_id["eindhoven-s0-i0"]["expectedOutputs"]["regels_hoofdstuk_van_toepassing"], True)

    def test_quote_is_verbatim_bronregel(self):
        bronregels = json.loads((ROOT / "poc-bp2op/runs/20260830-124515-eindhoven/bronregels.json").read_text())
        tekst = next(b for b in bronregels if b["id"] == "BR-001")["tekst"]
        self.assertEqual(" ".join(self.run["articleQuote"].split()), " ".join(tekst.split()))

    def test_abstentions_seventy_needs_human(self):
        tabel = json.loads((ROOT / "poc-bp2op/runs/20260830-124515-eindhoven/omzettabel.json").read_text())
        self.assertEqual(self.run["abstentions"]["count"], sum(1 for r in tabel if r["status"] == "needs_human"))
        self.assertEqual(self.run["abstentions"]["count"], 70)

    def test_run_schema_valid(self):
        _schema().validate(self.run)
```

- [ ] **Step 2: Draai — moet falen** (`AttributeError: build_eindhoven_run`)

- [ ] **Step 3: Implementatie (toevoegen in build_runs.py)**

```python
def eindhoven_cases(execution: dict) -> list[dict]:
    cases = []
    for strijd in (True, False):
        for iwt in (True, False):
            inputs = {"strijd_met_tijdelijk_deel": strijd, "voorschriften_verbonden_voor_iwt": iwt}
            r = reference_engine.evaluate(execution, inputs)
            cases.append({
                "id": f"eindhoven-s{int(strijd)}-i{int(iwt)}",
                "inputs": inputs,
                "expectedOutputs": r["outputs"],
                "trace": r["trace"],
            })
    return cases


def build_eindhoven_run(artifacts: dict, stamp: str) -> dict:
    cfg = POC_CONFIGS["eindhoven"]
    _, article = _example_article(artifacts, cfg["article_number"])
    bronregels = artifacts["bronregel"]["data"]
    quote = next(b for b in bronregels if b["id"] == "BR-001")["tekst"]
    tabel = artifacts["omzettabel"]["data"]
    needs_human = sum(1 for r in tabel if r["status"] == "needs_human")
    source_artifacts = [
        {"path": v["path"], "role": role, "sha256": v["sha256"]}
        for role, v in artifacts.items()
    ]
    return {
        "schemaVersion": "1",
        "runId": _run_id(source_artifacts),
        "generatedAt": stamp,
        "poc": "eindhoven",
        "instrument": cfg["instrument"],
        "sourceArtifacts": source_artifacts,
        "machineReadable": article["machine_readable"],
        "articleQuote": quote,
        "demoCases": eindhoven_cases(_execution_of(article)),
        "abstentions": {"count": needs_human, **cfg["abstentions"]},
        "humanOnTheButtons": "v4_pending",
        "validations": [
            {"level": "V0", "verdict": "pass",
             "evidence": "voorbeeld-YAML gevalideerd tegen regelrecht-schema v0.7.1"},
            {"level": "V2", "verdict": "pass",
             "evidence": "articleQuote letterlijk uit BR-001 (bronregels.json canonieke run)"},
            {"level": "V4", "verdict": "pending", "evidence": "jurittoets staat structureel open (MC-6)"},
        ],
    }
```

En in `main()` na de Utrecht-tak (spiegelbeeldig):

```python
    run = build_eindhoven_run(load_artifacts("eindhoven"), args.stamp)
    Draft202012Validator(json.loads(RUN_SCHEMA_PATH.read_text())).validate(run)
    (runs_dir / POC_CONFIGS["eindhoven"]["run_file"]).write_text(
        json.dumps(run, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK eindhoven runId={run['runId']} cases={len(run['demoCases'])}")
```

- [ ] **Step 4: Draai tests + generator** → 25 tests OK; uitvoer `OK eindhoven … cases=4`.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/regelrecht/build_runs.py nldt/simulation/regelrecht/runs/eindhoven-bp2op-art10.2.json nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): generate validated Eindhoven RegelRecht demo-run"
```

---

### Task 5: Golden set + mini-engine + node-selftest

**Files:**
- Create: `nldt/simulation/regelrecht/engine/mini-engine.js` (dual-mode: CommonJS voor Node, `window.RegelRechtEngine` in browser)
- Create: `nldt/simulation/regelrecht/engine/selftest.mjs`
- Modify: `nldt/simulation/regelrecht/build_runs.py` (golden-set-generatie)
- Generated: `nldt/simulation/regelrecht/engine/engine-cases.json`
- Test: unittest die selftest.mjs via subprocess draait.

**Interfaces:**
- Consumes: run-JSON's uit Task 3/4 (`demoCases` + `machineReadable.execution`).
- Produces: `RegelRechtEngine.evaluate(execution, inputs) -> {outputs, trace}` met **exact dezelfde** trace-vorm als `reference_engine` (sleutelvolgorde `action, operation, operands, result`); `engine-cases.json`: `[{id, execution, inputs, expectedOutputs, trace}]` — 16 items.

- [ ] **Step 1: Falende unittest**

```python
import subprocess  # noqa: E402

ENGINE_DIR = REGELRECHT_DIR / "engine"


class TestGoldenSetAndJsEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.run(
            ["node", str(ENGINE_DIR / "selftest.mjs")],
            capture_output=True, text=True, cwd=str(ROOT),
        )

    def test_engine_cases_exist_and_sixteen(self):
        data = json.loads((ENGINE_DIR / "engine-cases.json").read_text())
        self.assertEqual(len(data), 16)

    def test_node_selftest_passes(self):
        self.assertEqual(self.proc.returncode, 0, msg=self.proc.stdout + self.proc.stderr)
        self.assertIn("16/16", self.proc.stdout)
```

- [ ] **Step 2: Draai — moet falen** (`FileNotFoundError` engine-cases.json / node-script)

- [ ] **Step 3: mini-engine.js**

```javascript
// nldt/simulation/regelrecht/engine/mini-engine.js
// Deterministische mini-engine voor de regelrecht-subset (AND, EQUALS,
// LESS_THAN_OR_EQUAL, IF) — spiegel van reference_engine.py. Dual-mode:
// Node (CommonJS) voor de selftest, window.RegelRechtEngine in de browser.
"use strict";

class EngineError extends Error {}

function evaluate(execution, inputs) {
  const scope = Object.assign({}, inputs);
  const trace = [];
  for (const action of execution.actions || []) {
    resolve(action.value, scope, trace, action.output);
  }
  const outputs = {};
  for (const o of execution.output || []) outputs[o.name] = scope[o.name];
  return { outputs, trace };
}

function resolve(node, scope, trace, label) {
  if (typeof node === "string" && node.startsWith("$")) {
    if (!(node.slice(1) in scope)) throw new EngineError("onbekende referentie: " + node);
    return scope[node.slice(1)];
  }
  if (typeof node !== "object" || node === null || !("operation" in node)) return node;
  const result = apply(node, scope, trace, label);
  scope[label] = result;
  return result;
}

function apply(op, scope, trace, label) {
  const name = op.operation;
  if (name === "AND") {
    const results = op.conditions.map((c) => Boolean(apply(c, scope, trace, label)));
    const result = results.every(Boolean);
    trace.push({ action: label, operation: "AND", operands: { conditions: op.conditions }, result });
    return result;
  }
  if (name === "EQUALS" || name === "LESS_THAN_OR_EQUAL") {
    const subject = operand(op.subject, scope);
    const value = operand(op.value, scope);
    const result = name === "EQUALS" ? subject === value : subject <= value;
    trace.push({ action: label, operation: name, operands: { subject: op.subject, value: op.value }, result });
    return result;
  }
  if (name === "IF") {
    let i = 0;
    for (const c of op.cases || []) {
      if (Boolean(apply(c.when, scope, trace, label))) {
        const result = operand(c.then, scope);
        trace.push({ action: label, operation: "IF", operands: { cases: (op.cases || []).length, default: op.default, firedCase: i + 1 }, result });
        return result;
      }
      i += 1;
    }
    if (!("default" in op)) throw new EngineError("IF zonder passerende case en zonder default");
    const result = operand(op.default, scope);
    trace.push({ action: label, operation: "IF", operands: { cases: (op.cases || []).length, default: op.default, firedCase: 0 }, result });
    return result;
  }
  throw new EngineError("niet-ondersteunde operatie: " + name);
}

function operand(node, scope) {
  if (typeof node === "string" && node.startsWith("$")) {
    if (!(node.slice(1) in scope)) throw new EngineError("onbekende referentie: " + node);
    return scope[node.slice(1)];
  }
  return node;
}

const Engine = { evaluate, EngineError };
if (typeof module !== "undefined" && module.exports) module.exports = Engine;
if (typeof window !== "undefined") window.RegelRechtEngine = Engine;
```

- [ ] **Step 4: selftest.mjs**

```javascript
// nldt/simulation/regelrecht/engine/selftest.mjs
// Draait de golden set (gegenereerd door build_runs.py via reference_engine)
// door de JS-mini-engine. Exit 0 alleen bij 16/16 exacte overeenkomst
// (outputs én volledige trace).
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const { evaluate } = require("./mini-engine.js");
const cases = JSON.parse(readFileSync(new URL("./engine-cases.json", import.meta.url), "utf8"));

let failed = 0;
for (const c of cases) {
  const got = evaluate(c.execution, c.inputs);
  const ok =
    JSON.stringify(got.outputs) === JSON.stringify(c.expectedOutputs) &&
    JSON.stringify(got.trace) === JSON.stringify(c.trace);
  if (!ok) {
    failed += 1;
    console.error(`FAIL ${c.id}\n  verwacht: ${JSON.stringify(c.expectedOutputs)}\n  gekregen: ${JSON.stringify(got.outputs)}`);
  }
}
console.log(`${cases.length - failed}/${cases.length}`);
process.exit(failed ? 1 : 0);
```

- [ ] **Step 5: Golden-set-generatie in build_runs.py (in main(), na beide runs)**

```python
    cases = []
    for poc in ("utrecht", "eindhoven"):
        run = json.loads((runs_dir / POC_CONFIGS[poc]["run_file"]).read_text())
        execution = run["machineReadable"]["execution"]
        for case in run["demoCases"]:
            cases.append({
                "id": case["id"],
                "execution": execution,
                "inputs": case["inputs"],
                "expectedOutputs": case["expectedOutputs"],
                "trace": case["trace"],
            })
    engine_dir = outdir / "engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    (engine_dir / "engine-cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"OK golden set cases={len(cases)}")
```

- [ ] **Step 6: Draai generator + node-selftest + unittest**

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/build_runs.py --stamp 2026-09-29T00:00:00Z
node nldt/simulation/regelrecht/engine/selftest.mjs        # → 16/16
nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v   # → 27 tests OK
```

- [ ] **Step 7: Commit**

```bash
git add nldt/simulation/regelrecht/engine/ nldt/simulation/regelrecht/build_runs.py nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): add JS mini-engine with golden-set selftest (16/16)"
```

---

### Task 6: Template + single-file demopagina

**Files:**
- Create: `nldt/simulation/regelrecht/regelrecht-demo.template.html`
- Modify: `nldt/simulation/regelrecht/build_runs.py` (template-vulling, stap 6)
- Generated: `nldt/simulation/regelrecht-demo.html`
- Test: `nldt/tests/test_simulation_regelrecht.py` (uitbreiden)

**Interfaces:**
- Consumes: run-JSON's, `engine-cases.json`, `mini-engine.js` (inline geplaatst), placeholders `__RUN_UTRECHT__`, `__RUN_EINDHOVEN__`, `__GOLDEN__`, `__ENGINE_JS__`, `__BUILD_STAMP__`.
- Produces: `regelrecht-demo.html` met PoC-switch via `?poc=utrecht|eindhoven`, ketenbalk, interactielab, eerlijkheidspaneel, selftest-badge.

- [ ] **Step 1: Falende unittest**

```python
DEMO_HTML = ROOT / "nldt" / "simulation" / "regelrecht-demo.html"


class TestDemoPage(unittest.TestCase):
    def test_page_exists_and_contains_inline_data(self):
        text = DEMO_HTML.read_text()
        for marker in ('id="run-utrecht"', 'id="run-eindhoven"', 'id="golden-cases"',
                       "window.RegelRechtEngine", "__RUN_UTRECHT__"):
            if marker.startswith("__"):
                self.assertNotIn(marker, text)  # placeholder moet gevuld zijn
            else:
                self.assertIn(marker, text)

    def test_page_quotes_articles(self):
        text = DEMO_HTML.read_text()
        self.assertIn("Gebied kleine windturbine", text)
        self.assertIn("tijdelijke deel", text)
```

- [ ] **Step 2: Draai — moet falen** (pagina bestaat nog niet)

- [ ] **Step 3: Template `regelrecht-demo.template.html`**

Volledige single-file pagina (huisstijl zoals de bestaande demo's; compact). Volledige inhoud:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
 <title>nLDT — RegelRecht: van artikel naar uitvoerbare regel</title>
  <style>
    :root {
      --paper: #e8e2d6; --ink: #1a2428; --ink-soft: #3d4a50; --muted: #6a757a;
      --teal: #0d6e6e; --teal-bright: #149494; --teal-wash: rgba(13,110,110,.12);
      --focus: #c45c26; --focus-wash: rgba(196,92,38,.15);
      --line: rgba(26,36,40,.18); --panel: #f4efe6; --ok: #1c7a4f; --fail: #b23a2f;
      --font-ui: "DM Sans", system-ui, sans-serif;
      --font-display: "Fraunces", Georgia, serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: var(--font-ui); color: var(--ink); background: var(--paper); line-height: 1.5; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
    h1 { font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 2.6rem); margin: .5rem 0 .25rem; }
    .sub { color: var(--muted); font-size: .9rem; margin-bottom: 1rem; }
    .top { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; justify-content: space-between; }
    .switch a { padding: .35rem .8rem; border: 1px solid var(--line); border-radius: 4px; text-decoration: none; color: var(--ink-soft); font-size: .85rem; }
    .switch a.active { background: var(--teal); border-color: var(--teal); color: #fff; }
    #badge { font-size: .8rem; padding: .3rem .7rem; border-radius: 999px; border: 1px solid var(--line); }
    #badge.ok { background: var(--teal-wash); color: var(--teal); border-color: var(--teal); }
    #badge.fail { background: var(--focus-wash); color: var(--focus); border-color: var(--focus); font-weight: 600; }
    section { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 1.1rem 1.25rem; margin: 1rem 0; }
    h2 { font-size: 1.05rem; margin-bottom: .6rem; color: var(--teal); }
    .chain { display: flex; flex-wrap: wrap; gap: .4rem; }
    .chain button { font: inherit; font-size: .8rem; padding: .3rem .65rem; border-radius: 4px; border: 1px solid var(--line); background: #fff; color: var(--ink-soft); cursor: pointer; }
    .chain button.active { background: var(--teal); border-color: var(--teal); color: #fff; }
    #chain-detail { margin-top: .8rem; font-size: .9rem; }
    #chain-detail pre { background: #fff; border: 1px solid var(--line); border-radius: 4px; padding: .6rem; overflow-x: auto; font-size: .78rem; }
    .lab-controls { display: flex; flex-wrap: wrap; gap: 1.25rem; align-items: center; }
    .lab-controls label { font-size: .88rem; display: inline-flex; gap: .4rem; align-items: center; }
    #verdict { font-family: var(--font-display); font-size: 1.6rem; margin: .6rem 0; }
    #verdict.ok { color: var(--ok); } #verdict.fail { color: var(--fail); }
    #trace { list-style: none; font-size: .82rem; }
    #trace li { padding: .3rem .5rem; border-left: 3px solid var(--line); margin: .25rem 0; background: #fff; }
    #trace li.ok { border-color: var(--ok); } #trace li.fail { border-color: var(--fail); }
    table { width: 100%; border-collapse: collapse; font-size: .8rem; }
    th, td { text-align: left; padding: .3rem .4rem; border-bottom: 1px solid var(--line); }
    .pill { display: inline-block; padding: .15rem .6rem; border-radius: 999px; background: var(--focus-wash); color: var(--focus); font-size: .78rem; font-weight: 600; }
    .meta { color: var(--muted); font-size: .78rem; margin-top: .6rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <nav class="switch" aria-label="PoC-keuze">
        <a href="?poc=utrecht" id="sw-utrecht">Utrecht · art. 5.3</a>
        <a href="?poc=eindhoven" id="sw-eindhoven">Eindhoven · art. 10.2</a>
      </nav>
      <span id="badge">selftest…</span>
    </div>
    <h1>Van artikel naar uitvoerbare regel</h1>
    <p class="sub" id="subtitle"></p>

    <section>
      <h2>De keten</h2>
      <div class="chain" id="chain"></div>
      <div id="chain-detail"></div>
    </section>

    <section class="lab">
      <h2>Interactielab — reken zelf</h2>
      <div class="lab-controls" id="lab-controls"></div>
      <div id="verdict"></div>
      <ol id="trace"></ol>
    </section>

    <section>
      <h2>Eerlijkheidspaneel</h2>
      <p id="abstentions" style="font-size:.88rem"></p>
      <p style="font-size:.88rem">Jurittoets (V4): <span class="pill">altijd pending — de mens op de knoppen</span></p>
      <table id="artifacts"><thead><tr><th>pad</th><th>rol</th><th>sha256</th></tr></thead><tbody></tbody></table>
      <p class="meta" id="runmeta"></p>
    </section>
  </div>

  <script type="application/json" id="run-utrecht">__RUN_UTRECHT__</script>
  <script type="application/json" id="run-eindhoven">__RUN_EINDHOVEN__</script>
  <script type="application/json" id="golden-cases">__GOLDEN__</script>
  <script>__ENGINE_JS__</script>
  <script>
    "use strict";
    const $ = (sel) => document.querySelector(sel);
    const RUNS = {
      utrecht: JSON.parse($("#run-utrecht").textContent),
      eindhoven: JSON.parse($("#run-eindhoven").textContent),
    };
    const GOLDEN = JSON.parse($("#golden-cases").textContent);
    const ENGINE = window.RegelRechtEngine;
    const OUT_LABEL = {
      toegestaan_kleine_windturbine: ["TOEGESTAAN", "NIET TOEGESTAAN"],
      regels_hoofdstuk_van_toepassing: ["VAN TOEPASSING", "NIET VAN TOEPASSING"],
    };

    // 1) selftest — golden set door de engine; bij afwijking interactie blokkeren
    (function selftest() {
      let failed = 0;
      for (const c of GOLDEN) {
        try {
          const got = ENGINE.evaluate(c.execution, c.inputs);
          if (JSON.stringify(got.outputs) !== JSON.stringify(c.expectedOutputs) ||
              JSON.stringify(got.trace) !== JSON.stringify(c.trace)) failed += 1;
        } catch (e) { failed += 1; }
      }
      const badge = $("#badge");
      if (failed === 0) {
        badge.textContent = "engine-selftest " + GOLDEN.length + "/" + GOLDEN.length;
        badge.classList.add("ok");
      } else {
        badge.textContent = "SELFTEST GEFAALD (" + failed + ") — interactie geblokkeerd";
        badge.classList.add("fail");
        document.querySelectorAll(".lab input, .lab button").forEach((el) => (el.disabled = true));
      }
    })();

    // 2) keten
    const CHAIN_STEPS = ["artikel", "bron", "machine_readable", "schema", "executie", "trace & uitkomst"];
    function renderChain(run) {
      const chain = $("#chain");
      chain.innerHTML = "";
      CHAIN_STEPS.forEach((label, i) => {
        const b = document.createElement("button");
        b.textContent = (i + 1) + ". " + label;
        b.addEventListener("click", () => showStep(run, i));
        chain.appendChild(b);
      });
      showStep(run, 0);
    }
    function showStep(run, i) {
      document.querySelectorAll("#chain button").forEach((b, j) => b.classList.toggle("active", j === i));
      const ex = run.machineReadable.execution;
      const details = [
        "<strong>Artikel " + run.instrument.article + " — " + run.instrument.title + "</strong><pre>" +
          run.articleQuote.replace(/</g, "&lt;") + "</pre>",
        "<strong>Gronding</strong><pre>" + run.sourceArtifacts.map((a) => a.role + " · " + a.path + "\n  sha256 " + a.sha256).join("\n") + "</pre>",
        "<strong>machine_readable.execution</strong><pre>" +
          JSON.stringify(ex, null, 1).replace(/</g, "&lt;") + "</pre>",
        "<strong>Schema</strong><p>VALID — regelrecht-schema v0.7.1 (her-valideerd in de build)</p>",
        "<strong>Executie-declaratie</strong><pre>parameters: " +
          JSON.stringify((ex.parameters || []).map((p) => p.name)) + "\ninput (extern): " +
          JSON.stringify((ex.input || []).map((p) => p.name)) + "\noutput: " +
          JSON.stringify((ex.output || []).map((p) => p.name)) + "</pre>",
        "<strong>Trace &amp; uitkomst</strong><p>Beweeg de controls in het interactielab hieronder — elke stap toont haar tussenstappen.</p>",
      ];
      $("#chain-detail").innerHTML = details[i];
    }

    // 3) interactielab
    function renderLab(run) {
      const poc = run.poc;
      const controls = $("#lab-controls");
      controls.innerHTML = "";
      const inputs = {};
      function addCheckbox(name, labelText, checked) {
        const id = "cb-" + name;
        const label = document.createElement("label");
        label.innerHTML = '<input type="checkbox" id="' + id + '"' + (checked ? " checked" : "") + "> " + labelText;
        controls.appendChild(label);
        const cb = label.querySelector("input");
        cb.addEventListener("change", () => { inputs[name] = cb.checked; recompute(); });
        inputs[name] = checked;
      }
      if (poc === "utrecht") {
        const label = document.createElement("label");
        label.innerHTML = 'ashoogte <output id="ash-out">19</output> m <input type="range" min="0" max="40" step="1" value="19" id="ash">';
        controls.appendChild(label);
        const slider = label.querySelector("#ash");
        slider.addEventListener("input", () => { label.querySelector("#ash-out").textContent = slider.value; inputs.ashoogte_m = Number(slider.value); recompute(); });
        inputs.ashoogte_m = 19;
        addCheckbox("op_of_in_aansluiting_op_bestaand_bouwperceel", "op/in aansluiting op bestaand bouwperceel", true);
        addCheckbox("in_gebied_kleine_windturbine", "binnen het Gebied kleine windturbine", true);
      } else {
        addCheckbox("strijd_met_tijdelijk_deel", "strijd met tijdelijk deel (hfd 22/23)", false);
        addCheckbox("voorschriften_verbonden_voor_iwt", "voorschriften verbonden vóór IWT-vergunning", false);
      }
      function recompute() {
        const execution = run.machineReadable.execution;
        const r = ENGINE.evaluate(execution, Object.assign({}, inputs));
        const outName = (ex) => ex.output[0].name;
        const name = outName(run.machineReadable.execution);
        const value = r.outputs[name];
        const verdict = $("#verdict");
        const [yes, no] = OUT_LABEL[name];
        verdict.textContent = value ? yes : no;
        verdict.className = value ? "ok" : "fail";
        const trace = $("#trace");
        trace.innerHTML = "";
        for (const step of r.trace) {
          const li = document.createElement("li");
          li.className = step.result ? "ok" : "fail";
          li.textContent = step.operation + " · " + JSON.stringify(step.operands) + " → " + step.result;
          trace.appendChild(li);
        }
      }
      recompute();
    }

    // 4) eerlijkheidspaneel + PoC-switch
    function renderHonesty(run) {
      $("#abstentions").innerHTML = "Onthoudingen: <strong>" + run.abstentions.count + "</strong> (" +
        run.abstentions.label.replace(/</g, "&lt;") + ") — bron: <code>" + run.abstentions.source + "</code>";
      const tbody = $("#artifacts tbody");
      tbody.innerHTML = "";
      for (const a of run.sourceArtifacts) {
        const tr = document.createElement("tr");
        tr.innerHTML = "<td>" + a.path + "</td><td>" + a.role + "</td><td>" + a.sha256.slice(0, 12) + "…</td>";
        tbody.appendChild(tr);
      }
      $("#runmeta").textContent = "runId " + run.runId + " · gegenereerd " + run.generatedAt + " · build " + "__BUILD_STAMP__";
    }
    function activate(poc) {
      const run = RUNS[poc] || RUNS.utrecht;
      poc = run.poc;
      $("#sw-utrecht").classList.toggle("active", poc === "utrecht");
      $("#sw-eindhoven").classList.toggle("active", poc === "eindhoven");
      $("#subtitle").textContent = run.instrument.title + " (" + run.instrument.cvdr + ") — " +
        run.instrument.regulatoryLayer.toLowerCase().replace(/_/g, " ") + ", artikel " + run.instrument.article;
      renderChain(run);
      renderLab(run);
      renderHonesty(run);
    }
    activate(new URLSearchParams(location.search).get("poc"));
  </script>
</body>
</html>
```

- [ ] **Step 4: Template-vulling in build_runs.py (laatste stap van main())**

```python
    template = (DIR / "regelrecht-demo.template.html").read_text(encoding="utf-8")
    engine_js = (DIR / "engine" / "mini-engine.js").read_text(encoding="utf-8")
    golden = (engine_dir / "engine-cases.json").read_text(encoding="utf-8")
    page = (
        template
        .replace("__RUN_UTRECHT__", (runs_dir / POC_CONFIGS["utrecht"]["run_file"]).read_text())
        .replace("__RUN_EINDHOVEN__", (runs_dir / POC_CONFIGS["eindhoven"]["run_file"]).read_text())
        .replace("__GOLDEN__", golden)
        .replace("__ENGINE_JS__", engine_js)
        .replace("__BUILD_STAMP__", args.stamp)
    )
    out_html = outdir.parent / "regelrecht-demo.html" if outdir == DIR else outdir / "regelrecht-demo.html"
    out_html.write_text(page, encoding="utf-8")
    print(f"OK demo-page {out_html}")
```

- [ ] **Step 5: Bouw en test**

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/build_runs.py --stamp 2026-09-29T00:00:00Z
nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v   # → 29 tests OK
open nldt/simulation/regelrecht-demo.html   # handcheck: badge 16/16, lab reageert, beide ?poc= varianten
```

- [ ] **Step 6: Commit**

```bash
git add nldt/simulation/regelrecht/regelrecht-demo.template.html nldt/simulation/regelrecht/build_runs.py nldt/simulation/regelrecht-demo.html nldt/tests/test_simulation_regelrecht.py
git commit -m "feat(nldt): single-file RegelRecht demo page (chain, lab, honesty panel, selftest)"
```

---

### Task 7: Integratie bestaande pagina's + README

**Files:**
- Modify: `nldt/simulation/poc-utrecht.html` (sectie vóór `<section class="demos-bar"` rond regel 242)
- Modify: `nldt/simulation/poc-eindhoven.html` (idem, rond regel 242)
- Modify: `nldt/simulation/index.html` (demo-kaart na de bestaande primary card, regels ~104 en ~130)
- Modify: `nldt/simulation/README.md`
- Test: linkcheck in `nldt/tests/test_simulation_regelrecht.py`

**Interfaces:**
- Produces: zichtbare ingangen naar `regelrecht-demo.html?poc=utrecht|eindhoven`.

- [ ] **Step 1: Falende linkcheck-test**

```python
SIM_DIR = ROOT / "nldt" / "simulation"


class TestSimulationLinks(unittest.TestCase):
    def test_story_pages_link_demo(self):
        for page, poc in (("poc-utrecht.html", "utrecht"), ("poc-eindhoven.html", "eindhoven")):
            text = (SIM_DIR / page).read_text()
            self.assertIn(f"regelrecht-demo.html?poc={poc}", text)

    def test_hub_links_demo(self):
        text = (SIM_DIR / "index.html").read_text()
        self.assertIn("regelrecht-demo.html", text)

    def test_readme_documents_build(self):
        text = (SIM_DIR / "README.md").read_text()
        self.assertIn("regelrecht-demo.html", text)
        self.assertIn("build_runs.py", text)
```

- [ ] **Step 2: Draai — moet falen**

- [ ] **Step 3: Secties toevoegen.** In beide story-pagina's direct vóór `<section class="demos-bar"`:

```html
    <section class="regelrecht-teaser" aria-label="RegelRecht">
      <h2>RegelRecht: van artikel naar uitvoerbare regel</h2>
      <p>
        De keten artikel → NormCard/bronregel → machine-leesbaar YAML → schema →
        deterministische executie → trace, gebouwd op de echte run-artefacten.
        Rekent live, onder een golden set van 16 gevallen; de jurittoets (V4)
        staat altijd open.
      </p>
      <a class="demo primary" href="regelrecht-demo.html?poc=utrecht"><div class="t">RegelRecht-demo</div><div class="d">artikel 5.3 live uitvoeren</div></a>
    </section>
```

(eindhoven-variant: `?poc=eindhoven` en `artikel 10.2 live uitvoeren`.) In `index.html` na de bestaande primary card van elk PoC:

```html
        <a class="demo" href="regelrecht-demo.html?poc=utrecht"><div class="t">RegelRecht-demo</div><div class="d">artikel → YAML → executie → trace</div></a>
```

In `simulation/README.md` onder "Per PoC" een eigen sectie:

```markdown
## RegelRecht-demo (Utrecht & Eindhoven)

[`regelrecht-demo.html`](regelrecht-demo.html) — de keten artikel → YAML → schema →
executie → trace, live rekenend op de echte voorbeeld-YAML's en run-artefacten,
met engine-selftest (16/16), onthoudingen-paneel en de altijd openstaande
jurittoets. Herbouwen:

```bash
nldt/.venv/bin/python nldt/simulation/regelrecht/build_runs.py --stamp <ISO-timestamp>
```

 gegenereerde onderdelen: `regelrecht/runs/*.json`, `regelrecht/engine/engine-cases.json`,
de single-file pagina zelf. Contract: `regelrecht/simulation-run.schema.json`;
ontwerp: `docs/superpowers/specs/2026-09-29-simulation-regelrecht-design.md`.
```

- [ ] **Step 4: Draai tests** → 32 tests OK. Handcheck: hub en story-pagina's openen vanaf `file://`, links werken.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/poc-utrecht.html nldt/simulation/poc-eindhoven.html nldt/simulation/index.html nldt/simulation/README.md nldt/tests/test_simulation_regelrecht.py
git commit -m "docs(nldt): link RegelRecht demo from stories, hub and simulation README"
```

---

### Task 8: Idempotentie, volledige suite en afronding

**Files:**
- Test: `nldt/tests/test_simulation_regelrecht.py` (laatste uitbreiding)
- Modify: `nldt/simulation/README.md` alleen als Task 7-verwijzing ontbreekt

- [ ] **Step 1: Idempotentie-test + referentie-reproductie (spec-test 3)**

```python
import tempfile  # noqa: E402


class TestIdempotency(unittest.TestCase):
    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            outs = []
            for _ in range(2):
                rc = subprocess.run(
                    ["nldt/.venv/bin/python",
                     "nldt/simulation/regelrecht/build_runs.py",
                     "--stamp", "2026-09-29T00:00:00Z", "--outdir", td],
                    capture_output=True, text=True, cwd=str(ROOT),
                )
                self.assertEqual(rc.returncode, 0, msg=rc.stderr)
                outs.append({p.name: p.read_text() for p in pathlib.Path(td).rglob("*.*")})
            self.assertEqual(outs[0], outs[1])


class TestDemoCasesReproduceInReference(unittest.TestCase):
    def test_all_cases_match_reference_engine(self):
        for poc in ("utrecht", "eindhoven"):
            run = build_runs.build_utrecht_run(build_runs.load_artifacts("utrecht"), STAMP) \
                if poc == "utrecht" else build_runs.build_eindhoven_run(build_runs.load_artifacts("eindhoven"), STAMP)
            execution = run["machineReadable"]["execution"]
            for case in run["demoCases"]:
                r = reference_engine.evaluate(execution, case["inputs"])
                self.assertEqual(r["outputs"], case["expectedOutputs"], msg=case["id"])
                self.assertEqual(r["trace"], case["trace"], msg=case["id"])
```

- [ ] **Step 2: Draai — moet slagen (dict-invoegvolgorde in `sourceArtifacts` is deterministisch via `POC_CONFIGS`). Faalt de idempotentie-test op volgordeverschil, sorteer dan in beide build-functies `source_artifacts` op `path` en draai opnieuw.**

- [ ] **Step 3: Volledige suites**

```bash
nldt/.venv/bin/python nldt/tests/test_simulation_regelrecht.py -v      # 33 tests OK
nldt/.venv/bin/python -m unittest discover -s poc/tests                # PoC-suite onaangetast (167)
python3 -m unittest discover -s poc-bp2op/tests                        # 32 tests OK
node nldt/simulation/regelrecht/engine/selftest.mjs                    # 16/16
```

- [ ] **Step 4: Eindcontrole in de browser** — `regelrecht-demo.html` vanaf `file://`: badge 16/16, beide PoC-varianten, slider/toggles kleuren condities, eerlijkheidspaneel toont 13/70 onthoudingen en V4-pending.

- [ ] **Step 5: Slotcommit**

```bash
git add nldt/tests/test_simulation_regelrecht.py
git commit -m "test(nldt): generator idempotency for RegelRecht simulations"
```
