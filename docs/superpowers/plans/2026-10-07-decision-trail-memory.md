# Decision-trail memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Executiestatus (2026-10-07):** alle 6 taken via subagent-driven development geïmplementeerd
> (implementer + taakreview per taak; Taak 1 had een BLOCKED-ronde op twee plan-defecten —
> schemanaam moest `"decision-trail.schema.json"` zijn, provenance moest `agent` toestaan —
> daarna opgelost). Eindverificatie: nldt 390 passed, poc 304/1, golden-kring live bewezen
> (runner → diff → consolidator; 3 echte trails uit bestaande journal-errors). Gepusht.
> Eindreview-triage (kan-later): update_trail-param schaduwt trail_id; niet-atomische batch;
> didItHelp niet naar null terug; XPASS/XFAIL-regex-blindvlek; journal-ruis opruimen/markeren.

**Goal:** De semantic memory-laag: deterministische consolidatie van automatische observaties (journal-errors, HITL-verdicts, ledger-rejects, golden-drift) naar durabele, schema-gedwongen decision-trail-records met de drie leerniveaus, plus idempotente CLI en een leerrapport.

**Architecture:** Nieuw pakket `nldt/services/memory/` met vier gescheiden onderdelen (observations → store → consolidate → report), gelezen op de bestaande episodische laag zonder hot-path-writers. Observatie→trail-mapping via een vaste, citeerbare waardentabel (geen LLM). Trails zijn append-only JSONL per dag; `--handle`/`--promote` herschrijven de dagfile die de trail bevat.

**Tech Stack:** stdlib (json/hashlib/argparse/re/collections), bestaande `services.common.schema.load_schema`/`validate_instance`, bestaande `services.process_adapter.journal.journal_path` — geen nieuwe dependencies.

**Spec:** [`docs/superpowers/specs/2026-10-07-decision-trail-memory-design.md`](../specs/2026-10-07-decision-trail-memory-design.md)

## Global Constraints

- Geen LLM in de kring; alle waarden (what/why/whatShouldChange) komen uit de vaste waardentabel in `observations.py` ("selection, not generation").
- Consolidatie is async en buiten het hot path: geen enkele bestaande writer (journal, run-records, ledgers) verandert.
- Extractors zijn lenient: afwezige bron → lege lijst, nooit een fout.
- Trails: `${NLDT_MEMORY_DIR:-nldt/data/memory/trails}/YYYYMMDD-trails.jsonl` (`nldt/data/` is gitignored); elk record valideert tegen `decision-trail.schema.json` bij schrijven.
- Promotie tussen leerniveaus is nooit automatisch; rapport markeert alleen kandidaten (zelfde observationType ≥ 3× open op operationeel).
- Bronnen-shapes geverifieerd: `nldt/data/runs/<runId>/validation.json` heeft `verdict`; `poc/runs/<run>/norm-llm-ledger.json` (geschreven door `poc/run.py:1209`); `poc/scenario-runs/<run>/proposals-rejected.json` = dict `{author, rejected: [...], note}`.
- Testinterpreter: `cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q` (venv heeft pytest + alle deps).
- Commit-stijl: `feat(nldt): …`, `test(nldt): …`, `docs(…): …`, Nederlands.

---

### Task 1: Schema + trail-store (`decision-trail.schema.json`, `store.py`)

**Files:**
- Create: `nldt/schemas/decision-trail.schema.json`
- Create: `nldt/services/memory/__init__.py` (leeg)
- Create: `nldt/services/memory/store.py`
- Test: `nldt/tests/test_memory_store.py`

**Interfaces:**
- Consumes: `services.common.schema.validate_instance(instance, schema_name)` (bestaand).
- Produces (Tasks 2–4 consumeren): `memory_dir() -> Path`, `trail_id(observation: dict) -> str` (`"dt-<sha8>"` over `type|source|detail`), `make_trail(observation, what, why, what_should_change, created_at=None) -> dict` (valideert), `append_trails(records: list[dict]) -> int` (dedup op trailId, retourneert aantal geschreven), `load_trails() -> list[dict]`, `update_trail(trail_id, *, status=None, did_it_help=None, learning_level=None) -> dict | None`.

- [ ] **Step 1: Schrijf het schema**

