# PoC-fundament M1+M2 Implementatieplan (MiniGIM-harnas: schema's, registers, binding-executor, byte-identiek bewijs)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw het `poc-fundament/`-package (fase-manifest-schema, registers, binding-executor, matrix-renderer) en zet PoC-5 (`poc-minigim`) erop om met **byte-identieke artefacten** — het bewijsmijlpaal M2 uit de spec.

**Architecture:** De generieke mechaniek uit `poc-minigim/minigim/` (pure derivaties, cache-first fetch, binding-executor, registry-interface) wordt verplaatst naar `poc-fundament/fundament/` met injectiepunten (`cache_dir`, `user_agent`, `fetch_fn`, `ops`, `cbs_filter`); `poc-minigim` importeert terug via een dun compat-shim zodat de bestaande test-seams (`mock.patch.object(clmod, "fetch_layer", …)`) intact blijven. De agent–fase–tool matrix wordt declaratief (`fase-manifest.json`, gegenereerd uit de bestaande bindings) en gerenderd per run.

**Tech Stack:** Python (stdlib-first) via `nldt/.venv`, shapely, pyproj, jsonschema; unittest (geen nieuwe dependencies).

**Spec:** `docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md` — dit plan implementeert **M1 + M2** (§11). M3 (deep-agents-slotgates), M4 (transport-bruggen nldt/a2a) en M5 (golden-per-fase + herdok) krijgen eigen plannen na dit bewijsmijlpaal.

## Global Constraints

- **Dependency-richting (spec §12):** `fundament` importeert nooit `deep-agents` en nooit `poc-minigim`; alleen de andere richting. Afgedwongen in taak 10 met een grep-test.
- **Byte-identiek bewijs (spec §11 M2):** na de refactor produceert de offline fixture-run van PoC-5 canonisch identieke artefacten t.o.v. de vóór-refactor golden (volatile velden `runId`, `generatedAt`, `artifacts` uitgezonderd; `report.html` en `prov.json` volledig uitgesloten — die bevatten per-run tijden/paden).
- **Pinnen raken we niet aan:** `registry/minigim-lijst.json`, `minigim-ils.json`, `lijst-bindings.json`, `data/sources.json` en de xlsx-snapshots blijven byte-identiek (hun sha's zitten in de prov-verhaallijn).
- **Geen LLM in de beslislijn; faal-isolatie per taak:** een falende bron degradeert de taak naar `not-delivered` + risicovlag, breekt nooit de run en fakes nooit.
- **Cache-first, offline tests:** de unittest-suites draaien zonder netwerk (synthetische fixtures); de live-pilot in taak 6/10 draait cache-first.
- **Testcommando's:** fundament: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -v`; poc-minigim: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -v`.
- Commit per taak; commit-bericht in het Nederlands, conventie `feat(fundament): …` / `refactor(poc-minigim): …` / `test(poc-minigim): …`.
- Bestaande PoC's (`poc`, `poc-nspd`, `poc-breda`, …) worden niet aangeraakt.

## Bestandskaart (wat waar komt)

```
poc-fundament/                      NIEUW (M1+M2)
  fundament/
    __init__.py                     publieke API (re-exports)
    manifest.py                     load/validate fase-manifest (V0 op het harnas zelf)
    registers.py                    TaskRegistry (tasks/bindings/bronnen + dekkingscheck)
    derivations.py                  pure derivatie-helpers (verbatim uit minigim/checklist.py)
    fetch.py                        cache-first fetchers (uit minigim/fetch.py; cache_dir/user_agent geïnjecteerd)
    ops.py                          generieke derivatie-ops (echo_input … presence)
    executor.py                     BindingExecutor (generalisatie ChecklistRunner)
    matrix.py                       agent–fase–tool matrix → markdown
  schemas/
    fase-manifest.schema.json
  tests/
    fixtures.py                     kopie van poc-minigim/tests/fixtures.py (synthetisch, generiek)
    mini_registry.py                klein taakregister-fixture voor executor-tests
    test_manifest.py  test_registers.py  test_derivations.py  test_executor.py  test_matrix.py  test_deps.py
  README.md                         (taak 10)

poc-minigim/                        AANGEPAST (M2)
  minigim/__init__.py               sys.path-bridge naar poc-fundament (één punt)
  minigim/fetch.py                  compat-shim (cache_dir+UA gebonden; OGC_FILTER_BREDA verhuist hierheen)
  minigim/registry.py               MiniGimRegistry subclasst fundament TaskRegistry (ILS-deel blijft)
  minigim/checklist.py              ChecklistRunner subclasst BindingExecutor; proxy-ops blijven hier
  minigim/ils.py, report.py, validate.py   ongewijzigd (duck-typing op executor)
  run.py                            ongewijzigd behalve comment
  fase-manifest.json                NIEUW — gegenereerd (taak 8)
  tools/capture_golden.py           NIEUW — gouden offline-run vóór refactor (taak 6)
  tools/compare_runs.py             NIEUW — canonische vergelijking twee runs (taak 6)
  tools/gen_fase_manifest.py        NIEUW — manifest-generator (taak 8)
  tests/test_golden.py              NIEUW — het bewijs zelf (taak 6)
  tests/golden/*.json + layers__*   NIEUW — gouden artefacten (gecommit, taak 6)
```

---

### Task 1: Scaffold `poc-fundament/` + fase-manifest-schema + manifest-loader

**Files:**
- Create: `poc-fundament/fundament/__init__.py`
- Create: `poc-fundament/schemas/fase-manifest.schema.json`
- Create: `poc-fundament/fundament/manifest.py`
- Test: `poc-fundament/tests/test_manifest.py`

**Interfaces:**
- Produces: `fundament.manifest.load_manifest(path: Path) -> dict` (valideert tegen het schema; raise `ManifestError` met locatie-informatie). Later taken (8, 9) roepen dit aan; het schema is het contract uit spec §5.

- [ ] **Step 1: Maak directorystructuur + leeg test-loketje**

```bash
mkdir -p poc-fundament/fundament poc-fundament/schemas poc-fundament/tests
touch poc-fundament/tests/__init__.py
```

`poc-fundament/fundament/__init__.py` (tijdelijk, wordt in taak 4 uitgebreid):

```python
"""PoC-fundament: het MiniGIM-harnas voor PoC's (agent–fase–tool matrix).

Deel van de LDT-toolbox. Dependency-regel: dit package importeert nooit
deep-agents en nooit een poc-package (spec 2026-10-18, §12).
"""
```

- [ ] **Step 2: Schrijf het schema** — `poc-fundament/schemas/fase-manifest.schema.json` (volledig):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldt-toolbox/schemas/fase-manifest.schema.json",
  "title": "Fase-manifest: agent–fase–tool matrix van één PoC",
  "type": "object",
  "required": ["poc", "methodiek", "phases"],
  "additionalProperties": false,
  "properties": {
    "poc": { "type": "string", "minLength": 1 },
    "methodiek": { "type": "string", "minLength": 1,
      "description": "herkenbare methodiek-pin, bv. minigim-v0.91" },
    "aoi": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "schema": { "type": "string" },
        "crs": { "type": "string" }
      }
    },
    "phases": {
      "type": "array", "minItems": 1,
      "items": { "$ref": "#/$defs/phase" }
    }
  },
  "$defs": {
    "agent": {
      "type": "object", "required": ["role"],
      "additionalProperties": false,
      "properties": {
        "role": { "type": "string", "minLength": 1 },
        "llm": { "type": "boolean", "default": false },
        "note": { "type": "string" }
      }
    },
    "tool": {
      "type": "object", "required": ["class", "ref"],
      "additionalProperties": false,
      "properties": {
        "class": { "enum": ["retrieval", "computation", "validation", "report"] },
        "ref": { "type": "string", "minLength": 1,
          "description": "bron-id(s) uit het bronregister, modelregister-ref, of 'run-input'" },
        "transport": { "enum": ["in-process", "processes", "mcp", "a2a"],
          "default": "in-process" },
        "derive": { "type": "array", "items": { "type": "string" } },
        "prov": { "type": "string" }
      }
    },
    "task": {
      "type": "object", "required": ["id", "binding"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "from": { "type": "string", "description": "taakregister-ref, bv. 'register:minigim-lijst'" },
        "binding": { "enum": ["auto", "partial", "manual", "out-of-scope"] },
        "tool": { "$ref": "#/$defs/tool" },
        "manualPointer": { "type": ["string", "null"] },
        "proxyNote": { "type": ["string", "null"] },
        "notes": { "type": "array", "items": { "type": "string" } }
      },
      "allOf": [
        { "if": { "properties": { "binding": { "enum": ["manual"] } } },
          "then": { "required": ["manualPointer"] } },
        { "if": { "properties": { "binding": { "enum": ["auto", "partial"] } } },
          "then": { "required": ["tool"] } }
      ]
    },
    "gate": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "validate": { "type": "array", "items": { "enum": ["V0", "V1", "V2", "V3"] } },
        "hitl": { "type": "string" },
        "onFail": { "type": "string" }
      }
    },
    "phase": {
      "type": "object", "required": ["id", "title", "agent"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^F[0-9]+-[a-z0-9-]+$" },
        "title": { "type": "string", "minLength": 1 },
        "agent": { "$ref": "#/$defs/agent" },
        "tasks": { "type": "array", "items": { "$ref": "#/$defs/task" } },
        "gate": { "$ref": "#/$defs/gate" }
      }
    }
  }
}
```

- [ ] **Step 3: Schrijf de failing test** — `poc-fundament/tests/test_manifest.py` (volledig):

```python
"""Manifest-loader: valide tegen schema; ongeldige manifesten falen luid."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.manifest import ManifestError, load_manifest  # noqa: E402

MINIMAL = {
    "poc": "test-poc",
    "methodiek": "test-v1",
    "phases": [
        {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse",
         "agent": {"role": "poc-specialist"},
         "tasks": [
             {"id": "t1", "binding": "auto",
              "tool": {"class": "retrieval", "ref": "bron:x", "transport": "in-process"}},
             {"id": "t2", "binding": "manual", "manualPointer": "KLIC"},
         ],
         "gate": {"validate": ["V0", "V2"]}},
    ],
}


class TestManifest(unittest.TestCase):
    def test_minimaal_manifest_valideert(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(MINIMAL), encoding="utf-8")
            m = load_manifest(p)
            self.assertEqual(m["poc"], "test-poc")
            self.assertEqual(len(m["phases"]), 1)

    def test_manual_zonder_pointer_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][1].pop("manualPointer")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)

    def test_onbekende_toolklasse_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][0]["tool"]["class"] = "magische-berekening"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)

    def test_auto_zonder_tool_is_fout(self):
        bad = json.loads(json.dumps(MINIMAL))
        bad["phases"][0]["tasks"][0].pop("tool")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(p)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run — verwacht FAIL (module bestaat niet)**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_manifest -v`
Expected: `ModuleNotFoundError: No module named 'fundament.manifest'`

- [ ] **Step 5: Implementeer `fundament/manifest.py`** (volledig):

```python
"""Laadt en valideert een fase-manifest (de agent–fase–tool matrix)."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "fase-manifest.schema.json"


class ManifestError(RuntimeError):
    """Manifest ongeldig tegen fase-manifest.schema.json."""


def load_manifest(path: Path) -> dict:
    """Leest het manifest en valideert tegen het schema; luide faal."""
    import jsonschema

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(p) for p in exc.absolute_path) or "<top>"
        raise ManifestError(f"{Path(path).name}: {where}: {exc.message[:300]}") from exc
    return doc
```

- [ ] **Step 6: Run — verwacht PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_manifest -v`
Expected: `OK` (4 tests)

- [ ] **Step 7: Commit**

