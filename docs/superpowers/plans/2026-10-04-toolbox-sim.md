# Toolbox-sim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `toolbox-sim/` — a runnable local simulation of the six PoC-relevant EU LDT Toolbox solutions (IM, Data Platform, Play & Visualise, UCS, Marketplace, EU Building Database feed) speaking exactly the HTTP contracts the existing nldt adapters already call, replaying canonical PoC run artifacts.

**Architecture:** One FastAPI/uvicorn process, one port per solution (9191–9196). Fixtures are derived deterministically from the canonical Utrecht/Eindhoven runs (fase-1 NGSI-LD entity model, `urn:ldt:` URIs) by `build_fixtures.py` and committed. Auth: sim-minted HS256 JWTs plus the `a2a-simulation` static mesh token; every response carries an `X-Sim-Provenance` header.

**Tech Stack:** Python ≥3.11, FastAPI, uvicorn, httpx (mirrors `nldt/requirements.txt`), psycopg (EUBD path only), pytest via `../nldt/.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md`

## Global Constraints

- Ports fixed: 9191 IM · 9192 DP-broker (+Trino) · 9193 P&V · 9194 UCS · 9195 Marketplace · 9196 EUBD. Bind `127.0.0.1` only.
- Static mesh token: `sim-toolbox-token`. JWT dev secret: `toolbox-sim-dev-secret` (override via `TOOLBOX_SIM_JWT_SECRET`).
- No invented values: every fixture value traces to a canonical run artifact (or, for EUBD, real PostGIS rows); regeneration is byte-identical (`json.dumps(..., sort_keys=True, separators=(",", ":"))` + trailing `\n`, no wall-clock stamps in fixtures).
- Existing suites stay untouched: no code edits under `nldt/`, `poc/`, `poc-bp2op/` (docs link in Task 16 only).
- All contract tests run in-process via `fastapi.testclient`; only Tasks 13–15 boot real ports.
- Test command (from `toolbox-sim/`): `../nldt/.venv/bin/python -m pytest tests -q`
- Every task ends with a commit `feat(toolbox-sim): …` / `test(toolbox-sim): …` / `docs(toolbox-sim): …`.
- Work happens on branch `toolbox-sim` (isolated worktree per the spec's risk table), merged to `main` at the end.

---

### Task 1: Skeleton + catalogue manifest

**Files:**
- Create: `toolbox-sim/requirements.txt`, `toolbox-sim/README.md`, `toolbox-sim/catalogue.json`, `toolbox-sim/app/__init__.py`, `toolbox-sim/tests/__init__.py`, `toolbox-sim/tests/conftest.py`
- Test: `toolbox-sim/tests/test_catalogue.py`

**Interfaces:**
- Produces: `catalogue.json` — `{"catalogue": <url>, "generated": "2026-10-04", "solutions": [...]}`; each solution `{"name", "kind": "tool"|"algorithm-model", "status": "simulated"|"consumed-as-data"|"skipped", "evidence"?, "reason"?}`. Later tasks and the README treat this file as the source of truth for what the sim covers.

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_catalogue.py
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAT = json.loads((REPO / "toolbox-sim" / "catalogue.json").read_text())

SIMULATED = {
    "EU LDT Identity Management",
    "EU LDT Data Platform",
    "EU LDT Play & Visualise",
    "EU LDT Use Cases & Scenarios",
    "EU LDT Marketplace",
}


def test_twenty_solutions():
    assert len(CAT["solutions"]) == 20
    names = [s["name"] for s in CAT["solutions"]]
    assert len(set(names)) == 20


def test_statuses_valid_and_grounded():
    for s in CAT["solutions"]:
        assert s["status"] in {"simulated", "consumed-as-data", "skipped"}
        if s["status"] == "skipped":
            assert s.get("reason"), f"{s['name']} skipped without reason"
        else:
            assert s.get("evidence"), f"{s['name']} without evidence"
        assert s["kind"] in {"tool", "algorithm-model"}


def test_simulated_set_matches_spec():
    got = {s["name"] for s in CAT["solutions"] if s["status"] == "simulated"}
    assert got == SIMULATED
    eubd = [s for s in CAT["solutions"] if s["name"] == "EU Building Database"]
    assert eubd[0]["status"] == "consumed-as-data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_catalogue.py -q`
Expected: FAIL — `catalogue.json` does not exist (`FileNotFoundError`).

- [ ] **Step 3: Create skeleton files and catalogue**

`toolbox-sim/requirements.txt`:

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
httpx>=0.27.0
psycopg[binary]>=3.2
```

`toolbox-sim/catalogue.json` (statuses/reasons verbatim from the spec §Catalogusmanifest):

```json
{
  "catalogue": "https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue",
  "generated": "2026-10-04",
  "solutions": [
    {"name": "EU LDT Identity Management", "kind": "tool", "status": "simulated", "evidence": "nldt/services/adapters/keycloak_auth.py; realm LDT (real IM also deployed at im.ldt.local)"},
    {"name": "EU LDT Data Platform", "kind": "tool", "status": "simulated", "evidence": "nldt/services/adapters/data_platform.py (broker + UCS-proxy + Trino)"},
    {"name": "EU LDT Play & Visualise", "kind": "tool", "status": "simulated", "evidence": "nldt/services/adapters/play_visualise.py (real P&V also deployed at pv.ldt.local)"},
    {"name": "EU LDT Use Cases & Scenarios", "kind": "tool", "status": "simulated", "evidence": "nldt/services/process_adapter/router.py::UCSAdapter (trigger-process)"},
    {"name": "EU LDT Marketplace", "kind": "tool", "status": "simulated", "evidence": "nldt/services/marketplace_publish.py (assets + publish)"},
    {"name": "EU LDT Integrated Environment", "kind": "tool", "status": "skipped", "reason": "nLDT is zijn eigen voordeur (OGC Records/Processes/Recipes); IE-portaal/asset-registry heeft geen PoC-functie"},
    {"name": "EU LDT AI Notebook", "kind": "tool", "status": "skipped", "reason": "lokale open modellen (Ollama) bedienen al de propose-benen S1/S2/S7/S8; AIN-stack is zwaar en Linux-only"},
    {"name": "EU LDT City Innovation Planner", "kind": "tool", "status": "skipped", "reason": "co-creatietool zonder PoC-rol"},
    {"name": "EU LDT Data Modeller", "kind": "tool", "status": "skipped", "reason": "eigen @context + shapes (fase-1 NGSI-LD) dekken de behoefte"},
    {"name": "EU LDT Data Space Ready", "kind": "tool", "status": "skipped", "reason": "buiten evidence-set deze snede; nldt/13 (EDC/ODRL) dekt het pad"},
    {"name": "EU LDT Federated Learning", "kind": "tool", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "EU LDT Participate", "kind": "tool", "status": "skipped", "reason": "V4/eParticipatie is toekomstspoor, geen adapter"},
    {"name": "Urban Mobility", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "Pollution Propagation", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "Neighbourhood Energy Demand Forecasting", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol vandaag; eerste uitbreidingskandidaat zodra de Utrecht-congestietrack (art. 5.10/5.11) start"},
    {"name": "Building Environmental Footprint", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "Renovation Strategies", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "Urban Planning Vulnerability Mitigation", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "Police Routing Tool", "kind": "algorithm-model", "status": "skipped", "reason": "geen PoC-rol"},
    {"name": "EU Building Database", "kind": "algorithm-model", "status": "consumed-as-data", "evidence": "PostGIS exposure-slice (SETUP.md); sim ontsluit hem als entiteitsfeed op 9196"}
  ]
}
```

`toolbox-sim/app/__init__.py` and `toolbox-sim/tests/__init__.py`: empty files.

`toolbox-sim/tests/conftest.py`:

```python
import sys
from pathlib import Path

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))
```

`toolbox-sim/README.md`:

```markdown
# Toolbox-sim — runnable simulatie van de PoC-relevante EU LDT Toolbox-oplossingen

Eén lokaal FastAPI-proces dat instaat voor de zes oplossingen met hard bewijs
van PoC-gebruik (zie `catalogue.json` voor alle 20 catalogusoplossingen met
status en reden) en exact de HTTP-contracten spreekt die de nldt-adapters
al aanroepen. Ontwerp: `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md`.

| Poort | Oplossing |
|---|---|
| 9191 | Identity Management (OIDC, realm LDT) |
| 9192 | Data Platform — NGSI-LD-broker + UCS-proxy + Trino-stub |
| 9193 | Play & Visualise |
| 9194 | Use Cases & Scenarios |
| 9195 | Marketplace Agent |
| 9196 | EU Building Database-feed (alleen met `--eubd`) |

```bash
# fixtures (deterministisch, gecommit) hergenereren:
../nldt/.venv/bin/python build_fixtures.py
# sim starten (IM+DP+P&V+UCS+Marketplace):
./run_sim.sh
# inclusief EUBD-feed (vereist lokale PostGIS `exposure`):
TOOLBOX_SIM_EUBD_DSN="postgresql://marc@localhost:5432/exposure" \
  ../nldt/.venv/bin/python build_fixtures.py --eubd "$TOOLBOX_SIM_EUBD_DSN"
./run_sim.sh --eubd
# tests:
../nldt/.venv/bin/python -m pytest tests -q
```

