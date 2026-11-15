# Live-sim alle PoC's — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De live fetch-keten-simulatie uitbreiden naar zes PoC-chains uit simulation.html (utrecht · eindhoven · breda · gent · veenendaal · dsorr): pipeline-stappen echt executerend via MCP, PoC-switcher in de UI, twee nieuwe process-wrappers, tool `run_artifact`, en async-executie zodat SSE levend blijft.

**Architecture:** `fetch_script.py` wordt `chains.py` (registry van 6 chains, zelfde stap-model + nieuwe `args_uit_vorige`-resolver zodat een pipeline-runDir expliciet doorvoert naar `run_artifact`); `ScriptedAgent` krijgt de gekozen chain; server krijgt `GET /api/chains` en `POST /api/session {chain}`; UI krijgt chips-switcher. Spec: [docs/superpowers/specs/2026-11-15-live-sim-alle-pocs-design.md](../specs/2026-11-15-live-sim-alle-pocs-design.md).

**Tech Stack:** Python 3.14 (venv `nldt/.venv`), FastAPI + uvicorn + `mcp` SDK 2.3.0, plain HTML/JS/SVG. Bestaande contracten: `execute_poc_process(process_id, inputs) -> {"summary"}`, `_run_poc_tool(tool_name, arguments)` (met `NLDT_OFFLINE=1` in-process), `McpLoopbackClient(base_url).call_tool(server, tool, args) -> str`, `ScriptedAgent(client, stappen).run(emit)`, `SessionStore.start/stream`.

## Global Constraints

- Tests: `cd nldt && .venv/bin/python -m pytest ...`; geen netwerk in tests; de zware execute-paden worden in tests gestub/replay (productie-chains gebruiken execute; zie Task 8-strategie).
- Eventnamen exact en ongewijzigd: `step_started`, `tool_result`, `layer_ready`, `run_done`, `error`.
- Toolnamen exact: bestaand `run_opportunity_map` (args `mode`, `useCase`: wind|zon|bos, `runDir?`), `run_bp2op_transform` (args `mode`, `useCase` default eindhoven, `outDir?`), `run_value_scan` (args `mode`, `runDir?`); nieuw `gent_life_event_run` (`mode`, `package` default `gent-mobiliteit-ondernemer`, `persona` default `sanne`), `veenendaal_gebiedscheck_run` (`mode`), `run_artifact` (`run_dir`, `artifact`). Processen: `opportunity-map-run`, `bp2op-transform`, `breda-scan-run` (bestaan), `gent-life-event-run`, `veenendaal-gebiedscheck-run`, `run-artifact` (nieuw).
- Alle drie de bestaande pipeline-executors geven in execute-modus `summary.runDir` terug (geverifieerd) — `run_artifact`-stappen resolven hun `run_dir` daaruit via `args_uit_vorige`.
- `run_artifact`-beveiliging: resolved pad moet binnen `run_dir` blijven (geen `..`-ontsnapping), bestand ≤ 5 MB (5_242_880 bytes), anders `ValueError`.
- Elke scriptstap = precies één tool call; agent blijft voorwaardeloos; `args_uit_vorige` is een pure functie van het vorige ruwe resultaat.
- Agent inline-lagen: laag-key `"inline"` met optioneel `"inline_uit": "artifact_content"` — de agent extraheert dan `payload["outputs"]["artifact"]["content"]` i.p.v. de ruwe payload (run_artifact wrapt de FeatureCollection).
- Commit per task; commit alleen de bestanden van die task.
- Async: sync-executors in de offline-toolpaden via `asyncio.to_thread` (SSE blijft levend tijdens lange stappen).
- productie-chains: execute-modus; tests overschrijven mode via `chains.chain_met_mode(chain_id, "replay")`.

---

### Task 1: Async-executie in de offline-toolpaden

**Files:**
- Modify: `nldt/services/mcp_servers/poc_server.py` (`_run_poc_tool`, offline-tak)
- Modify: `nldt/services/mcp_servers/data_server.py` (`list_entities`, `entities_to_geojson`)
- Modify: `nldt/services/mcp_servers/dso_server.py` (`_run_dso_tool`, offline-tak)
- Test: `nldt/tests/test_live_sim_async_tools.py` (nieuw)

**Interfaces:**
- Consumes: bestaande functies (gedrag ongewijzigd, alleen non-blocking uitgevoerd).
- Produces: dezelfde handtekeningen en return-waarden; Task 5+ bouwen hierop zonder wijziging. Semantisch: tijdens een sync-executor draait de event loop door.

- [ ] **Step 1: Write the failing test**

```python
"""Offline-toolpaden blokkeren de event loop niet meer (asyncio.to_thread).

De SSE-stream moet levend blijven tijdens een multi-seconde pipeline-stap:
een ticker-task moet ticken TERWIJL een langzame sync-executor draait.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))


def test_poc_offline_pad_blokkeert_loop_niet(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")
    from services.mcp_servers import poc_server
    from services.process_adapter import jobs as job_store

    def trage_route(process_id, inputs, backend="local"):
        import time

        time.sleep(0.4)
        return {"jobId": "j1", "outputs": {"summary": {}}, "prov": {"startedAtTime": "t", "endedAtTime": "t"}}

    monkeypatch.setattr(job_store, "route_execute", trage_route)

    async def scenario():
        ticks = []

        async def ticker():
            for _ in range(20):
                await asyncio.sleep(0.05)
                ticks.append(1)

        t = asyncio.create_task(ticker())
        await poc_server._run_poc_tool("fetch_geo_layer", {"source_id": "agrest-ov-gebied-windenergie"})
        await t
        return ticks

    assert len(asyncio.run(scenario())) >= 4, "event loop stond stil tijdens de executor"


def test_data_list_entities_blokkeert_loop_niet(monkeypatch):
    from services.adapters import data_platform
    from services.mcp_servers import data_server

    def trage_list(entity_type, scope=None, geoproperty=None):
        import time

        time.sleep(0.4)
        return [{"id": "urn:ngsi-ld:X:1", "type": entity_type, "mock": True}]

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)
    monkeypatch.setattr(data_platform, "list_entities", trage_list)

    async def scenario():
        ticks = []

        async def ticker():
            for _ in range(20):
                await asyncio.sleep(0.05)
                ticks.append(1)

        t = asyncio.create_task(ticker())
        await data_server.list_entities("AirQualityObserved")
        await t
        return ticks

    assert len(asyncio.run(scenario())) >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_async_tools.py -v`
Expected: FAIL — `len(ticks) == 0` op minstens één van de twee (de loop stond stil tijdens de sync-executor).

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/mcp_servers/poc_server.py`, in `_run_poc_tool`, verander de offline-tak:

```python
    if os.environ.get("NLDT_OFFLINE") == "1":
        result = await asyncio.to_thread(_execute_local, process_id, inputs)
```

voeg bovenin toe (bij de stdlib-imports): `import asyncio`.

In `nldt/services/mcp_servers/data_server.py`, in `list_entities` en `entities_to_geojson`, wrap de sync-aanroep:

```python
    entities = await asyncio.to_thread(
        data_platform.list_entities,
        entity_type=entity_type,
        scope=scope,
        geoproperty=geoproperty,
    )
```

resp. (in `entities_to_geojson`, die `fetch_ngsi_as_features` aanroept):

```python
    from services.hybrid_bridge import fetch_ngsi_as_features

    fc = await asyncio.to_thread(fetch_ngsi_as_features, entity_type, scope=scope)
```

voeg bovenin toe: `import asyncio`.

In `nldt/services/mcp_servers/dso_server.py`, in `_run_dso_tool`, verander de offline-tak:

```python
    if os.environ.get("NLDT_OFFLINE") == "1":
        result = await asyncio.to_thread(_execute_local, spec["process_id"], inputs)
