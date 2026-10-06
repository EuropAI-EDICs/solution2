# Eval-harness en trace-correlatie Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Golden-regressie over de 13 canonieke Utrecht-tracks als pytest-marker-harness (cache-only her-uitvoering, diff tegen gecommitte goldens), plus run/job-id-correlatie over journal en spans met een JSONL-spanexporter — zonder CI (gedescoped, zie spec).

**Architecture:** Pure diff-module (`poc/pipeline/golden.py`) + pytest-markers (`golden`, `llm`) met default-deselectie via `poc/pytest.ini`; jobId stroomt van `route_execute` via `execute_local` naar het journal, en een contextvar verrijkt elke `span()` met `job.id` waarvoor `telemetry.py` naast de console-exporter een JSONL-bestandsexporter krijgt.

**Tech Stack:** pytest (markers + ini-addopts), shapely (IoU), xml.etree (GML-samenvatting), opentelemetry-sdk 1.44 (custom SpanExporter), geen nieuwe dependencies.

**Spec:** [`docs/superpowers/specs/2026-10-06-eval-harness-trace-correlatie-design.md`](../specs/2026-10-06-eval-harness-trace-correlatie-design.md)

## Global Constraints

- Geen CI/workflow-bestanden in dit plan (bewust gedescoped op gebruikersbesluit); de afdwingingsdiscipline is: golden-regressie draaien vóór het committen van prompt-, model- of formalizer-wijzigingen.
- Geen nieuwe dependencies: shapely en opentelemetry-sdk zitten al in de nldt-venv/requirements.
- Golden-regressie is cache-only (geen `--refresh`); de geo-caches liggen in git en een track die toch live-fetch triggert, faalt zichtbaar.
- Diff-semantiek volgens spec: verdicts + perRule exact; zone-geometrie IoU ≥ 0,9999 + gelijk feature-aantal; `zones.gml` structureel (zone-ids); `runId`/`requestId`/`generatedAt`/`durationS` gestript.
- Bestaande suites blijven groen: nldt 362 passed, poc 295 passed/1 skipped.
- Testinterpreter: `cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest …` (venv heeft pytest + alle poc/nldt-deps); poc-tests draaien met cwd `poc/`.
- Commit-stijl: `feat(poc): …`, `test(poc): …`, `feat(nldt): …`, Nederlands.

---

### Task 1: Golden-diff-module (`poc/pipeline/golden.py`)

**Files:**
- Create: `poc/pipeline/golden.py`
- Test: `poc/tests/test_golden.py`

**Interfaces:**
- Produces (Task 3 consumeert): `CANONICAL_RUNS: dict[str, str]` (13 tracks), `golden_dir(track: str) -> Path`, `diff_runs(new_dir: Path, gold_dir: Path, iou_tolerance: float = 0.9999) -> dict` met sleutels `pass`, `verdictsEqual`, `geo` (`{pass, iou, featureCountEqual}`), `gmlEqual`, `gmlZoneCount`, `details`; plus de pure helpers `normalize_run_summary(summary) -> dict`, `load_verdicts(summary) -> dict`, `gml_zone_ids(path) -> list[str]`, `zones_iou(new_geojson: Path, gold_geojson: Path, tolerance: float) -> dict`.

- [ ] **Step 1: Schrijf de falende unit-tests** (mini-fixture-runs, geen volledige runs)