```bash
git add poc-fundament
git commit -m "feat(fundament): package-scaffold + fase-manifest-schema + manifest-loader (M1)"
```

---

### Task 2: TaskRegistry — de register-interface (taken, bindings, bronnen)

**Files:**
- Create: `poc-fundament/fundament/registers.py`
- Test: `poc-fundament/tests/test_registers.py`

**Interfaces:**
- Produces: `fundament.registers.TaskRegistry(tasks: list, bindings: list, sources: list)` met `.tasks() -> list[dict]`, `.item(task_id) -> dict`, `.binding(task_id) -> dict`, `.sources_by_id: dict`, `.bindings_by_id: dict`, `.items: dict`, en `.check_complete()` (raise `AssertionError` bij dekkingsgaten). `BindingExecutor` (taak 4) en PoC-5's `MiniGimRegistry` (taak 7) hangen hieraan.
- Contract: de binding-sleutel heet `lijstItemId` (historische naam uit de MiniGIM-Lijst; documentatie in de docstring — geen rename, de registries zijn gepind).

- [ ] **Step 1: Schrijf de failing test** — `poc-fundament/tests/test_registers.py` (volledig):

```python
"""TaskRegistry: dekkingscheck en indexering van taken/bindings/bronnen."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.registers import TaskRegistry  # noqa: E402

TASKS = [{"id": "a"}, {"id": "b"}]
BINDINGS = [
    {"lijstItemId": "a", "status": "auto", "serviceRefs": ["bron-x"]},
    {"lijstItemId": "b", "status": "manual", "manualPointer": "KLIC"},
]
SOURCES = [{"id": "bron-x", "title": "Bron X", "protocol": "ogc-api-features"}]


class TestTaskRegistry(unittest.TestCase):
    def test_indexering_en_toegang(self):
        reg = TaskRegistry(TASKS, BINDINGS, SOURCES)
        self.assertEqual([t["id"] for t in reg.tasks()], ["a", "b"])
        self.assertEqual(reg.item("a")["id"], "a")
        self.assertEqual(reg.binding("b")["status"], "manual")
        self.assertEqual(reg.sources_by_id["bron-x"]["title"], "Bron X")

    def test_binding_zonder_taak_is_inconsistent(self):
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS, BINDINGS + [{"lijstItemId": "spook", "status": "auto"}], SOURCES)

    def test_taak_zonder_binding_is_inconsistent(self):
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS + [{"id": "c"}], BINDINGS, SOURCES)

    def test_onbekende_serviceref_is_inconsistent(self):
        bad = [{"lijstItemId": "a", "status": "auto", "serviceRefs": ["niet-geregistreerd"]}]
        with self.assertRaises(AssertionError):
            TaskRegistry(TASKS[:1], bad, SOURCES)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — verwacht FAIL**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_registers -v`
Expected: `ModuleNotFoundError: No module named 'fundament.registers'`

- [ ] **Step 3: Implementeer `fundament/registers.py`** (volledig):

```python
"""TaskRegistry: geïndexeerde view over taken, bindings en bronnen.

Generalisatie van de checklist-relevantie-helft van poc-minigim
MiniGimRegistry (die hier subclass van wordt en het ILS-deel zelf houdt).
De binding-sleutel heet historisch `lijstItemId` (MiniGIM Omgevingsanalyse
Lijst v0.91); de gepinde registries worden niet hernoemd.
"""

from __future__ import annotations


class TaskRegistry:
    """V2-voorwaarde: elke taak exact één binding; elke serviceRef geregistreerd."""

    def __init__(self, tasks: list, bindings: list, sources: list) -> None:
        self._tasks = list(tasks)
        self.items = {t["id"]: t for t in self._tasks}
        self.bindings_by_id = {b["lijstItemId"]: b for b in bindings}
        self.sources_by_id = {s["id"]: s for s in sources}
        self.check_complete()

    def tasks(self) -> list[dict]:
        return self._tasks

    def item(self, task_id: str) -> dict:
        return self.items[task_id]

    def binding(self, task_id: str) -> dict:
        return self.bindings_by_id[task_id]

    def check_complete(self) -> None:
        missing = set(self.items) - set(self.bindings_by_id)
        extra = set(self.bindings_by_id) - set(self.items)
        if missing or extra:
            raise AssertionError(
                f"bindings/dekking inconsistent — missing={sorted(missing)} extra={sorted(extra)}"
            )
        for b in self.bindings_by_id.values():
            for ref in b.get("serviceRefs", []):
                if ref not in self.sources_by_id:
                    raise AssertionError(
                        f"onbekende serviceRef {ref} in {b['lijstItemId']}"
                    )
```

- [ ] **Step 4: Run — verwacht PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_registers -v`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add poc-fundament
git commit -m "feat(fundament): TaskRegistry met dekkingscheck (M1)"
```

---

### Task 3: Derivatie-helpers + cache-first fetch (verbatim verhuizen, injectiepunten erin)

**Files:**
- Create: `poc-fundament/fundament/derivations.py` (verbatim uit `poc-minigim/minigim/checklist.py:27–115` + `:434–453`)
- Create: `poc-fundament/fundament/fetch.py` (uit `poc-minigim/minigim/fetch.py`, met twee geïnjecteerde parameters)
- Test: `poc-fundament/tests/test_derivations.py`

**Interfaces:**
- Produces: `_geom`, `_clip`, `_current_only`, `_area_m2`, `_length_km`, `_breakdown`, `_histogram`, `_entropy_norm`, `summarize`, `_slugify`, `CBS_SENTINELS` (identieke naam/signatuur/gedrag) en `fetch_layer(source, bbox=None, refresh=False, cbs_filter=None, cache_dir: Path, user_agent: str = …) -> (fc, manifest)` plus `load_aoi(path)` en `FetchError`.
- Belangrijk: `OGC_FILTER_BREDA` verhuist **niet** mee — dat is PoC-specifiek en gaat in taak 7 naar de `minigim/fetch.py`-shim.

- [ ] **Step 1: Verplaats de pure helpers.** Maak `poc-fundament/fundament/derivations.py` met deze kop en verplaats daaronder **ongewijzigd** de genoemde functies (zelfde code, alleen de module-docstring is nieuw):

```python
"""Pure derivatie-helpers: clippen, filteren, statistiek — geen I/O.

Verplaatst (byte-verbatim) uit poc-minigim/minigim/checklist.py; PoC-5
importeert ze terug via de compat-re-exports in minigim/checklist.py.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter

import shapely.geometry as sg
```

Verplaats daarna ongewijzigd uit `poc-minigim/minigim/checklist.py`: `_geom` (r. 27–28), `_clip` (r. 31–49), `_current_only` (r. 52–63), `_area_m2` (r. 66–72), `_length_km` (r. 75–81), `_breakdown` (r. 84–90), `_histogram` (r. 93–99), `_entropy_norm` (r. 102–112), `CBS_SENTINELS` (r. 115), `summarize` (r. 434–447), `_slugify` (r. 450–453). Let op: `summarize` staat daar onderaan met een lege regel; `_slugify` gebruiken de ops in taak 4.

- [ ] **Step 2: Maak `poc-fundament/fundament/fetch.py`.** Kopieer `poc-minigim/minigim/fetch.py` **volledig** en pas exact vier dingen aan:
  1. Module-docstring eerste regel wordt: `"""Sleutelloze open-bron fetchers, cache-first (generalisatie van PoC-5)."""` en de PoC-5-verwijzing in regel 27–28 (`DATA`/`CACHE`/`USER_AGENT`-constante-blok, r. 25–27) vervalt vervangen door:

```python
DEFAULT_USER_AGENT = "ldt-toolbox-fundament/1.0 (poc-fundament fetch)"
```

  2. `OGC_FILTER_BREDA` (r. 32–35) **verwijderen** (verhuist in taak 7 naar de PoC-shim).
  3. `_get` krijgt een user-agent-parameter (r. 46–49 wordt):

```python
def _get(url: str, timeout: int = 60, user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
```

  4. `_cache_key` en `fetch_layer` krijgen een verplicht `cache_dir: Path`:

```python
def _cache_key(cache_dir: Path, source_id: str, fingerprint: str) -> Path:
    # filters (CBS OGC-XML) en bbox'en hashen naar een korte slug — leesbaar
    # en veilig als bestandsnaam
    readable = re.sub(r"[^a-zA-Z0-9_-]+", "-", fingerprint.split(";")[1] if ";" in fingerprint else fingerprint)[:60].strip("-")
    digest = hashlib.sha256(fingerprint.encode()).hexdigest()[:10]
    return cache_dir / f"{source_id}__{readable}-{digest}.28992.geojson"
```

```python
def fetch_layer(source: dict, bbox=None, refresh: bool = False,
                cbs_filter: str | None = None, *,
                cache_dir: Path, user_agent: str = DEFAULT_USER_AGENT):
    """Haalt één laag op (cache-first) en geeft (FeatureCollection, manifest).

    cache_dir is verplicht: het fundament kent geen eigen dataroot — de
    aanroepende PoC bindt zijn eigen cache (en user-agent) zelf.
    cbs_filter: optioneel OGC-XML-filter voor de WFS (protocol-plumbing; de
    filterwaarde is PoC-specifiek).
    """
```

  en in de functie-body: de drie `_get(url)`-aanroepen worden `_get(url, user_agent=user_agent)`; de aanroep `cache_path = _cache_key(source["id"], fingerprint)` wordt `cache_path = _cache_key(cache_dir, source["id"], fingerprint)`; en `CACHE.mkdir(parents=True, exist_ok=True)` wordt `cache_dir.mkdir(parents=True, exist_ok=True)`. Alles anders (protocol-fetchers, manifestvorm, cache-formaat, fingerprint-logica) blijft byte-gelijk — de cache-bestanden moeten uitwisselbaar blijven met de bestaande `poc-minigim/data/cache/`.

- [ ] **Step 3: Schrijf de failing test** — `poc-fundament/tests/test_derivations.py` (volledig):