```

voeg bovenin toe: `import asyncio`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_async_tools.py -v`
Expected: 2 PASSED. Daarna de live-sim-familie: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_poc_tool.py tests/test_live_sim_fetch_geo_layer.py tests/test_live_sim_agent.py tests/test_live_sim_server.py tests/test_live_sim_session.py tests/test_live_sim_ui.py tests/test_live_sim_e2e.py -q` — 16 PASSED (gedrag ongewijzigd).

- [ ] **Step 5: Commit**

```bash
git add nldt/services/mcp_servers/poc_server.py nldt/services/mcp_servers/data_server.py nldt/services/mcp_servers/dso_server.py nldt/tests/test_live_sim_async_tools.py
git commit -m "feat(live-sim): offline-toolpaden via asyncio.to_thread — SSE blijft levend tijdens lange pipeline-stappen (eindreview-opvolger, nu harde eis voor multi-sekonden stappen)"
```

---

### Task 2: Proces `run-artifact` + tool `run_artifact`

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (definitie vóór `"opportunity-map-run"`, executor boven `EXECUTORS`, entry bovenin `EXECUTORS`)
- Modify: `nldt/services/mcp_servers/poc_tools.py` (onderaan `POC_TOOLS`)
- Modify: `nldt/services/mcp_servers/poc_server.py` (`@mcp.tool` na `fetch_geo_layer`)
- Test: `nldt/tests/test_live_sim_run_artifact.py` (nieuw)

**Interfaces:**
- Consumes: poc-server-patroon (`_run_poc_tool`), `asyncio.to_thread` uit Task 1.
- Produces: `execute_poc_process("run-artifact", {"run_dir": str, "artifact": str}) -> {"artifact": {"name": str, "path": str, "kind": "geojson"|"json"|"text", "bytes": int, "content": object|str}}`; MCP-tool `run_artifact(run_dir, artifact) -> str`. Task 5 (chains) gebruikt `outputs.artifact.content` als inline-geojson voor `layer_ready`.

- [ ] **Step 1: Write the failing test**

```python
"""run-artifact: pipeline-output via MCP, met pad- en grootte-beveiliging."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
if str(NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(NLDT_ROOT))

from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def _tmp_run(tmp_path: Path) -> Path:
    run = tmp_path / "runs" / "20261115T000000Z-test"
    run.mkdir(parents=True)
    return run


def test_run_artifact_leest_geojson_inline(tmp_path):
    run = _tmp_run(tmp_path)
    (run / "zones.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "id": 1}]}),
        encoding="utf-8",
    )
    out = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "zones.geojson"})
    a = out["artifact"]
    assert a["name"] == "zones.geojson"
    assert a["kind"] == "geojson"
    assert a["bytes"] > 0
    assert a["content"]["type"] == "FeatureCollection"
    assert a["content"]["features"][0]["id"] == 1
    assert a["path"] == str((run / "zones.geojson").resolve())


def test_run_artifact_leest_json_en_text(tmp_path):
    run = _tmp_run(tmp_path)
    (run / "run.json").write_text(json.dumps({"runId": "r1"}), encoding="utf-8")
    (run / "report.md").write_text("# rapport", encoding="utf-8")
    a1 = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "run.json"})["artifact"]
    assert a1["kind"] == "json" and a1["content"] == {"runId": "r1"}
    a2 = execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "report.md"})["artifact"]
    assert a2["kind"] == "text" and a2["content"].startswith("# rapport")


def test_run_artifact_weigert_pad_ontsnapping(tmp_path):
    run = _tmp_run(tmp_path)
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "../buiten.json"})
    except ValueError as exc:
        assert "binnen" in str(exc)
    else:
        raise AssertionError("pad-ontsnapping moet geweigerd worden")


def test_run_artifact_weigert_onbekend_bestand_en_te_groot(tmp_path):
    run = _tmp_run(tmp_path)
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "ontbreekt.json"})
    except ValueError:
        pass
    else:
        raise AssertionError("ontbrekend bestand moet ValueError geven")
    groot = run / "groot.json"
    groot.write_bytes(b"x" * (5_242_880 + 1))
    try:
        execute_poc_process("run-artifact", {"run_dir": str(run), "artifact": "groot.json"})
    except ValueError as exc:
        assert "5 MB" in str(exc)
    else:
        raise AssertionError("bestand boven het plafond moet geweigerd worden")


def test_run_artifact_weigert_run_dir_geen_dir(tmp_path):
    niet_dir = tmp_path / "geen-dir"
    niet_dir.write_text("x", encoding="utf-8")
    try:
        execute_poc_process("run-artifact", {"run_dir": str(niet_dir), "artifact": "x.json"})
    except ValueError:
        pass
    else:
        raise AssertionError("run_dir dat geen dir is moet geweigerd worden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_run_artifact.py -v`
Expected: FAIL — `KeyError: 'run-artifact'`.

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/process_adapter/poc_handlers.py` — definitie in `POC_PROCESS_DEFINITIONS` direct vóór `"opportunity-map-run"`:

```python
    "run-artifact": {
        "id": "run-artifact",
        "title": "Read run artifact",
        "description": (
            "Lees één outputbestand uit een pipeline-run-dir en geef de inhoud "
            "inline terug (geojson/json/text). Beveiligd: het resolved pad moet "
            "binnen run_dir blijven en het bestand mag max 5 MB zijn."
        ),
        "version": "1.0.0",
        "keywords": ["poc", "artifact", "live-sim"],
        "inputs": {
            "run_dir": {"title": "Run dir", "schema": {"type": "string"}, "required": True},
            "artifact": {"title": "Bestandsnaam binnen run_dir", "schema": {"type": "string"}, "required": True},
        },
        "outputs": {
            "artifact": {"title": "Artifact met content", "schema": {"type": "object"}},
        },
    },
```

Executor boven `EXECUTORS`:

```python
_RUN_ARTIFACT_MAX_BYTES = 5_242_880


def execute_run_artifact(inputs: dict[str, Any]) -> dict[str, Any]:
    """Eén outputbestand uit een run-dir lezen, inline (pad- en grootte-proof)."""
    run_dir = Path(inputs["run_dir"]).resolve()
    if not run_dir.is_dir():
        raise ValueError(f"run_dir is geen bestaande map: {run_dir}")
    pad = (run_dir / inputs["artifact"]).resolve()
    if run_dir not in pad.parents:
        raise ValueError(f"artifact moet binnen run_dir blijven: {inputs['artifact']!r}")
    if not pad.is_file():
        raise ValueError(f"artifact niet gevonden: {pad}")
    grootte = pad.stat().st_size
    if grootte > _RUN_ARTIFACT_MAX_BYTES:
        raise ValueError(f"artifact groter dan 5 MB plafond: {grootte} bytes")
    tekst = pad.read_text(encoding="utf-8")
    content: Any
    if pad.suffix == ".geojson":
        kind = "geojson"
        content = json.loads(tekst)
    elif pad.suffix == ".json":
        kind = "json"
        content = json.loads(tekst)
    else:
        kind = "text"
        content = tekst
    return {
        "artifact": {
            "name": pad.name,
            "path": str(pad),
            "kind": kind,
            "bytes": grootte,
            "content": content,
        }
    }
```

(let op: `json` is al geïmporteerd in poc_handlers; `Path` ook.)

Entry in `EXECUTORS`, bovenaan:

```python
    "run-artifact": execute_run_artifact,
```

In `nldt/services/mcp_servers/poc_tools.py`, onderaan `POC_TOOLS`:

```python
    "run_artifact": {
        "process_id": "run-artifact",
        "description": "Lees één outputbestand uit een pipeline-run-dir (inline, max 5 MB)",
    },
```

In `nldt/services/mcp_servers/poc_server.py`, na de `fetch_geo_layer`-tool:

```python
@mcp.tool(name="run_artifact", description=POC_TOOLS["run_artifact"]["description"])
async def run_artifact(run_dir: str, artifact: str) -> str:
    return await _run_poc_tool("run_artifact", {"run_dir": run_dir, "artifact": artifact})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_run_artifact.py -v`
Expected: 5 PASSED. Daarna: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_poc_tool.py tests/test_live_sim_async_tools.py -q` — groen.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py nldt/services/mcp_servers/poc_tools.py nldt/services/mcp_servers/poc_server.py nldt/tests/test_live_sim_run_artifact.py
git commit -m "feat(live-sim): proces run-artifact + tool run_artifact — pipeline-output via MCP, inline content, pad-ontsnapping en 5MB-plafond geweigerd"
```

---

### Task 3: Proces `gent-life-event-run`

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (definitie vóór `"opportunity-map-run"`, executor, `EXECUTORS`-entry, constante `POC_GENT` bij de andere POC-constanten bovenin)
- Modify: `nldt/services/mcp_servers/poc_tools.py` + `nldt/services/mcp_servers/poc_server.py`
- Test: `nldt/tests/test_live_sim_gent_wrapper.py` (nieuw)

**Interfaces:**
- Consumes: `_latest_dir(root, pattern)` (bestaand in poc_handlers), poc-server-patroon.
- Produces: `execute_poc_process("gent-life-event-run", {"mode": "replay"|"execute", "package"?: str, "persona"?: str}) -> {"summary": {"mode", "runDir", "runId", "outcome"}}`. Task 5 ket de chain hieraan (execute) en Task 8 E2E (replay op gecommitte run).

- [ ] **Step 1: Write the failing test**

```python
"""gent-life-event-run wrapper: replay op run-dir, execute via echte CLI (offline)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
POC_GENT = NLDT_ROOT.parent / "poc-gent"
for _p in (str(NLDT_ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter import poc_handlers  # noqa: E402
from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def test_gent_replay_leest_nieuwste_run_dir(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "20261102T121500Z-gent-transactional-fien"
    run.mkdir(parents=True)
    (run / "run.json").write_text(
        json.dumps({"runId": "20261102T121500Z-gent-transactional-fien", "routing": {"outcome": "indienen"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(poc_handlers, "POC_GENT", tmp_path)
    out = execute_poc_process("gent-life-event-run", {"mode": "replay"})
    s = out["summary"]
    assert s["mode"] == "replay"
    assert s["runDir"] == str(run)
    assert s["runId"] == "20261102T121500Z-gent-transactional-fien"
    assert s["outcome"] == "indienen"


def test_gent_execute_draait_echte_replay_cli():
    """Deterministisch en offline: de CLI repstudt fase 1+2+3 uit het gecommitte pakket."""
    out = execute_poc_process(
        "gent-life-event-run",
        {"mode": "execute", "package": "gent-mobiliteit-ondernemer", "persona": "sanne"},
    )
    s = out["summary"]
    assert s["mode"] == "execute"
    assert Path(s["runDir"]).is_dir()
    assert (Path(s["runDir"]) / "run.json").is_file()
    assert s["runId"]


def test_gent_onbekende_mode_geweigerd():
    try:
        execute_poc_process("gent-life-event-run", {"mode": "anders"})
    except ValueError:
        pass
    else:
        raise AssertionError("onbekende mode moet geweigerd worden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_gent_wrapper.py -v`
Expected: FAIL — `KeyError: 'gent-life-event-run'`.

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/process_adapter/poc_handlers.py`:

Constant bij de andere POC-constanten (bovenin, na `POC_MINIGIM`):

```python
POC_GENT = WORKSPACE / "poc-gent"
```

Definitie in `POC_PROCESS_DEFINITIONS` (vóór `"opportunity-map-run"`):

```python
    "gent-life-event-run": {
        "id": "gent-life-event-run",
        "title": "Gent life-event run (EUROPAI-piloot)",
        "description": (
            "Deterministische levensgebeurtenis-replay (fase 1+2+3) uit "
            "poc-gent: replay leest de nieuwste run-dir, execute draait de "
            "echte CLI (--package, --persona) en resolvets de nieuwe run-dir."
        ),
        "version": "1.0.0",
        "keywords": ["poc-gent", "life-event", "live-sim"],
        "inputs": {
            "mode": {"title": "replay|execute", "schema": {"type": "string", "default": "replay"}},
            "package": {"title": "Pakket", "schema": {"type": "string", "default": "gent-mobiliteit-ondernemer"}, "required": False},
            "persona": {"title": "Persona", "schema": {"type": "string", "default": "sanne"}, "required": False},
        },
        "outputs": {"summary": {"title": "Run summary", "schema": {"type": "object"}}},
    },
```

Executor boven `EXECUTORS`:

```python
def execute_gent_life_event_run(inputs: dict[str, Any]) -> dict[str, Any]:
    """Gent levensgebeurtenis: replay (nieuwste run-dir) of execute (echte CLI)."""
    mode = inputs.get("mode") or "replay"
    if mode not in ("replay", "execute"):
        raise ValueError("mode must be replay|execute")
    if mode == "replay":
        run_dir = _resolve_dir(inputs.get("runDir"), default=_latest_dir(POC_GENT / "runs", "*"))
        run_pad = run_dir / "run.json"
        if not run_pad.is_file():
            raise FileNotFoundError(f"geen run.json in {run_dir}")
        run = _load_json(run_pad)
        return {
            "summary": {
                "mode": "replay",
                "runDir": str(run_dir),
                "runId": run.get("runId") or run_dir.name,
                "outcome": (run.get("routing") or {}).get("outcome") or run.get("uitkomst"),
            }
        }
    package = inputs.get("package") or "gent-mobiliteit-ondernemer"
    persona = inputs.get("persona") or "sanne"
    cmd = [sys.executable, str(POC_GENT / "run.py"), "--package", package, "--persona", persona]
    proc = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(f"gent CLI faalde (rc={proc.returncode}): {proc.stderr[-400:]}")
    run_dir = _latest_dir(POC_GENT / "runs", "*")
    run = _load_json(run_dir / "run.json")
    return {
        "summary": {
            "mode": "execute",
            "runDir": str(run_dir),
            "runId": run.get("runId") or run_dir.name,
            "outcome": (run.get("routing") or {}).get("outcome") or run.get("uitkomst"),
        }
    }
```

Entry in `EXECUTORS` (bovenaan, na `run-artifact`):

```python
    "gent-life-event-run": execute_gent_life_event_run,
```

In `nldt/services/mcp_servers/poc_tools.py`, onderaan `POC_TOOLS`:

```python
    "gent_life_event_run": {
        "process_id": "gent-life-event-run",
        "description": "Gent levensgebeurtenis-replay (fase 1+2+3): nieuwste run of echte CLI",
    },
```

In `nldt/services/mcp_servers/poc_server.py`, na `run_artifact`:

```python
@mcp.tool(name="gent_life_event_run", description=POC_TOOLS["gent_life_event_run"]["description"])
async def gent_life_event_run(
    mode: str = "replay",
    package: str = "gent-mobiliteit-ondernemer",
    persona: str = "sanne",
) -> str:
    return await _run_poc_tool(
        "gent_life_event_run",
        {"mode": mode, "package": package, "persona": persona},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_gent_wrapper.py -v`
Expected: 3 PASSED (de execute-test draait de echte, deterministische CLI — enkele seconden). Als de CLI faalt op ontbrekende lokaal-cache: rapporteer BLOCKED met de exacte fout — forceer niets.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py nldt/services/mcp_servers/poc_tools.py nldt/services/mcp_servers/poc_server.py nldt/tests/test_live_sim_gent_wrapper.py
git commit -m "feat(live-sim): proces gent-life-event-run — deterministische levensgebeurtenis-replay (replay nieuwste run-dir, execute echte CLI) via poc-server"
```

---

### Task 4: Proces `veenendaal-gebiedscheck-run`

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (definitie, executor, `EXECUTORS`-entry, constante `POC_VEENENDAAL`)
- Modify: `nldt/services/mcp_servers/poc_tools.py` + `nldt/services/mcp_servers/poc_server.py`
- Test: `nldt/tests/test_live_sim_veenendaal_wrapper.py` (nieuw)

**Interfaces:**
- Consumes: `_latest_dir`, `_load_json`, poc-server-patroon.
- Produces: `execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "replay"|"execute"}) -> {"summary": {"mode", "runDir", "runId", "indicatorCount"}}`. Execute roept `poc-veenendaal/run.py::main(refresh=False)` aan via een aparte helper `_veenendaal_main()` (module-level, zodat tests die kunnen stubben).

- [ ] **Step 1: Write the failing test**

```python
"""veenendaal-gebiedscheck-run wrapper: replay op run-dir, execute met gestubde main."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(NLDT_ROOT),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from services.process_adapter import poc_handlers  # noqa: E402
from services.process_adapter.poc_handlers import execute_poc_process  # noqa: E402


def _fixture_run(root: Path, naam: str, indicators: int) -> Path:
    run = root / "runs" / naam
    run.mkdir(parents=True)
    (run / "indicators.json").write_text(
        json.dumps({"indicators": [{"id": f"i{k}"} for k in range(indicators)]}),
        encoding="utf-8",
    )
    (run / "manifest.json").write_text("{}", encoding="utf-8")
    return run


def test_veenendaal_replay_leest_nieuwste_run_dir(tmp_path, monkeypatch):
    oud = _fixture_run(tmp_path, "20261106T151732Z-gebiedscheck", 3)
    nieuw = _fixture_run(tmp_path, "20261112T194937Z-gebiedscheck", 74)
    monkeypatch.setattr(poc_handlers, "POC_VEENENDAAL", tmp_path)
    out = execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "replay"})
    s = out["summary"]
    assert s["mode"] == "replay"
    assert s["runDir"] == str(nieuw)  # lexicaal nieuwste wint
    assert s["indicatorCount"] == 74


def test_veenendaal_execute_roept_main_en_resolvets_nieuwe_run(tmp_path, monkeypatch):
    monkeypatch.setattr(poc_handlers, "POC_VEENENDAAL", tmp_path)

    def fake_main(refresh: bool = False) -> int:
        _fixture_run(tmp_path, "20261201T000000Z-gebiedscheck", 74)
        return 0

    monkeypatch.setattr(poc_handlers, "_veenendaal_main", fake_main)
    out = execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "execute"})
    s = out["summary"]
    assert s["mode"] == "execute"
    assert s["runDir"] == str(tmp_path / "runs" / "20261201T000000Z-gebiedscheck")
    assert s["indicatorCount"] == 74


def test_veenendaal_onbekende_mode_geweigerd():
    try:
        execute_poc_process("veenendaal-gebiedscheck-run", {"mode": "anders"})
    except ValueError:
        pass
    else:
        raise AssertionError("onbekende mode moet geweigerd worden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_veenendaal_wrapper.py -v`
Expected: FAIL — `KeyError: 'veenendaal-gebiedscheck-run'`.

- [ ] **Step 3: Write minimal implementation**

In `nldt/services/process_adapter/poc_handlers.py`:

Constant (naast `POC_GENT`):

```python
POC_VEENENDAAL = WORKSPACE / "poc-veenendaal"
```

Definitie (vóór `"opportunity-map-run"`):

```python
    "veenendaal-gebiedscheck-run": {
        "id": "veenendaal-gebiedscheck-run",
        "title": "Veenendaal gebiedscheck (Spoorzone)",
        "description": (
            "74-item gebiedscheck (Lijst + ILS draft): replay leest de "
            "nieuwste gebiedscheck-run-dir, execute roept run.main(refresh=False) aan."
        ),
        "version": "1.0.0",
        "keywords": ["poc-veenendaal", "gebiedscheck", "live-sim"],
        "inputs": {
            "mode": {"title": "replay|execute", "schema": {"type": "string", "default": "replay"}},
        },
        "outputs": {"summary": {"title": "Run summary", "schema": {"type": "object"}}},
    },
```

Executor + helper boven `EXECUTORS`:

```python
def _veenendaal_main(refresh: bool = False) -> int:
    """Roep poc-veenendaal run.main aan (aparte helper zodat tests stubben)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("veenendaal_run", POC_VEENENDAAL / "run.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.main(refresh=refresh)


def _sum_gebiedscheck_summary(run_dir: Path, mode: str) -> dict[str, Any]:
    indicators_pad = run_dir / "indicators.json"
    aantal = 0
    if indicators_pad.is_file():
        data = _load_json(indicators_pad)
        lijst = data.get("indicators") or data if isinstance(data, list) else data.get("indicators") or []
        aantal = len(lijst)
    return {
        "mode": mode,
        "runDir": str(run_dir),
        "runId": run_dir.name,
        "indicatorCount": aantal,
    }


def execute_veenendaal_gebiedscheck_run(inputs: dict[str, Any]) -> dict[str, Any]:
    """Veenendaal gebiedscheck: replay (nieuwste run-dir) of execute (run.main)."""
    mode = inputs.get("mode") or "replay"
    if mode not in ("replay", "execute"):
        raise ValueError("mode must be replay|execute")
    if mode == "execute":
        rc = _veenendaal_main(refresh=False)
        if rc != 0:
            raise ValueError(f"veenendaal main faalde (rc={rc})")
        run_dir = _latest_dir(POC_VEENENDAAL / "runs", "*-gebiedscheck")
        return {"summary": _sum_gebiedscheck_summary(run_dir, "execute")}
    run_dir = _resolve_dir(inputs.get("runDir"), default=_latest_dir(POC_VEENENDAAL / "runs", "*-gebiedscheck"))
    return {"summary": _sum_gebiedscheck_summary(run_dir, "replay")}
```

Entry in `EXECUTORS` (bovenaan):

```python
    "veenendaal-gebiedscheck-run": execute_veenendaal_gebiedscheck_run,
```

In `nldt/services/mcp_servers/poc_tools.py`:

```python
    "veenendaal_gebiedscheck_run": {
        "process_id": "veenendaal-gebiedscheck-run",
        "description": "Veenendaal Spoorzone gebiedscheck: nieuwste run of echte run.main()",
    },
```

In `nldt/services/mcp_servers/poc_server.py`, na `gent_life_event_run`:

```python
@mcp.tool(name="veenendaal_gebiedscheck_run", description=POC_TOOLS["veenendaal_gebiedscheck_run"]["description"])
async def veenendaal_gebiedscheck_run(mode: str = "replay") -> str:
    return await _run_poc_tool("veenendaal_gebiedscheck_run", {"mode": mode})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_veenendaal_wrapper.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py nldt/services/mcp_servers/poc_tools.py nldt/services/mcp_servers/poc_server.py nldt/tests/test_live_sim_veenendaal_wrapper.py
git commit -m "feat(live-sim): proces veenendaal-gebiedscheck-run — replay nieuwste run / execute run.main(refresh=False), indicatorCount-summary"
```

---

### Task 5: Chain-registry, agent-resolver, server chain-API

**Files:**
- Create: `nldt/simulation/live/chains.py` (vervangt `fetch_script.py` — `git rm` op het oude bestand)
- Modify: `nldt/simulation/live/agent.py` (import + `args_uit_vorige` + inline_uit)
- Modify: `nldt/tests/live_sim_fakes.py` (FakeMcpClient: alle nieuwe tools)
- Modify: `nldt/simulation/live/server.py` (`GET /api/chains`, `POST /api/session {chain}`, 400)
- Modify: `nldt/tests/test_live_sim_agent.py` (chains-gebaseerd)
- Modify: `nldt/tests/test_live_sim_session.py` (chain-parameter + 400)
- Test: `nldt/tests/test_live_sim_chains.py` (nieuw)

**Interfaces:**
- Consumes: Tasks 1-4 (tools `run_artifact`, `gent_life_event_run`, `veenendaal_gebiedscheck_run`; bestaand `run_opportunity_map`, `run_bp2op_transform`, `run_value_scan`), `ScriptedAgent`/`SessionStore` (onveranderd contract, `start(agent_factory)`).
- Produces:
  - `chains.CHAINS: dict[str, dict]` met keys `id`, `label`, `stappen`; `chains.chain_met_mode(chain_id, mode) -> list[dict]` (test-hulp: kopie met pipeline-stappen op opgegeven mode).
  - Stap-model uitgebreid met optioneel `args_uit_vorige: callable(raw: str) -> dict` en laag-key `"inline_uit": "artifact_content"`.
  - `GET /api/chains -> [{"id", "label", "stepCount"}]`; `POST /api/session` met optionele JSON-body `{"chain": "<id>"}` (default `"utrecht"`), 400 bij onbekende chain.
  - Task 6 (UI) en Task 8 (E2E) bouwen hierop.

- [ ] **Step 1: Write the failing test**

`nldt/tests/test_live_sim_chains.py`:

```python
"""Chain-registry: zes chains, alle stappen naar geregistreerde tools, resolver-flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

NLDT_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = NLDT_ROOT / "simulation" / "live"
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import chains  # noqa: E402
from live_sim_fakes import FakeMcpClient  # noqa: E402

VERWACHT = {
    "utrecht": (8, 4),
    "eindhoven": (4, 0),
    "breda": (3, 1),
    "gent": (3, 0),
    "veenendaal": (3, 0),
    "dsorr": (4, 0),
}


def test_registry_heeft_zes_chains_met_verwachte_stappen_en_lagen():
    assert set(chains.CHAINS) == set(VERWACHT)
    for cid, (stappen, lagen) in VERWACHT.items():
        chain = chains.CHAINS[cid]
        assert chain["id"] == cid and chain["label"]
        assert len(chain["stappen"]) == stappen, cid
        assert len([s for s in chain["stappen"] if "laag" in s]) == lagen, cid


def test_alle_stappen_gebruiken_geregistreerde_tools():
    bekende = {
        ("catalog", "list_poc_capabilities"),
        ("dso", "dso_kb_overview"),
        ("dso", "dso_kb_annotations"),
        ("dso", "dso_kb_tpod"),
        ("poc", "fetch_geo_layer"),
        ("data", "list_entities"),
        ("data", "entities_to_geojson"),
        ("poc", "run_opportunity_map"),
        ("poc", "run_bp2op_transform"),
        ("poc", "run_value_scan"),
        ("poc", "gent_life_event_run"),
        ("poc", "veenendaal_gebiedscheck_run"),
        ("poc", "run_artifact"),
    }
    for chain in chains.CHAINS.values():
        for stap in chain["stappen"]:
            assert (stap["server"], stap["tool"]) in bekende, stap


def test_args_uit_vorige_resolvets_rundir_uit_pipeline_resultaat():
    raw = json.dumps(
        {
            "tool": "run_opportunity_map",
            "outputs": {"summary": {"mode": "execute", "runDir": "/x/runs/20261115-wind"}},
        }
    )
    stap = chains.CHAINS["utrecht"]["stappen"][-1]
    args = stap["args_uit_vorige"](raw)
    assert args == {"run_dir": "/x/runs/20261115-wind", "artifact": "zones.geojson"}


def test_chain_met_mode_geeft_kopie_met_andere_mode():
    origineel = chains.CHAINS["breda"]["stappen"]
    replay = chains.chain_met_mode("breda", "replay")
    assert origineel[1]["args"]["mode"] == "execute"  # productie blijft execute
    assert replay[1]["args"]["mode"] == "replay"  # kopie overgeschreven
    assert chains.CHAINS["breda"]["stappen"][1]["args"]["mode"] == "execute"  # onveranderd


def test_agent_draait_utrecht_chain_end_to_end_met_fake():
    import asyncio

    import agent

    events = []
    fake = FakeMcpClient()

    def emit(ev, data):
        events.append((ev, data))

    agent_ = agent.ScriptedAgent(fake, stappen=chains.CHAINS["utrecht"]["stappen"])
    result = asyncio.run(agent_.run(emit))
    namen = [ev for ev, _ in events]
    assert namen.count("step_started") == 8
    assert namen.count("tool_result") == 8
    assert namen.count("layer_ready") == 4
    assert namen[-1] == "run_done"
    assert result["status"] == "ok"
    # zones-laag komt uit run_artifact (artifact_content), niet de ruwe payload
    zones = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "utrecht-zones"]
    assert zones[0]["geojson"]["type"] == "FeatureCollection"
    # run_artifact kreeg de runDir uit de opportunity-map-stap
    run_artifact_calls = [c for c in fake.calls if c[1] == "run_artifact"]
    assert run_artifact_calls and "/fake-run/run_opportunity_map" in run_artifact_calls[0][2]["run_dir"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_chains.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chains'`.

- [ ] **Step 3: Write minimal implementation**

`nldt/simulation/live/chains.py` (volledig nieuw bestand):

```python
"""Chain-registry: zes PoC-chains, elke stap één MCP-toolcall.

Vervangt fetch_script.py. Stap-model: label, server, tool, args,
samenvatting(raw)->str, optioneel laag; nieuw: optioneel args_uit_vorige
(prev_raw:str)->dict — resolved vlak vóór de call, zodat een runDir uit het
vorige pipeline-resultaat expliciet doorvoert naar run_artifact. Geen
condities, geen LLM — "no invented numbers".
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
    payload = json.loads(raw)
    s = (payload.get("outputs") or {}).get("summary") or {}
    return f"{s.get('featureCount')} features · {s.get('title')}"


def _sum_entities(raw: str) -> str:
    ents = json.loads(raw)
    mock = any(isinstance(e, dict) and e.get("mock") for e in ents)
    return f"{len(ents)} entities{' (mock)' if mock else ''}"


def _sum_fc(raw: str) -> str:
    fc = json.loads(raw)
    return f"{len(fc.get('features') or [])} features"


def _sum_pipeline(raw: str) -> str:
    payload = json.loads(raw)
    s = (payload.get("outputs") or {}).get("summary") or {}
    run = (s.get("runDir") or "").replace("\\", "/").rsplit("/", 1)[-1] or "-"
    detail = s.get("verdict") or s.get("uitkomst") or s.get("outcome") or s.get("indicatorCount") or ""
    return f"{s.get('mode', 'execute')} · {run}" + (f" · {detail}" if detail != "" else "")


def _sum_artifact(raw: str) -> str:
    payload = json.loads(raw)
    a = (payload.get("outputs") or {}).get("artifact") or {}
    return f"{a.get('name')} · {a.get('kind')} · {a.get('bytes')}B"


def _run_dir_uit_vorige(artifact: str):
    def resolve(raw: str) -> dict:
        payload = json.loads(raw)
        s = (payload.get("outputs") or {}).get("summary") or {}
        run_dir = s.get("runDir")
        if not run_dir:
            raise ValueError("vorige stap gaf geen runDir — artifact niet te resolven")
        return {"run_dir": run_dir, "artifact": artifact}

    return resolve


NGSI_LAAG = {"source_id": "ngsi-ld-dpl-airquality", "laagtype": "punten", "inline": True}

CHAINS: dict[str, dict[str, Any]] = {
    "utrecht": {
        "id": "utrecht",
        "label": "PoC-1 · Utrecht (wind)",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Inclusion-zone wind (agrest)", "server": "poc", "tool": "fetch_geo_layer",
             "args": {"source_id": "agrest-ov-gebied-windenergie"},
             "laag": {"source_id": "agrest-ov-gebied-windenergie", "laagtype": "zone"},
             "samenvatting": _sum_poc_tool},
            {"label": "Kaartlaag wind (ArcGIS Online)", "server": "poc", "tool": "fetch_geo_layer",
             "args": {"source_id": "arcgis-et-wind-gebieden"},
             "laag": {"source_id": "arcgis-et-wind-gebieden", "laagtype": "zone"},
             "samenvatting": _sum_poc_tool},
            {"label": "NGSI-LD entities (lucht)", "server": "data", "tool": "list_entities",
             "args": {"entity_type": "AirQualityObserved"}, "samenvatting": _sum_entities},
            {"label": "NGSI-LD → GeoJSON", "server": "data", "tool": "entities_to_geojson",
             "args": {"entity_type": "AirQualityObserved"}, "laag": NGSI_LAAG, "samenvatting": _sum_fc},
            {"label": "Opportunity-map engine (wind)", "server": "poc", "tool": "run_opportunity_map",
             "args": {"mode": "execute", "useCase": "wind"}, "samenvatting": _sum_pipeline},
            {"label": "Zonelaag uit de engine-run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("zones.geojson"),
             "laag": {"source_id": "utrecht-zones", "laagtype": "zone", "inline": True,
                      "inline_uit": "artifact_content"},
             "samenvatting": _sum_artifact},
        ],
    },
    "eindhoven": {
        "id": "eindhoven",
        "label": "PoC-2 · BP→OP Eindhoven",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "BP→OP-omzetting (engine)", "server": "poc", "tool": "run_bp2op_transform",
             "args": {"mode": "execute", "useCase": "eindhoven"}, "samenvatting": _sum_pipeline},
            {"label": "Omzettabel uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("omzettabel.json"), "samenvatting": _sum_artifact},
        ],
    },
    "breda": {
        "id": "breda",
        "label": "PoC-4 · Breda vijf-waarden",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Vijf-waardenscan (engine)", "server": "poc", "tool": "run_value_scan",
             "args": {"mode": "execute"}, "samenvatting": _sum_pipeline},
            {"label": "Buurtkaart uit de scan", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("geo-buurten.wgs84.geojson"),
             "laag": {"source_id": "breda-buurten", "laagtype": "zone", "inline": True,
                      "inline_uit": "artifact_content"},
             "samenvatting": _sum_artifact},
        ],
    },
    "gent": {
        "id": "gent",
        "label": "Gent · EUROPAI-piloot",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Levensgebeurtenis-replay (fase 1+2+3)", "server": "poc",
             "tool": "gent_life_event_run",
             "args": {"mode": "execute", "package": "gent-mobiliteit-ondernemer", "persona": "sanne"},
             "samenvatting": _sum_pipeline},
            {"label": "Run-registratie uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("run.json"), "samenvatting": _sum_artifact},
        ],
    },
    "veenendaal": {
        "id": "veenendaal",
        "label": "Veenendaal · Spoorzone",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "74-item gebiedscheck (engine)", "server": "poc",
             "tool": "veenendaal_gebiedscheck_run", "args": {"mode": "execute"},
             "samenvatting": _sum_pipeline},
            {"label": "Indicatoren uit de run", "server": "poc", "tool": "run_artifact",
             "args_uit_vorige": _run_dir_uit_vorige("indicators.json"), "samenvatting": _sum_artifact},
        ],
    },
    "dsorr": {
        "id": "dsorr",
        "label": "DSO ↔ RegelRecht",
        "stappen": [
            {"label": "Wat is beschikbaar?", "server": "catalog", "tool": "list_poc_capabilities",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Regels-instrumenten in het gebied", "server": "dso", "tool": "dso_kb_overview",
             "args": {}, "samenvatting": _count_top_level},
            {"label": "Annotaties Utrecht Domplein", "server": "dso", "tool": "dso_kb_annotations",
             "args": {"instrument": "utrecht-domplein"}, "samenvatting": _count_top_level},
            {"label": "TPOD-profiel Utrecht Domplein", "server": "dso", "tool": "dso_kb_tpod",
             "args": {"instrument": "utrecht-domplein"}, "samenvatting": _count_top_level},
        ],
    },
}

_PIPELINE_TOOLS = {
    "run_opportunity_map",
    "run_bp2op_transform",
    "run_value_scan",
    "gent_life_event_run",
    "veenendaal_gebiedscheck_run",
}


def chain_met_mode(chain_id: str, mode: str) -> list[dict[str, Any]]:
    """Test-hulp: diepe kopie van de stappen met pipeline-stappen op `mode`."""
    uit = []
    for stap in CHAINS[chain_id]["stappen"]:
        s = dict(stap)
        if s.get("tool") in _PIPELINE_TOOLS:
            s["args"] = {**s["args"], "mode": mode}
        uit.append(s)
    return uit
```

Verwijder het oude bestand: `git rm nldt/simulation/live/fetch_script.py`.

In `nldt/simulation/live/agent.py`:

vervang `from fetch_script import STAPPEN` door:

```python
from chains import CHAINS
```

vervang in `ScriptedAgent.__init__`:

```python
        self.stappen = stappen if stappen is not None else CHAINS["utrecht"]["stappen"]
```

vervang de lus-body (vóór `t0 = ...`) zodat args en vorige-raw doorstromen:

```python
        per_stap: list[dict[str, Any]] = []
        vorige_raw: str | None = None
        for i, stap in enumerate(self.stappen):
            args = stap["args_uit_vorige"](vorige_raw) if "args_uit_vorige" in stap else stap["args"]
            emit(
                "step_started",
                {
                    "index": i,
                    "label": stap["label"],
                    "server": stap["server"],
                    "tool": stap["tool"],
                    "args": args,
                },
            )
            t0 = time.perf_counter()
            try:
                raw = await self.client.call_tool(stap["server"], stap["tool"], args)
                vorige_raw = raw
```

en de laag-emit wordt:

```python
            laag = stap.get("laag")
            if laag:
                event: dict[str, Any] = {"laagtype": laag["laagtype"], "source_id": laag["source_id"]}
                if laag.get("inline"):
                    obj = _json_object(raw)
                    if laag.get("inline_uit") == "artifact_content":
                        obj = obj["outputs"]["artifact"]["content"]
                    event["geojson"] = obj
                emit("layer_ready", event)
```

In `nldt/tests/live_sim_fakes.py` — breid `FakeMcpClient.call_tool` uit (vóór de bestaande takken; de classes krijgt ook een class-level call-log voor de chains-test):

```python
class FakeMcpClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on  # (server, tool) die RuntimeError werpt

    async def call_tool(self, server: str, tool: str, args: dict) -> str:
        self.calls.append((server, tool, args))
        if self.fail_on and (server, tool) == self.fail_on:
            raise RuntimeError("broker onbereikbaar")
        if tool == "run_artifact":
            return json.dumps(
                {
                    "tool": "run_artifact",
                    "processId": "run-artifact",
                    "status": "successful",
                    "outputs": {
                        "artifact": {
                            "name": args.get("artifact"),
                            "path": f"{args.get('run_dir')}/{args.get('artifact')}",
                            "kind": "geojson" if str(args.get("artifact", "")).endswith(".geojson") else "json",
                            "bytes": 42,
                            "content": {
                                "type": "FeatureCollection",
                                "features": [
                                    {
                                        "type": "Feature",
                                        "id": "fakelayer-1",
                                        "properties": {},
                                        "geometry": {"type": "Point", "coordinates": [5.12, 52.09]},
                                    }
                                ],
                            },
                        }
                    },
                }
            )
        if tool in {
            "run_opportunity_map",
            "run_bp2op_transform",
            "run_value_scan",
            "gent_life_event_run",
            "veenendaal_gebiedscheck_run",
        }:
            return json.dumps(
                {
                    "tool": tool,
                    "processId": tool,
                    "status": "successful",
                    "outputs": {
                        "summary": {
                            "mode": args.get("mode", "execute"),
                            "runDir": f"/tmp/fake-run/{tool}",
                            "runId": "fake-run",
                            "verdict": "ok",
                        }
                    },
                }
            )
        # ... bestaande takken ongewijzigd (fetch_geo_layer, list_entities,
        # entities_to_geojson, default)
```

(let op: houd de bestaande takken voor `fetch_geo_layer` / `list_entities` / `entities_to_geojson` en de default exact zoals ze waren; alleen het `__init__`-hoofd en de twee nieuwe takken komen erbij.)

In `nldt/simulation/live/server.py`:

voeg bovenaan toe (naast de bestaande imports): `import chains`.

vervang `_default_tool_client_factory` (levert nu een **client**, geen ScriptedAgent — de agent wordt met de chain-stappen in `agent_factory` gebouwd):

```python
    def _default_tool_client_factory():
        base = os.environ.get("NLDT_LIVE_SIM_BASE") or (
            f"http://127.0.0.1:{os.environ.get('NLDT_LIVE_SIM_PORT', '8095')}"
        )
        return McpLoopbackClient(base)
```

vervang de hele oude `start_session`-definitie door het onderstaande blok (inclusief nieuw `GET /api/chains`; `chain` komt als **query-parameter** binnen — plain default-parameter in FastAPI, en de UI POST't naar `/api/session?chain=<id>`):

```python
    @app.get("/api/chains")
    def list_chains():
        return [
            {"id": c["id"], "label": c["label"], "stepCount": len(c["stappen"])}
            for c in chains.CHAINS.values()
        ]

    @app.post("/api/session")
    async def start_session(chain: str = "utrecht"):
        if chain not in chains.CHAINS:
            raise HTTPException(status_code=400, detail=f"onbekende chain: {chain}")
        factory = tool_client_factory or _default_tool_client_factory

        def agent_factory():
            gekozen = factory()
            # compat: een geïnjecteerde factory mag een ScriptedAgent (oud
            # test-contract) of een client (productie-contract) teruggeven
            client = gekozen.client if isinstance(gekozen, ScriptedAgent) else gekozen
            return ScriptedAgent(client, stappen=chains.CHAINS[chain]["stappen"])

        try:
            sid = store.start(agent_factory)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"sessionId": sid, "chain": chain}
```

In `nldt/tests/test_live_sim_agent.py`:

vervang de import `from fetch_script import STAPPEN`-gebruik: voeg toe `import chains` en verander de drie agent-tests zodat ze expliciete stappen gebruiken:

- `test_agent_event_volgorde_deterministisch`: `agent.run_sync(agent.ScriptedAgent(fake, stappen=chains.CHAINS["utrecht"]["stappen"]), emit)` en verwacht `step_started == 8`, `tool_result == 8`, `layer_ready == 4`, laatste event `run_done`; de call-volgorde-vergelijking blijft (`[(c[:2]) for c in fake.calls] == [(s["server"], s["tool"]) for s in chains.CHAINS["utrecht"]["stappen"]]`); de inline-NGSI-laag-assert blijft (source_id `ngsi-ld-dpl-airquality`); de zone-lagen-assert krijgt er `utrecht-zones` bij: `{z["source_id"] for z in zone_lagen} == {"agrest-ov-gebied-windenergie", "arcgis-et-wind-gebieden", "utrecht-zones"}`.
- `test_agent_stopt_met_error_event`: fail_on `("poc", "fetch_geo_layer")` blijft; `len(fake.calls) == 3` blijft (de fout zit op stap 3).
- `test_script_heeft_zes_stappen_drie_lagen` vervang je door de nieuwe chains-test in `test_live_sim_chains.py` — verwijder de oude test uit dit bestand.
- `test_session_store_stream_sluit_en_bezet` en `ScriptedAgentMetFake` blijven werken (default stappen = utrecht-chain; de fake beantwoordt alle tools).

In `nldt/tests/test_live_sim_session.py`:

- de twee bestaande tests blijven werken (default chain utrecht; de fake beantwoordt alle 8 stappen — pas event-count-asserts aan naar 8/8/4).
- voeg toe:

```python
def test_chain_parameter_en_onbekende_chain_400():
    app = server.create_app(tool_client_factory=lambda: ScriptedAgent(FakeMcpClient()))
    with httpx.Client(transport=httpx.ASGITransport(app=app), timeout=20.0) as http:
        resp = http.post("http://test/api/session", params={"chain": "dsorr"})
        assert resp.status_code == 200
        assert resp.json()["chain"] == "dsorr"
        _lees_sse(http, f"http://test/api/session/{resp.json()['sessionId']}/events")

        slecht = http.post("http://test/api/session", params={"chain": "nietbestaand"})
        assert slecht.status_code == 400
```

en pas de chains-opvolgtest aan: na het leeglezen van de eerste sessie kan een tweede sessie met een ANDERE chain starten (bijv. `chain=gent`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_chains.py tests/test_live_sim_agent.py tests/test_live_sim_session.py -v`
Expected: alle groen (chains 5, agent 3, session 3). Daarna de hele familie: `... tests/test_live_sim_server.py tests/test_live_sim_ui.py tests/test_live_sim_e2e.py -q` — de UI-test kan nu falen (er is nog geen switcher — komt in Task 6; de e2e-test faalt nog op de nieuwe default chain van 8 stappen: pas in het E2E-bestand NOG NIETS aan — Task 8 herschrijft hem; markeer voor nu de oude e2e-test met `@pytest.mark.skip(reason="herschreven in Task 8")` boven de testfunctie en commit die skip mee).

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/live/chains.py nldt/simulation/live/agent.py nldt/simulation/live/server.py nldt/tests/live_sim_fakes.py nldt/tests/test_live_sim_agent.py nldt/tests/test_live_sim_session.py nldt/tests/test_live_sim_chains.py nldt/tests/test_live_sim_e2e.py
git rm nldt/simulation/live/fetch_script.py
git commit -m "feat(live-sim): chain-registry (6 PoC-chains) + args_uit_vorige-runDir-doorvoer + server /api/chains en POST {chain} (400 onbekend); fetch_script.py opgeheven in chains.py"
```

---

### Task 6: UI — PoC-switcher

**Files:**
- Modify: `nldt/simulation/live/index.html` (header: chips-rij; JS: chains laden, selectie, POST met `?chain=`)
- Test: `nldt/tests/test_live_sim_ui.py` (uitbreiden)

**Interfaces:**
- Consumes: `GET /api/chains`, `POST /api/session?chain=<id>` (Task 5).
- Produces: startpagina met `id="chain-switcher"` (chips, actieve chip klasse `active`), start-knop start de geselecteerde chain. Bestaande naalden blijven bestaan.

- [ ] **Step 1: Extend the failing test**

In `nldt/tests/test_live_sim_ui.py`, breid de naald-lijst uit:

```python
    for naald in ('id="kaart"', 'id="trace"', 'id="start"', 'id="ngsi-badge"',
                  'id="chain-switcher"', "EventSource", "/api/session", "/api/chains"):
        assert naald in html, f"index.html mist {naald}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_ui.py -v`
Expected: FAIL — mist `id="chain-switcher"` en `/api/chains`.

- [ ] **Step 3: Implement**

In `nldt/simulation/live/index.html`:

CSS toevoegen:

```css
  #chain-switcher{display:flex;gap:6px;flex-wrap:wrap}
  #chain-switcher .chip{border:1px solid var(--line2);border-radius:999px;padding:4px 12px;
    font-size:12px;color:var(--faint);cursor:pointer;background:var(--panel)}
  #chain-switcher .chip.active{color:#04121f;background:var(--acc);border-color:var(--acc);font-weight:600}
```

Header tussen de sub-tekst en de start-knop:

```html
  <div id="chain-switcher"></div>
```

JS — bovenaan de script-sectie:

```javascript
let gekozenChain = "utrecht";
const elSwitcher = document.getElementById("chain-switcher");

async function laadChains() {
  const resp = await fetch("/api/chains");
  if (!resp.ok) return;
  for (const c of await resp.json()) {
    const knop = document.createElement("button");
    knop.className = "chip" + (c.id === gekozenChain ? " active" : "");
    knop.textContent = c.label;
    knop.dataset.chain = c.id;
    knop.addEventListener("click", () => {
      gekozenChain = c.id;
      elSwitcher.querySelectorAll(".chip").forEach(k =>
        k.classList.toggle("active", k.dataset.chain === c.id));
    });
    elSwitcher.appendChild(knop);
  }
}
laadChains();
```

en in `start()` verandert de POST-regel in:

```javascript
    const resp = await fetch(`/api/session?chain=${encodeURIComponent(gekozenChain)}`, {method: "POST"});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_ui.py tests/test_live_sim_session.py tests/test_live_sim_chains.py -v`
Expected: groen. Handmatige check: `cd nldt && .venv/bin/python simulation/live/server.py` → open pagina → zes chips zichtbaar, dsorr-chain draait (4 stappen, geen lagen, kaart leeg), Ctrl-C.

- [ ] **Step 5: Commit**

```bash
git add nldt/simulation/live/index.html nldt/tests/test_live_sim_ui.py
git commit -m "feat(live-sim): PoC-switcher in de UI — chips uit /api/chains, POST ?chain=, actieve chip gemarkeerd"
```

---

### Task 7: Offline-precondities committeren

**Files:**
- Commit: subset van `poc-breda/runs/20260913T192628Z-breda-scan/` (alleen `run_summary.json`, `value-scan.json`, `geo-buurten.wgs84.geojson`), subset van `poc-gent/runs/20261102T121500Z-gent-transactional-fien/` (alleen `run.json`)
- Test: `nldt/tests/test_live_sim_precondities.py` (nieuw)

**Interfaces:**
- Consumes: niets.
- Produces: gecommitte canonical run-dirs zodat de Task 8-E2E's (replay + run_artifact) op een fresh clone draaien. `_latest_dir`-volgorde: lokaal kunnen nieuwere untracked runs bestaan — de E2E geeft daarom nooit een lege `runDir` op maar vertrouwt op de nieuwste; op een fresh clone is dat de gecommitte.

- [ ] **Step 1: Write the failing test**

```python
"""Offline-precondities voor de chain-E2E's: canonical runs zijn gecommit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _tracked(rel: str) -> bool:
    uit = subprocess.run(
        ["git", "ls-files", rel], cwd=str(REPO), capture_output=True, text=True
    )
    return bool(uit.stdout.strip())


def test_breda_canonical_subset_gecommit():
    basis = "poc-breda/runs/20260913T192628Z-breda-scan"
    for naam in ("run_summary.json", "value-scan.json", "geo-buurten.wgs84.geojson"):
        assert _tracked(f"{basis}/{naam}"), f"{basis}/{naam} is niet gecommit"


def test_gent_canonical_run_gecommit():
    assert _tracked("poc-gent/runs/20261102T121500Z-gent-transactional-fien/run.json")


def test_overige_canonical_runs_gecommit():
    assert _tracked("poc-bp2op/runs/20260830-124515-eindhoven/run_summary.json")
    assert _tracked("poc-veenendaal/runs/20261106T151732Z-gebiedscheck/indicators.json")
    assert _tracked("poc/runs/20260830T113234Z-wind/zones.geojson")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_precondities.py -v`
Expected: FAIL op de breda- en gent-asserts (nog niet gecommit). Als ook de overige faien, voeg die toe met hetzelfde patroon.

- [ ] **Step 3: Commit the preconditions**

Voeg exact de bestanden toe die de falende test noemt (de breda- en gent-subsets zijn verwacht; als ook een overige assert faalt, force-add die op dezelfde manier — zelfde patroon als de cache-twins):

```bash
git add poc-breda/runs/20260913T192628Z-breda-scan/run_summary.json poc-breda/runs/20260913T192628Z-breda-scan/value-scan.json poc-breda/runs/20260913T192628Z-breda-scan/geo-buurten.wgs84.geojson poc-gent/runs/20261102T121500Z-gent-transactional-fien/run.json
git commit -m "chore(live-sim): canonical run-subsets gecommit als offline-preconditie voor chain-E2E's (breda: summary+scan+buurtkaart, gent: run.json)"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_precondities.py -v`
Expected: 3 PASSED.

---

### Task 8: E2E per chain + README

**Files:**
- Modify: `nldt/tests/test_live_sim_e2e.py` (herschrijven: zes chain-E2E's, verwijder de Task 5-skip)
- Modify: `nldt/simulation/live/README.md` (chains, switcher, timing)
- Test: zelfde bestand (de E2E's zíjn de tests)

**Interfaces:**
- Consumes: alles (Tasks 1-7). Elke E2E draait de volledige chain over écht MCP-loopback; zware pipeline-stappen draaien in replay via `chains.chain_met_mode` (productie blijft execute — de user ziet execute in de demo; replay is hier bewust: deterministisch, offline, geen multi-minuten tests).
- Produces: integratie-bewijs per chain: stap-tellingen, runDir-doorvoer (run_artifact krijgt de echte runDir), inline-lagen (utrecht zones + breda buurten), run_done zonder error.

- [ ] **Step 1: Write the failing tests**

Vervang de inhoud van `nldt/tests/test_live_sim_e2e.py` (fixture `_vrije_poort`/`e2e` blijft staan zoals hij is — monkeypatch van data_platform-attrs + `NLDT_LIVE_SIM_BASE`; voeg bovenaan toe `import chains` en `from live_sim_fakes import FakeMcpClient` — nee: de E2E gebruikt de ECHTE default factory (echte MCP), alleen de chains-modes worden met `chain_met_mode` op replay gezet):

```python
"""E2E per chain over echt MCP-loopback, offline (cache + gecommitte runs).

Productie-chains draaien execute; in deze E2E staan de pipeline-stappen op
replay (chains.chain_met_mode) zodat elke chain deterministisch en offline in
seconden draait en het hele wiring bewijst: registry → agent → echte MCP →
executor → runDir-doorvoer → run_artifact → events/lagen.
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

import chains  # noqa: E402
import server  # noqa: E402


def _vrije_poort():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def e2e(monkeypatch):
    from services.adapters import data_platform

    monkeypatch.setattr(data_platform, "NGSI_LD_URL", "")
    monkeypatch.setattr(data_platform, "DATA_PLATFORM_URL", "")
    monkeypatch.setattr(data_platform, "MOCK", True)

    port = _vrije_poort()
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


def _lees_events(http, base, chain):
    resp = http.post(f"{base}/api/session", params={"chain": chain})
    assert resp.status_code == 200, resp.text
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


def _basis_asserts(events, stappen_count, lagen_count):
    namen = [ev for ev, _ in events]
    assert "error" not in namen, [d for ev, d in events if ev == "error"]
    assert namen.count("step_started") == stappen_count
    assert namen.count("tool_result") == stappen_count
    assert all(d["ok"] for ev, d in events if ev == "tool_result")
    assert namen.count("layer_ready") == lagen_count
    assert namen[-1] == "run_done"


def test_chains_endpoint_noemt_zes_chains(e2e):
    with httpx.Client(timeout=30.0) as http:
        resp = http.get(f"{e2e}/api/chains")
    assert resp.status_code == 200
    lijst = resp.json()
    assert {c["id"] for c in lijst} == {"utrecht", "eindhoven", "breda", "gent", "veenendaal", "dsorr"}


def test_e2e_utrecht(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "utrecht": {**chains.CHAINS["utrecht"], "stappen": chains.chain_met_mode("utrecht", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "utrecht")
        _basis_asserts(events, 8, 4)
        # zones-laag is inline geojson uit run_artifact (canonical wind-run)
        zones = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "utrecht-zones"]
        assert zones and zones[0]["geojson"]["type"] == "FeatureCollection"
        # fetch-lagen zijn via /api/layers op te halen
        for sid in ("agrest-ov-gebied-windenergie", "arcgis-et-wind-gebieden"):
            resp = http.get(f"{e2e}/api/layers/{sid}")
            assert resp.status_code == 200
            assert resp.json()["type"] == "FeatureCollection"


def test_e2e_breda(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "breda": {**chains.CHAINS["breda"], "stappen": chains.chain_met_mode("breda", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "breda")
        _basis_asserts(events, 3, 1)
        buurt = [d for ev, d in events if ev == "layer_ready" and d.get("source_id") == "breda-buurten"]
        assert buurt and buurt[0]["geojson"]["type"] == "FeatureCollection"
        assert buurt[0]["geojson"]["features"], "buurtkaart heeft features"


def test_e2e_eindhoven(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "eindhoven": {**chains.CHAINS["eindhoven"], "stappen": chains.chain_met_mode("eindhoven", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "eindhoven")
        _basis_asserts(events, 4, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "omzettabel.json" in art["summary"]


def test_e2e_gent(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "gent": {**chains.CHAINS["gent"], "stappen": chains.chain_met_mode("gent", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "gent")
        _basis_asserts(events, 3, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "run.json" in art["summary"]


def test_e2e_veenendaal(e2e, monkeypatch):
    monkeypatch.setattr(chains, "CHAINS", {**chains.CHAINS, "veenendaal": {**chains.CHAINS["veenendaal"], "stappen": chains.chain_met_mode("veenendaal", "replay")}})
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "veenendaal")
        _basis_asserts(events, 3, 0)
        art = [d for ev, d in events if ev == "tool_result"][-1]
        assert "indicators.json" in art["summary"]


def test_e2e_dsorr(e2e):
    with httpx.Client(timeout=120.0) as http:
        events = _lees_events(http, e2e, "dsorr")
        _basis_asserts(events, 4, 0)
```

(let op: de oude `test_volledige_keten_over_echt_mcp` vervalt — de zes nieuwe E2E's dekken hem af; verwijder de Task 5-skip.)

- [ ] **Step 2: Run the tests**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_e2e.py -v`
Expected: 7 PASSED. Waar ze falen: debug de keten — meest voorkomend: `_latest_dir` pakt een lokale, ongecommitte nieuwere run met andere artifact-namen (los op door in de replay-override de stap-args expliciet een `runDir` mee te geven op de gecommitte canonical dir via `chain_met_mode` + extra arg-patch in de test, documenteer die patch in de test), of een artifact heet anders in de canonical run (verifieer met `ls` op de run-dir en gebruik de echte naam in de chain-definitie).

- [ ] **Step 3: Update the README**

In `nldt/simulation/live/README.md`, vervang de stappenlijst-sectie door de chain-tabel en voeg de switcher/timing toe:

```markdown
## Chains (zes PoC's uit simulation.html)

De pagina heeft een PoC-switcher; elke chain is een vaste stappenlijst waarin
elke stap één echte MCP-toolcall is:

| Chain | Stappen (kern) | Kaartlagen | Duur |
|---|---|---|---|
| PoC-1 · Utrecht (wind) | capabilities → dso-kb → 2× fetch_geo_layer → NGSI ×2 → `run_opportunity_map(execute, wind)` → `run_artifact(zones.geojson)` | 4 | ~10–60 s (engine) |
| PoC-2 · BP→OP Eindhoven | capabilities → dso-kb → `run_bp2op_transform(execute)` → `run_artifact(omzettabel.json)` | — | seconden |
| PoC-4 · Breda vijf-waarden | capabilities → `run_value_scan(execute)` → `run_artifact(geo-buurten.wgs84.geojson)` | buurtkaart | seconden |
| Gent · EUROPAI-piloot | capabilities → `gent_life_event_run(execute)` → `run_artifact(run.json)` | — | seconden |
| Veenendaal · Spoorzone | capabilities → `veenendaal_gebiedscheck_run(execute)` → `run_artifact(indicators.json)` | — | seconden |
| DSO ↔ RegelRecht | capabilities → dso-kb → `dso_kb_annotations` → `dso_kb_tpod` | — | instant |

`run_artifact` leest pipeline-output (zones, buurtkaart, tabellen) via MCP en
geeft de inhoud inline terug; de `runDir` komt letterlijk uit het resultaat
van de pipeline-stap (`args_uit_vorige`) — geen verzonnen paden. Zware
pipeline-stappen executeren echt (cache-first voor data); de SSE-stream blijft
levend door `asyncio.to_thread` in de tool-lagen.
```

- [ ] **Step 4: Run the complete suite**

Run: `cd nldt && .venv/bin/python -m pytest tests/test_live_sim_async_tools.py tests/test_live_sim_fetch_geo_layer.py tests/test_live_sim_poc_tool.py tests/test_live_sim_run_artifact.py tests/test_live_sim_gent_wrapper.py tests/test_live_sim_veenendaal_wrapper.py tests/test_live_sim_chains.py tests/test_live_sim_agent.py tests/test_live_sim_server.py tests/test_live_sim_session.py tests/test_live_sim_ui.py tests/test_live_sim_precondities.py tests/test_live_sim_e2e.py -q`
Expected: alles groen.

- [ ] **Step 5: Commit**

```bash
git add nldt/tests/test_live_sim_e2e.py nldt/simulation/live/README.md
git commit -m "feat(live-sim): E2E per chain over echt MCP-loopback (replay-modes, runDir-doorvoer, inline-lagen) + README chain-tabel en timing"
```

---

## Zelfreview-notities (uitgevoerd)

- **Specdekking**: chain-registry ✓ (T5), twee wrappers ✓ (T3/T4), run_artifact ✓ (T2), to_thread ✓ (T1), server-API ✓ (T5), UI-switcher ✓ (T6), offline-precondities ✓ (T7), E2E per chain ✓ (T8), testing-matrix uit de spec ✓ (verdeeld over T1-T8). Bewuste keuzes: `POST /api/session` gebruikt query-parameter `?chain=` (geen JSON-body) — simpelst en consistent met de UI-fetch; de E2E's draaien replay-modes (`chain_met_mode`) i.p.v. execute om offline-deterministisch te blijven; productie blijft execute per spec.
- **Typeconsistentie**: stap-keys (`label`, `server`, `tool`, `args`, `samenvatting`, `laag`, `args_uit_vorige`, `inline_uit`) consistent door chains.py/agent.py/fakes/tests; `summary.runDir`-doorvoer via `args_uit_vorige` in alle vier pipeline-chains; toolnamen exact zoals geverifieerd in `poc_server.py`.
- **Geen placeholders**: alle stappen bevatten volledige code en exacte commando's. De twee bewust-vervangen codeblokken in Task 5 (server `start_session`) zijn duidelijk gemarkeerd als "NIET bruikbaar" vs "gebruik exact dit".