```python
# poc/tests/test_golden.py
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import golden  # noqa: E402

POLY = {
    "type": "Polygon",
    "coordinates": [[[120000.0, 450000.0], [150000.0, 450000.0], [150000.0, 480000.0], [120000.0, 480000.0], [120000.0, 450000.0]]],
}
POLY_SHIFTED = {
    "type": "Polygon",
    "coordinates": [[[125000.0, 450000.0], [155000.0, 450000.0], [155000.0, 480000.0], [125000.0, 480000.0], [125000.0, 450000.0]]],
}


def _mini_run(path: Path, verdict: str = "pass", geom=POLY) -> Path:
    path.mkdir(parents=True)
    (path / "run_summary.json").write_text(json.dumps({
        "runId": "x", "requestId": "r", "generatedAt": "nu", "durationS": 1.0,
        "verdict": verdict,
        "verdicts": {"norm-card-set": "pass", "zone-result-set": "pass"},
        "perRule": [{"ruleId": "WE-01", "verdict": "pass"}],
    }), encoding="utf-8")
    (path / "zones.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": geom}],
    }), encoding="utf-8")
    (path / "zones.gml").write_text(
        '<gml:FeatureCollection gml:id="aFeatureCollection">'
        '<gml:featureMember><imgeo:Zones gml:id="zones.0"><prop>a</prop></imgeo:Zones></gml:featureMember>'
        '<gml:featureMember><imgeo:Zones gml:id="zones.1"><prop>b</prop></imgeo:Zones></gml:featureMember>'
        "</gml:FeatureCollection>", encoding="utf-8")
    return path


def test_normalize_run_summary_strips_volatile() -> None:
    summary = {"runId": "x", "requestId": "r", "generatedAt": "nu", "durationS": 1.0, "verdict": "pass"}
    normalized = golden.normalize_run_summary(summary)
    assert normalized == {"verdict": "pass"}


def test_load_verdicts_extracts_exact_fields(tmp_path: Path) -> None:
    d = _mini_run(tmp_path / "run")
    summary = json.loads((d / "run_summary.json").read_text(encoding="utf-8"))
    assert golden.load_verdicts(summary) == {
        "verdict": "pass",
        "verdicts": {"norm-card-set": "pass", "zone-result-set": "pass"},
        "perRule": [("WE-01", "pass")],
    }


def test_zones_iou_identical_is_one(tmp_path: Path) -> None:
    a = tmp_path / "a.geojson"; b = tmp_path / "b.geojson"
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY}]}
    a.write_text(json.dumps(fc), encoding="utf-8"); b.write_text(json.dumps(fc), encoding="utf-8")
    assert golden.zones_iou(a, b)["iou"] == 1.0
    assert golden.zones_iou(a, b)["pass"] is True


def test_zones_iou_shifted_below_tolerance(tmp_path: Path) -> None:
    a = tmp_path / "a.geojson"; b = tmp_path / "b.geojson"
    a.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY}]}), encoding="utf-8")
    b.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": POLY_SHIFTED}]}), encoding="utf-8")
    out = golden.zones_iou(a, b)
    assert out["iou"] < 0.9999 and out["pass"] is False


def test_gml_zone_ids(tmp_path: Path) -> None:
    d = _mini_run(tmp_path / "run")
    assert golden.gml_zone_ids(d / "zones.gml") == ["zones.0", "zones.1"]


def test_diff_runs_equal_passes(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new"); gold = _mini_run(tmp_path / "gold")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is True and out["verdictsEqual"] is True and out["gmlEqual"] is True


def test_diff_runs_flags_verdict_drift(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new", verdict="fail"); gold = _mini_run(tmp_path / "gold")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is False and out["verdictsEqual"] is False
    assert "verdicts" in out["details"]


def test_diff_runs_flags_gml_drift(tmp_path: Path) -> None:
    new = _mini_run(tmp_path / "new"); gold = _mini_run(tmp_path / "gold")
    text = (new / "zones.gml").read_text(encoding="utf-8").replace('gml:id="zones.1"', 'gml:id="zones.2"')
    (new / "zones.gml").write_text(text, encoding="utf-8")
    out = golden.diff_runs(new, gold)
    assert out["pass"] is False and out["gmlEqual"] is False
    assert out["details"]["gmlOnlyInNew"] == ["zones.2"]
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd /Users/marc/Projecten/ldttoolbox/poc && ../nldt/.venv/bin/python -m pytest tests/test_golden.py -q` → ModuleNotFoundError (`pipeline.golden` bestaat niet).

- [ ] **Step 3: Implementeer `poc/pipeline/golden.py`**

