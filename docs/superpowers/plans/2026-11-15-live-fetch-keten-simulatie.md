# Live fetch-keten-simulatie — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een live server + pagina in `nldt/simulation/live/` die de fetch-keten (catalogus → DSO-kb → agrest/ArcGIS → NGSI-LD) tijdens het kijken uitvoert, waarbij elke stap een échte MCP `call_tool` is die naar de UI streamt (SSE) met kaartweergave.

**Architecture:** Eén FastAPI-app mount de bestaande MCP-servers (`data`, `dso`, `catalog`, `poc`) via `build_mcp_http_app`; een gescripte agent doet elke stap via een echte MCP-client over streamable-http loopback; één nieuw proces `fetch-geo-layer` (+ MCP-tool `fetch_geo_layer`) ontsluit `poc/pipeline/geodata.fetch_layer`. Spec: [docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md](../specs/2026-11-15-live-fetch-keten-simulatie-design.md).

**Tech Stack:** Python 3.14 (venv `nldt/.venv`), FastAPI + uvicorn (in `nldt/requirements.txt`), `mcp` SDK (server: `MCPServer`; client: `streamable_http_client` + `ClientSession` — naamgebruik met onderstrepingjes, géén `streamablehttp_client`), plain HTML/JS/SVG (geen build-step, geen externe deps).

## Global Constraints

- Tests draaien met `cd nldt && .venv/bin/python -m pytest ...`; géén netwerk in tests: agrest/ArcGIS-stappen draaien uit de gecommitte cache-twins in `poc/data/cache/` (74 geojson-files in git), NGSI-LD via adapter-mock (`NLDT_DATA_PLATFORM_MOCK` default true; module-attrs `NGSI_LD_URL`/`DATA_PLATFORM_URL` leeg).
- Eventnamen exact: `step_started`, `tool_result`, `layer_ready`, `run_done`, `error` (SSE-regels `event: <naam>\ndata: <json>\n\n`).
- Mount-paden: `/mcp/data`, `/mcp/dso`, `/mcp/catalog`, `/mcp/poc`; de SDK-app serveert `POST {mount}/mcp`.
- Poort default `8095` (env `NLDT_LIVE_SIM_PORT`), host default `127.0.0.1` (env `NLDT_LIVE_SIM_HOST`).
- `server.py` zet `os.environ.setdefault("NLDT_OFFLINE", "1")` — poc- én dso-tools executeren dan in-process via de job-store (zelfde switch, geverifieerd in beide servers).
- Toolnamen exact: `catalog.list_poc_capabilities` (geen args), `dso.dso_kb_overview` (geen args), `poc.fetch_geo_layer` (`source_id`, `bbox?`, `refresh?`, `cache_dir?`), `data.list_entities` (`entity_type`, `scope?`, `geoproperty?`), `data.entities_to_geojson` (`entity_type`, `scope?`).
- Elke scriptstap = precies één tool call; de agent heeft geen condities of LLM.
- Commits per task; commit alleen de bestanden van die task (de werkmap heeft meer lopende wijzigingen).
- Deviatie t.o.v. spec, bewust: spec-tabel rij 5 ("list_entities → entities_to_geojson") wordt in het script **twee** stappen (6 stappen totaal), omdat elke stap precies één call is. `layer_ready` krijgt voor de NGSI-laag het GeoJSON **inline** (`geojson`-veld) — `data.entities_to_geojson` schrijft geen cache-twin; `/api/layers/{source_id}` blijft een dumb file-server voor de ArcGIS-twins.

---

### Task 1: Proces `fetch-geo-layer` in de process-adapter

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (dict `POC_PROCESS_DEFINITIONS` op :138, executor boven `EXECUTORS` op :1187, entry in `EXECUTORS`)
- Test: `nldt/tests/test_live_sim_fetch_geo_layer.py` (nieuw)

**Interfaces:**
- Consumes: `poc/pipeline/geodata.fetch_layer(source_id, bbox=None, *, refresh=False, sources=None, cache_dir=None, ...)` (bestaand); `POC_ROOT` (bestaande constante in poc_handlers).
- Produces: `execute_poc_process("fetch-geo-layer", {"source_id": str, "bbox"?: str, "refresh"?: bool, "cache_dir"?: str}) -> {"summary": {sourceId, title, protocol, entityType, dataPlatformMock, featureCount, pages, fetchedAt, serviceUrl}}`. Task 2 en de live-server bouwen hierop.

- [ ] **Step 1: Write the failing test**

```python
"""fetch-geo-layer proces: cache-first samenvatting, offline (geen netwerk).

agrest/ArcGIS-stappen draaien uit de gecommitte cache-twins; de NGSI-stap
gebruikt een gestubde data-platform adapter (patroon: poc/tests/test_geodata_ngsi.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
POC_ROOT = NLDT_ROOT.parent / "poc"
for _p in (str(NLDT_ROOT), str(POC_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def test_fetch_geo_layer_cache_hit_uit_git_cache():
    out = execute_poc_process("fetch-geo-layer", {"source_id": "agrest-ov-gebied-windenergie"})
    s = out["summary"]
    assert s["sourceId"] == "agrest-ov-gebied-windenergie"
    assert s["featureCount"] == 44
    assert s["protocol"] is None  # ArcGIS-dialect zet geen protocol-veld
    assert s["fetchedAt"]  # provenance aanwezig uit de cache


def test_fetch_geo_layer_ngsi_mock(tmp_path, monkeypatch):
    from pipeline import geodata

    class _StubDP:
        MOCK = True

        def list_entities(self, *, entity_type, limit=100, **kwargs):
            return [
                {
                    "id": f"urn:ngsi-ld:{entity_type}:ut-001",
                    "type": entity_type,
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [5.12, 52.09]},
                    },
                    "NO2": {"type": "Property", "value": 12.5},
                }
            ]

    monkeypatch.setattr(geodata, "_load_data_platform", lambda: _StubDP())
    out = execute_poc_process(
        "fetch-geo-layer",
        {"source_id": "ngsi-ld-dpl-airquality", "cache_dir": str(tmp_path)},
    )
    s = out["summary"]
    assert s["protocol"] == "ngsi-ld"
    assert s["dataPlatformMock"] is True
    assert s["featureCount"] == 1
    assert (tmp_path / "ngsi-ld-dpl-airquality.4326.geojson").is_file()
    assert (tmp_path / "ngsi-ld-dpl-airquality.28992.geojson").is_file()


def test_fetch_geo_layer_ngsi_uri_afgewezen():
    try:
        execute_poc_process("fetch-geo-layer", {"source_id": "ngsi-ld://AirQualityObserved"})
    except ValueError as exc:
        assert "fetch-features" in str(exc)
    else:
        raise AssertionError("ngsi-ld:// URI moet worden afgewezen (gebruik fetch-features)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_fetch_geo_layer.py -v`