```json
// nldt/schemas/decision-trail.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "decision-trail.schema.json",
  "title": "Decision trail record (leerstaat B10 / semantic memory)",
  "type": "object",
  "required": ["trailId", "observation", "what", "why", "whatShouldChange", "whoDecides", "didItHelp", "learningLevel", "status", "createdAt"],
  "additionalProperties": false,
  "properties": {
    "trailId": { "type": "string", "pattern": "^dt-[0-9a-f]{8}$" },
    "observation": {
      "type": "object",
      "required": ["type", "source", "detail"],
      "additionalProperties": false,
      "properties": {
        "type": { "enum": ["journal_error", "hitl_needs_human", "ledger_reject", "golden_drift"] },
        "source": { "type": "string" },
        "provenance": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "jobId": { "type": "string" },
            "runId": { "type": "string" },
            "agent": { "type": "string" }
          }
        },
        "detail": { "type": "string" }
      }
    },
    "what": { "type": "string" },
    "why": { "type": "string" },
    "whatShouldChange": { "type": "string" },
    "whoDecides": { "type": "string" },
    "didItHelp": { "type": ["string", "null"] },
    "learningLevel": { "enum": ["operationeel", "organisatie", "institutioneel"] },
    "status": { "enum": ["open", "handled"] },
    "createdAt": { "type": "string" }
  }
}
```

- [ ] **Step 2: Schrijf de falende tests**

```python
# nldt/tests/test_memory_store.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import store

OBS = {
    "type": "journal_error",
    "source": "steps.jsonl",
    "provenance": {"jobId": "job-1", "agent": "compute-area-statistics"},
    "detail": "compute-area-statistics: KeyError: 'features'",
}


@pytest.fixture
def memory_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "trails"
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(d))
    return d


def test_make_trail_validates_and_fills_defaults(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    assert trail["trailId"] == store.trail_id(OBS)
    assert trail["status"] == "open"
    assert trail["learningLevel"] == "operationeel"
    assert trail["whoDecides"] == "operator"
    assert trail["didItHelp"] is None
    assert trail["observation"]["provenance"]["jobId"] == "job-1"


def test_trail_id_is_stable_over_dict_order(memory_dir: Path) -> None:
    a = store.trail_id({"type": "t", "source": "s", "detail": "d"})
    b = store.trail_id({"detail": "d", "source": "s", "type": "t"})
    assert a == b and a.startswith("dt-")


def test_append_and_load_roundtrip(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    assert store.append_trails([trail]) == 1
    assert store.append_trails([trail]) == 0  # idempotent op trailId
    assert [t["trailId"] for t in store.load_trails()] == [trail["trailId"]]


def test_append_trails_invalid_record_raises(memory_dir: Path) -> None:
    bad = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    bad["status"] = "onbekend"
    with pytest.raises(Exception):
        store.append_trails([bad])
    assert store.load_trails() == []  # niets weggeschreven


def test_update_trail_edits_in_place(memory_dir: Path) -> None:
    trail = store.make_trail(OBS, what="w", why="o", what_should_change="v")
    store.append_trails([trail])
    updated = store.update_trail(trail["trailId"], status="handled", did_it_help="opgelost", learning_level="organisatie")
    assert updated["status"] == "handled" and updated["didItHelp"] == "opgelost" and updated["learningLevel"] == "organisatie"
    assert store.load_trails()[0]["status"] == "handled"


def test_update_trail_unknown_returns_none(memory_dir: Path) -> None:
    assert store.update_trail("dt-00000000", status="handled") is None
```