```python
"""Golden-regressie: normalisatie en diff van canonieke PoC-runs (eval-harness).

Pure module — geen netwerk, geen schrijfacties. De 13 canonieke runs onder
poc/runs/ zijn de frozen goldens (GS-1/GS-3-kern); de mapping is bewust
expliciet. Diff-semantiek (spec 2026-10-06): verdicts + perRule exact,
zone-geometrie IoU-gelimiteerd, zones.gml structureel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

POC_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = POC_ROOT / "runs"

CANONICAL_RUNS: dict[str, str] = {
    "wind": "20260830T113234Z-wind",
    "zon": "20260830T142439Z-zon",
    "bos": "20260830T142446Z-bos",
    "water": "20261004T185116Z-water",
    "bodem": "20261004T185509Z-bodem",
    "mobiliteit": "20261005T072839Z-mobiliteit",
    "landschap": "20261005T070621Z-landschap",
    "landbouw": "20261005T094244Z-landbouw",
    "wonen": "20261005T100258Z-wonen",
    "werken": "20261006T121921Z-werken",
    "recreatie": "20261006T114934Z-recreatie",
    "biomassa": "20261006T120133Z-biomassa",
    "energietoets": "20261006T171730Z-energietoets",
}

VOLATILE_SUMMARY_KEYS = ("runId", "requestId", "generatedAt", "durationS")


def golden_dir(track: str) -> Path:
    return RUNS_ROOT / CANONICAL_RUNS[track]


def normalize_run_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in summary.items() if k not in VOLATILE_SUMMARY_KEYS}


def load_verdicts(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": summary.get("verdict"),
        "verdicts": summary.get("verdicts"),
        "perRule": [(r.get("ruleId"), r.get("verdict")) for r in summary.get("perRule", [])],
    }


def gml_zone_ids(path: Path) -> list[str]:
    """Zone-feature-ids (`zones.<n>`) uit zones.gml, gesorteerd en ontdubbeld."""
    text = path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'gml:id="(zones\.\d+)"', text)))


def _features(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("features", [])
    return [z for z in data if isinstance(z, dict)]


def zones_iou(new_geojson: Path, gold_geojson: Path, tolerance: float = 0.9999) -> dict[str, Any]:
    from shapely.geometry import shape
    from shapely.ops import unary_union

    new = _features(new_geojson)
    gold = _features(gold_geojson)
    count_equal = len(new) == len(gold)
    union_new = unary_union([shape(z["geometry"]) for z in new if z.get("geometry")]) if new else None
    union_gold = unary_union([shape(z["geometry"]) for z in gold if z.get("geometry")]) if gold else None
    if union_new is None or union_gold is None or union_new.area == 0 or union_gold.area == 0:
        iou = 1.0 if (union_new is None and union_gold is None) else 0.0
    else:
        iou = union_new.intersection(union_gold).area / union_new.union(union_gold).area
    return {
        "featureCountEqual": count_equal,
        "iou": round(iou, 6),
        "pass": count_equal and iou >= tolerance,
    }


def diff_runs(new_dir: Path, gold_dir: Path, iou_tolerance: float = 0.9999) -> dict[str, Any]:
    new_summary = json.loads((new_dir / "run_summary.json").read_text(encoding="utf-8"))
    gold_summary = json.loads((gold_dir / "run_summary.json").read_text(encoding="utf-8"))
    verdicts_new, verdicts_gold = load_verdicts(new_summary), load_verdicts(gold_summary)
    verdicts_equal = verdicts_new == verdicts_gold

    if (new_dir / "zones.geojson").is_file() and (gold_dir / "zones.geojson").is_file():
        geo = zones_iou(new_dir / "zones.geojson", gold_dir / "zones.geojson", iou_tolerance)
    else:
        geo = {"featureCountEqual": True, "iou": None, "pass": True}

    gml_new = gml_zone_ids(new_dir / "zones.gml") if (new_dir / "zones.gml").is_file() else []
    gml_gold = gml_zone_ids(gold_dir / "zones.gml") if (gold_dir / "zones.gml").is_file() else []
    gml_equal = gml_new == gml_gold

    passed = verdicts_equal and geo["pass"] and gml_equal
    return {
        "pass": passed,
        "verdictsEqual": verdicts_equal,
        "geo": geo,
        "gmlEqual": gml_equal,
        "gmlZoneCount": len(gml_gold),
        "details": {} if passed else {
            "verdicts": None if verdicts_equal else {"new": verdicts_new, "golden": verdicts_gold},
            "gmlOnlyInNew": sorted(set(gml_new) - set(gml_gold))[:10],
            "gmlOnlyInGolden": sorted(set(gml_gold) - set(gml_new))[:10],
        },
    }
```

- [ ] **Step 4: Draai, verwacht PASS** — `../nldt/.venv/bin/python -m pytest tests/test_golden.py -q` → `8 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add poc/pipeline/golden.py poc/tests/test_golden.py
git commit -m "feat(poc): golden-diff-module — normalisatie, IoU-tolerantie, gml-structuurvergelijking, canonieke mapping van 13 tracks"
```

### Task 2: `poc/pytest.ini` — markers registreren, standaard snel houden

**Files:**
- Create: `poc/pytest.ini`

