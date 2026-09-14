# Beleidskompas BK-2 (application record type) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute BK-2 from [`nldt/14-beleidskompas-integration.md`](../../../nldt/14-beleidskompas-integration.md): make beleidskompas the first *catalogued app* — a new `application` record type in the nLDT catalog, plus the twin-instance `apps` configuration that lets a front door discover and launch it.

**Architecture:** A JSON Schema (`schemas/application.schema.json`) defines the application descriptor (launchUrl, publisher, trustLevel, capabilities, consumed recipes). `catalog_adapter/seed.py` gains a module-level `APPLICATIONS` list whose entries are **validated against the schema at seed time** and served as OGC API Records of `type: "application"` — discoverable via `?type=application` and `?q=`. A twin-instance example config gains an `apps` array scoped to the recipes each app may consume.

**Tech Stack:** Python/FastAPI TestClient, jsonschema (Draft 2020-12) — both already in `nldt/requirements.txt`.

**Spec:** [`nldt/14-beleidskompas-integration.md`](../../../nldt/14-beleidskompas-integration.md) §8 BK-2, §10 decision 4 (after BK-1 MVP — consumption loop proven 2026-09-14).

## Global Constraints

- Repo root `/Users/marc/Projecten/ldttoolbox`; commands from `nldt/` with `PYTHONPATH=.`; venv `nldt/.venv`.
- **No new dependencies.** Auth stays off in tests (default); the gated live services are untouched (a live smoke check at the end uses the bearer token).
- Schema style follows [`schemas/recipe.schema.json`](../../../nldt/schemas/recipe.schema.json): `$schema` draft 2020-12, `$id` under `https://ldttoolbox.example/nldt/schemas/`, `additionalProperties: false`, `$defs` for repeated shapes.
- Seed-time validation: every entry in `APPLICATIONS` must validate against `application.schema.json` when `seed_records()` runs (fail loudly, not silently unvalidated).
- Existing behavior unchanged: current record sets, search semantics (`find_records` matches title OR properties), and all 144 tests stay green.
- Commit messages prefixed `BK-2:`; commit per task; never `git add -A` (working tree carries user WIP).

---

### Task 1: `application` record type — schema, seed registration, tests

**Files:**
- Create: `nldt/schemas/application.schema.json`
- Modify: `nldt/services/catalog_adapter/seed.py` (module-level `APPLICATIONS` + records loop)
- Test: `nldt/tests/test_bk2_application.py`

**Interfaces:**
- Produces: `schemas/application.schema.json` (descriptor schema); catalog record `application-beleidskompas` of `type: "application"`; module constant `APPLICATIONS` in `services.catalog_adapter.seed` (monkeypatchable for negative tests).

- [ ] **Step 1: Write the failing tests**

Create `nldt/tests/test_bk2_application.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.catalog_adapter.app import app as catalog_app
from services.common.schema import validate_instance


@pytest.fixture
def client():
    return TestClient(catalog_app)


def test_application_record_valid_against_schema(client):
    rec = client.get("/records/application-beleidskompas").json()
    assert rec["type"] == "application"
    validate_instance(rec["properties"], "application.schema.json")


def test_catalog_lists_application_type(client):
    resp = client.get("/records", params={"type": "application"})
    ids = [f["id"] for f in resp.json()["features"]]
    assert ids == ["application-beleidskompas"]


def test_application_discoverable_by_query(client):
    resp = client.get("/records", params={"q": "beleidskompas"})
    ids = [f["id"] for f in resp.json()["features"]]
    assert "application-beleidskompas" in ids
    assert "recipe-beleidskompas-omgevingsanalyse" in ids


def test_application_links(client):
    rec = client.get("/records/application-beleidskompas").json()
    rels = {l["rel"]: l["href"] for l in rec["links"]}
    assert rels["launch"].startswith("https://")
    assert rels["docs"].startswith("https://")


def test_application_consumes_real_recipes(client):
    rec = client.get("/records/application-beleidskompas").json()
    for rid in rec["properties"]["consumesRecipes"]:
        assert client.get(f"/records/recipe-{rid}").status_code == 200


def test_seed_rejects_invalid_application(monkeypatch):
    from jsonschema import ValidationError

    from services.catalog_adapter import seed

    aid, title, descriptor, tags = seed.APPLICATIONS[0]
    bad = (aid, title, {**descriptor, "trustLevel": "banana"}, tags)
    monkeypatch.setattr(seed, "APPLICATIONS", [bad])
    with pytest.raises(ValidationError):
        seed.seed_records()
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_bk2_application.py -q
```

