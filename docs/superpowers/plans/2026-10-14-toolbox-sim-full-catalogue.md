# toolbox-sim volledige catalogus — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Alle 20 EU LDT Toolbox catalogus-oplossingen lokaal draaibaar of gesimuleerd (geen k8s nodig), volgens spec `docs/superpowers/specs/2026-10-14-toolbox-sim-full-catalogue-design.md`.

**Architecture:** Eén FastAPI-simulatieproces (`toolbox-sim`) groeit van 6 naar 14 apps op poorten 9191–9204; bestaande diensten krijgen ontbrekende capabilities (NGSI-LD subscriptions/temporal/registrations, kaartviewer, experiment-authoring, EDC-flow); nldt-adapters gaan alles echt aanroepen met tests. Pure logica staat in functies naast de routers.

**Tech Stack:** FastAPI + uvicorn + httpx + pydantic (toolbox-sim), stdlib + shapely/pyproj/duckdb via `nldt/.venv`, pytest + TestClient.

## Global Constraints

- Python: `../nldt/.venv/bin/python` voor build_fixtures, tests en de sim (shapely/pyproj/duckdb beschikbaar).
- Elke response draagt `X-Sim-Provenance` (via `app.guards.add_provenance(app, "<solution>")`).
- Auth: `Depends(require_bearer)` op alle endpoints behalve `/health` en `/ui/map`; token `sim-toolbox-token` (STATIC_TOKEN) of sim-JWT.
- Geen verzonnen waarden: echte grondslag (lake-silver, eubd-fixture) of expliciet `syntheticSeed`; grondslag ontbreekt → HTTP 503 met top-level `{"error": "missing-ground", "description": <wat>}`.
- Fouten: top-level `{"error": ..., "description": ...}`-vorm (geen FastAPI `{"detail": ...}`-wrapping) — precedent in `ucs.py`/`data_platform.py`.
- Determinisme: twee identieke requests → byte-gelijke payloads; sim-klok = vaste basis `2026-01-01T00:00:00Z` + teller; geen `datetime.now()` in outputs.
- Bestaand gedrag ongewijzigd: zonder `--full` starten alleen 9191–9196; alle bestaande tests blijven groen.
- Broker-paden volgen het bestaande sim-contract `/ngsi-ld/v1/...` (spec zei `/cb/ngsi-ld/v1/...` — bewuste correctie op het bestaande contract).
- Recipe-fixtures: één bestand `fixtures/recipes.json` (combined dict) in plaats van een directory (zelfde inhoud, simpeler te laden).

## Bestandskaart

| Bestand | Actie | Verantwoordelijkheid |
|---|---|---|
| `toolbox-sim/build_fixtures.py` | Modify | + `dp-temporal.jsonld`, `recipes.json`, `participate-seed.json`, manifest-`extras` |
| `toolbox-sim/app/data_platform.py` | Modify | + subscriptions/registrations/temporal op de broker-app |
| `toolbox-sim/app/play_visualise.py` | Modify | + `GET /ui/map` (Leaflet HTML) |
| `toolbox-sim/app/algorithms.py` | Create | 7 model-stubs: pure `run_model` + `Ground` + `create_app` (:9198) |
| `toolbox-sim/app/ucs.py` | Modify | + experiment-authoring + model-executie |
| `toolbox-sim/app/dataspace_ready.py` | Create | EDC-stub (Management v3 + flow v2) (:9197) |
| `toolbox-sim/app/participate.py` | Create | Decidim- + Jitsi-stub (:9199) |
| `toolbox-sim/app/federated_learning.py` | Create | FL-rounds (:9200) |
| `toolbox-sim/app/ai_notebook.py` | Create | notebooks + pipeline-runs (:9201) |
| `toolbox-sim/app/data_modeller.py` | Create | model-registry + validatie (:9202) |
| `toolbox-sim/app/integrated_environment.py` | Create | portal/catalogus/metrics (:9203) |
| `toolbox-sim/app/cip.py` | Create | scenarios + contributions (:9204) |
| `toolbox-sim/app/server.py` | Modify | + 8 poorten, `--full`, `build_apps()`-extractie |
| `toolbox-sim/run_sim.sh` | Modify | + `--full`-passthrough |
| `toolbox-sim/tests/test_full_catalogue.py` | Create | contracttests nieuwe apps + determinisme |
| `toolbox-sim/tests/test_adapters_live.py` | Modify | + live adaptertests (subscriptions/temporal, EDC-flow, model-run, map_url) |
| `toolbox-sim/tests/test_server_boot.py` | Modify | + boot met `--full` |
| `toolbox-sim/catalogue.json` | Modify | 20/20 statussen + bewijs |
| `toolbox-sim/README.md` | Modify | poorttabel + `--full` |
| `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md` | Modify | addendum: non-goals vervallen |
| `nldt/services/adapters/data_platform.py` | Modify | + subscription/temporal/registration-methoden |
| `nldt/services/adapters/play_visualise.py` | Modify | + `map_url()` |
| `nldt/services/adapters/dataspace_connector.py` | Modify | + `negotiate_and_transfer()` |
| `nldt/services/process_adapter/handlers.py` | Modify | + 7 model-process handlers |
| `nldt/tests/test_full_catalogue_adapters.py` | Create | adaptertests tegen draaiende sim |

---

### Taak 1: build_fixtures — dp-temporal, recipes, participate-seed

**Files:**
- Modify: `toolbox-sim/build_fixtures.py`
- Create: `toolbox-sim/tests/test_fixtures_full_catalogue.py`
- Generates: `toolbox-sim/fixtures/dp-temporal.jsonld`, `toolbox-sim/fixtures/recipes.json`, `toolbox-sim/fixtures/participate-seed.json`

**Interfaces:**
- Produces: `build_dp_temporal() -> dict`, `copy_recipes() -> dict[str, dict]`, `build_participate_seed() -> dict` (taak 2/7/11 consumeren de bestanden; server laadt ze in taak 14).

- [ ] **Step 1: Schrijf de falende test**

Voeg toe aan nieuw bestand `toolbox-sim/tests/test_fixtures_full_catalogue.py`:

```python
# toolbox-sim/tests/test_fixtures_full_catalogue.py
"""Nieuwe catalogus-fixtures: deterministisch en herleidbaar."""
import hashlib
import json
import sys
from pathlib import Path

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from build_fixtures import build_dp_temporal, build_participate_seed, copy_recipes

FIXTURES = SIM_ROOT / "fixtures"


def test_dp_temporal_knmi_instances_herleidbaar():
    entities = build_dp_temporal()
    knmi = entities["urn:ngsi-ld:WeatherObserved:knmi-260"]
    assert knmi["attribute"] == "rainfall"
    assert knmi["instances"][0]["value"] == 1.2  # eerste observatie uit observations.jsonl
    assert knmi["instances"] == sorted(knmi["instances"], key=lambda i: i["observedAt"])
    assert knmi["provenance"].startswith("lake://nldt-poc-lake/silver/timeseries/")


def test_dp_temporal_peilen_instances():
    entities = build_dp_temporal()
    peilen = entities["urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"]
    assert peilen["instances"], "peilen_fixture leeg"
    first = peilen["instances"][0]
    assert first["unit"] == "mNAP"
    assert "T" in first["observedAt"] and first["observedAt"].endswith("Z")


def test_recipes_combined_dict():
    recipes = copy_recipes()
    assert "beleidskompas-omgevingsanalyse" in recipes
    assert all(isinstance(v, dict) for v in recipes.values())


def test_participate_seed_herleidbaar():
    seed = build_participate_seed()
    assert len(seed["proposals"]) == 3
    assert all(p["provenance"].startswith("canonical replay:") for p in seed["proposals"])


def test_fixturebestanden_deterministisch(tmp_path):
    # twee generatierondes geven byte-gelijke bestanden
    import subprocess
    for _ in range(2):
        subprocess.run(
            [sys.executable, str(SIM_ROOT / "build_fixtures.py"), "--catalogue-extras"],
            cwd=SIM_ROOT, check=True, capture_output=True,
        )
    shas = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (FIXTURES / "dp-temporal.jsonld", FIXTURES / "recipes.json", FIXTURES / "participate-seed.json")
    }
    subprocess.run(
        [sys.executable, str(SIM_ROOT / "build_fixtures.py"), "--catalogue-extras"],
        cwd=SIM_ROOT, check=True, capture_output=True,
    )
    for name, sha in shas.items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == sha, name
```

- [ ] **Step 2: Verifieer dat de test faalt**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_full_catalogue.py -v`
Expected: FAIL (`ImportError: cannot import name 'build_dp_temporal'`)

- [ ] **Step 3: Implementeer de drie bouwers + CLI-vlag**

In `toolbox-sim/build_fixtures.py`, voeg toe na `build_eubd_batch` (en `LAKE` bovenaan na `FIXTURES`):

```python
LAKE = REPO / "nldt" / "data" / "lake" / "nldt-poc-lake"


def build_dp_temporal() -> dict:
    """NGSI-LD temporele entiteiten uit echte lake-silver-reeksen (KNMI + peilen)."""
    import duckdb

    entities: dict[str, Any] = {}

    knmi_dir = LAKE / "silver" / "timeseries" / "knmi-daily-neerslag-260"
    instances = []
    for line in (knmi_dir / "year=2024" / "observations.jsonl").read_text().splitlines():
        obs = json.loads(line)
        instances.append({"observedAt": obs["observedAt"], "value": obs["value"], "unitCode": obs["unit"]})
    entities["urn:ngsi-ld:WeatherObserved:knmi-260"] = {
        "id": "urn:ngsi-ld:WeatherObserved:knmi-260",
        "type": "WeatherObserved",
        "attribute": "rainfall",
        "provenance": "lake://nldt-poc-lake/silver/timeseries/knmi-daily-neerslag-260 (KNMI daggegevens, CC BY 4.0)",
        "instances": sorted(instances, key=lambda i: i["observedAt"]),
    }

    peilen_path = LAKE / "silver" / "rijnland" / "peilen_latest" / "peilen_latest.parquet"
    rows = duckdb.connect().execute(
        f"SELECT peilgebied_id, waterstand_m, measured_at FROM read_parquet('{peilen_path.as_posix()}') ORDER BY peilgebied_id"
    ).fetchall()
    entities["urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"] = {
        "id": "urn:ngsi-ld:WaterObserved:rijnland-peilen-latest",
        "type": "WaterObserved",
        "attribute": "waterLevel",
        "provenance": "lake://nldt-poc-lake/silver/rijnland/peilen_latest/peilen_latest.parquet",
        "instances": [
            {"observedAt": measured_at.isoformat().replace("+00:00", "") + "Z",
             "value": waterstand, "unitCode": "mNAP", "datasetId": peilgebied_id}
            for peilgebied_id, waterstand, measured_at in rows
        ],
    }
    return entities


def copy_recipes() -> dict[str, dict]:
    """Alle nldt-recipes als gecombineerde dict (fixtures/recipes.json)."""
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted((REPO / "nldt" / "recipes").glob("*.json"))
    }


def build_participate_seed() -> dict:
    """Participate-seed: voorstellen/meetings herleidbaar naar canonieke runs."""
    return {
        "proposals": [
            {"id": "prop-1", "title": "Zonneweide Noorderpark: 15 ha", "area": "utrecht",
             "state": "open", "provenance": "canonical replay: poc/runs/20260830T142439Z-zon"},
            {"id": "prop-2", "title": "Boscompensatie Leersum: 40 ha", "area": "utrecht",
             "state": "open", "provenance": "canonical replay: poc/runs/20260830T142446Z-bos"},
            {"id": "prop-3", "title": "BP2OP-omzettingsvoorstel: 232 voorgestelde regels",
             "area": "eindhoven", "state": "closed",
             "provenance": "canonical replay: poc-bp2op/runs/20260830-124515-eindhoven"},
        ],
        "meetings": [
            {"id": "meet-1", "title": "Gebiedssessie Utrecht energy-vs-nature", "area": "utrecht"},
        ],
    }
```

In `main()` van hetzelfde bestand: voeg een CLI-vlag toe en schrijf de extras vóór het manifest-schrijven (de extras gaan níet in `manifest["batches"]` — de broker-loader laadt alleen batches als entiteiten):

```python
    parser.add_argument("--catalogue-extras", action="store_true",
                        help="schrijf ook dp-temporal/recipes/participate-seed (catalogus-sim)")
```

en vóór `manifest_path.write_text(...)`:

```python
    if args.catalogue_extras:
        extras = {}
        (FIXTURES / "dp-temporal.jsonld").write_text(json.dumps(build_dp_temporal(), indent=1))
        extras["dp-temporal"] = _sha(FIXTURES / "dp-temporal.jsonld")
        (FIXTURES / "recipes.json").write_text(json.dumps(copy_recipes(), indent=1))
        extras["recipes"] = _sha(FIXTURES / "recipes.json")
        (FIXTURES / "participate-seed.json").write_text(json.dumps(build_participate_seed(), indent=1))
        extras["participate-seed"] = _sha(FIXTURES / "participate-seed.json")
        manifest["extras"] = extras