Expected: FAIL — `KeyError: 'fetch-geo-layer'` in `execute_poc_process`.

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/process_adapter/poc_handlers.py` — voeg toe in `POC_PROCESS_DEFINITIONS` (direct vóór de entry `"opportunity-map-run"`):

```python
    "fetch-geo-layer": {
        "id": "fetch-geo-layer",
        "title": "Fetch geo layer (PoC geodata)",
        "description": (
            "Haal één laag uit het PoC-bronnenregister via geodata.fetch_layer "
            "(ArcGIS/agrest-dialecten, cache-first) en geef een compacte "
            "samenvatting; de geometrie blijft in de cache-twins "
            "(<sourceId>.28992.geojson + .4326.geojson)."
        ),
        "version": "1.0.0",
        "keywords": ["poc-utrecht", "geodata", "fetch", "live-sim"],
        "inputs": {
            "source_id": {"title": "Source id", "schema": {"type": "string"}},
            "bbox": {
                "title": "BBOX xmin,ymin,xmax,ymax (EPSG:28992)",
                "schema": {"type": "string"},
                "required": False,
            },
            "refresh": {
                "title": "Cache negeren",
                "schema": {"type": "boolean", "default": False},
                "required": False,
            },
            "cache_dir": {
                "title": "Cache map (tests)",
                "schema": {"type": "string"},
                "required": False,
            },
        },
        "outputs": {
            "summary": {"title": "Laag-samenvatting", "schema": {"type": "object"}},
        },
    },
```

Voeg boven `EXECUTORS` de executor toe:

```python
def execute_fetch_geo_layer(inputs: dict[str, Any]) -> dict[str, Any]:
    """Eén PoC-geolaag ophalen via geodata.fetch_layer (cache-first, compact)."""
    source_id = inputs["source_id"]
    if str(source_id).startswith("ngsi-ld://"):
        raise ValueError("ngsi-ld:// URI-bronnen horen bij het fetch-features-proces")
    if str(POC_ROOT) not in sys.path:
        sys.path.insert(0, str(POC_ROOT))
    from pipeline import geodata

    cache_dir = inputs.get("cache_dir")
    fc = geodata.fetch_layer(
        source_id,
        bbox=inputs.get("bbox"),
        refresh=bool(inputs.get("refresh")),
        cache_dir=Path(cache_dir) if cache_dir else None,
    )
    p = fc.get("properties") or {}
    return {
        "summary": {
            "sourceId": p.get("sourceId"),
            "title": p.get("title"),
            "protocol": p.get("protocol"),
            "entityType": p.get("entityType"),
            "dataPlatformMock": p.get("dataPlatformMock"),
            "featureCount": p.get("featureCount"),
            "pages": p.get("pages"),
            "fetchedAt": p.get("fetchedAt"),
            "serviceUrl": p.get("serviceUrl"),
        }
    }
```

En in `EXECUTORS` (bovenaan, vóór `"world-scene-build"`):

```python
    "fetch-geo-layer": execute_fetch_geo_layer,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_fetch_geo_layer.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py nldt/tests/test_live_sim_fetch_geo_layer.py
git commit -m "feat(live-sim): proces fetch-geo-layer — geodata.fetch_layer via process-adapter (cache-first, compacte samenvatting, NGSI-mock via stub)"
```

---

### Task 2: MCP-tool `fetch_geo_layer` in poc-server

**Files:**
- Modify: `nldt/services/mcp_servers/poc_tools.py` (dict `POC_TOOLS`)
- Modify: `nldt/services/mcp_servers/poc_server.py` (nieuwe `@mcp.tool` bij de overige tools)
- Test: `nldt/tests/test_live_sim_poc_tool.py` (nieuw)

**Interfaces:**
- Consumes: Task 1-proces `fetch-geo-layer`; `_run_poc_tool(tool_name, arguments)` (bestaand in poc_server; met `NLDT_OFFLINE=1` in-process via job-store, status `"successful"`).
- Produces: MCP-tool `fetch_geo_layer(source_id, bbox=None, refresh=False, cache_dir=None) -> str` (JSON in het poc-server-patroon `{tool, processId, jobId, status, outputs, prov}`). De agent (Task 3) en live-server roepen deze via MCP aan.

- [ ] **Step 1: Write the failing test**

```python
"""MCP-tool fetch_geo_layer via _run_poc_tool, offline (NLDT_OFFLINE=1)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))


def test_fetch_geo_layer_tool_offline_cache(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.mcp_servers import poc_server

    raw = asyncio.run(
        poc_server._run_poc_tool("fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
    )
    payload = json.loads(raw)
    assert payload["tool"] == "fetch_geo_layer"
    assert payload["processId"] == "fetch-geo-layer"
    assert payload["status"] == "successful"
    assert payload["outputs"]["summary"]["featureCount"] == 44
    assert payload["prov"]["startedAtTime"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_poc_tool.py -v`
Expected: FAIL — `ValueError: Unknown tool: fetch_geo_layer`.

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/mcp_servers/poc_tools.py`, voeg toe aan `POC_TOOLS` (onderaan, na `run_minigim_gebiedscheck`):

```python
    "fetch_geo_layer": {
        "process_id": "fetch-geo-layer",
        "description": "Haal één PoC-geolaag op (ArcGIS/agrest, cache-first); compacte samenvatting",
    },
```

In `nldt/services/mcp_servers/poc_server.py`, voeg bij de overige tools toe (na `run_opportunity_map`):

```python
@mcp.tool(name="fetch_geo_layer", description=POC_TOOLS["fetch_geo_layer"]["description"])
async def fetch_geo_layer(
    source_id: str,
    bbox: str | None = None,
    refresh: bool = False,
    cache_dir: str | None = None,
) -> str:
    return await _run_poc_tool(
        "fetch_geo_layer",
        {"source_id": source_id, "bbox": bbox, "refresh": refresh, "cache_dir": cache_dir},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_poc_tool.py -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/mcp_servers/poc_tools.py nldt/services/mcp_servers/poc_server.py nldt/tests/test_live_sim_poc_tool.py
git commit -m "feat(live-sim): MCP-tool fetch_geo_layer in poc-server (poc-server-patroon: tool → proces → job-store)"
```

---

### Task 3: Gescripte agent + stappenlijst (`agent.py`, `fetch_script.py`)

**Files:**
- Create: `nldt/simulation/live/fetch_script.py`
- Create: `nldt/simulation/live/agent.py`
- Create: `nldt/tests/live_sim_fakes.py` (gedeelde FakeMcpClient; `nldt/tests` is géén package, maar pytest zet de map op sys.path, dus sibling-import werkt)
- Test: `nldt/tests/test_live_sim_agent.py` (nieuw)

**Interfaces:**
- Consumes: tool-resultaten als JSON-**strings** (wat `McpLoopbackClient.call_tool` in Task 4 teruggeeft: eerste tekstblok van het MCP-resultaat).
- Produces (Task 5 gebruikt dit):
  - `fetch_script.STAPPEN: list[dict]` — stappen met keys `label`, `server`, `tool`, `args`, `samenvatting(raw:str)->str`, optioneel `laag: {"source_id": str} | {"inline": True, "source_id": str}` + `laagtype`.
  - `agent.ScriptedAgent(client, stappen=None)` met `async run(emit) -> dict`; `emit(event: str, data: dict)`.
  - `agent.SessionStore` met `start(agent_factory) -> str` (werpt `RuntimeError` als er al een sessie draait), `stream(sid)` (async generator `(event, data)` tot sluiting; `KeyError` bij onbekende sid).

- [ ] **Step 1: Write the failing test (+ gedeelde fake)**

Eerst de gedeelde fake — `nldt/tests/live_sim_fakes.py`:

```python
"""Gedeelde FakeMcpClient voor de live-sim tests (sibling-import via pytest sys.path).