**Interfaces:**
- Produces: geregistreerde markers `golden` en `llm`; addopts-deselectie zodat `pytest` (zonder args) de snelle suite draait en `-m golden`/`-m llm` de regressies expliciet selecteren (CLI `-m` overschrijft addopts).

- [ ] **Step 1: Maak het bestand**

```ini
# poc/pytest.ini — eval-harness markers (spec 2026-10-06-eval-harness-trace-correlatie)
# Standaard run = snelle suite; de golden-regressie en de LLM-seam-comparators
# worden expliciet geselecteerd: `pytest -m golden` / `pytest -m llm`.
[pytest]
addopts = -m "not golden and not llm"
markers =
    golden: her-uitvoering van de 13 canonieke tracks tegen de frozen goldens (traag: enkele minuten totaal)
    llm: LLM-seam-comparators (alleen met LDT_NORM_LLM_ENDPOINT / LDT_SCENARIO_LLM_ENDPOINT)
```

- [ ] **Step 2: Verifieer beide gedragingen**

```bash
cd /Users/marc/Projecten/ldttoolbox/poc
../nldt/.venv/bin/python -m pytest tests -q            # standaard: 295 passed, 1 skipped (golden-deselection werkt)
../nldt/.venv/bin/python -m pytest tests -m golden -q  # collect: 0 items nog (regressietest komt in Task 3) — geen fout
```

- [ ] **Step 3: Commit**

```bash
git add poc/pytest.ini
git commit -m "test(poc): pytest-markers golden/llm geregistreerd, standaard run blijft de snelle suite"
```

### Task 3: Golden-regressiesuite (`poc/tests/test_golden_regression.py`)

**Files:**
- Test: `poc/tests/test_golden_regression.py`

**Interfaces:**
- Consumes: Task 1 (`CANONICAL_RUNS`, `golden_dir`, `diff_runs`) en `run.py::main(argv) -> int` (bestaand, regel 1109; `--use-case <track> --out <dir>` schrijft exact naar `<dir>`, cache-first zonder `--refresh`).

- [ ] **Step 1: Schrijf de regressietest**

```python
# poc/tests/test_golden_regression.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import golden  # noqa: E402
from run import main as run_main  # noqa: E402


@pytest.mark.golden
@pytest.mark.parametrize("track", sorted(golden.CANONICAL_RUNS))
def test_golden_regression(track: str, tmp_path: Path) -> None:
    out = tmp_path / f"run-{track}"
    rc = run_main(["--use-case", track, "--out", str(out)])
    assert rc == 0, f"run.py faalde voor track {track}"
    result = golden.diff_runs(out, golden.golden_dir(track))
    assert result["pass"], f"golden-drift op {track}: {result['details']}"
```

- [ ] **Step 2: Smoke één track** — `cd poc && ../nldt/.venv/bin/python -m pytest "tests/test_golden_regression.py::test_golden_regression[biomassa]" -m golden -q` → `1 passed` (biomassa is een jonge, stabiele track; als `--out` anders nest dan verwacht, fix dat eerst — de diff zal het direct tonen).

- [ ] **Step 3: Volledige golden-run** — `../nldt/.venv/bin/python -m pytest tests -m golden -q` → `13 passed`. Als een track offline niet kan her-uitvoeren (live-fetch poging), is dat een zichtbare fout: onderzoek dan welke cache ontbreekt vóór verdergaan (geen toleratie in code toevoegen).

- [ ] **Step 4: Verifieer de standaard suite is ongewijzigd** — `../nldt/.venv/bin/python -m pytest tests -q` → `295 passed, 1 skipped` (golden is gedeselecteerd).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add poc/tests/test_golden_regression.py
git commit -m "test(poc): golden-regressie — 13 canonieke tracks cache-only her-uitvoerd en gediff't tegen de frozen goldens"
```

### Task 4: Seam-comparators als `llm`-marker tests

**Files:**
- Test: `poc/tests/test_seam_comparators.py`

**Interfaces:**
- Consumes: `poc/llm/compare_norm_llm.py::main(argv) -> int` (regel 127) en `poc/scenarios/compare_authors.py::main(argv) -> int` (regel 66); env-gates `LDT_NORM_LLM_ENDPOINT` resp. `LDT_SCENARIO_LLM_ENDPOINT` (bestaande scripts loggen "LLM leg skipped" zonder endpoint).

- [ ] **Step 1: Schrijf de tests**

```python
# poc/tests/test_seam_comparators.py
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

