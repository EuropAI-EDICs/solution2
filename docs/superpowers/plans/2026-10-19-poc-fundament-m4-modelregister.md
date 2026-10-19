# PoC-fundament M4 Implementatieplan (modelregister + transport-bruggen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het modelregister (BB13-patroon) maakt de computation-tools van het manifest koppelbaar aan hun transports: het minigim-model is geregistreerd én bewezen bereikbaar via **OGC API Processes** (nldt process-adapter) en **A2A** (Agent Card-catalogus), met versie-pinnen, riskLevel en PROV-verwijzingen.

**Architecture:** `poc-fundament/fundament/models.py` + schema laden/valideren `poc-minigim/modelregister.json` (drie modellen: de gebiedscheck-run met processes+a2a-transports, de ILS-classificatie en de proxy-derivaties in-process). De generator koppelt de manifest-computation-tasks aan register-refs (`model:…`); conformance-tests bewijzen dat elke `model:`-ref resolvet en dat de gedeclareerde transports werkelijk bestaan in de repo (processId in de process-adapter, agent-id/recipes/port in de a2a-catalogus, riskLevel gelijk aan het recipe). Een verify-tool voert de echte processes-replay uit.

**Tech Stack:** Python (stdlib + jsonschema), unittest offline suites; nldt process-adapter alleen in het verify-tool (handmatig, `PYTHONPATH=nldt`).

**Spec:** `docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md` §11 **M4**. **Gedocumenteerde deviatie op de exit-formulering:** de spec zegt "een extern rekenmodel aanroepbaar via beide transports" — een extern rekenmodel bestaat nog niet (GREX is een fase-2-haak; toolbox-modellen zijn nog niet ontsloten). M4 levert daarom het register + beide transports bewezen op het eerste (interne) model, en is de registratie-aanzet: een extern model wordt later alleen een register-entry met een a2a-transport (Agent Card), geen codewijziging.

## Global Constraints

- **Dependency-richting:** `fundament.models` importeert nooit deep-agents/poc/nldt (wordt gecontroleerd door de bestaande `test_deps.py`).
- **Golden-veilig:** het fase-manifest en de modelregister zitten niet in de golden-set; de M2-golden-test blijft onaangetast groen. De manifest-regeneratie moet byte-deterministisch blijven (twee runs → identieke bytes).
- **Pinnen raken we niet aan:** `registry/*`, `data/sources.json`, `nldt/recipes/minigim-gebiedscheck.json`, `a2a-simulation/catalog/poc-agents.json` en `nldt/services/process_adapter/poc_handlers.py` worden alleen **gelezen**, nooit gewijzigd — het register bewijst tegen die bronnen aan.
- **Offline suites groen:** poc-fundament (`cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q`) en poc-minigim (`cd poc-minigim && …`) blijven volledig groen (bestaande skips blijven skips).
- **Gebruikers-werkboom:** deep-agents/README.md, deep-agents/laya_router.py, deep-agents/laya_train/ nooit stagen; nooit `git add -A`.
- Commit per taak, Nederlands conventioneel (`feat(fundament): …` / `feat(poc-minigim): …`), direct op `main`.

## Bestandskaart

```
poc-fundament/
  schemas/modelregister.schema.json   NIEUW
  fundament/models.py                 NIEUW — loader + conformance (dubbele ids, schema)
  tests/test_models.py                NIEUW — loader-tests
poc-minigim/
  modelregister.json                  NIEUW — 3 modellen (gebiedscheck-run, ils, proxy-derivaties)
  tests/test_modelregister.py         NIEUW — transport-bestaanbewijs (offline, repo-grepend)
  tools/gen_fase_manifest.py          AANGEPAST — computation-refs → model:refs
  fase-manifest.json                  HERGENEREERD
  tests/test_manifest_conformance.py  AANGEPAST — ref-assertie splitst retrieval/computation
  tools/verify_transports.py          NIEUW — echte processes-replay + a2a-check (handmatig)
  README.md                           AANGEPAST — structuur + verify-commando
docs/
  (poc-fundament/README.md)           AANGEPAST — modelregister-rij
```