```

- [ ] **Step 4: Verifieer dat de test slaagt en bestaande fixture-tests groen blijven**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_fixtures_full_catalogue.py tests/test_fixtures_utrecht.py tests/test_fixtures_eindhoven.py -v`
Expected: PASS (alle)

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/build_fixtures.py toolbox-sim/tests/test_fixtures_full_catalogue.py toolbox-sim/fixtures/dp-temporal.jsonld toolbox-sim/fixtures/recipes.json toolbox-sim/fixtures/participate-seed.json
git commit -m "feat(toolbox-sim): fixtures dp-temporal (KNMI+peilen), recipes, participate-seed"
```

---

### Taak 2: broker — subscriptions, registrations, temporal

**Files:**
- Modify: `toolbox-sim/app/data_platform.py` (na de bestaande entity-endpoints, vóór `if include_proxy:`)
- Modify: `toolbox-sim/app/server.py` (alleen de broker-constructie: `temporal=` doorgeven)
- Test: `toolbox-sim/tests/test_broker.py` (aanvullen)

**Interfaces:**
- Consumes: `fixtures/dp-temporal.jsonld` (taak 1).
- Produces: `create_broker_app(..., temporal: dict | None = None)`; endpoints `POST/GET/DELETE /ngsi-ld/v1/subscriptions/`, `POST /ngsi-ld/v1/subscriptions/{id}/notify`, `GET /ngsi-ld/v1/subscriptions/{id}/notifications`, `GET /ngsi-ld/v1/temporal/entities/{id}`, `POST/GET/DELETE /ngsi-ld/v1/registrations/`. Taak 3 (adapter) en 14 (server) bouwen hierop.

- [ ] **Step 1: Schrijf de falende tests**

Aanvullen in `toolbox-sim/tests/test_broker.py` (patroon: bestaande file; gebruik dezelfde client-fixture; token via header):

```python
SUB = {
    "type": "Subscription",
    "entities": [{"type": "ldt:OpportunityZone"}],
    "notification": {"endpoint": {"uri": "http://localhost:1/none"}},
}
AUTH = {"Authorization": "Bearer sim-toolbox-token"}


def test_subscription_lifecycle(broker_client):
    r = broker_client.post("/ngsi-ld/v1/subscriptions/", json=SUB, headers=AUTH)
    assert r.status_code == 201
    sid = r.headers["Location"].rsplit("/", 1)[-1]
    assert r.text == ""  # 201 zonder body, alleen Location-header
    listing = broker_client.get("/ngsi-ld/v1/subscriptions/", headers=AUTH)
    assert any(s["id"] == sid for s in listing.json())
    assert listing.json()[0]["status"] == "active"
    assert broker_client.delete(f"/ngsi-ld/v1/subscriptions/{sid}", headers=AUTH).status_code == 204
    assert broker_client.get(f"/ngsi-ld/v1/subscriptions/{sid}", headers=AUTH).status_code == 404


def test_subscription_validatie():
    r = broker_client.post("/ngsi-ld/v1/subscriptions/", json={"type": "Subscription"}, headers=AUTH)
    assert r.status_code == 400 and r.json()["error"] == "BadRequest"


def test_notify_outbox_deterministisch(broker_client):
    sid = broker_client.post("/ngsi-ld/v1/subscriptions/", json=SUB, headers=AUTH).headers["Location"].rsplit("/", 1)[-1]
    a = broker_client.post(f"/ngsi-ld/v1/subscriptions/{sid}/notify", headers=AUTH).json()
    b = broker_client.post(f"/ngsi-ld/v1/subscriptions/{sid}/notify", headers=AUTH).json()
    assert a["subscriptionId"] == sid and a["data"], "notificatie moet gematchte entiteiten bevatten"
    assert a["notifiedAt"] != b["notifiedAt"]  # sim-klok telt
    assert a["data"] == b["data"]  # zelfde entiteiten, deterministisch
    outbox = broker_client.get(f"/ngsi-ld/v1/subscriptions/{sid}/notifications", headers=AUTH).json()
    assert len(outbox["data"]) == 2


def test_registrations_crud(broker_client):
    reg = {"type": "ContextSourceRegistration", "information": [{"entities": [{"type": "WeatherObserved"}]}],
           "endpoint": "http://localhost:9199/ngsi-ld/v1"}
    r = broker_client.post("/ngsi-ld/v1/registrations/", json=reg, headers=AUTH)
    assert r.status_code == 201
    rid = r.headers["Location"].rsplit("/", 1)[-1]
    assert any(x["id"] == rid for x in broker_client.get("/ngsi-ld/v1/registrations/", headers=AUTH).json())
    assert broker_client.delete(f"/ngsi-ld/v1/registrations/{rid}", headers=AUTH).status_code == 204