- [ ] **Step 3: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_memory_store.py -q` → ModuleNotFoundError (`services.memory` bestaat niet).

- [ ] **Step 4: Implementeer `nldt/services/memory/store.py`** (en een leeg `__init__.py`)

```python
"""Durabele decision-trail store (semantic memory, leerstaat B10).

Append-only JSONL onder ${NLDT_MEMORY_DIR:-nldt/data/memory/trails}/
YYYYMMDD-trails.jsonl. Schrijven valideert elk record tegen
decision-trail.schema.json; --handle/--promote herschrijven de dagfile
die de trail bevat (in-place, regelvolgorde blijft).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.common.schema import validate_instance

MEMORY_ROOT = Path(__file__).resolve().parents[2] / "data" / "memory" / "trails"


def memory_dir() -> Path:
    return Path(os.environ.get("NLDT_MEMORY_DIR", str(MEMORY_ROOT)))


def _day_file() -> Path:
    return memory_dir() / f"{datetime.now(timezone.utc):%Y%m%d}-trails.jsonl"


def trail_id(observation: dict[str, Any]) -> str:
    ident = json.dumps(
        {k: observation.get(k) for k in ("type", "source", "detail")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return "dt-" + hashlib.sha256(ident.encode("utf-8")).hexdigest()[:8]


def make_trail(
    observation: dict[str, Any],
    what: str,
    why: str,
    what_should_change: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    record = {
        "trailId": trail_id(observation),
        "observation": {k: observation[k] for k in ("type", "source", "provenance", "detail") if k in observation},
        "what": what,
        "why": why,
        "whatShouldChange": what_should_change,
        "whoDecides": "operator",
        "didItHelp": None,
        "learningLevel": "operationeel",
        "status": "open",
        "createdAt": created_at or datetime.now(timezone.utc).isoformat(),
    }
    validate_instance(record, "decision-trail.schema.json")
    return record


def append_trails(records: list[dict[str, Any]]) -> int:
    existing = {t["trailId"] for t in load_trails()}
    path = _day_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            if record["trailId"] in existing:
                continue
            validate_instance(record, "decision-trail.schema.json")
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            existing.add(record["trailId"])
            written += 1
    return written


def load_trails() -> list[dict[str, Any]]:
    trails: list[dict[str, Any]] = []
    if not memory_dir().is_dir():
        return trails
    for path in sorted(memory_dir().glob("*-trails.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                trails.append(json.loads(line))
    return trails


def update_trail(
    trail_id: str,
    *,
    status: str | None = None,
    did_it_help: str | None = None,
    learning_level: str | None = None,
) -> dict[str, Any] | None:
    """Pas één trail aan en herschrijf de dagfile waarin hij staat."""
    for path in sorted(memory_dir().glob("*-trails.jsonl")):
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        hit = False
        for record in records:
            if record["trailId"] != trail_id:
                continue
            hit = True
            if status is not None:
                record["status"] = status
            if did_it_help is not None:
                record["didItHelp"] = did_it_help
            if learning_level is not None:
                record["learningLevel"] = learning_level
        if hit:
            for record in records:
                validate_instance(record, "decision-trail.schema.json")
            path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in records), encoding="utf-8")
            return next(r for r in records if r["trailId"] == trail_id)
    return None
```

- [ ] **Step 5: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_memory_store.py -q` → `6 passed`.

- [ ] **Step 6: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/schemas/decision-trail.schema.json nldt/services/memory/ nldt/tests/test_memory_store.py
git commit -m "feat(nldt): decision-trail schema + trail-store — append-only JSONL, schema-gedwongen, idempotent"
```

### Task 2: Observation-extractors (`observations.py`)

**Files:**
- Create: `nldt/services/memory/observations.py`
- Test: `nldt/tests/test_memory_observations.py`

**Interfaces:**
- Consumes: `services.process_adapter.journal.journal_path()` (bestaand); Task 1 (`make_trail`, `trail_id`).
- Produces (Task 3 consumeert): `read_journal_errors(journal_path=None) -> list[dict]`, `read_hitl_observations(runs_root=None) -> list[dict]`, `read_ledger_observations(poc_root=None) -> list[dict]`, `read_golden_drift(diff_path=None) -> list[dict]`, `collect_observations() -> list[dict]`, `to_trail(observation) -> dict` (via de vaste `DEFAULTS`-tabel), en de constante `DEFAULTS`.

- [ ] **Step 1: Schrijf de falende tests**

```python
# nldt/tests/test_memory_observations.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import observations as obs

PSEUDO_PATH = Path("steps.jsonl")  # relatief: trailId-machine-onafhankelijk


def _journal(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "steps.jsonl"
    p.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    return p


def test_journal_errors_extracted_with_provenance(tmp_path: Path) -> None:
    p = _journal(tmp_path, [
        {"ts": "10:00:00", "kind": "process_result", "agent": "compute-area-statistics", "status": "ok", "summary": "ok", "jobId": "j1"},
        {"ts": "10:00:01", "kind": "process_result", "agent": "run_opportunity_map", "status": "error", "summary": "KeyError: 'useCase'", "jobId": "j2"},
        {"ts": "10:00:02", "kind": "tool_call", "agent": "x", "status": "error", "summary": "geen process_result"},
        "geen json regel",
    ])
    out = obs.read_journal_errors(p)
    assert len(out) == 1
    o = out[0]
    assert o["type"] == "journal_error"
    assert o["provenance"]["jobId"] == "j2"
    assert "KeyError" in o["detail"]


def test_journal_missing_file_is_empty(tmp_path: Path) -> None:
    assert obs.read_journal_errors(tmp_path / "bestaatniet.jsonl") == []


def test_hitl_needs_human_from_validation_json(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    (runs / "run-a").mkdir(parents=True)
    (runs / "run-a" / "validation.json").write_text(json.dumps({"verdict": "needs_human", "artifactId": "bp2op"}), encoding="utf-8")
    (runs / "run-b").mkdir()
    (runs / "run-b" / "validation.json").write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    out = obs.read_hitl_observations(runs)
    assert len(out) == 1 and out[0]["provenance"]["runId"] == "run-a"


def test_hitl_missing_root_is_empty(tmp_path: Path) -> None:
    assert obs.read_hitl_observations(tmp_path / "runs") == []


def test_ledger_dict_and_list_forms(tmp_path: Path) -> None:
    scen = tmp_path / "scenario-runs" / "r1"
    scen.mkdir(parents=True)
    (scen / "proposals-rejected.json").write_text(json.dumps(
        {"author": "llm", "rejected": [{"ruleId": "s1", "reason": "schema"}], "note": "x"}), encoding="utf-8")
    run = tmp_path / "runs" / "r2"
    run.mkdir(parents=True)
    (run / "norm-llm-ledger.json").write_text(json.dumps([{"id": "NC-1", "reason": "unreachable"}]), encoding="utf-8")
    out = obs.read_ledger_observations(tmp_path)
    assert len(out) == 2
    assert all(o["type"] == "ledger_reject" for o in out)


def test_ledger_empty_rejected_list_is_no_observation(tmp_path: Path) -> None:
    scen = tmp_path / "scenario-runs" / "r1"
    scen.mkdir(parents=True)
    (scen / "proposals-rejected.json").write_text(json.dumps({"author": "llm", "rejected": [], "note": "x"}), encoding="utf-8")
    assert obs.read_ledger_observations(tmp_path) == []


def test_golden_drift_from_diff_file(tmp_path: Path) -> None:
    p = tmp_path / "golden-diff.json"
    p.write_text(json.dumps({"ranAt": "nu", "tracks": {
        "wind": {"pass": True, "iou": 1.0},
        "zon": {"pass": False, "iou": 0.99, "verdictsEqual": False},
    }}), encoding="utf-8")
    out = obs.read_golden_drift(p)
    assert len(out) == 1 and "zon" in out[0]["detail"]


def test_golden_drift_missing_file_is_empty(tmp_path: Path) -> None:
    assert obs.read_golden_drift(tmp_path / "bestaatniet.json") == []


def test_defaults_table_covers_all_types() -> None:
    assert set(obs.DEFAULTS) == {"journal_error", "hitl_needs_human", "ledger_reject", "golden_drift"}


def test_to_trail_fills_b10_defaults() -> None:
    observation = obs._obs("golden_drift", "poc/eval/golden-diff.json", "track zon: drift", {"runId": "r"})
    trail = obs.to_trail(observation)
    assert trail["why"] == obs.DEFAULTS["golden_drift"]["why"]
    assert trail["whatShouldChange"] == obs.DEFAULTS["golden_drift"]["whatShouldChange"]
    assert trail["trailId"].startswith("dt-")
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_memory_observations.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer `nldt/services/memory/observations.py`**

```python
"""Observation-extractors: lees de episodische laag, lever triggers (v1 automatische bronnen).