---

### Task 1: Modelregister — schema, loader, registratie, transport-bestaanbewijs

**Files:**
- Create: `poc-fundament/schemas/modelregister.schema.json`, `poc-fundament/fundament/models.py`, `poc-fundament/tests/test_models.py`
- Create: `poc-minigim/modelregister.json`, `poc-minigim/tests/test_modelregister.py`
- Modify: `poc-fundament/fundament/__init__.py` (één re-export-regel)

**Interfaces:**
- Produces (taak 2 hangt hieraan): `load_model_registry(path: Path) -> dict` (schema-validatie + dubbele-id-check; raise `ModelRegistryError`), `model_by_id(registry, model_id) -> dict` (raise KeyError), `ModelRegistryError`.

- [ ] **Step 1: Schema** — `poc-fundament/schemas/modelregister.schema.json` (volledig):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldt-toolbox/schemas/modelregister.schema.json",
  "title": "Modelregister: computation-modellen met transports, risico en versie-pinnen",
  "type": "object",
  "required": ["poc", "models"],
  "additionalProperties": false,
  "properties": {
    "poc": { "type": "string", "minLength": 1 },
    "models": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/model" } }
  },
  "$defs": {
    "transport": {
      "type": "object",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": { "enum": ["processes", "a2a", "mcp", "in-process"] },
        "processId": { "type": "string" },
        "handler": { "type": "string" },
        "catalogRef": { "type": "string" },
        "agentId": { "type": "string" },
        "port": { "type": "integer" },
        "agentSkill": { "type": "string" },
        "ref": { "type": "string" },
        "ops": { "type": "array", "items": { "type": "string" } },
        "note": { "type": "string" }
      },
      "allOf": [
        { "if": { "properties": { "type": { "const": "processes" } } },
          "then": { "required": ["processId"] } },
        { "if": { "properties": { "type": { "const": "a2a" } } },
          "then": { "required": ["catalogRef", "agentId"] } }
      ]
    },
    "model": {
      "type": "object",
      "required": ["id", "title", "class", "riskLevel", "version", "transports"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
        "title": { "type": "string", "minLength": 1 },
        "class": { "const": "computation" },
        "riskLevel": { "enum": ["low", "medium", "high"] },
        "version": { "type": "string", "minLength": 1 },
        "sourceVersion": { "type": "object" },
        "prov": { "type": "object" },
        "transports": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/transport" } }
      }
    }
  }
}
```

- [ ] **Step 2: Loader** — `poc-fundament/fundament/models.py` (volledig):

```python
"""Modelregister: computation-modellen + hun transports (BB13-patroon).

Het register declareert welke transports een model heeft (OGC API
Processes, A2A Agent Card, MCP, in-process); de conformance-tests bewijzen
dat de gerefereerde transports werkelijk bestaan (processId in de
process-adapter, agent-id in de a2a-catalogus) — het register claimt niets
wat de repo niet waarmaakt.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "modelregister.schema.json"


class ModelRegistryError(RuntimeError):
    """Modelregister ongeldig tegen het schema, of dubbele model-ids."""


def load_model_registry(path: Path) -> dict:
    """Leest het register, valideert tegen het schema; luide faal."""
    import jsonschema

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(p) for p in exc.absolute_path) or "<top>"
        raise ModelRegistryError(f"{Path(path).name}: {where}: {exc.message[:300]}") from exc
    ids = [m["id"] for m in doc["models"]]
    if len(ids) != len(set(ids)):
        raise ModelRegistryError("dubbele model-ids in het register")
    return doc


def model_by_id(registry: dict, model_id: str) -> dict:
    for m in registry["models"]:
        if m["id"] == model_id:
            return m
    raise KeyError(model_id)
```

En in `poc-fundament/fundament/__init__.py` één regel toevoegen bij de re-exports:

```python
from .models import ModelRegistryError, load_model_registry, model_by_id  # noqa: F401
```

- [ ] **Step 3: Failing loader-tests** — `poc-fundament/tests/test_models.py` (volledig):

```python
"""Modelregister-loader: schema-validatie, dubbele ids, opzoeken."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.models import ModelRegistryError, load_model_registry, model_by_id  # noqa: E402