Auth: sim-IM mint HS256-JWTs; het statische mesh-token `sim-toolbox-token`
(a2a-simulation) wordt ook geaccepteerd. Elke response draagt
`X-Sim-Provenance`. Geen verzonnen waarden: alles herleidbaar naar canonieke
run-artefacten of echte PostGIS-rijen.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_catalogue.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim
git commit -m "feat(toolbox-sim): skelet + catalogusmanifest (20 oplossingen, evidence-set)"
```

---

### Task 2: JWT utility (mint + verify, static mesh token)

**Files:**
- Create: `toolbox-sim/app/jwtutil.py`
- Test: `toolbox-sim/tests/test_jwtutil.py`

**Interfaces:**
- Produces:
  - `SIGNING_SECRET: str` (env `TOOLBOX_SIM_JWT_SECRET`, default `"toolbox-sim-dev-secret"`)
  - `STATIC_TOKEN = "sim-toolbox-token"`
  - `mint_token(client_id: str, groups: list[str], ttl_s: int = 300) -> str`
  - `verify_token(token: str) -> dict` — payload with `iss="http://127.0.0.1:9191/realms/LDT"`, `sub`, `iat`, `exp`, `groups`, `"toolbox-sim": True`; raises `InvalidToken` on bad signature/format/expiry.
  - `class InvalidToken(Exception)`

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_jwtutil.py
import time

import pytest

from app.jwtutil import STATIC_TOKEN, InvalidToken, mint_token, verify_token


def test_mint_and_verify_roundtrip():
    tok = mint_token("nldt-agent", ["/context-data/default/User"])
    payload = verify_token(tok)
    assert payload["sub"] == "nldt-agent"
    assert payload["groups"] == ["/context-data/default/User"]
    assert payload["iss"] == "http://127.0.0.1:9191/realms/LDT"
    assert payload["toolbox-sim"] is True


def test_expired_token_rejected():
    tok = mint_token("nldt-agent", [], ttl_s=-10)
    with pytest.raises(InvalidToken):
        verify_token(tok)


def test_tampered_token_rejected():
    tok = mint_token("nldt-agent", [])
    header, payload, sig = tok.split(".")
    with pytest.raises(InvalidToken):
        verify_token(f"{header}.{payload}.{sig[:-1]}{'A' if sig[-1] != 'A' else 'B'}")


def test_garbage_token_rejected():
    with pytest.raises(InvalidToken):
        verify_token("not-a-token")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_jwtutil.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jwtutil'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/jwtutil.py
"""HS256-JWTs voor de sim-IM. Dev-geheim, uitsluitend localhost-verkeer."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

SIGNING_SECRET = os.environ.get("TOOLBOX_SIM_JWT_SECRET", "toolbox-sim-dev-secret")
STATIC_TOKEN = "sim-toolbox-token"
ISSUER = "http://127.0.0.1:9191/realms/LDT"


class InvalidToken(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def mint_token(client_id: str, groups: list[str], ttl_s: int = 300) -> str:
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": client_id,
        "iat": now,
        "exp": now + ttl_s,
        "groups": list(groups),
        "toolbox-sim": True,
    }
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(SIGNING_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64(sig)}"


def verify_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidToken("malformed token")
    header, body, sig = parts
    expected = hmac.new(SIGNING_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64(expected), sig):
        raise InvalidToken("bad signature")
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidToken("bad payload") from exc
    if payload.get("exp", 0) < time.time():
        raise InvalidToken("expired")
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_jwtutil.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/jwtutil.py toolbox-sim/tests/test_jwtutil.py
git commit -m "feat(toolbox-sim): HS256 jwt-util + statisch mesh-token"
```

---

### Task 3: Guards — bearer dependency + provenance header

**Files:**
- Create: `toolbox-sim/app/guards.py`
- Test: `toolbox-sim/tests/test_guards.py`

**Interfaces:**
- Consumes: `app.jwtutil.verify_token`, `app.jwtutil.STATIC_TOKEN`, `app.jwtutil.InvalidToken`.
- Produces:
  - `require_bearer(authorization: str = Header(default="")) -> dict` — FastAPI dependency; returns JWT payload; for `STATIC_TOKEN` returns `{"sub": "static-mesh", "groups": ["/context-data/default/User", "/data-query/timescaledb/User"], "toolbox-sim": True}`; raises `HTTPException(401)` with `WWW-Authenticate: Bearer` otherwise.
  - `add_provenance(app: FastAPI, solution: str) -> None` — middleware setting `X-Sim-Provenance: toolbox-sim/<solution>` on every response (handlers may override with a more specific value).
  - `provenance_detail(value: str) -> dict` — `{"X-Sim-Provenance": value}` helper for handlers.

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_guards.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.guards import add_provenance, require_bearer
from app.jwtutil import STATIC_TOKEN, mint_token

app = FastAPI()
add_provenance(app, "data-platform")


@app.get("/protected")
def protected(payload: dict = __import__("fastapi").Depends(require_bearer)):
    return {"sub": payload["sub"]}


client = TestClient(app)


def test_valid_jwt_accepted():
    r = client.get("/protected", headers={"Authorization": f"Bearer {mint_token('nldt-agent', [])}"})
    assert r.status_code == 200
    assert r.json()["sub"] == "nldt-agent"


def test_static_mesh_token_accepted():
    r = client.get("/protected", headers={"Authorization": f"Bearer {STATIC_TOKEN}"})
    assert r.status_code == 200
    assert r.json()["sub"] == "static-mesh"