Pure functies met injecteerbare paden; afwezige bronnen leveren een lege
lijst (nooit een fout). De waardentabel per observationType is vast en
citeerbaar — geen LLM-tekstgeneratie (selection, not generation).
Bronpaden in observations worden repo-relatief genormaliseerd zodat
trailId's machine-onafhankelijk zijn.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
NLDT_ROOT = REPO_ROOT / "nldt"
POC_ROOT = REPO_ROOT / "poc"

DEFAULTS: dict[str, dict[str, str]] = {
    "journal_error": {
        "what": "Process-executie faalde met een fout (journal, process_result/error).",
        "why": "Onbekend — het proces faalde; oorzaak ligt in de procesimplementatie of de invoer.",
        "whatShouldChange": "Oorzaak analyseren; bij herhaling proces of invoer verbeteren.",
    },
    "hitl_needs_human": {
        "what": "Validatie-verdict needs_human: de keten wacht op een menselijk oordeel (V4/HITL).",
        "why": "RiskLevel hoog of het V4-verdict vraagt expliciete menselijke beoordeling.",
        "whatShouldChange": "Menselijk oordeel vastleggen; terugkerende redenen zijn kandidaat voor procedureverduidelijking.",
    },
    "ledger_reject": {
        "what": "Een LLM-proposal is afgewezen door een gate (cite-or-abstain ledger).",
        "why": "De proposal voldeed niet aan schema-, grounding- of budget-gate; hij is nooit uitgevoerd.",
        "whatShouldChange": "Patronen in afwijzingen reviewen; terugkerende afwijzingen wijzen op prompt- of schema-onderhoud.",
    },
    "golden_drift": {
        "what": "Golden-regressie wijst drift op: een of meer canonieke tracks diffen tegen de frozen goldens.",
        "why": "Een pipeline-, prompt- of modelwijziging veranderde de canonieke output.",
        "whatShouldChange": "Drift beoordelen: goldens vervangen bij intentionele wijziging, anders de wijziging terugdraaien.",
    },
}


