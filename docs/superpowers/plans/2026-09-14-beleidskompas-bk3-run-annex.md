# Beleidskompas BK-3 (partial: S9 run annex + hardening) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the buildable core of BK-3 from [`nldt/14-beleidskompas-integration.md`](../../../nldt/14-beleidskompas-integration.md) §6/§8: the **S9 run-annex generator** (traceability annex for policy documents — every nLDT number in an exported document traces to a jobId + PROV), plus the deferred BK-1 hardening sweep. HITL mapping, OTel propagation and Keycloak client provisioning stay open (they need a real consumer / IM instance) and are marked as such in the docs task.

**Architecture:** `services/run_annex.py` turns recipe executions (the dict `run_recipe` returns: recipeId, steps[] with jobId + prov each, outputs) into a deterministic, schema-validated annex document plus a Markdown rendering for attachment to Word/PDF exports. Determinism is the contract: same executions in → byte-identical annex out (no wall-clock fields), matching the receipt-trail doctrine. A `build-run-annex` CLI command consumes saved execution JSON files (`export-context` precedent). The hardening sweep touches only `services/common/auth.py`, its tests, and one seed tag.

**Tech Stack:** Python, jsonschema Draft 2020-12, pytest — all existing.

**Spec:** integration plan §6 (seam S9 definition), §8 BK-3. Ledger backlog: `.superpowers/sdd/progress.md` BK-0/BK-1 section ("Deferred minors").

## Global Constraints

- Repo root `/Users/marc/Projecten/ldttoolbox`; commands from `nldt/` with `PYTHONPATH=.`; venv `nldt/.venv`.
- **No new dependencies.** No wall-clock/timezone fields in the annex (determinism). Existing 151 tests stay green.
- Schema style per `schemas/recipe.schema.json` (draft 2020-12, `$id` under `https://ldttoolbox.example/nldt/schemas/`, `additionalProperties: false`).
- Commits prefixed `BK-3:`; per task; never `git add -A` (user WIP in tree). Live services (:8081-8085, :8090-8093, Docker) untouched — no restarts needed for these tasks.

---

### Task 1: S9 run-annex generator — schema, module, CLI, tests

**Files:**
- Create: `nldt/schemas/run-annex.schema.json`
- Create: `nldt/services/run_annex.py`
- Modify: `nldt/services/cli.py` (one subcommand)
- Test: `nldt/tests/test_run_annex.py`

**Interfaces:**
- Consumes: execution dicts from `services.recipe_runner.run_recipe` (shape: `{"recipeId", "inputs", "steps": [{"stepId", "processId", "jobId", "outputs", "prov"}], "outputs"}`); optional `"validation_report"` key when produced by the orchestrator path.
- Produces: `build_run_annex(executions: list[dict]) -> dict`; `render_annex_markdown(annex: dict) -> str`; CLI `build-run-annex execution.json [...] [--out FILE]`.

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_run_annex.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common.schema import validate_instance
from services.process_adapter.jobs import create_job
from services.recipe_runner import run_recipe
from services.run_annex import build_run_annex, render_annex_markdown

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class InProcessClient:
    """ProcessClient stand-in that executes locally in-process (real jobs)."""

    def execute(self, process_id, inputs, backend="local"):
        return create_job(process_id, inputs, backend=backend)


@pytest.fixture
def execution():
    return run_recipe(
        "beleidskompas-omgevingsanalyse",
        {
            "aoi": json.loads((EXAMPLES / "aoi.geojson").read_text()),
            "layerAUri": f"file://{EXAMPLES / 'layer-a.geojson'}",
            "layerBUri": f"file://{EXAMPLES / 'layer-b.geojson'}",
        },
        process_client=InProcessClient(),
    )


def test_annex_schema_valid_and_deterministic(execution):
    a1 = build_run_annex([execution])
    a2 = build_run_annex([json.loads(json.dumps(execution))])
    assert a1 == a2
    validate_instance(a1, "run-annex.schema.json")
    assert a1["runs"][0]["recipeId"] == "beleidskompas-omgevingsanalyse"


def test_annex_carries_job_ids_and_prov(execution):
    annex = build_run_annex([execution])
    steps = annex["runs"][0]["steps"]
    assert len(steps) == 4
    for s in steps:
        assert s["jobId"]
        assert "startedAtTime" in s["prov"]


def test_annex_includes_validation_report_when_present(execution):
    execution["validation_report"] = {"verdict": "pass"}
    annex = build_run_annex([execution])
    assert annex["runs"][0]["validationReport"] == {"verdict": "pass"}


