# Beleidskompas BK-0 + BK-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute phases BK-0 (GovChat-NL connectivity spike) and BK-1 (governed MCP MVP with bearer auth) from [`nldt/14-beleidskompas-integration.md`](../../../nldt/14-beleidskompas-integration.md).

**Architecture:** BK-0 proves the HTTP path: run GovChat-NL (OpenWebUI) + n8n locally, bridge one chat question to `POST :8082` (OGC API Processes) and return a GeoJSON export URL from `:8084`. BK-1 makes the connection governed and MCP-native: an env-gated bearer-auth dependency on the FastAPI services (static tokens now, Keycloak introspection later), MCP servers that forward tokens on their outbound calls, and each MCP server additionally served over streamable-HTTP behind the same gate so a Dockerised n8n/OpenWebUI can mount it.

**Tech Stack:** Python 3 (FastAPI, httpx, `mcp` SDK with `MCPServer` supporting `stdio|sse|streamable-http`), pytest via `fastapi.testclient`, Docker (OpenWebUI fork of GovChat-NL, n8n), curl/jq.

**Spec:** [`nldt/14-beleidskompas-integration.md`](../../../nldt/14-beleidskompas-integration.md) §8 (BK-0, BK-1), §7 (identity), §10 (decisions 1–5).

## Global Constraints

- Repo root: `/Users/marc/Projecten/ldttoolbox`; nLDT code root: `nldt/`. All Python/pytest commands run from `nldt/` with `PYTHONPATH=.`; venv: `nldt/.venv`.
- **No new Python dependencies** — auth uses only fastapi/httpx already in `nldt/requirements.txt`.
- **Auth default OFF**: `NLDT_AUTH_MODE` unset/`off` must leave every existing test green and every service behave exactly as today.
- Auth modes: `off` (default) | `static` (env `NLDT_STATIC_TOKENS`, comma-separated; empty list denies all — fail closed) | `keycloak` (RFC 7662 introspection, reuses `KEYCLOAK_URL`/`KEYCLOAK_REALM`/`KEYCLOAK_CLIENT_ID`/`KEYCLOAK_CLIENT_SECRET` conventions from `services/adapters/keycloak_auth.py`).
- Protected services: cookbook `:8081`, process adapter `:8082`, catalog `:8083`, A2A `:8085`, MCP-over-HTTP ports `8090–8093`. **context3d `:8084` stays public by design** (export URLs are embedded in chat answers and viewers — recorded as a deviation from integration-plan §7, revisit with signed URLs later).
- **Keycloak client provisioning** (spec §7, client `beleidskompas-svc`) happens when a real Keycloak (EU LDT IM) is deployed; BK-1 ships the `keycloak` auth mode + runbook and uses a static token as the local MVP credential.
- Decisions (spec §10): MCP transport, local GovChat-NL instance, existing PoC areas (Breda/Utrecht), no GovChat-NL community contact during BK-0/BK-1, bridge/orchestration engine **Kestra** (decision 6: Apache-2.0, flow-as-code, per-task execution audit trail — n8n decommissioned in the testbed; nLDT seams are engine-agnostic).
- Commit messages: English, prefixed `BK-0:`/`BK-1:`. Commit per task.
-beleidskompas app code does not exist yet (docs only in GovChat-NL) — never couple to beleidskompas internals; couple to the GovChat-NL *platform* (OpenWebUI + n8n).

---

# Part 1 — BK-0: connectivity spike

### Task 1: Verify the nLDT side over plain HTTP (S4 answer + export URL)

Operational verification, no code. Everything later tasks rely on is proven here.

**Files:**
- Create: `nldt/govchat/BK0-FINDINGS.md` (findings log, filled further in Task 3)