def _rel(path: Path) -> str:
    """Repo-relatief als mogelijk — trailId blijft dan machine-onafhankelijk."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _obs(type_: str, source: str, detail: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    o: dict[str, Any] = {"type": type_, "source": source, "detail": detail}
    if provenance:
        clean = {k: v for k, v in provenance.items() if v}
        if clean:
            o["provenance"] = clean
    return o


def read_journal_errors(journal_path: Path | None = None) -> list[dict[str, Any]]:
    from services.process_adapter.journal import journal_path as default_journal_path

    path = journal_path or default_journal_path()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("kind") == "process_result" and entry.get("status") == "error":
            out.append(_obs(
                "journal_error",
                _rel(path),
                f"{entry.get('agent')}: {entry.get('summary')}",
                {"jobId": entry.get("jobId"), "agent": entry.get("agent")},
            ))
    return out


def read_hitl_observations(runs_root: Path | None = None) -> list[dict[str, Any]]:
    root = runs_root or NLDT_ROOT / "data" / "runs"
    out = []
    if not root.is_dir():
        return out
    for vfile in sorted(root.glob("*/validation.json")):
        try:
            report = json.loads(vfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(report, dict) and report.get("verdict") == "needs_human":
            out.append(_obs(
                "hitl_needs_human",
                _rel(vfile),
                f"validation verdict needs_human (artifactId={report.get('artifactId')})",
                {"runId": vfile.parent.name},
            ))
    return out


def _ledger_entries(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    if isinstance(data, dict) and isinstance(data.get("rejected"), list):
        return [e for e in data["rejected"] if isinstance(e, dict)]
    return []


def read_ledger_observations(poc_root: Path | None = None) -> list[dict[str, Any]]:
    root = poc_root or POC_ROOT
    out = []
    patterns = [
        "scenario-runs/*/proposals-rejected.json",
        "runs/*/norm-llm-ledger.json",
        "llm-runs/*/norm-llm-ledger.json",
    ]
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            for entry in _ledger_entries(path):
                out.append(_obs("ledger_reject", _rel(path), json.dumps(entry, ensure_ascii=False)[:300]))
    return out


def read_golden_drift(diff_path: Path | None = None) -> list[dict[str, Any]]:
    path = diff_path or POC_ROOT / "eval" / "golden-diff.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for track, result in (data.get("tracks") or {}).items():
        if isinstance(result, dict) and result.get("pass") is False:
            out.append(_obs("golden_drift", _rel(path), f"track {track}: {json.dumps(result, ensure_ascii=False)[:200]}"))
    return out


def collect_observations() -> list[dict[str, Any]]:
    return read_journal_errors() + read_hitl_observations() + read_ledger_observations() + read_golden_drift()


def to_trail(observation: dict[str, Any]) -> dict[str, Any]:
    from services.memory.store import make_trail

    defaults = DEFAULTS.get(observation.get("type", ""), {})
    return make_trail(
        observation,
        what=defaults.get("what", observation.get("detail", "")),
        why=defaults.get("why", ""),
        what_should_change=defaults.get("whatShouldChange", ""),
    )
```

Let op: `test_to_trail_fills_b10_defaults` zet géén env — `make_trail` schrijft niets (alleen `append_trails` doet dat), dus de test is zuiver in-memory.

- [ ] **Step 4: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_memory_observations.py -q` → `10 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/memory/observations.py nldt/tests/test_memory_observations.py
git commit -m "feat(nldt): observation-extractors — journal-errors, HITL-verdicts, ledger-rejects, golden-drift + vaste B10-waardentabel"
```

### Task 3: Consolidatie-CLI (`consolidate.py`)

**Files:**
- Create: `nldt/services/memory/consolidate.py`
- Test: `nldt/tests/test_memory_consolidate.py`

**Interfaces:**
- Consumes: Task 1 (`append_trails`, `update_trail`, `load_trails`), Task 2 (`collect_observations`, `to_trail`).
- Produces: `consolidate() -> int` (nieuwe trails; retourneert 0), `main(argv=None) -> int` met `--handle <trailId> --note "…"`, `--promote <trailId> --level organisatie|institutioneel`.

- [ ] **Step 1: Schrijf de falende tests**

```python
# nldt/tests/test_memory_consolidate.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import consolidate, store


@pytest.fixture
def memory_env(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "trails"
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(d))
    return d


@pytest.fixture
def journal_with_error(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "steps.jsonl"
    p.write_text(json.dumps({
        "ts": "10:00:01", "kind": "process_result", "agent": "run_opportunity_map",
        "status": "error", "summary": "KeyError: 'useCase'", "jobId": "j2",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(p))
    return p


def test_consolidate_writes_trails_and_is_idempotent(memory_env, journal_with_error) -> None:
    assert consolidate.consolidate() == 0
    trails = store.load_trails()
    journal_trails = [t for t in trails if t["observation"]["type"] == "journal_error"]
    assert len(journal_trails) == 1 and journal_trails[0]["status"] == "open"
    count_before = len(trails)
    assert consolidate.consolidate() == 0
    assert len(store.load_trails()) == count_before  # dedup op trailId


def test_handle_sets_status_and_did_it_help(memory_env, journal_with_error, capsys) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    rc = consolidate.main(["--handle", trail["trailId"], "--note", "opgelost door invoerfix"])
    assert rc == 0
    updated = store.load_trails()[0]
    assert updated["status"] == "handled" and updated["didItHelp"] == "opgelost door invoerfix"


def test_handle_requires_note(memory_env, journal_with_error) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    with pytest.raises(SystemExit):
        consolidate.main(["--handle", trail["trailId"]])


def test_promote_sets_learning_level(memory_env, journal_with_error) -> None:
    consolidate.consolidate()
    trail = store.load_trails()[0]
    rc = consolidate.main(["--promote", trail["trailId"], "--level", "organisatie"])
    assert rc == 0
    assert store.load_trails()[0]["learningLevel"] == "organisatie"


def test_unknown_trail_returns_one(memory_env) -> None:
    assert consolidate.main(["--handle", "dt-00000000", "--note", "x"]) == 1
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_memory_consolidate.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer `nldt/services/memory/consolidate.py`**

```python
"""Consolidatie: observaties → decision trails (idempotent) + afhandelacties.

    python -m services.memory.consolidate                          # nieuwe observaties → trails
    python -m services.memory.consolidate --handle dt-xxxx --note "…"
    python -m services.memory.consolidate --promote dt-xxxx --level organisatie