VALID = {
    "poc": "p",
    "models": [
        {"id": "m1", "title": "M1", "class": "computation", "riskLevel": "low",
         "version": "1.0.0",
         "transports": [{"type": "processes", "processId": "p1"},
                        {"type": "a2a", "catalogRef": "cat.json", "agentId": "a1"}]},
    ],
}


def _write(td: Path, doc) -> Path:
    p = Path(td) / "modelregister.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


class TestModelRegistry(unittest.TestCase):
    def test_geldig_register_laadt(self):
        with tempfile.TemporaryDirectory() as td:
            reg = load_model_registry(_write(Path(td), VALID))
            self.assertEqual(model_by_id(reg, "m1")["title"], "M1")

    def test_processes_zonder_processid_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["transports"][0].pop("processId")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_a2a_zonder_agentid_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["transports"][1].pop("agentId")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_onbekende_risklevel_is_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"][0]["riskLevel"] = "extreem"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_dubbele_ids_zijn_fout(self):
        bad = json.loads(json.dumps(VALID))
        bad["models"].append(json.loads(json.dumps(bad["models"][0])))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ModelRegistryError):
                load_model_registry(_write(Path(td), bad))

    def test_model_by_id_raakt_naast(self):
        with tempfile.TemporaryDirectory() as td:
            reg = load_model_registry(_write(Path(td), VALID))
            with self.assertRaises(KeyError):
                model_by_id(reg, "bestaat-niet")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run fundament-suite — eerst FAIL (module ontbreekt), na implementatie PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_models -v` → verwacht 6 passed; daarna volledige fundament-suite groen (incl. `test_deps` — models.py importeert alleen stdlib+jsonschema).

- [ ] **Step 5: Registratie + transport-bestaanbewijs.** `poc-minigim/modelregister.json` (volledig):

```json
{
 "poc": "minigim-gebiedscheck",
 "models": [
  {
   "id": "minigim-gebiedscheck-run",
   "title": "MiniGIM gebiedscheck (74-item Lijst v0.91 + ILS v0.8 draft)",
   "class": "computation",
   "riskLevel": "low",
   "version": "1.0.0",
   "sourceVersion": {"lijst": "v0.91", "ils": "v0.8"},
   "prov": {
    "recipe": "nldt/recipes/minigim-gebiedscheck.json",
    "handler": "nldt/services/process_adapter/poc_handlers.py::execute_minigim_gebiedscheck_run",
    "note": "deterministisch; PROV via runs/<rid>/prov.json (register-sha256 + per-laag fetch-manifesten); V4 pending by design"
   },
   "transports": [
    {"type": "processes", "processId": "minigim-gebiedscheck-run",
     "handler": "nldt/services/process_adapter/poc_handlers.py"},
    {"type": "a2a", "catalogRef": "a2a-simulation/catalog/poc-agents.json",
     "agentId": "minigim", "port": 9186, "agentSkill": "minigim-gebiedscheck"}
   ]
  },
  {
   "id": "minigim-ils-classificatie",
   "title": "ILS draft-gebiedsindeling (niveaus 0–3, IfcExportAs, EPset_minigim)",
   "class": "computation",
   "riskLevel": "low",
   "version": "v0.8",
   "prov": {"note": "in-process: minigim/ils.py IlsDraftBuilder; draft=true, v4 pending"},
   "transports": [{"type": "in-process", "ref": "register:minigim-ils"}]
  },
  {
   "id": "minigim-proxy-derivaties",
   "title": "Proxy-berekeningen (fsi/gsi/mxi-proxy, CBS oppervlaktegewogen, entropy)",
   "class": "computation",
   "riskLevel": "low",
   "version": "1.0.0",
   "prov": {"note": "in-process: minigim/checklist.py proxy-ops; proxyNote verplicht per item"},
   "transports": [{"type": "in-process", "ops": ["proxy_ratio", "proxy_entropy"], "ref": "run-input"}]
  }
 ]
}
```

En `poc-minigim/tests/test_modelregister.py` (volledig):

```python
"""Modelregister (M4): registratie + transport-bestaanbewijs (offline).

Het register claimt transports; deze suite bewijst ze tegen de repo:
processId letterlijk in de process-adapter, agent-id/recipes/port in de
a2a-catalogus, riskLevel gelijk aan het recipe. Geen netwerk.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from fundament.models import load_model_registry, model_by_id  # noqa: E402


class TestModelRegister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = load_model_registry(ROOT / "modelregister.json")

    def test_processes_transport_bestaat_in_de_process_adapter(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        handler_src = (REPO / "nldt" / "services" / "process_adapter" / "poc_handlers.py"
                       ).read_text(encoding="utf-8")
        for t in (t for t in m["transports"] if t["type"] == "processes"):
            self.assertIn(f'"{t["processId"]}"', handler_src, t["processId"])

    def test_a2a_transport_bestaat_in_de_catalog(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        cat = json.loads((REPO / "a2a-simulation" / "catalog" / "poc-agents.json").read_text(encoding="utf-8"))
        by_id = {a["id"]: a for a in cat["agents"]}
        for t in (t for t in m["transports"] if t["type"] == "a2a"):
            self.assertIn(t["agentId"], by_id, t["agentId"])
            agent = by_id[t["agentId"]]
            self.assertEqual(agent["port"], t["port"])
            self.assertIn(t["agentSkill"], agent["recipes"])

    def test_risklevel_komt_overeen_met_het_recipe(self):
        m = model_by_id(self.reg, "minigim-gebiedscheck-run")
        recipe = json.loads((REPO / "nldt" / "recipes" / "minigim-gebiedscheck.json").read_text(encoding="utf-8"))
        self.assertEqual(m["riskLevel"], recipe["riskLevel"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run beide suites — verwacht PASS**

Run: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest tests.test_modelregister -v` → 3 passed; `cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q` → groen. (De manifest-refs-test komt in taak 2, zodra de generator de `model:`-refs schrijft — zo blijft elke commit met een groene suite.)

- [ ] **Step 7: Commit**

```bash
git add poc-fundament/schemas/modelregister.schema.json poc-fundament/fundament/models.py poc-fundament/fundament/__init__.py poc-fundament/tests/test_models.py poc-minigim/modelregister.json poc-minigim/tests/test_modelregister.py
git commit -m "feat(fundament,poc-minigim): modelregister (schema, loader, registratie) + transport-bestaanbewijs (M4)"
```

---

### Task 2: Manifest-koppeling — computation-refs wijzen naar het modelregister

**Files:**
- Modify: `poc-minigim/tools/gen_fase_manifest.py` (twee regels), `poc-minigim/tests/test_manifest_conformance.py` (ref-assertie rework)
- Modify: `poc-minigim/fase-manifest.json` (hergegenereerd)

**Interfaces:**
- Consumes: `fundament.models.{load_model_registry, model_by_id}` (taak 1).
- Gedrag: F2-`ils-classificatie`-taak krijgt `tool.ref = "model:minigim-ils-classificatie"`; de F3-computation-taken (proxy-ops) krijgen `tool.ref = "model:minigim-proxy-derivaties"`; retrieval-taken blijven op hun serviceRefs. `tool.derive` en classes ongewijzigd; manifest blijft deterministisch.

- [ ] **Step 1: Voeg de manifest-refs-test toe aan `poc-minigim/tests/test_modelregister.py`** (in de `TestModelRegister`-klasse, na `setUpClass`):

```python
    def test_modelrefs_uit_het_manifest_resolven(self):
        manifest = json.loads((ROOT / "fase-manifest.json").read_text(encoding="utf-8"))
        gevonden = 0
        for ph in manifest["phases"]:
            for t in (ph.get("tasks") or []):
                ref = (t.get("tool") or {}).get("ref") or ""
                if ref.startswith("model:"):
                    model_by_id(self.reg, ref[len("model:"):])
                    gevonden += 1
        self.assertGreaterEqual(gevonden, 3, "manifest koppelt minder dan 3 model-refs")
```

- [ ] **Step 2: Rework de ref-assertie in `poc-minigim/tests/test_manifest_conformance.py`.** Vervang de bestaande testmethode `test_tool_ref_komt_overeen_met_servicerefs` door (en voeg bovenaan bij de imports toe: `from fundament.models import load_model_registry, model_by_id`):

```python
    def test_tool_ref_komt_overeen_met_binding_en_modelregister(self):
        models = load_model_registry(ROOT / "modelregister.json")
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t.get("from") != "register:minigim-lijst" or "tool" not in t:
                    continue
                b = self.reg.binding(t["id"])
                if t["tool"]["class"] == "computation":
                    self.assertEqual(t["tool"]["ref"], "model:minigim-proxy-derivaties", t["id"])
                else:
                    verwacht_ref = ",".join(b.get("serviceRefs") or []) or "run-input"
                    self.assertEqual(t["tool"]["ref"], verwacht_ref, t["id"])

    def test_alle_modelrefs_resolven_in_het_modelregister(self):
        models = load_model_registry(ROOT / "modelregister.json")
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                ref = (t.get("tool") or {}).get("ref") or ""
                if ref.startswith("model:"):
                    model_by_id(models, ref[len("model:"):])
```

- [ ] **Step 2: Pas de generator aan** — in `poc-minigim/tools/gen_fase_manifest.py`:
  1. In `_task`, vervang de regel `"ref": ",".join(binding.get("serviceRefs") or []) or "run-input",` binnen de `if binding["status"] in ("auto", "partial")`-tak door:

```python
            "ref": ("model:minigim-proxy-derivaties" if klasse == "computation"
                    else ",".join(binding.get("serviceRefs") or []) or "run-input"),
```

  2. In de F2-skelettaak (`ils-classificatie`) vervang `"ref": "register:minigim-ils"` door `"ref": "model:minigim-ils-classificatie"`.

- [ ] **Step 4: Her genereer + test**

Run: `cd poc-minigim && ../nldt/.venv/bin/python tools/gen_fase_manifest.py && ../nldt/.venv/bin/python -m unittest tests.test_manifest_conformance tests.test_modelregister -v`
Expected: conformance 6 passed (5 bestaande, waarvan de ref-test gereplace + 1 nieuwe), modelregister 4 passed (3 + de nieuwe manifest-refs-test). Daarna volledige poc-minigim-suite + poc-fundament-suite groen; determinisme: twee generaties → identieke bytes (`sha256` vergelijken).

- [ ] **Step 5: Commit**

```bash
git add poc-minigim/tools/gen_fase_manifest.py poc-minigim/fase-manifest.json poc-minigim/tests/test_manifest_conformance.py poc-minigim/tests/test_modelregister.py
git commit -m "feat(poc-minigim): manifest-computation-taken gekoppeld aan het modelregister (M4)"
```

---

### Task 3: Transport-verificatie (echte processes-replay) + docs

**Files:**
- Create: `poc-minigim/tools/verify_transports.py`
- Modify: `poc-minigim/README.md` (structuur-regel + verify-commando), `poc-fundament/README.md` (modelregister-rij)

**Interfaces:**
- Consumes: `fundament.models`, de nldt process-adapter (alleen hier, handmatig — niet in de offline suite).

- [ ] **Step 1: `poc-minigim/tools/verify_transports.py`** (volledig):

```python
#!/usr/bin/env python3
"""Bewijst beide transports van het minigim-model, met PROV-verwijzingen.

  processes : roept de nldt process-adapter aan (replay van de laatste echte
              run) — het resultaat draagt de run-summary met verdict;
  a2a       : verifieert de Agent Card-entry in de catalogus (id, port,
              defaultRecipeId) en pint de catalog-sha256.