def test_missing_or_bad_token_rejected_401():
    assert client.get("/protected").status_code == 401
    r = client.get("/protected", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_provenance_header_on_every_response():
    r = client.get("/protected")  # 401 — header moet er toch staan
    assert r.headers["X-Sim-Provenance"] == "toolbox-sim/data-platform"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_guards.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.guards'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/guards.py
"""Auth-dependency + herkomst-header voor alle sim-diensten."""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.jwtutil import STATIC_TOKEN, InvalidToken, verify_token

STATIC_PRINCIPAL = {
    "sub": "static-mesh",
    "groups": ["/context-data/default/User", "/data-query/timescaledb/User"],
    "toolbox-sim": True,
}


def require_bearer(authorization: str = Header(default="")) -> dict:
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :]
        if token == STATIC_TOKEN:
            return dict(STATIC_PRINCIPAL)
        try:
            return verify_token(token)
        except InvalidToken as exc:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_token", "error_description": str(exc)},
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    raise HTTPException(
        status_code=401,
        detail={"error": "invalid_token", "error_description": "missing bearer token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def add_provenance(app: FastAPI, solution: str) -> None:
    @app.middleware("http")
    async def _provenance(request: Request, call_next):
        response: JSONResponse = await call_next(request)
        response.headers.setdefault("X-Sim-Provenance", f"toolbox-sim/{solution}")
        return response


def provenance_detail(value: str) -> dict:
    return {"X-Sim-Provenance": value}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_guards.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/guards.py toolbox-sim/tests/test_guards.py
git commit -m "feat(toolbox-sim): bearer-guard + X-Sim-Provenance-middleware"
```

---

### Task 4: Identity Management app (OIDC token endpoint)

**Files:**
- Create: `toolbox-sim/app/identity.py`, `toolbox-sim/fixtures/clients.json`
- Test: `toolbox-sim/tests/test_identity.py`

**Interfaces:**
- Consumes: `app.jwtutil.mint_token`, `app.guards.add_provenance`.
- Produces: `create_app() -> FastAPI` with:
  - `GET /health` → `{"status": "UP"}` (no auth)
  - `POST /realms/{realm}/protocol/openid-connect/token` (form: `grant_type`, `client_id`, `client_secret`) → `{"access_token", "expires_in": 300, "token_type": "Bearer"}`; realm ≠ `LDT` → 404; unknown client/secret or wrong grant_type → 401 `{"error": "invalid_client"}`.
- `fixtures/clients.json`: `{"clients": {"nldt-agent": {"secret": "sim-dev-secret", "groups": ["/context-data/default/User", "/data-query/timescaledb/User"]}}}`

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_identity.py
import base64
import json

from fastapi.testclient import TestClient

from app.identity import create_app

client = TestClient(create_app())


def _payload(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "==="))


def test_health():
    assert client.get("/health").json() == {"status": "UP"}


def test_client_credentials_grant():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 300
    payload = _payload(body["access_token"])
    assert payload["sub"] == "nldt-agent"
    assert "/context-data/default/User" in payload["groups"]  # data_platform.list_scopes() leest deze
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/")


def test_unknown_secret_401():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "wrong"},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_client"


def test_unknown_realm_404():
    r = client.post(
        "/realms/master/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 404


def test_wrong_grant_type_401():
    r = client.post(
        "/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    assert r.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_identity.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.identity'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/identity.py
"""EU LDT Identity Management-sim: OIDC client_credentials, realm LDT."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException

from app.guards import add_provenance
from app.jwtutil import mint_token

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TTL_S = 300


def _clients() -> dict:
    return json.loads((FIXTURES / "clients.json").read_text())["clients"]


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim identity", docs_url=None, openapi_url=None)
    add_provenance(app, "identity")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/realms/{realm}/protocol/openid-connect/token")
    def token(
        realm: str,
        grant_type: str = Form(default=""),
        client_id: str = Form(default=""),
        client_secret: str = Form(default=""),
    ) -> dict:
        if realm != "LDT":
            raise HTTPException(status_code=404, detail={"error": "realm_not_found"})
        known = _clients().get(client_id)
        if grant_type != "client_credentials" or not known or known["secret"] != client_secret:
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_client", "error_description": "Client not found or invalid secret"},
            )
        return {
            "access_token": mint_token(client_id, known["groups"], ttl_s=TTL_S),
            "expires_in": TTL_S,
            "token_type": "Bearer",
        }

    return app
```

`toolbox-sim/fixtures/clients.json`:

```json
{
  "clients": {
    "nldt-agent": {
      "secret": "sim-dev-secret",
      "groups": ["/context-data/default/User", "/data-query/timescaledb/User"]
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_identity.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/identity.py toolbox-sim/fixtures/clients.json toolbox-sim/tests/test_identity.py
git commit -m "feat(toolbox-sim): IM-sim — OIDC tokenendpoint (realm LDT, fail-closed)"
```

---

### Task 5: Fixture builder — Utrecht batches (NGSI-LD, fase-1 model)

**Files:**
- Create: `toolbox-sim/build_fixtures.py`
- Test: `toolbox-sim/tests/test_fixtures_utrecht.py`
- Generated (committed): `toolbox-sim/fixtures/ngsi-ld/utrecht-wind.jsonld`, `…zon.jsonld`, `…bos.jsonld`

**Interfaces:**
- Produces (used by Task 7 broker, Task 12 server):
  - `CANONICAL_RUNS: dict[str, Path]` — `{"utrecht-wind": <repo>/poc/runs/20260830T113234Z-wind, "utrecht-zon": …20260830T142439Z-zon, "utrecht-bos": …20260830T142446Z-bos, "eindhoven-bp2op": <repo>/poc-bp2op/runs/20260830-124515-eindhoven}`
  - `build_utrecht_batch(run_dir: Path) -> list[dict]` — entities sorted by id, NGSI-LD normalized (`Property`/`GeoProperty`/`Relationship`), types `ldt:OpportunityZone`, `ldt:FormalRule`, `ldt:NormCard`, `ldt:PipelineRun`; URIs `urn:ldt:utrecht:{zone|rule|normcard|run}:{artifact-id}`.
  - `zone_role(zone_id: str) -> str` — `final|inclusion|exclusion|marker|other`.
  - `write_batch(path: Path, entities: list[dict]) -> None` — deterministic bytes.
  - CLI `python build_fixtures.py` writes all batches + `fixtures/manifest.json` (per batch: counts per type + sha256 of each source artifact read) + `fixtures/ucs-processes.json` (Task 10 consumes) + `fixtures/trino/tables.json` (Task 8 consumes). Run summary fields used: `runId`, `verdict`, `generatedAt`, `headline` (Utrecht) / `counts` (Eindhoven).

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_fixtures_utrecht.py
import json
from pathlib import Path

import pytest

from build_fixtures import CANONICAL_RUNS, build_utrecht_batch, zone_role

REPO = Path(__file__).resolve().parents[2]
WIND = CANONICAL_RUNS["utrecht-wind"]


def _load(name: str):
    return json.loads((WIND / name).read_text())


@pytest.mark.parametrize("key", ["utrecht-wind", "utrecht-zon", "utrecht-bos"])
def test_batch_counts_match_artifacts(key):
    run_dir = CANONICAL_RUNS[key]
    batch = build_utrecht_batch(run_dir)
    by_type = {}
    for e in batch:
        by_type.setdefault(e["type"], []).append(e)
    assert len(by_type["ldt:OpportunityZone"]) == len(json.loads((run_dir / "zones.json").read_text()))
    assert len(by_type["ldt:FormalRule"]) == len(json.loads((run_dir / "formalrules.json").read_text()))
    assert len(by_type["ldt:NormCard"]) == len(json.loads((run_dir / "normcards.json").read_text()))
    assert len(by_type["ldt:PipelineRun"]) == 1


def test_zone_entity_shape_and_grounding():
    batch = build_utrecht_batch(WIND)
    zones = [e for e in batch if e["type"] == "ldt:OpportunityZone"]
    rules = {e["id"] for e in batch if e["type"] == "ldt:FormalRule"}
    run = [e for e in batch if e["type"] == "ldt:PipelineRun"][0]
    for z in zones:
        assert z["location"]["type"] == "GeoProperty"
        assert z["location"]["value"]["type"] in {"Polygon", "MultiPolygon"}
        assert isinstance(z["areaKm2"]["value"], float)
        assert z["zoneRole"]["value"] in {"final", "inclusion", "exclusion", "marker", "other"}
        for ref in z["derivedFromRule"]["object"]:
            assert ref in rules  # geen zwevende randen
        assert z["generatedBy"]["object"] == run["id"]
    assert run["verdict"]["value"] == "pass"
    assert run["runId"]["value"] == "20260830T113234Z-wind"


def test_rule_and_normcard_chain():
    batch = build_utrecht_batch(WIND)
    rules = [e for e in batch if e["type"] == "ldt:FormalRule"]
    cards = {e["id"] for e in batch if e["type"] == "ldt:NormCard"}
    for r in rules:
        assert r["groundedIn"]["object"] in cards
    for c in [e for e in batch if e["type"] == "ldt:NormCard"]:
        assert c["cites"]["object"].startswith("http")


def test_unique_ids_and_sorted():
    batch = build_utrecht_batch(WIND)
    ids = [e["id"] for e in batch]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_deterministic_bytes(tmp_path):
    import hashlib

    from build_fixtures import write_batch

    p1, p2 = tmp_path / "a.jsonld", tmp_path / "b.jsonld"
    write_batch(p1, build_utrecht_batch(WIND))
    write_batch(p2, build_utrecht_batch(WIND))
    assert hashlib.sha256(p1.read_bytes()).digest() == hashlib.sha256(p2.read_bytes()).digest()


def test_zone_role_derivation():
    assert zone_role("ZR-final-opportunity-xyz") == "final"
    assert zone_role("ZR-inclusion_union-813") == "inclusion"
    assert zone_role("ZR-exclusion_natura-1") == "exclusion"
    assert zone_role("ZR-marker_groene_contour-2") == "marker"
    assert zone_role("ZR-something") == "other"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_utrecht.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_fixtures'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/build_fixtures.py
"""Canonieke run-artefacten → toolbox-sim fixtures. Deterministisch, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

CANONICAL_RUNS: dict[str, Path] = {
    "utrecht-wind": REPO / "poc" / "runs" / "20260830T113234Z-wind",
    "utrecht-zon": REPO / "poc" / "runs" / "20260830T142439Z-zon",
    "utrecht-bos": REPO / "poc" / "runs" / "20260830T142446Z-bos",
    "eindhoven-bp2op": REPO / "poc-bp2op" / "runs" / "20260830-124515-eindhoven",
}
UCS_PROCESSES = {  # processId → track; inputs worden genegeerd (documented replay)
    "utrecht-opportunity-map": "utrecht-wind",
    "utrecht-opportunity-map-wind": "utrecht-wind",
    "utrecht-opportunity-map-zon": "utrecht-zon",
    "utrecht-opportunity-map-bos": "utrecht-bos",
    "eindhoven-bp2op": "eindhoven-bp2op",
}


def prop(value: Any) -> dict:
    return {"type": "Property", "value": value}


def rel(objects: str | list[str]) -> dict:
    if isinstance(objects, str):
        return {"type": "Relationship", "object": objects}
    return {"type": "Relationship", "object": objects}


def zone_role(zone_id: str) -> str:
    z = zone_id.lower()
    if "final" in z:
        return "final"
    if "inclusion" in z:
        return "inclusion"
    if "exclusion" in z:
        return "exclusion"
    if any(k in z for k in ("marker", "attention", "conditional", "compensation")):
        return "marker"
    return "other"


def _load(run_dir: Path, name: str) -> Any:
    return json.loads((run_dir / name).read_text())


def build_utrecht_batch(run_dir: Path) -> list[dict]:
    zones = _load(run_dir, "zones.json")
    rules = _load(run_dir, "formalrules.json")
    cards = _load(run_dir, "normcards.json")
    summary = _load(run_dir, "run_summary.json")
    run_uri = f"urn:ldt:utrecht:run:{summary['runId']}"
    entities: list[dict] = [
        {
            "id": run_uri,
            "type": "ldt:PipelineRun",
            "runId": prop(summary["runId"]),
            "useCase": prop(summary["useCase"]),
            "verdict": prop(summary["verdict"]),
            "generatedAt": prop(summary["generatedAt"]),
            "headline": prop(summary["headline"]),
        }
    ]
    for card in cards:
        src = card.get("source", {})
        entities.append(
            {
                "id": f"urn:ldt:utrecht:normcard:{card['id']}",
                "type": "ldt:NormCard",
                "article": prop(src.get("article", "")),
                "quote": prop(src.get("quote_nl", "")),
                "legalForce": prop(card.get("legalForce", "")),
                "theme": prop(card.get("theme", "")),
                "cites": rel(src.get("url", "")),
            }
        )
    for rule in rules:
        entities.append(
            {
                "id": f"urn:ldt:utrecht:rule:{rule['id']}",
                "type": "ldt:FormalRule",
                "ruleType": prop(rule.get("ruleType", "")),
                "zoneSemantics": prop(rule.get("zoneSemantics", "")),
                "status": prop(rule.get("status", "")),
                "groundedIn": rel(f"urn:ldt:utrecht:normcard:{rule['normCardId']}"),
            }
        )
    for zone in zones:
        entities.append(
            {
                "id": f"urn:ldt:utrecht:zone:{zone['id']}",
                "type": "ldt:OpportunityZone",
                "location": {"type": "GeoProperty", "value": zone["geometry"]["payload"]},
                "areaKm2": prop(float(zone["areaKm2"])),
                "operation": prop(zone["operation"]),
                "zoneRole": prop(zone_role(zone["id"])),
                "derivedFromRule": rel([f"urn:ldt:utrecht:rule:{rid}" for rid in zone["ruleIds"]]),
                "generatedBy": rel(run_uri),
            }
        )
    entities.sort(key=lambda e: e["id"])
    return entities


def write_batch(path: Path, entities: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(entities, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(body, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_eubd_batch(dsn: str, limit: int = 2000) -> list[dict]:
    """Echte PostGIS `exposure.entities`-rijen → ldt:Building-entiteiten.

    Faalt hard wanneer de database onbereikbaar is — geen verzonnen gebouwen.
    """
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("psycopg niet geïnstalleerd (requirements.txt)") from exc
    sql = (
        "SELECT id, building_id, quadkey, attributes, ST_AsGeoJSON(geometry, 6)::json "
        "FROM exposure.entities WHERE category = 0 AND iso_3166 = 'NLD' "
        "ORDER BY quadkey LIMIT %s"
    )
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT doi, name FROM exposure.sources ORDER BY id LIMIT 1")
        src = cur.fetchone() or ("", "")
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
    entities = [
        {
            "id": f"urn:ldt:eubd:building:{r[0]}",
            "type": "ldt:Building",
            "buildingId": prop(r[1] or str(r[0])),
            "quadkey": prop(r[2]),
            "attributes": prop(r[3] or {}),
            "location": {"type": "GeoProperty", "value": r[4]},
            "sourceDoi": prop(src[0]),
        }
        for r in rows
    ]
    entities.sort(key=lambda e: e["id"])
    return entities


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", metavar="DSN", help="PostgreSQL DSN van de exposure-database")
    parser.add_argument("--eubd-limit", type=int, default=2000)
    args = parser.parse_args(argv)

    manifest: dict[str, Any] = {"batches": {}}
    for key, run_dir in CANONICAL_RUNS.items():
        if not run_dir.is_dir():
            raise SystemExit(f"canonieke run ontbreekt: {run_dir}")
        batch = build_utrecht_batch(run_dir) if key.startswith("utrecht") else None
        if batch is not None:
            out = FIXTURES / "ngsi-ld" / f"{key}.jsonld"
            write_batch(out, batch)
            manifest["batches"][key] = {
                "file": str(out.relative_to(FIXTURES.parent)),
                "counts": {t: sum(1 for e in batch if e["type"] == t) for t in sorted({e["type"] for e in batch})},
                "sources": {
                    name: _sha(run_dir / name)
                    for name in ("zones.json", "formalrules.json", "normcards.json", "run_summary.json")
                },
            }
    if args.eubd:
        batch = build_eubd_batch(args.eubd, limit=args.eubd_limit)
        out = FIXTURES / "ngsi-ld" / "eubd-buildings.jsonld"
        write_batch(out, batch)
        manifest["batches"]["eubd-buildings"] = {
            "file": str(out.relative_to(FIXTURES.parent)),
            "counts": {"ldt:Building": len(batch)},
            "sources": {"query": "exposure.entities category=0 iso_3166=NLD ORDER BY quadkey"},
        }
    ucs = {
        pid: {
            "track": track,
            "runId": json.loads((CANONICAL_RUNS[track] / "run_summary.json").read_text())["runId"],
            "outputs": _ucs_outputs(CANONICAL_RUNS[track]),
        }
        for pid, track in UCS_PROCESSES.items()
    }
    (FIXTURES / "ucs-processes.json").write_text(
        json.dumps(ucs, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    (FIXTURES / "trino").mkdir(exist_ok=True)
    runs_table = [
        [
            json.loads((d / "run_summary.json").read_text())["runId"],
            json.loads((d / "run_summary.json").read_text())["verdict"],
        ]
        for d in CANONICAL_RUNS.values()
    ]
    (FIXTURES / "trino" / "tables.json").write_text(
        json.dumps(
            {"catalogs": {"timescaledb": {"public": {"runs": {"columns": ["run_id", "verdict"], "rows": runs_table}}}}},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    (FIXTURES / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"fixtures herschreven: {len(manifest['batches'])} batches, ucs-processes, trino/tables.json")
    return 0


def _ucs_outputs(run_dir: Path) -> dict:
    summary = json.loads((run_dir / "run_summary.json").read_text())
    outputs = {"runId": summary["runId"], "verdict": summary["verdict"]}
    if "headline" in summary:
        outputs["headline"] = summary["headline"]
    if "counts" in summary:
        outputs["counts"] = summary["counts"]
    return outputs


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, then generate fixtures**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_utrecht.py -q`
Expected: `7 passed`

Run: `cd toolbox-sim && ../nldt/.venv/bin/python build_fixtures.py`
Expected: `fixtures herschreven: 3 batches, ucs-processes, trino/tables.json` and `fixtures/ngsi-ld/utrecht-{wind,zon,bos}.jsonld` exist.

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/build_fixtures.py toolbox-sim/tests/test_fixtures_utrecht.py toolbox-sim/fixtures
git commit -m "feat(toolbox-sim): fixture-builder Utrecht (fase-1 entiteitenmodel, deterministisch)"
```

---

### Task 6: Fixture builder — Eindhoven batch

**Files:**
- Modify: `toolbox-sim/build_fixtures.py`
- Test: `toolbox-sim/tests/test_fixtures_eindhoven.py`
- Generated (committed): `toolbox-sim/fixtures/ngsi-ld/eindhoven-bp2op.jsonld`

**Interfaces:**
- Consumes: `CANONICAL_RUNS["eindhoven-bp2op"]`, `prop`, `rel`, `write_batch` from Task 5.
- Produces: `build_eindhoven_batch(run_dir: Path) -> list[dict]` — types `ldt:ConversionRow`, `ldt:BronRegel`, `ldt:DoelRegel`, `ldt:KennisbankRelatie`, `ldt:PipelineRun`; URIs `urn:ldt:eindhoven:{row|bronregel|doelregel|kennisbank|run}:{id}`; instrument relationship target `http://lokaleregelgeving.overheid.nl/CVDR696400/4` (external URI — exempt from closure checks, which only cover `urn:ldt:` objects).

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_fixtures_eindhoven.py
import json

from build_fixtures import CANONICAL_RUNS, build_eindhoven_batch

RUN = CANONICAL_RUNS["eindhoven-bp2op"]


def _batch():
    return build_eindhoven_batch(RUN)


def test_counts_match_artifacts():
    batch = _batch()
    by_type = {}
    for e in batch:
        by_type.setdefault(e["type"], []).append(e)
    assert len(by_type["ldt:ConversionRow"]) == len(json.loads((RUN / "omzettabel.json").read_text()))
    assert len(by_type["ldt:BronRegel"]) == len(json.loads((RUN / "bronregels.json").read_text()))
    assert len(by_type["ldt:DoelRegel"]) == len(json.loads((RUN / "doelregels.json").read_text()))
    assert len(by_type["ldt:KennisbankRelatie"]) == len(json.loads((RUN / "kennisbank.json").read_text()))
    assert len(by_type["ldt:PipelineRun"]) == 1


def test_row_chain_and_score_on_relationship():
    batch = _batch()
    bron = {e["id"] for e in batch if e["type"] == "ldt:BronRegel"}
    doel = {e["id"] for e in batch if e["type"] == "ldt:DoelRegel"}
    kb = {e["id"] for e in batch if e["type"] == "ldt:KennisbankRelatie"}
    rows = [e for e in batch if e["type"] == "ldt:ConversionRow"]
    assert rows
    for r in rows:
        assert r["hasBronRegel"]["object"] in bron
        if "suggestsDoelRegel" in r:
            assert r["suggestsDoelRegel"]["object"] in doel
            assert isinstance(r["suggestsDoelRegel"]["ldt:score"]["value"], (int, float))
        if "basedOnKennisbank" in r:
            assert r["basedOnKennisbank"]["object"] in kb
        assert r["status"]["value"] != "gekoppeld"


def test_unique_sorted_ids():
    batch = _batch()
    ids = [e["id"] for e in batch]
    assert len(set(ids)) == len(ids) == len(sorted(ids))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_eindhoven.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_eindhoven_batch'`.

- [ ] **Step 3: Implement** — add to `build_fixtures.py` (after `build_utrecht_batch`) and call it in `main()` for the eindhoven key (replace the `if batch is not None` branch):

```python
def build_eindhoven_batch(run_dir: Path) -> list[dict]:
    omzettabel = _load(run_dir, "omzettabel.json")
    bronregels = _load(run_dir, "bronregels.json")
    doelregels = _load(run_dir, "doelregels.json")
    kennisbank = _load(run_dir, "kennisbank.json")
    summary = _load(run_dir, "run_summary.json")
    instrument = "http://lokaleregelgeving.overheid.nl/CVDR696400/4"
    run_uri = f"urn:ldt:eindhoven:run:{summary['runId']}"
    entities: list[dict] = [
        {
            "id": run_uri,
            "type": "ldt:PipelineRun",
            "runId": prop(summary["runId"]),
            "useCase": prop(summary["useCase"]),
            "verdict": prop(summary["verdict"]),
            "generatedAt": prop(summary["generatedAt"]),
            "counts": prop(summary["counts"]),
        }
    ]
    for kb in kennisbank:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:kennisbank:{kb['id']}",
                "type": "ldt:KennisbankRelatie",
                "relationType": prop(kb.get("relatie", "")),
                "source": prop(kb.get("url", "")),
                "bronDocId": prop(kb.get("bronDocId", "")),
            }
        )
    for br in bronregels:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:bronregel:{br['id']}",
                "type": "ldt:BronRegel",
                "locator": prop(br.get("locator", {})),
                "permalink": prop(br.get("url", "")),
                "statusInBron": prop(br.get("statusInBron", "")),
                "partOfInstrument": rel(instrument),
            }
        )
    for dr in doelregels:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:doelregel:{dr['id']}",
                "type": "ldt:DoelRegel",
                "locator": prop(dr.get("locator", {})),
                "permalink": prop(dr.get("url", "")),
                "partOfInstrument": rel(instrument),
            }
        )
    for row in omzettabel:
        suggesties = row.get("suggesties") or []
        best = suggesties[0] if suggesties else None
        entity = {
            "id": f"urn:ldt:eindhoven:row:{row['id']}",
            "type": "ldt:ConversionRow",
            "status": prop(row["status"]),
            "needsHumanReden": prop(row.get("needsHumanReden")),
            "suggestions": prop(suggesties),
            "hasBronRegel": rel(f"urn:ldt:eindhoven:bronregel:{row['bronRegelId']}"),
            "generatedBy": rel(run_uri),
        }
        if best:
            entity["suggestsDoelRegel"] = {
                "type": "Relationship",
                "object": f"urn:ldt:eindhoven:doelregel:{best['doelRegelId']}",
                "ldt:score": prop(best["score"]),
            }
        if best and best.get("kennisbankHitId"):
            entity["basedOnKennisbank"] = rel(
                f"urn:ldt:eindhoven:kennisbank:{best['kennisbankHitId']}"
            )
        entities.append(entity)
    entities.sort(key=lambda e: e["id"])
    return entities
```

In `main()`, replace the loop body:

```python
    for key, run_dir in CANONICAL_RUNS.items():
        if not run_dir.is_dir():
            raise SystemExit(f"canonieke run ontbreekt: {run_dir}")
        batch = (
            build_utrecht_batch(run_dir) if key.startswith("utrecht") else build_eindhoven_batch(run_dir)
        )
        out = FIXTURES / "ngsi-ld" / f"{key}.jsonld"
        write_batch(out, batch)
        manifest["batches"][key] = {
            "file": str(out.relative_to(FIXTURES.parent)),
            "counts": {t: sum(1 for e in batch if e["type"] == t) for t in sorted({e["type"] for e in batch})},
            "sources": {
                name: _sha(run_dir / name)
                for name in (
                    ("zones.json", "formalrules.json", "normcards.json", "run_summary.json")
                    if key.startswith("utrecht")
                    else ("omzettabel.json", "bronregels.json", "doelregels.json", "kennisbank.json", "run_summary.json")
                )
            },
        }
```

- [ ] **Step 4: Run tests, regenerate, commit**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_eindhoven.py tests/test_fixtures_utrecht.py -q`
Expected: `10 passed`

Run: `cd toolbox-sim && ../nldt/.venv/bin/python build_fixtures.py`
Expected: `fixtures herschreven: 4 batches, ucs-processes, trino/tables.json`

```bash
git add toolbox-sim/build_fixtures.py toolbox-sim/tests/test_fixtures_eindhoven.py toolbox-sim/fixtures
git commit -m "feat(toolbox-sim): fixture-builder Eindhoven (conversiegraaf, score-op-relatie)"
```

---

### Task 7: Data Platform broker app (NGSI-LD + UCS-proxy variant)

**Files:**
- Create: `toolbox-sim/app/data_platform.py`
- Test: `toolbox-sim/tests/test_broker.py`

**Interfaces:**
- Consumes: `app.guards.require_bearer`, `app.guards.add_provenance`, `app.guards.provenance_detail`.
- Produces: `create_broker_app(*, entities_by_tenant: dict[str, list[dict]], provenance_by_tenant: dict[str, str], include_proxy: bool = False, include_trino: bool = False) -> FastAPI`
  - `GET /health` (no auth) → `{"status": "UP"}`
  - `GET /ngsi-ld/v1/entities?type=&limit=` (auth; header `NGSILD-Tenant`, default `"ldt"`) → JSON list filtered by `type`
  - `GET /ngsi-ld/v1/entities/{id}` → entity or 404 `{"error": "NotFound"}`
  - `POST /ngsi-ld/v1/entityOperations/upsert` → `204`, merges list by `id` into the request's tenant
  - `GET /api/v1/data-platform/entities?scope=&type=&limit=` → `{"data": [...]}`; `GET /api/v1/data-platform/entities/{id}` → `{"data": entity}` (only when `include_proxy=True`)
  - Unknown tenant → empty list (broker semantics, no error)

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_broker.py
from fastapi.testclient import TestClient

from app.data_platform import create_broker_app
from app.jwtutil import mint_token

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
ENTITIES = [
    {
        "id": "urn:ldt:utrecht:zone:ZR-1",
        "type": "ldt:OpportunityZone",
        "areaKm2": {"type": "Property", "value": 1.5},
        "location": {"type": "GeoProperty", "value": {"type": "Point", "coordinates": [5.1, 52.1]}},
    },
    {"id": "urn:ldt:eindhoven:row:OT-1", "type": "ldt:ConversionRow"},
]

app = create_broker_app(
    entities_by_tenant={"ldt": ENTITIES},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform; fixture=utrecht-wind; run=20260830T113234Z-wind"},
    include_proxy=True,
)
client = TestClient(app)


def test_health_open():
    assert client.get("/health").status_code == 200


def test_list_by_type_with_tenant_header():
    r = client.get("/ngsi-ld/v1/entities", params={"type": "ldt:OpportunityZone"}, headers={**AUTH, "NGSILD-Tenant": "ldt"})
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == ["urn:ldt:utrecht:zone:ZR-1"]
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/data-platform")


def test_unknown_tenant_empty_list():
    r = client.get("/ngsi-ld/v1/entities", headers={**AUTH, "NGSILD-Tenant": "nope"})
    assert r.status_code == 200
    assert r.json() == []


def test_get_by_id_and_404():
    ok = client.get("/ngsi-ld/v1/entities/urn:ldt:eindhoven:row:OT-1", headers=AUTH)
    assert ok.status_code == 200 and ok.json()["id"] == "urn:ldt:eindhoven:row:OT-1"
    miss = client.get("/ngsi-ld/v1/entities/urn:ldt:none:1", headers=AUTH)
    assert miss.status_code == 404


def test_upsert_then_read_back_in_same_tenant():
    new = [{"id": "urn:ldt:test:zone:Z-9", "type": "ldt:OpportunityZone"}]
    r = client.post("/ngsi-ld/v1/entityOperations/upsert", json=new, headers={**AUTH, "NGSILD-Tenant": "ldt"})
    assert r.status_code == 204
    got = client.get("/ngsi-ld/v1/entities/urn:ldt:test:zone:Z-9", headers=AUTH)
    assert got.status_code == 200


def test_proxy_envelope_shape():  # data_platform._list_via_ucs_proxy verwacht {"data": ...}
    r = client.get("/api/v1/data-platform/entities", params={"type": "ldt:ConversionRow", "scope": "urn:ngsi-ld:scope:default"}, headers=AUTH)
    assert r.status_code == 200
    assert [e["id"] for e in r.json()["data"]] == ["urn:ldt:eindhoven:row:OT-1"]
    one = client.get("/api/v1/data-platform/entities/urn:ldt:eindhoven:row:OT-1", headers=AUTH)
    assert one.json()["data"]["id"] == "urn:ldt:eindhoven:row:OT-1"


def test_broker_requires_bearer():
    assert client.get("/ngsi-ld/v1/entities").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_broker.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.data_platform'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/data_platform.py
"""EU LDT Data Platform-sim: NGSI-LD-broker (+ UCS-proxyvariant; Trino in Task 8)."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response

from app.guards import add_provenance, provenance_detail, require_bearer


def create_broker_app(
    *,
    entities_by_tenant: dict[str, list[dict]],
    provenance_by_tenant: dict[str, str],
    include_proxy: bool = False,
    include_trino: bool = False,
) -> FastAPI:
    app = FastAPI(title="toolbox-sim data-platform", docs_url=None, openapi_url=None)
    add_provenance(app, "data-platform")
    store: dict[str, dict[str, dict]] = {
        tenant: {e["id"]: e for e in entities} for tenant, entities in entities_by_tenant.items()
    }

    def _tenant(x_tenant: str) -> dict[str, dict]:
        return store.setdefault(x_tenant, {})

    def _prov(x_tenant: str) -> dict:
        return provenance_detail(provenance_by_tenant.get(x_tenant, "toolbox-sim/data-platform"))

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/ngsi-ld/v1/entities")
    def list_entities(
        request: Request,
        type: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"),
        _: dict = Depends(require_bearer),
    ):
        tenant = _tenant(x_tenant)
        entities = list(tenant.values())
        if type:
            entities = [e for e in entities if e.get("type") == type]
        entities.sort(key=lambda e: e["id"])
        return Response(
            content=json.dumps(entities[:limit], separators=(",", ":")),
            media_type="application/json",
            headers=_prov(x_tenant),
        )

    @app.get("/ngsi-ld/v1/entities/{entity_id}")
    def get_entity(entity_id: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        entity = _tenant(x_tenant).get(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": entity_id})
        return Response(
            content=json.dumps(entity, separators=(",", ":")),
            media_type="application/json",
            headers=_prov(x_tenant),
        )

    @app.post("/ngsi-ld/v1/entityOperations/upsert", status_code=204)
    def upsert(batch: list[dict], x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        tenant = _tenant(x_tenant)
        for entity in batch:
            tenant[entity["id"]] = entity

    if include_proxy:

        @app.get("/api/v1/data-platform/entities")
        def proxy_list(
            type: str | None = Query(default=None),
            scope: str | None = Query(default=None),
            limit: int = Query(default=100, ge=1, le=1000),
            x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"),
            _: dict = Depends(require_bearer),
        ):
            tenant = _tenant(x_tenant)
            entities = list(tenant.values())
            if type:
                entities = [e for e in entities if e.get("type") == type]
            entities.sort(key=lambda e: e["id"])
            return {"data": entities[:limit]}

        @app.get("/api/v1/data-platform/entities/{entity_id}")
        def proxy_get(entity_id: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
            entity = _tenant(x_tenant).get(entity_id)
            if entity is None:
                raise HTTPException(status_code=404, detail={"error": "NotFound", "description": entity_id})
            return {"data": entity}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_broker.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/data_platform.py toolbox-sim/tests/test_broker.py
git commit -m "feat(toolbox-sim): NGSI-LD-broker + UCS-proxyvariant (tenants, 404, upsert)"
```

---

### Task 8: Trino stub (on the broker app)

**Files:**
- Modify: `toolbox-sim/app/data_platform.py`
- Test: `toolbox-sim/tests/test_trino.py`

**Interfaces:**
- Consumes: `fixtures/trino/tables.json` (`{"catalogs": {catalog: {schema: {table: {"columns": [...], "rows": [...]}}}}}`, generated by Task 5's `build_fixtures.py`).
- Produces (inside `create_broker_app` when `include_trino=True`): `POST /v1/statement` (auth) — body is raw SQL text; honours optional `X-Trino-User`/`X-Trino-Catalog`/`X-Trino-Schema` headers (accepted, not required); supports case-insensitively:
  - `SHOW SCHEMAS FROM <catalog>` → `{"columns": [{"name": "Schema", "type": "varchar"}], "data": [[schema], ...], "nextUri": null}`
  - `SHOW TABLES FROM <catalog>.<schema>` → same shape with table names
  - `SELECT * FROM <catalog>.<schema>.<table>` (optional trailing `LIMIT n`) → fixture columns/rows
  - statements starting with `insert|update|delete|drop|create|alter|truncate` → `403 {"error": "write-forbidden"}`
  - anything else → `400 {"error": "unsupported-statement", "error_description": "stub ondersteunt SHOW SCHEMAS FROM, SHOW TABLES FROM <cat>.<sch> en SELECT * FROM ... [LIMIT n]"}`

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_trino.py
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.data_platform import create_broker_app
from app.jwtutil import mint_token

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
TABLES = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "trino" / "tables.json").read_text())

app = create_broker_app(
    entities_by_tenant={"ldt": []},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform"},
    include_trino=True,
)
client = TestClient(app)


def test_show_schemas():
    r = client.post("/v1/statement", content="SHOW SCHEMAS FROM timescaledb", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert [c["name"] for c in body["columns"]] == ["Schema"]
    assert body["data"] == [[s] for s in TABLES["catalogs"]["timescaledb"]]
    assert body["nextUri"] is None  # adapter-stopping while-lus


def test_show_tables():
    r = client.post("/v1/statement", content="show tables from timescaledb.public", headers=AUTH)
    assert r.status_code == 200
    assert [row[0] for row in r.json()["data"]] == ["runs"]


def test_select_star_with_limit():
    r = client.post("/v1/statement", content="SELECT * FROM timescaledb.public.runs LIMIT 2", headers={**AUTH, "X-Trino-User": "nldt-agent"})
    assert r.status_code == 200
    body = r.json()
    assert [c["name"] for c in body["columns"]] == ["run_id", "verdict"]
    assert len(body["data"]) == 2
    assert all(row[1] == "pass" for row in body["data"])  # echte canonieke verdicts


def test_write_forbidden_403():
    r = client.post("/v1/statement", content="DELETE FROM timescaledb.public.runs", headers=AUTH)
    assert r.status_code == 403
    assert r.json()["error"] == "write-forbidden"


def test_unsupported_400():
    r = client.post("/v1/statement", content="SELECT count(*) FROM x", headers=AUTH)
    assert r.status_code == 400
    assert r.json()["error"] == "unsupported-statement"


def test_requires_bearer():
    assert client.post("/v1/statement", content="SHOW SCHEMAS FROM timescaledb").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_trino.py -q`
Expected: FAIL — `test_show_schemas` gets 404 (`/v1/statement` route does not exist yet).

- [ ] **Step 3: Implement** — add inside `create_broker_app`, after the proxy block (the module-level `import json` from Task 7 is already present):

```python
    if include_trino:
        import re

        from pathlib import Path

        tables = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "trino" / "tables.json").read_text())

        def _result(columns: list[str], rows: list[list]) -> dict:
            return {
                "id": "statement-sim-0",
                "stats": {},
                "columns": [{"name": c, "type": "varchar"} for c in columns],
                "data": rows,
                "nextUri": None,
            }

        @app.post("/v1/statement")
        async def statement(request: Request, _: dict = Depends(require_bearer)):
            sql = (await request.body()).decode("utf-8", "replace").strip()
            normalized = " ".join(sql.lower().split())
            if re.match(r"^(insert|update|delete|drop|create|alter|truncate)\b", normalized):
                raise HTTPException(status_code=403, detail={"error": "write-forbidden"})
            m = re.match(r"^show schemas from (\w+)$", normalized)
            if m:
                catalog = tables["catalogs"].get(m.group(1))
                if catalog is None:
                    raise HTTPException(status_code=404, detail={"error": "catalog-not-found"})
                return _result(["Schema"], [[s] for s in sorted(catalog)])
            m = re.match(r"^show tables from (\w+)\.(\w+)$", normalized)
            if m:
                schema = tables["catalogs"].get(m.group(1), {}).get(m.group(2))
                if schema is None:
                    raise HTTPException(status_code=404, detail={"error": "schema-not-found"})
                return _result(["Table"], [[t] for t in sorted(schema)])
            m = re.match(r"^select \* from (\w+)\.(\w+)\.(\w+)(?: limit (\d+))?$", normalized)
            if m:
                table = tables["catalogs"].get(m.group(1), {}).get(m.group(2), {}).get(m.group(3))
                if table is None:
                    raise HTTPException(status_code=404, detail={"error": "table-not-found"})
                rows = [list(r) for r in table["rows"]]
                if m.group(4):
                    rows = rows[: int(m.group(4))]
                return _result(table["columns"], rows)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported-statement",
                    "error_description": "stub ondersteunt SHOW SCHEMAS FROM, SHOW TABLES FROM <cat>.<sch> en SELECT * FROM ... [LIMIT n]",
                },
            )
```

- [ ] **Step 4: Run tests (all broker + trino) and commit**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_broker.py tests/test_trino.py -q`
Expected: `13 passed`

```bash
git add toolbox-sim/app/data_platform.py toolbox-sim/tests/test_trino.py
git commit -m "feat(toolbox-sim): Trino-stub (SHOW/SELECT-vormen, 403 schrijfacties)"
```

---

### Task 9: Play & Visualise app

**Files:**
- Create: `toolbox-sim/app/play_visualise.py`
- Test: `toolbox-sim/tests/test_play_visualise.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
  - `GET /health` → `{"status": "UP"}` (no auth)
  - `POST /api/dataSources` (auth, JSON `{name, sourceConfiguration: {type, url, headers}, securityConfiguration: {type, headers}}`) → `{"id": "ds-<n>", "name", "sourceConfiguration", "securityConfiguration"}` — 422 via FastAPI when `sourceConfiguration.url` missing (declare it as a nested model)
  - `POST /api/dataLayers` (auth, `{name, dataSource, type, configuration}`) → `{"id": "dl-<n>", ...}` — 404 when `dataSource` unknown
  - `GET /api/dataLayers/{id}` (auth) → layer or 404

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_play_visualise.py
from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.play_visualise import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
client = TestClient(create_app())

DS_PAYLOAD = {  # exact de vorm uit nldt/services/adapters/play_visualise.py
    "name": "utrecht-wind-source",
    "sourceConfiguration": {"type": "EXTERNAL", "url": "http://localhost:8084/exports/wind.geojson", "headers": []},
    "securityConfiguration": {"type": "OTHER", "headers": []},
}
DL_PAYLOAD = {"name": "utrecht-wind", "dataSource": "", "type": "SCENARIO", "configuration": {}}


def test_create_data_source_and_layer():
    ds = client.post("/api/dataSources", json=DS_PAYLOAD, headers=AUTH)
    assert ds.status_code == 200 and ds.json()["id"].startswith("ds-")
    payload = dict(DL_PAYLOAD, dataSource=ds.json()["id"])
    dl = client.post("/api/dataLayers", json=payload, headers=AUTH)
    assert dl.status_code == 200 and dl.json()["id"].startswith("dl-")
    fetched = client.get(f"/api/dataLayers/{dl.json()['id']}", headers=AUTH)
    assert fetched.status_code == 200 and fetched.json()["type"] == "SCENARIO"


def test_layer_unknown_datasource_404():
    r = client.post("/api/dataLayers", json=dict(DL_PAYLOAD, dataSource="ds-nope"), headers=AUTH)
    assert r.status_code == 404


def test_datasource_requires_url_422():
    bad = dict(DS_PAYLOAD, sourceConfiguration={"type": "EXTERNAL", "headers": []})
    assert client.post("/api/dataSources", json=bad, headers=AUTH).status_code == 422


def test_requires_bearer():
    assert client.post("/api/dataSources", json=DS_PAYLOAD).status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_play_visualise.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.play_visualise'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/play_visualise.py
"""EU LDT Play & Visualise-sim: dataSources + dataLayers (SCENARIO)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class SourceConfiguration(BaseModel):
    type: str
    url: str
    headers: list = []


class SecurityConfiguration(BaseModel):
    type: str
    headers: list = []


class DataSourceIn(BaseModel):
    name: str
    sourceConfiguration: SourceConfiguration
    securityConfiguration: SecurityConfiguration


class DataLayerIn(BaseModel):
    name: str
    dataSource: str
    type: str
    configuration: dict = {}


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim play-visualise", docs_url=None, openapi_url=None)
    add_provenance(app, "play-visualise")
    data_sources: dict[str, dict] = {}
    data_layers: dict[str, dict] = {}
    counter = {"n": 0}

    def _next(prefix: str) -> str:
        counter["n"] += 1
        return f"{prefix}-{counter['n']}"

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/dataSources")
    def create_data_source(payload: DataSourceIn, _: dict = Depends(require_bearer)):
        ds_id = _next("ds")
        data_sources[ds_id] = payload.model_dump()
        data_sources[ds_id]["id"] = ds_id
        return data_sources[ds_id]

    @app.post("/api/dataLayers")
    def create_data_layer(payload: DataLayerIn, _: dict = Depends(require_bearer)):
        if payload.dataSource not in data_sources:
            raise HTTPException(status_code=404, detail={"error": "dataSourceNotFound", "description": payload.dataSource})
        dl_id = _next("dl")
        data_layers[dl_id] = payload.model_dump()
        data_layers[dl_id]["id"] = dl_id
        return data_layers[dl_id]

    @app.get("/api/dataLayers/{dl_id}")
    def get_data_layer(dl_id: str, _: dict = Depends(require_bearer)):
        if dl_id not in data_layers:
            raise HTTPException(status_code=404, detail={"error": "dataLayerNotFound", "description": dl_id})
        return data_layers[dl_id]

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_play_visualise.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/play_visualise.py toolbox-sim/tests/test_play_visualise.py
git commit -m "feat(toolbox-sim): P&V-sim (dataSources/dataLayers, sessie-persistent)"
```

---

### Task 10: UCS app (trigger-process replay)

**Files:**
- Create: `toolbox-sim/app/ucs.py`
- Test: `toolbox-sim/tests/test_ucs.py`

**Interfaces:**
- Consumes: `fixtures/ucs-processes.json` — `{processId: {"track", "runId", "outputs"}}` (generated in Task 5).
- Produces: `create_app(processes: dict) -> FastAPI`
  - `GET /health` → `{"status": "UP"}` (no auth)
  - `POST /api/v1/experiments/trigger-process` (auth, `{processId, inputs}`) → `{"outputs": <outputs>, "provenance": "sim-replay://canonical/<runId>"}`; unknown processId → 404 `{"error": "process-not-found"}` (so `UCSAdapter` falls back to `execute_local`, exactly like the real tool).

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_ucs.py
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.ucs import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
PROCESSES = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ucs-processes.json").read_text())
client = TestClient(create_app(PROCESSES))


def test_trigger_known_process_replays_canonical_outputs():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "utrecht-opportunity-map", "inputs": {}}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["provenance"] == f"sim-replay://canonical/{body['outputs']['runId']}"
    assert body["outputs"]["verdict"] == "pass"
    assert "headline" in body["outputs"]


def test_unknown_process_404_for_local_fallback():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "nope", "inputs": {}}, headers=AUTH)
    assert r.status_code == 404
    assert r.json()["error"] == "process-not-found"


def test_requires_bearer():
    r = client.post("/api/v1/experiments/trigger-process", json={"processId": "utrecht-opportunity-map", "inputs": {}})
    assert r.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_ucs.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ucs'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/ucs.py
"""EU LDT Use Cases & Scenarios-sim: experiment-trigger = canonieke replay."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class TriggerIn(BaseModel):
    processId: str
    inputs: dict = {}


def create_app(processes: dict) -> FastAPI:
    app = FastAPI(title="toolbox-sim ucs", docs_url=None, openapi_url=None)
    add_provenance(app, "ucs")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/experiments/trigger-process")
    def trigger(payload: TriggerIn, _: dict = Depends(require_bearer)):
        entry = processes.get(payload.processId)
        if entry is None:
            raise HTTPException(status_code=404, detail={"error": "process-not-found", "description": payload.processId})
        return {
            "outputs": entry["outputs"],
            "provenance": f"sim-replay://canonical/{entry['runId']}",
        }

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_ucs.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/ucs.py toolbox-sim/tests/test_ucs.py
git commit -m "feat(toolbox-sim): UCS-sim (trigger-process, 404→local fallback)"
```

---

### Task 11: Marketplace app (assets + publish)

**Files:**
- Create: `toolbox-sim/app/marketplace.py`
- Test: `toolbox-sim/tests/test_marketplace.py`

**Interfaces:**
- Produces: `create_app() -> FastAPI`
  - `GET /health` → `{"status": "UP"}` (no auth)
  - `POST /api/v1/agent/assets` (auth, multipart `file`) → `{"id": "asset-<n>"}`
  - `POST /api/v1/agent/assets/{asset_id}/publish` (auth, `{name, description, categories, licence}`) → `{"id", "status": "published", "publishState": {"offering_id": "sim-offering-asset-<n>"}, "name", "licence"}`; unknown asset → 404
  - `GET /api/v1/agent/assets` (auth) → `{"data": [...]}` — published metadata only (asset bytes stay server-side)

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_marketplace.py
from fastapi.testclient import TestClient

from app.jwtutil import mint_token
from app.marketplace import create_app

AUTH = {"Authorization": f"Bearer {mint_token('nldt-agent', [])}"}
client = TestClient(create_app())


def test_upload_and_publish_flow():  # vorm van nldt/services/marketplace_publish.py
    up = client.post(
        "/api/v1/agent/assets",
        files={"file": ("recipe-utrecht-opportunity-map-v1.0.0.json", b'{"recipe": {}}', "application/json")},
        headers=AUTH,
    )
    assert up.status_code == 200
    asset_id = up.json()["id"]
    pub = client.post(
        f"/api/v1/agent/assets/{asset_id}/publish",
        json={"name": "Utrecht opportunity map", "description": "sim", "categories": ["urn:ngsi-ld:category:processes"], "licence": "EUPL-1.2"},
        headers=AUTH,
    )
    assert pub.status_code == 200
    body = pub.json()
    assert body["status"] == "published"
    assert body["publishState"]["offering_id"] == f"sim-offering-{asset_id}"


def test_listing_after_publish():
    listing = client.get("/api/v1/agent/assets", headers=AUTH)
    assert listing.status_code == 200
    assert any(a.get("status") == "published" for a in listing.json()["data"])


def test_publish_unknown_asset_404():
    r = client.post("/api/v1/agent/assets/asset-999/publish", json={"name": "x", "description": "y", "categories": [], "licence": "EUPL-1.2"}, headers=AUTH)
    assert r.status_code == 404


def test_requires_bearer():
    assert client.get("/api/v1/agent/assets").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_marketplace.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.marketplace'`.

- [ ] **Step 3: Implement**

```python
# toolbox-sim/app/marketplace.py
"""EU LDT Marketplace Agent-sim: upload + publish met offering-id."""
from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class PublishIn(BaseModel):
    name: str
    description: str
    categories: list[str]
    licence: str = "EUPL-1.2"


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim marketplace", docs_url=None, openapi_url=None)
    add_provenance(app, "marketplace")
    assets: dict[str, dict] = {}
    counter = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/agent/assets")
    async def upload(file: UploadFile = File(...), _: dict = Depends(require_bearer)):
        counter["n"] += 1
        asset_id = f"asset-{counter['n']}"
        assets[asset_id] = {"id": asset_id, "fileName": file.filename, "size": len(await file.read()), "status": "uploaded"}
        return {"id": asset_id}

    @app.post("/api/v1/agent/assets/{asset_id}/publish")
    def publish(asset_id: str, payload: PublishIn, _: dict = Depends(require_bearer)):
        asset = assets.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail={"error": "assetNotFound", "description": asset_id})
        asset.update(
            status="published",
            name=payload.name,
            description=payload.description,
            categories=payload.categories,
            licence=payload.licence,
            publishState={"offering_id": f"sim-offering-{asset_id}"},
        )
        return asset

    @app.get("/api/v1/agent/assets")
    def listing(_: dict = Depends(require_bearer)):
        return {"data": [dict(a) for a in assets.values()]}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_marketplace.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/marketplace.py toolbox-sim/tests/test_marketplace.py
git commit -m "feat(toolbox-sim): Marketplace-sim (multipart upload, publish, offering-id)"
```

---

### Task 12: Multi-port server + run_sim.sh + .env.sim

**Files:**
- Create: `toolbox-sim/app/server.py`, `toolbox-sim/run_sim.sh`, `toolbox-sim/.env.sim`
- Test: `toolbox-sim/tests/test_server_boot.py`

**Interfaces:**
- Consumes: all `create_app`/`create_broker_app` factories; fixtures from `fixtures/`.
- Produces: `python -m app.server [--eubd]` — boots 9191–9195 always, 9196 only with `--eubd` **and** an existing `fixtures/ngsi-ld/eubd-buildings.jsonld` (else exit 1 with reason). Loads all `fixtures/ngsi-ld/*.jsonld` (except `eubd-*`) into tenant `ldt` with provenance `toolbox-sim/data-platform; fixture=<name>; run=<runId from fixtures/manifest.json>`; EUBD batch into tenant `eubd`.

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_server_boot.py
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

SIM_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sim():
    proc = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=SIM_ROOT)
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:9191/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise AssertionError("sim kwam niet op binnen 20 s")
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _token() -> str:
    r = httpx.post(
        "http://127.0.0.1:9191/realms/LDT/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": "nldt-agent", "client_secret": "sim-dev-secret"},
    )
    return r.json()["access_token"]


def test_all_five_services_healthy(sim):
    for port in (9191, 9192, 9193, 9194, 9195):
        assert httpx.get(f"http://127.0.0.1:{port}/health").json()["status"] == "UP"


def test_broker_serves_canonical_fixture_over_http(sim):
    auth = {"Authorization": f"Bearer {_token()}", "NGSILD-Tenant": "ldt"}
    r = httpx.get("http://127.0.0.1:9192/ngsi-ld/v1/entities", params={"type": "ldt:OpportunityZone", "limit": 1000}, headers=auth)
    assert r.status_code == 200
    zones = r.json()
    assert zones and all(z["id"].startswith("urn:ldt:utrecht:zone:") for z in zones)
    assert r.headers["X-Sim-Provenance"].startswith("toolbox-sim/data-platform")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_server_boot.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.server'` in the subprocess (test errors on health-poll timeout).

- [ ] **Step 3: Implement**

`toolbox-sim/app/server.py`:

```python
# toolbox-sim/app/server.py
"""Start alle sim-diensten: 9191–9195 (+9196 met --eubd)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import uvicorn

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PORTS = {"identity": 9191, "broker": 9192, "pv": 9193, "ucs": 9194, "marketplace": 9195, "eubd": 9196}


def _load_batches(exclude_eubd: bool = True) -> tuple[dict[str, list[dict]], dict[str, str]]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    entities: list[dict] = []
    names: list[str] = []
    for name in sorted(manifest["batches"]):
        if exclude_eubd and name.startswith("eubd"):
            continue
        entities.extend(json.loads((FIXTURES / "ngsi-ld" / f"{name}.jsonld").read_text()))
        names.append(name)
    provenance = {"ldt": f"toolbox-sim/data-platform; fixtures={','.join(names)}"}
    return {"ldt": entities}, provenance


def _eubd_batch() -> list[dict]:
    path = FIXTURES / "ngsi-ld" / "eubd-buildings.jsonld"
    if not path.exists():
        raise SystemExit("--eubd gevraagd maar fixtures/ngsi-ld/eubd-buildings.jsonld ontbreekt; draai build_fixtures.py --eubd <DSN>")
    return json.loads(path.read_text())


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", action="store_true", help="start ook de EUBD-feed op 9196")
    args = parser.parse_args(argv)

    from app.data_platform import create_broker_app
    from app.identity import create_app as identity_app
    from app.marketplace import create_app as marketplace_app
    from app.play_visualise import create_app as pv_app
    from app.ucs import create_app as ucs_app

    entities_by_tenant, provenance = _load_batches()
    ucs_processes = json.loads((FIXTURES / "ucs-processes.json").read_text())
    apps = {
        "identity": identity_app(),
        "broker": create_broker_app(
            entities_by_tenant=entities_by_tenant,
            provenance_by_tenant=provenance,
            include_proxy=True,
            include_trino=True,
        ),
        "pv": pv_app(),
        "ucs": ucs_app(ucs_processes),
        "marketplace": marketplace_app(),
    }
    if args.eubd:
        apps["eubd"] = create_broker_app(
            entities_by_tenant={"eubd": _eubd_batch()},
            provenance_by_tenant={"eubd": "toolbox-sim/data-platform; fixture=eubd-buildings; source=exposure.entities"},
        )
    servers = [
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORTS[name], log_level="warning"))
        for name, app in apps.items()
    ]
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
```

`toolbox-sim/run_sim.sh`:

```bash
#!/usr/bin/env bash
# Start de toolbox-sim (9191–9195; --eubd voegt 9196 toe).
set -euo pipefail
cd "$(dirname "$0")"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
elif [ -x "../nldt/.venv/bin/python" ]; then PY="../nldt/.venv/bin/python"
else PY="python3"; fi
exec "$PY" -m app.server "$@"
```

`toolbox-sim/.env.sim`:

```bash
# nldt-adapters → toolbox-sim (alle mocks uit)
KEYCLOAK_URL=http://127.0.0.1:9191
KEYCLOAK_REALM=LDT
KEYCLOAK_CLIENT_ID=nldt-agent
KEYCLOAK_CLIENT_SECRET=sim-dev-secret
NLDT_NGSI_LD_URL=http://127.0.0.1:9192
NLDT_DATA_PLATFORM_MOCK=false
NLDT_TRINO_URL=http://127.0.0.1:9192
NLDT_PV_BASE_URL=http://127.0.0.1:9193
NLDT_PV_MOCK=false
NLDT_EXPORT_PUBLIC_BASE=http://127.0.0.1:9193/exports
UCS_BASE_URL=http://127.0.0.1:9194
UCS_TOKEN=sim-toolbox-token
MARKETPLACE_AGENT_URL=http://127.0.0.1:9195
MARKETPLACE_TOKEN=sim-toolbox-token
MARKETPLACE_MOCK=false
```

- [ ] **Step 4: Run test to verify it passes**

Run: `chmod +x toolbox-sim/run_sim.sh && cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_server_boot.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/server.py toolbox-sim/run_sim.sh toolbox-sim/.env.sim toolbox-sim/tests/test_server_boot.py
git commit -m "feat(toolbox-sim): multi-port server (9191-9195, --eubd) + run_sim.sh + .env.sim"
```

---

### Task 13: EUBD feed (PostGIS → Building entities)

**Files:**
- Modify: `toolbox-sim/build_fixtures.py` (no code change expected — `build_eubd_batch` exists from Task 5; this task verifies it end-to-end)
- Test: `toolbox-sim/tests/test_eubd.py`

**Interfaces:**
- Consumes: `build_eubd_batch(dsn, limit)` from Task 5; local PostGIS `exposure` database (SETUP.md: Postgres.app, port 5432, user `marc`, table `exposure.entities`).
- Produces: `fixtures/ngsi-ld/eubd-buildings.jsonld` when built with `--eubd`; served on 9196 (tenant `eubd`) by Task 12's server.

- [ ] **Step 1: Write the failing test**

```python
# toolbox-sim/tests/test_eubd.py
import json
import os
from pathlib import Path

import pytest

DSN = os.environ.get("TOOLBOX_SIM_EUBD_DSN", "")


def test_builder_fails_hard_without_db():
    from build_fixtures import build_eubd_batch

    with pytest.raises(Exception) as excinfo:  # psycopg OperationalError — nooit stille mock
        build_eubd_batch("postgresql://nobody@127.0.0.1:1/nowhere", limit=5)
    assert "mock" not in str(excinfo.value).lower()


@pytest.mark.skipif(not DSN, reason="TOOLBOX_SIM_EUBD_DSN niet gezet — PostGIS exposure niet beschikbaar")
def test_eubd_entities_from_real_rows():
    from build_fixtures import build_eubd_batch

    batch = build_eubd_batch(DSN, limit=50)
    assert 0 < len(batch) <= 50
    for e in batch:
        assert e["type"] == "ldt:Building"
        assert e["id"].startswith("urn:ldt:eubd:building:")
        assert e["location"]["type"] == "GeoProperty"
        assert e["location"]["value"]["type"] == "MultiPolygon"
        assert e["sourceDoi"]["value"]  # echte release-DOI uit exposure.sources
```

- [ ] **Step 2: Run test to verify it fails/passes as designed**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_eubd.py -q`
Expected: `1 passed, 1 skipped` (fail-hard test passes; PostGIS test skips without DSN). If `fail-hard` fails, fix `build_eubd_batch` in `build_fixtures.py` (Task 5 code) until it raises, never mocks.

- [ ] **Step 3: Build against the real database (machine with PostGIS)**

Run: `TOOLBOX_SIM_EUBD_DSN="postgresql://marc@localhost:5432/exposure" ../nldt/.venv/bin/python build_fixtures.py --eubd "$TOOLBOX_SIM_EUBD_DSN"`
Then rerun: `../nldt/.venv/bin/python -m pytest tests/test_eubd.py -q` → `2 passed`.

- [ ] **Step 4: Commit**

```bash
git add toolbox-sim/tests/test_eubd.py toolbox-sim/fixtures/ngsi-ld/eubd-buildings.jsonld toolbox-sim/fixtures/manifest.json
git commit -m "feat(toolbox-sim): EUBD-feed uit echte PostGIS-rijen (fail-hard zonder db)"
```

---

### Task 14: Live adapter test — nldt adapters against the running sim

**Files:**
- Create: `toolbox-sim/tests/test_adapters_live.py`
- Modify: `toolbox-sim/tests/conftest.py` (add live-sim session fixture)

**Interfaces:**
- Consumes: running sim from Task 12; `.env.sim`; nldt adapter modules (`sys.path` gets `<repo>/nldt` prepended, env set **before** import — the adapters read env at import time).
- Produces: pytest module proving the five adapter paths work live: `keycloak_auth.get_service_token`, `data_platform.list_entities`/`list_scopes`/`trino_query`, `play_visualise.register_geojson_layer`, `UCSAdapter.execute`, `marketplace_publish.publish_recipe`.

- [ ] **Step 1: Add the live-sim fixture to `conftest.py`**

```python
# toolbox-sim/tests/conftest.py — append below the existing sys.path lines
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

SIM_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def live_sim():
    proc = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=SIM_ROOT)
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:9191/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise AssertionError("sim kwam niet op binnen 20 s")
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=10)
```

- [ ] **Step 2: Write the failing test**

```python
# toolbox-sim/tests/test_adapters_live.py
"""nldt-adapters live tegen de toolbox-sim (env eerst, dan pas importeren)."""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

for line in (SIM_ENV := (Path(__file__).resolve().parents[1] / ".env.sim").read_text().splitlines()):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key] = value

sys.path.insert(0, str(REPO / "nldt"))

from services.adapters import data_platform, keycloak_auth, play_visualise  # noqa: E402
from services.marketplace_publish import publish_recipe  # noqa: E402
from services.process_adapter.router import UCSAdapter  # noqa: E402


def test_keycloak_live_token_with_scopes(live_sim):
    keycloak_auth.clear_token_cache()
    token = keycloak_auth.get_service_token()
    assert token
    scopes = data_platform.list_scopes()
    assert any(s["scope"].endswith("default") and s["plane"] == "context-data" for s in scopes)


def test_broker_live_entities(live_sim):
    zones = data_platform.list_entities(entity_type="ldt:OpportunityZone", limit=1000)
    assert zones and zones[0]["id"].startswith("urn:ldt:utrecht:zone:")
    one = data_platform.get_entity(zones[0]["id"])
    assert one["id"] == zones[0]["id"]


def test_trino_live_readonly(live_sim):
    result = data_platform.trino_query("SELECT * FROM timescaledb.public.runs")
    assert result["rowCount"] >= 4
    assert all(row[1] == "pass" for row in result["rows"])


def test_pv_live_registration(live_sim, tmp_path):
    fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [5.1, 52.1]}}]}
    reg = play_visualise.register_geojson_layer(geojson=fc, name="live-adapter-test", export_store=tmp_path)
    assert reg["dataSource"].get("mock") is None
    assert reg["dataLayer"].get("mock") is None
    assert reg["dataSource"]["id"].startswith("ds-")
    assert (tmp_path / f"{reg['exportId']}.geojson").exists()