sys.path.insert(0, str(POC_ROOT / "llm"))
sys.path.insert(0, str(POC_ROOT / "scenarios"))


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("LDT_NORM_LLM_ENDPOINT"), reason="LDT_NORM_LLM_ENDPOINT niet gezet — LLM-leg vergt een lokaal open model")
def test_norm_seam_comparator_wind(tmp_path: Path) -> None:
    """S1/S2: deterministische replay vs LLM-hooks op de wind-shard; het
    harde invariant (nul drift op citaties/rechtskracht/geo-bindingen) zit
    in de comparator zelf — rc 0 betekent geen drift boven de drempels."""
    import compare_norm_llm

    rc = compare_norm_llm.main(["--use-case", "wind", "--out", str(tmp_path)])
    assert rc == 0


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("LDT_SCENARIO_LLM_ENDPOINT"), reason="LDT_SCENARIO_LLM_ENDPOINT niet gezet — LLM-leg vergt een lokaal open model")
def test_scenario_author_comparator_wind(tmp_path: Path) -> None:
    """S7: floor/hybrid/llm authors over de laatste wind-run; rc 0 betekent
    floorIntact en geen gate-rejecties boven de drempels."""
    import compare_authors

    rc = compare_authors.main(["--use-case", "wind", "--out", str(tmp_path)])
    assert rc == 0
```

Let op: verifieer bij uitvoering of `main` een `--out`-vlag kent (beide scripts schrijven naar `OUT_ROOT` met timestamp-subdir); zo niet, laat de `--out` weg en assert alleen `rc == 0` — de scripts zelf bepalen hun uitvoerlocatie. Dit is de enige vrijheid in dit plan; alles anders is vast.

- [ ] **Step 2: Verifieer skip-gedrag (zonder endpoints)** — `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_seam_comparators.py -m llm -q` → `2 skipped`.

- [ ] **Step 3: Verifieer standaard suite** — `../nldt/.venv/bin/python -m pytest tests -q` → `295 passed, 1 skipped` (llm gedeselecteerd).

- [ ] **Step 4: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add poc/tests/test_seam_comparators.py
git commit -m "test(poc): S1/S2- en S7-comparators als llm-marker tests — skipped zonder lokaal LLM-endpoint"
```

### Task 5: jobId door de keten — router → `execute_local` → journal

**Files:**
- Modify: `nldt/services/process_adapter/handlers.py` (wrapper `execute_local`, regel ~394: signature + journal-extra)
- Modify: `nldt/services/process_adapter/router.py` (de `execute_local(process_id, inputs)`-aanroepen binnen `route_execute` — twee plaatsen: de kubeflow-fallback ~regel 59 en de lokale hoofdbranch)
- Test: `nldt/tests/test_process_journal.py` (uitbreiding)

**Interfaces:**
- Produces: `execute_local(process_id: str, inputs: dict[str, Any], job_id: str | None = None) -> dict` — journal-entries bevatten `jobId` wanneer die is meegegeven; Task 6 consumeert dezelfde contextvar-losse param niet, maar wel het journal-veld.

- [ ] **Step 1: Falende tests** (voeg toe aan `nldt/tests/test_process_journal.py`)

```python
def test_execute_local_includes_job_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    from services.process_adapter.handlers import execute_local

    execute_local("compute-area-statistics", {
        "features": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]}},
        ]},
    }, job_id="job-42")
    entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert entry["jobId"] == "job-42"


def test_route_execute_journals_job_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    from services.process_adapter.router import route_execute

    route_execute("compute-area-statistics", {
        "features": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]}},
        ]},
    })
    entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert entry.get("jobId")  # job-id uit route_execute komt in het journal
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_process_journal.py -q` → beide nieuwe testen falen (signature kent geen `job_id`; entry heeft geen `jobId`).

- [ ] **Step 3: Implementeer.** In `handlers.py` de wrapper-signature en journaling:

```python
def execute_local(process_id: str, inputs: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
    """Instrumented dispatch: elke process-executie landt als journal-event
    (harness-unificatie M3 + eval-harness jobId-correlatie)."""
    import time

    start = time.monotonic()
    extras = {"jobId": job_id} if job_id else {}
    try:
        result = _execute_local_inner(process_id, inputs)
    except Exception as exc:
        journal_process_event(process_id, "error", f"{type(exc).__name__}: {exc}", **extras)
        raise
    journal_process_event(
        process_id, "ok", f"process '{process_id}' executed",
        durationMs=int((time.monotonic() - start) * 1000), **extras,
    )
    return result
```