Niet onderdeel van de offline suite (de replay pakt de laatste echte run):
    cd poc-minigim && PYTHONPATH=$PWD/../nldt ../nldt/.venv/bin/python tools/verify_transports.py
Schrijft runs/transport-verify.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.models import load_model_registry, model_by_id  # noqa: E402


def main() -> int:
    reg = load_model_registry(ROOT / "modelregister.json")
    m = model_by_id(reg, "minigim-gebiedscheck-run")
    report: dict = {"model": m["id"], "transports": {}}

    proc = next(t for t in m["transports"] if t["type"] == "processes")
    from services.process_adapter.poc_handlers import execute_minigim_gebiedscheck_run
    result = execute_minigim_gebiedscheck_run({"mode": "replay"})
    ok = isinstance(result, dict) and not result.get("error")
    report["transports"]["processes"] = {
        "processId": proc["processId"], "ok": ok, "result": result,
    }

    catalog_path = ROOT.parent / "a2a-simulation" / "catalog" / "poc-agents.json"
    cat = json.loads(catalog_path.read_text(encoding="utf-8"))
    a2a = next(t for t in m["transports"] if t["type"] == "a2a")
    agent = next((a for a in cat["agents"] if a["id"] == a2a["agentId"]), None)
    report["transports"]["a2a"] = {
        "ok": agent is not None,
        "agentId": a2a["agentId"],
        "port": agent["port"] if agent else None,
        "defaultRecipeId": agent["defaultRecipeId"] if agent else None,
        "catalogSha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
    }

    out = ROOT / "runs" / "transport-verify.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    allemaal_ok = all(t["ok"] for t in report["transports"].values())
    print(f"transports: processes={report['transports']['processes']['ok']} "
          f"a2a={report['transports']['a2a']['ok']} → {out}")
    return 0 if allemaal_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Voer het verify-tool uit** (verwacht: de pilot-run van eerdere sessies ligt in `poc-minigim/runs/`; anders eerst een run draaien volgens de poc-README):