def test_temporal_between(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:WeatherObserved:knmi-260",
        params={"timerel": "between", "time": "2024-01-05T00:00:00Z", "endTime": "2024-02-01T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "urn:ngsi-ld:WeatherObserved:knmi-260"
    instances = body["rainfall"][0]["instances"]
    assert instances and all("2024-01-05" <= i["observedAt"] <= "2024-02-01" for i in instances)


def test_temporal_zonder_endtime_tussen_gaat_fout(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:WeatherObserved:knmi-260",
        params={"timerel": "between", "time": "2024-01-05T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 400 and r.json()["error"] == "BadRequest"


def test_temporal_onbekende_entity(broker_client):
    r = broker_client.get(
        "/ngsi-ld/v1/temporal/entities/urn:ngsi-ld:Onbekend:1",
        params={"timerel": "after", "time": "2024-01-01T00:00:00Z"},
        headers=AUTH,
    )
    assert r.status_code == 404 and r.json()["error"] == "NotFound"
```

Als de bestaande `test_broker.py` geen `broker_client`-fixture heeft, maak die dan bovenin zo (app mét temporal-fixture en proxy):

```python
import json
from pathlib import Path
from fastapi.testclient import TestClient

import sys
from pathlib import Path as _P
SIM_ROOT = _P(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from app.data_platform import create_broker_app

FIXTURES = SIM_ROOT / "fixtures"
_entities = {}
for name in json.loads((FIXTURES / "manifest.json").read_text())["batches"]:
    _entities.setdefault("ldt", []).extend(json.loads((FIXTURES / "ngsi-ld" / f"{name}.jsonld").read_text()))
_temporal = json.loads((FIXTURES / "dp-temporal.jsonld").read_text())
broker_client = TestClient(create_broker_app(
    entities_by_tenant={"ldt": _entities["ldt"]},
    provenance_by_tenant={"ldt": "toolbox-sim/data-platform; fixtures=test"},
    include_proxy=True,
    temporal=_temporal,
))
```

- [ ] **Step 2: Verifieer dat de tests falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_broker.py -v`
Expected: FAIL (`TypeError: create_broker_app() got an unexpected keyword argument 'temporal'` of 404)

- [ ] **Step 3: Implementeer de endpoints**

In `toolbox-sim/app/data_platform.py` — signature uitbreiden en registries na `store`:

```python
def create_broker_app(
    *,
    entities_by_tenant: dict[str, list[dict]],
    provenance_by_tenant: dict[str, str],
    include_proxy: bool = False,
    include_trino: bool = False,
    temporal: dict | None = None,
) -> FastAPI:
```

```python
    subscriptions: dict[str, dict] = {}
    subscription_notifications: dict[str, list[dict]] = {}
    registrations: dict[str, dict] = {}
    id_seq = {"n": 0}
    clock_seq = {"n": 0}

    def _sim_clock() -> str:
        # sim-klok: vaste basis + teller → deterministisch, monotón, ISO-8601 Z
        clock_seq["n"] += 1
        total = clock_seq["n"]
        hh, rest = divmod(total, 3600)
        mm, ss = divmod(rest, 60)
        return f"2026-01-01T{hh:02d}:{mm:02d}:{ss:02d}Z"

    def _next_urn(prefix: str) -> str:
        id_seq["n"] += 1
        return f"urn:ngsi-ld:{prefix}:sim-{id_seq['n']}"
```

Endpoints (invoegen ná `upsert`, vóór `if include_proxy:`):

```python
    @app.post("/ngsi-ld/v1/subscriptions/", status_code=201)
    def create_subscription(subscription: dict, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        if subscription.get("type") != "Subscription" or "entities" not in subscription or "notification" not in subscription:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "Subscription vereist type, entities en notification"})
        sid = _next_urn("Subscription")
        subscriptions[sid] = {**subscription, "id": sid, "status": "active"}
        return Response(status_code=201, headers={"Location": f"/ngsi-ld/v1/subscriptions/{sid}"})

    @app.get("/ngsi-ld/v1/subscriptions/")
    def list_subscriptions(_: dict = Depends(require_bearer)):
        return [dict(s) for s in subscriptions.values()]

    @app.get("/ngsi-ld/v1/subscriptions/{sid}")
    def get_subscription(sid: str, _: dict = Depends(require_bearer)):
        sub = subscriptions.get(sid)
        if sub is None:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": sid})
        return sub

    @app.delete("/ngsi-ld/v1/subscriptions/{sid}", status_code=204)
    def delete_subscription(sid: str, _: dict = Depends(require_bearer)):
        subscriptions.pop(sid, None)
        subscription_notifications.pop(sid, None)
        return Response(status_code=204)

    @app.post("/ngsi-ld/v1/subscriptions/{sid}/notify")
    def trigger_notify(sid: str, x_tenant: str = Header(default="ldt", alias="NGSILD-Tenant"), _: dict = Depends(require_bearer)):
        sub = subscriptions.get(sid)
        if sub is None:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": sid})
        watched = [(e.get("id"), e.get("type")) for e in sub.get("entities", [])]
        tenant = _tenant(x_tenant)
        matched = [
            e for e in tenant.values()
            if any((wid and e.get("id") == wid) or (wtype and e.get("type") == wtype) for wid, wtype in watched)
        ]
        payload = {
            "subscriptionId": sid,
            "notifiedAt": _sim_clock(),
            "data": matched,
        }
        subscription_notifications.setdefault(sid, []).append(payload)
        return payload

    @app.get("/ngsi-ld/v1/subscriptions/{sid}/notifications")
    def list_subscription_notifications(sid: str, _: dict = Depends(require_bearer)):
        if sid not in subscriptions:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": sid})
        return {"data": subscription_notifications.get(sid, [])}

    @app.post("/ngsi-ld/v1/registrations/", status_code=201)
    def create_registration(registration: dict, _: dict = Depends(require_bearer)):
        if registration.get("type") != "ContextSourceRegistration" or "endpoint" not in registration:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "ContextSourceRegistration vereist type en endpoint"})
        rid = _next_urn("ContextSourceRegistration")
        registrations[rid] = {**registration, "id": rid, "status": "active"}
        return Response(status_code=201, headers={"Location": f"/ngsi-ld/v1/registrations/{rid}"})

    @app.get("/ngsi-ld/v1/registrations/")
    def list_registrations(_: dict = Depends(require_bearer)):
        return [dict(r) for r in registrations.values()]

    @app.delete("/ngsi-ld/v1/registrations/{rid}", status_code=204)
    def delete_registration(rid: str, _: dict = Depends(require_bearer)):
        registrations.pop(rid, None)
        return Response(status_code=204)

    @app.get("/ngsi-ld/v1/temporal/entities/{entity_id}")
    def temporal_entity(
        entity_id: str,
        timerel: str = Query(...),
        time: str = Query(...),
        endTime: str | None = Query(default=None),
        time_property: str = Query(default="observedAt", alias="time_property"),
        _: dict = Depends(require_bearer),
    ):
        entity = (temporal or {}).get(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail={"error": "NotFound", "description": entity_id})
        if timerel not in ("before", "after", "between"):
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "timerel is before|after|between"})
        if timerel == "between" and not endTime:
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "timerel=between vereist endTime"})

        def _keep(instance: dict) -> bool:
            stamp = str(instance.get(time_property, ""))
            if timerel == "before":
                return stamp <= time
            if timerel == "after":
                return stamp >= time
            return time <= stamp <= (endTime or "")

        instances = [i for i in entity.get("instances", []) if _keep(i)]
        body = {k: v for k, v in entity.items() if k not in ("instances", "attribute")}
        body[entity["attribute"]] = [{"type": "Property", "instances": instances}]
        return body
```

In `toolbox-sim/app/server.py` — broker-constructie uitbreiden (laad de temporal-fixture naast de batches):

```python
    temporal_path = FIXTURES / "dp-temporal.jsonld"
    temporal = json.loads(temporal_path.read_text()) if temporal_path.exists() else None
```

en bij `create_broker_app(...)` in het `apps`-dict:

```python
        "broker": create_broker_app(
            entities_by_tenant=entities_by_tenant,
            provenance_by_tenant=provenance,
            include_proxy=True,
            include_trino=True,
            temporal=temporal,
        ),
```

- [ ] **Step 4: Verifieer dat alles slaagt**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_broker.py tests/test_server_boot.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/data_platform.py toolbox-sim/app/server.py toolbox-sim/tests/test_broker.py
git commit -m "feat(toolbox-sim): broker subscriptions/registrations/temporal (NGSI-LD-contract, sim-klok deterministisch)"
```

---

### Taak 3: nldt data_platform-adapter — subscription/temporal/registratie-methoden

**Files:**
- Modify: `nldt/services/adapters/data_platform.py` (na `_list_via_broker`)
- Modify: `toolbox-sim/tests/test_adapters_live.py` (aanvullen)

**Interfaces:**
- Consumes: taak 2 endpoints; env `NLDT_NGSI_LD_URL` (bestaand).
- Produces: `create_subscription(subscription: dict) -> str` (returns id), `trigger_notify(subscription_id: str) -> dict`, `get_temporal_entity(entity_id: str, *, timerel: str, time: str, end_time: str | None = None) -> dict`, `create_registration(registration: dict) -> str`. Taak 15 (live tests) gebruikt exact deze namen.

- [ ] **Step 1: Schrijf de falende live test**

Aanvullen in `toolbox-sim/tests/test_adapters_live.py`:

```python
SUB = {
    "type": "Subscription",
    "entities": [{"type": "ldt:OpportunityZone"}],
    "notification": {"endpoint": {"uri": "http://localhost:1/none"}},
}


def test_broker_live_subscription_outbox(live_sim):
    sid = data_platform.create_subscription(SUB)
    assert sid.startswith("urn:ngsi-ld:Subscription:sim-")
    payload = data_platform.trigger_notify(sid)
    assert payload["subscriptionId"] == sid and payload["data"]


def test_broker_live_temporal(live_sim):
    body = data_platform.get_temporal_entity(
        "urn:ngsi-ld:WeatherObserved:knmi-260",
        timerel="after", time="2024-01-20T00:00:00Z",
    )
    assert body["rainfall"][0]["instances"]
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_adapters_live.py -k subscription -v`
Expected: FAIL (`AttributeError: module ... has no attribute 'create_subscription'`)

- [ ] **Step 3: Implementeer de methoden**

In `nldt/services/adapters/data_platform.py` — voeg toe na `_list_via_broker` (hergebruik het headers-bouwsel uit die functie; als daar geen helper is, extraher je:

```python
def _broker_headers() -> dict[str, str]:
    from services.adapters import keycloak_auth

    return {
        "Authorization": f"Bearer {keycloak_auth.get_service_token()}",
        "NGSILD-Tenant": NGSI_TENANT,
    }
```

en vervang in `_list_via_broker` het inline headers-bouwsel door `headers=_broker_headers()` — gedrag identiek):

```python
def create_subscription(subscription: dict[str, Any]) -> str:
    """NGSI-LD subscription aanmaken; geeft de subscription-id terug."""
    if MOCK or not NGSI_LD_URL:
        return "urn:ngsi-ld:Subscription:mock-1"
    import httpx

    with httpx.Client(timeout=TRINO_TIMEOUT_S) as client:
        resp = client.post(f"{NGSI_LD_URL}/ngsi-ld/v1/subscriptions/", json=subscription, headers=_broker_headers())
    if resp.status_code != 201:
        raise RuntimeError(f"subscription geweigerd: {resp.status_code} {resp.text[:200]}")
    return resp.headers["Location"].rsplit("/", 1)[-1]


def trigger_notify(subscription_id: str) -> dict[str, Any]:
    """Sim-only: deterministische notificatie-trigger + outbox-payload."""
    if MOCK or not NGSI_LD_URL:
        return {"subscriptionId": subscription_id, "mock": True, "data": []}
    import httpx

    with httpx.Client(timeout=TRINO_TIMEOUT_S) as client:
        resp = client.post(f"{NGSI_LD_URL}/ngsi-ld/v1/subscriptions/{subscription_id}/notify", headers=_broker_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"notify mislukt: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def get_temporal_entity(
    entity_id: str, *, timerel: str, time: str, end_time: str | None = None
) -> dict[str, Any]:
    """NGSI-LD temporal read (before|after|between) via de broker."""
    if MOCK or not NGSI_LD_URL:
        return {"id": entity_id, "mock": True}
    import httpx

    params: dict[str, str] = {"timerel": timerel, "time": time, "time_property": "observedAt"}
    if end_time:
        params["endTime"] = end_time
    with httpx.Client(timeout=TRINO_TIMEOUT_S) as client:
        resp = client.get(
            f"{NGSI_LD_URL}/ngsi-ld/v1/temporal/entities/{entity_id}",
            params=params, headers=_broker_headers(),
        )
    if resp.status_code != 200:
        raise RuntimeError(f"temporal read mislukt: {resp.status_code} {resp.text[:200]}")
    return resp.json()


def create_registration(registration: dict[str, Any]) -> str:
    """NGSI-LD ContextSourceRegistration aanmaken; geeft de id terug."""
    if MOCK or not NGSI_LD_URL:
        return "urn:ngsi-ld:ContextSourceRegistration:mock-1"
    import httpx

    with httpx.Client(timeout=TRINO_TIMEOUT_S) as client:
        resp = client.post(f"{NGSI_LD_URL}/ngsi-ld/v1/registrations/", json=registration, headers=_broker_headers())
    if resp.status_code != 201:
        raise RuntimeError(f"registratie geweigerd: {resp.status_code} {resp.text[:200]}")
    return resp.headers["Location"].rsplit("/", 1)[-1]
```

- [ ] **Step 4: Verifieer groen (live + bestaande nldt-tests)**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_adapters_live.py -v` en `cd nldt && .venv/bin/python -m pytest tests/test_phase2_adapters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add nldt/services/adapters/data_platform.py toolbox-sim/tests/test_adapters_live.py
git commit -m "feat(nldt): data_platform-adapter subscriptions/notify/temporal/registrations (live tegen sim)"
```

---

### Taak 4: Play & Visualise — `/ui/map` kaartviewer + adapter `map_url()`

**Files:**
- Modify: `toolbox-sim/app/play_visualise.py`
- Modify: `nldt/services/adapters/play_visualise.py` (+ `map_url()`)
- Test: `toolbox-sim/tests/test_play_visualise.py` (aanvullen)

**Interfaces:**
- Consumes: de in-memory `data_sources`/`data_layers` in `create_app`.
- Produces: `GET /ui/map` (HTML, geen auth — browser-target); adapter `play_visualise.map_url() -> str`.

- [ ] **Step 1: Schrijf de falende test**

Aanvullen in `toolbox-sim/tests/test_play_visualise.py`:

```python
def test_ui_map_toont_geregistreerde_lagen():
    client = TestClient(create_app())
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    ds = client.post("/api/dataSources", headers=auth, json={
        "name": "zones", "type": "GeoJSON",
        "sourceConfiguration": {"type": "GeoJSON", "url": "http://localhost:9192/ngsi-ld/v1/entities", "headers": []},
        "securityConfiguration": {"type": "none", "headers": []},
    }).json()
    dl = client.post("/api/dataLayers", headers=auth, json={
        "name": "opportunity-zones", "dataSource": ds["id"], "type": "GeoJSON", "configuration": {},
    }).json()
    page = client.get("/ui/map")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "Leaflet" in page.text
    assert "opportunity-zones" in page.text
    assert dl["dataSource"] in page.text
```

(Als de bestaande file al `client`/imports heeft, hergebruik die; dit blok is zelfstandig.)

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_play_visualise.py -k ui_map -v`
Expected: FAIL (404)

- [ ] **Step 3: Implementeer `/ui/map` en de adapter-helper**

In `toolbox-sim/app/play_visualise.py` — bovenaan imports uitbreiden en het endpoint toevoegen (ná `get_data_layer`):

```python
import json

from fastapi.responses import HTMLResponse
```

```python
    @app.get("/ui/map", response_class=HTMLResponse)
    def ui_map():
        """Leesbare kaartviewer over de geregistreerde layers (browser-target, zonder auth)."""
        layers = [
            {
                "id": dl["id"],
                "name": dl["name"],
                "url": data_sources.get(dl["dataSource"], {}).get("sourceConfiguration", {}).get("url", ""),
            }
            for dl in data_layers.values()
        ]
        layers_js = json.dumps(layers)
        html = """<!doctype html>
<html><head><meta charset="utf-8"><title>toolbox-sim Play &amp; Visualise kaart</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>#map{height:100vh} .layerbox{position:absolute;top:8px;right:8px;z-index:1000;background:#fff;padding:8px;border-radius:6px;font:13px sans-serif}</style>
</head><body><div id="map"></div><div class="layerbox" id="layers"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const LAYERS = __LAYERS__;
const map = L.map('map').setView([52.09, 5.12], 8);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: 'OSM'}).addTo(map);
const box = document.getElementById('layers');
for (const layer of LAYERS) {
  const label = document.createElement('label');
  label.style.display = 'block';
  const cb = document.createElement('input');
  cb.type = 'checkbox'; cb.checked = true;
  const group = L.geoJSON.featureGroup ? L.featureGroup() : null;
  fetch(layer.url).then(r => r.json()).then(fc => {
    const g = L.geoJSON(fc, {onEachFeature: (f, popup) => popup.bindPopup(JSON.stringify(f.properties || {}, null, 1))});
    g.addTo(map); cb.addEventListener('change', () => cb.checked ? map.addLayer(g) : map.removeLayer(g));
    label.textContent = ' ' + layer.name;
  }).catch(() => { label.textContent = ' ' + layer.name + ' (bron onbereikbaar)'; });
  label.prepend(cb); box.appendChild(label);
}
</script></body></html>"""
        return HTMLResponse(content=html.replace("__LAYERS__", layers_js))
```

In `nldt/services/adapters/play_visualise.py` — naast de bestaande constanten/functies:

```python
def map_url() -> str:
    """URL van de sim-kaartviewer (leeg in mock zonder PV_BASE_URL)."""
    base = (os.environ.get("NLDT_PV_URL") or PV_BASE_URL or "").rstrip("/")
    return f"{base}/ui/map" if base else ""
```

(Controleer in de file de exacte constantennaam voor de basis-URL — `PV_BASE_URL` bestaat al volgens `test_play_visualise_mock_register`; gebruik die env-naam `NLDT_PV_URL` alleen als er nog geen bestaande env is, anders de bestaande.)

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_play_visualise.py tests/test_adapters_live.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/play_visualise.py nldt/services/adapters/play_visualise.py toolbox-sim/tests/test_play_visualise.py
git commit -m "feat(toolbox-sim): P&V /ui/map Leaflet-kaartviewer + adapter map_url()"
```

---

### Taak 5: algorithms — pure modelkern (`run_model` + `Ground`)

**Files:**
- Create: `toolbox-sim/app/algorithms.py`
- Test: `toolbox-sim/tests/test_full_catalogue.py` (nieuw; unit-test van de pure functies)

**Interfaces:**
- Consumes: `fixtures/dp-temporal.jsonld`, `fixtures/ngsi-ld/eubd-buildings.jsonld` (taak 1/bestaand).
- Produces: `MODEL_IDS: list[str]`, `SYNTHETIC: set[str]`, `MissingGround(RuntimeError)` (attr `.need`), `UnknownModel(KeyError)`, `BadInput(ValueError)`, `Ground`-dataclass (velden `knmi/peilen/eubd`), `load_ground(fixtures_dir: Path) -> Ground`, `run_model(name: str, inputs: dict, ground: Ground) -> dict`. Taak 6 (HTTP), 7 (UCS) en 14 (server) gebruiken exact deze namen.

- [ ] **Step 1: Schrijf de falende tests**

`toolbox-sim/tests/test_full_catalogue.py`:

```python
# toolbox-sim/tests/test_full_catalogue.py
"""Contract- en determinismetests voor de catalogus-apps (7 algoritmmodellen eerst)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM_ROOT))

from app.algorithms import Ground, MODEL_IDS, MissingGround, SYNTHETIC, load_ground, run_model

FIXTURES = SIM_ROOT / "fixtures"


@pytest.fixture(scope="module")
def ground():
    return load_ground(FIXTURES)


def test_model_ids_compleet():
    assert set(MODEL_IDS) == {
        "neighbourhood-energy-demand", "building-environmental-footprint", "renovation-strategies",
        "urban-planning-vulnerability", "urban-mobility", "pollution-propagation", "police-routing",
    }
    assert SYNTHETIC == {"urban-mobility", "pollution-propagation", "police-routing"}


def test_energy_eist_parameter(ground):
    with pytest.raises(ValueError):
        run_model("neighbourhood-energy-demand", {}, ground)  # geen intensiteit verzinnen


def test_energy_berekent_over_echte_areas(ground):
    out = run_model("neighbourhood-energy-demand", {"intensity_kwh_per_m2_year": 10.0}, ground)
    assert out["outputs"]["area_m2_total"] > 0
    assert abs(out["outputs"]["kwh_total"] - out["outputs"]["area_m2_total"] * 10.0) < 0.2
    assert out["provenance"]["areas"].startswith("fixtures/ngsi-ld/eubd-buildings.jsonld")


def test_footprint_en_renovatie_grondslag(ground):
    fp = run_model("building-environmental-footprint", {"carbon_kg_per_m2": 200.0}, ground)
    assert fp["outputs"]["carbon_kg_total"] > 0
    rn = run_model("renovation-strategies", {}, ground)
    assert len(rn["outputs"]["priority_by_tile"]) > 0


def test_vulnerability_uit_peilen(ground):
    out = run_model("urban-planning-vulnerability", {}, ground)
    rows = out["outputs"]["peilgebieden"]
    assert rows and 0.0 <= rows[0]["index"] <= 1.0
    assert out["provenance"]["source"] == "fixtures/dp-temporal.jsonld#peilen_latest"


def test_synthetische_modellen_gemarkeerd(ground):
    for name in sorted(SYNTHETIC):
        out = run_model(name, {}, ground)
        assert out["synthetic"] is True and out["provenance"]["syntheticSeed"] is True


def test_determinisme(ground):
    a = run_model("urban-mobility", {}, ground)
    b = run_model("urban-mobility", {}, ground)
    assert a == b


def test_missing_ground():
    with pytest.raises(MissingGround) as exc:
        run_model("urban-planning-vulnerability", {}, Ground())
    assert exc.value.need == "peilen"


def test_unknown_model():
    with pytest.raises(KeyError):
        run_model("bestaat-niet", {}, Ground())
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: FAIL (`ModuleNotFoundError: app.algorithms`)

- [ ] **Step 3: Implementeer `algorithms.py`**

```python
# toolbox-sim/app/algorithms.py
"""EU LDT algoritmmodel-stubs: echte grondslag waar die bestaat, anders expliciet seeded."""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path

MODEL_IDS = [
    "neighbourhood-energy-demand",
    "building-environmental-footprint",
    "renovation-strategies",
    "urban-planning-vulnerability",
    "urban-mobility",
    "pollution-propagation",
    "police-routing",
]
SYNTHETIC = {"urban-mobility", "pollution-propagation", "police-routing"}
KNMI_ID = "urn:ngsi-ld:WeatherObserved:knmi-260"
PEILEN_ID = "urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"
ZONES = ["utrecht-wind", "utrecht-zon", "utrecht-bos", "eindhoven-bp2op"]


class MissingGround(RuntimeError):
    def __init__(self, need: str):
        super().__init__(need)
        self.need = need


class UnknownModel(KeyError):
    pass


class BadInput(ValueError):
    pass


@dataclass
class Ground:
    knmi: list[dict] | None = None
    peilen: list[dict] | None = None
    eubd: list[dict] | None = None

    def require(self, what: str) -> None:
        if {"knmi": self.knmi, "peilen": self.peilen, "eubd": self.eubd}[what] is None:
            raise MissingGround(what)


def load_ground(fixtures_dir: Path) -> Ground:
    def _read(relpath: str):
        path = fixtures_dir / relpath
        return json.loads(path.read_text()) if path.exists() else None

    temporal = _read("dp-temporal.jsonld") or {}
    return Ground(
        knmi=(temporal.get(KNMI_ID) or {}).get("instances"),
        peilen=(temporal.get(PEILEN_ID) or {}).get("instances"),
        eubd=_read("ngsi-ld/eubd-buildings.jsonld"),
    )


def _seed(*parts: str) -> float:
    return (zlib.crc32("|".join(parts).encode()) % 10000) / 10000.0


def _entity_area_m2(entity: dict) -> float:
    """Planar oppervlak in EPSG:28992 (PoC-conventie: rekenen in RD)."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform

    geom = shape(entity["location"]["value"])
    to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True).transform
    return transform(to_rd, geom).area


def _eubd_totals(ground: Ground) -> dict:
    ground.require("eubd")
    tiles = {}
    total = 0.0
    for entity in ground.eubd or []:
        area = _entity_area_m2(entity)
        quadkey = entity.get("quadkey", {}).get("value", "?")
        tiles[quadkey] = tiles.get(quadkey, 0.0) + area
        total += area
    return {"tiles": dict(sorted(tiles.items(), key=lambda kv: -kv[1])), "total": total, "count": len(ground.eubd or [])}


def _energy_demand(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    intensity = inputs.get("intensity_kwh_per_m2_year")
    if not isinstance(intensity, (int, float)) or intensity <= 0:
        raise BadInput("intensity_kwh_per_m2_year (float > 0) is vereist; de stub verzint geen intensiteit")
    top = {q: round(area * intensity, 1) for q, area in list(totals["tiles"].items())[:10]}
    return {
        "outputs": {
            "kwh_total": round(totals["total"] * intensity, 1),
            "kwh_top10_tiles": top,
            "area_m2_total": round(totals["total"], 1),
            "tile_count": totals["count"],
        },
        "provenance": {
            "areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities, EPSG:28992-planar)",
            "parameter": "intensity_kwh_per_m2_year van aanvrager",
        },
    }


def _footprint(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    carbon = inputs.get("carbon_kg_per_m2")
    if not isinstance(carbon, (int, float)) or carbon <= 0:
        raise BadInput("carbon_kg_per_m2 (float > 0) is vereist; de stub verzint geen intensiteit")
    return {
        "outputs": {
            "carbon_kg_total": round(totals["total"] * carbon, 1),
            "area_m2_total": round(totals["total"], 1),
            "tile_count": totals["count"],
        },
        "provenance": {
            "areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities)",
            "parameter": "carbon_kg_per_m2 van aanvrager",
        },
    }


def _renovation(inputs: dict, ground: Ground) -> dict:
    totals = _eubd_totals(ground)
    priority = [{"quadkey": q, "area_m2": round(a, 1)} for q, a in list(totals["tiles"].items())[:10]]
    return {
        "outputs": {
            "priority_by_tile": priority,
            "note": "prioritering op echte tegeloppervlak; pakketkosten zijn bewust niet gesimuleerd",
        },
        "provenance": {"areas": "fixtures/ngsi-ld/eubd-buildings.jsonld (bron: exposure.entities)"},
    }


def _vulnerability(inputs: dict, ground: Ground) -> dict:
    ground.require("peilen")
    values = sorted(float(i["value"]) for i in ground.peilen or [])
    rows = []
    for i in sorted(ground.peilen or [], key=lambda x: x["datasetId"]):
        v = float(i["value"])
        rank = sum(1 for x in values if x <= v) / len(values)
        rows.append({"peilgebied": i["datasetId"], "waterstand_m": v, "index": round(rank, 3)})
    return {
        "outputs": {"peilgebieden": rows},
        "provenance": {
            "source": "fixtures/dp-temporal.jsonld#peilen_latest",
            "method": "percentielrang van waterstand per peilgebied (hoe ondieper/hoger, hoe hoger de index)",
        },
    }


def _mobility(inputs: dict, ground: Ground) -> dict:
    matrix = {a: {b: round(_seed(a, b, "od") * 1000, 1) for b in ZONES} for a in ZONES}
    modal = {z: {"car": round(0.4 + 0.2 * _seed(z, "car"), 2), "bike": round(0.3 + 0.1 * _seed(z, "bike"), 2)} for z in ZONES}
    return {
        "outputs": {"od_matrix_trips_day": matrix, "modal_split_share": modal},
        "provenance": {"syntheticSeed": True, "seed_basis": "crc32(zone|zone|tag)"},
        "synthetic": True,
    }


def _pollution(inputs: dict, ground: Ground) -> dict:
    raster = [[round(_seed("poll", r, c) * 50, 2) for c in range(16)] for r in range(16)]
    return {
        "outputs": {"grid_pm10_ug_m3": raster, "grid": "16x16 placeholder"},
        "provenance": {"syntheticSeed": True, "note": "placeholder voor het GPU-model (Pollution-Propagation-klasse)"},
        "synthetic": True,
    }


def _police(inputs: dict, ground: Ground) -> dict:
    response = {z: round(4 + 8 * _seed(z, "police"), 1) for z in ZONES}
    return {
        "outputs": {"response_minutes_by_zone": response},
        "provenance": {"syntheticSeed": True, "seed_basis": "crc32(zone|police)"},
        "synthetic": True,
    }


_HANDLERS = {
    "neighbourhood-energy-demand": _energy_demand,
    "building-environmental-footprint": _footprint,
    "renovation-strategies": _renovation,
    "urban-planning-vulnerability": _vulnerability,
    "urban-mobility": _mobility,
    "pollution-propagation": _pollution,
    "police-routing": _police,
}


def run_model(name: str, inputs: dict, ground: Ground) -> dict:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise UnknownModel(name)
    result = handler(inputs or {}, ground)
    return {"model": name, "deterministic": True, **result}


def create_app(ground: Ground) -> FastAPI:
    from fastapi import Depends, FastAPI
    from fastapi.responses import JSONResponse

    from app.guards import add_provenance, require_bearer

    app = FastAPI(title="toolbox-sim algorithms", docs_url=None, openapi_url=None)
    add_provenance(app, "algorithms")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/models")
    def list_models(_: dict = Depends(require_bearer)):
        return {"data": [{"id": m, "synthetic": m in SYNTHETIC} for m in MODEL_IDS]}

    @app.get("/models/{name}")
    def model_meta(name: str, _: dict = Depends(require_bearer)):
        if name not in _HANDLERS:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        return {"id": name, "synthetic": name in SYNTHETIC, "deterministic": True}

    @app.post("/models/{name}/run")
    def run(name: str, inputs: dict, _: dict = Depends(require_bearer)):
        try:
            return run_model(name, inputs, ground)
        except UnknownModel:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        except MissingGround as exc:
            return JSONResponse(status_code=503, content={"error": "missing-ground", "description": exc.need})
        except BadInput as exc:
            return JSONResponse(status_code=422, content={"error": "bad-input", "description": str(exc)})

    return app
```

(Voeg bovenin hetzelfde bestand de FastAPI-imports toe zoals in `create_app` getoond — het bestand importeert FastAPI lazy binnen `create_app` zodat de pure functies ook zonder FastAPI testbaar zijn.)

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: PASS (alle)

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/algorithms.py toolbox-sim/tests/test_full_catalogue.py
git commit -m "feat(toolbox-sim): 7 algoritmmodel-stubs — echte grondslag (eubd/peilen) of expliciet seeded"
```

---

### Taak 6: UCS — experiment-authoring + model-executie

**Files:**
- Modify: `toolbox-sim/app/ucs.py`
- Test: `toolbox-sim/tests/test_ucs.py` (aanvullen)

**Interfaces:**
- Consumes: `algorithms.MODEL_IDS`, `algorithms.run_model(name, inputs, ground)`, `algorithms.Ground` (taak 5); `fixtures/recipes.json` (taak 1).
- Produces: `create_app(processes: dict, recipes: dict | None = None, ground: "Ground | None" = None)`; endpoints `POST /api/v1/experiments` (201), `GET /api/v1/experiments`, `GET /api/v1/experiments/{id}`; bestaand trigger-contract ongewijzigd + `processId` in `MODEL_IDS` → model-uitvoering. Server (taak 14) geeft recipes+ground door.

- [ ] **Step 1: Schrijf de falende tests**

Aanvullen in `toolbox-sim/tests/test_ucs.py`:

```python
def test_experiment_authoring_en_model_run():
    from app.algorithms import load_ground
    from app.ucs import create_app as ucs_app

    processes = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ucs-processes.json").read_text())
    recipes = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "recipes.json").read_text())
    ground = load_ground(Path(__file__).resolve().parents[1] / "fixtures")
    client = TestClient(ucs_app(processes, recipes=recipes, ground=ground))
    auth = {"Authorization": "Bearer sim-toolbox-token"}

    recipe_id = sorted(recipes)[0]
    r = client.post("/api/v1/experiments", headers=auth, json={"name": "scan-1", "recipeId": recipe_id})
    assert r.status_code == 201
    exp = r.json()
    assert exp["id"].startswith("exp-") and exp["recipeId"] == recipe_id and exp["runs"] == []

    run = client.post("/api/v1/experiments/trigger-process", headers=auth,
                      json={"processId": "urban-mobility", "inputs": {}, "experimentId": exp["id"]})
    assert run.status_code == 200 and run.json()["synthetic"] is True
    listed = client.get(f"/api/v1/experiments/{exp['id']}", headers=auth).json()
    assert len(listed["runs"]) == 1 and listed["runs"][0]["processId"] == "urban-mobility"

    unknown = client.post("/api/v1/experiments", headers=auth, json={"name": "x", "recipeId": "ontbreekt"})
    assert unknown.status_code == 404 and unknown.json()["error"] == "recipe-not-found"
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_ucs.py -k authoring -v`
Expected: FAIL (404 op POST /api/v1/experiments)

- [ ] **Step 3: Implementeer**

Vervang de inhoud van `toolbox-sim/app/ucs.py` (bestaand replay-gedrag blijft exact gelijk):

```python
# toolbox-sim/app/ucs.py
"""EU LDT UCS-sim: experiment-trigger (canonieke replay) + authoring + model-executie."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class TriggerIn(BaseModel):
    processId: str
    inputs: dict = {}
    experimentId: str | None = None


class ExperimentIn(BaseModel):
    name: str
    recipeId: str


def create_app(processes: dict, recipes: dict | None = None, ground=None) -> FastAPI:
    app = FastAPI(title="toolbox-sim ucs", docs_url=None, openapi_url=None)
    add_provenance(app, "ucs")
    experiments: dict[str, dict] = {}
    counter = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/api/v1/experiments", status_code=201)
    def create_experiment(payload: ExperimentIn, _: dict = Depends(require_bearer)):
        recipe = (recipes or {}).get(payload.recipeId)
        if recipe is None:
            return JSONResponse(status_code=404, content={"error": "recipe-not-found", "description": payload.recipeId})
        counter["n"] += 1
        exp = {
            "id": f"exp-{counter['n']}",
            "name": payload.name,
            "recipeId": payload.recipeId,
            "recipeTitle": recipe.get("title", payload.recipeId),
            "runs": [],
        }
        experiments[exp["id"]] = exp
        return exp

    @app.get("/api/v1/experiments")
    def list_experiments(_: dict = Depends(require_bearer)):
        return {"data": [dict(e) for e in experiments.values()]}

    @app.get("/api/v1/experiments/{exp_id}")
    def get_experiment(exp_id: str, _: dict = Depends(require_bearer)):
        exp = experiments.get(exp_id)
        if exp is None:
            return JSONResponse(status_code=404, content={"error": "experiment-not-found", "description": exp_id})
        return exp

    @app.post("/api/v1/experiments/trigger-process")
    def trigger(payload: TriggerIn, _: dict = Depends(require_bearer)):
        from app import algorithms

        if payload.processId in algorithms.MODEL_IDS:
            if ground is None:
                return JSONResponse(status_code=503, content={"error": "missing-ground", "description": "ground niet geladen"})
            try:
                result = algorithms.run_model(payload.processId, payload.inputs, ground)
            except algorithms.MissingGround as exc:
                return JSONResponse(status_code=503, content={"error": "missing-ground", "description": exc.need})
            except algorithms.BadInput as exc:
                return JSONResponse(status_code=422, content={"error": "bad-input", "description": str(exc)})
        else:
            entry = processes.get(payload.processId)
            if entry is None:
                # Afwijking plan (taak-4/8-precedent): top-level {"error": ...};
                # HTTPException-detail wordt in {"detail": ...} gewrapped.
                return JSONResponse(status_code=404, content={"error": "process-not-found", "description": payload.processId})
            result = {
                "outputs": entry["outputs"],
                "provenance": f"sim-replay://canonical/{entry['runId']}",
            }
        exp = experiments.get(payload.experimentId or "")
        if exp is not None:
            exp["runs"].append({"processId": payload.processId, "inputs": payload.inputs})
        return result

    return app
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_ucs.py tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/ucs.py toolbox-sim/tests/test_ucs.py
git commit -m "feat(toolbox-sim): UCS experiment-authoring + model-executie via algorithms-kern"
```

---

### Taak 7: Data Space Ready — EDC-stub (:9197)

**Files:**
- Create: `toolbox-sim/app/dataspace_ready.py`
- Test: `toolbox-sim/tests/test_full_catalogue.py` (aanvullen)

**Interfaces:**
- Consumes: offers uit `nldt/data/dataspace/offers/*.json` (velden `uid`, `datasetId`, `lakeUri`, `accessClass`, `license`).
- Produces: `create_app(offers: list[dict], lake_root: Path | None = None) -> FastAPI`; endpoints `POST /v3/policydefinitions|/v3/assets|/v3/contractdefinitions` (201), `POST /v2/catalog/request`, `POST /v2/contractnegotiations` (REQUESTED) + `GET …/{id}` (→CONFIRMED), `POST /v2/transferprocesses` (STARTED) + `GET …/{id}` (→COMPLETED+destination). Taak 10 (connector) gebruikt exact deze paden.

- [ ] **Step 1: Schrijf de falende test**

Aanvullen in `toolbox-sim/tests/test_full_catalogue.py`:

```python
def test_edc_stub_flow():
    from app.dataspace_ready import create_app as dsr_app

    offer = {"uid": "offer-test1", "datasetId": "gold-x.geojson",
             "lakeUri": "lake://nldt-poc-lake/gold/x.geojson", "accessClass": "open", "license": "CC0-1.0"}
    client = TestClient(dsr_app([offer], lake_root=SIM_ROOT.parent / "nldt" / "data" / "lake"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}

    asset = client.post("/v3/assets", headers=auth, json={"@id": "asset-test1"})
    assert asset.status_code == 201
    catalog = client.post("/v2/catalog/request", headers=auth, json={}).json()
    assert any(o["uid"] == "offer-test1" for o in catalog["offers"])

    cn = client.post("/v2/contractnegotiations", headers=auth, json={"offerUid": "offer-test1"}).json()
    assert cn["state"] == "REQUESTED"
    assert client.get(f"/v2/contractnegotiations/{cn['id']}", headers=auth).json()["state"] == "CONFIRMED"

    tp = client.post("/v2/transferprocesses", headers=auth,
                     json={"negotiationId": cn["id"], "offerUid": "offer-test1"}).json()
    assert tp["state"] == "STARTED"
    done = client.get(f"/v2/transferprocesses/{tp['id']}", headers=auth).json()
    assert done["state"] == "COMPLETED"
    assert done["offerUid"] == "offer-test1"

    missing = client.post("/v2/contractnegotiations", headers=auth, json={"offerUid": "ontbreekt"})
    assert missing.status_code == 404 and missing.json()["error"] == "offer-not-found"
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -k edc -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementeer `dataspace_ready.py`**

```python
# toolbox-sim/app/dataspace_ready.py
"""EU LDT Data Space Ready-sim: EDC-connectorstub (Management v3 + flow v2)."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, Response

from app.guards import add_provenance, require_bearer


def create_app(offers: list[dict], lake_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="toolbox-sim dataspace-ready", docs_url=None, openapi_url=None)
    add_provenance(app, "dataspace-ready")
    offers_by_uid = {o["uid"]: o for o in offers}
    assets: dict[str, dict] = {}
    policies: dict[str, dict] = {}
    contract_defs: dict[str, dict] = {}
    negotiations: dict[str, dict] = {}
    transfers: dict[str, dict] = {}
    seq = {"n": 0}
    state_reads: dict[str, int] = {}

    def _next(prefix: str) -> str:
        seq["n"] += 1
        return f"{prefix}-sim-{seq['n']}"

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/v3/policydefinitions", status_code=201)
    def create_policy(policy: dict, _: dict = Depends(require_bearer)):
        pid = policy.get("@id") or _next("policy")
        policies[pid] = {**policy, "@id": pid}
        return Response(status_code=201, headers={"Location": f"/v3/policydefinitions/{pid}"})

    @app.post("/v3/assets", status_code=201)
    def create_asset(asset: dict, _: dict = Depends(require_bearer)):
        aid = asset.get("@id") or _next("asset")
        assets[aid] = {**asset, "@id": aid}
        return Response(status_code=201, headers={"Location": f"/v3/assets/{aid}"})

    @app.post("/v3/contractdefinitions", status_code=201)
    def create_contract_definition(definition: dict, _: dict = Depends(require_bearer)):
        cid = definition.get("@id") or _next("contract")
        contract_defs[cid] = {**definition, "@id": cid}
        return Response(status_code=201, headers={"Location": f"/v3/contractdefinitions/{cid}"})

    @app.post("/v2/catalog/request")
    def catalog_request(payload: dict, _: dict = Depends(require_bearer)):
        return {
            "@type": "cat:Catalog",
            "offers": [
                {"uid": o["uid"], "datasetId": o.get("datasetId"), "lakeUri": o.get("lakeUri"),
                 "accessClass": o.get("accessClass"), "license": o.get("license")}
                for o in offers
            ],
        }

    @app.post("/v2/contractnegotiations", status_code=201)
    def create_negotiation(payload: dict, _: dict = Depends(require_bearer)):
        offer = offers_by_uid.get(payload.get("offerUid") or "")
        if offer is None:
            return JSONResponse(status_code=404, content={"error": "offer-not-found", "description": payload.get("offerUid")})
        nid = _next("cn")
        negotiations[nid] = {"id": nid, "offerUid": offer["uid"], "state": "REQUESTED"}
        return negotiations[nid]

    @app.get("/v2/contractnegotiations/{nid}")
    def get_negotiation(nid: str, _: dict = Depends(require_bearer)):
        cn = negotiations.get(nid)
        if cn is None:
            return JSONResponse(status_code=404, content={"error": "negotiation-not-found", "description": nid})
        # deterministische state-machine: eerste read bevestigt
        cn["state"] = "CONFIRMED"
        return cn

    @app.post("/v2/transferprocesses", status_code=201)
    def create_transfer(payload: dict, _: dict = Depends(require_bearer)):
        offer = offers_by_uid.get(payload.get("offerUid") or "")
        if offer is None:
            return JSONResponse(status_code=404, content={"error": "offer-not-found", "description": payload.get("offerUid")})
        tid = _next("tp")
        local = ""
        if lake_root is not None and offer.get("lakeUri", "").startswith("lake://"):
            local = str(lake_root / offer["lakeUri"].removeprefix("lake://nldt-poc-lake/"))
        transfers[tid] = {"id": tid, "offerUid": offer["uid"], "state": "STARTED",
                          "destination": local, "negotiationId": payload.get("negotiationId")}
        return transfers[tid]

    @app.get("/v2/transferprocesses/{tid}")
    def get_transfer(tid: str, _: dict = Depends(require_bearer)):
        tp = transfers.get(tid)
        if tp is None:
            return JSONResponse(status_code=404, content={"error": "transfer-not-found", "description": tid})
        # deterministische state-machine: eerste read rondt de overdracht af
        tp["state"] = "COMPLETED"
        return tp

    return app
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/dataspace_ready.py toolbox-sim/tests/test_full_catalogue.py
git commit -m "feat(toolbox-sim): EDC-connectorstub (Management v3 + catalog/negotiate/transfer v2)"
```

---

### Taak 8: Participate (:9199) + Federated Learning (:9200)

**Files:**
- Create: `toolbox-sim/app/participate.py`, `toolbox-sim/app/federated_learning.py`
- Test: `toolbox-sim/tests/test_full_catalogue.py` (aanvullen)

**Interfaces:**
- Consumes: `fixtures/participate-seed.json` (taak 1).
- Produces: `participate.create_app(seed: dict) -> FastAPI` (endpoints `GET/POST /api/proposals`, `GET /api/meetings`, `POST /rooms`); `federated_learning.create_app(peilen_instances: list[dict] | None) -> FastAPI` (endpoints `POST /rounds`, `POST /rounds/{id}/updates`, `GET /rounds/{id}/result`). Taak 14 bouwt hierop.

- [ ] **Step 1: Schrijf de falende tests**

Aanvullen in `toolbox-sim/tests/test_full_catalogue.py`:

```python
def test_participate_stub():
    import json as _json

    from app.participate import create_app as participate_app

    seed = _json.loads((FIXTURES / "participate-seed.json").read_text())
    client = TestClient(participate_app(seed))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    assert len(client.get("/api/meetings", headers=auth).json()["data"]) == 1
    created = client.post("/api/proposals", headers=auth,
                          json={"title": "Nieuwe zone", "area": "utrecht"}).json()
    assert created["id"].startswith("prop-") and created["state"] == "open"
    room = client.post("/rooms", headers=auth, json={"title": "sessie"}).json()
    assert room["roomUrl"].startswith("http://localhost:9199/rooms/")

    noauth = client.get("/api/proposals")
    assert noauth.status_code == 401


def test_federated_learning_round():
    from app.algorithms import load_ground
    from app.federated_learning import create_app as fl_app

    ground = load_ground(FIXTURES)
    client = TestClient(fl_app(ground.peilen))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    rnd = client.post("/rounds", headers=auth, json={"name": "peilen-r1"}).json()
    update = client.post(f"/rounds/{rnd['id']}/updates", headers=auth,
                         json={"municipality": "rijnland"}).json()
    assert update["metric"]["mean_waterstand_m"] < 0  # echte peilen zijn onder NAP
    result = client.get(f"/rounds/{rnd['id']}/result", headers=auth).json()
    assert result["participants"] == 1 and "mean_waterstand_m" in result["aggregate"]
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -k "participate or learning" -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementeer beide apps**

`toolbox-sim/app/participate.py`:

```python
# toolbox-sim/app/participate.py
"""EU LDT Participate-sim: Decidim-vorm (proposals/meetings) + Jitsi-vorm (rooms)."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class ProposalIn(BaseModel):
    title: str
    area: str = "utrecht"


class RoomIn(BaseModel):
    title: str


def create_app(seed: dict) -> FastAPI:
    app = FastAPI(title="toolbox-sim participate", docs_url=None, openapi_url=None)
    add_provenance(app, "participate")
    proposals: dict[str, dict] = {p["id"]: dict(p) for p in seed.get("proposals", [])}
    meetings = [dict(m) for m in seed.get("meetings", [])]
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/api/proposals")
    def list_proposals(_: dict = Depends(require_bearer)):
        return {"data": [dict(p) for p in proposals.values()]}

    @app.post("/api/proposals", status_code=201)
    def create_proposal(payload: ProposalIn, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        prop = {"id": f"prop-{len(proposals) + seq['n']}", "title": payload.title,
                "area": payload.area, "state": "open",
                "provenance": "toolbox-sim/participate; seed=fixtures/participate-seed.json"}
        proposals[prop["id"]] = prop
        return prop

    @app.get("/api/meetings")
    def list_meetings(_: dict = Depends(require_bearer)):
        return {"data": meetings}

    @app.post("/rooms")
    def create_room(payload: RoomIn, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        slug = payload.title.lower().replace(" ", "-")[:24] or f"room-{seq['n']}"
        return {"roomUrl": f"http://localhost:9199/rooms/{slug}-{seq['n']}", "title": payload.title}

    return app
```

`toolbox-sim/app/federated_learning.py`:

```python
# toolbox-sim/app/federated_learning.py
"""EU LDT Federated Learning-sim: rounds met deterministische gemeente-aggregaten."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def _aggregate(peilen_instances: list[dict] | None, tag: str) -> dict:
    if peilen_instances:
        values = [float(i["value"]) for i in peilen_instances]
        return {"mean_waterstand_m": round(sum(values) / len(values), 3), "n_peilgebieden": len(values)}
    return {"mean_waterstand_m": 0.0, "n_peilgebieden": 0, "syntheticSeed": True, "seed": str(sum(map(ord, tag)))}


def create_app(peilen_instances: list[dict] | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim federated-learning", docs_url=None, openapi_url=None)
    add_provenance(app, "federated-learning")
    rounds: dict[str, dict] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/rounds", status_code=201)
    def create_round(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        rid = f"round-{seq['n']}"
        rounds[rid] = {"id": rid, "name": payload.get("name", rid), "participants": []}
        return rounds[rid]

    @app.post("/rounds/{rid}/updates")
    def submit_update(rid: str, payload: dict, _: dict = Depends(require_bearer)):
        rnd = rounds.get(rid)
        if rnd is None:
            return JSONResponse(status_code=404, content={"error": "round-not-found", "description": rid})
        municipality = payload.get("municipality", f"muni-{len(rnd['participants']) + 1}")
        if municipality not in rnd["participants"]:
            rnd["participants"].append(municipality)
        return {"round": rid, "municipality": municipality, "metric": _aggregate(peilen_instances, municipality)}

    @app.get("/rounds/{rid}/result")
    def result(rid: str, _: dict = Depends(require_bearer)):
        rnd = rounds.get(rid)
        if rnd is None:
            return JSONResponse(status_code=404, content={"error": "round-not-found", "description": rid})
        aggregate = _aggregate(peilen_instances, "|".join(rnd["participants"]) or rid)
        return {"round": rid, "participants": len(rnd["participants"]), "aggregate": aggregate}

    return app
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/participate.py toolbox-sim/app/federated_learning.py toolbox-sim/tests/test_full_catalogue.py
git commit -m "feat(toolbox-sim): Participate- (Decidim/Jitsi-vorm) en Federated Learning-stub"
```

---

### Taak 9: AI Notebook (:9201) + Data Modeller (:9202)

**Files:**
- Create: `toolbox-sim/app/ai_notebook.py`, `toolbox-sim/app/data_modeller.py`
- Test: `toolbox-sim/tests/test_full_catalogue.py` (aanvullen)

**Interfaces:**
- Consumes: `fixtures/lake-inventory` niet nodig; `nldt/schemas/*.json` (lezen) en lake-inventaris via `REPO/nldt/data/lake-inventory.json`.
- Produces: `ai_notebook.create_app(lake_root: Path | None) -> FastAPI` (`POST /notebooks`, `POST /pipelines/runs`, `GET /pipelines/runs/{id}`); `data_modeller.create_app(schemas: dict[str, dict]) -> FastAPI` (`GET/POST/DELETE /models`, `POST /models/{name}/validate`). Taak 14 bouwt hierop.

- [ ] **Step 1: Schrijf de falende tests**

Aanvullen in `toolbox-sim/tests/test_full_catalogue.py`:

```python
def test_ai_notebook_pipeline_run():
    from app.ai_notebook import create_app as ain_app

    client = TestClient(ain_app(lake_root=SIM_ROOT.parent / "nldt" / "data" / "lake" / "nldt-poc-lake"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    nb = client.post("/notebooks", headers=auth, json={"name": "analyse"}).json()
    assert nb["id"].startswith("nb-")
    run = client.post("/pipelines/runs", headers=auth,
                      json={"notebookId": nb["id"], "pipeline": "inventory-count"}).json()
    assert run["state"] == "SUCCEEDED"
    assert run["outputs"]["inventoryDatasets"] > 0
    again = client.get(f"/pipelines/runs/{run['id']}", headers=auth).json()
    assert again == run  # deterministisch


def test_data_modeller_registry_en_validatie():
    from app.data_modeller import create_app as dm_app

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id"],
        "properties": {"id": {"type": "string"}},
    }
    client = TestClient(dm_app({"Address": schema}))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    models = client.get("/models", headers=auth).json()
    assert "Address" in models["data"]
    ok = client.post("/models/Address/validate", headers=auth, json={"id": "adr-1"}).json()
    assert ok["valid"] is True and ok["findings"] == []
    bad = client.post("/models/Address/validate", headers=auth, json={"nope": 1}).json()
    assert bad["valid"] is False and bad["findings"]
    missing = client.post("/models/Onbekend/validate", headers=auth, json={})
    assert missing.status_code == 404 and missing.json()["error"] == "model-not-found"
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -k "notebook or modeller" -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementeer beide apps**

`toolbox-sim/app/ai_notebook.py`:

```python
# toolbox-sim/app/ai_notebook.py
"""EU LDT AI Notebook-sim: notebook-sessies + deterministische pipeline-runs over de lake-inventaris."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def create_app(lake_root: Path | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim ai-notebook", docs_url=None, openapi_url=None)
    add_provenance(app, "ai-notebook")
    notebooks: dict[str, dict] = {}
    runs: dict[str, dict] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.post("/notebooks", status_code=201)
    def create_notebook(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        nb = {"id": f"nb-{seq['n']}", "name": payload.get("name", f"notebook-{seq['n']}")}
        notebooks[nb["id"]] = nb
        return nb

    @app.post("/pipelines/runs", status_code=201)
    def run_pipeline(payload: dict, _: dict = Depends(require_bearer)):
        nb = notebooks.get(payload.get("notebookId") or "")
        if nb is None:
            return JSONResponse(status_code=404, content={"error": "notebook-not-found", "description": payload.get("notebookId")})
        seq["n"] += 1
        rid = f"run-{seq['n']}"
        inventory = 0
        if lake_root is not None:
            inv = lake_root / "catalog" / "inventory.parquet"
            mirrors = lake_root / "iceberg" / "mirrors" / "inventory.parquet"
            count_path = mirrors if mirrors.exists() else inv
            if count_path.exists():
                import duckdb

                inventory = duckdb.connect().execute(
                    f"SELECT count(*) FROM read_parquet('{count_path.as_posix()}')"
                ).fetchone()[0]
        run = {
            "id": rid, "notebookId": nb["id"], "pipeline": payload.get("pipeline", "inventory-count"),
            "state": "SUCCEEDED" if inventory else "NO_GROUND",
            "outputs": {"inventoryDatasets": inventory, "lakeRoot": str(lake_root or "")},
            "provenance": "lake://nldt-poc-lake/iceberg/mirrors/inventory.parquet",
        }
        runs[rid] = run
        return run

    @app.get("/pipelines/runs/{rid}")
    def get_run(rid: str, _: dict = Depends(require_bearer)):
        run = runs.get(rid)
        if run is None:
            return JSONResponse(status_code=404, content={"error": "run-not-found", "description": rid})
        return run

    return app
```

`toolbox-sim/app/data_modeller.py`:

```python
# toolbox-sim/app/data_modeller.py
"""EU LDT Data Modeller-sim: model-registry (seeded uit nldt/schemas) + jsonschema-validatie."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, Response

from app.guards import add_provenance, require_bearer


def create_app(schemas: dict[str, dict]) -> FastAPI:
    app = FastAPI(title="toolbox-sim data-modeller", docs_url=None, openapi_url=None)
    add_provenance(app, "data-modeller")
    models: dict[str, dict] = {name: dict(s) for name, s in schemas.items()}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/models")
    def list_models(_: dict = Depends(require_bearer)):
        return {"data": sorted(models)}

    @app.post("/models", status_code=201)
    def create_model(payload: dict, _: dict = Depends(require_bearer)):
        name = payload.get("name") or ""
        schema = payload.get("schema")
        if not name or not isinstance(schema, dict):
            return JSONResponse(status_code=400, content={"error": "BadRequest", "description": "name en schema (object) zijn vereist"})
        models[name] = schema
        return Response(status_code=201, headers={"Location": f"/models/{name}"})

    @app.delete("/models/{name}", status_code=204)
    def delete_model(name: str, _: dict = Depends(require_bearer)):
        models.pop(name, None)
        return Response(status_code=204)

    @app.post("/models/{name}/validate")
    def validate(name: str, instance: dict, _: dict = Depends(require_bearer)):
        schema = models.get(name)
        if schema is None:
            return JSONResponse(status_code=404, content={"error": "model-not-found", "description": name})
        import jsonschema

        try:
            jsonschema.Draft202012Validator(schema).validate(instance)
            return {"valid": True, "findings": []}
        except jsonschema.ValidationError as exc:
            return {"valid": False, "findings": [{"path": list(exc.absolute_path), "message": exc.message}]}

    return app
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/ai_notebook.py toolbox-sim/app/data_modeller.py toolbox-sim/tests/test_full_catalogue.py
git commit -m "feat(toolbox-sim): AI Notebook- (pipeline over lake-inventaris) en Data Modeller-stub"
```

---

### Taak 10: Integrated Environment (:9203) + City Innovation Planner (:9204)

**Files:**
- Create: `toolbox-sim/app/integrated_environment.py`, `toolbox-sim/app/cip.py`
- Test: `toolbox-sim/tests/test_full_catalogue.py` (aanvullen)

**Interfaces:**
- Consumes: `REPO/nldt/data/lake-inventory.json` (IE `/catalogue`).
- Produces: `integrated_environment.create_app(solutions: list[dict], inventory_path: Path | None) -> FastAPI` (`GET /solutions`, `GET /catalogue`, `GET /metrics`); `cip.create_app() -> FastAPI` (`GET/POST /scenarios`, `GET/POST /scenarios/{id}/contributions`). Taak 14 bouwt hierop.

- [ ] **Step 1: Schrijf de falende test**

Aanvullen in `toolbox-sim/tests/test_full_catalogue.py`:

```python
def test_integrated_environment_portal():
    from app.integrated_environment import create_app as ie_app

    solutions = [{"name": "identity", "port": 9191, "status": "simulated"}]
    client = TestClient(ie_app(solutions, inventory_path=SIM_ROOT.parent / "nldt" / "data" / "lake-inventory.json"))
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    listed = client.get("/solutions", headers=auth).json()
    assert listed["data"][0]["name"] == "identity" and listed["total"] == 1
    metrics = client.get("/metrics", headers=auth)
    assert metrics.status_code == 200 and "solutions_total 1" in metrics.text
    catalogue = client.get("/catalogue", headers=auth).json()
    assert catalogue["total"] >= 50  # lake-inventaris telt ruim honderd datasets


def test_cip_scenarios_en_contributions():
    from app.cip import create_app as cip_app

    client = TestClient(cip_app())
    auth = {"Authorization": "Bearer sim-toolbox-token"}
    scenario = client.post("/scenarios", headers=auth, json={"name": "energietransitie"}).json()
    assert scenario["id"].startswith("scen-")
    contribution = client.post(f"/scenarios/{scenario['id']}/contributions", headers=auth,
                               json={"author": "buurtgroep", "text": "meer groen"}).json()
    assert contribution["id"].startswith("contrib-")
    listed = client.get(f"/scenarios/{scenario['id']}/contributions", headers=auth).json()
    assert listed["total"] == 1
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -k "environment or cip" -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Implementeer beide apps**

`toolbox-sim/app/integrated_environment.py`:

```python
# toolbox-sim/app/integrated_environment.py
"""EU LDT Integrated Environment-sim: portal-aggregatie, OGC-Records-vorm, metrics."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Response

from app.guards import add_provenance, require_bearer


def create_app(solutions: list[dict], inventory_path: Path | None) -> FastAPI:
    app = FastAPI(title="toolbox-sim integrated-environment", docs_url=None, openapi_url=None)
    add_provenance(app, "integrated-environment")

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/solutions")
    def list_solutions(_: dict = Depends(require_bearer)):
        return {"total": len(solutions), "data": [dict(s) for s in solutions]}

    @app.get("/catalogue")
    def catalogue(_: dict = Depends(require_bearer)):
        datasets = []
        if inventory_path is not None and inventory_path.exists():
            inv = json.loads(inventory_path.read_text())
            datasets = [
                {"id": d.get("id"), "poc": d.get("poc"), "zone": d.get("zone"),
                 "lakeUri": d.get("lakeUri"), "license": d.get("license")}
                for d in inv.get("datasets", [])
            ]
        return {"type": "Catalogue", "total": len(datasets), "data": datasets}

    @app.get("/metrics")
    def metrics(_: dict = Depends(require_bearer)):
        lines = [f"solutions_total {len(solutions)}"]
        for s in solutions:
            lines.append(f'solution_up{{name="{s.get("name", "?")}"}} 1')
        return Response(content="\n".join(lines) + "\n", media_type="text/plain")

    return app
```

`toolbox-sim/app/cip.py`:

```python
# toolbox-sim/app/cip.py
"""EU LDT City Innovation Planner-sim: co-creatie-scenario's + contributions."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.guards import add_provenance, require_bearer


def create_app() -> FastAPI:
    app = FastAPI(title="toolbox-sim cip", docs_url=None, openapi_url=None)
    add_provenance(app, "cip")
    scenarios: dict[str, dict] = {}
    contributions: dict[str, list[dict]] = {}
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/scenarios")
    def list_scenarios(_: dict = Depends(require_bearer)):
        return {"total": len(scenarios), "data": [dict(s) for s in scenarios.values()]}

    @app.post("/scenarios", status_code=201)
    def create_scenario(payload: dict, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        scen = {"id": f"scen-{seq['n']}", "name": payload.get("name", f"scenario-{seq['n']}"), "contributions": 0}
        scenarios[scen["id"]] = scen
        contributions[scen["id"]] = []
        return scen

    @app.post("/scenarios/{scen_id}/contributions", status_code=201)
    def add_contribution(scen_id: str, payload: dict, _: dict = Depends(require_bearer)):
        if scen_id not in scenarios:
            return JSONResponse(status_code=404, content={"error": "scenario-not-found", "description": scen_id})
        seq["n"] += 1
        contrib = {"id": f"contrib-{seq['n']}", "author": payload.get("author", "anoniem"),
                   "text": payload.get("text", "")}
        contributions[scen_id].append(contrib)
        scenarios[scen_id]["contributions"] = len(contributions[scen_id])
        return contrib

    @app.get("/scenarios/{scen_id}/contributions")
    def list_contributions(scen_id: str, _: dict = Depends(require_bearer)):
        if scen_id not in scenarios:
            return JSONResponse(status_code=404, content={"error": "scenario-not-found", "description": scen_id})
        items = contributions.get(scen_id, [])
        return {"total": len(items), "data": items}

    return app
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/integrated_environment.py toolbox-sim/app/cip.py toolbox-sim/tests/test_full_catalogue.py
git commit -m "feat(toolbox-sim): Integrated Environment-portal en City Innovation Planner-stub"
```

---

### Taak 11: server.py — `build_apps()`, 8 nieuwe poorten, `--full`; run_sim.sh

**Files:**
- Modify: `toolbox-sim/app/server.py`
- Modify: `toolbox-sim/run_sim.sh`
- Test: `toolbox-sim/tests/test_server_boot.py` (aanvullen)

**Interfaces:**
- Consumes: alle `create_app`-fabrieken uit taak 2/4–10; `build_fixtures`-artefacten (taak 1).
- Produces: `build_apps(full: bool, eubd: bool) -> dict[str, FastAPI]` — de enige app-fabrieksbron; `main()` start alleen nog de servers. Eubd-gedrag ongewijzigd.

- [ ] **Step 1: Schrijf de falende test**

Aanvullen in `toolbox-sim/tests/test_server_boot.py` (pas aan op de bestaande imports in die file):

```python
def test_build_apps_basis():
    from app.server import build_apps

    apps = build_apps(full=False, eubd=False)
    assert set(apps) == {"identity", "broker", "pv", "ucs", "marketplace"}


def test_build_apps_full_omvat_alle_veertien():
    from app.server import build_apps

    apps = build_apps(full=True, eubd=False)
    assert set(apps) == {
        "identity", "broker", "pv", "ucs", "marketplace",
        "dataspace", "algorithms", "participate", "fl", "ain", "dm", "ie", "cip",
    }
    for name, app in apps.items():
        client = TestClient(app)
        assert client.get("/health").status_code == 200, name
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_server_boot.py -v`
Expected: FAIL (`ImportError: cannot import name 'build_apps'`)

- [ ] **Step 3: Herstructureer `server.py`**

Vervang de inhoud van `toolbox-sim/app/server.py`:

```python
# toolbox-sim/app/server.py
"""Start alle sim-diensten: 9191–9195 (+9196 met --eubd, +9197–9204 met --full)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import uvicorn

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REPO = Path(__file__).resolve().parents[2]
PORTS = {
    "identity": 9191, "broker": 9192, "pv": 9193, "ucs": 9194, "marketplace": 9195, "eubd": 9196,
    "dataspace": 9197, "algorithms": 9198, "participate": 9199,
    "fl": 9200, "ain": 9201, "dm": 9202, "ie": 9203, "cip": 9204,
}


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


def _read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def build_apps(full: bool, eubd: bool) -> dict[str, "FastAPI"]:
    from app.algorithms import create_app as algorithms_app
    from app.algorithms import load_ground
    from app.cip import create_app as cip_app
    from app.ai_notebook import create_app as ain_app
    from app.data_modeller import create_app as dm_app
    from app.data_platform import create_broker_app
    from app.dataspace_ready import create_app as dataspace_app
    from app.federated_learning import create_app as fl_app
    from app.identity import create_app as identity_app
    from app.integrated_environment import create_app as ie_app
    from app.marketplace import create_app as marketplace_app
    from app.participate import create_app as participate_app
    from app.play_visualise import create_app as pv_app
    from app.ucs import create_app as ucs_app

    entities_by_tenant, provenance = _load_batches()
    ucs_processes = json.loads((FIXTURES / "ucs-processes.json").read_text())
    temporal = _read_json(FIXTURES / "dp-temporal.jsonld")
    recipes = _read_json(FIXTURES / "recipes.json") or {}
    participate_seed = _read_json(FIXTURES / "participate-seed.json") or {"proposals": [], "meetings": []}
    ground = load_ground(FIXTURES)

    offers: list[dict] = []
    offers_dir = REPO / "nldt" / "data" / "dataspace" / "offers"
    if offers_dir.exists():
        for path in sorted(offers_dir.glob("*.json")):
            offers.append(json.loads(path.read_text()))

    lake_root = REPO / "nldt" / "data" / "lake"
    inventory_path = REPO / "nldt" / "data" / "lake-inventory.json"

    def _schemas() -> dict:
        out = {}
        for path in sorted((REPO / "nldt" / "schemas").glob("*.json")):
            try:
                out[path.stem] = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
        return out

    solutions_ie = [{"name": name, "port": PORTS[name], "status": "simulated"} for name in
                    ("identity", "broker", "pv", "ucs", "marketplace", "dataspace",
                     "algorithms", "participate", "fl", "ain", "dm", "cip")]

    apps: dict[str, "FastAPI"] = {
        "identity": identity_app(),
        "broker": create_broker_app(
            entities_by_tenant=entities_by_tenant,
            provenance_by_tenant=provenance,
            include_proxy=True,
            include_trino=True,
            temporal=temporal,
        ),
        "pv": pv_app(),
        "ucs": ucs_app(ucs_processes, recipes=recipes, ground=ground),
        "marketplace": marketplace_app(),
    }
    if eubd:
        apps["eubd"] = create_broker_app(
            entities_by_tenant={"eubd": _eubd_batch()},
            provenance_by_tenant={"eubd": "toolbox-sim/data-platform; fixture=eubd-buildings; source=exposure.entities"},
        )
    if full:
        apps["dataspace"] = dataspace_app(offers, lake_root=lake_root)
        apps["algorithms"] = algorithms_app(ground)
        apps["participate"] = participate_app(participate_seed)
        apps["fl"] = fl_app(ground.peilen)
        apps["ain"] = ain_app(lake_root=lake_root / "nldt-poc-lake")
        apps["dm"] = dm_app(_schemas())
        apps["ie"] = ie_app(solutions_ie, inventory_path=inventory_path)
        apps["cip"] = cip_app()
    return apps


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", action="store_true", help="start ook de EUBD-feed op 9196")
    parser.add_argument("--full", action="store_true", help="start ook de catalogus-apps op 9197–9204")
    args = parser.parse_args(argv)

    apps = build_apps(full=args.full, eubd=args.eubd)
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

Let op: `build_apps()` en `main()` moeten exact deze vorm hebben; de server-tests roepen `build_apps` rechtstreeks aan zonder uvicorn.

In `toolbox-sim/run_sim.sh` — vlaggen doorgeven (lees het bestand; pas de aanroep van `app.server` aan naar):

```bash
exec ../nldt/.venv/bin/python -m app.server "$@"
```

zodat `./run_sim.sh --full --eubd` gewoon doorkomt (als het script al `"$@"` doorgeeft is dit een no-op; verifieer dat).

- [ ] **Step 4: Verifieer groen (boot + alles)**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_server_boot.py tests/test_full_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/app/server.py toolbox-sim/run_sim.sh toolbox-sim/tests/test_server_boot.py
git commit -m "feat(toolbox-sim): build_apps()+--full — catalogus-apps op 9197–9204"
```

---

### Taak 12: EDC-connector `negotiate_and_transfer` + model-run/process handlers (nldt-kant)

**Files:**
- Modify: `nldt/services/adapters/dataspace_connector.py` (na `http_register_offer`)
- Modify: `nldt/services/process_adapter/handlers.py` (aanvullen)
- Create: `nldt/tests/test_full_catalogue_adapters.py`
- Test: `toolbox-sim/tests/test_adapters_live.py` (aanvullen)

**Interfaces:**
- Consumes: taak 7 (EDC-stub op 9197), taak 6 (UCS-model-executie), env `NLDT_EDC_MANAGEMENT_URL` (bestaand in de connector).
- Produces: `dataspace_connector.negotiate_and_transfer(offer_uid: str) -> dict` (keys: `backend`, `negotiationState`, `transferState`, `destination`, `offerUid`); process handlers geregistreerd voor de 7 `MODEL_IDS`. Taak 15 (docs) verwijst hiernaar.

- [ ] **Step 1: Schrijf de falende live tests**

Nieuw bestand `nldt/tests/test_full_catalogue_adapters.py`:

```python
# nldt/tests/test_full_catalogue_adapters.py
"""Full-catalogus adaptertests: draaien tegen een gestarte toolbox-sim (--full)."""
import os
from pathlib import Path

import pytest

SIM_ENV = Path(__file__).resolve().parents[2] / "toolbox-sim" / ".env.sim"

if SIM_ENV.exists():
    for line in SIM_ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)

os.environ.setdefault("NLDT_EDC_MANAGEMENT_URL", "http://127.0.0.1:9197")

from services.adapters import dataspace_connector  # noqa: E402
from services.process_adapter.router import UCSAdapter  # noqa: E402

MODEL_IDS = [
    "neighbourhood-energy-demand", "building-environmental-footprint", "renovation-strategies",
    "urban-planning-vulnerability", "urban-mobility", "pollution-propagation", "police-routing",
]


@pytest.mark.skipif(not os.environ.get("NLDT_FULL_SIM"), reason="start de sim met --full en NLDT_FULL_SIM=1")
def test_edc_negotiate_and_transfer_live():
    offers = dataspace_connector.list_offers()
    offer_uid = offers[0]["uid"]
    result = dataspace_connector.negotiate_and_transfer(offer_uid)
    assert result["backend"] == "http"
    assert result["negotiationState"] == "CONFIRMED"
    assert result["transferState"] == "COMPLETED"
    assert result["offerUid"] == offer_uid


@pytest.mark.skipif(not os.environ.get("NLDT_FULL_SIM"), reason="start de sim met --full en NLDT_FULL_SIM=1")
@pytest.mark.parametrize("process_id", MODEL_IDS)
def test_model_processes_via_ucs_adapter(process_id):
    adapter = UCSAdapter()
    inputs = {"intensity_kwh_per_m2_year": 10.0} if "energy" in process_id else {}
    if "footprint" in process_id:
        inputs = {"carbon_kg_per_m2": 200.0}
    outputs = adapter.execute(process_id, inputs)
    assert outputs["model"] == process_id
    assert outputs["deterministic"] is True
```

En in `toolbox-sim/tests/test_adapters_live.py`:

```python
def test_edc_live_flow(live_sim):
    import os

    from services.adapters import dataspace_connector

    os.environ.setdefault("NLDT_EDC_MANAGEMENT_URL", "http://127.0.0.1:9197")
    offers = dataspace_connector.list_offers()
    if not offers:  # zonder lake-offers in de repo:Fixture-pad afdwingen
        pytest.skip("geen offers in nldt/data/dataspace/offers")
    result = dataspace_connector.negotiate_and_transfer(offers[0]["uid"])
    assert result["transferState"] == "COMPLETED"
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_adapters_live.py -k edc -v`
Expected: FAIL (`AttributeError: ... no attribute 'negotiate_and_transfer'`)

- [ ] **Step 3: Implementeer**

In `nldt/services/adapters/dataspace_connector.py`, na `http_register_offer`:

```python
def negotiate_and_transfer(offer_uid: str) -> dict[str, Any]:
    """Volledige EDC-flow tegen een Management-API-endpoint:
    catalog → contractnegotiation (REQUESTED→CONFIRMED) → transfer (→COMPLETED)."""
    base = (os.environ.get("NLDT_EDC_MANAGEMENT_URL") or "").rstrip("/")
    if not base:
        return {"backend": "http", "status": "mock_only_no_url", "offerUid": offer_uid}

    import httpx

    with httpx.Client(timeout=30.0) as client:
        catalog = client.post(f"{base}/v2/catalog/request", json={}).json()
        offers = {o["uid"]: o for o in catalog.get("offers", [])}
        if offer_uid not in offers:
            return {"backend": "http", "status": "offer_not_found", "offerUid": offer_uid}
        cn = client.post(f"{base}/v2/contractnegotiations", json={"offerUid": offer_uid}).json()
        negotiation = client.get(f"{base}/v2/contractnegotiations/{cn['id']}").json()
        tp = client.post(
            f"{base}/v2/transferprocesses",
            json={"negotiationId": cn["id"], "offerUid": offer_uid},
        ).json()
        transfer = client.get(f"{base}/v2/transferprocesses/{tp['id']}").json()
        return {
            "backend": "http",
            "offerUid": offer_uid,
            "negotiationState": negotiation.get("state"),
            "transferState": transfer.get("state"),
            "destination": transfer.get("destination"),
        }
```

In `nldt/services/process_adapter/handlers.py`: voeg bovenaan een constant lijstje toe en registreer de 7 process_ids in de bestaande handler-registry (volg het bestaande registratiepatroon in dat bestand; de handler hoeft niets te doen behalve bestaan — de UCSAdapter stuurt `processId` door en de sim voert uit):

```python
FULL_CATALOGUE_MODEL_PROCESSES = frozenset({
    "neighbourhood-energy-demand",
    "building-environmental-footprint",
    "renovation-strategies",
    "urban-planning-vulnerability",
    "urban-mobility",
    "pollution-propagation",
    "police-routing",
})
```

en neem deze set op waar de bestaande handler-registry zijn bekende process_ids registreert (zelfde vorm als de bestaande entries; bij execute: `processId` doorgaan naar `UCSAdapter`, geen local fallback nodig omdat de sim antwoordt; behoud de bestaande `execute_local`-fallback).

- [ ] **Step 4: Verifieer groen**

Run: start de sim met `cd toolbox-sim && ../nldt/.venv/bin/python -m app.server --full &` en draai:
`cd toolbox-sim && NLDT_FULL_SIM=1 ../nldt/.venv/bin/python -m pytest tests/test_adapters_live.py -k edc -v` en `cd nldt && NLDT_FULL_SIM=1 .venv/bin/python -m pytest tests/test_full_catalogue_adapters.py -v`; kill de sim daarna.
Expected: PASS (met `NLDT_FULL_SIM=1`; zonder die env skippen de nieuwe tests netjes)

- [ ] **Step 5: Commit**

```bash
git add nldt/services/adapters/dataspace_connector.py nldt/services/process_adapter/handlers.py nldt/tests/test_full_catalogue_adapters.py toolbox-sim/tests/test_adapters_live.py
git commit -m "feat(nldt): EDC negotiate_and_transfer + 7 model-process handlers (live tegen sim --full)"
```

---

### Taak 13: catalogue.json 20/20 + README + design-addendum

**Files:**
- Modify: `toolbox-sim/catalogue.json`
- Modify: `toolbox-sim/README.md`
- Modify: `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md` (addendum onderaan)
- Test: `toolbox-sim/tests/test_catalogue.py` (aanvullen)

**Interfaces:**
- Consumes: alles uit taak 1–12.
- Produces: catalogue-status `simulated` voor alle 14 nieuwe; bewijsvelden wijzen naar module + testpaden.

- [ ] **Step 1: Schrijf de falende test**

Aanvullen in `toolbox-sim/tests/test_catalogue.py`:

```python
def test_catalogue_volledig_gedekt():
    import json
    from pathlib import Path

    catalogue = json.loads((Path(__file__).resolve().parents[1] / "catalogue.json").read_text())
    items = catalogue if isinstance(catalogue, list) else catalogue.get("solutions", [])
    assert len(items) == 20
    statuses = {item["status"] for item in items}
    assert "skipped" not in statuses
    assert statuses <= {"simulated", "consumed-as-data"}
```

- [ ] **Step 2: Verifieer falen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_catalogue.py -v`
Expected: FAIL (`assert 'skipped' not in statuses`)

- [ ] **Step 3: Werk catalogue.json, README en design-addendum bij**

In `toolbox-sim/catalogue.json`: zet voor elk van de 14 items `"status": "simulated"` en vul `"evidence"` met module- en testpaden, bijvoorbeeld voor de algoritmmodellen:

```json
{
  "name": "Neighbourhood Energy Demand Forecasting",
  "status": "simulated",
  "evidence": "toolbox-sim/app/algorithms.py#neighbourhood-energy-demand; tests: toolbox-sim/tests/test_full_catalogue.py",
  "grounding": "areas: eubd-buildings fixture (exposure.entities); intensiteit = aanvrager-parameter; geen verzonnen waarden"
}
```

Vergelijkbaar voor de overige 13 (EU LDT Identity Management, Data Platform, Play & Visualise, Use Cases & Scenarios, Marketplace, Integrated Environment, AI Notebook, City Innovation Planner, Data Modeller, Data Space Ready, Federated Learning, Participate; EU Building Database blijft `consumed-as-data`; Urban Mobility, Pollution Propagation, Building Environmental Footprint, Renovation Strategies, Urban Planning Vulnerability Mitigation, Police Routing Tool → `simulated` met `grounding`-notitie; Neighbourhood Energy Demand Forecasting zoals hierboven).

In `toolbox-sim/README.md`: vervang de poorttabel door de volledige tabel (9191–9204 met `--full`), documenteer `--full` en de NLDT_FULL_SIM-adaptertests, en vervang de kopregel "zes oplossingen" door "alle twintig catalogus-oplossingen".

In `docs/superpowers/specs/2026-10-04-toolbox-sim-design.md`: voeg onderaan een addendum toe:

```markdown
## Addendum 2026-10-14: volledige catalogus

De non-goals in §9 ("geen NGSI-LD subscriptions/temporal/registrations, geen
live EDC") komen te vervallen sinds de catalogus-uitbreiding
(`2026-10-14-toolbox-sim-full-catalogue-design.md`): de broker ondersteunt
subscriptions/temporal/registrations en `dataspace_ready.py` simuleert de
EDC-flow. Blijvende non-goals: geen echte product-UI's, geen zware
(GPU/TB-klasse) modellen, geen echte netwerkaflevering van notificaties.
```

- [ ] **Step 4: Verifieer groen**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_catalogue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/catalogue.json toolbox-sim/README.md docs/superpowers/specs/2026-10-04-toolbox-sim-design.md toolbox-sim/tests/test_catalogue.py
git commit -m "docs(toolbox-sim): catalogue 20/20 gedekt, README poorten 9191–9204, design-addendum"
```

---

### Taak 14: E2E-smoke + volledige testrun

**Files:**
- Modify: `toolbox-sim/tests/test_e2e_smoke.py` (aanvullen)

**Interfaces:**
- Consumes: `build_apps(full=True)` (taak 11).
- Produces: één smoke-test die per nieuwe app ten minste één geslaagde geauthenticeerde request aantont.

- [ ] **Step 1: Schrijf de falende smoke-test**

Aanvullen in `toolbox-sim/tests/test_e2e_smoke.py`:

```python
def test_full_catalogue_smoke_per_app():
    from fastapi.testclient import TestClient

    from app.server import build_apps

    auth = {"Authorization": "Bearer sim-toolbox-token"}
    apps = build_apps(full=True, eubd=False)
    # één request per nieuwe app (health-checks zitten al in test_build_apps_full)
    probes = {
        "dataspace": lambda c: c.post("/v2/catalog/request", headers=auth, json={}),
        "algorithms": lambda c: c.get("/models", headers=auth),
        "participate": lambda c: c.get("/api/proposals", headers=auth),
        "fl": lambda c: c.post("/rounds", headers=auth, json={"name": "smoke"}),
        "ain": lambda c: c.post("/notebooks", headers=auth, json={"name": "smoke"}),
        "dm": lambda c: c.get("/models", headers=auth),
        "ie": lambda c: c.get("/solutions", headers=auth),
        "cip": lambda c: c.get("/scenarios", headers=auth),
    }
    for name, probe in probes.items():
        response = probe(TestClient(apps[name]))
        assert response.status_code == 200, f"{name}: {response.status_code} {response.text[:120]}"
        assert response.headers.get("x-sim-provenance", "").startswith("toolbox-sim/"), name
```

- [ ] **Step 2: Verifieer falen (ontbrekende provenance-header per nieuwe app)**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests/test_e2e_smoke.py -k full_catalogue -v`
Expected: PASS mits taak 2–11 de headers zetten; als een app de header mist, failt deze test — fix dan de betreffende `add_provenance`-aanroep.

- [ ] **Step 3: Volledige testrun beide suites**

Run: `cd toolbox-sim && ../nldt/.venv/bin/python -m pytest tests -q` en `cd nldt && .venv/bin/python -m pytest tests -q`
Expected: alle PASS (incl. bestaande tests — zonder `--full` is gedrag ongewijzigd)

- [ ] **Step 4: Handmatige run-check**

Run: `cd toolbox-sim && ./run_sim.sh --full &` → `curl -s -H "Authorization: Bearer sim-toolbox-token" http://127.0.0.1:9198/models | head -c 200` → `curl -s http://127.0.0.1:9193/ui/map | head -c 120` → kill.
Expected: JSON met 7 modellen; HTML met Leaflet.

- [ ] **Step 5: Commit**

```bash
git add toolbox-sim/tests/test_e2e_smoke.py
git commit -m "test(toolbox-sim): e2e-smoke over alle catalogus-apps (--full)"
```

---

## Self-review notities (bij oplevering van het plan)

- Spec-dekking: taak 1 ↔ spec (fixtures/adapter-grondslag), 2–3 ↔ Data Platform + adapter, 4 ↔ P&V + map_url, 5–6 ↔ algoritmemodellen (grondslag/503-regel), 6 ↔ UCS-authoring, 7 ↔ DSR + state-machines, 8–10 ↔ zes overige oplossingen, 11 ↔ server/--full, 12 ↔ connector + handlers, 13 ↔ catalogue/README/addendum, 14 ↔ teststrategie/e2e.
- Type-consistentie: `create_broker_app(..., temporal=)`, `create_app(processes, recipes=, ground=)`, `dataspace_ready.create_app(offers, lake_root=)`, `negotiate_and_transfer(offer_uid)`, `MODEL_IDS`/`SYNTHETIC`/`Ground`/`run_model` — consistent gebruikt tussen taken.
- Bewuste afwijkingen van de spec (gedocumenteerd in Global Constraints): broker-pad `/ngsi-ld/v1/...` in plaats van `/cb/...`; `fixtures/recipes.json` in plaats van directory; sim-klok is vaste basis + teller.
- Extra afwijking (taak 5): het renovatiemodel prioriteert op echte tegeloppervlak uit de eubd-fixture in plaats van op `attributes.legacy_2023_01`-sommen — die sommen staan in de PostGIS `assets`-tabel en zitten níet in de entiteit-fixture; pakketkosten blijven bewust buiten beeld (geen verzonnen waarden).