Tool-resultaten als JSON-strings, vormgetrouw aan de echte servers.
"""

from __future__ import annotations

import json


class FakeMcpClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on  # (server, tool) die RuntimeError werpt

    async def call_tool(self, server: str, tool: str, args: dict) -> str:
        self.calls.append((server, tool, args))
        if self.fail_on and (server, tool) == self.fail_on:
            raise RuntimeError("broker onbereikbaar")
        if tool == "fetch_geo_layer":
            return json.dumps(
                {
                    "tool": "fetch_geo_layer",
                    "processId": "fetch-geo-layer",
                    "status": "successful",
                    "outputs": {
                        "summary": {
                            "sourceId": args["source_id"],
                            "title": "laag",
                            "featureCount": 44,
                        }
                    },
                }
            )
        if tool == "list_entities":
            return json.dumps(
                [
                    {
                        "id": "urn:ngsi-ld:AirQualityObserved:mock-001",
                        "type": "AirQualityObserved",
                        "mock": True,
                    }
                ]
            )
        if tool == "entities_to_geojson":
            return json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": "urn:ngsi-ld:AirQualityObserved:mock-001",
                            "properties": {
                                "type": "AirQualityObserved",
                                "source": "ngsi-ld",
                                "mock": True,
                            },
                            "geometry": {"type": "Point", "coordinates": [5.12, 52.09]},
                        }
                    ],
                }
            )
        return json.dumps(
            {"capabilities": ["opportunity-map-run"], "instrumenten": ["utrecht-domplein"]}
        )
```

Daarna de test zelf — `nldt/tests/test_live_sim_agent.py`:

```python
"""Gescripte agent: vaste stappen → deterministische event-volgorde (FakeMcpClient)."""

from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402
import fetch_script  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402 (sibling in tests/, op sys.path via pytest)


def test_script_heeft_zes_stappen_drie_lagen():
    assert len(fetch_script.STAPPEN) == 6
    met_laag = [s for s in fetch_script.STAPPEN if "laag" in s]
    assert len(met_laag) == 3
    inline = [s for s in met_laag if s["laag"].get("inline")]
    assert len(inline) == 1 and inline[0]["laag"]["source_id"] == "ngsi-ld-dpl-airquality"
    servers = {(s["server"], s["tool"]) for s in fetch_script.STAPPEN}
    assert ("catalog", "list_poc_capabilities") in servers
    assert ("dso", "dso_kb_overview") in servers
    assert ("data", "list_entities") in servers
    assert ("data", "entities_to_geojson") in servers


def test_agent_event_volgorde_deterministisch():
    events = []

    def emit(ev, data):
        events.append((ev, data))

    fake = FakeMcpClient()
    result = agent.run_sync(agent.ScriptedAgent(fake), emit)
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 6
    assert namen.count("tool_result") == 6
    assert namen.count("layer_ready") == 3
    assert namen[-1] == "run_done"
    assert result["status"] == "ok"
    # elke stap exact één call, in scriptvolgorde
    assert [c[:2] for c in fake.calls] == [(s["server"], s["tool"]) for s in fetch_script.STAPPEN]
    # inline NGSI-laag draagt het GeoJSON in het event
    ngsi_laag = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "punten"]
    assert ngsi_laag and ngsi_laag[0]["geojson"]["type"] == "FeatureCollection"
    assert ngsi_laag[0]["source_id"] == "ngsi-ld-dpl-airquality"
    # bestand-backed lagen verwijzen naar /api/layers/<source_id>
    zone_lagen = [d for ev, d in events if ev == "layer_ready" and d.get("laagtype") == "zone"]
    assert {z["source_id"] for z in zone_lagen} == {
        "agrest-ov-gebied-windenergie",
        "arcgis-et-wind-gebieden",
    }


def test_agent_stopt_met_error_event():
    events = []

    def emit(ev, data):
        events.append((ev, data))

    fake = FakeMcpClient(fail_on=("poc", "fetch_geo_layer"))
    result = agent.run_sync(agent.ScriptedAgent(fake), emit)
    namen = [ev for ev, _ in events]
    assert "error" in namen
    assert "run_done" not in namen
    assert result["status"] == "error"
    err = [d for ev, d in events if ev == "error"][0]
    assert err["label"] == "Inclusion-zone wind (agrest)"
    # stappen na de fout worden niet meer uitgevoerd
    assert len(fake.calls) == 3


def test_session_store_stream_sluit_en_bezet():
    import asyncio

    async def scenario():
        store = agent.SessionStore()
        sid = store.start(lambda: ScriptedAgentMetFake())
        verzameld = []
        async for ev, data in store.stream(sid):
            verzameld.append((ev, data))
        assert verzameld[-1][0] == "run_done"

        # na afloop is een nieuwe sessie weer toegestaan…
        sid2 = store.start(lambda: ScriptedAgentMetFake())
        async for ev, _ in store.stream(sid2):
            pass

        # …maar zolang er één actief is, is een tweede geweigerd
        sid3 = store.start(lambda: ScriptedAgentMetFake())
        try:
            store.start(lambda: None)
        except RuntimeError:
            pass
        else:
            raise AssertionError("tweede gelijktijdige sessie moet worden geweigerd")
        async for ev, _ in store.stream(sid3):
            pass

    asyncio.run(scenario())


class ScriptedAgentMetFake(agent.ScriptedAgent):
    def __init__(self):
        super().__init__(FakeMcpClient())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent'`.

- [ ] **Step 3: Write minimal implementation**

`nldt/simulation/live/fetch_script.py`:

```python
"""Stappenlijst fetch-keten v1 — data, geen vertakking.

Spec: docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md.
Elke stap is precies één MCP-toolcall; samenvattingen zijn pure functies van
het ruwe tool-resultaat (JSON-string).
"""

from __future__ import annotations

import json
from typing import Any


def _count_top_level(raw: str) -> str:
    data = json.loads(raw)
    if isinstance(data, list):
        return f"{len(data)} items"
    if isinstance(data, dict):
        return f"{len(data)} sleutels"
    return "ok"


def _sum_poc_tool(raw: str) -> str:
    payload = json.loads(raw)  # poc-server-patroon {tool, processId, status, outputs}
    s = (payload.get("outputs") or {}).get("summary") or {}
    return f"{s.get('featureCount')} features · {s.get('title')}"


def _sum_entities(raw: str) -> str:
    ents = json.loads(raw)
    mock = any(isinstance(e, dict) and e.get("mock") for e in ents)
    return f"{len(ents)} entities{' (mock)' if mock else ''}"


def _sum_fc(raw: str) -> str:
    fc = json.loads(raw)
    return f"{len(fc.get('features') or [])} features"


STAPPEN: list[dict[str, Any]] = [
    {
        "label": "Wat is beschikbaar?",
        "server": "catalog",
        "tool": "list_poc_capabilities",
        "args": {},
        "samenvatting": _count_top_level,
    },
    {
        "label": "Regels-instrumenten in het gebied",
        "server": "dso",
        "tool": "dso_kb_overview",
        "args": {},
        "samenvatting": _count_top_level,
    },
    {
        "label": "Inclusion-zone wind (agrest)",
        "server": "poc",
        "tool": "fetch_geo_layer",
        "args": {"source_id": "agrest-ov-gebied-windenergie"},
        "laag": {"source_id": "agrest-ov-gebied-windenergie", "laagtype": "zone"},
        "samenvatting": _sum_poc_tool,
    },
    {
        "label": "Kaartlaag wind (ArcGIS Online)",
        "server": "poc",
        "tool": "fetch_geo_layer",
        "args": {"source_id": "arcgis-et-wind-gebieden"},
        "laag": {"source_id": "arcgis-et-wind-gebieden", "laagtype": "zone"},
        "samenvatting": _sum_poc_tool,
    },
    {
        "label": "NGSI-LD entities (lucht)",
        "server": "data",
        "tool": "list_entities",
        "args": {"entity_type": "AirQualityObserved"},
        "samenvatting": _sum_entities,
    },
    {
        "label": "NGSI-LD → GeoJSON",
        "server": "data",
        "tool": "entities_to_geojson",
        "args": {"entity_type": "AirQualityObserved"},
        "laag": {"source_id": "ngsi-ld-dpl-airquality", "laagtype": "punten", "inline": True},
        "samenvatting": _sum_fc,
    },
]
```

`nldt/simulation/live/agent.py`:

```python
"""Gescripte agent: doorloopt STAPPEN, elke stap één echte MCP-toolcall.

