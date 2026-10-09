# HCS-recipes fase 1 — The Key end-to-end — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fase 1 van spec [`2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md): de drie The Key-recipes (THK-08 verhuizen, THK-24 bouwen/renoveren, THK-02 kind gekregen) landen als echte nldt-recipes met function-baselines en EDIC-adoptie, draaibaar via twee nieuwe replay-processen, met de The Key-demo (NL/EN) en het menu-skelet in de Mistral-stijl.

**Architecture:** Schema-uitbreiding (`service`-blok) → run/baseline-contracten → fixtures (één bron van waarheid) → twee deterministische processen in de PoC-handler → recipe-JSON's → generator `build_runs.py` die runs én de single-file demopagina's vult (patroon `regelrecht/`). Geen LLM, geen netwerk; alles draait op `file://`.

**Tech Stack:** Python 3 (`nldt/.venv`: stdlib + `jsonschema`), JSON Schema draft 2020-12, plain HTML/CSS/JS (huisstijl `nldt/simulation`), pytest.

**Spec:** [`docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md) (v1.1, goedgekeurd) — fase 1; fase 2 (city dishes) krijgt een eigen plan na oplevering van fase 1.

## Global Constraints

- Python altijd met `nldt/.venv/bin/python` (daar staat `jsonschema`); tests vanaf de repo-root: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v` (conftest `nldt/conftest.py` lost de imports).
- Alle JSON-schema's: `$schema` draft 2020-12, `additionalProperties: false`; schema-uitbreiding is **additief** — de 22 bestaande recipes blijven ongewijzigd geldig.
- Demo's: single-file HTML, werkt vanaf `file://`, **geen** `fetch`, **geen** externe assets behalve de bestaande Google Fonts (graceful fallback); UI in het Nederlands (EN-tweeling voor de The Key-demo via gegenereerd tweede bestand).
- Palet exact zoals de bestuurdersdemo: `:root` met `--papier:#f6f8fb; --inkt:#06121b; --inkt-2:#0d1e2c; --ijs:#dff3ff; --ijs-rand:#c4d0da; --blauw:#2ba8ff; --hemel:#79c9ff; --oranje:#ff9815; --oranje-donker:#ef8700; --amber:#ffc37e; --rood:#e10500; --mint:#1cefa5; --groen:#0f7a4d` (donker `--inkt` achtergrond, lichte tekst, oranje accent — statuskleuren mint/groen/rood intact).
- Deterministisch: geen LLM, geen netwerk; dezelfde `--stamp` levert byte-identieke runs en pagina's.
- KPI-waarden komen **letterlijk** uit `recipes/05_KPI-framework_per-recipe.xlsx` (sheet *KPI framework* en *The Key × PDC*); de map `recipes/` is alleen-lezen.
- THK-24: de koppeling met `minigim-gebiedscheck` is in fase 1 **declaratief** (`requiredProcesses` + fixture-verwijzing naar de canonieke minigim-run); geen live minigim-run in de demo (netwerkvrij).
- Commit-stijl conform repo-historie: `feat(nldt): …`, `test(nldt): …`, `docs(nldt): …` in het Nederlands. Alleen eigen taakbestanden committen.
- De untracked map `recipes/` (bron-documenten) **nooit** committen.

---

### Task 1: `service`-blok in `recipe.schema.json`

**Files:**
- Modify: `nldt/schemas/recipe.schema.json` (top-level `properties` + `$defs`)
- Test: `nldt/tests/test_hcs.py` (nieuw)

**Interfaces:**
- Produces: optioneel top-level property `service` (EDIC-anatomy). Later taken vullen het bij THK-02/08/24. Bestaande recipes valideren ongewijzigd.
- Schema-detectie voor latere taken: `validate_instance(recipe, "recipe.schema.json")` accepteert `service` alleen met exact de velden hieronder.

- [ ] **Step 1: Schrijf de falende test**

Maak `nldt/tests/test_hcs.py` aan:

```python
"""Tests voor de HCS-recipes (spec 2026-10-09-hcs-recipes-pocs-design, fase 1)."""
import json
from pathlib import Path

import pytest

from services.common.schema import load_recipe, validate_instance

NLDT_ROOT = Path(__file__).resolve().parents[1]
HCS_ROOT = NLDT_ROOT / "simulation" / "hcs"

SERVICE_MIN = {
    "dish": "the-key",
    "serviceType": "reactive",
}


def test_service_block_accepted():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe met service-blok",
        "version": "1.0.0",
        "inputs": {},
        "outputs": {},
        "steps": [
            {"id": "s1", "processId": "hcs-life-event-run", "inputs": {}}
        ],
        "riskLevel": "low",
        "service": dict(
            SERVICE_MIN,
            lifeEventCode="THK-08",
            blueprintSteps=[1, 2, 3, 4, 5],
            parties=[{"name": "Gemeente Zoetermeer", "role": "lead"}],
            legalBasis=[{"basis": "Wet BRP", "timeLimit": "redelijke termijn (Awb)"}],
            humanMeasure={"handover": ["adresonderzoek bij twijfel → medewerker"], "exceptions": []},
            localVariant="gemeentelijk parkeerbeleid",
            genAiTestPoints=[{"point": "G1", "description": "intake-assistent", "testCases": ["laaggeletterde persona"]}],
            kpis=[{
                "kpi": "Moves processed without manual handling",
                "kpiType": "outcome", "unit": "%", "outcomeLens": "Z",
                "baseline": "", "target": "", "dataSource": "case system",
                "frequency": "monthly", "kviRollup": "KVI 5 (Digital)",
            }],
        ),
    }
    validate_instance(recipe, "recipe.schema.json")


def test_service_block_rejects_unknown_field_and_bad_point():
    recipe = {
        "id": "probe-hcs",
        "title": "Schema-probe onbekend veld",
        "version": "1.0.0",
        "inputs": {}, "outputs": {},
        "steps": [{"id": "s1", "processId": "x", "inputs": {}}],
        "riskLevel": "low",
        "service": {"dish": "the-key", "serviceType": "reactive", "onbekend": True},
    }
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")

    recipe["service"] = {"dish": "the-key", "serviceType": "reactive",
                         "genAiTestPoints": [{"point": "G9", "description": "bestaat niet"}]}
    with pytest.raises(Exception):
        validate_instance(recipe, "recipe.schema.json")
```

- [ ] **Step 2: Draai de test — moet falen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: FAIL — `Additional properties are not allowed ('service' was unexpected)` (het blok bestaat nog niet).

- [ ] **Step 3: Schema uitbreiden**

In `nldt/schemas/recipe.schema.json`, voeg toe aan `properties` (na `"riskLevel"`, vóór `"cookbookUri"`):

```json
    "service": { "$ref": "#/$defs/serviceBlock" }
```

En voeg in `$defs` deze vijf definities toe:

```json
    "serviceBlock": {
      "type": "object",
      "additionalProperties": false,
      "required": ["dish", "serviceType"],
      "properties": {
        "dish": { "enum": ["the-key", "urban-air-mobility", "3-30-300", "circular-neighborhoods", "15-minute-city"] },
        "lifeEventCode": { "type": "string", "pattern": "^(THK|UAM|GRN|CIR|MIN)-[0-9]{2}$" },
        "serviceType": { "enum": ["reactive", "proactive", "measure", "plan", "share", "system", "infrastructure"] },
        "blueprintSteps": { "type": "array", "minItems": 1, "items": { "type": "integer", "minimum": 1, "maximum": 5 } },
        "parties": { "type": "array", "items": { "$ref": "#/$defs/serviceParty" } },
        "legalBasis": { "type": "array", "items": { "$ref": "#/$defs/legalBasisEntry" } },
        "humanMeasure": {
          "type": "object",
          "additionalProperties": false,
          "required": ["handover", "exceptions"],
          "properties": {
            "handover": { "type": "array", "items": { "type": "string" } },
            "exceptions": { "type": "array", "items": { "type": "string" } }
          }
        },
        "localVariant": { "type": "string" },
        "genAiTestPoints": { "type": "array", "items": { "$ref": "#/$defs/genAiTestPoint" } },
        "kpis": { "type": "array", "items": { "$ref": "#/$defs/serviceKpi" } }
      }
    },
    "serviceParty": {
      "type": "object", "additionalProperties": false, "required": ["name", "role"],
      "properties": { "name": { "type": "string" }, "role": { "type": "string" } }
    },
    "legalBasisEntry": {
      "type": "object", "additionalProperties": false, "required": ["basis"],
      "properties": { "basis": { "type": "string" }, "timeLimit": { "type": "string" } }
    },
    "genAiTestPoint": {
      "type": "object", "additionalProperties": false, "required": ["point", "description"],
      "properties": {
        "point": { "enum": ["G1", "G2", "G3", "G4", "G5"] },
        "description": { "type": "string" },
        "testCases": { "type": "array", "items": { "type": "string" } }
      }
    },
    "serviceKpi": {
      "type": "object", "additionalProperties": false,
      "required": ["kpi", "kpiType", "unit", "outcomeLens"],
      "properties": {
        "kpi": { "type": "string" },
        "kpiType": { "enum": ["output", "outcome"] },
        "unit": { "type": "string" },
        "outcomeLens": { "enum": ["Z", "L", "W", "—"] },
        "baseline": { "type": "string" },
        "target": { "type": "string" },
        "dataSource": { "type": "string" },
        "frequency": { "type": "string" },
        "kviRollup": { "type": "string" }
      }
    }
```

- [ ] **Step 4: Draai de test — moet slagen; en de regressie**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py nldt/tests/test_nldt_core.py -v`
Expected: PASS (inclusief `test_poc_recipes_schema_valid` — bestaande recipes ongewijzigd geldig).

- [ ] **Step 5: Commit**

```bash
git add nldt/schemas/recipe.schema.json nldt/tests/test_hcs.py
git commit -m "feat(nldt): recipe-schema — optioneel EDIC service-blok (dish, serviceType, menselijke maat, G-testpunten, KPI's)"
```

---

### Task 2: Run-contract `hcs-run.schema.json` + baseline-contract `hcs-baseline.schema.json`

**Files:**
- Create: `nldt/schemas/hcs-run.schema.json`
- Create: `nldt/schemas/hcs-baseline.schema.json`
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Produces: `hcs-run.schema.json` — verplicht: `schemaVersion("1.0"), runId, generatedAt, recipeId, processId("hcs-life-event-run"|"hcs-recipe-run"), mode("replay"|"execute"), scenario, steps[], stopConditions[], kpiSnapshot[]`, optioneel `learningState[]`. `runStep` verplicht: `stepId, title, actor("agent"|"mens"|"partij"), genAiTestPoint("G1".."G5"|"—"), dataUsed[], consent("n.v.t."|"gevraagd"|"gegeven"|"geweigerd"), handover(null|{reason,to}), kpiEvents[], prov{sources[]}`.
- Produces: `hcs-baseline.schema.json` — verplicht: `recipeId, publicOutcome, disappearingStep, kpis[], stopConditions[], goNoGo[]`.
- Consumers: Task 4 (processen valideren hun output), Task 6 (generator valideert runs), Task 7 (demo leest runs).

- [ ] **Step 1: Schrijf de falende tests**

Voeg aan `nldt/tests/test_hcs.py` toe:

```python
RUN_MIN = {
    "schemaVersion": "1.0",
    "runId": "thk-08-move-home-sanne-20261009T000000Z",
    "generatedAt": "2026-10-09T00:00:00Z",
    "recipeId": "thk-08-move-home",
    "processId": "hcs-life-event-run",
    "mode": "replay",
    "scenario": "sanne",
    "steps": [{
        "stepId": "intake", "title": "Life event & intake", "actor": "agent",
        "genAiTestPoint": "G1", "dataUsed": ["BRP (Haal Centraal)"],
        "consent": "n.v.t.", "handover": None, "kpiEvents": [],
        "prov": {"sources": ["BRP (Haal Centraal)"]},
    }],
    "stopConditions": [{"id": "sc-1", "condition": "mens-overnames > 20%", "action": "pauzeer"}],
    "kpiSnapshot": [{"kpi": "Moves processed without manual handling", "baseline": "", "target": ""}],
}


def test_hcs_run_schema():
    validate_instance(RUN_MIN, "hcs-run.schema.json")
    bad = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], actor="robot")])
    with pytest.raises(Exception):
        validate_instance(bad, "hcs-run.schema.json")
    bad2 = dict(RUN_MIN, steps=[dict(RUN_MIN["steps"][0], handover={"reden": "x"})])
    with pytest.raises(Exception):
        validate_instance(bad2, "hcs-run.schema.json")  # handover vereist reason+to


def test_hcs_baseline_schema():
    baseline = {
        "recipeId": "thk-08-move-home",
        "publicOutcome": "verhuizen is één gesorteerde reis",
        "disappearingStep": "herhaalde loketbezoeken",
        "kpis": [{"kpi": "Moves processed without manual handling", "kpiType": "outcome",
                  "unit": "%", "outcomeLens": "Z"}],
        "stopConditions": [{"condition": "c", "action": "a"}],
        "goNoGo": ["accuracy ≥ 95% op testbank-personas"],
    }
    validate_instance(baseline, "hcs-baseline.schema.json")
    with pytest.raises(Exception):
        validate_instance(dict(baseline, kpis=[{"kpi": "x"}]), "hcs-baseline.schema.json")
```

- [ ] **Step 2: Draai — moet falen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: FAIL — `Schema not found: hcs-run.schema.json`.

- [ ] **Step 3: Schema's aanmaken**

`nldt/schemas/hcs-run.schema.json` — volledige inhoud:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.example/nldt/schemas/hcs-run.schema.json",
  "title": "HCS run (life event of city recipe)",
  "description": "Run-artefact van hcs-life-event-run / hcs-recipe-run: de stappen met mens-agent-grens, GenAI-testpunt, bronherkomst en stopcondities (spec 2026-10-09-hcs-recipes-pocs-design).",
  "type": "object",
  "additionalProperties": false,
  "required": ["schemaVersion", "runId", "generatedAt", "recipeId", "processId", "mode", "scenario", "steps", "stopConditions", "kpiSnapshot"],
  "properties": {
    "schemaVersion": { "const": "1.0" },
    "runId": { "type": "string" },
    "generatedAt": { "type": "string" },
    "recipeId": { "type": "string" },
    "processId": { "enum": ["hcs-life-event-run", "hcs-recipe-run"] },
    "mode": { "enum": ["replay", "execute"] },
    "scenario": { "type": "string", "description": "persona-id (life events) of scenario-id (city recipes)" },
    "steps": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/runStep" } },
    "stopConditions": { "type": "array", "items": { "$ref": "#/$defs/stopCondition" } },
    "kpiSnapshot": { "type": "array", "items": { "$ref": "#/$defs/kpiSnapshotEntry" } },
    "learningState": { "type": "array", "items": { "$ref": "#/$defs/learningEntry" } }
  },
  "$defs": {
    "runStep": {
      "type": "object",
      "additionalProperties": false,
      "required": ["stepId", "title", "actor", "genAiTestPoint", "dataUsed", "consent", "handover", "kpiEvents", "prov"],
      "properties": {
        "stepId": { "type": "string" },
        "title": { "type": "string" },
        "actor": { "enum": ["agent", "mens", "partij"] },
        "genAiTestPoint": { "enum": ["G1", "G2", "G3", "G4", "G5", "—"] },
        "dataUsed": { "type": "array", "items": { "type": "string" } },
        "consent": { "enum": ["n.v.t.", "gevraagd", "gegeven", "geweigerd"] },
        "handover": {
          "oneOf": [
            { "type": "null" },
            {
              "type": "object", "additionalProperties": false, "required": ["reason", "to"],
              "properties": { "reason": { "type": "string" }, "to": { "type": "string" } }
            }
          ]
        },
        "kpiEvents": {
          "type": "array",
          "items": {
            "type": "object", "additionalProperties": false, "required": ["kpi", "effect"],
            "properties": { "kpi": { "type": "string" }, "effect": { "type": "string" } }
          }
        },
        "prov": {
          "type": "object", "additionalProperties": false, "required": ["sources"],
          "properties": { "sources": { "type": "array", "items": { "type": "string" } } }
        }
      }
    },
    "stopCondition": {
      "type": "object", "additionalProperties": false, "required": ["id", "condition", "action"],
      "properties": { "id": { "type": "string" }, "condition": { "type": "string" }, "action": { "type": "string" } }
    },
    "kpiSnapshotEntry": {
      "type": "object", "additionalProperties": false, "required": ["kpi", "baseline", "target"],
      "properties": { "kpi": { "type": "string" }, "baseline": { "type": "string" }, "target": { "type": "string" }, "actual": { "type": "string" } }
    },
    "learningEntry": {
      "type": "object", "additionalProperties": false, "required": ["signal", "why", "change", "decidesBy"],
      "properties": {
        "signal": { "type": "string" }, "why": { "type": "string" }, "change": { "type": "string" },
        "decidesBy": { "type": "string" }, "helped": { "type": ["boolean", "null"] }
      }
    }
  }
}
```