```python
"""Pure derivaties + fetch-contract (offline: cache_dir is verplicht)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.derivations import (  # noqa: E402
    CBS_SENTINELS,
    _area_m2,
    _breakdown,
    _clip,
    _current_only,
    _entropy_norm,
    _geom,
    _histogram,
    _length_km,
    _slugify,
    summarize,
)
from fundament.fetch import fetch_layer, load_aoi  # noqa: E402

AOI_POLY = [[100000.0, 400000.0], [100500.0, 400000.0], [100500.0, 400500.0],
            [100000.0, 400500.0], [100000.0, 400000.0]]


def _poly(x, y, w=50.0, h=50.0):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]]}


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


class TestDerivations(unittest.TestCase):
    def test_punten_overleven_de_clip(self):
        fc = _fc([
            {"type": "Feature", "properties": {"a": 1}, "geometry": {"type": "Point", "coordinates": [100100, 400100]}},
            {"type": "Feature", "properties": {"a": 2}, "geometry": {"type": "Point", "coordinates": [99000, 39000]}},
        ])
        import shapely.geometry as sg
        clipped, n = _clip(fc, sg.Polygon(AOI_POLY))
        self.assertEqual(len(clipped), 1)
        self.assertEqual(n, 2)

    def test_current_only_filtert_historie_allen_bgt(self):
        fc = _fc([
            {"type": "Feature", "properties": {"eind_registratie": "2020-01-01"}, "geometry": _poly(100000, 400000)},
            {"type": "Feature", "properties": {}, "geometry": _poly(100100, 400000)},
        ])
        out, dropped = _current_only(fc, "pdok-bgt-ogc-api")
        self.assertEqual(dropped, 1)
        self.assertEqual(len(out["features"]), 1)
        out2, dropped2 = _current_only(fc, "pdok-bag-wfs")  # andere bron: onaangetast
        self.assertEqual((dropped2, len(out2["features"])), (0, 2))

    def test_area_length_breakdown_entropy(self):
        feats = [
            {"type": "Feature", "properties": {"functie": "rijbaan"}, "geometry": _poly(100000, 400000, 100, 100)},
            {"type": "Feature", "properties": {"functie": "voetpad"}, "geometry": _poly(100000, 400000, 100, 100)},
            {"type": "Feature", "properties": {"functie": "voetpad"}, "geometry": _poly(100000, 400000, 100, 100)},
        ]
        self.assertEqual(_area_m2(feats), 30000.0)
        self.assertEqual(_entropy_norm(feats, "functie"), 0.9183)  # genormaliseerde entropy 1:2-verhouding, 4 dp
        self.assertEqual(list(_breakdown(feats, "functie")), ["voetpad", "rijbaan"])

    def test_summarize_telt_statussen(self):
        recs = [
            {"bindingStatus": "auto", "deliveredStatus": "delivered", "prioriteit": "hoog", "lijstItemId": "a"},
            {"bindingStatus": "manual", "deliveredStatus": "manual-action", "prioriteit": "hoog", "lijstItemId": "b"},
            {"bindingStatus": "partial", "deliveredStatus": "not-delivered", "prioriteit": "laag", "lijstItemId": "c"},
        ]
        s = summarize(recs)
        self.assertEqual(s["itemCount"], 3)
        self.assertEqual(s["autoCoverageOfHoog"]["delivered"], 1)
        self.assertEqual(s["hoogPrioriteitNotDelivered"], ["b"])

    def test_slugify(self):
        self.assertEqual(_slugify("topografie.hoogte.hoogte-maaiveld"), "topografie-hoogte-hoogte-maaiveld")

    def test_fetch_layer_zonder_cache_dir_is_fout(self):
        with self.assertRaises(TypeError):
            fetch_layer({"id": "x", "protocol": "ogc-api-features", "baseUrl": "https://example.test", "collections": ["c"]})

    def test_cbs_sentinels_bestaan(self):
        self.assertIn(-99999, CBS_SENTINELS)


if __name__ == "__main__":
    unittest.main()
```

Let op: de entropy-verwachtingswaarde — reken hem niet blind na: draai eerst de test; als `0.9183` afwijkt (genormaliseerde entropy over 2 klassen met verhouding 1:2), zet de werkelijke waarde van de run in de assert (determinisme is het punt, niet het exacte decimaal).

- [ ] **Step 4: Run — verwacht eerst FAIL (modules ontbreken), na implementatie PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_derivations -v`
Expected: eerst `ModuleNotFoundError`; na stap 1–2: `OK` (7 tests)

- [ ] **Step 5: Commit**

```bash
git add poc-fundament
git commit -m "feat(fundament): pure derivatie-helpers + cache-first fetch met geïnjecteerde cache_dir/user_agent (M2-voorbereiding)"
```

---

### Task 4: BindingExecutor + generieke ops (het hart van het harnas)

**Files:**
- Create: `poc-fundament/fundament/ops.py`
- Create: `poc-fundament/fundament/executor.py`
- Modify: `poc-fundament/fundament/__init__.py` (re-exports)
- Test: `poc-fundament/tests/fixtures.py` (kopie), `poc-fundament/tests/mini_registry.py`, `poc-fundament/tests/test_executor.py`

**Interfaces:**
- Consumes: `TaskRegistry` (taak 2), `derivations`/`fetch` (taak 3).
- Produces: `fundament.executor.BindingExecutor(registry, aoi_fc, runs_dir, refresh=False, *, fetch_fn, cbs_filter=None, ops: dict)` met methoden `.run() -> list[dict]`, `._execute(item, binding) -> dict` (wordt door PoC-5's V3-validator aangeroepen!), `._layer(service_id, collection=None, cbs=False, use_bbox=True) -> dict`, `._ok(layer) -> bool`, attributen `.aoi_geom`, `.bto_m2`, `.bbox`, `.layer_results`. En `fundament.ops.DEFAULT_OPS` (echo_input, representative_point, clip_layer, clip_stats, count_in_aoi, list_in_aoi, presence). Op-handlers hebben signatuur `handler(ex, rec, binding, item, params)` met `ex` = executor.

- [ ] **Step 1: Kopieer `poc-minigim/tests/fixtures.py` naar `poc-fundament/tests/fixtures.py`** — ongewijzigd (de inhoud is generiek: synthetische lagen + `fake_fetch_layer_factory`).

- [ ] **Step 2: Maak `poc-fundament/tests/mini_registry.py`** (volledig):

```python
"""Klein taakregister voor executor-tests: vier bindingen, drie bronnen.

De bron `pdok-nwb-wegen` + collectie `wegvakken` bestaat ook in
tests/fixtures.py (synthetische NWB-lijn binnen de test-AOI), zodat de
clip-op een echt resultaat heeft.
"""

TASKS = [
    {"id": "t.echo", "thema": "th", "onderdeel": "ond", "item": "echo", "prioriteit": "laag"},
    {"id": "t.clip", "thema": "th", "onderdeel": "ond", "item": "clip", "prioriteit": "hoog"},
    {"id": "t.man", "thema": "th", "onderdeel": "ond", "item": "manual", "prioriteit": "hoog"},
    {"id": "t.broken-op", "thema": "th", "onderdeel": "ond", "item": "broken", "prioriteit": "laag"},
]
BINDINGS = [
    {"lijstItemId": "t.echo", "status": "auto", "serviceRefs": [],
     "derivation": {"op": "echo_input", "params": {}}, "notes": []},
    {"lijstItemId": "t.clip", "status": "auto", "serviceRefs": ["pdok-nwb-wegen"],
     "derivation": {"op": "clip_layer", "params": {"collection": "wegvakken"}}},
    {"lijstItemId": "t.man", "status": "manual", "manualPointer": "bevoegde bron"},
    {"lijstItemId": "t.broken-op", "status": "auto", "serviceRefs": [],
     "derivation": {"op": "bestaat_niet", "params": {}}},
]
SOURCES = [{"id": "pdok-nwb-wegen", "title": "NWB wegvakken", "protocol": "ogc-api-features"}]


def build():
    from fundament.registers import TaskRegistry
    return TaskRegistry(TASKS, BINDINGS, SOURCES)
```

- [ ] **Step 3: Schrijf de failing test** — `poc-fundament/tests/test_executor.py` (volledig):

```python
"""BindingExecutor: auto/manual/broken-bindingen, faal-isolatie, V3-replay-seam."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import mini_registry  # noqa: E402
from fundament.executor import BindingExecutor  # noqa: E402
from fundament.ops import DEFAULT_OPS  # noqa: E402

from tests import fixtures  # noqa: E402


class TestExecutor(unittest.TestCase):
    def _run(self, fetch_fn=None, **kw):
        reg = mini_registry.build()
        fn = fetch_fn or fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn,
                                 ops=DEFAULT_OPS, **kw)
            recs = ex.run()
        return recs

    def test_auto_echo_levert_met_derived_prov(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.echo")
        self.assertEqual(rec["deliveredStatus"], "delivered")
        self.assertEqual(rec["prov"]["protocol"], "derived")
        self.assertIn("btoM2", rec["values"])

    def test_manual_krijgt_pointer_en_geen_getallen(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.man")
        self.assertEqual(rec["deliveredStatus"], "manual-action")
        self.assertEqual(rec["values"]["route"], "bevoegde bron")
        self.assertEqual(rec["prov"], None)

    def test_clip_levert_met_bron_prov_en_laag(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "delivered")
        self.assertEqual(rec["values"]["featureCount"], 1)  # NWB-wegvakkenlijn ligt binnen de AOI
        self.assertTrue(rec["layerRef"].startswith("layers/"))
        self.assertEqual(rec["prov"]["protocol"], "ogc-api-features")

    def test_falende_bron_degradeert_niet_breekt(self):
        real = fixtures.fake_fetch_layer_factory()

        def failing(source, bbox=None, refresh=False, cbs_filter=None):
            if source["id"] == "pdok-nwb-wegen":
                raise RuntimeError("server onbereikbaar")
            return real(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)

        recs = self._run(fetch_fn=failing)
        rec = next(r for r in recs if r["lijstItemId"] == "t.clip")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("server onbereikbaar", " ".join(rec["notes"]))
        # hoog-prioriteitsvlag staat erbij (doctrine: zichtbaar, nooit stil)
        self.assertIn("hoog-prioriteit niet automatisch geleverd", rec["riskFlags"])

    def test_onbekende_op_is_not_delivered_met_note(self):
        recs = self._run()
        rec = next(r for r in recs if r["lijstItemId"] == "t.broken-op")
        self.assertEqual(rec["deliveredStatus"], "not-delivered")
        self.assertIn("onbekende derivation-op", " ".join(rec["notes"]))

    def test_replay_via_execute_is_deterministisch(self):
        reg = mini_registry.build()
        fn = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            ex = BindingExecutor(reg, fixtures.AOI_FC, Path(td), fetch_fn=fn, ops=DEFAULT_OPS)
            first = ex.run()
            again = ex._execute(reg.item("t.clip"), reg.binding("t.clip"))
        base = next(r for r in first if r["lijstItemId"] == "t.clip")
        self.assertEqual(json.dumps(again["values"], sort_keys=True),
                         json.dumps(base["values"], sort_keys=True))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run — verwacht FAIL**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_executor -v`
Expected: `ModuleNotFoundError: No module named 'fundament.executor'`

- [ ] **Step 5: Implementeer `fundament/ops.py`** — de generieke ops uit `minigim/checklist.py`, methodes → functies met `ex` als eerste parameter. Volledig:

```python
"""Generieke derivatie-ops voor de BindingExecutor (retrieval-familie).