In `router.py`: in `route_execute` elke `execute_local(process_id, inputs)` binnen de functie vervangen door `execute_local(process_id, inputs, job_id=job_id)` (de fallback binnen `UCSAdapter.execute_remote` op regel 38 blijft ongewijzigd — daar bestaat geen job-id).

- [ ] **Step 4: Draai de hele nldt-suite** — `.venv/bin/python -m pytest tests -q` → `364 passed` (362 + 2 nieuwe).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/process_adapter/handlers.py nldt/services/process_adapter/router.py nldt/tests/test_process_journal.py
git commit -m "feat(nldt): jobId door route_execute → execute_local → journal-entry (eval-harness correlatie)"
```

### Task 6: Telemetry — job-context en JSONL-spanexporter

**Files:**
- Modify: `nldt/services/common/telemetry.py` (contextvar + `set_current_job_id`, `span()`-verrijking, `_JsonlSpanExporter`, `init_telemetry` voegt exporter toe)
- Modify: `nldt/services/process_adapter/router.py` (`route_execute` zet de job-context)
- Test: `nldt/tests/test_telemetry_jsonl.py` (nieuw)

**Interfaces:**
- Produces: `set_current_job_id(job_id: str | None) -> None`; `span(name, attributes)` zet automatisch `job.id` wanneer een context actief is; JSONL-exporter schrijft naar `${NLDT_TRACES_DIR:-nldt/data/traces}/<YYYYMMDD>-spans.jsonl` — één JSON-object per gesloten span (name, traceId, spanId, start/end, attributes incl. `job.id`).

- [ ] **Step 1: Falende test**

```python
# nldt/tests/test_telemetry_jsonl.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common import telemetry


@pytest.fixture
def fresh_telemetry(tmp_path: Path, monkeypatch) -> Path:
    """Reset de module-global zodat init opnieuw loopt; stuur exporter naar tmp."""
    monkeypatch.setenv("NLDT_OTEL_ENABLED", "1")
    monkeypatch.setenv("NLDT_TRACES_DIR", str(tmp_path / "traces"))
    monkeypatch.setattr(telemetry, "_initialized", False)
    monkeypatch.setattr(telemetry, "_tracer", None)
    return tmp_path / "traces"


def test_span_writes_jsonl_with_and_without_job_id(fresh_telemetry: Path) -> None:
    """Één test voor beide gevallen: opentelemetry's set_tracer_provider is
    maar één keer per proces aanroepbaar, dus geen tweede init in een tweede test."""
    telemetry.set_current_job_id("job-7")
    with telemetry.span("unit.test", {"k": "v"}):
        pass
    telemetry.set_current_job_id(None)
    with telemetry.span("unit.clean"):
        pass
    from opentelemetry import trace as otel_trace

    otel_trace.get_tracer_provider().force_flush()
    files = list(fresh_telemetry.glob("*-spans.jsonl"))
    assert files, "geen spans-bestand geschreven"
    entries = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines() if line]
    with_job = next(e for e in entries if e["name"] == "unit.test")
    without = next(e for e in entries if e["name"] == "unit.clean")
    assert with_job["attributes"]["job.id"] == "job-7"
    assert with_job["attributes"]["k"] == "v"
    assert "job.id" not in without["attributes"]
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_telemetry_jsonl.py -q` → AttributeError (`set_current_job_id` bestaat niet).

- [ ] **Step 3: Implementeer.** In `telemetry.py` bovenaan de extra imports en de contextvar:

```python
import contextvars
import json
from datetime import datetime, timezone
from pathlib import Path

_job_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("nldt_job_id", default=None)


def set_current_job_id(job_id: str | None) -> None:
    _job_id_var.set(job_id)
```

In `init_telemetry`, direct na de console-processor (binnen het try-blok, na `provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))`):

```python
    traces_dir = Path(os.environ.get("NLDT_TRACES_DIR", Path(__file__).resolve().parents[2] / "data" / "traces"))
    provider.add_span_processor(BatchSpanProcessor(_JsonlSpanExporter(traces_dir)))