"""
from __future__ import annotations

import argparse

from services.memory.observations import collect_observations, to_trail
from services.memory.store import append_trails, update_trail


def consolidate() -> int:
    trails = [to_trail(o) for o in collect_observations()]
    written = append_trails(trails)
    print(f"{len(trails)} observatie(n), {written} nieuwe trail-record(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="services.memory.consolidate")
    parser.add_argument("--handle", metavar="TRAIL_ID", help="trail afhandelen (status → handled)")
    parser.add_argument("--note", metavar="NOTE", help="didItHelp-waarde bij --handle")
    parser.add_argument("--promote", metavar="TRAIL_ID", help="trail promoten naar hoger leerniveau")
    parser.add_argument("--level", choices=["organisatie", "institutioneel"], help="doel-niveau bij --promote")
    args = parser.parse_args(argv)

    if args.handle:
        if not args.note:
            parser.error("--handle vereist --note")
        updated = update_trail(args.handle, status="handled", did_it_help=args.note)
        if updated is None:
            print(f"trail {args.handle} niet gevonden")
            return 1
        print(f"handled: {updated['trailId']} → didItHelp: {updated['didItHelp']}")
        return 0

    if args.promote:
        if not args.level:
            parser.error("--promote vereist --level")
        updated = update_trail(args.promote, learning_level=args.level)
        if updated is None:
            print(f"trail {args.promote} niet gevonden")
            return 1
        print(f"promoted: {updated['trailId']} → {updated['learningLevel']}")
        return 0

    return consolidate()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_memory_consolidate.py -q` → `5 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/memory/consolidate.py nldt/tests/test_memory_consolidate.py
git commit -m "feat(nldt): consolidatie-CLI — observaties → trails idempotent, --handle en --promote"
```

### Task 4: Leerrapport (`report.py`)

**Files:**
- Create: `nldt/services/memory/report.py`
- Test: `nldt/tests/test_memory_report.py`

**Interfaces:**
- Consumes: Task 1 (`load_trails`).
- Produces: `PROMOTION_THRESHOLD = 3`, `promote_candidates(trails: list[dict]) -> list[str]` (gesorteerde `"operationeel:<type>"`-strings), `main(argv=None) -> int` (console-rapport, exit 0).

- [ ] **Step 1: Schrijf de falende tests**

```python
# nldt/tests/test_memory_report.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.memory import report, store

TRAIL = {
    "trailId": "dt-11111111", "observation": {"type": "journal_error", "source": "s", "detail": "d"},
    "what": "w", "why": "o", "whatShouldChange": "v", "whoDecides": "operator",
    "didItHelp": None, "learningLevel": "operationeel", "status": "open", "createdAt": "2026-10-07T00:00:00+00:00",
}


def _trail(**over) -> dict:
    t = json.loads(json.dumps(TRAIL))
    t.update(over)
    return t


def test_promote_candidates_threshold_and_level() -> None:
    trails = [_trail(trailId=f"dt-{i:08d}", observation={"type": "journal_error", "source": "s", "detail": "d"}) for i in range(3)]
    trails.append(_trail(trailId="dt-99999999", observation={"type": "hitl_needs_human", "source": "s", "detail": "d"}))
    trails.append(_trail(trailId="dt-99999998", observation={"type": "journal_error", "source": "s", "detail": "d"}, status="handled"))
    assert report.promote_candidates(trails) == ["operationeel:journal_error"]


def test_promote_candidates_ignores_non_operational() -> None:
    trails = [_trail(trailId=f"dt-{i:08d}", observation={"type": "journal_error", "source": "s", "detail": "d"}, learningLevel="organisatie") for i in range(3)]
    assert report.promote_candidates(trails) == []


def test_report_main_runs_on_empty_store(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(tmp_path / "trails"))
    assert report.main([]) == 0
    assert "0 trail-record(s)" in capsys.readouterr().out


def test_report_main_lists_open_items(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("NLDT_MEMORY_DIR", str(tmp_path / "trails"))
    store.append_trails([_trail()])
    assert report.main([]) == 0
    out = capsys.readouterr().out
    assert "open (1)" in out and "dt-11111111" in out
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_memory_report.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer `nldt/services/memory/report.py`**

```python
"""Leerrapport (retrieval v1): aggregatie per leerniveau/observationType/status.

    python -m services.memory.report