Verplaatst uit poc-minigim/minigim/checklist.py (methodes → functies met de
executor als eerste argument). PoC-specifieke ops (bv. proxy_ratio/proxy_entropy
met vaste bron-ids) registreren PoC's zelf naast DEFAULT_OPS.
"""

from __future__ import annotations

from pyproj import Transformer

from .derivations import (_area_m2, _breakdown, _clip, _current_only, _geom,
                          _histogram, _length_km, _slugify)


def op_echo_input(ex, rec, binding, item, params):
    rec["values"] = {
        "btoM2": ex.bto_m2,
        "btoHa": round(ex.bto_m2 / 10000, 2),
        "bbox28992": [round(v, 1) for v in ex.bbox],
        "perimeterM": round(ex.aoi_geom.length, 1),
    }
    rec["layerRef"] = ex._write_layer("plangrens", ex.aoi_fc["features"])
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, None, derived=True)


def op_representative_point(ex, rec, binding, item, params):
    p = ex.aoi_geom.representative_point()
    lon, lat = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True).transform(p.x, p.y)
    rec["values"] = {"rdX": round(p.x, 2), "rdY": round(p.y, 2),
                     "lon": round(lon, 6), "lat": round(lat, 6)}
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, None, derived=True)


def _clip_based(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    colls = params.get("collections") or [params.get("collection") or params.get("typeName")]
    all_feats, src_n, hist = [], 0, 0
    layer = None
    for coll in colls:
        layer = ex._layer(sid, coll)
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"bronlaag {coll} niet beschikbaar: {layer['error']}")
            return
        fc, dropped = _current_only(layer["fc"], sid)
        hist += dropped
        feats, n = _clip(fc, ex.aoi_geom)
        all_feats.extend(feats)
        src_n += n
    feats = all_feats
    values = {"featureCount": len(feats), "sourceFeatureCount": src_n}
    if hist:
        values["historicalObjectsFiltered"] = hist
    cap = (ex.reg.sources_by_id.get(sid) or {}).get("maxFeaturesWithoutPagination")
    if cap is not None and src_n >= cap:
        values["layerCapped"] = True
        rec["notes"].append(
            f"bronlaag server-afgekapt op {cap} features (geen paginering) — dekking kan incompleet zijn"
        )
    if feats:
        g0 = feats[0]["geometry"]["type"]
        if g0 in ("Polygon", "MultiPolygon"):
            values["areaM2"] = round(_area_m2(feats), 1)
            values["areaHa"] = round(values["areaM2"] / 10000, 2)
        elif g0 in ("LineString", "MultiLineString"):
            values["lengthKm"] = round(_length_km(feats), 2)
    field = params.get("field")
    if field == "bouwjaar":
        values["bouwjaarHistogram"] = _histogram(feats, "bouwjaar")
    elif field == "gebruiksdoel":
        values["gebruiksdoelBreakdown"] = _breakdown(feats, "gebruiksdoel")
    elif field == "functie" or "wegdeel" in colls:
        values["functieBreakdown"] = _breakdown(feats, "functie")
    rec["values"].update(values)
    rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


op_clip_layer = op_clip_stats = op_count_in_aoi = _clip_based


def op_list_in_aoi(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    coll = params.get("collection") or params.get("typeName")
    layer = ex._layer(sid, coll)
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
        return
    fc, _dropped = _current_only(layer["fc"], sid)
    feats, src_n = _clip(fc, ex.aoi_geom)
    fields = params.get("fields") or ["ci_citation"]
    rows = [{k: (f.get("properties") or {}).get(k) for k in fields
             if k in (f.get("properties") or {})} for f in feats[:250]]
    rec["values"] = {"count": len(feats), "sourceFeatureCount": src_n,
                     "list": rows, "listCap": 250}
    rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


def op_presence(ex, rec, binding, item, params):
    sid = binding["serviceRefs"][0]
    # bij afstandsbepaling de laag landelijk ophalen (geen bbox-beperking)
    layer = ex._layer(sid, None, use_bbox=not params.get("maxDistanceKm"))
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"bronlaag niet beschikbaar: {layer['error']}")
        return
    feats, _src = _clip(layer["fc"], ex.aoi_geom)
    values = {"overlapFeatureCount": len(feats)}
    if feats and feats[0].get("geometry", {}).get("type") in ("Polygon", "MultiPolygon"):
        values["overlapM2"] = round(_area_m2(feats), 1)
    if params.get("maxDistanceKm"):
        best = None
        for f in layer["fc"].get("features", []):
            if f.get("geometry") is None:
                continue
            d = _geom(f).distance(ex.aoi_geom) / 1000.0
            if best is None or d < best:
                best = d
        values["distanceToNearestKm"] = round(best, 2) if best is not None else None
        values["presence"] = bool(feats)
    rec["values"].update(values)
    if feats:
        rec["layerRef"] = ex._write_layer(_slugify(item["id"]), feats)
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


DEFAULT_OPS = {
    "echo_input": op_echo_input,
    "representative_point": op_representative_point,
    "clip_layer": op_clip_layer,
    "clip_stats": op_clip_stats,
    "count_in_aoi": op_count_in_aoi,
    "list_in_aoi": op_list_in_aoi,
    "presence": op_presence,
}
```

**Correctienota bij verplaatsen:** `_op_clip_based` gebruikte in de origineel-code de Closure over `colls` in de `field == "functie"`-tak — die staat hier exact zo (lokale variabele); niets hernoemen.

- [ ] **Step 6: Implementeer `fundament/executor.py`** — generalisatie van `minigim/checklist.py:118–247`. Volledig nieuw gedrag is alleen de constructor (injectie); de methodes komen verbatim uit het origineel (`self`→`self`, op-lookup via `self.ops`):

```python
"""BindingExecutor: voert taak-bindingen deterministisch uit (faal-isolerend).

Generalisatie van poc-minigim ChecklistRunner (PoC-5). Doctrine:
- binding auto/partial → executor levert, met prov; manual → gedocumenteerde
  mens-route; falen degradeert de taak (not-delivered + risicovlag), breekt
  nooit de run en wordt nooit gefaked;
- alle getallen komen uit derivatie-ops; er zit geen LLM in deze laag.

Injectiepunten:
  fetch_fn   : callable(source, bbox=..., refresh=..., cbs_filter=...) -> (fc, manifest)
  cbs_filter : optioneel protocol-filter dat bij cbs=True wordt doorgegeven
  ops        : dict op-naam -> handler(ex, rec, binding, item, params)
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import shapely.geometry as sg

from .derivations import _geom, _slugify


class BindingExecutor:
    def __init__(self, registry, aoi_fc: dict, runs_dir: Path, refresh: bool = False, *,
                 fetch_fn, cbs_filter: str | None = None, ops: dict):
        self.reg = registry
        self.aoi_fc = aoi_fc
        self.refresh = refresh
        self._fetch_fn = fetch_fn
        self.cbs_filter = cbs_filter
        self.ops = dict(ops)
        self.layers_dir = runs_dir / "layers"
        self.layers_dir.mkdir(parents=True, exist_ok=True)

        polys = [g for f in aoi_fc["features"] for g in self._polys(_geom(f))]
        self.aoi_geom = sg.MultiPolygon(polys) if polys else sg.Polygon()
        self.bto_m2 = round(self.aoi_geom.area, 1)
        self.bbox = self.aoi_geom.bounds
        self.layer_results: dict[str, dict] = {}

    @staticmethod
    def _polys(g):
        if g.geom_type == "Polygon":
            return [g]
        if g.geom_type == "MultiPolygon":
            return list(g.geoms)
        return []

    # ------------------------------------------------------------------ #
    def _layer(self, service_id: str, collection: str | None = None,
               cbs: bool = False, use_bbox: bool = True) -> dict:
        """Bronlaag cache-first ophalen; memoized per (bron, laag, filter, bbox-modus)."""
        key = f"{service_id}::{collection or ''}::{'cbs' if cbs else ''}::{'' if use_bbox else 'nb'}"
        if key in self.layer_results:
            return self.layer_results[key]

        source = dict(self.reg.sources_by_id[service_id])
        if collection:
            if source["protocol"] == "ogc-api-features":
                source["collections"] = [collection]
            elif source["protocol"] == "wfs2":
                source["typeNames"] = [collection]
        bbox = self.bbox if use_bbox else None
        try:
            fc, manifest = self._fetch_fn(
                source, bbox=bbox, refresh=self.refresh,
                cbs_filter=self.cbs_filter if cbs else None,
            )
            res = {"key": key, "fc": fc, "manifest": manifest, "error": None}
        except Exception as exc:  # noqa: BLE001 — faal-isolatie per laag
            res = {"key": key, "fc": None, "manifest": None,
                   "error": f"{type(exc).__name__}: {exc}"}
        self.layer_results[key] = res
        return res

    @staticmethod
    def _ok(layer: dict) -> bool:
        return layer.get("fc") is not None and layer.get("error") is None

    def _write_layer(self, slug: str, features) -> str:
        fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
            "features": features,
        }
        path = self.layers_dir / f"{slug}.28992.geojson"
        path.write_text(json.dumps(fc, ensure_ascii=False) + "\n", encoding="utf-8")
        return f"layers/{path.name}"

    def _set_prov(self, rec, binding, layer: dict, derived: bool = False) -> None:
        item = self.reg.item(binding["lijstItemId"])
        if derived:
            rec["prov"] = {
                "bronRegistratie": "afgeleid van run-input (plangrens)",
                "bronLeverancier": None, "fetchedAt": None, "sha256": None,
                "protocol": "derived", "urls": [],
            }
            return
        m = layer["manifest"]
        rec["prov"] = {
            "bronRegistratie": item.get("bronRegistratie"),
            "bronLeverancier": item.get("bronLeverancier"),
            "fetchedAt": m.get("fetchedAt"),
            "sha256": m.get("sha256"),
            "protocol": m.get("protocol"),
            "urls": m.get("urls"),
        }

    # ------------------------------------------------------------------ #
    def run(self) -> list[dict]:
        return [self._execute(i, self.reg.binding(i["id"])) for i in self.reg.tasks()]

    def _execute(self, item: dict, binding: dict) -> dict:
        rec = {
            "lijstItemId": item["id"],
            "thema": item.get("thema"),
            "onderdeel": item.get("onderdeel"),
            "item": item.get("item"),
            "prioriteit": item.get("prioriteit"),
            "bindingStatus": binding["status"],
            "deliveredStatus": "nvt",
            "values": {},
            "layerRef": None,
            "prov": None,
            "proxyNote": binding.get("proxyNote"),
            "manualPointer": binding.get("manualPointer"),
            "riskFlags": [],
            "notes": list(binding.get("notes", [])),
        }

        if binding["status"] in ("manual", "out-of-scope"):
            rec["deliveredStatus"] = "manual-action" if binding["status"] == "manual" else "nvt"
            if binding["status"] == "manual":
                rec["values"] = {"route": binding.get("manualPointer")}
            self._flag_risks(rec)
            return rec

        op = (binding.get("derivation") or {}).get("op", "none")
        params = (binding.get("derivation") or {}).get("params", {})
        handler = self.ops.get(op)
        if handler is None:
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"runner-fout: onbekende derivation-op {op}")
        else:
            try:
                handler(self, rec, binding, item, params)
            except Exception as exc:  # noqa: BLE001 — faal-isolatie per item
                rec["deliveredStatus"] = "not-delivered"
                rec["notes"].append(f"runner-fout: {type(exc).__name__}: {exc}")
        self._flag_risks(rec)
        return rec

    def _flag_risks(self, rec) -> None:
        if rec.get("prioriteit") == "hoog" and rec["deliveredStatus"] != "delivered":
            rec["riskFlags"].append("hoog-prioriteit niet automatisch geleverd")
```

En `poc-fundament/fundament/__init__.py` wordt (volledig):

```python
"""PoC-fundament: het MiniGIM-harnas voor PoC's (agent–fase–tool matrix).

Deel van de LDT-toolbox. Dependency-regel: dit package importeert nooit
deep-agents en nooit een poc-package (spec 2026-10-18, §12).
"""

from .manifest import ManifestError, load_manifest  # noqa: F401
from .registers import TaskRegistry  # noqa: F401
from .executor import BindingExecutor  # noqa: F401
from .ops import DEFAULT_OPS  # noqa: F401
```

- [ ] **Step 7: Run — verwacht PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -v`
Expected: `OK` (alle fundament-tests: manifest 4 + registers 4 + derivations 7 + executor 6)

- [ ] **Step 8: Commit**

```bash
git add poc-fundament
git commit -m "feat(fundament): BindingExecutor + generieke derivatie-ops (M2-kern)"
```

---

### Task 5: Matrix-renderer (manifest → markdown)

**Files:**
- Create: `poc-fundament/fundament/matrix.py`
- Test: `poc-fundament/tests/test_matrix.py`

**Interfaces:**
- Produces: `fundament.matrix.render_matrix(manifest: dict) -> str` (declaratieve matrix: fase × agent × toolklassen × taakaantallen) en `render_run_matrix(manifest: dict, records: list[dict]) -> str` (idem met per taak de `deliveredStatus` uit de executor-records, gejoind op `lijstItemId`). Deterministisch (geen tijden) — geschikt voor golden-vergelijking en rapport.

- [ ] **Step 1: Schrijf de failing test** — `poc-fundament/tests/test_matrix.py` (volledig):