emit(event, data) is de sink (SessionStore-queue in de server; list in tests).
Deterministisch: geen condities, geen LLM — "no invented numbers".
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Callable

from fetch_script import STAPPEN

Emit = Callable[[str, dict], None]


def _json_object(raw: str) -> Any:
    return json.loads(raw) if isinstance(raw, str) else raw


class ScriptedAgent:
    def __init__(self, client, stappen: list[dict[str, Any]] | None = None):
        self.client = client
        self.stappen = stappen if stappen is not None else STAPPEN

    async def run(self, emit: Emit) -> dict[str, Any]:
        per_stap: list[dict[str, Any]] = []
        for i, stap in enumerate(self.stappen):
            emit(
                "step_started",
                {
                    "index": i,
                    "label": stap["label"],
                    "server": stap["server"],
                    "tool": stap["tool"],
                    "args": stap["args"],
                },
            )
            t0 = time.perf_counter()
            try:
                raw = await self.client.call_tool(stap["server"], stap["tool"], stap["args"])
                duur_ms = int((time.perf_counter() - t0) * 1000)
                samenvatting = stap["samenvatting"](raw)
            except Exception as exc:  # stap faalt → run stopt (spec: foutafhandeling)
                duur_ms = int((time.perf_counter() - t0) * 1000)
                emit(
                    "tool_result",
                    {"index": i, "ok": False, "duration_ms": duur_ms, "summary": str(exc)[:300]},
                )
                emit("error", {"stap": i, "label": stap["label"], "melding": str(exc)[:300]})
                return {"status": "error", "stap": i, "per_stap": per_stap}
            emit(
                "tool_result",
                {"index": i, "ok": True, "duration_ms": duur_ms, "summary": samenvatting},
            )
            per_stap.append({"index": i, "ok": True})
            laag = stap.get("laag")
            if laag:
                event: dict[str, Any] = {"laagtype": laag["laagtype"], "source_id": laag["source_id"]}
                if laag.get("inline"):
                    event["geojson"] = _json_object(raw)
                emit("layer_ready", event)
        emit("run_done", {"per_stap": per_stap, "totaal": len(per_stap)})
        return {"status": "ok", "per_stap": per_stap}


def run_sync(agent_: ScriptedAgent, emit: Emit) -> dict[str, Any]:
    return asyncio.run(agent_.run(emit))


class SessionStore:
    """Eén actieve sessie; events via asyncio.Queue tot sluiting."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def start(self, agent_factory) -> str:
        if self._queues:
            raise RuntimeError("er draait al een sessie")
        sid = uuid.uuid4().hex[:12]
        q: asyncio.Queue = asyncio.Queue()
        self._queues[sid] = q
        asyncio.get_running_loop().create_task(self._run(sid, q, agent_factory))
        return sid

    async def _run(self, sid: str, q: asyncio.Queue, agent_factory) -> None:
        agent_ = agent_factory()
        try:
            await agent_.run(lambda ev, data: q.put_nowait((ev, data)))
        finally:
            q.put_nowait(("_close", None))

    async def stream(self, sid: str):
        q = self._queues.get(sid)
        if q is None:
            raise KeyError(sid)
        try:
            while True:
                ev, data = await q.get()
                if ev == "_close":
                    return
                yield ev, data
        finally:
            self._queues.pop(sid, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_agent.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/live/fetch_script.py nldt/simulation/live/agent.py nldt/tests/live_sim_fakes.py nldt/tests/test_live_sim_agent.py
git commit -m "feat(live-sim): gescripte agent + fetch-script — 6 stappen (catalog→dso→2×geo→ngsi×2), deterministische SSE-events, één actieve sessie"
```

---

### Task 4: MCP-loopback-client + server met mounts (`mcp_client.py`, `server.py`)

**Files:**
- Create: `nldt/simulation/live/mcp_client.py`
- Create: `nldt/simulation/live/server.py`
- Test: `nldt/tests/test_live_sim_server.py` (nieuw)

**Interfaces:**
- Consumes: `MCPServer`-objecten `mcp` uit `services/mcp_servers/{data,dso,catalog,poc}_server`; `build_mcp_http_app(server)` uit `services/mcp_servers/http_transport.py`; Tasks 1-2 (tool `fetch_geo_layer`); `geodata`-cache-twins in `poc/data/cache/`.
- Produces:
  - `mcp_client.McpLoopbackClient(base_url).call_tool(server, tool, args) -> str` (échte MCP over streamable-http; werpt `McpToolError`); gebruikt door Task 5/7.
  - `server.create_app(tool_client_factory=None) -> FastAPI` met mounts `/mcp/{data,dso,catalog,poc}`, `GET /api/layers/{source_id}` (4326-twin, `application/geo+json`, 404 bij afwezig), `GET /` (index.html uit Task 6). Task 5 breidt `create_app` uit met sessie-endpoints.
  - `server.main()` — uvicorn op `127.0.0.1:8095` (env-overrides).

- [ ] **Step 1: Write the failing test**

```python
"""Server-mounts + echte MCP-loopback-client + lagen-endpoint (real sockets, offline).

De server draait in-thread op een vrije poort; de client callingt over echt
HTTP tegen de mounts. NGSI-LD draait op de adapter-mock (module-attrs leeg).
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx
import pytest
import uvicorn

import server  # noqa: E402
from mcp_client import McpLoopbackClient  # noqa: E402


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)


def _vrije_poort() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def live_server(monkeypatch):
    from services.adapters import data_platform

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)

    port = _vrije_poort()
    config = uvicorn.Config(server.create_app(), host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if uv_server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("live-server startte niet")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=5)


def test_mcp_loopback_data_list_entities_mock(live_server):
    client = McpLoopbackClient(live_server)
    raw = asyncio_run(client.call_tool("data", "list_entities", {"entity_type": "AirQualityObserved"}))
    ents = json.loads(raw)
    assert isinstance(ents, list) and ents
    assert ents[0]["id"].startswith("urn:ngsi-ld:AirQualityObserved:")
    assert ents[0].get("mock") is True