- [ ] **Step 1: Start the nLDT services**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
./scripts/start-services.sh
```

Expected: after ~1s, `Ready: cookbook :8081, processes :8082, catalog :8083, context3d :8084, a2a :8085`.

- [ ] **Step 2: Verify the S4 grounded Q&A process over HTTP**

```bash
curl -s http://localhost:8082/processes/breda-scan-query -o /dev/null -w "%{http_code}\n"
curl -s -X POST http://localhost:8082/processes/breda-scan-query/execution \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"question": "Why does Belcrum score low on spatial value?"}, "backend": "local"}' | jq '{jobId, status, hasResult: (.outputs.result != null)}'
```

Expected: `200`, then a JSON object with `"status": "successful"` and `hasResult: true` (the run is grounded on the latest `poc-breda/runs/*-breda-scan` — five runs exist, e.g. `20260913T192628Z-breda-scan`). If status is `failed`, inspect `.outputs` and note the error in findings.

- [ ] **Step 3: Produce a public GeoJSON export URL**

`:8084/exports` expects `{"geojson": {...}}`, so wrap the example layer:

```bash
jq '{geojson: .}' nldt/examples/layer-a.geojson | curl -s -X POST http://localhost:8084/exports \
  -H 'Content-Type: application/json' -d @- | jq .
```

Expected: `{"exportId": "<12-hex>", "href": "/exports/<12-hex>.geojson"}`. Then fetch it and expect HTTP 200 + a FeatureCollection:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8084/exports/<12-hex>.geojson"
```

- [ ] **Step 4: Create the findings log**

Create `nldt/govchat/BK0-FINDINGS.md` (mkdir `nldt/govchat/` first):

```markdown
# BK-0 findings — GovChat-NL ↔ nLDT connectivity spike

Started: <date>. Decisions in force: nldt/14-beleidskompas-integration.md §10.

## nLDT side verified
- [ ] S4 Q&A over `POST :8082/processes/breda-scan-query/execution` — jobId: ____
- [ ] GeoJSON export via `POST :8084/exports` — export URL: ____

## GovChat-NL local instance
(fill in Task 2)

## n8n → nLDT bridge
(fill in Task 3)

## Deviations / surprises
- (none yet)
```

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/govchat/BK0-FINDINGS.md
git commit -m "BK-0: findings log for GovChat-NL connectivity spike"
```

---

### Task 2: Run GovChat-NL (OpenWebUI) and n8n locally

Operational setup. GovChat-NL is an OpenWebUI fork with a root `docker-compose.yaml`, `.env.example` and `run-compose.sh`; n8n is deployed separately (it is not in their compose files — Limburg runs it via Elestio), so we run the official n8n image ourselves.

**Files:** none in-repo (external tooling; record outcomes in findings).

- [ ] **Step 1: Clone and start GovChat-NL**

```bash
cd /Users/marc/Projecten  # keep ldttoolbox and the clone side by side
git clone https://github.com/jeannotdamoiseaux/GovChat-NL.git
cd GovChat-NL
cp .env.example .env
./run-compose.sh
```

Expected: Docker containers up (OpenWebUI on port 8080). If `run-compose.sh` needs flags, run `docker compose up -d` and consult `TROUBLESHOOTING.md` in their repo. **Port conflict:** nLDT services use 8081–8085, OpenWebUI defaults to 8080 — no overlap. If something else occupies 8080, set OpenWebUI's port mapping to `3000:8080` in `.env`/compose.

- [ ] **Step 2: Verify OpenWebUI is up**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/health
```

Expected: `200`. Register the initial admin account via the UI at http://localhost:8080 (first-run flow) and log in.

- [ ] **Step 3: Run n8n**

```bash
docker run -d --name bk0-n8n -p 5678:5678 \
  -e N8N_ENCRYPTION_KEY=dev-only-key \
  n8nio/n8n
```

Expected: container running; `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5678` returns `200`. Open the editor at http://localhost:5678 and create the owner account.

- [ ] **Step 4: Verify n8n (Docker) can reach the nLDT services on the host**

```bash
docker exec bk0-n8n sh -c "wget -q -O- http://host.docker.internal:8083/ && echo REACHABLE"
```

Expected: JSON landing of the catalog adapter + `REACHABLE`. (macOS Docker Desktop provides `host.docker.internal`; on Linux add `--add-host=host.docker.internal:host-gateway`.)

- [ ] **Step 5: Record in findings, commit**

Fill the *GovChat-NL local instance* section of `nldt/govchat/BK0-FINDINGS.md` (versions, ports, admin created, deviations). No repo code changed — nothing to commit unless findings live in-repo (they do):

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/govchat/BK0-FINDINGS.md
git commit -m "BK-0: GovChat-NL + n8n local instance verified"
```

---

### Task 3: Kestra bridge flow — webhook trigger → nLDT answer + export URL

The spike flow: webhook trigger → fetch features via OGC Processes → store as public GeoJSON export → return an answer containing the nLDT-produced URL. This is Option C (plain HTTP) from the integration plan — deliberately throwaway; BK-1 replaces the HTTP tasks with MCP. Engine: **Kestra** (decision 6, spec §10 — Apache-2.0, flow-as-code in git, per-task execution audit trail).

**Deviation from spec §8 BK-0:** the spec says "POST `spatial-overlay-analysis/execution`", but `spatial-overlay-analysis` is a *recipe* (4 process steps), not a process — that POST would 404. The spike therefore calls the simplest single Cook process (`fetch-features`); the full overlay flow is executed end-to-end in Task 8 via `run-recipe`. The spec also predates decision 6 (n8n → Kestra swap) and the OpenWebUI-chat surfacing being admin-gated: verification goes through Kestra's execution API, with the OpenWebUI connection recorded as a human step.

**Files:**
- Create: `nldt/govchat/kestra-bk0-bridge-flow.yaml`

- [ ] **Step 1: Decommission the n8n spike container**

```bash
docker rm -f bk0-n8n
```

- [ ] **Step 2: Run Kestra locally**

```bash
docker run -d --name bk0-kestra -p 8086:8080 \
  -v bk0-kestra-data:/app/storage \
  kestra/kestra:latest server local
```

UI/API at http://localhost:8086 (port 8086 — OpenWebUI owns 8080). If `server local` refuses on this image version (embedded DB removed in some releases), fall back to Kestra's documented docker-compose (postgres + kestra) and record it in findings. Wait for readiness: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8086/api/v1/stats` → `200`.

- [ ] **Step 3: Write the flow file**

Create `nldt/govchat/kestra-bk0-bridge-flow.yaml`:

```yaml
id: bk0-nldt-bridge
namespace: bk0
description: >
  BK-0 spike — webhook trigger -> nLDT fetch-features (OGC Processes) ->
  public GeoJSON export (:8084). Every execution is a durable audit record
  (per-task inputs/outputs) — see nldt/14-beleidskompas-integration.md.

triggers:
  - id: spike
    type: io.kestra.plugin.core.trigger.Webhook
    key: spike

tasks:
  - id: fetch_layer
    type: io.kestra.plugin.fs.http.Request
    uri: http://host.docker.internal:8082/processes/fetch-features/execution
    method: POST
    contentType: application/json
    body: |
      {
        "inputs": {
          "source": "file:///Users/marc/Projecten/ldttoolbox/nldt/examples/layer-a.geojson"
        },
        "backend": "local"
      }

  - id: publish_export
    type: io.kestra.plugin.fs.http.Request
    uri: http://host.docker.internal:8084/exports
    method: POST
    contentType: application/json
    body: |
      {"geojson": {{ (outputs['fetch_layer'].body | json)['outputs']['features'] }}}

  - id: answer
    type: io.kestra.plugin.core.debug.Return
    format: |
      nLDT job {{ (outputs['fetch_layer'].body | json).jobId }} succeeded.
      Public GeoJSON export: http://localhost:8084{{ (outputs['publish_export'].body | json).href }}

outputs:
  answer: "{{ outputs['answer'].value }}"
  jobId: "{{ (outputs['fetch_layer'].body | json).jobId }}"
  exportUrl: "http://localhost:8084{{ (outputs['publish_export'].body | json).href }}"
```

The Pebble expression helpers (`| json` filter, indexing) are written to the best of current knowledge — verify against the Kestra expression docs for the installed version and adjust until the flow validates; record the final working YAML (up to ~3 fix rounds before escalating).

- [ ] **Step 4: Import the flow**

```bash
curl -s -X POST http://localhost:8086/api/v1/flows \
  -H 'Content-Type: application/x-yaml' \
  --data-binary @nldt/govchat/kestra-bk0-bridge-flow.yaml
```

Expected: `200` with the flow JSON (or the documented validation error — fix and retry). If the API route differs in this version, use the CLI inside the container after `docker cp` (`docker exec bk0-kestra kestra flow update bk0 /tmp/flow.yaml`).

- [ ] **Step 5: Trigger and verify end-to-end**

```bash
curl -s -X POST http://localhost:8086/api/v1/executions/webhook/bk0/bk0-nldt-bridge/spike \
  -H 'Content-Type: application/json' -d '{"message": "hi"}'
```

Then read the execution (the audit record):

```bash
curl -s "http://localhost:8086/api/v1/executions?namespace=bk0" | jq '.results[0] | {id, state: .state.current}'
curl -s "http://localhost:8086/api/v1/executions/<executionId>" | jq '.outputs'
```

Expected: state `SUCCESS`; outputs contain `jobId` (uuid) and `exportUrl` (`http://localhost:8084/exports/<12-hex>.geojson`). Verify: `curl -s -o /dev/null -w "%{http_code}\n" <exportUrl>` → `200`. Also confirm the task-level audit trail: the execution detail's `taskRunList` has ≥ 3 entries.

- [ ] **Step 6: OpenWebUI → bridge reachability + human step**

```bash
docker exec open-webui python3 -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8086').status)"
```

Expected `200`. The OpenWebUI-side surfacing needs Marc's admin login — record in findings as the remaining human step, noting that chat display would need an OpenAI-compatible wrapper (BK-1 supersedes this via MCP tools instead).

- [ ] **Step 7: Fill findings, commit**

Complete the bridge section of `BK0-FINDINGS.md` (retitle "n8n → nLDT bridge" → "Kestra → nLDT bridge"): n8n decommissioned (decision 6), Kestra version, verified export URL, expression fixes applied, audit-record observation (taskRunList), human step remaining.

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/govchat/kestra-bk0-bridge-flow.yaml nldt/govchat/BK0-FINDINGS.md
git commit -m "BK-0: Kestra bridge flow (webhook -> OGC Processes -> export URL, audited)"
```

---

# Part 2 — BK-1: governed MVP (auth + MCP)

### Task 4: Shared bearer-auth dependency (`services/common/auth.py`)

TDD. One module, three modes, fail-closed.

**Files:**
- Create: `nldt/services/common/auth.py`
- Test: `nldt/tests/test_auth.py`

**Interfaces:**
- Produces: `async def require_bearer(request: Request) -> None` — FastAPI dependency; raises `HTTPException(401/503/500)`. Helpers `auth_mode() -> str`, `async def introspect_keycloak(token: str) -> bool`. Env: `NLDT_AUTH_MODE`, `NLDT_STATIC_TOKENS`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET` (optional overrides `KEYCLOAK_INTROSPECT_CLIENT_ID`/`_SECRET`).

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_auth.py`:

```python
from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.common.auth import require_bearer


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    monkeypatch.delenv("NLDT_AUTH_MODE", raising=False)
    monkeypatch.delenv("NLDT_STATIC_TOKENS", raising=False)


@pytest.fixture
def guarded_client():
    app = FastAPI(dependencies=[Depends(require_bearer)])

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_mode_off_allows_anonymous(guarded_client):
    resp = guarded_client.get("/ping")
    assert resp.status_code == 200


def test_static_mode_requires_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    assert guarded_client.get("/ping").status_code == 401


def test_static_mode_rejects_wrong_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_static_mode_accepts_known_token(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "tok-a,tok-b")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer tok-b"})
    assert resp.status_code == 200


def test_static_mode_fails_closed_without_tokens(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 401


def test_keycloak_mode_accepts_active_token(guarded_client, monkeypatch):
    import services.common.auth as auth

    async def fake_introspect(token: str) -> bool:
        return token == "kc-good"

    monkeypatch.setattr(auth, "introspect_keycloak", fake_introspect)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    ok = guarded_client.get("/ping", headers={"Authorization": "Bearer kc-good"})
    bad = guarded_client.get("/ping", headers={"Authorization": "Bearer kc-bad"})
    assert ok.status_code == 200
    assert bad.status_code == 401


def test_keycloak_introspection_failure_is_503(guarded_client, monkeypatch):
    import services.common.auth as auth

    async def exploding(token: str) -> bool:
        raise RuntimeError("keycloak down")

    monkeypatch.setattr(auth, "introspect_keycloak", exploding)
    monkeypatch.setenv("NLDT_AUTH_MODE", "keycloak")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503


def test_unknown_mode_fails_closed(guarded_client, monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "banana")
    resp = guarded_client.get("/ping", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 500
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_auth.py -q
```

Expected: collection error / FAIL — `ModuleNotFoundError: No module named 'services.common.auth'` (or equivalent import failure).

- [ ] **Step 3: Implement `services/common/auth.py`**

```python
"""Shared bearer-token gate for nLDT FastAPI services (beleidskompas BK-1).

NLDT_AUTH_MODE: off (default, dev/tests) | static (NLDT_STATIC_TOKENS,
comma-separated, fail closed) | keycloak (RFC 7662 introspection against
EU LDT Identity Management).
"""

from __future__ import annotations

import os

import httpx
from fastapi import HTTPException, Request

_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def auth_mode() -> str:
    return os.environ.get("NLDT_AUTH_MODE", "off").strip().lower()


def _static_tokens() -> list[str]:
    raw = os.environ.get("NLDT_STATIC_TOKENS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


async def introspect_keycloak(token: str) -> bool:
    url = os.environ.get("KEYCLOAK_URL", "").rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "LDT")
    client_id = os.environ.get("KEYCLOAK_INTROSPECT_CLIENT_ID", os.environ.get("KEYCLOAK_CLIENT_ID", ""))
    client_secret = os.environ.get(
        "KEYCLOAK_INTROSPECT_CLIENT_SECRET", os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
    )
    if not url or not client_id or not client_secret:
        raise RuntimeError("keycloak auth mode requires KEYCLOAK_URL, KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{url}/realms/{realm}/protocol/openid-connect/token/introspect",
            data={"token": token, "client_id": client_id, "client_secret": client_secret},
        )
    resp.raise_for_status()
    return bool(resp.json().get("active"))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers=_CHALLENGE)


async def require_bearer(request: Request) -> None:
    mode = auth_mode()
    if mode == "off":
        return
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("missing bearer token")
    if mode == "static":
        if token not in _static_tokens():
            raise _unauthorized("invalid token")
        return
    if mode == "keycloak":
        try:
            active = await introspect_keycloak(token)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"token introspection failed: {exc}") from exc
        if not active:
            raise _unauthorized("invalid token")
        return
    raise HTTPException(status_code=500, detail=f"unknown NLDT_AUTH_MODE: {mode}")
```

- [ ] **Step 4: Run to verify pass**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_auth.py -q
```

Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/common/auth.py nldt/tests/test_auth.py
git commit -m "BK-1: shared bearer-auth dependency (off|static|keycloak, fail closed)"
```

---

### Task 5: Wire the gate into cookbook, process adapter, catalog and A2A

**Files:**
- Modify: `nldt/services/cookbook/app.py` (FastAPI ctor, line ~10)
- Modify: `nldt/services/process_adapter/app.py` (line ~13)
- Modify: `nldt/services/catalog_adapter/app.py` (line ~14)
- Modify: `nldt/services/a2a/app.py` (line ~10)
- Test: `nldt/tests/test_auth.py` (append)

**Interfaces:**
- Consumes: `require_bearer` from Task 4.
- Produces: all four services reject unauthenticated requests whenever `NLDT_AUTH_MODE != off`. context3d `:8084` intentionally untouched.

- [ ] **Step 1: Append the failing wiring test**

Append to `nldt/tests/test_auth.py`:

```python
def test_services_guarded_in_static_mode(monkeypatch):
    from services.a2a.app import app as a2a_app
    from services.catalog_adapter.app import app as catalog_app
    from services.cookbook.app import app as cookbook_app
    from services.process_adapter.app import app as process_app

    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "svc-tok")
    cases = [
        (cookbook_app, "/recipes/spatial-overlay-analysis"),
        (process_app, "/processes"),
        (catalog_app, "/records"),
        (a2a_app, "/agent-card"),
    ]
    for app, path in cases:
        client = TestClient(app)
        assert client.get(path).status_code == 401, f"{app.title}: anonymous must be 401"
        ok = client.get(path, headers={"Authorization": "Bearer svc-tok"})
        assert ok.status_code == 200, f"{app.title}: valid token must pass ({ok.status_code})"


def test_services_open_by_default():
    from services.process_adapter.app import app as process_app

    client = TestClient(process_app)
    assert client.get("/processes").status_code == 200
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_auth.py -q
```

Expected: `test_services_guarded_in_static_mode` FAILs (services return 200 anonymously).

- [ ] **Step 3: Apply the same 3-line change to each of the four apps**

In `nldt/services/cookbook/app.py`:

```python
from fastapi import Depends, FastAPI, HTTPException

from services.common.auth import require_bearer
from services.common.schema import load_recipe

app = FastAPI(title="nLDT Cookbook", version="1.0.0", dependencies=[Depends(require_bearer)])
```

In `nldt/services/process_adapter/app.py`:

```python
from fastapi import Depends, FastAPI, HTTPException

from services.common.auth import require_bearer
from services.common.telemetry import init_telemetry, span

app = FastAPI(
    title="nLDT Process Adapter", version="1.0.0", dependencies=[Depends(require_bearer)]
)
```

In `nldt/services/catalog_adapter/app.py`:

```python
from fastapi import Depends, FastAPI, HTTPException, Query

from services.catalog_adapter.marketplace import fetch_marketplace_assets
from services.catalog_adapter.seed import find_records, seed_records
from services.common.auth import require_bearer
from services.common.schema import load_recipe
from services.marketplace_publish import publish_recipe

app = FastAPI(
    title="nLDT Catalog Adapter", version="1.0.0", dependencies=[Depends(require_bearer)]
)
```

In `nldt/services/a2a/app.py`:

```python
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.common.auth import require_bearer

app = FastAPI(title="nLDT A2A Agent", version="1.0.0", dependencies=[Depends(require_bearer)])
```

(Keep every existing import that is not shown; the blocks above show the changed/added lines in context.)

- [ ] **Step 4: Run the full suite — nothing may regress**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: all pass, including pre-existing tests (auth defaults to `off`). `8 + 2` new auth tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/cookbook/app.py nldt/services/process_adapter/app.py nldt/services/catalog_adapter/app.py nldt/services/a2a/app.py nldt/tests/test_auth.py
git commit -m "BK-1: bearer gate on cookbook/process/catalog/a2a (context3d stays public)"
```

---

### Task 6: MCP servers forward bearer tokens on outbound calls

The MCP servers call `:8082`/`:8083` over HTTP; once Task 5's gate is on, those calls must carry `Authorization`.

**Files:**
- Create: `nldt/services/mcp_servers/headers.py`
- Modify: `nldt/services/mcp_servers/catalog_server.py` (`_get`)
- Modify: `nldt/services/mcp_servers/process_server.py` (`_request`)
- Modify: `nldt/services/mcp_servers/client.py` (`ProcessClient.execute`)
- Test: `nldt/tests/test_mcp_auth_headers.py`

**Interfaces:**
- Produces: `def mcp_auth_headers() -> dict[str, str]` — `{"Authorization": "Bearer <NLDT_MCP_BEARER_TOKEN>"}` when set; else delegates to `services.adapters.keycloak_auth.auth_headers()` (empty dict when unconfigured).

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_mcp_auth_headers.py`:

```python
from __future__ import annotations

import asyncio

from services.mcp_servers.headers import mcp_auth_headers


def test_static_token_preferred(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    assert mcp_auth_headers() == {"Authorization": "Bearer mcp-tok"}


def test_no_config_returns_empty(monkeypatch):
    monkeypatch.delenv("NLDT_MCP_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("KEYCLOAK_URL", raising=False)
    monkeypatch.delenv("KEYCLOAK_HOST", raising=False)
    assert mcp_auth_headers() == {}


def test_process_server_request_sends_header(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    from services.mcp_servers import process_server

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(process_server.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(process_server._request("POST", "/jobs/x", {"a": 1}))
    assert out == {"ok": True}
    assert captured["headers"]["Authorization"] == "Bearer mcp-tok"


def test_catalog_server_get_sends_header(monkeypatch):
    monkeypatch.setenv("NLDT_MCP_BEARER_TOKEN", "mcp-tok")
    from services.mcp_servers import catalog_server

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"features": []}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, headers=None):
            captured["headers"] = headers
            return FakeResp()

    monkeypatch.setattr(catalog_server.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(catalog_server._get("/records"))
    assert out == {"features": []}
    assert captured["headers"]["Authorization"] == "Bearer mcp-tok"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_mcp_auth_headers.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'services.mcp_servers.headers'`.

- [ ] **Step 3: Implement `headers.py` and patch the callers**

Create `nldt/services/mcp_servers/headers.py`:

```python
"""Outbound auth headers for MCP servers calling gated nLDT services (BK-1)."""

from __future__ import annotations

import os


def mcp_auth_headers() -> dict[str, str]:
    static = os.environ.get("NLDT_MCP_BEARER_TOKEN", "").strip()
    if static:
        return {"Authorization": f"Bearer {static}"}
    from services.adapters.keycloak_auth import auth_headers

    return auth_headers()
```

In `catalog_server.py`, add the import next to the other `services` imports and pass headers in `_get`:

```python
from services.mcp_servers.headers import mcp_auth_headers

async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{CATALOG_URL}{path}", headers=mcp_auth_headers())
        resp.raise_for_status()
        return resp.json()
```

In `process_server.py`, same import, and headers on both verbs in `_request`:

```python
from services.mcp_servers.headers import mcp_auth_headers

async def _request(method: str, path: str, json_body: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=120.0) as client:
        url = f"{PROCESS_URL.rstrip('/')}{path}"
        if method == "GET":
            resp = await client.get(url, headers=mcp_auth_headers())
        else:
            resp = await client.post(url, json=json_body, headers=mcp_auth_headers())
        resp.raise_for_status()
        return resp.json()
```

In `client.py`, same import, and headers in `ProcessClient.execute`:

```python
from services.mcp_servers.headers import mcp_auth_headers

    def execute(
        self, process_id: str, inputs: dict[str, Any], backend: str = "local"
    ) -> dict[str, Any]:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url}/processes/{process_id}/execution",
                json={"inputs": inputs, "backend": backend},
                headers=mcp_auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()
```

- [ ] **Step 4: Run to verify pass**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_mcp_auth_headers.py tests/ -q
```

Expected: all pass (4 new + full suite).

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/mcp_servers/headers.py nldt/services/mcp_servers/catalog_server.py nldt/services/mcp_servers/process_server.py nldt/services/mcp_servers/client.py nldt/tests/test_mcp_auth_headers.py
git commit -m "BK-1: MCP servers send bearer tokens on outbound service calls"
```

---

### Task 7: Serve MCP servers over streamable-HTTP behind the same gate

stdio servers cannot be reached from Dockerised n8n/OpenWebUI. The installed `mcp` SDK exposes `MCPServer.streamable_http_app()` (ASGI, default path `/mcp`), which we mount in a FastAPI app guarded by `require_bearer`.

**Files:**
- Create: `nldt/services/mcp_servers/http_transport.py`
- Modify: `main()` in `catalog_server.py`, `process_server.py`, `data_server.py`, `poc_server.py`
- Test: `nldt/tests/test_mcp_http_transport.py`

**Interfaces:**
- Produces: `def build_mcp_http_app(server: MCPServer) -> FastAPI` and `def run_mcp_http(server: MCPServer, default_port: int) -> None`. Env: `NLDT_MCP_TRANSPORT` (`stdio` default | `streamable-http`), `NLDT_MCP_HTTP_PORT`, `NLDT_MCP_HTTP_HOST` (default `127.0.0.1`). Default ports: catalog 8090, process 8091, data 8092, poc 8093. MCP endpoint on each: `POST /mcp`.

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_mcp_http_transport.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.mcp_servers.catalog_server import mcp as catalog_mcp
from services.mcp_servers.http_transport import build_mcp_http_app

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}


@pytest.fixture
def http_client(monkeypatch):
    monkeypatch.setenv("NLDT_AUTH_MODE", "static")
    monkeypatch.setenv("NLDT_STATIC_TOKENS", "mcp-tok")
    with TestClient(build_mcp_http_app(catalog_mcp)) as client:
        yield client


def test_mcp_http_rejects_anonymous(http_client):
    resp = http_client.post("/mcp", json=INIT)
    assert resp.status_code == 401


def test_mcp_http_authenticated_reaches_mcp_layer(http_client):
    resp = http_client.post(
        "/mcp",
        json=INIT,
        headers={"Authorization": "Bearer mcp-tok", "Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code != 401  # 400/406/200 = reached MCP protocol layer
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_mcp_http_transport.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'services.mcp_servers.http_transport'`.

- [ ] **Step 3: Implement the transport helper**

Create `nldt/services/mcp_servers/http_transport.py`:

```python
"""Streamable-HTTP transport for nLDT MCP servers behind the shared bearer gate.

Dockerised clients (n8n/OpenWebUI in GovChat-NL) cannot spawn stdio servers;
NLDT_MCP_TRANSPORT=streamable-http serves the same MCPServer over HTTP.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer


def build_mcp_http_app(server: MCPServer) -> Any:
    from fastapi import Depends, FastAPI

    from services.common.auth import require_bearer

    app: Any = FastAPI(
        title=f"{server.name}-http",
        version="1.0.0",
        dependencies=[Depends(require_bearer)],
    )
    app.mount("/", server.streamable_http_app())
    return app


def run_mcp_http(server: MCPServer, default_port: int) -> None:
    import uvicorn

    uvicorn.run(
        build_mcp_http_app(server),
        host=os.environ.get("NLDT_MCP_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("NLDT_MCP_HTTP_PORT", str(default_port))),
    )
```

- [ ] **Step 4: Update `main()` in all four servers**

Replace `main()` in `catalog_server.py` (port 8090), `process_server.py` (8091), `data_server.py` (8092), `poc_server.py` (8093) with — adjust only the default port per file:

```python
def main() -> None:
    if os.environ.get("NLDT_MCP_TRANSPORT", "stdio") == "streamable-http":
        from services.mcp_servers.http_transport import run_mcp_http

        run_mcp_http(mcp, 8090)  # catalog; process=8091, data=8092, poc=8093
        return
    mcp.run()
```

- [ ] **Step 5: Run to verify pass, then a live smoke test**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_mcp_http_transport.py -q
```

Expected: `2 passed`. Live smoke (services from Task 1 still running):

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
NLDT_AUTH_MODE=static NLDT_STATIC_TOKENS=svc-tok \
NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8091 \
PYTHONPATH=. .venv/bin/python -m services.mcp_servers.process_server &
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8091/mcp \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8091/mcp \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer svc-tok' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
kill %1
```

Expected: `401` then a non-401 code (400/406).

- [ ] **Step 6: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/mcp_servers/http_transport.py nldt/services/mcp_servers/catalog_server.py nldt/services/mcp_servers/process_server.py nldt/services/mcp_servers/data_server.py nldt/services/mcp_servers/poc_server.py nldt/tests/test_mcp_http_transport.py
git commit -m "BK-1: MCP streamable-http transport behind bearer gate (:8090-8093)"
```

---

### Task 8: Beleidskompas policy-step recipes + catalog registration

Makes the two wired policy steps discoverable as nLDT assets: a dedicated omgevingsanalyse recipe, and beleidskompas tags on the existing S4 Q&A recipe.

**Files:**
- Create: `nldt/recipes/beleidskompas-omgevingsanalyse.json`
- Modify: `nldt/recipes/breda-scan-qa.json` (tags only)
- Modify: `nldt/services/catalog_adapter/seed.py` (recipes list)
- Test: `nldt/tests/test_beleidskompas.py`

**Interfaces:**
- Produces: recipe id `beleidskompas-omgevingsanalyse` (served by `:8081`, record `recipe-beleidskompas-omgevingsanalyse`); recipe `breda-scan-qa` gains tags `beleidskompas`, `policy-step:substantiation`. Catalog search `?q=beleidskompas` returns both records (search matches title or properties/tags — verified in `seed.find_records`).

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_beleidskompas.py`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from services.catalog_adapter.app import app as catalog_app
from services.cookbook.app import app as cookbook_app


def test_cookbook_serves_beleidskompas_recipe():
    client = TestClient(cookbook_app)
    resp = client.get("/recipes/beleidskompas-omgevingsanalyse")
    assert resp.status_code == 200
    data = resp.json()
    assert "beleidskompas" in data["tags"]
    assert data["steps"][0]["processId"] == "fetch-features"
    assert data["riskLevel"] == "low"


def test_catalog_search_finds_beleidskompas_assets():
    client = TestClient(catalog_app)
    resp = client.get("/records", params={"q": "beleidskompas"})
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()["features"]]
    assert "recipe-beleidskompas-omgevingsanalyse" in ids
    assert "recipe-breda-scan-qa" in ids


def test_scan_qa_recipe_tagged_for_beleidskompas():
    client = TestClient(catalog_app)
    rec = client.get("/records/recipe-breda-scan-qa").json()
    tags = rec["properties"]["tags"]
    assert "beleidskompas" in tags
    assert "policy-step:substantiation" in tags
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_beleidskompas.py -q
```

Expected: 3 failures (404 for the new recipe; search misses it; tag missing).

- [ ] **Step 3: Create the recipe**

Create `nldt/recipes/beleidskompas-omgevingsanalyse.json`:

```json
{
  "id": "beleidskompas-omgevingsanalyse",
  "title": "Beleidskompas omgevingsanalyse (overlay)",
  "description": "GENAI-safe omgevingsanalyse for the beleidskompas policy step: fetch two layers, intersect, compute area statistics. Wraps the generic overlay processes; area-agnostic (AOI + layer URIs as inputs).",
  "version": "1.0.0",
  "tags": ["beleidskompas", "policy-step:omgevingsanalyse", "spatial", "overlay"],
  "requiredData": [
    { "id": "aoi", "role": "aoi", "format": "geojson" },
    { "id": "layerA", "role": "reference_layer", "format": "url" },
    { "id": "layerB", "role": "context_layer", "format": "url" }
  ],
  "requiredProcesses": ["fetch-features", "spatial-intersection", "compute-area-statistics"],
  "inputs": {
    "aoi": { "type": "geojson", "description": "Area of interest polygon (e.g. province or municipality)", "required": true },
    "layerAUri": { "type": "uri", "description": "URI to layer A GeoJSON", "required": true },
    "layerBUri": { "type": "uri", "description": "URI to layer B GeoJSON", "required": true }
  },
  "outputs": {
    "intersection": { "type": "geojson", "description": "Intersection FeatureCollection" },
    "statistics": { "type": "json", "description": "Area statistics in m²" }
  },
  "steps": [
    {
      "id": "fetch-layer-a",
      "processId": "fetch-features",
      "title": "Fetch layer A",
      "inputs": { "source": "${recipe.inputs.layerAUri}", "aoi": "${recipe.inputs.aoi}" },
      "outputs": { "features": "features" },
      "backend": "local"
    },
    {
      "id": "fetch-layer-b",
      "processId": "fetch-features",
      "title": "Fetch layer B",
      "inputs": { "source": "${recipe.inputs.layerBUri}", "aoi": "${recipe.inputs.aoi}" },
      "outputs": { "features": "features" },
      "backend": "local"
    },
    {
      "id": "intersect",
      "processId": "spatial-intersection",
      "title": "Spatial intersection",
      "inputs": {
        "layerA": "${steps.fetch-layer-a.outputs.features}",
        "layerB": "${steps.fetch-layer-b.outputs.features}"
      },
      "outputs": { "result": "intersection" },
      "backend": "local"
    },
    {
      "id": "stats",
      "processId": "compute-area-statistics",
      "title": "Compute area statistics",
      "inputs": { "features": "${steps.intersect.outputs.result}" },
      "outputs": { "statistics": "statistics" },
      "backend": "local"
    }
  ],
  "visualizationHint": { "preferredFormat": "geojson", "layerTitle": "Omgevingsanalyse overlay" },
  "riskLevel": "low",
  "cookbookUri": "http://localhost:8081/recipes/beleidskompas-omgevingsanalyse"
}
```

- [ ] **Step 4: Tag the Q&A recipe and register both in the catalog seed**

In `nldt/recipes/breda-scan-qa.json`, extend the tags line:

```json
  "tags": ["poc-breda", "qa", "s4", "scan", "legal", "beleidskompas", "policy-step:substantiation"],
```

In `nldt/services/catalog_adapter/seed.py`, in the `recipes = [...]` list, change the `breda-scan-qa` entry and append the new one (after the `eindhoven-bp2op` tuple, before the closing `]`):

```python
        (
            "breda-scan-qa",
            "Breda five-value scan Q&A",
            ["poc-breda", "qa", "s4", "scan", "beleidskompas", "policy-step:substantiation"],
        ),
```

```python
        (
            "beleidskompas-omgevingsanalyse",
            "Beleidskompas omgevingsanalyse (overlay)",
            ["beleidskompas", "policy-step:omgevingsanalyse", "spatial", "overlay"],
        ),
```

- [ ] **Step 5: Run to verify pass, plus an end-to-end recipe run**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_beleidskompas.py -q
PYTHONPATH=. .venv/bin/python -m services.cli run-recipe beleidskompas-omgevingsanalyse \
  --aoi-file examples/rijnsweerd/aoi.geojson \
  --input layerAUri=file://$(pwd)/examples/rijnsweerd/layer-a.geojson \
  --input layerBUri=file://$(pwd)/examples/rijnsweerd/layer-b.geojson
```

Expected: `3 passed`; recipe run finishes with statistics (totalAreaM2 > 0).

- [ ] **Step 6: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/recipes/beleidskompas-omgevingsanalyse.json nldt/recipes/breda-scan-qa.json nldt/services/catalog_adapter/seed.py nldt/tests/test_beleidskompas.py
git commit -m "BK-1: beleidskompas policy-step recipes + catalog registration"
```

---

### Task 9: Runbook, start-script support, plan-status update

Documentation task: everything an engineer (or the beleidskompas team, later) needs to run the governed MVP, and the spec doc brought up to date.

**Files:**
- Create: `nldt/govchat/README.md`
- Modify: `nldt/scripts/start-services.sh`
- Modify: `nldt/14-beleidskompas-integration.md` (status lines)

- [ ] **Step 1: Add the MCP-http block to `start-services.sh`**

Replace the `wait`-less tail block (from `python -m services.a2a.app &` through `trap cleanup EXIT INT TERM`) so it reads:

```bash
python -m services.a2a.app &
PID5=$!

if [[ "${NLDT_START_MCP_HTTP:-0}" == "1" ]]; then
  echo "Starting MCP servers over streamable-http (auth: NLDT_AUTH_MODE/NLDT_STATIC_TOKENS)"
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8090 python -m services.mcp_servers.catalog_server &
  PID6=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8091 python -m services.mcp_servers.process_server &
  PID7=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8092 python -m services.mcp_servers.data_server &
  PID8=$!
  NLDT_MCP_TRANSPORT=streamable-http NLDT_MCP_HTTP_PORT=8093 python -m services.mcp_servers.poc_server &
  PID9=$!
fi

cleanup() {
  kill "$PID1" "$PID2" "$PID3" "$PID4" "$PID5" ${PID6:-} ${PID7:-} ${PID8:-} ${PID9:-} 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1
echo "Ready: cookbook :8081, processes :8082, catalog :8083, context3d :8084, a2a :8085"
[[ "${NLDT_START_MCP_HTTP:-0}" == "1" ]] && echo "MCP-http: catalog :8090, process :8091, data :8092, poc :8093 (POST /mcp)"
wait
```

- [ ] **Step 2: Write `nldt/govchat/README.md`**

```markdown
# GovChat-NL ↔ nLDT — beleidskompas integration (BK-0/BK-1)

How to run the governed MVP: beleidskompas (or any GovChat-NL app) consumes
nLDT capabilities via authenticated MCP servers. Plan:
[`../14-beleidskompas-integration.md`](../14-beleidskompas-integration.md).

## 1. Start nLDT with auth + MCP-over-HTTP

```bash
cd nldt
export NLDT_AUTH_MODE=static
export NLDT_STATIC_TOKENS="beleidskompas-svc-tok"   # any string; one per consumer
export NLDT_MCP_BEARER_TOKEN="beleidskompas-svc-tok" # used by MCP servers upstream
NLDT_START_MCP_HTTP=1 ./scripts/start-services.sh
```

Ports: services :8081–:8085 (context3d :8084 deliberately public — export
URLs), MCP streamable-HTTP: catalog :8090, process :8091, data :8092,
poc :8093 — endpoint `POST /mcp` on each, `Authorization: Bearer <token>`.

Keycloak instead of static tokens: `NLDT_AUTH_MODE=keycloak` with
`KEYCLOAK_URL/REALM/CLIENT_ID/CLIENT_SECRET` (EU LDT Identity Management);
MCP servers then fetch service tokens automatically.

## 2. Connect a GovChat-NL app

From the bridge/workflow engine — engine-agnostic (Kestra in the testbed;
any MCP-capable or plain-HTTP client works): connect to
`http://host.docker.internal:8091/mcp` with header
`Authorization: Bearer beleidskompas-svc-tok`. Tools: `describe_process`,
`execute_process`, `get_job_status`. Catalog server (:8090) adds
`search_records`, `list_processes`; poc server (:8093) adds `ask_scan`,
`propose_scenarios`, `run_scenario_sweep`, `run_opportunity_map`, ….
(Kestra: `io.kestra.plugin.core.http.Request` against the MCP endpoint, or an
MCP plugin if the installed version ships one — MCP client support across
engines is still maturing; the HTTP/OGC seam always works.)

## 3. The two wired policy steps

| Beleidskompas step | MCP call | nLDT asset |
|---|---|---|
| Omgevingsanalyse | `execute_process` / recipe `beleidskompas-omgevingsanalyse` | `recipes/beleidskompas-omgevingsanalyse.json` |
| Substantiation Q&A (S4, cite-or-abstain) | `ask_scan` (poc server) | recipe `breda-scan-qa` → process `breda-scan-query` |

`ask_scan` returns the full S4 bundle (answer, citations, verdict/gates);
beleidskompas must quote only from it (seam S9, integration plan §6).

## 4. Verify

```bash
# unauthenticated MCP call must fail
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8091/mcp \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
# → 401
```

BK-0 spike artifacts: [`BK0-FINDINGS.md`](BK0-FINDINGS.md),
[`kestra-bk0-bridge-flow.yaml`](kestra-bk0-bridge-flow.yaml) (throwaway
plain-HTTP bridge, superseded by the MCP path; engine pluggable — decision 6).
```

- [ ] **Step 3: Update the integration plan status**

In `nldt/14-beleidskompas-integration.md`:

- Status row: `| Status | Decided 2026-09-14 (§10) · BK-0 not yet started |` → `| Status | Decided 2026-09-14 (§10) · BK-0 + BK-1 implemented (runbook: govchat/README.md) |`
- Under **### BK-0** and **### BK-1** headings, append one line each: `**Status:** done — see [govchat/BK0-FINDINGS.md](govchat/BK0-FINDINGS.md).` and `**Status:** done — see [govchat/README.md](govchat/README.md) (context3d :8084 left public, see §7).`

- [ ] **Step 4: Full suite + smoke, commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: all green.

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/govchat/README.md nldt/scripts/start-services.sh nldt/14-beleidskompas-integration.md
git commit -m "BK-1: govchat runbook, start-script MCP-http flag, plan status"
```

---

## Definition of done (maps to spec §8)

- BK-0: a webhook-triggered Kestra execution (durable, per-task audit record) returns an nLDT jobId + `:8084` export URL (HTTP 200); findings logged; OpenWebUI surfacing recorded as human step.
- BK-1: bearer gate on :8081/:8082/:8083/:8085 + MCP :8090–8093 (401 anonymous, fail-closed); MCP outbound calls authenticated; `beleidskompas-omgevingsanalyse` + tagged `breda-scan-qa` discoverable via `?q=beleidskompas`; runbook in `nldt/govchat/README.md`; full test suite green with auth off by default.