```python
"""Matrix-renderer: deterministische markdown, fase × agent × tools."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.matrix import render_matrix, render_run_matrix  # noqa: E402

MANIFEST = {
    "poc": "test-poc",
    "methodiek": "test-v1",
    "phases": [
        {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse",
         "agent": {"role": "poc-specialist"},
         "tasks": [
             {"id": "t1", "binding": "auto", "tool": {"class": "retrieval", "ref": "bron:x"}},
             {"id": "t2", "binding": "manual", "manualPointer": "KLIC"},
         ],
         "gate": {"validate": ["V0", "V2"]}},
        {"id": "F3-doorrekening", "title": "Doorrekening",
         "agent": {"role": "poc-specialist"},
         "tasks": [{"id": "t3", "binding": "partial",
                    "tool": {"class": "computation", "ref": "model:mix", "transport": "in-process"}}]},
    ],
}


class TestMatrix(unittest.TestCase):
    def test_bevat_fasen_agenten_en_gates(self):
        md = render_matrix(MANIFEST)
        self.assertIn("F1-omgevingsanalyse", md)
        self.assertIn("poc-specialist", md)
        self.assertIn("retrieval", md)
        self.assertIn("computation", md)
        self.assertIn("V0, V2", md)
        self.assertIn("| 2 |", md)  # taken-aantal F1

    def test_bewijsbindingen_tellen_op(self):
        md = render_matrix(MANIFEST)
        self.assertIn("1 auto", md)
        self.assertIn("1 manual", md)
        self.assertIn("1 partial", md)

    def test_run_matrix_toont_delivered_status(self):
        records = [
            {"lijstItemId": "t1", "deliveredStatus": "delivered"},
            {"lijstItemId": "t2", "deliveredStatus": "manual-action"},
            {"lijstItemId": "t3", "deliveredStatus": "delivered"},
        ]
        md = render_run_matrix(MANIFEST, records)
        self.assertIn("delivered", md)
        self.assertIn("manual-action", md)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — verwacht FAIL**, dan implementeer `fundament/matrix.py` (volledig):

```python
"""Agent–fase–tool matrix: het manifest als leesbare tabel (md)."""

from __future__ import annotations

_BINDINGS = ("auto", "partial", "manual", "out-of-scope")


def _counts(tasks: list[dict]) -> str:
    parts = [f"{sum(1 for t in tasks if t['binding'] == b)} {b}"
             for b in _BINDINGS if any(t["binding"] == b for t in tasks)]
    return ", ".join(parts) if parts else "—"


def _classes(tasks: list[dict]) -> str:
    classes = []
    for t in tasks:
        c = (t.get("tool") or {}).get("class")
        if c and c not in classes:
            classes.append(c)
    return ", ".join(classes) if classes else "—"


def render_matrix(manifest: dict) -> str:
    lines = [
        "| fase | agent | tools | taken | bindingen | gate |",
        "|---|---|---|---|---|---|",
    ]
    for ph in manifest["phases"]:
        tasks = ph.get("tasks") or []
        gate = ph.get("gate") or {}
        gate_txt = ", ".join(gate.get("validate") or [])
        if gate.get("hitl"):
            gate_txt = (gate_txt + " " if gate_txt else "") + f"HITL: {gate['hitl']}"
        agent = ph["agent"]
        agent_txt = agent["role"] + (" (LLM)" if agent.get("llm") else "")
        lines.append(
            f"| {ph['id']} — {ph['title']} | {agent_txt} | {_classes(tasks)} "
            f"| {len(tasks)} | {_counts(tasks)} | {gate_txt or '—'} |"
        )
    return "\n".join(lines) + "\n"