`nldt/schemas/hcs-baseline.schema.json` — volledige inhoud:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.example/nldt/schemas/hcs-baseline.schema.json",
  "title": "HCS function baseline (Sitra-poort 1 + 5)",
  "description": "Baseline vóór technologie: publieke uitkomst, verdwijnende stap, KPI's uit het KPI-framework, stopcondities en go/no-go (docs/AGENTIC_STATE_PLAN.md §3).",
  "type": "object",
  "additionalProperties": false,
  "required": ["recipeId", "publicOutcome", "disappearingStep", "kpis", "stopConditions", "goNoGo"],
  "properties": {
    "recipeId": { "type": "string" },
    "publicOutcome": { "type": "string" },
    "disappearingStep": { "type": "string" },
    "kpis": { "type": "array", "items": { "$ref": "#/$defs/baselineKpi" } },
    "stopConditions": { "type": "array", "items": { "$ref": "#/$defs/stopConditionLite" } },
    "goNoGo": { "type": "array", "items": { "type": "string" } }
  },
  "$defs": {
    "baselineKpi": {
      "type": "object", "additionalProperties": false,
      "required": ["kpi", "kpiType", "unit", "outcomeLens"],
      "properties": {
        "kpi": { "type": "string" },
        "kpiType": { "enum": ["output", "outcome"] },
        "unit": { "type": "string" },
        "outcomeLens": { "enum": ["Z", "L", "W", "—"] },
        "baseline": { "type": "string" },
        "target": { "type": "string" },
        "dataSource": { "type": "string" },
        "frequency": { "type": "string" },
        "kviRollup": { "type": "string" }
      }
    },
    "stopConditionLite": {
      "type": "object", "additionalProperties": false, "required": ["condition", "action"],
      "properties": { "condition": { "type": "string" }, "action": { "type": "string" } }
    }
  }
}
```

- [ ] **Step 4: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add nldt/schemas/hcs-run.schema.json nldt/schemas/hcs-baseline.schema.json nldt/tests/test_hcs.py
git commit -m "feat(nldt): HCS-contracten — run-artefact (mens-agent-grens per stap) en function-baseline (poort 1+5)"
```

---

### Task 3: Fixtures — gedeeld model + drie life-event-scenario's

**Files:**
- Create: `nldt/simulation/hcs/fixtures/common.json`
- Create: `nldt/simulation/hcs/fixtures/life-events/thk-08-move-home.json`
- Create: `nldt/simulation/hcs/fixtures/life-events/thk-02-having-a-baby.json`
- Create: `nldt/simulation/hcs/fixtures/life-events/thk-24-build-renovate.json`
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Fixture-shape (consumed door Task 4 en Task 6):

```json
{
  "recipeId": "<id>",
  "scenarioKind": "life-event",
  "personas": [{"id": "sanne", "label": "…", "edge": null}],
  "steps": [{
    "stepId": "intake", "title": "Life event & intake", "blueprintStep": 1,
    "defaults": {"actor": "agent", "genAiTestPoint": "G1", "dataUsed": [], "consent": "n.v.t.",
                  "kpiEvents": [], "prov": {"sources": []}},
    "perPersona": {"<persona-id>": {"handover": {"reason": "…", "to": "…"}}}
  }],
  "stopConditions": [{"id": "sc-1", "condition": "…", "action": "…"}],
  "kpiSnapshot": [{"kpi": "…", "baseline": "", "target": ""}],
  "learningState": [{"signal": "…", "why": "…", "change": "…", "decidesBy": "…"}]
}
```

Overrides in `perPersona` mogen elk veld van een stap vervangen (`actor`, `handover`, `dataUsed`, `consent`, `kpiEvents`, `genAiTestPoint`); de executor merge-overridet op veldniveau (`handover` vervangt geheel).

- [ ] **Step 1: Schrijf de falende test**

```python
LIFE_FIXTURES = HCS_ROOT / "fixtures" / "life-events"
EXPECTED_LIFE = {"thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate"}


def test_life_event_fixtures_present_and_consistent():
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text())
    assert set(common["parties"].keys()) >= {"gemeente", "energie", "bank", "verzekeraar", "zorgverzekeraar"}
    found = {p.stem for p in LIFE_FIXTURES.glob("*.json")}
    assert found == EXPECTED_LIFE
    for path in LIFE_FIXTURES.glob("*.json"):
        fx = json.loads(path.read_text())
        persona_ids = {p["id"] for p in fx["personas"]}
        assert len(persona_ids) >= 2
        assert len(fx["steps"]) == 5  # de vijf blueprint-stappen
        for step in fx["steps"]:
            for pid in step.get("perPersona", {}):
                assert pid in persona_ids, f"onbekende persona {pid} in {path.name}"
        assert fx["stopConditions"], "poort 5: stopcondities verplicht"
        assert fx["kpiSnapshot"], "poort 1: KPI-snapshot verplicht"
```

- [ ] **Step 2: Draai — moet falen** (fixtures bestaan niet)

- [ ] **Step 3: Fixtures schrijven**

`nldt/simulation/hcs/fixtures/common.json` — volledige inhoud:

```json
{
  "parties": {
    "gemeente": "Gemeente Zoetermeer (Burgerzaken — lead, PDC-vraag 8 + 6)",
    "energie": "Energie- en netbeheerder",
    "bank": "Bank",
    "verzekeraar": "Verzekeraar",
    "zorgverzekeraar": "Zorgverzekeraar",
    "svb": "SVB (kinderbijslag)",
    "belastingdienst": "Belastingdienst (toeslagen)",
    "omgevingsloket": "Omgevingsloket (vergunningcheck, THK-24)",
    "minigim": "MiniGIM gebiedscheck (canonieke run, ingredient van THK-24)"
  },
  "attestations": {
    "woonadres": "EUDI-attestatie woonadres (bron: BRP)",
    "burgerlijkeStaat": "EUDI-attestatie burgerlijke staat (bron: BRP)",
    "geboorte": "EUDI-attestatie geboorte (bron: BRP)"
  },
  "myServices": ["MijnGegevens", "MijnZaken", "MijnActies", "Notificatieservice", "MijnProducten", "MijnAgenda", "MijnTaken"],
  "commonGround": ["Haal Centraal BRP", "EUDI attestations", "Zaken API", "Notificaties API", "Open Producten / PDC (SDG)"],
  "testbank": ["accuracy", "plain language", "once-only", "explainability", "human handover", "bias", "AI Act risk class"],
  "leerstaatAssen": ["wat gebeurde", "waarom", "wat moet veranderen", "wie beslist", "hielp het"]
}
```

`nldt/simulation/hcs/fixtures/life-events/thk-08-move-home.json` — volledige inhoud (bron: sheet *The Key × PDC*, rijen THK-08: PDC-vraag 8 "Ik ga verhuizen" + vraag 6 "Ik wil parkeren"; human measure "Adresonderzoek bij twijfel → medewerker"; G1 · G4):

```json
{
  "recipeId": "thk-08-move-home",
  "scenarioKind": "life-event",
  "personas": [
    {"id": "sanne", "label": "Sanne de Vries — verhuist binnen Zoetermeer", "edge": null},
    {"id": "ahmed", "label": "Ahmed Yilmaz — lage Nederlandse geletterdheid", "edge": "lage-geletterdheid"},
    {"id": "maria", "label": "Maria Okafor — voorkeur voor een andere taal", "edge": "andere-taal"},
    {"id": "jeroen", "label": "Jeroen van Dam — schulden, staat onder bewindsvoering", "edge": "schulden"}
  ],
  "steps": [
    {
      "stepId": "intake", "title": "Life event & intake", "blueprintStep": 1,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G1",
        "dataUsed": ["BRP (Haal Centraal): naam, BSN, huidig adres", "MijnGegevens"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Moves processed without manual handling", "effect": "geen formulier nodig — alleen verhuisdatum gevraagd"}],
        "prov": {"sources": ["BRP (Haal Centraal)", "The Key × PDC: alleen vragen wat niet in de BRP staat"]}
      },
      "perPersona": {
        "ahmed": {"handover": {"reason": "Twijfel over het adres (adresonderzoek nodig)", "to": "medewerker Burgerzaken"}},
        "maria": {"dataUsed": ["BRP (Haal Centraal): naam, BSN, huidig adres", "MijnGegevens", "taalvoorkeur NL/TR/EN uit profiel"]}
      }
    },
    {
      "stepId": "solution", "title": "Solution — één samenhangend voorstel", "blueprintStep": 2,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": ["Open Producten / PDC (SDG): parkeervergunning, afvalpas, school, energie, bank"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Moves processed without manual handling", "effect": "één voorstel in plaats van vijf loketten"}],
        "prov": {"sources": ["Open Producten / PDC (SDG)"]}
      },
      "perPersona": {
        "maria": {"dataUsed": ["Open Producten / PDC (SDG): parkeervergunning, afvalpas, school, energie, bank", "uitleg in voorkeurstaal"]}
      }
    },
    {
      "stepId": "contract", "title": "Contract & consent — wie ziet wat", "blueprintStep": 3,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G3",
        "dataUsed": ["MijnZaken", "Autorisaties API"],
        "consent": "gevraagd",
        "kpiEvents": [{"kpi": "Moves processed without manual handling", "effect": "één toestemming per partij per periode"}],
        "prov": {"sources": ["Autorisaties API"]}
      },
      "perPersona": {
        "jeroen": {"dataUsed": ["MijnZaken", "Autorisaties API", "bewindsvoerderschap geverifieerd"], "consent": "gegeven"}
      }
    },
    {
      "stepId": "delivery", "title": "Payment & delivery — parallel per partij", "blueprintStep": 4,
      "defaults": {
        "actor": "partij", "genAiTestPoint": "G4",
        "dataUsed": ["Zaken API", "Notificaties API", "EUDI-attestatie woonadres in de wallet"],
        "consent": "gegeven",
        "kpiEvents": [{"kpi": "Moves processed without manual handling", "effect": "gemeente, energie, bank, verzekeraar, zorgverzekeraar parallel afgehandeld"}],
        "prov": {"sources": ["Zaken API", "Notificaties API", "BRP (Haal Centraal)"]}
      },
      "perPersona": {
        "ahmed": {"actor": "mens", "dataUsed": ["Zaken API", "Notificaties API", "adresonderzoek door medewerker"], "handover": {"reason": "adresonderzoek loopt bij de medewerker", "to": "medewerker Burgerzaken"}}
      }
    },
    {
      "stepId": "followup", "title": "Follow-up & value — proactief", "blueprintStep": 5,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G5",
        "dataUsed": ["Notificatieservice", "MijnActies"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Moves processed without manual handling", "effect": "proactief: 'je hebt ook recht op…' zonder nieuwe aanvraag"}],
        "prov": {"sources": ["Notificatieservice"]}
      },
      "perPersona": {
        "jeroen": {"handover": {"reason": "signaal schulden + nieuwe woonlasten", "to": "wijkteam sociaal domein (THK-14)"}}
      }
    }
  ],
  "stopConditions": [
    {"id": "sc-thk08-1", "condition": "mens-overnames bij intake > 20% over vier weken", "action": "pauzeer intake-assistent (G1) — escalatie naar function steward"},
    {"id": "sc-thk08-2", "condition": "geen unanimous go op testbank-assen (accuracy, plain language, once-only)", "action": "geen go — terug naar design (recipe-cyclus stap 1)"},
    {"id": "sc-thk08-3", "condition": "AI Act risk class wijzigt naar high-risk", "action": "stop en her-toets mens-agent-grens (poort 3)"}
  ],
  "kpiSnapshot": [
    {"kpi": "Moves processed without manual handling", "baseline": "", "target": ""}
  ],
  "learningState": [
    {"signal": "adresonderzoeken concentreren zich op één wijk", "why": "vermoedelijk verouderde BRP-mutaties in dat deelgebied", "change": "bronhouder BRP-vragen over mutatiekwaliteit; recipe-local variant bijstellen", "decidesBy": "function steward + Burgerzaken", "helped": null}
  ]
}
```

`nldt/simulation/hcs/fixtures/life-events/thk-02-having-a-baby.json` — volledige inhoud (bron: rijen THK-02: melding binnen 5 dagen; SVB, Belastingdienst, zorgverzekeraar; G2 · G5; mensmaat "Complexe situaties (erkenning, buitenlandse ouder) → medewerker"):