"""
from __future__ import annotations

import collections
from typing import Any

from services.memory.store import load_trails

PROMOTION_THRESHOLD = 3


def promote_candidates(trails: list[dict[str, Any]]) -> list[str]:
    """Observatietypen met ≥ PROMOTION_THRESHOLD open trails op operationeel niveau."""
    counter = collections.Counter(
        (t["observation"]["type"], t["learningLevel"])
        for t in trails
        if t["status"] == "open"
    )
    return sorted(
        f"operationeel:{type_}"
        for type_, level in counter
        if counter[(type_, level)] >= PROMOTION_THRESHOLD and level == "operationeel"
    )


def report() -> int:
    trails = load_trails()
    print(f"{len(trails)} trail-record(s)")
    if not trails:
        return 0
    by_level = collections.Counter(t["learningLevel"] for t in trails)
    by_type = collections.Counter(t["observation"]["type"] for t in trails)
    print(f"per leerniveau: {dict(by_level)}")
    print(f"per observationType: {dict(by_type)}")
    open_items = [t for t in trails if t["status"] == "open"]
    print(f"\nopen ({len(open_items)}):")
    for t in open_items:
        print(f"  {t['trailId']} [{t['learningLevel']}/{t['observation']['type']}] {t['what'][:80]}")
    candidates = promote_candidates(trails)
    if candidates:
        print("\npromotie-kandidaten (≥3 open op operationeel):")
        for candidate in candidates:
            print(f"  {candidate}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_memory_report.py -q` → `4 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/memory/report.py nldt/tests/test_memory_report.py
git commit -m "feat(nldt): leerrapport — aggregatie per leerniveau/type/status met promotie-kandidaten"
```

### Task 5: Golden-diff-runner (`poc/eval/golden_report.py`)

**Files:**
- Create: `poc/eval/golden_report.py`
- Test: `poc/tests/test_golden_report.py`

**Interfaces:**
- Consumes: `pytest -m golden` (bestaand, taak van de eval-harness).
- Produces: `parse_pytest_output(text: str) -> dict[str, dict]` (track → `{pass: bool}`) en `main(argv=None) -> int` (draait pytest `-m golden -v`, schrijft `poc/eval/golden-diff.json` = `{"ranAt": iso, "tracks": {...}}`, retourneert de pytest-exitcode). De consolidator leest dit bestand als `golden_drift`-bron (Task 2).

- [ ] **Step 1: Schrijf de falende test** (parser only — geen subprocess in de suite)

```python
# poc/tests/test_golden_report.py
from __future__ import annotations

import sys
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

sys.path.insert(0, str(POC_ROOT / "eval"))

from golden_report import parse_pytest_output  # noqa: E402

SAMPLE = (
    "poc/tests/test_golden_regression.py::test_golden_regression[wind] PASSED [  7%]\n"
    "poc/tests/test_golden_regression.py::test_golden_regression[zon] PASSED [ 15%]\n"
    "poc/tests/test_golden_regression.py::test_golden_regression[biomassa] FAILED [100%]\n"
    "=== 12 passed, 1 failed ===\n"
)


def test_parse_extracts_track_results() -> None:
    tracks = parse_pytest_output(SAMPLE)
    assert tracks["wind"]["pass"] is True
    assert tracks["biomassa"]["pass"] is False
    assert set(tracks) == {"wind", "zon", "biomassa"}


def test_parse_empty_output() -> None:
    assert parse_pytest_output("") == {}
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_golden_report.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer `poc/eval/golden_report.py`**

```python
"""Draait de golden-regressie en leg per-track resultaten vast als
poc/eval/golden-diff.json — de observatiebron voor golden_drift-consolidatie.