def test_ucs_live_replay(live_sim):
    adapter = UCSAdapter()
    assert adapter.available
    outputs = adapter.execute("utrecht-opportunity-map", {})
    assert outputs["verdict"] == "pass"
    assert "sim-replay://canonical/" in json.dumps(outputs) or outputs.get("runId")


def test_marketplace_live_publish(live_sim):
    recipe = {"id": "live-adapter-test", "title": "Live adapter test", "description": "sim", "version": "1.0.0"}
    result = publish_recipe(recipe, categories=["urn:ngsi-ld:category:processes"])
    assert result["offeringId"].startswith("sim-offering-")
    assert result["mock"] is False
    assert result["marketplaceLink"]
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_adapters_live.py -q`
Expected: `6 passed`. (These cannot be written "failing first" meaningfully — the sim they exercise is already built; run once, fix any contract mismatch found by raising it back into the matching app task, then rerun.)

- [ ] **Step 4: Commit**

```bash
git add toolbox-sim/tests/test_adapters_live.py toolbox-sim/tests/conftest.py
git commit -m "test(toolbox-sim): nldt-adapters live tegen de sim (env-first import)"
```

---

### Task 15: End-to-end smoke — hybrid bridge over the sim

**Files:**
- Create: `toolbox-sim/tests/test_e2e_smoke.py`

**Interfaces:**
- Consumes: `live_sim` fixture; `services.hybrid_bridge.post_execution_hooks`; adapters from Task 14's env-first pattern.
- Produces: one test proving the full offline story: token → NGSI-LD query → hybrid bridge P&V registration → Marketplace publish, with `mock` flags absent/False everywhere.

- [ ] **Step 1: Write the test**

```python
# toolbox-sim/tests/test_e2e_smoke.py
"""E2E: sim op → brug over adapters → alles geregistreerd, niets gemockt."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

for line in (Path(__file__).resolve().parents[1] / ".env.sim").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ[key] = value

sys.path.insert(0, str(REPO / "nldt"))

from services.adapters import data_platform, keycloak_auth  # noqa: E402
from services.hybrid_bridge import post_execution_hooks  # noqa: E402
from services.marketplace_publish import publish_recipe  # noqa: E402

FC = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"note": "e2e"}, "geometry": {"type": "Point", "coordinates": [5.11, 52.09]}}]}


def test_full_offline_story(live_sim, tmp_path):
    keycloak_auth.clear_token_cache()
    assert keycloak_auth.get_service_token()

    zones = data_platform.list_entities(entity_type="ldt:OpportunityZone", limit=1000)
    assert zones, "canonieke zones moeten in de broker zitten"

    execution = {"recipeId": "toolbox-sim-e2e", "outputs": {"intersection": FC}}
    hooks = post_execution_hooks(execution, run_id="toolbox-sim-e2e")
    reg = hooks["visualization"]
    assert reg["dataSource"].get("mock") is None and reg["dataLayer"]["id"].startswith("dl-")

    result = publish_recipe(
        {"id": "toolbox-sim-e2e", "title": "Toolbox-sim e2e", "description": "smoke", "version": "1.0.0"},
        categories=["urn:ngsi-ld:category:processes"],
    )
    assert result["mock"] is False and result["offeringId"].startswith("sim-offering-")
```

- [ ] **Step 2: Run it**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_e2e_smoke.py -q`
Expected: `1 passed`

- [ ] **Step 3: Full suite + commit**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: all passed (EUBD PostGIS test skipped unless DSN set).

```bash
git add toolbox-sim/tests/test_e2e_smoke.py
git commit -m "test(toolbox-sim): e2e-smoke — token, broker, hybrid bridge, marketplace"
```

---

### Task 16: Docs wiring (fase 4) + final verification

**Files:**
- Modify: `nldt/10-toolbox-integration.md`, `toolbox-sim/README.md` (if links changed)

**Interfaces:**
- Consumes: everything built.
- Produces: documentation links only.

- [ ] **Step 1: Add a section to `nldt/10-toolbox-integration.md`** (after "Live configuration"):

```markdown
## Local simulation (toolbox-sim)

Voor de laptop-zonder-cluster: [`toolbox-sim/`](../toolbox-sim/) simuleert de
PoC-relevante oplossingen (IM, Data Platform/NGSI-LD, P&V, UCS, Marketplace,
EUBD-feed) over hun echte adaptercontracten. Start met
`toolbox-sim/run_sim.sh` en laad `toolbox-sim/.env.sim` — alle `*_MOCK`-vlaggen
gaan uit en de adapters praten live met de sim, die canonieke run-artefacten
replayt (`X-Sim-Provenance` op elk antwoord). Catalogusfilter met
skipped-redenen: `toolbox-sim/catalogue.json`.
```

- [ ] **Step 2: Verify nothing else broke**

Run: `cd nldt && .venv/bin/python -m pytest tests -q` (existing suite, mock defaults — must stay green)
Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests -q`
Expected: both green.

- [ ] **Step 3: Commit and merge**

```bash
git add nldt/10-toolbox-integration.md toolbox-sim/README.md
git commit -m "docs(toolbox-sim): verwijzing vanuit nldt/10 en README"
```

Merge `toolbox-sim` branch → `main` (worktree pattern), delete the branch.