```

Onderaan het bestand de exporter en de verrijkte `span()`:

```python
class _JsonlSpanExporter:
    """Schrijft gesloten spans als JSONL (één object per regel) — bestandsbasis
    vervangt de console-only observability (roadmap 08: OTLP i.p.v. console)."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def export(self, spans):
        path = self.directory / f"{datetime.now(timezone.utc):%Y%m%d}-spans.jsonl"
        lines = []
        for span in spans:
            lines.append(json.dumps({
                "name": span.name,
                "traceId": f"{span.context.trace_id:032x}",
                "spanId": f"{span.context.span_id:016x}",
                "startTimeUnixNano": span.start_time,
                "endTimeUnixNano": span.end_time,
                "attributes": {k: span.attributes[k] for k in span.attributes.keys()},
            }, ensure_ascii=False, default=str))
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + ("\n" if lines else ""))
        from opentelemetry.sdk.trace.export import SpanExportResult

        return SpanExportResult.SUCCESS

    def shutdown(self):
        return None

    def force_flush(self, timeout_millis: int = 30000):
        return True
```

De bestaande `span()`-contextmanager vervangen door de verrijkte variant:

```python
@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    tracer = get_tracer()
    if tracer is None:
        yield
        return
    merged = dict(attributes or {})
    job_id = _job_id_var.get()
    if job_id:
        merged.setdefault("job.id", job_id)
    with tracer.start_as_current_span(name) as s:
        for k, v in merged.items():
            s.set_attribute(k, str(v))
        yield
```

In `router.py` de hoofdexecutie van `route_execute` omhullen (import bovenaan: `from services.common.telemetry import set_current_job_id`):

```python
    from services.common.telemetry import set_current_job_id  # (top-level import verkiest)

    set_current_job_id(job_id)
    try:
        # … bestaande backend-dispatch die outputs oplevert …
        set_current_job_id(None)
```

Concreet: zet `set_current_job_id(job_id)` direct na `job_id = new_job_id()` en `set_current_job_id(None)` vóór elke `return` in `route_execute` (de functie heeft enkele terugkeerpaden; de simpelste correcte vorm is een `try/finally` om de backend-dispatch met `finally: set_current_job_id(None)`).

- [ ] **Step 4: Draai de hele nldt-suite** — `.venv/bin/python -m pytest tests -q` → `365 passed` (364 + 1 nieuwe; de exporter schrijft tijdens de suite alleen naar tmp-paths via de fixture, en naar `nldt/data/traces/` voor processen die de suite zelf draait — die map is gitignored).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/common/telemetry.py nldt/services/process_adapter/router.py nldt/tests/test_telemetry_jsonl.py
git commit -m "feat(nldt): JSONL-spanexporter + job-context — elke span draagt job.id, traces in nldt/data/traces (NLDT_TRACES_DIR override)"
```

### Task 7: Afsluiting — README-notitie en eindverificatie

**Files:**
- Modify: `poc/README.md` (na de test-suite-regel in het "Run it"-blok)

- [ ] **Step 1: README-notitie** — voeg na de regel `cd poc && python3 -m pytest tests -q  # offline test suite (295 tests)` toe:

```markdown
Eval-regressie (golden): `python3 -m pytest tests -m golden -q` her-uitvoert alle 13
canonieke tracks op cache en diff't tegen de frozen goldens (`pipeline/golden.py`).
Draai dit vóór het committen van prompt-, model- of formalizer-wijzigingen. De
LLM-seam-comparators draaien lokaal met `pytest -m llm` (vereist `LDT_NORM_LLM_ENDPOINT`
resp. `LDT_SCENARIO_LLM_ENDPOINT`).
```

- [ ] **Step 2: Eindverificatie**

```bash
cd /Users/marc/Projecten/ldttoolbox/poc && ../nldt/.venv/bin/python -m pytest tests -q          # 295 passed, 1 skipped
../nldt/.venv/bin/python -m pytest tests -m golden -q                                          # 13 passed
cd ../nldt && .venv/bin/python -m pytest tests -q                                              # 365 passed
PYTHONPATH=. NLDT_OFFLINE=1 .venv/bin/python -c "
from services.process_adapter.router import route_execute
r = route_execute('compute-area-statistics', {'features': {'type': 'FeatureCollection', 'features': []}})
print('route_execute OK')" ; tail -1 ../deep-agents/runs/live/steps.jsonl                       # laatste regel bevat jobId
```

- [ ] **Step 3: Commit + push**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add poc/README.md
git commit -m "docs(poc): eval-regressie gebruiksinstructie in README (golden + llm markers)"
git push origin main
```