def test_mcp_loopback_poc_fetch_geo_layer_cache(live_server):
    client = McpLoopbackClient(live_server)
    raw = asyncio_run(
        client.call_tool("poc", "fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
    )
    payload = json.loads(raw)
    assert payload["status"] == "successful"
    assert payload["outputs"]["summary"]["featureCount"] == 44


def test_layers_endpoint_dient_4326_twin(live_server):
    with httpx.Client(timeout=10.0) as http:
        resp = http.get(f"{live_server}/api/layers/agrest-ov-gebied-windenergie")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/geo+json")
    fc = resp.json()
    assert fc["type"] == "FeatureCollection" and fc["features"]


def test_layers_endpoint_404_bij_onbekende_bron(live_server):
    with httpx.Client(timeout=10.0) as http:
        resp = http.get(f"{live_server}/api/layers/bestaat-niet")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server'`.

- [ ] **Step 3: Write minimal implementation**

`nldt/simulation/live/mcp_client.py`:

```python
"""Echte MCP-client over streamable-http tegen de eigen loopback-mounts.

Elke call opent een korte sessie (initialize → call_tool) — robuust voor de
demo, geen sessie-hergebruik tussen stappen.
"""

from __future__ import annotations

from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class McpToolError(RuntimeError):
    pass


class McpLoopbackClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def call_tool(self, server: str, tool: str, args: dict[str, Any]) -> str:
        url = f"{self.base_url}/mcp/{server}/mcp"
        async with streamable_http_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
        if getattr(result, "isError", False):
            raise McpToolError(f"{server}.{tool} mislukt: {result.content}")
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text is not None:
                return text
        raise McpToolError(f"{server}.{tool}: geen tekst-resultaat")
```

`nldt/simulation/live/server.py`:

```python
"""Live fetch-keten server (spec 2026-11-15).

Mount de bestaande MCP-servers, serves de WGS84-cache-twins als lagen en
(Transient in deze task) de startpagina. Start:

    cd nldt && .venv/bin/python simulation/live/server.py
    open http://127.0.0.1:8095
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

LIVE_ROOT = Path(__file__).resolve().parent
NLDT_ROOT = LIVE_ROOT.parents[1]
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# poc-/dso-tools executeren in-process via de job-store (één proces voor de demo)
os.environ.setdefault("NLDT_OFFLINE", "1")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

from services.mcp_servers.catalog_server import mcp as catalog_mcp  # noqa: E402
from services.mcp_servers.data_server import mcp as data_mcp  # noqa: E402
from services.mcp_servers.dso_server import mcp as dso_mcp  # noqa: E402
from services.mcp_servers.http_transport import build_mcp_http_app  # noqa: E402
from services.mcp_servers.poc_server import mcp as poc_mcp  # noqa: E402

POC_CACHE = NLDT_ROOT.parent / "poc" / "data" / "cache"
MOUNTS = [
    ("/mcp/data", data_mcp),
    ("/mcp/dso", dso_mcp),
    ("/mcp/catalog", catalog_mcp),
    ("/mcp/poc", poc_mcp),
]


@asynccontextmanager
async def _lifespan(_app):
    # Gemounte ASGI-apps krijgen geen lifespan-events: de parent start de
    # session-managers (zelfde patroon als http_transport.run_mcp_http).
    managers = [srv.session_manager.run() for _, srv in MOUNTS]
    for mgr in managers:
        await mgr.__aenter__()
    try:
        yield
    finally:
        for mgr in managers:
            await mgr.__aexit__(None, None, None)


def create_app(tool_client_factory=None):
    app = FastAPI(title="nldt-live-fetch-sim", version="1.0.0", lifespan=_lifespan)
    for prefix, srv in MOUNTS:
        app.mount(prefix, build_mcp_http_app(srv))

    @app.get("/api/layers/{source_id}")
    def layer(source_id: str):
        pad = POC_CACHE / f"{source_id}.4326.geojson"
        if not pad.is_file():
            raise HTTPException(status_code=404, detail=f"geen 4326-twin voor {source_id}")
        return FileResponse(pad, media_type="application/geo+json")

    @app.get("/")
    def index():
        return FileResponse(LIVE_ROOT / "index.html")

    return app


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_LIVE_SIM_PORT", "8095"))
    host = os.environ.get("NLDT_LIVE_SIM_HOST", "127.0.0.1")
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_server.py -v`
Expected: 4 PASSED (2 loopback-MCP, 2 layers-endpoint).

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/live/mcp_client.py nldt/simulation/live/server.py nldt/tests/test_live_sim_server.py
git commit -m "feat(live-sim): server met MCP-mounts + echte loopback-MCP-client + /api/lagen uit cache-twins (NLDT_OFFLINE default 1)"
```

---

### Task 5: SSE-sessie-endpoints in de server

**Files:**
- Modify: `nldt/simulation/live/server.py` (in `create_app`)
- Test: `nldt/tests/test_live_sim_session.py` (nieuw)

**Interfaces:**
- Consumes: Task 3 (`ScriptedAgent`, `SessionStore`), Task 4 (`create_app`, `McpLoopbackClient`).
- Produces: `POST /api/session -> {"sessionId": str}` (409 als er al een sessie draait); `GET /api/session/{sid}/events -> text/event-stream` met de events uit Task 3; `create_app(tool_client_factory=...)` — tests injecteren hiermee een fake client (ASGI-transport opent geen sockets, dus de echte loopback-client kan daar niet werken; Task 7 test de echte route wel).

- [ ] **Step 1: Write the failing test**

```python
"""SSE-sessie-endpoints met geïnjecteerde fake-toolclient (geen sockets)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

import server  # noqa: E402
from agent import ScriptedAgent  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402 (sibling in tests/)


def _parse_sse(regels: list[str]) -> list[tuple[str, dict]]:
    events = []
    ev, data = None, None
    for regel in regels:
        if regel.startswith("event: "):
            ev = regel[len("event: "):].strip()
        elif regel.startswith("data: "):
            data = json.loads(regel[len("data: "):])
        elif regel == "" and ev is not None:
            events.append((ev, data))
            ev, data = None, None
    return events


def _lees_sse(http, url) -> list[str]:
    """Lees alle SSE-regels; de server sluit de stream na run_done/error vanzelf."""
    regels = []
    with http.stream("GET", url) as stream:
        for regel in stream.iter_lines():
            regels.append(regel)
    return regels


def test_sessie_start_en_eventstroom():
    app = server.create_app(tool_client_factory=lambda: ScriptedAgent(FakeMcpClient()))
    with httpx.Client(transport=httpx.ASGITransport(app=app), timeout=20.0) as http:
        resp = http.post("http://test/api/session")
        assert resp.status_code == 200
        sid = resp.json()["sessionId"]

        events = _parse_sse(_lees_sse(http, f"http://test/api/session/{sid}/events"))
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 6
    assert namen.count("tool_result") == 6
    assert namen.count("layer_ready") == 3
    assert "run_done" in namen


def test_tweede_sessie_409_en_onbekende_sessie_error_event():
    app = server.create_app(tool_client_factory=lambda: ScriptedAgent(FakeMcpClient()))
    with httpx.Client(transport=httpx.ASGITransport(app=app), timeout=20.0) as http:
        eerste = http.post("http://test/api/session")
        assert eerste.status_code == 200

        tweede = http.post("http://test/api/session")
        assert tweede.status_code == 409

        # sessie aflopen: stream leeglezen tot sluiting, dan is een nieuwe sessie weer ok
        sid = eerste.json()["sessionId"]
        _lees_sse(http, f"http://test/api/session/{sid}/events")
        derde = http.post("http://test/api/session")
        assert derde.status_code == 200

        # onbekende sessie → error-event op de stream (200, SSE-error, geen 404)
        events = _parse_sse(_lees_sse(http, "http://test/api/session/niets/events"))
        assert events and events[0][0] == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_session.py -v`
Expected: FAIL — `httpx.HTTPStatusError` 404 op `POST /api/session` (route bestaat nog niet).

- [ ] **Step 3: Write minimal implementation**

In `nldt/simulation/live/server.py` — importeer bovenaan (na de MCP-imports):

```python
import json

from fastapi.responses import StreamingResponse  # noqa: E402

from agent import ScriptedAgent, SessionStore  # noqa: E402
from mcp_client import McpLoopbackClient  # noqa: E402
```

En in `create_app`, direct ná de mounts en vóór `/api/layers`:

```python
    store = SessionStore()

    def _default_tool_client_factory():
        base = os.environ.get("NLDT_LIVE_SIM_BASE") or (
            f"http://127.0.0.1:{os.environ.get('NLDT_LIVE_SIM_PORT', '8095')}"
        )
        return ScriptedAgent(McpLoopbackClient(base))

    @app.post("/api/session")
    async def start_session():
        factory = tool_client_factory or _default_tool_client_factory
        try:
            sid = store.start(factory)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"sessionId": sid}

    @app.get("/api/session/{sid}/events")
    async def events(sid: str):
        async def gen():
            try:
                async for ev, data in store.stream(sid):
                    yield f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            except KeyError:
                yield 'event: error\ndata: {"melding": "onbekende sessie"}\n\n'

        return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_session.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/live/server.py nldt/tests/test_live_sim_session.py
git commit -m "feat(live-sim): SSE-sessie-endpoints — POST /api/session (één actief, 409) + events-stream; factory injecteerbaar voor tests"
```

---

### Task 6: UI — `index.html` (trace + SVG-kaart + mock-badge)

**Files:**
- Create: `nldt/simulation/live/index.html`
- Test: `nldt/tests/test_live_sim_ui.py` (nieuw)

**Interfaces:**
- Consumes: `POST /api/session` → `{"sessionId"}`; `GET /api/session/{sid}/events` (SSE, events uit Task 3); `GET /api/layers/{source_id}` (GeoJSON WGS84).
- Produces: startpagina `GET /` met: startknop (`id="start"`), trace-lijst (`id="trace"`), SVG-kaart (`id="kaart"`), NGSI-LD herkomstbadge (`id="ngsi-badge"`, toont `NGSI-LD: MOCK` of `NGSI-LD: LIVE`).

- [ ] **Step 1: Write the failing test**

```python
"""UI-startpagina: server serves index.html met kaart, trace en EventSource-wiring."""

from __future__ import annotations

import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx  # noqa: E402

import server  # noqa: E402


def test_index_bevat_kaart_trace_en_eventsource():
    app = server.create_app()
    with httpx.Client(transport=httpx.ASGITransport(app=app), timeout=10.0) as http:
        resp = http.get("http://test/")
    assert resp.status_code == 200
    html = resp.text
    for naald in ('id="kaart"', 'id="trace"', 'id="start"', 'id="ngsi-badge"', "EventSource", "/api/session"):
        assert naald in html, f"index.html mist {naald}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_ui.py -v`
Expected: FAIL — 500/404 op `GET /` (index.html bestaat nog niet).

- [ ] **Step 3: Write minimal implementation**

`nldt/simulation/live/index.html`:

```html
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live fetch-keten · nLDT</title>
<style>
  :root{--bg:#0b1220;--panel:#111a2c;--panel2:#0d1626;--line:#1e293b;--line2:#24324a;
        --txt:#e2e8f0;--faint:#94a3b8;--acc:#38bdf8;--ok:#22c55e;--err:#f87171;--zone:#93c5fd;--punt:#f59e0b}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--txt)}
  header{display:flex;align-items:center;gap:14px;padding:12px 18px;border-bottom:1px solid var(--line)}
  header h1{font-size:16px;margin:0;font-weight:600}
  header .sub{color:var(--faint);font-size:12px}
  #start{background:var(--acc);color:#04121f;border:0;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer}
  #start:disabled{opacity:.45;cursor:wait}
  #ngsi-badge{margin-left:auto;font-size:12px;padding:4px 10px;border-radius:999px;border:1px solid var(--line2);color:var(--faint)}
  #ngsi-badge.mock{color:#fbbf24;border-color:#fbbf24}
  #ngsi-badge.live{color:var(--ok);border-color:var(--ok)}
  main{display:grid;grid-template-columns:390px 1fr;gap:0;min-height:calc(100vh - 57px)}
  @media (max-width:1000px){main{grid-template-columns:1fr}}
  #trace{border-right:1px solid var(--line);padding:10px 12px;overflow-y:auto;max-height:calc(100vh - 57px)}
  .stap{border:1px solid var(--line2);border-radius:10px;padding:8px 10px;margin:8px 0;background:var(--panel)}
  .stap .kop{display:flex;justify-content:space-between;gap:8px;font-size:12.5px}
  .stap .tool{color:var(--acc);font-family:ui-monospace,monospace;font-size:11.5px}
  .stap .status{font-size:11.5px}
  .stap .status.ok{color:var(--ok)} .stap .status.err{color:var(--err)} .stap .status.wait{color:var(--faint)}
  .stap details{margin-top:4px} .stap pre{font-size:11px;color:var(--faint);white-space:pre-wrap;margin:4px 0 0}
  .stap .sam{color:var(--faint);font-size:12px;margin-top:2px}
  #kaartwrap{padding:10px 14px}
  #kaart{width:100%;height:auto;aspect-ratio:16/10;background:var(--panel2);border:1px solid var(--line2);border-radius:12px;display:block}
  #legenda{display:flex;gap:16px;color:var(--faint);font-size:12px;margin-top:8px}
  .chip{display:inline-flex;align-items:center;gap:6px}
  .chip i{width:10px;height:10px;border-radius:2px;display:inline-block}
  #fout{display:none;color:var(--err);padding:8px 12px;border-bottom:1px solid var(--err)}
</style>
</head>
<body>
<header>
  <h1>Live fetch-keten</h1>
  <span class="sub">elke stap = één echte MCP-toolcall · catalogus → DSO-kb → geolagen → NGSI-LD</span>
  <button id="start">▶ Start fetch-keten</button>
  <span id="ngsi-badge">NGSI-LD: —</span>
</header>
<div id="fout"></div>
<main>
  <aside id="trace"><div class="sub" style="color:var(--faint);padding:6px 2px">De trace verschijnt hier zodra de keten start.</div></aside>
  <section id="kaartwrap">
    <svg id="kaart" viewBox="0 0 960 600" preserveAspectRatio="xMidYMid meet"></svg>
    <div id="legenda">
      <span class="chip"><i style="background:var(--zone)"></i> inclusion-/kaartlaag wind</span>
      <span class="chip"><i style="background:var(--punt);border-radius:50%"></i> NGSI-LD AirQualityObserved</span>
    </div>
  </section>
</main>
<script>
"use strict";
const lagen = [];           // {laagtype, geojson}
const bbox = {minLon:1e9,minLat:1e9,maxLon:-1e9,maxLat:-1e9};
const rijen = {};           // index -> DOM-node

const elStart = document.getElementById("start");
const elTrace = document.getElementById("trace");
const elKaart = document.getElementById("kaart");
const elBadge = document.getElementById("ngsi-badge");
const elFout  = document.getElementById("fout");

elStart.addEventListener("click", start);

async function start() {
  elStart.disabled = true;
  elFout.style.display = "none";
  elTrace.innerHTML = "";
  lagen.length = 0;
  Object.assign(bbox, {minLon:1e9, minLat:1e9, maxLon:-1e9, maxLat:-1e9});
  try {
    const resp = await fetch("/api/session", {method: "POST"});
    if (!resp.ok) throw new Error((await resp.json()).detail || resp.status);
    const {sessionId} = await resp.json();
    const es = new EventSource(`/api/session/${sessionId}/events`);
    for (const naam of ["step_started", "tool_result", "layer_ready", "run_done", "error"]) {
      es.addEventListener(naam, (ev) => verwerk(naam, JSON.parse(ev.data)));
    }
    es.addEventListener("run_done", () => { es.close(); elStart.disabled = false; });
    es.addEventListener("error", () => { /* verbinding sluit na afloop */ });
  } catch (exc) {
    elFout.textContent = "Start mislukt: " + exc.message;
    elFout.style.display = "block";
    elStart.disabled = false;
  }
}

function verwerk(naam, data) {
  if (naam === "step_started") voegStapToe(data);
  else if (naam === "tool_result") zetResultaat(data);
  else if (naam === "layer_ready") voegLaagToe(data);
  else if (naam === "error") toonFout(data);
}

function voegStapToe(d) {
  const div = document.createElement("div");
  div.className = "stap";
  div.innerHTML = `
    <div class="kop"><span>${d.index + 1}. ${d.label}</span><span class="status wait">•</span></div>
    <div class="tool">${d.server} · ${d.tool}()</div>
    <details><summary>args</summary><pre>${JSON.stringify(d.args, null, 1)}</pre></details>
    <div class="sam"></div>`;
  elTrace.appendChild(div);
  rijen[d.index] = div;
  div.scrollIntoView({block: "nearest"});
}

function zetResultaat(d) {
  const div = rijen[d.index];
  if (!div) return;
  const st = div.querySelector(".status");
  st.textContent = (d.ok ? "✓ " : "✗ ") + d.duration_ms + " ms";
  st.className = "status " + (d.ok ? "ok" : "err");
  div.querySelector(".sam").textContent = d.summary || "";
}

async function voegLaagToe(d) {
  let geo = d.geojson || null;
  if (!geo && d.source_id) {
    const resp = await fetch(`/api/layers/${encodeURIComponent(d.source_id)}`);
    if (resp.ok) geo = await resp.json();
  }
  if (!geo) return;
  lagen.push({laagtype: d.laagtype, geojson: geo});
  if (d.laagtype === "punten") zetNgsiBadge(geo);
  breidBboxUit(geo);
  teken();
}

function zetNgsiBadge(geo) {
  const mock = (geo.features || []).some(f => (f.properties || {}).mock === true);
  elBadge.textContent = mock ? "NGSI-LD: MOCK" : "NGSI-LD: LIVE";
  elBadge.className = mock ? "mock" : "live";
}

function toonFout(d) {
  elFout.textContent = `Stap ${d.stap + 1} (${d.label}) mislukt: ${d.melding}`;
  elFout.style.display = "block";
  elStart.disabled = false;
}

function walkCoords(geom, cb) {
  if (!geom) return;
  const t = geom.type;
  if (t === "Point") cb(geom.coordinates);
  else if (t === "MultiPoint" || t === "LineString") geom.coordinates.forEach(cb);
  else if (t === "Polygon" || t === "MultiLineString") geom.coordinates.forEach(r => r.forEach(cb));
  else if (t === "MultiPolygon") geom.coordinates.forEach(p => p.forEach(r => r.forEach(cb)));
}

function breidBboxUit(geo) {
  for (const f of geo.features || []) walkCoords(f.geometry, c => {
    bbox.minLon = Math.min(bbox.minLon, c[0]); bbox.maxLon = Math.max(bbox.maxLon, c[0]);
    bbox.minLat = Math.min(bbox.minLat, c[1]); bbox.maxLat = Math.max(bbox.maxLat, c[1]);
  });
}

const W = 960, H = 600, PAD = 30;
function px(lon, lat) {
  const x = (lon - bbox.minLon) / (bbox.maxLon - bbox.minLon || 1);
  const y = (lat - bbox.minLat) / (bbox.maxLat - bbox.minLat || 1);
  return [PAD + x * (W - 2 * PAD), H - PAD - y * (H - 2 * PAD)];
}

function teken() {
  elKaart.innerHTML = "";
  for (const {laagtype, geojson} of lagen) {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    if (laagtype === "punten") {
      for (const f of geojson.features || []) {
        if (!f.geometry || f.geometry.type !== "Point") continue;
        const [x, y] = px(f.geometry.coordinates[0], f.geometry.coordinates[1]);
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", 5);
        c.setAttribute("fill", "var(--punt)"); c.setAttribute("stroke", "#0b1220");
        const titel = document.createElementNS("http://www.w3.org/2000/svg", "title");
        titel.textContent = (f.properties || {}).entityId || f.id || "";
        c.appendChild(titel);
        g.appendChild(c);
      }
    } else {
      for (const f of geojson.features || []) {
        if (!f.geometry) continue;
        const ringGroepen = f.geometry.type === "Polygon" ? [f.geometry.coordinates]
          : f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [];
        for (const ringen of ringGroepen) {
          let d = "";
          for (const ring of ringen) {
            ring.forEach((c, i) => {
              const [x, y] = px(c[0], c[1]);
              d += (i === 0 ? "M" : "L") + x.toFixed(1) + " " + y.toFixed(1) + " ";
            });
            d += "Z ";
          }
          if (!d) continue;
          const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
          p.setAttribute("d", d);
          p.setAttribute("fill", "var(--zone)"); p.setAttribute("fill-opacity", "0.25");
          p.setAttribute("stroke", "var(--zone)"); p.setAttribute("stroke-width", "0.8");
          g.appendChild(p);
        }
      }
    }
    elKaart.appendChild(g);
  }
}
</script>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_ui.py -v`
Expected: 1 PASSED. Draai daarna ook de eerdere suites: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_*.py -v` — alles groen.

- [ ] **Step 5: Handmatige visuele check**

Run: `cd nldt && .venv/bin/python simulation/live/server.py` → open `http://127.0.0.1:8095` → klik **▶ Start fetch-keten**. Verwacht: 6 trace-stappen verschijnen met duur, de kaart vult met de twee wind-zonelagen en het NGSI-LD-punt, badge toont `NGSI-LD: MOCK` (zonder broker-config). Stop de server (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add nldt/simulation/live/index.html nldt/tests/test_live_sim_ui.py
git commit -m "feat(live-sim): UI — tool-call trace, SVG-kaart met lagen per stap, NGSI-LD MOCK/LIVE-herkomstbadge"
```

---

### Task 7: End-to-end over echt MCP + README

**Files:**
- Create: `nldt/tests/test_live_sim_e2e.py`
- Create: `nldt/simulation/live/README.md`

**Interfaces:**
- Consumes: alles (Tasks 1-6). E2E draait de volledige keten over écht MCP-loopback in één proces (uvicorn in-thread; server en tests delen de interpreter, dus module-monkeypatches gelden ook server-zijde).
- Produces: bewijs dat de volledige keten (6 tool calls, 3 lagen, run_done) over het echte MCP-protocol loopt; README met startinstructies.

- [ ] **Step 1: Write the failing test**

```python
"""E2E: volledige fetch-keten over echt MCP-loopback, offline (cache + mock)."""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import httpx
import pytest
import uvicorn

import server  # noqa: E402


def _vrije_poort():  # zelfde helper als test_live_sim_server
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def e2e(monkeypatch):
    from services.adapters import data_platform

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)

    port = _vrije_poart()
    monkeypatch.setenv("NLDT_LIVE_SIM_BASE", f"http://127.0.0.1:{port}")
    config = uvicorn.Config(server.create_app(), host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if uv_server.started:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("live-server startte niet")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=5)


def _lees_events(http, base):
    resp = http.post(f"{base}/api/session")
    assert resp.status_code == 200
    sid = resp.json()["sessionId"]
    events, ev, data = [], None, None
    with http.stream("GET", f"{base}/api/session/{sid}/events") as stream:
        for regel in stream.iter_lines():
            if regel.startswith("event: "):
                ev = regel[7:].strip()
            elif regel.startswith("data: "):
                data = json.loads(regel[6:])
            elif regel == "" and ev is not None:
                events.append((ev, data))
                if ev in ("run_done", "error"):
                    return events
                ev, data = None, None
    return events


def test_volledige_keten_over_echt_mcp(e2e):
    with httpx.Client(timeout=60.0) as http:
        events = _lees_events(http, e2e)
        namen = [ev for ev, _ in events]
        assert "error" not in namen, [d for ev, d in events if ev == "error"]
        assert namen.count("step_started") == 6
        assert namen.count("tool_result") == 6
        assert all(d["ok"] for ev, d in events if ev == "tool_result")
        assert namen.count("layer_ready") == 3
        assert "run_done" in namen

        # bestand-backed lagen zijn daadwerkelijk op te halen
        zone_ids = [d["source_id"] for ev, d in events if ev == "layer_ready" and d.get("source_id") and not d.get("geojson")]
        assert set(zone_ids) == {"agrest-ov-gebied-windenergie", "arcgis-et-wind-gebieden"}
        for sid in zone_ids:
            resp = http.get(f"{e2e}/api/layers/{sid}")
            assert resp.status_code == 200
            assert resp.json()["type"] == "FeatureCollection"

        # inline NGSI-laag is een FeatureCollection (mock-entity)
        ngsi = [d for ev, d in events if ev == "layer_ready" and d.get("geojson")][0]
        assert ngsi["source_id"] == "ngsi-ld-dpl-airquality"
        assert ngsi["geojson"]["type"] == "FeatureCollection"
        assert ngsi["geojson"]["features"]
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_e2e.py -v`
Expected: als Tasks 1-6 correct zijn: PASSED. Faalt hij, debug dan de keten (meest voorkomend: `NLDT_LIVE_SIM_BASE` die niet bij de gekozen poort past, of een ontbrekende cache-twin) — dit is de integratie-gate, verbeter eerdere taken waar nodig en her-run.

- [ ] **Step 3: Write the README**

`nldt/simulation/live/README.md`:

```markdown
# Live fetch-keten — simulatie die de stappen echt uitvoert

> Spec: [docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md](../../../docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md)

## Starten

```bash
cd nldt
.venv/bin/python simulation/live/server.py     # 127.0.0.1:8095 (env: NLDT_LIVE_SIM_PORT/HOST)
open http://127.0.0.1:8095
```

Klik **▶ Start fetch-keten**. De gescripte agent doorloopt zes stappen, elke
stap is één **echte MCP-toolcall** (streamable-http over loopback tegen de
gemounte servers `/mcp/{data,dso,catalog,poc}`):

1. `catalog.list_poc_capabilities` — wat is beschikbaar?
2. `dso.dso_kb_overview` — regels-instrumenten in het gebied
3. `poc.fetch_geo_layer("agrest-ov-gebied-windenergie")` — inclusion-zone wind (cache-first)
4. `poc.fetch_geo_layer("arcgis-et-wind-gebieden")` — kaartlaag wind (cache-first)
5. `data.list_entities("AirQualityObserved")` — NGSI-LD entities
6. `data.entities_to_geojson("AirQualityObserved")` — naar GeoJSON (inline laag)

De kaart vult per stap; de trace toont args, duur en samenvatting. De badge
rechtsboven toont de NGSI-LD-herkomst: **MOCK** (adapter-mock, default) of
**LIVE** (zet `NLDT_NGSI_LD_URL` of `NLDT_DATA_PLATFORM_URL` + mock uit).

De server zet `NLDT_OFFLINE=1` voor zichzelf: poc-/dso-tools executeren
in-process via de job-store. ArcGIS/agrest-lagen komen cache-first uit
`poc/data/cache/` — offline deterministisch; `NLDT_LIVE_SIM_BASE` overschrijft
de loopback-basis-URL (gebruikt door de E2E-test op een vrije poort).

## Tests

```bash
cd nldt && .venv/bin/python -m pytest tests/test_live_sim_*.py -v
```
```

- [ ] **Step 4: Run the complete suite**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_*.py -v`
Expected: alle tests groen (fetch_geo_layer 3, poc_tool 1, agent 4, server 4, session 2, ui 1, e2e 1).

- [ ] **Step 5: Commit**

```bash
git add nldt/tests/test_live_sim_e2e.py nldt/simulation/live/README.md
git commit -m "feat(live-sim): E2E over echt MCP-loopback (6 calls, 3 lagen, run_done) + README met start- en mock/live-instructies"
```

---

## Zelfreview-notities (uitgevoerd)

- **Specdekking**: mounts ✓ (Task 4), echte MCP-client ✓ (Task 4), gescripte agent + SSE ✓ (Tasks 3/5), `fetch_geo_layer`-tool ✓ (Tasks 1-2), UI met kaart/trace/badge ✓ (Task 6), events ✓ (Task 3), foutafhandeling ✓ (Tasks 3/5), tests ✓ (alle), poort 8095 + loopback ✓ (Task 4), MOCK/LIVE-badge ✓ (Task 6). Bewuste deviaties staan in Global Constraints (6 stappen i.p.v. 5; inline-geojson voor de NGSI-laag).
- **Typeconsistentie**: `ScriptedAgent(client, stappen=None).run(emit)`, `SessionStore.start(agent_factory)/stream(sid)`, `McpLoopbackClient(base_url).call_tool(server, tool, args) -> str`, `execute_poc_process("fetch-geo-layer", {...}) -> {"summary": {...}}` — consistent door alle taken.
- **Geen placeholders**: alle stappen bevatten volledige code en exacte commando's.