Expected: FAIL — `404` on `/records/application-beleidskompas` (and `AttributeError: APPLICATIONS` in the negative test).

- [ ] **Step 3: Create the schema**

Create `nldt/schemas/application.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ldttoolbox.example/nldt/schemas/application.schema.json",
  "title": "Application (App Store record descriptor)",
  "description": "Descriptor for a catalogued nLDT application (OGC API Records type 'application'): an external or platform app a twin front door can discover and launch, scoped to the capabilities and recipes it may consume. Lives in the record's 'properties'.",
  "type": "object",
  "additionalProperties": false,
  "required": ["appId", "launchUrl", "publisher", "trustLevel"],
  "properties": {
    "appId": {
      "type": "string",
      "pattern": "^[a-z0-9][a-z0-9-]*$",
      "description": "Stable application identifier, e.g. beleidskompas"
    },
    "launchUrl": {
      "type": "string",
      "format": "uri",
      "description": "Where the front door launches the app (platform or product URL)"
    },
    "publisher": { "type": "string", "minLength": 2 },
    "docsUrl": {
      "type": "string",
      "format": "uri",
      "description": "Human-readable documentation of the app"
    },
    "trustLevel": {
      "type": "string",
      "enum": ["experimental", "verified"],
      "description": "Governance mark; 'verified' requires the App Store quality process (future)"
    },
    "requiredCapabilities": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "uniqueItems": true,
      "description": "nLDT seams the app consumes, e.g. mcp, ogc-processes, a2a, web3d-context"
    },
    "consumesRecipes": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$" },
      "uniqueItems": true,
      "description": "Recipe ids the app is scoped to; the twin instance trusts this as the allow-list"
    },
    "tags": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "uniqueItems": true
    }
  },
  "$defs": {}
}
```

- [ ] **Step 4: Register the application in the seed**

In `nldt/services/catalog_adapter/seed.py`:

Add after the existing imports:

```python
from services.common.schema import validate_instance

# Catalogued applications (App Store records, type "application"). Every
# entry's descriptor is validated against application.schema.json at seed
# time — an invalid app fails loudly, it is never served unvalidated.
APPLICATIONS: list[tuple[str, str, dict[str, Any], list[str]]] = [
    (
        "beleidskompas",
        "Beleidskompas (GovChat-NL)",
        {
            "appId": "beleidskompas",
            "launchUrl": "https://www.govchat-nl.nl",
            "publisher": "GovChat-NL / Provincie Limburg",
            "trustLevel": "experimental",
            "docsUrl": "https://github.com/jeannotdamoiseaux/GovChat-NL/blob/main/docs/app-launcher/beleidskompas/beleidskompas.md",
            "requiredCapabilities": ["mcp", "ogc-processes"],
            "consumesRecipes": ["beleidskompas-omgevingsanalyse", "breda-scan-qa"],
        },
        ["beleidskompas", "govchat-nl", "policy", "app-launcher"],
    ),
]
```

Inside `seed_records()`, after the recipes loop (before the lake-datasets block), add:

```python
    for aid, title, descriptor, tags in APPLICATIONS:
        validate_instance({**descriptor, "tags": tags}, "application.schema.json")
        records.append(
            {
                "id": f"application-{aid}",
                "type": "application",
                "title": title,
                "properties": {**descriptor, "tags": tags},
                "links": [
                    {"rel": "self", "href": f"{CATALOG_BASE}/records/application-{aid}"},
                    {"rel": "launch", "href": descriptor["launchUrl"], "type": "text/html"},
                    {"rel": "docs", "href": descriptor["docsUrl"], "type": "text/html"},
                ],
            }
        )
```

(`json` import already exists at module top if used elsewhere; no other changes.)

- [ ] **Step 5: Run to verify pass, then full suite**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/test_bk2_application.py -q
PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: `6 passed`, then full suite green (144 + 6 = 150).

- [ ] **Step 6: Live smoke against the running (gated) catalog**

```bash
curl -s -H 'Authorization: Bearer beleidskompas-svc-tok' 'http://localhost:8083/records?type=application' | python3 -m json.tool | head -20
```