def test_markdown_renders_every_job(execution):
    annex = build_run_annex([execution])
    md = render_annex_markdown(annex)
    assert "beleidskompas-omgevingsanalyse" in md
    for s in annex["runs"][0]["steps"]:
        assert s["jobId"] in md


def test_cli_build_run_annex(tmp_path, execution):
    from services.cli import main

    exec_file = tmp_path / "exec.json"
    exec_file.write_text(json.dumps(execution))
    out = tmp_path / "annex.md"
    rc = main(["build-run-annex", str(exec_file), "--out", str(out)])
    assert rc == 0
    assert "beleidskompas-omgevingsanalyse" in out.read_text()
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_run_annex.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'services.run_annex'`.

- [ ] **Step 3: Create the schema**

Create `nldt/schemas/run-annex.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.example/nldt/schemas/run-annex.schema.json",
  "title": "Run annex (seam S9)",
  "description": "Traceability annex for policy documents produced in an external front door: per-run receipts (recipe, step jobIds, PROV bundles, validation verdicts). Deterministic for identical executions — no wall-clock fields. Every spatial number quoted in the document must trace to an entry here (nldt/14-beleidskompas-integration.md §6).",
  "type": "object",
  "additionalProperties": false,
  "required": ["annexVersion", "runs"],
  "properties": {
    "annexVersion": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "runs": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/run" }
    }
  },
  "$defs": {
    "run": {
      "type": "object",
      "additionalProperties": false,
      "required": ["recipeId", "steps", "outputKeys"],
      "properties": {
        "recipeId": { "type": "string", "minLength": 1 },
        "steps": {
          "type": "array",
          "items": { "$ref": "#/$defs/step" }
        },
        "outputKeys": {
          "type": "array",
          "items": { "type": "string" },
          "uniqueItems": true
        },
        "validationReport": { "type": "object" }
      }
    },
    "step": {
      "type": "object",
      "additionalProperties": false,
      "required": ["stepId", "processId", "jobId", "prov"],
      "properties": {
        "stepId": { "type": "string", "minLength": 1 },
        "processId": { "type": "string", "minLength": 1 },
        "jobId": { "type": ["string", "null"] },
        "prov": { "type": "object" },
        "startedAt": { "type": "string" },
        "finishedAt": { "type": "string" }
      }
    }
  }
}
```

- [ ] **Step 4: Implement `services/run_annex.py`**

```python
"""S9 run annex — traceability receipts for policy documents (BK-3).

Given recipe executions (services.recipe_runner.run_recipe shape), build a
deterministic annex document: every spatial number in an exported policy
document must trace to a step jobId + PROV bundle recorded here. Identical
executions produce an identical annex — no wall-clock fields — so an annex
re-generated after an offline replay must match byte-for-byte.
"""

from __future__ import annotations

import json
from typing import Any

ANNEX_VERSION = "1.0.0"


def build_run_annex(executions: list[dict[str, Any]]) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for ex in executions:
        run: dict[str, Any] = {
            "recipeId": ex.get("recipeId", ""),
            "steps": [
                {
                    "stepId": s.get("stepId", ""),
                    "processId": s.get("processId", ""),
                    "jobId": s.get("jobId"),
                    "prov": s.get("prov") or {},
                }
                for s in ex.get("steps", [])
            ],
            "outputKeys": sorted(ex.get("outputs", {}).keys()),
        }
        if isinstance(ex.get("validation_report"), dict):
            run["validationReport"] = ex["validation_report"]
        runs.append(run)
    return {"annexVersion": ANNEX_VERSION, "runs": runs}


def render_annex_markdown(annex: dict[str, Any]) -> str:
    lines = [
        "## Annex: nLDT run receipts (seam S9)",
        "",
        "Every spatial figure in this document traces to the engine runs below",
        "(jobId + PROV). Runs replay offline and bit-identically via",
        "`PYTHONPATH=. python -m services.cli run-recipe <recipeId>`.",
        "",
    ]
    for run in annex.get("runs", []):
        lines.append(f"### Recipe: {run['recipeId']}")
        lines.append("")
        lines.append("| Step | Process | Job ID |")
        lines.append("|---|---|---|")
        for s in run["steps"]:
            lines.append(f"| {s['stepId']} | {s['processId']} | {s['jobId']} |")
        if "validationReport" in run:
            lines.append("")
            lines.append(f"Validation: `{json.dumps(run['validationReport'], sort_keys=True)}`")
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 5: Add the CLI subcommand**