Op verzoek draaien, nooit onderdeel van de standaard consolidatie:

    python3 poc/eval/golden_report.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
OUT = POC_ROOT / "eval" / "golden-diff.json"

_TRACK_LINE = re.compile(r"test_golden_regression\[(\w+)\] (PASSED|FAILED)")


def parse_pytest_output(text: str) -> dict[str, dict]:
    tracks: dict[str, dict] = {}
    for match in _TRACK_LINE.finditer(text):
        tracks[match.group(1)] = {"pass": match.group(2) == "PASSED"}
    return tracks


def main(argv: list[str] | None = None) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-m", "golden", "-v"],
        cwd=POC_ROOT,
        capture_output=True,
        text=True,
    )
    tracks = parse_pytest_output(result.stdout)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "ranAt": datetime.now(timezone.utc).isoformat(),
        "tracks": tracks,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(tracks)} track-resultaat(en) → {OUT}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Draai, verwacht PASS** — `../nldt/.venv/bin/python -m pytest tests/test_golden_report.py -q` → `2 passed`.

- [ ] **Step 5: Eénmalige live-smoke (handmatig)** — `../nldt/.venv/bin/python eval/golden_report.py` → schrijft `eval/golden-diff.json` met 13 tracks, exitcode 0; daarna `cd ../nldt && .venv/bin/python -m services.memory.consolidate` → meldt 13 observaties (golden_drift? nee: alle tracks pass → 0 observaties; verwacht `0 observatie(n), 0 nieuwe trail-record(s)`). Dit bevestigt de kring: runner → diff-bestand → consolidator, zonder drift.

- [ ] **Step 6: Genereerd artefact gitignoren** — voeg `poc/eval/golden-diff.json` toe aan `.gitignore` (append):

```
poc/eval/golden-diff.json
```

- [ ] **Step 7: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add poc/eval/golden_report.py poc/tests/test_golden_report.py .gitignore
git commit -m "feat(poc): golden-diff-runner — pytest -m golden vastgelegd als observation-bron voor de consolidatie"
```

### Task 6: Koppeling plan + eindverificatie + push

**Files:**
- Modify: `docs/AGENTIC_STATE_PLAN.md` (fase E-blok: decision-trail-notitie)
- Modify: `poc/README.md` (eval-regressie-notitie uitgebreid met de memory-kring, één regel)

- [ ] **Step 1: Fase-E-notitie** — in `docs/AGENTIC_STATE_PLAN.md`, in het fase E-blok, vervang de regel `- Decision trail (B10) bovenop journal + PROV; eerste leerrapport over de drie niveaus (operationeel/organisatorisch/institutioneel).` door:

```markdown
- Decision trail (B10): **vervroegd en geland** in `nldt/services/memory/` (spec
  `docs/superpowers/specs/2026-10-07-decision-trail-memory-design.md`) — automatische observaties
  (journal-errors, HITL-verdicts, ledger-rejects, golden-drift) → durabele, schema-gedwongen
  trail-records met de drie leerniveaus; consolidatie + leerrapport via
  `python -m services.memory.consolidate` / `report`. Fase E houdt restant: menselijke
  observatie-invoer, promotieproces met de beslispuntenkalender, eerste leerrapport over de
  demonstrator.
```

- [ ] **Step 2: README-notitie** — in `poc/README.md`, direct onder de bestaande "Eval-regressie (golden)"-paragraaf, voeg toe:

```markdown
Leerstaat (decision trails): `python3 -m services.memory.consolidate` (uit `nldt/`) zet
automatische observaties (o.a. golden-drift via `eval/golden_report.py`, journal-errors,
HITL-verdicts, ledger-rejects) om in durabele decision-trail-records met leerniveau;
`python3 -m services.memory.report` geeft het leerrapport (`--handle`/`--promote` voor afhandeling).
```

- [ ] **Step 3: Eindverificatie**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q   # 390 passed (365 + 25 nieuwe)
cd ../poc && ../nldt/.venv/bin/python -m pytest tests -q                          # 304 passed, 1 skipped (302 + 2 golden-report)
../nldt/.venv/bin/python -m pytest tests -m golden -q                             # 13 passed
PYTHONPATH=../nldt ../nldt/.venv/bin/python -m services.memory.report             # rapport draait op de echte store
```

- [ ] **Step 4: Commit + push**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add docs/AGENTIC_STATE_PLAN.md poc/README.md
git commit -m "docs: fase E-notitie decision trail vervroegd + README-leerstaat-kring"
git push origin main
```