Note: the running :8083 process has the old code — this smoke is expected to return the new record only after a service restart in Task 2's wrap-up. Record the pre-restart result honestly; do NOT restart services in this task.

- [ ] **Step 7: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/schemas/application.schema.json nldt/services/catalog_adapter/seed.py nldt/tests/test_bk2_application.py
git commit -m "BK-2: application record type + beleidskompas registration (schema-validated at seed)"
```

---

### Task 2: Twin-instance `apps` configuration + docs + wrap-up

**Files:**
- Create: `nldt/examples/twin-instance.example.json`
- Modify: `nldt/03-building-blocks.md` (twin instance JSON block + one sentence)
- Modify: `nldt/14-beleidskompas-integration.md` (BK-2 status line)

**Interfaces:**
- Consumes: record `application-beleidskompas` from Task 1.
- Produces: twin-instance example with `apps` array (`recordId`, `appId`, `allowedRecipes`).

- [ ] **Step 1: Create the twin-instance example**

Create `nldt/examples/twin-instance.example.json`:

```json
{
  "twinId": "ref-generic-001",
  "catalogEndpoint": "http://localhost:8083",
  "processEndpoint": "http://localhost:8082",
  "cookbookEndpoint": "http://localhost:8081",
  "apps": [
    {
      "recordId": "application-beleidskompas",
      "appId": "beleidskompas",
      "allowedRecipes": ["beleidskompas-omgevingsanalyse", "breda-scan-qa"]
    }
  ],
  "recipes": [
    "spatial-overlay-analysis",
    "beleidskompas-omgevingsanalyse",
    "breda-scan-qa"
  ],
  "trustPolicy": { "defaultRiskLevel": "low", "hitlOnFail": true }
}
```

- [ ] **Step 2: Update the building-blocks doc**

In `nldt/03-building-blocks.md`, in the twin-instance JSON block (§ "Building-block composition: Digital Twin instance"), add the `apps` array between `cookbookEndpoint` and `recipes` (same content as the example file), and after the JSON block add one sentence:

```markdown
`apps` lists catalogued applications (catalog record type `application`) the
twin's front door may launch, each scoped to the recipes it may consume —
first example: beleidskompas
([14-beleidskompas-integration.md](14-beleidskompas-integration.md) §8 BK-2).
```

- [ ] **Step 3: Mark BK-2 done in the integration plan**

In `nldt/14-beleidskompas-integration.md`, under the `### BK-2` heading (before its bullet list), add:

```markdown
**Status:** done (2026-09-14) — `application` record type + beleidskompas
registered and schema-validated at seed; twin-instance `apps` config in
[examples/twin-instance.example.json](examples/twin-instance.example.json).
Marketplace publication deferred (optional per plan).
```

- [ ] **Step 4: Full suite + live restart-and-smoke**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expected: 150 passed. Then restart the catalog adapter only (the other services keep running):

```bash
kill $(lsof -ti :8083) 2>/dev/null; sleep 1
nohup env NLDT_AUTH_MODE=static NLDT_STATIC_TOKENS=beleidskompas-svc-tok \
  PYTHONPATH=. .venv/bin/python -m services.catalog_adapter.app > /tmp/nldt-catalog.log 2>&1 &
sleep 3
curl -s -H 'Authorization: Bearer beleidskompas-svc-tok' 'http://localhost:8083/records?type=application' | python3 -c 'import json,sys; print([f["id"] for f in json.load(sys.stdin)["features"]])'
```

Expected: `['application-beleidskompas']`. Also verify auth still gates: anonymous `curl -s -o /dev/null -w "%{http_code}" http://localhost:8083/records` → `401`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/examples/twin-instance.example.json nldt/03-building-blocks.md nldt/14-beleidskompas-integration.md
git commit -m "BK-2: twin-instance apps config + docs; BK-2 done"
```

---

## Definition of done (maps to spec §8 BK-2)

- `GET :8083/records?type=application` returns beleidskompas (live, authenticated) ✓ Task 2 Step 4
- Twin instance lists it (`apps` in example config + building-blocks doc) ✓ Task 2
- Descriptor schema-validated at seed time, with a negative test proving invalid apps fail loudly ✓ Task 1
- Discover → launch → consume loop demonstrable: `?q=beleidskompas` finds app + recipes; app record links to launch/docs; `consumesRecipes` resolve to real records ✓ Task 1
- Full suite green (150) with auth off; marketplace publication explicitly deferred ✓