def render_run_matrix(manifest: dict, records: list[dict]) -> str:
    by_id = {r["lijstItemId"]: r for r in records}
    lines = [
        "| fase | taak | binding | tool | status |",
        "|---|---|---|---|---|",
    ]
    for ph in manifest["phases"]:
        for t in ph.get("tasks") or []:
            tool = t.get("tool") or {}
            tool_txt = f"{tool.get('class', '—')}:{tool.get('ref', '—')}" if tool else \
                (t.get("manualPointer") or "—")
            status = by_id.get(t["id"], {}).get("deliveredStatus", "—")
            lines.append(f"| {ph['id']} | {t['id']} | {t['binding']} | {tool_txt} | {status} |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 3: Run — verwacht PASS**

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_matrix -v`
Expected: `OK` (3 tests)

- [ ] **Step 4: Commit**

```bash
git add poc-fundament
git commit -m "feat(fundament): matrix-renderer (agent–fase–tool matrix → markdown) (M1)"
```

---

### Task 6: Bewijsmateriaal vóór de refactor — golden-fixtures, live baseline, vergelijktool

**Files:**
- Create: `poc-minigim/tools/capture_golden.py`
- Create: `poc-minigim/tools/compare_runs.py`
- Create: `poc-minigim/tests/test_golden.py`
- Create: `poc-minigim/tests/golden/*.json`, `layers__*.geojson` (gegenereerd, gecommit)
- Create (buiten repo): `/tmp/m2-baseline/` — live baseline-run (niet committen)

Dit is dé taak die het bewijs mogelijk maakt: alles hier wordt **vóór** de refactor gedaan en gecommit.

**Interfaces:**
- Produces: canon-functie met `VOLATILE = {"runId", "generatedAt", "artifacts"}` — identiek in capture/compare/test; golden-set = `omgevingsanalyse.json`, `ils-draft.json`, `ils-draft.features.28992.geojson`, `validation.json`, `run_summary.json` (alle met canon toegepast, `sort_keys=True, indent=1`) + `layers__<naam>` per laag. `report.html` en `prov.json` vallen bewust buiten de set (bevatten per-run tijden resp. het aoi-pad).

- [ ] **Step 1: Schrijf `poc-minigim/tools/capture_golden.py`** (volledig):

```python
#!/usr/bin/env python3
"""Vangt de offline (fixture) run van PoC-5 als golden-artefacten.

Vóór de M2-refactor draaien en committen — test_golden.py bewijst dat de
refactor byte-identieke (canonische) artefacten oplevert. Volatile velden
(runId, generatedAt) en de artifacts-lijst worden gecanoniseerd; report.html
en prov.json worden bewust uitgesloten (per-run tijden resp. aoi-pad).

Gebruik: ../nldt/.venv/bin/python tools/capture_golden.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run as runmod  # noqa: E402
from minigim import checklist as clmod  # noqa: E402

from tests import fixtures  # noqa: E402

GOLDEN = ROOT / "tests" / "golden"
VOLATILE = {"runId", "generatedAt", "artifacts"}
ARTIFACTS = ("omgevingsanalyse.json", "ils-draft.json",
             "ils-draft.features.28992.geojson", "validation.json", "run_summary.json")


def canon(doc):
    if isinstance(doc, dict):
        return {k: canon(v) for k, v in doc.items() if k not in VOLATILE}
    if isinstance(doc, list):
        return [canon(v) for v in doc]
    return doc


def run_offline(runs_root: Path) -> Path:
    fake = fixtures.fake_fetch_layer_factory()
    aoi = runs_root / "plangrens.geojson"
    aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
    with mock.patch.object(clmod, "fetch_layer", fake):
        rc = runmod.main(["--aoi", str(aoi), "--label", "golden",
                          "--runs-dir", str(runs_root / "runs")])
    assert rc == 0, "offline run faalde — golden kan niet gevangen worden"
    return next((runs_root / "runs").iterdir())


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        run_dir = run_offline(Path(td))
        GOLDEN.mkdir(parents=True, exist_ok=True)
        for old in GOLDEN.iterdir():
            old.unlink()
        for name in ARTIFACTS:
            doc = json.loads((run_dir / name).read_text(encoding="utf-8"))
            (GOLDEN / name).write_text(
                json.dumps(canon(doc), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
        for lf in sorted((run_dir / "layers").glob("*.geojson")):
            (GOLDEN / f"layers__{lf.name}").write_text(lf.read_text(encoding="utf-8"),
                                                       encoding="utf-8")
    n_layers = len(list(GOLDEN.glob("layers__*")))
    print(f"golden: {len(ARTIFACTS)} artefacten + {n_layers} lagen → {GOLDEN}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Draai en commit de golden**

Run: `cd poc-minigim && ../nldt/.venv/bin/python tools/capture_golden.py`
Expected: `golden: 5 artefacten + N lagen → …/tests/golden` (N ≈ 15; exacte waarde hoeft niet vooraf vast te staan, de test vergelijkt de verzameling)

```bash
git add poc-minigim/tests/golden poc-minigim/tools/capture_golden.py
git commit -m "test(poc-minigim): golden-artefacten van de offline fixture-run (vóór M2-refactor)"
```

- [ ] **Step 3: Schrijf `poc-minigim/tests/test_golden.py`** (volledig):

```python
"""M2-bewijs: een verse offline run reproduceert de pre-refactor golden.

Dit is het hart van het bewijsmijlpaal: de refactor (taak 7) mag hier niets
aan breken. Canon-regels identiek aan tools/capture_golden.py.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_golden_core import run_and_canon  # noqa: E402  (zie stap 3b)

GOLDEN = ROOT / "tests" / "golden"
ARTIFACTS = ("omgevingsanalyse.json", "ils-draft.json",
             "ils-draft.features.28992.geojson", "validation.json", "run_summary.json")


class TestGoldenReproductie(unittest.TestCase):
    def test_offline_run_is_canonisch_identiek(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir, canon_dir = run_and_canon(Path(td))
            for name in ARTIFACTS:
                expected = (GOLDEN / name).read_text(encoding="utf-8")
                actual = (canon_dir / name).read_text(encoding="utf-8")
                self.assertEqual(actual, expected, f"artefact wijkt af: {name}")
            exp_layers = sorted(p.name[8:] for p in GOLDEN.glob("layers__*"))
            act_layers = sorted(p.name for p in (run_dir / "layers").glob("*.geojson"))
            self.assertEqual(act_layers, exp_layers, "lagen-set wijkt af")
            for name in exp_layers:
                self.assertEqual(
                    (run_dir / "layers" / name).read_text(encoding="utf-8"),
                    (GOLDEN / f"layers__{name}").read_text(encoding="utf-8"),
                    f"laag wijkt af: {name}")


if __name__ == "__main__":
    unittest.main()
```

En `poc-minigim/tests/test_golden_core.py` (gedeelde run-hulp, volledig):

```python
"""Gedeelde run-hulp voor golden- en vergelijk-tests (offline, stub-fetch)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import run as runmod  # noqa: E402  (test-files zetten sys.path vóór import)
from minigim import checklist as clmod

from tests import fixtures

VOLATILE = {"runId", "generatedAt", "artifacts"}


def canon(doc):
    if isinstance(doc, dict):
        return {k: canon(v) for k, v in doc.items() if k not in VOLATILE}
    if isinstance(doc, list):
        return [canon(v) for v in doc]
    return doc


def run_and_canon(work: Path, label: str = "golden") -> tuple[Path, Path]:
    """Draait de offline run en schrijft canonieke kopieën naar work/canon.

    Geeft (run_dir, canon_dir); de canon-dir bevat dezelfde bestandsnamen.
    """
    fake = fixtures.fake_fetch_layer_factory()
    aoi = work / "plangrens.geojson"
    aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
    with mock.patch.object(clmod, "fetch_layer", fake):
        rc = runmod.main(["--aoi", str(aoi), "--label", label,
                          "--runs-dir", str(work / "runs")])
    assert rc == 0, "offline run faalde"
    run_dir = next((work / "runs").iterdir())
    canon_dir = work / "canon"
    canon_dir.mkdir()
    for name in ("omgevingsanalyse.json", "ils-draft.json",
                 "ils-draft.features.28992.geojson", "validation.json",
                 "run_summary.json"):
        doc = json.loads((run_dir / name).read_text(encoding="utf-8"))
        (canon_dir / name).write_text(
            json.dumps(canon(doc), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return run_dir, canon_dir
```

- [ ] **Step 4: Run de golden-test — verwacht PASS (de code is nog onveranderd)**

Run: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest tests.test_golden -v`
Expected: `OK` (1 test)

- [ ] **Step 5: Live baseline vangen.** Draai de echte pilot cache-first en bewaar de artefacten buiten de repo (niet committen):

```bash
cd /Users/marc/Projecten/ldttoolbox
nldt/.venv/bin/python poc-minigim/run.py \
  --aoi poc-minigim/examples/plangrens-breda-teteringen.28992.geojson \
  --label "M2-baseline" --runs-dir /tmp/m2-baseline
# verwacht: verdict: pass, 29 delivered / 45 manual-action, 3/11 hoog-prioriteit auto
```

- [ ] **Step 6: Schrijf `poc-minigim/tools/compare_runs.py`** (volledig):

```python
#!/usr/bin/env python3
"""Vergelijkt twee PoC-5-runs canonisch (voor/na refactor).

Gebruik: ../nldt/.venv/bin/python tools/compare_runs.py /tmp/m2-baseline/<run> /tmp/m2-na/<run>
Exit 0 = canonisch identiek. report.html/prov.json en de volatile velden
(runId, generatedAt, artifacts) zijn bewust uitgesloten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VOLATILE = {"runId", "generatedAt", "artifacts"}
ARTIFACTS = ("omgevingsanalyse.json", "ils-draft.json",
             "ils-draft.features.28992.geojson", "validation.json", "run_summary.json")


def canon(doc):
    if isinstance(doc, dict):
        return {k: canon(v) for k, v in doc.items() if k not in VOLATILE}
    if isinstance(doc, list):
        return [canon(v) for v in doc]
    return doc


def main() -> int:
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    diffs = []
    for name in ARTIFACTS:
        da = canon(json.loads((a / name).read_text(encoding="utf-8")))
        db = canon(json.loads((b / name).read_text(encoding="utf-8")))
        if da != db:
            diffs.append(name)
    la = sorted(p.name for p in (a / "layers").glob("*.geojson"))
    lb = sorted(p.name for p in (b / "layers").glob("*.geojson"))
    if la != lb:
        diffs.append("layers/set")
    else:
        for n in la:
            if (a / "layers" / n).read_bytes() != (b / "layers" / n).read_bytes():
                diffs.append(f"layers/{n}")
    if diffs:
        print("VERSCHILLEN:", ", ".join(diffs))
        return 1
    print("canonisch identiek ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Commit (tooling; golden zit er al in)**

```bash
git add poc-minigim/tools/compare_runs.py poc-minigim/tests/test_golden.py poc-minigim/tests/test_golden_core.py
git commit -m "test(poc-minigim): golden-reproductietest + canonische run-vergelijker (bewijsmateriaal M2)"
```

---

### Task 7: DE REFACTOR — `poc-minigim` op het fundament (byte-identiek bewijs)

**Files:**
- Modify: `poc-minigim/minigim/__init__.py` (sys.path-bridge)
- Modify: `poc-minigim/minigim/fetch.py` (wordt compat-shim; `OGC_FILTER_BREDA` verhuist hierheen)
- Modify: `poc-minigim/minigim/registry.py` (MiniGimRegistry → subclass TaskRegistry)
- Modify: `poc-minigim/minigim/checklist.py` (wordt ops+subclass; helpers re-exported)
- Test: de volledige bestaande suite + `tests/test_golden.py`

**Interfaces:**
- Consumes: `fundament.executor.BindingExecutor`, `fundament.ops.DEFAULT_OPS`, `fundament.registers.TaskRegistry`, `fundament.derivations.*`, `fundament.fetch.{load_aoi, fetch_layer, FetchError}` (taken 2–4).
- Behoudt exact: `clmod.ChecklistRunner(reg, aoi_fc, runs_dir, refresh=…)` (positie-args!), `clmod.summarize`, `clmod._clip`, `clmod._current_only`, `clmod._geom` (ils.py en de tests gebruiken deze namen), `mock.patch.object(clmod, "fetch_layer", fake)` als werkende seam, `minigim.fetch.{load_aoi, fetch_layer, OGC_FILTER_BREDA, FetchError, DATA, CACHE, USER_AGENT}` (run.py/tests importen deze), `MiniGimRegistry` met `.lijst/.ils/.bindings/.sources`, `.item/.binding/.sources_by_id/.ils_path_labels/.ils_ifc`, `runner._layer/_ok/._execute/.aoi_geom/.bto_m2/.bbox/.layer_results` (ils.py/validate.py/run.py).

- [ ] **Step 1: `poc-minigim/minigim/__init__.py`** — vervang de inhoud door de bridge (één brugpunt, zodat élke import van `minigim.*` — ook in de tests — het fundament kan vinden):

```python
"""PoC-5 MiniGIM-pakket; de generieke mechaniek staat in poc-fundament (M2)."""

import sys
from pathlib import Path

_FUNDAMENT = Path(__file__).resolve().parents[2] / "poc-fundament"
if _FUNDAMENT.is_dir() and str(_FUNDAMENT) not in sys.path:
    sys.path.insert(0, str(_FUNDAMENT))
```

(Als het bestand nu andere inhoud heeft — exports of versie — die regels behouden en de bridge toevoegen.)

- [ ] **Step 2: `poc-minigim/minigim/fetch.py` → compat-shim** (volledige nieuwe inhoud; het origineel is verhuisd naar `fundament/fetch.py` in taak 3):

```python
"""Compat-shim: de fetch-mechaniek staat sinds M2 in fundament.fetch.

Deze shim bindt de PoC-specifieke zaken (cache-locatie, user-agent, het
Breda-CBS-filter) zodat run.py, tests en checklist ongewijzigd blijven.
De cache-bestanden zijn uitwisselbaar met de bestaande data/cache/.
"""

from __future__ import annotations

from pathlib import Path

from fundament.fetch import FetchError, load_aoi  # noqa: F401 — publieke API

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = DATA / "cache"
USER_AGENT = "ldt-toolbox-poc-minigim/1.0 (MiniGIM gebiedscheck)"

OGC_FILTER_BREDA = (
    "<Filter><PropertyIsEqualTo><PropertyName>gemeentenaam</PropertyName>"
    "<Literal>Breda</Literal></PropertyIsEqualTo></Filter>"
)


def fetch_layer(source: dict, bbox=None, refresh: bool = False,
                cbs_filter: str | None = None):
    from fundament import fetch as _f

    return _f.fetch_layer(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter,
                          cache_dir=CACHE, user_agent=USER_AGENT)
```

- [ ] **Step 3: `poc-minigim/minigim/registry.py`** — vervang de klant `MiniGimRegistry`-body: subclass van `TaskRegistry`, de loads en de twee ILS-helpers blijven. Volledige nieuwe inhoud:

```python
"""Laadt en indexeert de MiniGIM-registries (lijst, ILS, bindings, bronnen).

De registries onder registry/ zijn gegenereerd uit de gepinde Excel-artefacten
(zie tools/convert_minigim_xlsx.py) en zijn de norm voor de runner. De
taak-/bindings-/bronnen-mechaniek staat sinds M2 in fundament.registers;
dit bestand houdt de MiniGIM-specifieke delen (ILS-niveaus, pad-labels).
"""

from __future__ import annotations

import json
from pathlib import Path

from fundament.registers import TaskRegistry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"
DATA = ROOT / "data"


def load_lijst() -> dict:
    return json.loads((REGISTRY / "minigim-lijst.json").read_text(encoding="utf-8"))


def load_ils() -> dict:
    return json.loads((REGISTRY / "minigim-ils.json").read_text(encoding="utf-8"))


def load_bindings() -> dict:
    return json.loads((REGISTRY / "lijst-bindings.json").read_text(encoding="utf-8"))


def load_sources() -> dict:
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))


class MiniGimRegistry(TaskRegistry):
    """Geïndexeerde view over lijst + bindings + bronnen + ILS."""

    def __init__(self) -> None:
        self.lijst = load_lijst()
        self.ils = load_ils()
        self.bindings = load_bindings()
        self.sources = load_sources()
        super().__init__(tasks=self.lijst["items"],
                         bindings=self.bindings["bindings"],
                         sources=self.sources["sources"])
        self.ils_nodes = {n["id"]: n for n in self.ils["nodes"]}
        self._path_cache: dict[str, list[str]] = {}

    def tasks(self) -> list[dict]:
        return self.lijst["items"]

    # ------------------------------------------------------------------ #
    def ils_path_labels(self, node_id: str) -> list[str]:
        """Labels van wortel naar knoop (Niveau 0 → …)."""
        if node_id in self._path_cache:
            return self._path_cache[node_id]
        labels: list[str] = []
        nid: str | None = node_id
        while nid is not None:
            node = self.ils_nodes[nid]
            labels.append(node["label"])
            nid = node["parent"]
        labels.reverse()
        self._path_cache[node_id] = labels
        return labels

    def ils_ifc(self, node_id: str) -> str | None:
        """IfcExportAs van de knoop of de dichtstbijzijnde voorouder."""
        nid: str | None = node_id
        while nid is not None:
            node = self.ils_nodes[nid]
            if node.get("ifcExportAs"):
                return node["ifcExportAs"]
            nid = node["parent"]
        return None
```

- [ ] **Step 4: `poc-minigim/minigim/checklist.py`** — vervang de inhoud: proxy-ops blijven (methodes → functies, `self`→`ex`), generic ops komen uit `fundament.ops`, helpers worden re-exported zodat `clmod._clip`/`clmod._current_only`/`clmod._geom`/`clmod.summarize` blijven bestaan. Volledige nieuwe inhoud:

```python
"""PoC-5-checklist: MiniGIM-bindingen op de fundament-executor (M2).

De generieke executie (bindingen, faal-isolatie, lagen, prov) staat in
fundament.executor; hier staan alleen de PoC-specifieke derivaties
(proxy_ratio/proxy_entropy met vaste bron-ids en het Breda-CBS-filter) en de
re-exports die ils.py/tests/run.py gebruiken. Doctrine onveranderd: falen
degradeert, breekt nooit, faket nooit.
"""

from __future__ import annotations

import math

from fundament.derivations import (CBS_SENTINELS, _area_m2, _breakdown, _clip,
                                   _current_only, _entropy_norm, _geom,
                                   _histogram, _length_km, summarize)
from fundament.executor import BindingExecutor
from fundament.ops import DEFAULT_OPS

from .fetch import OGC_FILTER_BREDA, fetch_layer

__all__ = ["ChecklistRunner", "summarize", "_clip", "_current_only", "_geom",
           "OGC_FILTER_BREDA", "fetch_layer"]


def _patchable_fetch(source, bbox=None, refresh=False, cbs_filter=None):
    """Module-global `fetch_layer` blijft de test-seam (mock.patch.object)."""
    return fetch_layer(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter)


class _FetchLayerError(RuntimeError):
    """Bronlaag kon niet worden opgehaald (faal-isolatie per item)."""


def _op_proxy_ratio(ex, rec, binding, item, params):
    stat_field = params.get("statField")
    if stat_field:  # CBS-buurtstatistiek, oppervlaktegewogen
        layer = ex._layer("pdok-cbs-wijkenbuurten-2024", None, cbs=True)
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"CBS niet beschikbaar: {layer['error']}")
            return
        tot_w, tot_a = 0.0, 0.0
        for f in layer["fc"].get("features", []):
            inter = _geom(f).buffer(0).intersection(ex.aoi_geom)
            if inter.is_empty:
                continue
            v = (f.get("properties") or {}).get(stat_field)
            if isinstance(v, (int, float)) and v not in CBS_SENTINELS:
                tot_w += float(v) * inter.area
                tot_a += inter.area
        rec["values"] = {
            "statField": stat_field,
            "estimate": round(tot_w / tot_a, 1) if tot_a else None,
            "method": "oppervlaktegewogen CBS 2024 buurtstatistiek binnen plangrens",
        }
        rec["deliveredStatus"] = "delivered"
        ex._set_prov(rec, binding, layer)
        return

    num = params.get("numerator")
    if num == "vbo_oppervlakte_sum":
        layer = ex._layer("pdok-bag-wfs", "bag:verblijfsobject")
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
            return
        feats, _ = _clip(layer["fc"], ex.aoi_geom)
        area_sum = sum(float((f.get("properties") or {}).get("oppervlakte") or 0) for f in feats)
        rec["values"] = {"fsiProxy": round(area_sum / ex.bto_m2, 4) if ex.bto_m2 else None,
                         "vboOppervlakteM2": round(area_sum, 1)}
    elif num == "begroeid_terreindeel_m2":
        layer = ex._layer("pdok-bgt-ogc-api", "begroeidterreindeel")
        if not ex._ok(layer):
            rec["deliveredStatus"] = "not-delivered"
            rec["notes"].append(f"BGT niet beschikbaar: {layer['error']}")
            return
        fc, _hist = _current_only(layer["fc"], "pdok-bgt-ogc-api")
        feats, _ = _clip(fc, ex.aoi_geom)
        groen = _area_m2(feats)
        rec["values"] = {"gsiProxy": round(groen / ex.bto_m2, 4) if ex.bto_m2 else None,
                         "begroeidTerreindeelM2": round(groen, 1)}
    else:
        raise _FetchLayerError(f"onbekende proxy_ratio {num}")
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


def _op_proxy_entropy(ex, rec, binding, item, params):
    layer = ex._layer("pdok-bag-wfs", "bag:verblijfsobject")
    if not ex._ok(layer):
        rec["deliveredStatus"] = "not-delivered"
        rec["notes"].append(f"BAG niet beschikbaar: {layer['error']}")
        return
    feats, _ = _clip(layer["fc"], ex.aoi_geom)
    rec["values"] = {"mxiProxy": _entropy_norm(feats, params.get("field", "gebruiksdoel")),
                     "method": "genormaliseerde Shannon-entropy van gebruiksdoelen"}
    rec["deliveredStatus"] = "delivered"
    ex._set_prov(rec, binding, layer)


MINIGIM_OPS = {**DEFAULT_OPS,
               "proxy_ratio": _op_proxy_ratio,
               "proxy_entropy": _op_proxy_entropy}


class ChecklistRunner(BindingExecutor):
    """PoC-5-bindingen: zelfde constructor-signatuur als vóór de refactor."""

    def __init__(self, registry, aoi_fc, runs_dir, refresh: bool = False):
        super().__init__(registry, aoi_fc, runs_dir, refresh=refresh,
                         fetch_fn=_patchable_fetch, cbs_filter=OGC_FILTER_BREDA,
                         ops=MINIGIM_OPS)
```

- [ ] **Step 5: Draai de volledige PoC-5-suite — verwacht PASS zonder dat tests wijzigen**

Run: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -v`
Expected: alle bestaande tests groen (checklist, e2e, fetch, ils_validate, indicator_refs, registry) **plus** `test_golden` groen. Als `test_golden` faalt: het verschil lezen (`git diff` levert niets — vergelijk de canon-uitvoer), de oorzaak zit dan in een gewijzigd op-gedrag; NIET de golden aanpassen vóór dat de oorzaak helder is (de golden is het bewijs, geen envelop).

- [ ] **Step 6: Live pilot opnieuw draaien en vergelijken met de taak-6-baseline**

```bash
cd /Users/marc/Projecten/ldttoolbox
nldt/.venv/bin/python poc-minigim/run.py \
  --aoi poc-minigim/examples/plangrens-breda-teteringen.28992.geojson \
  --label "M2-na-refactor" --runs-dir /tmp/m2-na
nldt/.venv/bin/python poc-minigim/tools/compare_runs.py \
  /tmp/m2-baseline/2*-minigim-gebiedscheck /tmp/m2-na/2*-minigim-gebiedscheck
```

Expected: `canonisch identiek ✔` (exit 0). Beide runs draaien cache-first; als de cache in de tussentijd zou zijn gemist, verwijder dan `/tmp/m2-na` en draai opnieuw (de cache in `poc-minigim/data/cache` is leidend).

- [ ] **Step 7: Commit**

```bash
git add poc-minigim
git commit -m "refactor(poc-minigim): checklist/fetch/registry op poc-fundament — byte-identiek bewezen (M2)"
```

---

### Task 8: `fase-manifest.json` voor PoC-5 — generator + conformance-test

**Files:**
- Create: `poc-minigim/tools/gen_fase_manifest.py`
- Create: `poc-minigim/fase-manifest.json` (gegenereerd, gecommit)
- Test: `poc-minigim/tests/test_manifest_conformance.py`

**Interfaces:**
- Consumes: `fundament.manifest.load_manifest` (taak 1), de MiniGIM-registries.
- Produces: manifest met fasen F0-intake (schema-gate), F1-omgevingsanalyse (alle lijst-taken met retrieval-op of manual-pointer), F2-gebiedsindeling (ILS, geen lijst-taken), F3-doorrekening (taken met proxy-ops), F4-synthese (critic/explainer). Mapping: op ∈ {proxy_ratio, proxy_entropy} → F3/computation; anders auto/partial → F1/retrieval; manual/out-of-scope → F1 met manualPointer.

- [ ] **Step 1: Schrijf `poc-minigim/tools/gen_fase_manifest.py`** (volledig):

```python
#!/usr/bin/env python3
"""Genereert poc-minigim/fase-manifest.json uit de bestaande registries.

De matrix is hiermee declaratief: de bindings (taakregister) zijn leidend;
de generator knoopt ze aan fasen/agents/tools volgens de mapping van de
spec (§8). Deterministisch; elke run schrijft dezelfde bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from minigim.registry import MiniGimRegistry  # noqa: E402

RETRIEVAL_OPS = {"echo_input", "representative_point", "clip_layer", "clip_stats",
                 "count_in_aoi", "list_in_aoi", "presence"}
COMPUTATION_OPS = {"proxy_ratio", "proxy_entropy"}


def _task(item: dict, binding: dict) -> dict:
    t = {"id": item["id"], "from": "register:minigim-lijst", "binding": binding["status"]}
    if binding["status"] in ("auto", "partial"):
        op = (binding.get("derivation") or {}).get("op")
        klasse = "computation" if op in COMPUTATION_OPS else "retrieval"
        transport = "in-process"
        t["tool"] = {
            "class": klasse,
            "ref": ",".join(binding.get("serviceRefs") or []) or "run-input",
            "transport": transport,
            "derive": [op] if op else [],
        }
    else:
        t["manualPointer"] = binding.get("manualPointer")
    if binding.get("proxyNote"):
        t["proxyNote"] = binding["proxyNote"]
    if binding.get("notes"):
        t["notes"] = binding["notes"]
    return t


def build() -> dict:
    reg = MiniGimRegistry()
    f1, f3 = [], []
    for item in reg.tasks():
        b = reg.binding(item["id"])
        op = (b.get("derivation") or {}).get("op")
        (f3 if op in COMPUTATION_OPS else f1).append(_task(item, b))
    return {
        "poc": "minigim-gebiedscheck",
        "methodiek": "minigim-v0.91",
        "aoi": {"schema": "geojson", "crs": "EPSG:28992|WGS84"},
        "phases": [
            {"id": "F0-intake", "title": "Intake/scoping",
             "agent": {"role": "intake", "llm": True},
             "tasks": [{"id": "request-schema", "from": "run-input", "binding": "auto",
                        "tool": {"class": "validation", "ref": "schema:OpportunityMapRequest",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0"]}},
            {"id": "F1-omgevingsanalyse", "title": "Omgevingsanalyse (informatie ophalen)",
             "agent": {"role": "minigim-specialist"},
             "tasks": f1,
             "gate": {"validate": ["V0", "V2"], "onFail": "degradeer-taak"}},
            {"id": "F2-gebiedsindeling", "title": "ILS-draft gebiedsindeling",
             "agent": {"role": "geospecialist"},
             "tasks": [{"id": "ils-classificatie", "from": "register:minigim-ils",
                        "binding": "auto",
                        "tool": {"class": "computation", "ref": "register:minigim-ils",
                                 "transport": "in-process", "derive": ["ils_bgt_mapping"]}}],
             "gate": {"validate": ["V1"], "hitl": "draft-keuze (v4 pending by design)"}},
            {"id": "F3-doorrekening", "title": "Doorrekening (rekenmodel aanroepen)",
             "agent": {"role": "minigim-specialist"},
             "tasks": f3,
             "gate": {"validate": ["V3"]}},
            {"id": "F4-synthese", "title": "Synthese & rapport",
             "agent": {"role": "critic + explainer"},
             "tasks": [{"id": "v0-v3-verdict", "from": "run-input", "binding": "auto",
                        "tool": {"class": "validation", "ref": "fundament:validate",
                                 "transport": "in-process"}},
                       {"id": "rapport", "from": "run-input", "binding": "auto",
                        "tool": {"class": "report", "ref": "minigim:report",
                                 "transport": "in-process"}}],
             "gate": {"validate": ["V0", "V1", "V2", "V3"], "hitl": "v4 (mens) pending"}},
        ],
    }


def main() -> None:
    manifest = build()
    out = ROOT / "fase-manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(p.get("tasks") or []) for p in manifest["phases"])
    print(f"fase-manifest: {len(manifest['phases'])} fasen, {n} taken → {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Genereer en schrijf de conformance-test** — `poc-minigim/tests/test_manifest_conformance.py` (volledig):

```python
"""Het manifest beschrijft de werkelijkheid: taak-dekking en binding-gelijkheid."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fundament.manifest import load_manifest  # noqa: E402
from minigim.registry import MiniGimRegistry  # noqa: E402

COMPUTATION_OPS = {"proxy_ratio", "proxy_entropy"}


class TestManifestConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest(ROOT / "fase-manifest.json")
        cls.reg = MiniGimRegistry()

    def test_taakdekking_exact_de_lijst(self):
        ids = [t["id"] for ph in self.manifest["phases"]
               for t in (ph.get("tasks") or []) if t.get("from") == "register:minigim-lijst"]
        self.assertEqual(sorted(ids), sorted(self.reg.items), "lijst-taken kloppen niet")

    def test_bindings_komen_overeen_met_het_register(self):
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t.get("from") != "register:minigim-lijst":
                    continue
                b = self.reg.binding(t["id"])
                self.assertEqual(t["binding"], b["status"], t["id"])
                if t["binding"] in ("auto", "partial"):
                    op = (b.get("derivation") or {}).get("op")
                    self.assertEqual(t["tool"]["derive"], [op] if op else [], t["id"])
                    verwacht = "computation" if op in COMPUTATION_OPS else "retrieval"
                    self.assertEqual(t["tool"]["class"], verwacht, t["id"])

    def test_manual_heeft_altijd_pointer(self):
        for ph in self.manifest["phases"]:
            for t in (ph.get("tasks") or []):
                if t["binding"] == "manual":
                    self.assertTrue(t.get("manualPointer"), t["id"])

    def test_vijf_fasen_met_gate(self):
        self.assertEqual([p["id"] for p in self.manifest["phases"]],
                         ["F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
                          "F3-doorrekening", "F4-synthese"])
        for p in self.manifest["phases"]:
            self.assertIn("gate", p)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Genereer + run**

Run: `cd poc-minigim && ../nldt/.venv/bin/python tools/gen_fase_manifest.py && ../nldt/.venv/bin/python -m unittest tests.test_manifest_conformance -v`
Expected: `fase-manifest: 5 fasen, 79 taken → …` (74 lijst-taken + 5 harnas-taken) en `OK` (4 tests). Het handmatig nagaan (spec M1): open `fase-manifest.json`, controleer steekproefsgewijs 5 bindings tegen `registry/lijst-bindings.json` (bv. `locatie.plangrens` → auto/echo_input/retrieval/run-input; `topografie.hoogte.hoogte-maaiveld` → manual met AHN-pointer; `ruimtelijke-ordening.bestemmingsplan.milieuzone` → partial/presence/retrieval).

- [ ] **Step 4: Commit**

```bash
git add poc-minigim/fase-manifest.json poc-minigim/tools/gen_fase_manifest.py poc-minigim/tests/test_manifest_conformance.py
git commit -m "feat(poc-minigim): fase-manifest (agent–fase–tool matrix) gegenereerd uit de bindings + conformance-test (M1)"
```

---

### Task 9: Matrix in de run — `fase-matrix.md`-artefact (additief)

**Files:**
- Modify: `poc-minigim/run.py` (één import + één schrijfstap; verder niets)
- Test: uitbreiding `poc-minigim/tests/test_e2e.py` — nieuw testgeval

**Interfaces:**
- Consumes: `fundament.matrix.render_matrix`, `render_run_matrix` (taak 5), `fase-manifest.json` (taak 8).
- Produces: per run `fase-matrix.md` (declaratieve matrix + status per taak). `run_summary.json["artifacts"]` krijgt één extra entry (canon-veilig: `artifacts` staat op de VOLATILE-lijst; de golden-set wijzigt niet).

- [ ] **Step 1: Schrijf het failing testgeval** — voeg aan `poc-minigim/tests/test_e2e.py` binnen `TestE2EOffline` toe:

```python
    def test_fase_matrix_artefact(self):
        fake = fixtures.fake_fetch_layer_factory()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            aoi = tmp / "plangrens.geojson"
            aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
            with mock.patch.object(clmod, "fetch_layer", fake):
                runmod.main(["--aoi", str(aoi), "--label", "matrix-test",
                             "--runs-dir", str(tmp / "runs")])
            run_dir = next((tmp / "runs").iterdir())
            md = (run_dir / "fase-matrix.md").read_text(encoding="utf-8")
            self.assertIn("F1-omgevingsanalyse", md)
            self.assertIn("manual-action", md)
            summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
            self.assertIn("fase-matrix.md", summary["artifacts"])
```

- [ ] **Step 2: Run — verwacht FAIL**

Run: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest tests.test_e2e.TestE2EOffline.test_fase_matrix_artefact -v`
Expected: FAIL — `fase-matrix.md` bestaat niet

- [ ] **Step 3: Implementeer in `poc-minigim/run.py`.** Twee aanpassingen:
  1. Bij de andere imports (na `from minigim.registry import MiniGimRegistry`):

```python
from fundament.manifest import load_manifest  # noqa: E402
from fundament.matrix import render_matrix, render_run_matrix  # noqa: E402
```

  2. Na de stap waarin `run_summary` is weggeschreven (dus ná het schrijven van `run_summary.json`, vóór de `print(f"run: …")`), voeg toe:

```python
    # 7b. fase-matrix (agent–fase–tool, declaratief + wat er daadwerkelijk leverde)
    manifest_path = ROOT / "fase-manifest.json"
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        matrix_md = ("## Declaratieve matrix\n\n" + render_matrix(manifest)
                     + "\n## Uitkomst per taak\n\n"
                     + render_run_matrix(manifest, records))
        (runs_dir / "fase-matrix.md").write_text(matrix_md, encoding="utf-8")
        run_summary["artifacts"].append("fase-matrix.md")
        (runs_dir / "run_summary.json").write_text(
            json.dumps(run_summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run de hele suite — verwacht PASS, inclusief `test_golden`**

Run: `cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -v`
Expected: `OK` — de golden wijzigt niet (`artifacts` is canon-volatile; `fase-matrix.md` zit buiten de golden-set)

- [ ] **Step 5: Commit**

```bash
git add poc-minigim/run.py poc-minigim/tests/test_e2e.py
git commit -m "feat(poc-minigim): fase-matrix.md per run — declaratieve matrix + status per taak (M1+M2)"
```

---

### Task 10: Live-verificatie, dependency-regel-test en documentatie

**Files:**
- Create: `poc-fundament/tests/test_deps.py`
- Modify: `poc-minigim/README.md` (structuur + fundament-verwijzing)
- Modify: `docs/MINIGIM.md` (één alinea onder „nLDT-integratie")
- Create: `poc-fundament/README.md`

- [ ] **Step 1: Dependency-regel als test** — `poc-fundament/tests/test_deps.py` (volledig):

```python
"""Dependency-richting (spec §12): fundament importeert nooit deep-agents/poc's."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

VERBODEN = ("deep_agents", "deep-agents", "minigim", "poc", "nldt")


class TestDependencyRichting(unittest.TestCase):
    def test_geen_verboden_imports_in_de_package_brondaad(self):
        hits = []
        for py in (ROOT / "fundament").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), start=1):
                s = line.strip()
                if not (s.startswith("import ") or s.startswith("from ")):
                    continue
                if any(v in s for v in VERBODEN):
                    hits.append(f"{py.relative_to(ROOT)}:{i}: {s}")
        self.assertEqual(hits, [], "fundament mag de agent-/poc-laag niet importeren")


if __name__ == "__main__":
    unittest.main()
```

Run: `cd poc-fundament && ../nldt/.venv/bin/python -m unittest tests.test_deps -v` → Expected: `OK`

- [ ] **Step 2: Live eindverificatie** — beide suites groen + live pilot nogmaals canonisch identiek:

```bash
cd /Users/marc/Projecten/ldttoolbox
(cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
nldt/.venv/bin/python poc-minigim/run.py \
  --aoi poc-minigim/examples/plangrens-breda-teteringen.28992.geojson \
  --label "M2-eindverificatie" --runs-dir /tmp/m2-eind
nldt/.venv/bin/python poc-minigim/tools/compare_runs.py \
  /tmp/m2-baseline/2*-minigim-gebiedscheck /tmp/m2-eind/2*-minigim-gebiedscheck
```

Expected: beide suites `OK`; vergelijker `canonisch identiek ✔`; de run bevat nu ook `fase-matrix.md`.

- [ ] **Step 3: `poc-fundament/README.md`** (volledig):

```markdown
# poc-fundament — het MiniGIM-harnas voor PoC's

Het gedeelde fundament onder de nLDT-PoC's, gebaseerd op de MiniGIM-aanpak
(checklist-gedreven, expliciete bindingen `auto`/`partial`/`manual`,
faal-isolatie, PROV, deterministisch — zie
[`docs/MINIGIM.md`](../docs/MINIGIM.md) en de spec
`docs/superpowers/specs/2026-10-18-poc-fundament-minigim-harnas-design.md`).

## Wat hier ligt

| module | doet |
|---|---|
| `fundament/manifest.py` | laadt/valideert `fase-manifest.json` (de agent–fase–tool matrix) tegen `schemas/fase-manifest.schema.json` |
| `fundament/registers.py` | `TaskRegistry`: taken + bindings + bronnen met dekkingscheck |
| `fundament/fetch.py` | cache-first fetchers (OGC API Features, WFS 2.0, ArcGIS REST) met geïnjecteerde `cache_dir`/`user_agent` |
| `fundament/derivations.py` | pure derivatie-helpers (clip, historiefilter, statistiek, entropy) |
| `fundament/ops.py` + `executor.py` | `BindingExecutor` + generieke ops: per taak deterministisch leveren, falen degradeert (nooit fake, nooit fataal) |
| `fundament/matrix.py` | matrix → markdown (declaratief + per-run uitkomst) |

## Hoe een PoC het gebruikt

1. **Registries**: taken (checklist), bindings en bronnen in eigen `registry/`/`data/` (gepinde JSON).
2. **Manifest**: genereer `fase-manifest.json` uit de bindings (zie `poc-minigim/tools/gen_fase_manifest.py` als voorbeeld) — per fase agent, tools (retrieval/computation), bindingen en gates.
3. **Executor**: subclass `BindingExecutor`, bind `fetch_fn`/`cache_dir`/`cbs_filter`, registreer PoC-specifieke ops naast `DEFAULT_OPS` (zie `poc-minigim/minigim/checklist.py`).
4. **Bewijs**: golden-artefacten vóór refactors (`poc-minigim/tools/capture_golden.py`-patroon), `test_golden` erna.

## Regels

- `fundament` importeert nooit `deep-agents`, `nldt` of een poc-package (getest in `tests/test_deps.py`).
- Getallen komen uit ops, nooit uit een LLM; een falende bron is `not-delivered` + risicovlag.
- Cache-first: her-runs zijn offline reproduceerbaar; cache-bestanden zijn uitwisselbaar tussen PoC's die dezelfde bron pinnen.

Eerste consument: `poc-minigim` (PoC-5) — byte-identiek bewezen in M2.
Vervolg (eigen plannen): M3 slotgates in deep-agents, M4 transport-bruggen
(nldt-processes / A2A Agent Cards), M5 golden-per-fase.
```

- [ ] **Step 4: `poc-minigim/README.md`** — vervang in de sectie „Structuur" het blok over `minigim/` door:

```markdown
├── minigim/          package: PoC-specifieke laag op poc-fundament
│                     (registry = TaskRegistry-subclass, checklist = BindingExecutor-
│                     subclass + proxy-ops, fetch = compat-shim, ils, report, validate)
├── fase-manifest.json  agent–fase–tool matrix (gegenereerd: tools/gen_fase_manifest.py)
```

en voeg onder „Run" toe:

```markdown
De generieke mechaniek (fetch, derivaties, binding-executor) staat sinds M2 in
[`poc-fundament/`](../poc-fundament/README.md); deze PoC levert de MiniGIM-bindings,
de proxy-ops en de rapportage. Het bewijs dat de migratie niets veranderde:
`tests/test_golden.py` (canonisch identiek t.o.v. de pre-refactor golden).
```

- [ ] **Step 5: `docs/MINIGIM.md`** — voeg direct onder de kop „## nLDT-integratie" deze alinea toe:

```markdown
Sinds okt 2026 draait de executie via het gedeelde
[`poc-fundament/`](../poc-fundament/README.md) (MiniGIM-harnas): de checklist-
bindingen zijn er declaratief als `poc-minigim/fase-manifest.json`
(agent–fase–tool matrix) en de mechaniek (fetch/derivaties/executor) is
gegeneraliseerd voor de volgende PoC's — bewezen byte-identiek (M2).
```

- [ ] **Step 6: Volledige eindrun van beide suites + commit**

```bash
(cd poc-fundament && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
(cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests -q)
git add poc-fundament poc-minigim/README.md docs/MINIGIM.md
git commit -m "docs(fundament,poc-minigim): README's + MINIGIM-haak; dependency-regel-test (M2 afronding)"
```

---

## Afhankelijkheden tussen taken

| taak | vereist |
|---|---|
| 1, 2, 5 | — |
| 3 | — |
| 4 | 2, 3 |
| 6 | (poc-minigim onveranderd — eerst of parallel met 1–5, maar **vóór 7**) |
| 7 | 3, 4, **6** |
| 8 | 1, 7 |
| 9 | 5, 8 |
| 10 | alle |

## Buiten scope van dit plan (eigen plannen na review van dit bewijs)

- **M3**: slotgate-middleware in `deep-agents` (per-fase-specialisten uit het manifest; journal vermeldt fase + gate-verdicts).
- **M4**: computation-tool → nldt-processId en A2A Agent Card; riskLevel-tiering op een high-voorbeeld.
- **M5**: V-tool-suite per binding, golden-runs per fase, tweede pilot-PoC (beslispunt 5 in de spec).