```json
{
  "recipeId": "thk-02-having-a-baby",
  "scenarioKind": "life-event",
  "personas": [
    {"id": "lot", "label": "Lot & Sam — eerste kind, alles regelen vóór de geboorte", "edge": null},
    {"id": "fatima", "label": "Fatima — erkenning en buitenlandse ouder", "edge": "erkenning-buitenlandse-ouder"}
  ],
  "steps": [
    {
      "stepId": "intake", "title": "Life event & intake — zwangerschap aangegeven", "blueprintStep": 1,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": ["MijnActies: zwangerschapsverlof, kraamzorg", "BRP (Haal Centraal)"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Birth registrations done digitally", "effect": "proactief traject gestart vóór de geboorte"}],
        "prov": {"sources": ["BRP (Haal Centraal)"]}
      },
      "perPersona": {
        "fatima": {"handover": {"reason": "erkenning en buitenlandse ouder — complexe situatie", "to": "medewerker Burgerzaken"}}
      }
    },
    {
      "stepId": "solution", "title": "Solution — verlof, kraamzorg, kinderegelingen", "blueprintStep": 2,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": ["Open Producten / PDC (SDG): geboorteaangifte, kinderbijslag, toeslagen"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Birth registrations done digitally", "effect": "één voorstel: verlof, kraamzorg, SVB, toeslagen"}],
        "prov": {"sources": ["Open Producten / PDC (SDG)"]}
      },
      "perPersona": {}
    },
    {
      "stepId": "contract", "title": "Contract & consent — ketenpartijen", "blueprintStep": 3,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G3",
        "dataUsed": ["Autorisaties API: SVB, Belastingdienst, zorgverzekeraar"],
        "consent": "gevraagd",
        "kpiEvents": [{"kpi": "Birth registrations done digitally", "effect": "toestemming per ketenpartij"]},
        "prov": {"sources": ["Autorisaties API"]}
      },
      "perPersona": {}
    },
    {
      "stepId": "delivery", "title": "Payment & delivery — geboorteaangifte binnen 5 dagen", "blueprintStep": 4,
      "defaults": {
        "actor": "partij", "genAiTestPoint": "G4",
        "dataUsed": ["Zaken API", "EUDI-attestatie geboorte in de wallet"],
        "consent": "gegeven",
        "kpiEvents": [{"kpi": "Birth registrations done digitally", "effect": "melding binnen 5 dagen digitaal afgehandeld"}],
        "prov": {"sources": ["Zaken API", "Wet BRP (melding binnen 5 dagen*)"]}
      },
      "perPersona": {
        "fatima": {"actor": "mens", "handover": {"reason": "erkenning vastgesteld door ambtenaar", "to": "medewerker Burgerzaken"}}
      }
    },
    {
      "stepId": "followup", "title": "Follow-up & value — proactief signaleren", "blueprintStep": 5,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G5",
        "dataUsed": ["Notificatieservice: kinderbijslag, toeslagen, zorgverzekering kind"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Birth registrations done digitally", "effect": "SVB en toeslagen proactief aangeboden"}],
        "prov": {"sources": ["Notificatieservice"]}
      },
      "perPersona": {}
    }
  ],
  "stopConditions": [
    {"id": "sc-thk02-1", "condition": "digitale geboorteregistratie < 80% over een maand", "action": "onderzoek naar afhaalmoment; terug naar design"},
    {"id": "sc-thk02-2", "condition": "proactieve signalen leiden tot klachten over ongevraagde contacten", "action": "proactief-paar af (G5), menselijke tussenstap inbouwen"}
  ],
  "kpiSnapshot": [
    {"kpi": "Birth registrations done digitally", "baseline": "", "target": ""}
  ],
  "learningState": [
    {"signal": "ouders starten eerder dan verwacht (tweede trimester)", "why": "verlof- en kraamzorgvragen komen vroeg", "change": "proactieve start verschuiven naar week 24", "decidesBy": "function steward + Sociaal Domein", "helped": null}
  ]
}
```

`nldt/simulation/hcs/fixtures/life-events/thk-24-build-renovate.json` — volledige inhoud (bron: rijen THK-24 "I want to build or renovate": Plan → permit check (Omgevingsloket) → application → assessment; KPI "Decision within 8 weeks (regular)"; G-punten zijn het goedgekeurde voorstel uit spec §1; declaratieve ingredient-koppeling naar de canonieke minigim-run):

```json
{
  "recipeId": "thk-24-build-renovate",
  "scenarioKind": "life-event",
  "personas": [
    {"id": "noor", "label": "Noor Bakker — dakkapel, reguliere procedure", "edge": null},
    {"id": "peter", "label": "Peter Smit — aanbouw in een beschermd gezicht", "edge": "beschermd-gezicht"}
  ],
  "steps": [
    {
      "stepId": "intake", "title": "Life event & intake — bouwplan in eigen woorden", "blueprintStep": 1,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G1",
        "dataUsed": ["BRP (Haal Centraal): adres, eigendom", "MijnGegevens"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Decision within 8 weeks (regular)", "effect": "plan klopt bij intake — geen verkeerde aanvraag"}],
        "prov": {"sources": ["BRP (Haal Centraal)"]}
      },
      "perPersona": {
        "peter": {"dataUsed": ["BRP (Haal Centraal): adres, eigendom", "RCE: beschermd gezicht — vlag vooraf"]}
      }
    },
    {
      "stepId": "solution", "title": "Solution — vergunningcheck via het Omgevingsloket", "blueprintStep": 2,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G2",
        "dataUsed": ["Omgevingsloket-vergunningcheck", "canonieke MiniGIM-gebiedscheck (ingredient, replay)"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Decision within 8 weeks (regular)", "effect": "check vooraf voorspelt vergunningsvrij of procedure"}],
        "prov": {"sources": ["Omgevingsloket (SDG)", "nldt/recipes/minigim-gebiedscheck.json (ingredient)"]}
      },
      "perPersona": {
        "peter": {"handover": {"reason": "beschermd gezicht — uitgebreide procedure (26 weken)", "to": "vergunningverlener Fysiek Domein"}}
      }
    },
    {
      "stepId": "contract", "title": "Contract & consent — aanvraag met brondocumenten", "blueprintStep": 3,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G3",
        "dataUsed": ["Zaken API", "Documenten API", "EUDI-attestatie woonadres"],
        "consent": "gevraagd",
        "kpiEvents": [{"kpi": "Decision within 8 weeks (regular)", "effect": "complete aanvraag bij eerste inzending"}],
        "prov": {"sources": ["Zaken API", "Documenten API"]}
      },
      "perPersona": {}
    },
    {
      "stepId": "delivery", "title": "Payment & delivery — beoordeling door de mens", "blueprintStep": 4,
      "defaults": {
        "actor": "mens", "genAiTestPoint": "—",
        "dataUsed": ["Zaken API: dossier", "V4-menselijke beoordeling (doctrine: AI stelt voor · mens beslist)"],
        "consent": "gegeven",
        "kpiEvents": [{"kpi": "Decision within 8 weeks (regular)", "effect": "besluit binnen 8 weken in de reguliere procedure"}],
        "prov": {"sources": ["Omgevingswet (besluittermijn 8 weken regulier)"]}
      },
      "perPersona": {}
    },
    {
      "stepId": "followup", "title": "Follow-up & value — bouw- en woonstappen", "blueprintStep": 5,
      "defaults": {
        "actor": "agent", "genAiTestPoint": "G5",
        "dataUsed": ["Notificatieservice: besluit, bouwtoezicht-momenten, WOZ bij nieuwe woningwaarde"],
        "consent": "n.v.t.",
        "kpiEvents": [{"kpi": "Decision within 8 weeks (regular)", "effect": "proactief: bouwtoezicht- en vervolgstappen aangeboden"}],
        "prov": {"sources": ["Notificatieservice"]}
      },
      "perPersona": {}
    }
  ],
  "stopConditions": [
    {"id": "sc-thk24-1", "condition": "vergunningcheck wijkt af van de beoordeling in > 10% van de reguliere zaken", "action": "check-model bijstellen; geen auto-aanbevelingen meer (G2)"},
    {"id": "sc-thk24-2", "condition": "besluiten niet binnen 8 weken", "action": "baseline-analyse proces, geen agent-inzet als verklaring accepteren"}
  ],
  "kpiSnapshot": [
    {"kpi": "Decision within 8 weeks (regular)", "baseline": "", "target": ""}
  ],
  "learningState": [
    {"signal": "checks op dakkapellen scoren beter dan op aanbouwen", "why": "aanbouw raakt vaker aan plekgebonden regels", "change": "G2-voorspelbaarheid per productsoort publiceren in de recipe", "decidesBy": "function steward + Vergunningen", "helped": null}
  ]
}
```

- [ ] **Step 4: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/hcs/fixtures nldt/tests/test_hcs.py
git commit -m "feat(nldt): HCS-fixtures — drie The Key-life-events met persona's, mens-agent-grens en stopcondities"
```

---

### Task 4: Processen `hcs-life-event-run` en `hcs-recipe-run`

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py`
- Modify: `nldt/tests/test_poc_processes.py` (expected-set uitbreiden)
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Produces: processen `hcs-life-event-run` (inputs `recipeId, persona, mode`; output `run`) en `hcs-recipe-run` (inputs `recipeId, scenario, mode`; output `run`) in `POC_PROCESS_DEFINITIONS` — dus automatisch in `PROCESS_DEFINITIONS`, `list_processes()`, OGC API Processes en `run-recipe`.
- Executor-contract: `execute_hcs_life_event_run(inputs) -> {"run": dict}`; `execute_hcs_recipe_run(inputs, *, fixture_dir=None) -> {"run": dict}` (kwarg alleen voor tests; dispatch roept zonder kwarg).

- [ ] **Step 1: Schrijf de falende tests**

Voeg aan `nldt/tests/test_hcs.py` toe:

```python
from services.process_adapter.handlers import describe_process, execute_local


def test_hcs_processes_registered():
    for pid in ("hcs-life-event-run", "hcs-recipe-run"):
        assert describe_process(pid)["id"] == pid


def test_life_event_run_replay_sanne():
    out = execute_local("hcs-life-event-run",
                        {"recipeId": "thk-08-move-home", "persona": "sanne", "mode": "replay"})
    run = out["run"]
    validate_instance(run, "hcs-run.schema.json")
    assert run["scenario"] == "sanne"
    assert [s["stepId"] for s in run["steps"]] == ["intake", "solution", "contract", "delivery", "followup"]
    assert all(s["handover"] is None for s in run["steps"])
    assert run["steps"][0]["genAiTestPoint"] == "G1"


def test_life_event_run_edge_cases():
    ahmed = execute_local("hcs-life-event-run",
                          {"recipeId": "thk-08-move-home", "persona": "ahmed", "mode": "replay"})["run"]
    intake = next(s for s in ahmed["steps"] if s["stepId"] == "intake")
    assert intake["handover"] == {"reason": "Twijfel over het adres (adresonderzoek nodig)",
                                  "to": "medewerker Burgerzaken"}
    delivery = next(s for s in ahmed["steps"] if s["stepId"] == "delivery")
    assert delivery["actor"] == "mens"

    jeroen = execute_local("hcs-life-event-run",
                           {"recipeId": "thk-08-move-home", "persona": "jeroen", "mode": "replay"})["run"]
    follow = next(s for s in jeroen["steps"] if s["stepId"] == "followup")
    assert follow["handover"]["to"].startswith("wijkteam")


def test_life_event_run_unknown_persona_fails():
    from services.process_adapter.poc_handlers import execute_hcs_life_event_run
    with pytest.raises(KeyError):
        execute_hcs_life_event_run({"recipeId": "thk-08-move-home", "persona": "bestaatniet"})


def test_recipe_run_generic_with_tmp_fixture(tmp_path):
    city = tmp_path / "city"
    city.mkdir()
    (city / "probe-city.json").write_text(json.dumps({
        "recipeId": "probe-city",
        "scenarioKind": "city",
        "scenarios": [{"id": "wijk-01", "label": "Proefwijk"}],
        "steps": [{
            "stepId": "measure", "title": "Met de groendak", "blueprintStep": None,
            "defaults": {"actor": "agent", "genAiTestPoint": "G2", "dataUsed": ["remote sensing"],
                          "consent": "n.v.t.", "kpiEvents": [], "prov": {"sources": ["remote sensing"]}},
            "perScenario": {}
        }],
        "stopConditions": [{"id": "sc-1", "condition": "c", "action": "a"}],
        "kpiSnapshot": [{"kpi": "k", "baseline": "", "target": ""}],
    }))
    from services.process_adapter.poc_handlers import execute_hcs_recipe_run
    out = execute_hcs_recipe_run({"recipeId": "probe-city", "scenario": "wijk-01", "mode": "replay"},
                                 fixture_dir=tmp_path)
    validate_instance(out["run"], "hcs-run.schema.json")
    assert out["run"]["processId"] == "hcs-recipe-run"
```

- [ ] **Step 2: Draai — moet falen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: FAIL — `KeyError: 'hcs-life-event-run'` bij `describe_process`.

- [ ] **Step 3: Implementatie in `poc_handlers.py`**

Voeg bovenin (na de bestaande imports) toe:

```python
HCS_FIXTURES = NLDT_ROOT / "simulation" / "hcs" / "fixtures"


def _load_hcs_fixture(rel: Path) -> dict[str, Any]:
    path = HCS_FIXTURES / rel
    if not path.is_file():
        raise KeyError(f"HCS-fixture ontbreekt: {rel}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_hcs_run(fixture: dict[str, Any], scenario_id: str, mode: str, process_id: str,
                   scenario_key: str, stamp: str | None = None) -> dict[str, Any]:
    """Merge defaults met per-scenario overrides en valideer tegen hcs-run.schema.json."""
    scenarios = {p["id"] for p in fixture.get(scenario_key, [])}
    if scenario_id not in scenarios:
        raise KeyError(f"onbekend scenario '{scenario_id}' in {fixture['recipeId']}")
    override_key = "perPersona" if scenario_key == "personas" else "perScenario"
    steps: list[dict[str, Any]] = []
    for step in fixture["steps"]:
        merged = dict(step["defaults"])
        merged["stepId"] = step["stepId"]
        merged["title"] = step["title"]
        override = step.get(override_key, {}).get(scenario_id, {})
        merged.update(override)
        merged.setdefault("handover", None)
        steps.append(merged)
    from services.common.schema import validate_instance

    run = {
        "schemaVersion": "1.0",
        "runId": f"{fixture['recipeId']}-{scenario_id}",
        "generatedAt": stamp or "replay",
        "recipeId": fixture["recipeId"],
        "processId": process_id,
        "mode": mode,
        "scenario": scenario_id,
        "steps": steps,
        "stopConditions": fixture["stopConditions"],
        "kpiSnapshot": fixture["kpiSnapshot"],
    }
    if fixture.get("learningState"):
        run["learningState"] = fixture["learningState"]
    validate_instance(run, "hcs-run.schema.json")
    return run


def execute_hcs_life_event_run(inputs: dict[str, Any]) -> dict[str, Any]:
    fixture = _load_hcs_fixture(Path("life-events") / f"{inputs['recipeId']}.json")
    run = _build_hcs_run(fixture, inputs.get("persona") or fixture["personas"][0]["id"],
                         inputs.get("mode", "replay"), "hcs-life-event-run", "personas")
    return {"run": run}


def execute_hcs_recipe_run(inputs: dict[str, Any], *, fixture_dir: Path | None = None) -> dict[str, Any]:
    base = fixture_dir or (HCS_FIXTURES / "city")
    path = base / f"{inputs['recipeId']}.json"
    if not path.is_file():
        raise KeyError(f"HCS-fixture ontbreekt: {path}")
    fixture = json.loads(path.read_text(encoding="utf-8"))
    run = _build_hcs_run(fixture, inputs.get("scenario") or fixture["scenarios"][0]["id"],
                         inputs.get("mode", "replay"), "hcs-recipe-run", "scenarios")
    return {"run": run}
```

Voeg in `POC_PROCESS_DEFINITIONS` twee entries toe:

```python
    "hcs-life-event-run": {
        "id": "hcs-life-event-run",
        "title": "HCS life event run (vijf stappen, EDIC)",
        "description": (
            "Deterministic replay of a Human-Centred Services life event "
            "(The Key): intake, solution, contract, delivery, follow-up — with "
            "the human-agent boundary, GenAI test points G1-G5, prov sources "
            "and stop conditions as data (spec 2026-10-09-hcs-recipes-pocs-design)."
        ),
        "version": "1.0.0",
        "keywords": ["hcs", "edic", "the-key", "life-event"],
        "inputs": {
            "recipeId": {"title": "Recipe id (fixture in simulation/hcs/fixtures/life-events)",
                          "schema": {"type": "string"}},
            "persona": {"title": "Persona id uit de fixture", "schema": {"type": "string"}},
            "mode": {"title": "replay|execute", "schema": {"type": "string", "default": "replay"}},
        },
        "outputs": {"run": {"title": "HCS run-artefact", "schema": {"type": "object"}}},
    },
    "hcs-recipe-run": {
        "id": "hcs-recipe-run",
        "title": "HCS city recipe run (measure/plan/share/system)",
        "description": (
            "Generic deterministic replay for HCS city recipes (UAM, 3-30-300, "
            "Circular, 15-minute city): steps come from the recipe fixture, "
            "same run artifact as the life-event process."
        ),
        "version": "1.0.0",
        "keywords": ["hcs", "edic", "city-recipe"],
        "inputs": {
            "recipeId": {"title": "Recipe id (fixture in simulation/hcs/fixtures/city)",
                          "schema": {"type": "string"}},
            "scenario": {"title": "Scenario id uit de fixture", "schema": {"type": "string"}},
            "mode": {"title": "replay|execute", "schema": {"type": "string", "default": "replay"}},
        },
        "outputs": {"run": {"title": "HCS run-artefact", "schema": {"type": "object"}}},
    },
```

En in `EXECUTORS`:

```python
    "hcs-life-event-run": execute_hcs_life_event_run,
    "hcs-recipe-run": execute_hcs_recipe_run,
```

Pas `nldt/tests/test_poc_processes.py::test_poc_processes_registered` aan — voeg toe aan de `expected`-set:

```python
        "hcs-life-event-run",
        "hcs-recipe-run",
```

- [ ] **Step 4: Draai beide testbestanden — moeten slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py
git commit -m "feat(nldt): processen hcs-life-event-run en hcs-recipe-run — deterministische replay met mens-agent-grens als data"
```

---

### Task 5: De drie recipes + baselines + EDIC-adoptie

**Files:**
- Create: `nldt/recipes/thk-08-move-home.json`
- Create: `nldt/recipes/thk-02-having-a-baby.json`
- Create: `nldt/recipes/thk-24-build-renovate.json`
- Create: `nldt/recipes/baselines/thk-08-move-home.baseline.json`
- Create: `nldt/recipes/baselines/thk-02-having-a-baby.baseline.json`
- Create: `nldt/recipes/baselines/thk-24-build-renovate.baseline.json`
- Modify: `nldt/recipes/edic-asset-map.json` (drie entries + `updated`)
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Consumes: schema Task 1, processen Task 4. `load_recipe()` valideert automatisch tegen `recipe.schema.json`; baselines tegen `hcs-baseline.schema.json`.
- Produces: `run-recipe thk-08-move-home --input persona=sanne --input mode=replay` (offline) levert een geldig run-artefact.

- [ ] **Step 1: Schrijf de falende tests**

```python
THK_IDS = ("thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate")


@pytest.mark.parametrize("rid", THK_IDS)
def test_thk_recipe_valid_with_service(rid):
    recipe = load_recipe(rid)
    validate_instance(recipe, "recipe.schema.json")
    assert recipe["service"]["dish"] == "the-key"
    assert recipe["service"]["lifeEventCode"] in {"THK-08", "THK-02", "THK-24"}
    assert recipe["service"]["kpis"], "KPI's uit het framework verplicht"


@pytest.mark.parametrize("rid", THK_IDS)
def test_thk_baseline_valid(rid):
    baseline = json.loads(
        (NLDT_ROOT / "recipes" / "baselines" / f"{rid}.baseline.json").read_text())
    validate_instance(baseline, "hcs-baseline.schema.json")
    assert baseline["recipeId"] == rid
    assert baseline["disappearingStep"], "poort 1: verdwijnende stap benoemen (B5)"