```bash
cd poc-minigim && PYTHONPATH=$PWD/../nldt ../nldt/.venv/bin/python tools/verify_transports.py
```
Expected: `transports: processes=True a2a=True → …/runs/transport-verify.json`, exit 0. Faalt de replay omdat er geen run-dir is: draai eerst `../nldt/.venv/bin/python run.py --aoi examples/plangrens-breda-teteringen.28992.geojson --label "M4-transport-proof"` en herhaal. Rapporteer de uitvoer letterlijk.

- [ ] **Step 3: Docs.** In `poc-minigim/README.md`: in de „Structuur"-sectie een regel toevoegen onder `fase-manifest.json`:

```markdown
├── modelregister.json  computation-modellen + transports (processes/a2a/in-process,
│                       riskLevel, versie-pinnen) — bewijs: tests/test_modelregister.py
```

en onder „Run" (na het nLDT-replay-blok):

```markdown
Beide transports van het geregistreerde model bewijzen (replay + catalog-check):

    cd poc-minigim && PYTHONPATH=$PWD/../nldt ../nldt/.venv/bin/python tools/verify_transports.py
```

In `poc-fundament/README.md`: in de module-tabel onder de `matrix.py`-rij toevoegen:

```markdown
| `fundament/models.py` | modelregister-loader (BB13-patroon): computation-modellen + transports, schema-gevalideerd; conformance bewijst transport-bestaan |
```

- [ ] **Step 4: Volledige verificatie + commit**

```bash
(cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
git add poc-minigim/tools/verify_transports.py poc-minigim/README.md poc-fundament/README.md
git commit -m "feat(poc-minigim): transport-verificatietool (processes-replay + a2a) + docs (M4 afronding)"
```

---

## Buiten scope van dit plan

- **M5**: golden-per-fase + V-tool-suite-uitbreiding + tweede pilot-PoC (pilot-keuze is beslispunt 5 in de spec, nog open).
- Externe rekenmodellen registreren (GREX, toolbox-modellen) — de registratie-aanzet is er (alleen een register-entry met a2a-transport), geen codewijziging.
- riskLevel-tiering met een high-voorbeeld: de tiering zelf bestaat al in de nldt-execution-harness; een high-voorbeeld vraagt om een echt high-model en is verschoven naar het moment dat zo'n model zich aanbiedt.