In `nldt/services/cli.py`, add after `cmd_export_context`:

```python
def cmd_build_run_annex(args: argparse.Namespace) -> int:
    from services.run_annex import build_run_annex, render_annex_markdown

    executions = []
    for path in args.execution_file:
        with Path(path).open(encoding="utf-8") as f:
            executions.append(json.load(f))
    annex = build_run_annex(executions)
    md = render_annex_markdown(annex)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(json.dumps(annex, indent=2))
    return 0
```

And in `main()` after the `p_ctx` block:

```python
    p_annex = sub.add_parser(
        "build-run-annex", help="Build S9 run annex (JSON + Markdown) from execution JSON files"
    )
    p_annex.add_argument("execution_file", nargs="+")
    p_annex.add_argument("--out", help="Write Markdown annex to this path")
    p_annex.set_defaults(func=cmd_build_run_annex)
```

- [ ] **Step 6: Run to verify pass, then full suite**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_run_annex.py -q
PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: `5 passed`, then 156 total (151 + 5).

- [ ] **Step 7: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/schemas/run-annex.schema.json nldt/services/run_annex.py nldt/services/cli.py nldt/tests/test_run_annex.py
git commit -m "BK-3: S9 run-annex generator (deterministic receipts, schema + CLI)"
```

---

### Task 2: BK-1 hardening sweep (auth + seed tag)

**Files:**
- Modify: `nldt/services/common/auth.py` (constant-time compare; introspection TTL cache)
- Modify: `nldt/services/catalog_adapter/seed.py` (breda-scan-qa tuple gains `legal` tag)
- Test: `nldt/tests/test_auth.py` (append), `nldt/tests/test_beleidskompas.py` (one assertion)

**Interfaces:**
- Consumes: `require_bearer` semantics unchanged (401/503/500, fail-closed, WWW-Authenticate).
- Produces: `_static_tokens` unchanged; static check via `hmac.compare_digest` per token; `introspect_keycloak` results cached per token for `INTROSPECTION_CACHE_TTL` (30 s default, env `NLDT_INTROSPECTION_CACHE_TTL` overrides; cache keyed by SHA-256 of the token — never store raw tokens).

- [ ] **Step 1: Write the failing tests** — append to `nldt/tests/test_auth.py`:

```python
def test_lowercase_bearer_scheme_accepted(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    resp = guarded_client.get("/ping", headers={"Authorization": "bearer tok-a"})
    assert resp.status_code == 200


def test_keycloak_missing_config_is_503_without_network(guarded_client, monkeypatch):
    for var in (
        "KEYCLOAK_URL",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
        "KEYCLOAK_INTROSPECT_CLIENT_ID",
        "KEYCLOAK_INTROSPECT_CLIENT_SECRET",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "token introspection unavailable"


def test_introspection_result_is_cached(monkeypatch):
    import asyncio

    import services.common.auth as auth

    calls = {"n": 0}

    async def counting(token: str) -> bool:
        calls["n"] += 1
        return True

    monkeypatch.setattr(auth, "introspect_keycloak", counting)
    monkeypatch.delenv("NLDT_INTROSPECTION_CACHE_TTL", raising=False)
    auth.clear_introspection_cache()
    assert asyncio.run(auth.cached_introspect("t1")) is True
    assert asyncio.run(auth.cached_introspect("t1")) is True
    assert calls["n"] == 1
    auth.clear_introspection_cache()
```

And in `nldt/tests/test_beleidskompas.py`, extend `test_scan_qa_recipe_tagged_for_beleidskompas` with:

```python
    assert "legal" in tags
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_auth.py tests/test_beleidskompas.py -q
```

Expected: FAIL — `AttributeError: clear_introspection_cache` / `cached_introspect`; `legal` assertion fails.

- [ ] **Step 3: Implement in `services/common/auth.py`**

Add to the imports: `import hashlib`, `import hmac`, `import time`. Add after `_static_tokens()`:

```python
_INTROSPECTION_CACHE: dict[str, tuple[float, bool]] = {}


def clear_introspection_cache() -> None:
    _INTROSPECTION_CACHE.clear()


async def cached_introspect(token: str) -> bool:
    """RFC 7662 introspection with a short per-token cache (keyed by SHA-256)."""
    ttl = float(os.environ.get("NLDT_INTROSPECTION_CACHE_TTL", "30"))
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _INTROSPECTION_CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    active = await introspect_keycloak(token)
    _INTROSPECTION_CACHE[key] = (time.time() + ttl, active)
    return active
```

In `require_bearer`'s keycloak branch, replace `active = await introspect_keycloak(token)` with `active = await cached_introspect(token)` (leave logging/503 handling identical). In the static branch, replace the membership test with:

```python
        ok = any(hmac.compare_digest(token, candidate) for candidate in _static_tokens())
        if not ok:
            raise _unauthorized("invalid token")
        return
```

In `seed.py`, change the `breda-scan-qa` recipe tuple tags to `["poc-breda", "qa", "s4", "scan", "legal", "beleidskompas", "policy-step:substantiation"]`.

- [ ] **Step 4: Run to verify pass, then full suite**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_auth.py tests/test_beleidskompas.py -q
PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: all auth + beleidskompas tests pass; full suite 159 (156 + 3).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/common/auth.py nldt/services/catalog_adapter/seed.py nldt/tests/test_auth.py nldt/tests/test_beleidskompas.py
git commit -m "BK-3: auth hardening (constant-time compare, introspection cache) + seed legal tag"
```

---

### Task 3: Docs — S9 status, BK-3 status, runbook annex section

**Files:**
- Modify: `docs/GENAI_SEAMS.md` (technical annex seam table: add S9 row)
- Modify: `nldt/14-beleidskompas-integration.md` (BK-3 status)
- Modify: `nldt/govchat/README.md` (annex how-to)

- [ ] **Step 1: GENAI_SEAMS annex table** — after the S8 row in the seam catalogue table, add:

```markdown
| S9 | policy-document narration in an external front door (grounded-artifact contract; deterministic run annex, schema `run-annex.schema.json`) | — (beleidskompas BK-3) | **generator implemented** (`nldt/services/run_annex.py` + CLI `build-run-annex`); Word/PDF attachment + number-grounding on the foreign platform's text still open (needs beleidskompas app code) |
```

- [ ] **Step 2: Integration plan BK-3 status** — under `### BK-3 — Governance hardening (S9)` add before the bullets:

```markdown
**Status:** partially done (2026-09-14) — S9 run-annex generator shipped
(deterministic receipts, `schemas/run-annex.schema.json`, CLI `build-run-annex`);
auth hardening swept (constant-time compare, introspection cache). Still open:
HITL/RBAC↔trustPolicy mapping, OTel propagation, Keycloak client (needs IM), and
the Word/PDF attachment + foreign-side number gate (needs beleidskompas code).
```

- [ ] **Step 3: Runbook annex section** — in `nldt/govchat/README.md`, after §3 add a §3a block:

```markdown
### 3a. Run annex for the policy document (S9)

Save a recipe execution, then generate the traceability annex (JSON + Markdown)
that travels with the exported document:

```bash
PYTHONPATH=. python -m services.cli run-recipe beleidskompas-omgevingsanalyse \
  --aoi-file examples/rijnsweerd/aoi.geojson \
  --input layerAUri=file://$(pwd)/examples/rijnsweerd/layer-a.geojson \
  --input layerBUri=file://$(pwd)/examples/rijnsweerd/layer-b.geojson \
  > /tmp/exec.json
PYTHONPATH=. python -m services.cli build-run-annex /tmp/exec.json --out annex.md
```

Beleidskompas (S9 contract): quote only figures that trace to an annex entry.
```

(Adjust the section numbering style to match the README's existing headings.)

- [ ] **Step 4: Full suite + commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: 159 passed.

```bash
cd /Users/marc/Projecten/ldttoolbox
git add docs/GENAI_SEAMS.md nldt/14-beleidskompas-integration.md nldt/govchat/README.md
git commit -m "BK-3: docs — S9 seam status, BK-3 partial, runbook annex how-to"
```

---

## Definition of done

- Annex: schema-valid, deterministic (no wall-clock), carries every step jobId + PROV, includes validationReport when present, Markdown renders all jobIds, CLI works end-to-end from a saved execution file. (Task 1)
- Hardening: constant-time static compare; 30 s introspection cache keyed by token hash with cache-clear; lowercase-scheme + missing-config + cache tests; `legal` tag parity between recipe JSON and seed. (Task 2)
- Docs: S9 in the seam catalogue with honest status; BK-3 partial status in the integration plan; runbook how-to. (Task 3)
- Suite green (159); no service restarts required; HITL/OTel/Keycloak explicitly marked open.