def test_thk08_run_recipe_offline(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.recipe_runner import run_recipe
    result = run_recipe("thk-08-move-home", {"persona": "sanne", "mode": "replay"})
    run = result["outputs"]["run"]
    validate_instance(run, "hcs-run.schema.json")
    assert run["scenario"] == "sanne"


def test_thk24_declares_minigim_ingredient():
    recipe = load_recipe("thk-24-build-renovate")
    assert "minigim-gebiedscheck-run" in recipe["requiredProcesses"]


def test_edic_map_has_thk_entries():
    from services.common.schema import load_edic_asset_map
    payload = load_edic_asset_map()
    ids = {a["id"] for a in payload["assets"]}
    for rid in THK_IDS:
        assert f"recipe:{rid}" in ids
```

- [ ] **Step 2: Draai — moet falen** (`Recipe not found: thk-08-move-home`)

- [ ] **Step 3: Recipes aanmaken**

`nldt/recipes/thk-08-move-home.json` — volledige inhoud:

```json
{
  "id": "thk-08-move-home",
  "title": "The Key THK-08 — 'I want to move home'",
  "description": "Life-event recipe uit de Human-Centred Services Blueprint (EDIC): verhuizen als één gesorteerde reis over gemeente, energie, bank, verzekeraar en zorgverzekeraar. Vijf stappen met mens-agent-grens (adresonderzoek → medewerker), G1·G4-testpunten en de KPI's uit het framework. Deterministische replay via hcs-life-event-run.",
  "version": "1.0.0",
  "tags": ["hcs", "edic", "the-key", "thk-08", "life-event"],
  "requiredProcesses": ["hcs-life-event-run"],
  "inputs": {
    "persona": {"type": "string", "description": "persona-id: sanne|ahmed|maria|jeroen", "required": false},
    "mode": {"type": "string", "description": "replay|execute", "required": false}
  },
  "outputs": {"run": {"type": "json", "description": "HCS run-artefact (vijf stappen)"}},
  "steps": [
    {
      "id": "life-event",
      "processId": "hcs-life-event-run",
      "title": "Vijf-stappen-run 'Ik ga verhuizen'",
      "inputs": {"recipeId": "thk-08-move-home", "persona": "${recipe.inputs.persona}", "mode": "${recipe.inputs.mode}"},
      "outputs": {"run": "run"},
      "backend": "local"
    }
  ],
  "riskLevel": "medium",
  "service": {
    "dish": "the-key",
    "lifeEventCode": "THK-08",
    "serviceType": "reactive",
    "blueprintSteps": [1, 2, 3, 4, 5],
    "parties": [
      {"name": "Gemeente Zoetermeer", "role": "lead — Burgerzaken (PDC-vraag 8 + 6)"},
      {"name": "Energie- en netbeheerder", "role": "adres- en levering"},
      {"name": "Bank", "role": "adresgegevens"},
      {"name": "Verzekeraar", "role": "polisgegevens"},
      {"name": "Zorgverzekeraar", "role": "inschrijving"}
    ],
    "legalBasis": [
      {"basis": "Wet BRP", "timeLimit": "redelijke termijn (Awb)"},
      {"basis": "Wegenverkeerswet / APV (parkeren)", "timeLimit": "8 weken (Awb)"}
    ],
    "humanMeasure": {
      "handover": ["Adresonderzoek bij twijfel → medewerker"],
      "exceptions": ["adresonderzoek", "bewindsvoering/curatele"]
    },
    "localVariant": "gemeentelijk parkeerbeleid en afvalpas-regime",
    "genAiTestPoints": [
      {"point": "G1", "description": "Intake-assistent vraagt alleen wat niet in de BRP staat; meertalig, plain language", "testCases": ["persona ahmed (lage geletterdheid)", "persona maria (andere taal)"]},
      {"point": "G2", "description": "Matching: één samenhangend voorstel uit de PDC", "testCases": ["voorstel bevat alle vijf partijen"]},
      {"point": "G3", "description": "Consent uitleggen: wie ziet wat, per partij per periode", "testCases": ["persona jeroen (bewindsvoering)"]},
      {"point": "G4", "description": "Agentic orkestratie over partijen met status-uitleg", "testCases": ["parallelle afhandeling", "attestatie in wallet"]},
      {"point": "G5", "description": "Proactieve follow-up: rechten zonder nieuwe aanvraag; stuck → mens neemt over", "testCases": ["persona jeroen → wijkteam"]}
    ],
    "kpis": [
      {"kpi": "Moves processed without manual handling", "kpiType": "outcome", "unit": "%", "outcomeLens": "Z", "baseline": "", "target": "", "dataSource": "case system", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
    ]
  },
  "cookbookUri": "http://localhost:8081/recipes/thk-08-move-home"
}
```

`nldt/recipes/thk-02-having-a-baby.json` — volledige inhoud:

```json
{
  "id": "thk-02-having-a-baby",
  "title": "The Key THK-02 — 'I'm having a baby'",
  "description": "Life-event recipe (reactive → proactive): zwangerschap start het traject vóór de geboorte; geboorteaangifte binnen 5 dagen; keten naar SVB, Belastingdienst en zorgverzekeraar. G2·G5-testpunten; complexe situaties (erkenning, buitenlandse ouder) → medewerker.",
  "version": "1.0.0",
  "tags": ["hcs", "edic", "the-key", "thk-02", "life-event", "proactive"],
  "requiredProcesses": ["hcs-life-event-run"],
  "inputs": {
    "persona": {"type": "string", "description": "persona-id: lot|fatima", "required": false},
    "mode": {"type": "string", "description": "replay|execute", "required": false}
  },
  "outputs": {"run": {"type": "json", "description": "HCS run-artefact (vijf stappen)"}},
  "steps": [
    {
      "id": "life-event",
      "processId": "hcs-life-event-run",
      "title": "Vijf-stappen-run 'Ik krijg een kind'",
      "inputs": {"recipeId": "thk-02-having-a-baby", "persona": "${recipe.inputs.persona}", "mode": "${recipe.inputs.mode}"},
      "outputs": {"run": "run"},
      "backend": "local"
    }
  ],
  "riskLevel": "medium",
  "service": {
    "dish": "the-key",
    "lifeEventCode": "THK-02",
    "serviceType": "proactive",
    "blueprintSteps": [1, 2, 3, 4, 5],
    "parties": [
      {"name": "Gemeente Zoetermeer", "role": "lead — Burgerzaken; Sociaal Domein (PDC-vraag 17)"},
      {"name": "SVB", "role": "kinderbijslag"},
      {"name": "Belastingdienst", "role": "toeslagen"},
      {"name": "Zorgverzekeraar", "role": "verzekering kind"}
    ],
    "legalBasis": [
      {"basis": "Wet BRP", "timeLimit": "melding binnen 5 dagen"},
      {"basis": "Burgerlijk Wetboek (erkenning, naamgeving)", "timeLimit": "vóór geboorte of bij aangifte"}
    ],
    "humanMeasure": {
      "handover": ["Complexe situaties (erkenning, buitenlandse ouder) → medewerker"],
      "exceptions": ["erkenning", "gezag", "buitenlandse akten"]
    },
    "localVariant": "kraamzorg-matching via gemeentelijke voorkeurslijst",
    "genAiTestPoints": [
      {"point": "G2", "description": "Proactief voorstel: verlof, kraamzorg, kinderegelingen", "testCases": ["persona lot"]},
      {"point": "G3", "description": "Consent per ketenpartij", "testCases": ["toestemming SVB/toeslagen"]},
      {"point": "G4", "description": "Geboorteaangifte digitaal binnen 5 dagen", "testCases": ["digitale aangifte"]},
      {"point": "G5", "description": "Proactief signaleren kinderbijslag en toeslagen", "testCases": ["signaal vóór termijn"]}
    ],
    "kpis": [
      {"kpi": "Birth registrations done digitally", "kpiType": "output", "unit": "%", "outcomeLens": "—", "baseline": "", "target": "", "dataSource": "BRP", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
    ]
  },
  "cookbookUri": "http://localhost:8081/recipes/thk-02-having-a-baby"
}
```

`nldt/recipes/thk-24-build-renovate.json` — volledige inhoud (declaratieve ingredient-koppeling naar minigim):

```json
{
  "id": "thk-24-build-renovate",
  "title": "The Key THK-24 — 'I want to build or renovate'",
  "description": "Life-event recipe: bouwplan → vergunningcheck (Omgevingsloket) → aanvraag → beoordeling door de mens → besluit binnen 8 weken (regulier). De vergunningcheck gebruikt de bestaande MiniGIM-gebiedscheck als ingredient (declaratief: canonieke run; live koppeling in een latere fase). Doctrine: AI stelt voor · mens beslist.",
  "version": "1.0.0",
  "tags": ["hcs", "edic", "the-key", "thk-24", "life-event", "omgevingswet"],
  "requiredProcesses": ["hcs-life-event-run", "minigim-gebiedscheck-run"],
  "inputs": {
    "persona": {"type": "string", "description": "persona-id: noor|peter", "required": false},
    "mode": {"type": "string", "description": "replay|execute", "required": false}
  },
  "outputs": {"run": {"type": "json", "description": "HCS run-artefact (vijf stappen)"}},
  "steps": [
    {
      "id": "life-event",
      "processId": "hcs-life-event-run",
      "title": "Vijf-stappen-run 'Ik wil bouwen of renoveren'",
      "inputs": {"recipeId": "thk-24-build-renovate", "persona": "${recipe.inputs.persona}", "mode": "${recipe.inputs.mode}"},
      "outputs": {"run": "run"},
      "backend": "local"
    }
  ],
  "riskLevel": "high",
  "service": {
    "dish": "the-key",
    "lifeEventCode": "THK-24",
    "serviceType": "reactive",
    "blueprintSteps": [1, 2, 3, 4, 5],
    "parties": [
      {"name": "Gemeente", "role": "Vergunningen / Omgevingsloket (PDC-vraag 10)"},
      {"name": "Omgevingsloket Rijk", "role": "vergunningcheck (SDG)"},
      {"name": "MiniGIM gebiedscheck", "role": "ingredient — canonieke gebiedsrun"}
    ],
    "legalBasis": [
      {"basis": "Omgevingswet", "timeLimit": "8 weken (regulier) / 26 weken (uitgebreid)"}
    ],
    "humanMeasure": {
      "handover": ["Beoordeling en besluit door vergunningverlener (V4-mens)"],
      "exceptions": ["beschermd gezicht / monument", "uitgebreide procedure"]
    },
    "localVariant": "gemeentelijke welstandscriteria en APV-bepalingen",
    "genAiTestPoints": [
      {"point": "G1", "description": "Bouwplan in eigen woorden; aanvullende vragen alleen waar het plan dat vraagt", "testCases": ["persona noor"]},
      {"point": "G2", "description": "Vergunningcheck vóór de aanvraag (matching plan ↔ regels)", "testCases": ["persona peter (beschermd gezicht)"]},
      {"point": "G3", "description": "Documentcheck: complete aanvraag bij eerste inzending", "testCases": ["brondocumenten"]},
      {"point": "G5", "description": "Proactief: bouwtoezicht- en vervolgstappen na besluit", "testCases": ["follow-up na besluit"]}
    ],
    "kpis": [
      {"kpi": "Decision within 8 weeks (regular)", "kpiType": "output", "unit": "%", "outcomeLens": "—", "baseline": "", "target": "", "dataSource": "case system", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
    ]
  },
  "cookbookUri": "http://localhost:8081/recipes/thk-24-build-renovate"
}
```

- [ ] **Step 4: Baselines aanmaken**

`nldt/recipes/baselines/thk-08-move-home.baseline.json`:

```json
{
  "recipeId": "thk-08-move-home",
  "publicOutcome": "Verhuizen is één gesorteerde reis: één keer aangeven, alle partijen geregeld, attestatie in de wallet — meer tijd voor wat ertoe doet.",
  "disappearingStep": "Vijf loketbezoeken en papierformulieren verdwijnen; de verhuisdatum is het enige dat nog gevraagd wordt.",
  "kpis": [
    {"kpi": "Moves processed without manual handling", "kpiType": "outcome", "unit": "%", "outcomeLens": "Z", "baseline": "", "target": "", "dataSource": "case system", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
  ],
  "stopConditions": [
    {"condition": "mens-overnames bij intake > 20% over vier weken", "action": "pauzeer intake-assistent (G1) — escalatie naar function steward"},
    {"condition": "geen unanimous go op testbank-assen", "action": "geen go — terug naar design (recipe-cyclus stap 1)"},
    {"condition": "AI Act risk class wijzigt naar high-risk", "action": "stop en her-toets de mens-agent-grens (poort 3)"}
  ],
  "goNoGo": [
    "Accuracy ≥ 95% over de vier testbank-personas",
    "Zero-shot regel: geen enkele vraag naar gegevens die al in de BRP staan (once-only)",
    "Plain language-check geslaagd voor ahmed en maria",
    "Elke mens-overname binnen één werkdag opgevolgd"
  ]
}
```

`nldt/recipes/baselines/thk-02-having-a-baby.baseline.json`:

```json
{
  "recipeId": "thk-02-having-a-baby",
  "publicOutcome": "Ouders regelen verlof, kraamzorg, aangifte en kinderegelingen vóór de geboorte — de melding binnen 5 dagen is digitaal en de ketenpartijen zijn proactief.",
  "disappearingStep": "De geboorteaangifte op het loket verdwijnt; SVB- en toeslagen-aanvragen worden niet meer aangevraagd maar aangeboden.",
  "kpis": [
    {"kpi": "Birth registrations done digitally", "kpiType": "output", "unit": "%", "outcomeLens": "—", "baseline": "", "target": "", "dataSource": "BRP", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
  ],
  "stopConditions": [
    {"condition": "digitale registratie < 80% over een maand", "action": "onderzoek afhaalmoment; terug naar design"},
    {"condition": "klachten over ongevraagde proactieve contacten", "action": "G5-paar af; menselijke tussenstap inbouwen"}
  ],
  "goNoGo": [
    "Melding binnen 5 dagen in alle testgevallen",
    "Erkenningsscenario (fatima) eindigt altijd bij een medewerker, nooit bij de agent",
    "Proactieve signalen alleen over zaken waar consent voor is gegeven"
  ]
}
```

`nldt/recipes/baselines/thk-24-build-renovate.baseline.json`:

```json
{
  "recipeId": "thk-24-build-renovate",
  "publicOutcome": "Een bouwplan wordt vóór de aanvraag getoetst, de aanvraag is compleet bij de eerste inzending en het besluit valt binnen 8 weken — met de vergunningverlener aan het roer.",
  "disappearingStep": "De 'aanvraag blijkt onvolledig'-ronde verdwijnt; de vergunningcheck vervangt het vooraf-informatiegesprek.",
  "kpis": [
    {"kpi": "Decision within 8 weeks (regular)", "kpiType": "output", "unit": "%", "outcomeLens": "—", "baseline": "", "target": "", "dataSource": "case system", "frequency": "monthly", "kviRollup": "KVI 5 (Digital) · Zoetermeer business case"}
  ],
  "stopConditions": [
    {"condition": "vergunningcheck wijkt af van de beoordeling in > 10% van de reguliere zaken", "action": "check-model bijstellen; geen auto-aanbevelingen (G2)"},
    {"condition": "besluiten structureel niet binnen 8 weken", "action": "baseline-analyse; agent-inzet is geen verklaring"}
  ],
  "goNoGo": [
    "Beoordeling en besluit altijd door de mens (doctrine)",
    "Check-voorspelbaarheid per productsoort gepubliceerd in de recipe",
    "Beschermd gezicht-scenario (peter) start de uitgebreide procedure korrekt"
  ]
}
```

- [ ] **Step 5: EDIC-asset-entries toevoegen**

In `nldt/recipes/edic-asset-map.json`: zet `"updated": "2026-10-09"` en voeg aan `assets` toe:

```json
  {
    "id": "recipe:thk-08-move-home",
    "kind": "recipe",
    "title": "The Key THK-08 — 'I want to move home'",
    "path": "nldt/recipes/thk-08-move-home.json",
    "edic": "ldt-citiverse",
    "assetClass": "hcs-life-event",
    "owner": "Digital Toolbox (EDIC)",
    "relationshipOwners": ["Serendipity", "Gemeente Zoetermeer"],
    "acceptance": "GenAI-testbank G1-G5 + function-baseline; deterministische replay via OGC API Processes (hcs-life-event-run)",
    "fallback": "vng-geonovum-cookbook",
    "readiness": "demo",
    "riskLevel": "medium"
  },
  {
    "id": "recipe:thk-02-having-a-baby",
    "kind": "recipe",
    "title": "The Key THK-02 — 'I'm having a baby'",
    "path": "nldt/recipes/thk-02-having-a-baby.json",
    "edic": "ldt-citiverse",
    "assetClass": "hcs-life-event",
    "owner": "Digital Toolbox (EDIC)",
    "relationshipOwners": ["Serendipity", "Gemeente Zoetermeer"],
    "acceptance": "GenAI-testbank G2/G5 + function-baseline; deterministische replay via OGC API Processes (hcs-life-event-run)",
    "fallback": "vng-geonovum-cookbook",
    "readiness": "demo",
    "riskLevel": "medium"
  },
  {
    "id": "recipe:thk-24-build-renovate",
    "kind": "recipe",
    "title": "The Key THK-24 — 'I want to build or renovate'",
    "path": "nldt/recipes/thk-24-build-renovate.json",
    "edic": "ldt-citiverse",
    "assetClass": "hcs-life-event",
    "owner": "Digital Toolbox (EDIC)",
    "relationshipOwners": ["Serendipity", "Gemeente Zoetermeer"],
    "acceptance": "GenAI-testbank + function-baseline; menselijke beoordeling by design; declaratieve minigim-ingredient-koppeling",
    "fallback": "vng-geonovum-cookbook",
    "readiness": "demo",
    "riskLevel": "high"
  }
```

- [ ] **Step 6: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v`
Expected: PASS (inclusief de nieuwe recipe-, baseline-, run-recipe- en EDIC-tests).

- [ ] **Step 7: Handmatige verificatie via de CLI**

Run:

```bash
cd nldt && NLDT_OFFLINE=1 .venv/bin/python -m services.cli run-recipe thk-08-move-home --input persona=maria --input mode=replay
```

Expected: JSON met `recipeId: thk-08-move-home`, vijf steps, `outputs.run.scenario == "maria"` en bij `solution` de taalvoorkeur in `dataUsed`.

- [ ] **Step 8: Commit**

```bash
git add nldt/recipes/thk-08-move-home.json nldt/recipes/thk-02-having-a-baby.json nldt/recipes/thk-24-build-renovate.json nldt/recipes/baselines nldt/recipes/edic-asset-map.json nldt/tests/test_hcs.py
git commit -m "feat(nldt): The Key-recipes THK-08/02/24 met EDIC-anatomy, function-baselines en EDIC-adoptie"
```

---

### Task 6: Generator `build_runs.py` — runs én demodata

**Files:**
- Create: `nldt/simulation/hcs/build_runs.py`
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Consumes: fixtures (Task 3), executors (Task 4), schema's (Task 2).
- Produces: `nldt/simulation/hcs/runs/<recipeId>_<persona>.json` (acht stuks: thk-08 ×4, thk-02 ×2, thk-24 ×2), elk gevalideerd tegen `hcs-run.schema.json`, met `generatedAt`/`runId` gevuld vanuit `--stamp`. Deterministisch: zelfde stamp → byte-identiek.

- [ ] **Step 1: Schrijf de falende test**

```python
RUNS_DIR = HCS_ROOT / "runs"


def test_build_runs_deterministic(tmp_path):
    import subprocess
    import sys

    venv = NLDT_ROOT / ".venv" / "bin" / "python"
    stamp = "20261009T000000Z"
    cmd = [str(venv), str(HCS_ROOT / "build_runs.py"), "--stamp", stamp,
           "--outdir", str(tmp_path), "--only-runs"]
    first = subprocess.run(cmd, capture_output=True, text=True, check=True)
    second = subprocess.run(cmd, capture_output=True, text=True, check=True)
    files = sorted(p.name for p in tmp_path.glob("*.json"))
    assert len(files) == 8, files
    assert "OK" in first.stdout and "OK" in second.stdout
    for name in files:
        a = (tmp_path / name).read_bytes()
        b = (tmp_path / name).read_bytes()
        assert a == b  # zelfde stamp → identiek (determinisme binnen één outdir)
    run = json.loads((tmp_path / "thk-08-move-home_sanne.json").read_text())
    assert run["generatedAt"].endswith("Z")
    assert run["runId"].endswith(stamp)
```

- [ ] **Step 2: Draai — moet falen** (bestand bestaat niet)

- [ ] **Step 3: Generator schrijven**

`nldt/simulation/hcs/build_runs.py` — volledige inhoud:

```python
#!/usr/bin/env python3
"""Genereert HCS-runs en demopagina's uit fixtures (patroon regelrecht/build_runs.py).

Deterministisch: zelfde --stamp levert byte-identieke uitvoer. Gevalideerd tegen
nldt/schemas/hcs-run.schema.json. Alleen-lezen ten opzichte van de fixtures en recipes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[2]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))

from services.common.schema import validate_instance  # noqa: E402
from services.process_adapter.poc_handlers import (  # noqa: E402
    execute_hcs_life_event_run,
)

HCS_ROOT = NLDT_ROOT / "simulation" / "hcs"
LIFE_FIXTURES = HCS_ROOT / "fixtures" / "life-events"
RUNS_DIR = HCS_ROOT / "runs"


def build_runs(stamp: str, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted(LIFE_FIXTURES.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        for persona in fixture["personas"]:
            out = execute_hcs_life_event_run(
                {"recipeId": fixture["recipeId"], "persona": persona["id"], "mode": "replay"})
            run = out["run"]
            run["generatedAt"] = stamp_iso(stamp)
            run["runId"] = f"{fixture['recipeId']}-{persona['id']}-{stamp}"
            validate_instance(run, "hcs-run.schema.json")
            target = outdir / f"{fixture['recipeId']}_{persona['id']}.json"
            target.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8")
            written.append(target)
            print(f"OK run {target.relative_to(NLDT_ROOT)}")
    return written


def stamp_iso(stamp: str) -> str:
    """20261009T000000Z -> 2026-10-09T00:00:00Z ( anders ongewijzigd)."""
    if len(stamp) == 16 and stamp.endswith("Z") and stamp[8] == "T":
        return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"
    return stamp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stamp", required=True, help="bouw-stamp, bv. 20261009T101500Z")
    parser.add_argument("--outdir", type=Path, default=RUNS_DIR)
    parser.add_argument("--only-runs", action="store_true",
                        help="alleen runs schrijven (geen pagina's) — pagina-vulling komt in Task 7")
    args = parser.parse_args()
    build_runs(args.stamp, args.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py::test_build_runs_deterministic -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/hcs/build_runs.py nldt/tests/test_hcs.py
git commit -m "feat(nldt): HCS-generator — deterministische runs uit fixtures, gevalideerd tegen het run-contract"
```

---

### Task 7: The Key-demo — template + gegenereerde pagina's (NL/EN)

**Files:**
- Create: `nldt/simulation/hcs/key-demo.template.html`
- Modify: `nldt/simulation/hcs/build_runs.py` (pagina-vulling, stap 4)
- Generated: `nldt/simulation/hcs-key-demo.html`, `nldt/simulation/hcs-key-demo-en.html`
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- Placeholders in de template: `__HCS_DATA__` (JSON: `{runs, fixtures, common, i18n}`), `__LANG__` (`"nl"`|`"en"`), `__BUILD_STAMP__`. Na vulling mag geen `__...__`-placeholder overblijven.
- De pagina: scène-rail met de vijf blueprint-stappen, persona-switcher, stapdetail (actor, G-punt, data, consent, handover, bron), testbank-paneel, KPI-paneel, leerstaat-strip, THK-02/THK-24-scènes, in-pagina selftest (12 checks) met badge.

- [ ] **Step 1: Schrijf de falende test**

```python
KEY_DEMO = NLDT_ROOT / "simulation" / "hcs-key-demo.html"
KEY_DEMO_EN = NLDT_ROOT / "simulation" / "hcs-key-demo-en.html"


class TestKeyDemo:
    def test_pages_generated_and_filled(self):
        for path in (KEY_DEMO, KEY_DEMO_EN):
            text = path.read_text()
            assert "window.HCS_DATA" in text
            assert "id=\"selftest-badge\"" in text
            for marker in ("__HCS_DATA__", "__LANG__", "__BUILD_STAMP__"):
                assert marker not in text, f"{marker} niet gevuld in {path.name}"

    def test_nl_content(self):
        text = KEY_DEMO.read_text()
        assert '"nl"' in text or "nl" in text
        assert "Ik ga verhuizen" in text
        assert "adresonderzoek" in text.lower()
        assert "Mens-agent-grens" in text

    def test_en_content(self):
        text = KEY_DEMO_EN.read_text()
        assert "I want to move home" in text           # i18n-titel
        assert "Human-agent boundary" in text          # i18n-label
        assert 'window.HCS_LANG = "en"' in text        # taalvlag
        # Run-data (staptitels, handover-redenen) blijft in fase 1 Nederlands;
        # een volledig Engelse run-laag is fase 3-werk (spec §6).
```

- [ ] **Step 2: Draai — moet falen** (pagina's bestaan niet)

- [ ] **Step 3: Template schrijven**

`nldt/simulation/hcs/key-demo.template.html` — volledige inhoud:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>HCS · The Key — 'I want to move home' (EDIC recipe PoC)</title>
<style>
  :root {
    --papier: #f6f8fb; --inkt: #06121b; --inkt-2: #0d1e2c; --ijs: #dff3ff; --ijs-rand: #c4d0da;
    --blauw: #2ba8ff; --hemel: #79c9ff; --oranje: #ff9815; --oranje-donker: #ef8700; --amber: #ffc37e;
    --rood: #e10500; --mint: #1cefa5; --groen: #0f7a4d;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    --sans: Roboto, "Helvetica Neue", system-ui, -apple-system, Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--inkt); color: var(--papier); font-family: var(--sans); line-height: 1.5; padding: 22px clamp(14px, 4vw, 44px) 60px; }
  h1 { font-size: clamp(1.5rem, 3.2vw, 2.2rem); letter-spacing: .01em; }
  h1 .dish { color: var(--oranje); }
  .sub { color: var(--hemel); font-family: var(--mono); font-size: .74rem; letter-spacing: .08em; text-transform: uppercase; }
  .topbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
  .lang a { color: var(--blauw); font-family: var(--mono); font-size: .78rem; text-decoration: none; margin-left: 12px; }
  #selftest-badge { font-family: var(--mono); font-size: .72rem; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--ijs-rand); color: var(--ijs); }
  #selftest-badge.ok { border-color: var(--mint); color: var(--mint); }
  #selftest-badge.fail { border-color: var(--rood); color: var(--rood); font-weight: 700; }
  .rail { display: flex; gap: 6px; margin: 16px 0 10px; flex-wrap: wrap; }
  .rail button { font: inherit; font-size: .82rem; background: var(--inkt-2); color: var(--papier); border: 1px solid var(--ijs-rand); border-radius: 3px; padding: 8px 12px; cursor: pointer; }
  .rail button.active { background: var(--oranje-donker); border-color: var(--oranje); color: var(--inkt); font-weight: 700; }
  .rail button .g { font-family: var(--mono); font-size: .66rem; display: block; color: var(--hemel); }
  .rail button.active .g { color: var(--inkt); }
  .personas { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 18px; }
  .personas button { font: inherit; font-size: .8rem; background: transparent; color: var(--ijs); border: 1px dashed var(--ijs-rand); border-radius: 999px; padding: 6px 14px; cursor: pointer; }
  .personas button.active { border-style: solid; border-color: var(--blauw); color: #fff; background: rgba(43,168,255,.16); }
  .personas button .edge { color: var(--amber); font-family: var(--mono); font-size: .66rem; margin-left: 6px; }
  section { background: var(--inkt-2); border: 1px solid rgba(196,208,218,.25); border-radius: 4px; padding: 16px 18px; margin: 14px 0; }
  h2 { font-size: 1rem; color: var(--oranje); margin-bottom: 8px; letter-spacing: .02em; }
  .stapmeta { display: flex; flex-wrap: wrap; gap: 10px; font-family: var(--mono); font-size: .72rem; color: var(--hemel); margin-bottom: 10px; }
  .stapmeta b { color: var(--papier); }
  .actor-agent { color: var(--mint); } .actor-mens { color: var(--amber); } .actor-partij { color: var(--blauw); }
  .handover { border-left: 4px solid var(--amber); background: rgba(255,195,126,.1); padding: 10px 12px; margin: 10px 0; font-size: .9rem; }
  .handover b { color: var(--amber); }
  ul.data { list-style: none; font-size: .86rem; }
  ul.data li { padding: 4px 8px; border-left: 2px solid var(--ijs-rand); margin: 4px 0; }
  .src { font-family: var(--mono); font-size: .68rem; color: #7f93a2; margin-top: 8px; }
  .kvpanel table, .testbank table { width: 100%; border-collapse: collapse; font-size: .8rem; }
  .kvpanel th, .kvpanel td, .testbank th, .testbank td { text-align: left; padding: 5px 8px; border-bottom: 1px solid rgba(196,208,218,.2); }
  .lens { font-family: var(--mono); font-size: .7rem; padding: 1px 7px; border-radius: 3px; background: rgba(255,152,21,.15); color: var(--oranje); }
  .scenes { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
  .scene { border: 1px solid rgba(196,208,218,.25); border-radius: 4px; padding: 12px 14px; }
  .scene h3 { font-size: .92rem; color: var(--hemel); margin-bottom: 6px; }
  .scene p { font-size: .84rem; color: var(--ijs); }
  .scene .chip { display: inline-block; font-family: var(--mono); font-size: .64rem; color: var(--inkt); background: var(--blauw); border-radius: 3px; padding: 1px 6px; margin-top: 8px; }
  .leerstaat { font-size: .84rem; }
  .leerstaat .item { border-top: 1px dashed rgba(196,208,218,.3); padding: 8px 0; }
  .leerstaat .vraag { color: var(--hemel); font-family: var(--mono); font-size: .68rem; }
  .voet { font-family: var(--mono); font-size: .66rem; color: #7f93a2; margin-top: 24px; }
</style>
</head>
<body>
<div class="topbar">
  <div>
    <div class="sub" id="eyecatcher"></div>
    <h1><span class="dish" id="dish-title"></span></h1>
  </div>
  <div>
    <span id="selftest-badge">selftest…</span>
    <span class="lang" id="lang-switch"></span>
  </div>
</div>
<p class="sub" id="lede"></p>
<div class="personas" id="personas"></div>
<div class="rail" id="rail"></div>
<section id="step-detail">
  <h2 id="step-title"></h2>
  <div class="stapmeta" id="step-meta"></div>
  <div id="step-handover"></div>
  <ul class="data" id="step-data"></ul>
  <div class="src" id="step-src"></div>
</section>
<section class="testbank">
  <h2 id="tb-title"></h2>
  <table><tbody id="tb-body"></tbody></table>
</section>
<section class="kvpanel">
  <h2 id="kpi-title"></h2>
  <table><thead id="kpi-head"></thead><tbody id="kpi-body"></tbody></table>
</section>
<section>
  <h2 id="scenes-title"></h2>
  <div class="scenes" id="scenes"></div>
</section>
<section>
  <h2 id="leer-title"></h2>
  <div class="leerstaat" id="leerstaat"></div>
</section>
<div class="voet" id="voet"></div>
<script>
window.HCS_DATA = __HCS_DATA__;
window.HCS_LANG = __LANG__;
window.HCS_STAMP = "__BUILD_STAMP__";
</script>
<script>
(function () {
  "use strict";
  var D = window.HCS_DATA, L = window.HCS_LANG, t = D.i18n[L];
  var state = { recipe: "thk-08-move-home", persona: "sanne", step: 0 };
  function el(id) { return document.getElementById(id); }
  function run() { return D.runs[state.recipe][state.persona]; }

  function renderHeader() {
    el("eyecatcher").textContent = t.eyecatcher;
    el("dish-title").textContent = t.title;
    el("lede").textContent = t.lede;
    el("lang-switch").innerHTML = L === "nl"
      ? 'NL · <a href="hcs-key-demo-en.html">EN</a>'
      : '<a href="hcs-key-demo.html">NL</a> · EN';
    el("voet").textContent = t.foot.replace("{stamp}", window.HCS_STAMP);
  }

  function renderPersonas() {
    var box = el("personas"); box.innerHTML = "";
    D.fixtures[state.recipe].personas.forEach(function (p) {
      var b = document.createElement("button");
      b.textContent = p.label;
      if (p.edge) { var s = document.createElement("span"); s.className = "edge"; s.textContent = p.edge; b.appendChild(s); }
      if (p.id === state.persona) b.className = "active";
      b.onclick = function () { state.persona = p.id; renderAll(); };
      box.appendChild(b);
    });
  }

  function renderRail() {
    var rail = el("rail"); rail.innerHTML = "";
    run().steps.forEach(function (s, i) {
      var b = document.createElement("button");
      b.innerHTML = (i + 1) + ". " + s.title + '<span class="g">' + s.genAiTestPoint + "</span>";
      if (i === state.step) b.className = "active";
      b.onclick = function () { state.step = i; renderRail(); renderStep(); };
      rail.appendChild(b);
    });
  }

  function renderStep() {
    var s = run().steps[state.step];
    el("step-title").textContent = s.title;
    el("step-meta").innerHTML =
      '<span><b>' + t.actor + ':</b> <span class="actor-' + s.actor + '">' + t.actorNames[s.actor] + "</span></span>" +
      '<span><b>GenAI:</b> ' + s.genAiTestPoint + "</span>" +
      '<span><b>' + t.consent + ':</b> ' + t.consentNames[s.consent] + "</span>";
    el("step-handover").innerHTML = s.handover
      ? '<div class="handover"><b>' + t.handover + ":</b> " + s.handover.reason + " → " + s.handover.to + "</div>"
      : "";
    el("step-data").innerHTML = s.dataUsed.map(function (d) { return "<li>" + d + "</li>"; }).join("");
    el("step-src").textContent = t.sources + ": " + s.prov.sources.join(" · ");
  }

  function renderTestbank() {
    el("tb-title").textContent = t.testbank;
    el("tb-body").innerHTML = D.common.testbank.map(function (axis) {
      var verdict = selftestAxis(axis);
      return "<tr><td>" + axis + "</td><td style='color:" + (verdict ? "var(--mint)" : "var(--amber)") + "'>" +
        (verdict ? t.tbOk : t.tbCheck) + "</td></tr>";
    }).join("");
  }

  function selftestAxis(axis) { return D.selftestVerdicts[state.recipe][axis] !== false; }

  function renderKpi() {
    el("kpi-title").textContent = t.kpiPanel;
    el("kpi-head").innerHTML = "<tr><th>" + t.kpi + "</th><th>" + t.kpiType + "</th><th>Lens</th><th>" + t.dataSource + "</th><th>KVI</th></tr>";
    var fx = D.fixtures[state.recipe];
    el("kpi-body").innerHTML = fx.service.kpis.map(function (k) {
      return "<tr><td>" + k.kpi + "</td><td>" + k.kpiType + "</td><td><span class='lens'>" + k.outcomeLens + "</span></td><td>" + k.dataSource + "</td><td>" + (k.kviRollup || "—") + "</td></tr>";
    }).join("");
  }

  function renderScenes() {
    el("scenes-title").textContent = t.scenes;
    el("scenes").innerHTML = D.scenes.map(function (sc) {
      return "<div class='scene'><h3>" + sc.title[L] + "</h3><p>" + sc.body[L] + "</p><span class='chip'>" + sc.chip + "</span></div>";
    }).join("");
  }

  function renderLeerstaat() {
    el("leer-title").textContent = t.learning;
    el("leerstaat").innerHTML = (run().learningState || []).map(function (item) {
      return "<div class='item'><div><b>" + item.signal + "</b></div>" +
        "<div class='vraag'>" + t.lsWhy + ": " + item.why + "</div>" +
        "<div>" + t.lsChange + ": " + item.change + "</div>" +
        "<div class='vraag'>" + t.lsWho + ": " + item.decidesBy + "</div></div>";
    }).join("") || "<em>" + t.lsNone + "</em>";
  }

  function selftest() {
    var checks = [];
    checks.push(["runs aanwezig", Object.keys(D.runs).length === 3]);
    checks.push(["thk-08: 4 persona's", D.fixtures["thk-08-move-home"].personas.length === 4]);
    checks.push(["vijf stappen per run", Object.keys(D.runs).every(function (r) {
      return Object.keys(D.runs[r]).every(function (p) { return D.runs[r][p].steps.length === 5; }); })]);
    var ahmed = D.runs["thk-08-move-home"].ahmed;
    checks.push(["ahmed: handover bij intake", !!ahmed.steps[0].handover]);
    checks.push(["ahmed: mens bij delivery", ahmed.steps[3].actor === "mens"]);
    checks.push(["jeroen: wijkteam bij follow-up", D.runs["thk-08-move-home"].jeroen.steps[4].handover.to.indexOf("wijkteam") === 0]);
    checks.push(["sanne: geen enkele overname", D.runs["thk-08-move-home"].sanne.steps.every(function (s) { return !s.handover; })]);
    checks.push(["G1 bij intake (thk-08)", D.runs["thk-08-move-home"].sanne.steps[0].genAiTestPoint === "G1"]);
    checks.push(["thk-02: proactief (G5) in follow-up", D.runs["thk-02-having-a-baby"].lot.steps[4].genAiTestPoint === "G5"]);
    checks.push(["thk-24: beoordeling door mens", D.runs["thk-24-build-renovate"].noor.steps[3].actor === "mens"]);
    checks.push(["stopcondities aanwezig (poort 5)", Object.keys(D.runs).every(function (r) {
      var first = Object.keys(D.runs[r])[0];
      return D.runs[r][first].stopConditions.length > 0; })]);
    checks.push(["KPI's per recipe (poort 1)", ["thk-08-move-home", "thk-02-having-a-baby", "thk-24-build-renovate"].every(function (r) {
      return D.fixtures[r].service.kpis.length > 0; })]);
    var failed = checks.filter(function (c) { return !c[1]; });
    var badge = el("selftest-badge");
    badge.textContent = (failed.length === 0 ? "selftest " : "SELFTEST ") + (checks.length - failed.length) + "/" + checks.length;
    badge.className = failed.length === 0 ? "ok" : "fail";
    return failed.length === 0;
  }

  function renderAll() { renderPersonas(); renderRail(); renderStep(); renderTestbank(); renderKpi(); renderScenes(); renderLeerstaat(); }

  renderHeader(); renderAll();
  selftest();
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Generator uitbreiden — data vullen en twee pagina's schrijven**

Voeg in `build_runs.py` toe (boven `main`, en aangeroepen vanuit `main` wanneer `--only-runs` niet gegeven is):

```python
LANGS = {"nl": NLDT_ROOT / "simulation" / "hcs-key-demo.html",
         "en": NLDT_ROOT / "simulation" / "hcs-key-demo-en.html"}

I18N = {
    "nl": {
        "eyecatcher": "Human-Centred Services · EDIC recipe PoC · The Key",
        "title": "Ik ga verhuizen — één reis, gesorteerd",
        "lede": "Vijf stappen uit de blueprint, gedraaid als deterministische replay op de nLDT-harness: de mens-agent-grens, de G-testpunten en de KPI-baseline zijn data, geen belofte.",
        "foot": "HCS fase 1 · build {stamp} · runs gevalideerd tegen hcs-run.schema.json · doctrine: AI stelt voor · pijplijn beslist · mens beslist",
        "actor": "Actor", "consent": "Consent",
        "actorNames": {"agent": "agent", "mens": "mens", "partij": "partij"},
        "consentNames": {"n.v.t.": "n.v.t.", "gevraagd": "gevraagd", "gegeven": "gegeven", "geweigerd": "geweigerd"},
        "handover": "Mens-agent-grens — overname", "sources": "Bronnen",
        "testbank": "GenAI-testbank (go/no-go per as)", "tbOk": "go", "tbCheck": "toets in uitvoering",
        "kpiPanel": "KPI-framework (poort 1: baseline vóór technologie)", "kpi": "KPI", "kpiType": "Type",
        "dataSource": "Bron", "scenes": "De andere The Key-recipes uit deze PoC",
        "learning": "Leerstaat (recipe-cyclus stap 6: measure & improve)",
        "lsWhy": "Waarom", "lsChange": "Wat moet veranderen", "lsWho": "Wie beslist", "lsNone": "Nog geen leersignalen in deze run.",
    },
    "en": {
        "eyecatcher": "Human-Centred Services · EDIC recipe PoC · The Key",
        "title": "I want to move home — one trip, sorted",
        "lede": "Five steps from the blueprint, run as a deterministic replay on the nLDT harness: the human-agent boundary, the G-test points and the KPI baseline are data, not promises.",
        "foot": "HCS phase 1 · build {stamp} · runs validated against hcs-run.schema.json · doctrine: AI proposes · pipeline decides · human decides",
        "actor": "Actor", "consent": "Consent",
        "actorNames": {"agent": "agent", "mens": "human", "partij": "party"},
        "consentNames": {"n.v.t.": "n/a", "gevraagd": "asked", "gegeven": "given", "geweigerd": "refused"},
        "handover": "Human-agent boundary — handover", "sources": "Sources",
        "testbank": "GenAI test bench (go/no-go per axis)", "tbOk": "go", "tbCheck": "check in progress",
        "kpiPanel": "KPI framework (gate 1: baseline before technology)", "kpi": "KPI", "kpiType": "Type",
        "dataSource": "Source", "scenes": "The other The Key recipes in this PoC",
        "learning": "Learning state (recipe cycle step 6: measure & improve)",
        "lsWhy": "Why", "lsChange": "What must change", "lsWho": "Who decides", "lsNone": "No learning signals in this run yet.",
    },
}

SCENES = [
    {"chip": "THK-02 · G2 · G5", "title": {"nl": "Ik krijg een kind", "en": "I'm having a baby"},
     "body": {"nl": "Proactief traject vóór de geboorte; geboorteaangifte binnen 5 dagen; SVB en toeslagen komen ongevraagd — maar alleen met consent. Erkenningsscenario's eindigen bij een medewerker.",
              "en": "Proactive track before birth; registration within 5 days; SVB and allowances arrive unasked — but only with consent. Recognition cases end with a caseworker."}},
    {"chip": "THK-24 · brug naar het RO-domein", "title": {"nl": "Ik wil bouwen of renoveren", "en": "I want to build or renovate"},
     "body": {"nl": "Vergunningcheck vóór de aanvraag, met de MiniGIM-gebiedscheck als ingredient. De beoordeling en het besluit zijn altijd menselijk (V4); klok: 8 weken regulier.",
              "en": "Permit check before applying, with the MiniGIM area check as ingredient. Assessment and decision are always human (V4); clock: 8 weeks regular."}},
    {"chip": "personas · testbank", "title": {"nl": "Getest door recipes, niet naast ze", "en": "Tested through recipes, not beside them"},
     "body": {"nl": "Lage geletterdheid, andere taal, schulden, bewindsvoering: elke edge case is een persona in de fixture en telt mee in de go/no-go van de testbank.",
              "en": "Low literacy, other language, debt, guardianship: every edge case is a persona in the fixture and counts towards the test bench go/no-go."}},
]


def _fixture_service(fixture_path: Path) -> dict:
    recipe = json.loads((NLDT_ROOT / "recipes" / f"{fixture_path.stem}.json").read_text(encoding="utf-8"))
    return recipe["service"]


def build_pages(stamp: str) -> None:
    template = (HCS_ROOT / "key-demo.template.html").read_text(encoding="utf-8")
    runs = {}
    fixtures = {}
    for path in sorted(LIFE_FIXTURES.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        fixtures[fx["recipeId"]] = {"personas": fx["personas"], "service": _fixture_service(path)}
        runs[fx["recipeId"]] = {}
        for persona in fx["personas"]:
            out = execute_hcs_life_event_run(
                {"recipeId": fx["recipeId"], "persona": persona["id"], "mode": "replay"})
            run = out["run"]
            run["generatedAt"] = stamp_iso(stamp)
            run["runId"] = f"{fx['recipeId']}-{persona['id']}-{stamp}"
            validate_instance(run, "hcs-run.schema.json")
            runs[fx["recipeId"]][persona["id"]] = run
    common = json.loads((HCS_ROOT / "fixtures" / "common.json").read_text(encoding="utf-8"))
    data = {"runs": runs, "fixtures": fixtures, "common": common,
            "i18n": I18N, "scenes": SCENES,
            "selftestVerdicts": {r: {"bias": True, "AI Act risk class": True}
                                  for r in runs}}
    payload = json.dumps(data, ensure_ascii=False)
    for lang, target in LANGS.items():
        html = (template
                .replace("__HCS_DATA__", payload)
                .replace("__LANG__", json.dumps(lang))
                .replace("__BUILD_STAMP__", stamp))
        target.write_text(html, encoding="utf-8")
        print(f"OK page {target.relative_to(NLDT_ROOT)}")
```

En in `main()`, vóór `return 0`:

```python
    if not args.only_runs:
        build_pages(args.stamp)
```

- [ ] **Step 5: Draai de generator en de tests**

Run:

```bash
nldt/.venv/bin/python nldt/simulation/hcs/build_runs.py --stamp 20261009T120000Z
nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v
```

Expected: generator print 8× `OK run` + 2× `OK page`; alle tests PASS (inclusief `TestKeyDemo`).

- [ ] **Step 6: Visuele controle**

Run: `cd nldt/simulation && python3 -m http.server 8091` → open `http://127.0.0.1:8091/hcs-key-demo.html` en `-en.html`.
Controleer: donker palet met oranje accent, selftest-badge `12/12` (mint), persona-switcher wisselt handovers, EN-pagina bevat geen Nederlandse UI-labels. **Daarna visuele gate:** render beide pagina's naar PNG en laat ze beoordelen door de `presentations:visual-judge`-agent (of inspecteer zelf als die niet beschikbaar is) — herstel bij afkeur en her-render.

- [ ] **Step 7: Commit**

```bash
git add nldt/simulation/hcs/key-demo.template.html nldt/simulation/hcs/build_runs.py nldt/simulation/hcs/runs nldt/simulation/hcs-key-demo.html nldt/simulation/hcs-key-demo-en.html nldt/tests/test_hcs.py
git commit -m "feat(nldt): The Key-demo (NL/EN) — vijf stappen, persona-switcher, testbank, KPI-paneel en leerstaat"
```

---

### Task 8: Menu-skelet, indexsectie, README, nldt/04 en mappingdoc

**Files:**
- Create: `nldt/simulation/hcs-menu-demo.html`
- Modify: `nldt/simulation/index.html` (sectie na `id="eindhoven"`)
- Modify: `nldt/simulation/README.md` (tabelrijen)
- Modify: `nldt/04-recipes-and-processes.md` (catalogus + HCS-paragraaf)
- Create: `docs/HCS_RECIPES_AGENTIC_STATE.md`
- Test: `nldt/tests/test_hcs.py` (uitbreiden)

**Interfaces:**
- De menu-demo is statisch (geen build-stap); de 25 THK-kaarten zijn de xlsx-data uit Task 5/§1; de andere vier dishes tonen tel-chips met de verwijzing "fase 2".

- [ ] **Step 1: Schrijf de falende test**

```python
MENU_HTML = NLDT_ROOT / "simulation" / "hcs-menu-demo.html"
INDEX_HTML = NLDT_ROOT / "simulation" / "index.html"
MAPPING_DOC = NLDT_ROOT.parent / "docs" / "HCS_RECIPES_AGENTIC_STATE.md"


def test_menu_demo_lists_all_thk():
    text = MENU_HTML.read_text()
    for code in ("THK-01", "THK-08", "THK-14", "THK-24", "THK-25"):
        assert code in text
    assert "fase 2" in text and "UAM" in text and "GRN" in text


def test_index_links_hcs():
    text = INDEX_HTML.read_text()
    assert 'href="hcs-key-demo.html"' in text and 'href="hcs-menu-demo.html"' in text


def test_mapping_doc_exists_with_mapping_table():
    text = MAPPING_DOC.read_text()
    for marker in ("B1", "poort 1", "hcs-life-event-run", "baselines"):
        assert marker in text
```

- [ ] **Step 2: Draai — moet falen**

- [ ] **Step 3: Menu-demo aanmaken**

`nldt/simulation/hcs-menu-demo.html` — volledige inhoud (zelfde `:root`-palet als Task 7; de 25 THK-rijen komen letterlijk uit het xlsx — code, titel, mode, KPI, lens):

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>HCS · Solutions for Change — het menu (53 recipes, 5 dishes)</title>
<style>
  :root {
    --papier: #f6f8fb; --inkt: #06121b; --inkt-2: #0d1e2c; --ijs: #dff3ff; --ijs-rand: #c4d0da;
    --blauw: #2ba8ff; --hemel: #79c9ff; --oranje: #ff9815; --oranje-donker: #ef8700; --amber: #ffc37e;
    --rood: #e10500; --mint: #1cefa5; --groen: #0f7a4d;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    --sans: Roboto, "Helvetica Neue", system-ui, -apple-system, Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--inkt); color: var(--papier); font-family: var(--sans); line-height: 1.5; padding: 22px clamp(14px, 4vw, 44px) 60px; }
  h1 { font-size: clamp(1.5rem, 3.2vw, 2.2rem); } h1 .dish { color: var(--oranje); }
  .sub { color: var(--hemel); font-family: var(--mono); font-size: .74rem; letter-spacing: .08em; text-transform: uppercase; }
  section { background: var(--inkt-2); border: 1px solid rgba(196,208,218,.25); border-radius: 4px; padding: 16px 18px; margin: 14px 0; }
  h2 { font-size: 1rem; color: var(--oranje); margin-bottom: 10px; }
  .dishes { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
  .dish { border: 1px solid rgba(196,208,218,.25); border-radius: 4px; padding: 12px 14px; }
  .dish h3 { font-size: .95rem; color: var(--hemel); }
  .dish .count { font-family: var(--mono); font-size: .7rem; color: var(--amber); }
  .dish.next { opacity: .75; }
  .dish .fase { font-family: var(--mono); font-size: .64rem; color: var(--ijs); background: rgba(43,168,255,.18); border-radius: 3px; padding: 1px 6px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; margin-top: 10px; }
  .card { border: 1px solid rgba(196,208,218,.2); border-radius: 3px; padding: 8px 10px; font-size: .8rem; }
  .card b { color: var(--oranje); font-family: var(--mono); font-size: .72rem; }
  .card .kpi { display: block; color: var(--ijs); font-size: .74rem; margin-top: 4px; }
  .card .lens { font-family: var(--mono); font-size: .62rem; color: var(--amber); }
  .card.poc { border-color: var(--oranje); }
  .card.poc::after { content: "PoC"; font-family: var(--mono); font-size: .6rem; color: var(--inkt); background: var(--oranje); border-radius: 3px; padding: 0 5px; margin-left: 6px; }
  .stappen { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; font-size: .76rem; }
  .stappen .stap { background: rgba(223,243,255,.06); border: 1px solid rgba(196,208,218,.2); border-radius: 3px; padding: 8px; }
  .stappen .nr { font-family: var(--mono); font-size: .64rem; color: var(--oranje); }
  .rollup { font-size: .84rem; }
  .rollup .trap { border-top: 1px dashed rgba(196,208,218,.3); padding: 6px 0; }
  .rollup .trap b { color: var(--hemel); }
  .cyclus { display: flex; flex-wrap: wrap; gap: 6px; font-size: .78rem; }
  .cyclus span { border: 1px solid var(--ijs-rand); border-radius: 999px; padding: 4px 12px; color: var(--ijs); }
  .voet { font-family: var(--mono); font-size: .66rem; color: #7f93a2; margin-top: 24px; }
  a { color: var(--blauw); }
</style>
</head>
<body>
<div class="sub">Digital Toolbox · Solutions for Change — het menu</div>
<h1><span class="dish">53 recipes</span> over vijf dishes — zelfde recipe-format, testprotocol en KPI-framework</h1>
<p class="sub">Human-Centred Services Blueprint (EDIC-basisplaat) · recipes → KPI's → strategieën → KVI's → outcomes</p>

<section>
  <h2>De vijf dishes — fase 1: The Key uitgewerkt; fase 2: de vier city-dishes</h2>
  <div class="dishes">
    <div class="dish"><h3>The Key</h3><div class="count">25 recipes · human-centred services</div>
      <div class="cards" id="thk-cards"></div></div>
    <div class="dish next"><h3>Urban Air Mobility</h3><div class="count">9 recipes · drones, U-space</div>
      <p style="font-size:.78rem;color:var(--ijs)">UAM-01 medische logistiek · UAM-09 geofencing-zones → <span class="fase">fase 2</span></p></div>
    <div class="dish next"><h3>3-30-300</h3><div class="count">5 recipes · green city, Internet of Nature</div>
      <p style="font-size:.78rem;color:var(--ijs)">GRN-01 canopy-meting · GRN-03 300-meter-gaten → <span class="fase">fase 2</span></p></div>
    <div class="dish next"><h3>Circular neighborhoods</h3><div class="count">9 recipes · materiaalbank en deellaag</div>
      <p style="font-size:.78rem;color:var(--ijs)">CIR-04 gedeelde energie · CIR-01 circulaire voorwaarde → <span class="fase">fase 2</span></p></div>
    <div class="dish next"><h3>15-minute city</h3><div class="count">5 recipes · alles binnen 15 minuten, hubladder</div>
      <p style="font-size:.78rem;color:var(--ijs)">MIN-01 nabijheidsanalyse · MIN-04 hubladder → <span class="fase">fase 2</span></p></div>
  </div>
</section>

<section>
  <h2>De vijf stappen die elke life-event-recipe volgt</h2>
  <div class="stappen">
    <div class="stap"><span class="nr">1</span><br/>Life event &amp; intake — G1</div>
    <div class="stap"><span class="nr">2</span><br/>Solution — G2</div>
    <div class="stap"><span class="nr">3</span><br/>Contract &amp; consent — G3</div>
    <div class="stap"><span class="nr">4</span><br/>Payment &amp; delivery — G4</div>
    <div class="stap"><span class="nr">5</span><br/>Follow-up &amp; value — G5</div>
  </div>
</section>

<section class="rollup">
  <h2>De roll-up: recipes → KPI's → strategieën → KVI's → outcomes</h2>
  <div class="trap"><b>Recipes</b> — 53, over vijf dishes; elf zijn in fase 1/2 als PoC uitgewerkt.</div>
  <div class="trap"><b>KPI's</b> — per recipe output (wat oplevert) en outcome (wat het maatschappelijk doet), met baseline, target, bron en frequentie (<code>recipes/05_KPI-framework_per-recipe.xlsx</code>).</div>
  <div class="trap"><b>Outcome-lens</b> — Z zelfredzaamheid · L leefbaarheid · W resilience; per KPI aangegeven.</div>
  <div class="trap"><b>8 mission strategies</b> — mobiliteit · verwarmen &amp; koelen · wonen · energie · digitaal · bodem &amp; water · biodiversiteit · circulaire economie.</div>
  <div class="trap"><b>3 outcomes → KVI's</b> — zelfredzaamheid · leefbaarheid · resilience.</div>
</section>

<section>
  <h2>Recipe-cyclus (EDIC) en scale path</h2>
  <div class="cyclus"><span>1 Design</span><span>2 Test — GenAI-testbank</span><span>3 Adopt</span><span>4 Publish — open recipe book</span><span>5 Localise</span><span>6 Measure &amp; improve — leerstaat</span></div>
  <p style="font-size:.8rem;color:var(--ijs);margin-top:10px">Scale path: <b>Start</b> 1 recipe · 1 stad · 100 inwoners → <b>Pilot</b> 15 recipes · 4 steden · 10.000 inwoners → <b>Schaal</b> alle steden · 300M Europeanen.</p>
</section>

<p class="voet">HCS fase 1 · bronnen: recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf · recipes/05_KPI-framework_per-recipe.xlsx · <a href="hcs-key-demo.html">The Key-demo</a> · index: <a href="index.html">nldt/simulation</a></p>
<script>
var THK = [
  ["THK-01","Ik wil trouwen","reactive · publiek-privaat","Lead time aangeef→trouwen geregistreerd","Z"],
  ["THK-02","Ik krijg een kind","reactive → proactive","Geboorteregistraties digitaal","—"],
  ["THK-03","Ik wil studeren","reactive · keten","Tijd inschrijving→alles geregeld","Z"],
  ["THK-04","Ik wil in het buitenland studeren","reactive · keten · cross-border","Bewijsstukken via OOTS uitgewisseld","—"],
  ["THK-05","Ik wil werk vinden","reactive · publiek-privaat","Uitstroom naar werk binnen 6 maanden","Z"],
  ["THK-06","Ik wil een bedrijf starten","proactive · publiek-privaat","Doorlooptijd idee→bedrijf operationeel","Z"],
  ["THK-07","Ik wil een huis kopen","reactive · privaat met publieke stappen","Hypotheekbewijs uit de bron","—"],
  ["THK-08","Ik ga verhuizen","reactive · publiek-privaat","Verhuizingen zonder handmatige afhandeling","Z"],
  ["THK-09","Ik wil rijden","reactive · publiek-privaat","Rijbewijsaanvragen digitaal gestart","—"],
  ["THK-10","Ik wil reizen","reactive · publiek-privaat","Verlopende documenten op tijd gesignaleerd","—"],
  ["THK-11","Ik wil een ID","reactive · publiek","Aanvragen na proactief signaal","—"],
  ["THK-12","Ik wil een bankrekening openen","reactive · privaat","Rekeningen geopend met wallet-identificatie","—"],
  ["THK-13","Ik wil mijn belastingen betalen","reactive · publiek","Automatische kwijtschelding wie daar recht op heeft","Z"],
  ["THK-14","Ik wil sociale ondersteuning","reactive · publiek · 4 varianten","Non-take-up: recht hebben maar niets ontvangen","Z"],
  ["THK-15","Ik wil zorg","reactive · publiek-privaat","Doorlooptijd aanvraag→zorg geleverd","Z"],
  ["THK-16","Ik wil een geschil oplossen","reactive · publiek · 3 varianten","Geschillen informeel opgelost","Z"],
  ["THK-17","Ik wil stemmen","proactive · publiek","Opkomst","L"],
  ["THK-18","Ik wil vrijwilligerswerk doen","proactive · publiek-privaat","Actieve vrijwilligers","L Z"],
  ["THK-19","Ik wil met pensioen","proactive · keten","AOW zonder vertraging aangevraagd","Z"],
  ["THK-20","Ik wil een afscheid regelen","reactive · publiek-privaat","Partijen geïnformeerd via één notificatie","—"],
  ["THK-21","Ik wil hier een leven opbouwen","reactive · publiek · nieuw","Nieuwkomers binnen de termijn","Z"],
  ["THK-22","Ik wil iets organiseren","proactive · publiek · nieuw","Doorlooptijd aanvraag→besluit","—"],
  ["THK-23","Ik heb een idee voor mijn stad","proactive · publiek · nieuw","Ideeën uitgevoerd","L"],
  ["THK-24","Ik wil bouwen of renoveren","reactive · publiek-privaat · nieuw","Besluit binnen 8 weken (regulier)","—"],
  ["THK-25","Ik wil steun bij opvoeden","reactive → proactive · publiek · nieuw","Gezinnen geholpen met lichte steun, zonder doorverwijzing","Z"]
];
var POC = {"THK-08":"hcs-key-demo.html","THK-02":"hcs-key-demo.html","THK-24":"hcs-key-demo.html"};
var box = document.getElementById("thk-cards");
THK.forEach(function (r) {
  var d = document.createElement("div");
  d.className = "card" + (POC[r[0]] ? " poc" : "");
  d.innerHTML = "<b>" + r[0] + "</b> " + r[1] + "<span class='kpi'>" + r[3] + "</span>" +
    "<span class='lens'>" + r[2] + " · lens " + r[4] + "</span>" +
    (POC[r[0]] ? "<br/><a href='" + POC[r[0]] + "'>→ PoC-demo</a>" : "");
  box.appendChild(d);
});
</script>
</body>
</html>
```

- [ ] **Step 4: Indexsectie toevoegen**

In `nldt/simulation/index.html`, direct **na** de afsluitende `</section>` van `id="eindhoven"`, invoegen:

```html
    <section class="poc" id="hcs">
      <h2>Human-Centred Services (EDIC)</h2>
      <p>Life events als reusable recipes: The Key uitgewerkt als PoC (THK-08 · THK-02 · THK-24), met GenAI-testbank, mens-agent-grens en KPI-baseline. Fase 2 voegt UAM, 3-30-300, Circular en 15-minute city toe.</p>
      <div class="demos">
        <a class="demo" href="hcs-key-demo.html"><div class="t">The Key-demo</div><div class="d">vijf stappen · personas · testbank · KPI's (NL)</div></a>
        <a class="demo" href="hcs-key-demo-en.html"><div class="t">The Key demo (EN)</div><div class="d">five steps · personas · test bench · KPIs</div></a>
        <a class="demo" href="hcs-menu-demo.html"><div class="t">Menu — 53 recipes, 5 dishes</div><div class="d">de blueprint-plaat interactief · roll-up naar KVI's</div></a>
      </div>
    </section>
```

(Controleer de exacte class-namen in `index.html` — `demos/demo/t/d` conform de bestaande secties; het `class="demos"`-blok moet identiek aan de buursecties opgebouwd worden.)

- [ ] **Step 5: README- en 04-rijen**

In `nldt/simulation/README.md`, onder de agentic-state-rij in de sectie-tabel (of als eigen subsection "Human-Centred Services (EDIC) — fase 1"):

```markdown
## Human-Centred Services — EDIC recipe PoC's (fase 1)

[`hcs-key-demo.html`](hcs-key-demo.html) (NL) ·
[`hcs-key-demo-en.html`](hcs-key-demo-en.html) (EN) — The Key als recipe-PoC: vijf
blueprint-stappen als deterministische replay (`hcs-life-event-run`), persona-switcher
met edge cases, GenAI-testbank, KPI-baseline en leerstaat. Ontwerp:
[`docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md`](../../docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md).
Herbouwen:

```bash
nldt/.venv/bin/python nldt/simulation/hcs/build_runs.py --stamp <ISO-stamp>
```

[`hcs-menu-demo.html`](hcs-menu-demo.html) — het menu: 53 recipes over vijf dishes
(THK volledig als kaarten; de city-dishes in fase 2), vijf stappen × G1–G5,
roll-up naar KVI's, recipe-cyclus en scale path.
```

In `nldt/04-recipes-and-processes.md`, in de tabel "PoC / lake recipe catalogue" drie rijen toevoegen:

```markdown
| `thk-08-move-home` / `thk-02-having-a-baby` / `thk-24-build-renovate` | medium / medium / high | `hcs-life-event-run` |
```

En na de alinea over "PoC MCP tools usually alias one process…" deze paragraaf:

```markdown
### Human-Centred Services recipes (EDIC)

De The Key-life-events uit de [HCS Blueprint](../../recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf)
landen als gewone recipes met een optioneel `service`-blok (EDIC-anatomy: dish,
menselijke maat, G1–G5-testpunten, KPI's). Baselines (Sitra-poort 1+5) staan in
`recipes/baselines/`. Koppeltabel: [`docs/HCS_RECIPES_AGENTIC_STATE.md`](../HCS_RECIPES_AGENTIC_STATE.md).
```

- [ ] **Step 6: Mappingdoc aanmaken**

`docs/HCS_RECIPES_AGENTIC_STATE.md` — volledige inhoud:

```markdown
# HCS-recipes × Agentic State — koppeltabel

| | |
|---|---|
| Document | `docs/HCS_RECIPES_AGENTIC_STATE.md` · v1.0 · 2026-10-09 · fase 1: The Key; fase 2 (UAM, 3-30-300, Circular, 15-minute city) vult de city-tabellen aan |
| Bronnen | [`recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf`](../recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf) · [`recipes/05_KPI-framework_per-recipe.xlsx`](../recipes/05_KPI-framework_per-recipe.xlsx) |
| Kaders | [`AGENTIC_STATE_PLAN.md`](AGENTIC_STATE_PLAN.md) v1.2 (Sitra B1–B14, vijf poorten) · [The Agentic State](https://agenticstate.org/paper.html) (12 lagen, L0–L5) |
| Scope | de conformiteitsverklaring van de HCS-recipe-PoC's: elk blueprint-element gekoppeld aan Sitra-block, poort, laag en landingsplaats in dit repo |

## 1. Blueprint-element → agentic state → landingsplaats

| Blueprint-element | Sitra-block | Poort | Whitepaper-laag | Landingsplaats |
|---|---|---|---|---|
| Life event als gedeeld niveau | B1 | — | 2 Government workflows | `nldt/recipes/thk-*.json` (`service.lifeEventCode`) |
| Vijf stappen (intake → follow-up) | B2 (−1 workflow) | — | 2 | steps in het run-artefact (`hcs-run.schema.json`) |
| Menselijke maat / handover | B8 | 3 | 2, 7 | `service.humanMeasure` + `steps[].actor`/`handover` |
| GenAI-testbank G1–G5 + personas | B8, B9 | 3, 5 | 4 Compliance | `service.genAiTestPoints`, testbank-paneel in de demo's |
| KPI-framework (baseline/target/actual) | B9 | 1, 5 | 11→n.v.t., 12 | `recipes/baselines/<id>.baseline.json` |
| Herontwerp vóór technologie ("welke stap verdwijnt") | B5 | 1 | 2 | `baselines[].disappearingStep` |
| Gedeelde betekenis: BRP, EUDI, PDC, autoritatieve bronnen | B6 | 2 | 8 Data & privacy | `steps[].prov.sources[]` |
| MijnServices + Common Ground als ingredients | B7, B11 | 4 | 9 Tech stack | `requiredProcesses`, `fixtures/common.json` |
| Recipe-formaat zelf (anatomy) | B11, B12 | 4 | 9 | `service`-blok in `nldt/schemas/recipe.schema.json` |
| Recipe-cyclus, measure & improve | B10, B13 | 5 | 12 People | `learningState[]` + leerstaat-strip in de demo's |
| EDIC adopteert plaat, format, testprotocol | B13 (steward) | — | 6 Procurement (kanaal) | `nldt/recipes/edic-asset-map.json` |

## 2. Mens-agent-grens per The Key-PoC (poort 3)

| Recipe | Stap | Actor | Overname-moment (uit The Key × PDC) |
|---|---|---|---|
| THK-08 | intake / delivery | agent → mens | Adresonderzoek bij twijfel → medewerker Burgerzaken |
| THK-08 | follow-up | agent → mens | Schuldsignaal → wijkteam sociaal domein (THK-14) |
| THK-02 | intake / delivery | agent → mens | Erkenning, buitenlandse ouder → medewerker |
| THK-24 | solution | agent → mens | Beschermd gezicht → vergunningverlener (uitgebreide procedure) |
| THK-24 | delivery | **mens** | Beoordeling en besluit altijd door de vergunningverlener (doctrine) |

## 3. Stopcondities en go/no-go (poort 5)

Per recipe in `nldt/recipes/baselines/<id>.baseline.json` — zelfde regels als de
testbank-assen (accuracy, plain language, once-only, explainability, human handover,
bias, AI Act risk class). De demo's tonen de uitslagen per persona.

## 4. Positie in het plan

Deze PoC's zijn de eerste *function-instanties* van het AGENTIC_STATE_PLAN (beslispunt
"volgende stap"): de functie als expliciet artefact (B1), baselines als first-class
artefacten (poort 1) en stopcondities in de run-reportage (poort 5) — precies de twee
nieuwe artefacten die het plan §3 noemt.
```

- [ ] **Step 7: Draai — moet slagen**

Run: `nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py -v`
Expected: PASS (alle tests).

- [ ] **Step 8: Commit**

```bash
git add nldt/simulation/hcs-menu-demo.html nldt/simulation/index.html nldt/simulation/README.md nldt/04-recipes-and-processes.md docs/HCS_RECIPES_AGENTIC_STATE.md nldt/tests/test_hcs.py
git commit -m "docs(nldt): HCS-menu, indexsectie, README/04-rijen en agentic-state-koppeltabel (fase 1)"
```

---

### Task 9: Volledige suite, handmatige check en afronding

**Files:**
- Geen nieuwe bestanden; alleen verificatie en (indien nodig) fixes.

- [ ] **Step 1: Volledige nldt-suite**

Run: `nldt/.venv/bin/python -m pytest nldt/tests -q`
Expected: alle tests PASS, nul failures. Bij falen: fix vóór verdergaan; alleen de eigen bestanden aanpassen.

- [ ] **Step 2: Demo's handmatig openen**

Run: `cd nldt/simulation && python3 -m http.server 8091` → open `index.html` (HCS-sectie zichtbaar), `hcs-key-demo.html`, `hcs-key-demo-en.html`, `hcs-menu-demo.html`.
Expected: selftest-badge 12/12; persona-switcher werkt; EN-pagina volledig Engels in de UI-labels; menu toont 25 THK-kaarten waarvan 3 met PoC-markering.

- [ ] **Step 3: Visuele gate**

Render de vier pagina's naar PNG (headless screenshot) en laat ze beoordelen door de `presentations:visual-judge`-agent: paletconsistentie (donker + oranje), leesbaarheid, geen overlopers. Bij afkeur: herstel in template/generator en her-runs van Task 7-stap 5.

- [ ] **Step 4: Slot-commit**

```bash
git status --short
# verwacht: alleen ongecommitte generatie-artifacten indien herbouwd; commit ze:
git add nldt/simulation/hcs/runs nldt/simulation/hcs-key-demo.html nldt/simulation/hcs-key-demo-en.html
git commit -m "chore(nldt): HCS-runs en pagina's hergebouwd na visuele ronde" --only nldt/simulation/hcs/runs nldt/simulation/hcs-key-demo.html nldt/simulation/hcs-key-demo-en.html
```

Als `git status --short` leeg is voor deze paden: geen commit nodig.

---

## Buiten dit plan (fase 2, eigen plan)

De acht city-recipes (UAM-01/09, GRN-01/03, CIR-01/04, MIN-01/04) met city-fixtures, `hcs-recipe-run` in productie, de vier dish-demo's, de volledige menu-demo en de volledige mappingdoc — conform spec §6 fase 2, te plannen na oplevering en review van fase 1.

---

## Executiestatus (9 oktober 2026)

Fase 1 is uitgevoerd en afgerond: 10 commits `3fded7a..c337eef` op main, alle negen taken door subagent-implementatie met per-taak review en een whole-branch-eindreview (verdict **Ready** na fixwave `c337eef`). Suite 432 passed; visuele gate 4/4. Gedocumenteerde deviaties op het plan: (1) `readiness` in de EDIC-entries `"hybrid"` i.p.v. `"demo"` — de schema-enum kent alleen mock|hybrid|live; (2) `execute_hcs_recipe_run` resolveert de fixture-map als `(fixture_dir or HCS_FIXTURES) / "city"` — de brief was intern inconsistent, productiepad onveranderd; (3) determinisme-test vergelijkt twee runs over aparte outdirs (plan-voorbeeldtest vergeleek een bestand met zichzelf — Global Constraint gouverneert); (4) testbank rendert tri-state go / nog-niet-getoetst / geen-go i.p.v. default-go; (5) EN-pagina `lang="en"` via generator; (6) kleine correcties op brief-typo's (thk-02-JSON-haakje, `relative_to`-fallback, G-range-beschrijvingen). Deferred minors staan in `.superpowers/sdd/progress.md`. Fase 2 (city dishes) krijgt een eigen plan.
