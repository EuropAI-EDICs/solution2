# Utrecht-harness unificatie Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Executiestatus (2026-10-06):** M1–M3 geïmplementeerd via inline executing-plans. Eén
> deviatie: `deep-agents/mcp_client.py` is gebouwd direct op de mcp-SDK 2.x (dezelfde pin als
> nldt) in plaats van `langchain-mcp-adapters` — die vereist mcp<2 en is daarmee incompatibel
> met de nldt-servers; interfaces (`build_client_config`, `load_mcp_tools`) ongewijzigd.
> Daarbij: `build_world_scene` is als poc-MCP-tool geregistreerd (stond al in POC_TOOLS maar
> was nooit blootgesteld). Eindverificatie: nldt 362 passed, poc 295 passed/1 skipped;
> live-ketencheck (execute_process → journal-regel in deep-agents/runs/live/steps.jsonl) OK.

**Goal:** deep-agents wordt het planningvlak op de nldt-execution harness: alle nldt-capabiliteit via MCP (M1), live `LLMHook` voor S1/S2 (M2), één gedeeld journal-format (M3).

**Architecture:** Vier lagen (Surface → Planningvlak → Operations/MCP → Execution harness). deep-agents verliest zijn filesystem-wrappers voor nldt-capabiliteit; gates/HITL/prov blijven in de harness. Modelconfig wordt gedeeld via `nldt/services/common/model_config.py`; het journal-format van deep-agents wordt het enige trajectory-format.

**Tech Stack:** Python 3.13+, `mcp` (MCPServer, streamable-HTTP), `langchain-mcp-adapters` (nieuw in deep-agents), `langchain-ollama` / `langchain-anthropic`, pytest.

**Spec:** [`docs/superpowers/specs/2026-10-06-utrecht-harness-unificatie-design.md`](../specs/2026-10-06-utrecht-harness-unificatie-design.md)

## Global Constraints

- Alleen lokale Ollama-modellen; cloud alleen via expliciet `zai:`-prefix (`models.py`-doctrine; `:cloud`-namen weigeren).
- Gates, risicotiers, HITL-verdicts en `prov.json` blijven in de harness (process-adapter + PoC-pipeline); deep-agents mag alleen lezen of via MCP aanvragen.
- Bestaande suites blijven groen: `poc/tests/` (295 passed/1 skipped) en `nldt/tests/`.
- Tests draaien met: `cd /Users/marc/Projecten/ldttoolbox/nldt && /Users/marc/Projecten/ldttoolbox/nldt/.venv/bin/python -m pytest tests -q` (de nldt-venv heeft pytest 9.1.1; de systeem-python niet).
- nldt-modules importeren via `services.*` / `agents.*` — tests draaien met cwd `nldt/` (bestaand patroon, zie `nldt/tests/test_poc_processes.py`).
- Werkbank: `/Users/marc/Projecten/ldttoolbox` (main). Commit-stijl van de repo: `feat(nldt): …`, `test(nldt): …`, `feat(deep-agents): …`, Nederlands.
- Read-only MCP-tools retourneren JSON-strings (`json.dumps(..., indent=2, default=str)`) — bestaand serverpatroon.

---

## M1 — MCP-contract

### Task 1: Read-only operaties als pure functies (`poc_readops.py`)

**Files:**
- Create: `nldt/services/process_adapter/poc_readops.py`
- Test: `nldt/tests/test_poc_readops.py`

**Interfaces:**
- Consumes: canonieke run-artefacten onder `poc/runs/<runId>/` (`prov.json`, `layers.json`, `zones.json` — geverifieerd: `prov.json` heeft sleutel `entity` (lijst); `layers.json` is dict keyed by zoneId; `zones.json` is lijst (of FeatureCollection) van zone-entries met `zoneId`).
- Produces: `get_provenance(run_id: str, runs_dir: Path | None = None) -> dict`, `inspect_geo_layer(run_id: str, layer: str, runs_dir: Path | None = None) -> dict`, `crosscheck_formal_rule(scenario_run_id: str, formal_rule_id: str, runs_dir: Path | None = None) -> dict`. Task 2 registreert deze functies als MCP-tools; `runs_dir` is de test-injectie-aansluiting.

- [ ] **Step 1: Schrijf de falende tests**

```python
# nldt/tests/test_poc_readops.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.process_adapter.poc_readops import (
    crosscheck_formal_rule,
    get_provenance,
    inspect_geo_layer,
)


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "20261006T120133Z-biomassa"
    d.mkdir()
    (d / "prov.json").write_text(json.dumps({
        "flavour": "poc", "runId": "20261006T120133Z-biomassa",
        "entity": [
            {"id": "e1", "type": "NormCard", "generatedBy": "NormAnalyst", "sha256": "abc"},
            {"id": "e2", "type": "ZoneResult", "generatedBy": "ZoneEngine", "extra": "drop"},
        ],
    }), encoding="utf-8")
    (d / "layers.json").write_text(json.dumps({
        "gebied_energie_biomassa_landelijk": {
            "zoneId": "gebied_energie_biomassa_landelijk",
            "aliasSourceId": "agrest-ov-gebied-energie-biomassa-landelijk",
            "title": "Gebied energie uit biomassa landelijk gebied",
        },
    }), encoding="utf-8")
    (d / "zones.json").write_text(json.dumps([
        {"zoneId": "gebied_energie_biomassa_landelijk", "areaKm2": 1560.054},
        {"zoneId": "aoi", "areaKm2": 1560.054},
    ]), encoding="utf-8")
    return d


def test_get_provenance_maps_entities(run_dir: Path) -> None:
    out = get_provenance("20261006T120133Z-biomassa", runs_dir=run_dir.parent)
    assert out["runId"] == "20261006T120133Z-biomassa"
    assert out["entities"][0] == {"id": "e1", "type": "NormCard", "generatedBy": "NormAnalyst", "sha256": "abc"}
    assert "extra" not in out["entities"][1]


def test_get_provenance_missing_run_is_explicit_error(run_dir: Path) -> None:
    out = get_provenance("bestaatniet", runs_dir=run_dir.parent)
    assert "error" in out and "bestaatniet" in out["error"]


def test_inspect_geo_layer_returns_meta_and_matching_zones(run_dir: Path) -> None:
    out = inspect_geo_layer("20261006T120133Z-biomassa", "gebied_energie_biomassa_landelijk", runs_dir=run_dir.parent)
    assert out["meta"]["aliasSourceId"] == "agrest-ov-gebied-energie-biomassa-landelijk"
    assert out["zoneCount"] == 1
    assert out["zones"][0]["areaKm2"] == 1560.054


def test_inspect_geo_layer_unknown_layer_lists_available(run_dir: Path) -> None:
    out = inspect_geo_layer("20261006T120133Z-biomassa", "onbekend", runs_dir=run_dir.parent)
    assert "error" in out
    assert "gebied_energie_biomassa_landelijk" in out["available"]


def test_crosscheck_formal_rule_scans_report(run_dir: Path) -> None:
    (run_dir / "scenario-report.json").write_text(json.dumps({
        "scenarios": [
            {"scenarioId": "s1", "mutationsApplied": [{"ruleId": "FR-BM-01", "action": "flip"}], "mutationsSkipped": []},
            {"scenarioId": "s2", "mutationsApplied": [], "mutationsSkipped": [{"ruleId": "FR-BM-01", "reason": "floor"}]},
        ],
    }), encoding="utf-8")
    out = crosscheck_formal_rule("20261006T120133Z-biomassa", "FR-bm-01", runs_dir=run_dir.parent)
    assert out["executedByEngine"] is True
    assert out["appliedMutations"][0]["scenarioId"] == "s1"
    assert out["skippedMutations"][0]["reason"] == "floor"


def test_crosscheck_without_report_is_explicit(run_dir: Path) -> None:
    out = crosscheck_formal_rule("20261006T120133Z-biomassa", "FR-BM-01", runs_dir=run_dir.parent)
    assert "error" in out and "scenario-report" in out["error"]
```

- [ ] **Step 2: Draai de tests, verwacht FAIL (module bestaat niet)**

Run: `cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests/test_poc_readops.py -q`
Verwacht: `ModuleNotFoundError` / collection error.

- [ ] **Step 3: Implementeer de module**

```python
# nldt/services/process_adapter/poc_readops.py
"""Read-only operaties op canonieke PoC-run-artefacten (harness-unificatie M1).

De server leest het bestandssysteem — de agent nooit direct. Alle functies
zijn puur en testbaar via de `runs_dir`-injectie; de MCP-registratie (Task 2)
roept ze met de canonieke locatie aan.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
POC_RUNS = WORKSPACE / "poc" / "runs"
POC_SCENARIO_RUNS = WORKSPACE / "poc" / "scenario-runs"


def _resolve_run_dir(runs_dir: Path | None, run_id: str) -> Path | None:
    """Zoek `<runs_dir>/<run_id>` (en scenario-runs als fallback)."""
    roots = [runs_dir] if runs_dir else [POC_RUNS, POC_SCENARIO_RUNS]
    for root in roots:
        candidate = root / run_id
        if candidate.is_dir():
            return candidate
    return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def get_provenance(run_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    work = _resolve_run_dir(runs_dir, run_id)
    if work is None:
        return {"error": f"Geen run-directory voor '{run_id}' onder poc/runs of poc/scenario-runs.", "runId": run_id}
    prov_path = work / "prov.json"
    entities: list[dict[str, Any]] = []
    if prov_path.is_file():
        prov = _read_json(prov_path)
        entities = [
            {k: e.get(k) for k in ("id", "type", "generatedBy", "sha256") if e.get(k)}
            for e in prov.get("entity", [])
            if isinstance(e, dict)
        ]
    return {"runId": run_id, "entities": entities}


def inspect_geo_layer(run_id: str, layer: str, runs_dir: Path | None = None) -> dict[str, Any]:
    work = _resolve_run_dir(runs_dir, run_id)
    if work is None:
        return {"error": f"Geen run-directory voor '{run_id}'.", "runId": run_id}
    layers_path = work / "layers.json"
    if not layers_path.is_file():
        return {"error": f"Geen layers.json in run '{run_id}'.", "runId": run_id}
    layers = _read_json(layers_path)
    if layer not in layers:
        return {"error": f"Laag '{layer}' niet in run '{run_id}'.", "available": sorted(layers), "runId": run_id}
    zones_path = work / "zones.json"
    zones_raw: Any = _read_json(zones_path) if zones_path.is_file() else []
    if isinstance(zones_raw, dict):
        zones_raw = zones_raw.get("features", [])
    matching = [
        z for z in zones_raw
        if isinstance(z, dict)
        and (z.get("zoneId") == layer or z.get("properties", {}).get("zoneId") == layer)
    ]
    return {"runId": run_id, "layer": layer, "meta": layers[layer], "zoneCount": len(matching), "zones": matching[:20]}


def crosscheck_formal_rule(scenario_run_id: str, formal_rule_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    rid = scenario_run_id.removeprefix("-worldscene")
    work = _resolve_run_dir(runs_dir, rid)
    report_path = work / "scenario-report.json" if work else None
    if report_path is None or not report_path.is_file():
        return {
            "error": f"Geen scenario-report voor '{scenario_run_id}' — gebruik het scenario-run-id en bouw eerst de world-scene.",
            "formalRuleId": formal_rule_id.upper(),
        }
    report = _read_json(report_path)
    rid_arg = formal_rule_id.upper()
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for sc in report.get("scenarios", []):
        for m in sc.get("mutationsApplied") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                applied.append({"scenarioId": sc.get("scenarioId"), "action": m.get("action"), "note": (m.get("note") or "")[:120]})
        for m in sc.get("mutationsSkipped") or []:
            if str(m.get("ruleId", "")).upper() == rid_arg:
                skipped.append({"scenarioId": sc.get("scenarioId"), "reason": (m.get("reason") or m.get("note") or "")[:120]})
    return {
        "scenarioRunId": rid,
        "formalRuleId": rid_arg,
        "executedByEngine": bool(applied),
        "appliedMutations": applied,
        "skippedMutations": skipped,
    }
```

- [ ] **Step 4: Draai de tests, verwacht PASS**

Run: `cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests/test_poc_readops.py -q`
Verwacht: `6 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Users/marc/Projecten/ldttoolbox
git add nldt/services/process_adapter/poc_readops.py nldt/tests/test_poc_readops.py
git commit -m "feat(nldt): read-only poc-run-operaties (provenance, geo-laag, formele-regel-crosscheck) als pure functies"
```

### Task 2: MCP-registratie van de read-ops (poc-server + data-server)

**Files:**
- Modify: `nldt/services/mcp_servers/poc_server.py` (voeg 2 tools toe naast de bestaande `@mcp.tool()`-functies)
- Modify: `nldt/services/mcp_servers/data_server.py` (voeg 1 tool toe)
- Test: `nldt/tests/test_poc_readops.py` (uitbreiding met registratietest)

**Interfaces:**
- Consumes: Task 1 (`get_provenance`, `inspect_geo_layer`, `crosscheck_formal_rule` met exact dezelfde namen en parameters).
- Produces: MCP-tools `get_provenance(run_id)`, `crosscheck_formal_rule(scenario_run_id, formal_rule_id)` op poc-server :8093 en `inspect_geo_layer(run_id, layer)` op data-server :8092 — Task 4/5 laden ze via de MCP-client.

- [ ] **Step 1: Schrijf de falende registratietest** (voeg toe aan `nldt/tests/test_poc_readops.py`)

```python
def test_mcp_servers_register_readops() -> None:
    from services.mcp_servers import data_server, poc_server

    assert hasattr(poc_server, "get_provenance")
    assert hasattr(poc_server, "crosscheck_formal_rule")
    assert hasattr(data_server, "inspect_geo_layer")
```

- [ ] **Step 2: Draai de test, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_poc_readops.py::test_mcp_servers_register_readops -q` → `assert hasattr(...) failed`.

- [ ] **Step 3: Registreer de tools.** In `nldt/services/mcp_servers/poc_server.py`, na de laatste bestaande `@mcp.tool()`-functie:

```python
from services.process_adapter.poc_readops import crosscheck_formal_rule as _crosscheck
from services.process_adapter.poc_readops import get_provenance as _get_provenance


@mcp.tool()
async def get_provenance(run_id: str) -> str:
    """Read-only: provenance-entiteiten (prov.json) van een canonieke PoC-run."""
    return json.dumps(_get_provenance(run_id), indent=2, default=str)


@mcp.tool()
async def crosscheck_formal_rule(scenario_run_id: str, formal_rule_id: str) -> str:
    """Read-only: is een FR-* regel daadwerkelijk door de scenario-engine uitgevoerd in deze run?"""
    return json.dumps(_crosscheck(scenario_run_id, formal_rule_id), indent=2, default=str)
```

In `nldt/services/mcp_servers/data_server.py`, na de laatste `@mcp.tool()`-functie:

```python
from services.process_adapter.poc_readops import inspect_geo_layer as _inspect_geo_layer


@mcp.tool()
async def inspect_geo_layer(run_id: str, layer: str) -> str:
    """Read-only: laag-metadata + zones van één zoneId binnen een canonieke PoC-run."""
    return json.dumps(_inspect_geo_layer(run_id, layer), indent=2, default=str)
```

Let op: `poc_server.py` importeert `json` al (bovenaan aanwezig); `data_server.py` ook.

- [ ] **Step 4: Draai alle read-op-tests, verwacht PASS** — `.venv/bin/python -m pytest tests/test_poc_readops.py -q` → `7 passed`.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/mcp_servers/poc_server.py nldt/services/mcp_servers/data_server.py nldt/tests/test_poc_readops.py
git commit -m "feat(nldt): MCP-tools get_provenance/crosscheck_formal_rule (poc) en inspect_geo_layer (data) geregistreerd"
```

### Task 3: `deep-agents/mcp_client.py` — de enige toolkanaal naar nldt

**Files:**
- Create: `deep-agents/mcp_client.py`
- Modify: `deep-agents/requirements.txt` (voeg `langchain-mcp-adapters` toe)
- Test: `deep-agents/tests/test_mcp_client.py` (nieuw; pytest draait hier met dezelfde venv: `cd deep-agents && ../nldt/.venv/bin/python -m pytest tests -q` — maak `deep-agents/tests/__init__.py` leeg aan)

**Interfaces:**
- Produces: `build_client_config(nldt_base: str | None = None) -> dict[str, dict[str, str]]` (4 entries: `nldt-catalog` :8090, `nldt-process` :8091, `nldt-data` :8092, `nldt-poc` :8093; transport `streamable_http`) en `async load_mcp_tools() -> list` — Task 4 consumeert beide.

- [ ] **Step 1: Schrijf de falende test**

```python
# deep-agents/tests/test_mcp_client.py
from mcp_client import build_client_config


def test_config_has_all_nldt_servers() -> None:
    cfg = build_client_config("http://testhost")
    assert set(cfg) == {"nldt-catalog", "nldt-process", "nldt-data", "nldt-poc"}
    assert cfg["nldt-poc"] == {"transport": "streamable_http", "url": "http://testhost:8093/mcp"}


def test_config_default_localhost_or_env(monkeypatch) -> None:
    monkeypatch.delenv("NLDT_MCP_BASE", raising=False)
    assert build_client_config()["nldt-catalog"]["url"].startswith("http://localhost:8090")
    monkeypatch.setenv("NLDT_MCP_BASE", "http://hbox")
    assert build_client_config()["nldt-data"]["url"] == "http://hbox:8092/mcp"
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd deep-agents && ../nldt/.venv/bin/python -m pytest tests/test_mcp_client.py -q` → import error.

- [ ] **Step 3: Implementeer**

```python
# deep-agents/mcp_client.py
"""MCP-client: het ENIGE kanaal van de agents naar nldt-capabiliteit (M1).

Harness-doctrine: de agent vraagt operaties aan; de harness (nldt-servers)
houdt credentials, gates en provenance. Geen stille fallback — een
onbereikbare server is een expliciete fout voor het agent-antwoord.
"""
from __future__ import annotations

import os
from typing import Any


def build_client_config(nldt_base: str | None = None) -> dict[str, dict[str, str]]:
    base = (nldt_base or os.environ.get("NLDT_MCP_BASE", "http://localhost")).rstrip("/")
    return {
        "nldt-catalog": {"transport": "streamable_http", "url": f"{base}:8090/mcp"},
        "nldt-process": {"transport": "streamable_http", "url": f"{base}:8091/mcp"},
        "nldt-data": {"transport": "streamable_http", "url": f"{base}:8092/mcp"},
        "nldt-poc": {"transport": "streamable_http", "url": f"{base}:8093/mcp"},
    }


async def load_mcp_tools() -> list:
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError as exc:  # expliciet, geen stille fallback
        raise SystemExit(
            "langchain-mcp-adapters ontbreekt — installeer met "
            "`pip install -r deep-agents/requirements.txt` (nldt-venv)."
        ) from exc
    client = MultiServerMCPClient(build_client_config())
    return await client.get_tools()
```

Voeg aan `deep-agents/requirements.txt` toe:

```
langchain-mcp-adapters
```

- [ ] **Step 4: Draai, verwacht PASS** — `../nldt/.venv/bin/python -m pytest tests/test_mcp_client.py -q` → `2 passed`.

- [ ] **Step 5: Verifieer het endpoint-pad tegen een draaiende server** (éénmalig, handmatig):

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python services/mcp_servers/poc_server.py &
sleep 2; curl -s -X POST http://localhost:8093/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' | head -c 300; kill %1
```

Als de server op een ander pad dan `/mcp` luistert (check `nldt/services/mcp_servers/http_transport.py::run_mcp_http`), pas dan de URLs in `build_client_config` aan zodat de curl-initialisatie `serverInfo` teruggeeft.

- [ ] **Step 6: Commit**

```bash
git add deep-agents/mcp_client.py deep-agents/requirements.txt deep-agents/tests/
git commit -m "feat(deep-agents): mcp_client — catalog/data/poc als streamable-http servers, expliciet geen stille fallback"
```

### Task 4: Wire deep-agents op MCP (agent.py + pocs.py + deprecation)

**Files:**
- Modify: `deep-agents/agent.py` (hele bestand, 71 regels)
- Modify: `deep-agents/pocs.py` (alleen signature `poc_subagents` + de utrecht-entry)
- Modify: `deep-agents/tools/recipes.py`, `deep-agents/tools/explain.py`, `deep-agents/tools/geo.py` (alleen module-docstring: deprecated-markering)
- Test: `deep-agents/tests/test_agent_wiring.py`

**Interfaces:**
- Consumes: Task 3 (`load_mcp_tools`), bestaande lokale gates `submit_request`, `submit_norm_cards`, `submit_formal_rule` (blijven lokaal: ze zijn deep-agents' chain-mode artefactgates mét journaling), `laya_advise_request`, `check_ollama`, `ollama_model`, `orchestrator_model_name`.
- Produces: `build_agent(tools: list)` en `async build_agent_with_mcp() -> deepagents agent` — Task 5 roept `build_agent_with_mcp` aan.

- [ ] **Step 1: Schrijf de falende wiring-test**

```python
# deep-agents/tests/test_agent_wiring.py
import agent


def test_local_tools_are_only_gates_and_laya() -> None:
    names = {getattr(t, "__name__", getattr(t, "name", "")) for t in agent.LOCAL_TOOLS}
    assert names == {"submit_request", "submit_norm_cards", "submit_formal_rule", "laya_advise_request"}


def test_recipes_no_longer_imported_in_agent() -> None:
    import inspect

    src = inspect.getsource(agent)
    assert "tools.recipes" not in src
    assert "list_recipes" not in src
```

- [ ] **Step 2: Draai, verwacht FAIL** (geen `LOCAL_TOOLS`, wel `list_recipes`).

- [ ] **Step 3: Pas `deep-agents/agent.py` aan** — vervang de imports en `build_agent`/`main`:

```python
import asyncio

from deepagents import create_deep_agent  # noqa: E402  (env must be loaded first)

from models import (  # noqa: E402
    check_ollama,
    ollama_model,
    orchestrator_model_name,
    subagent_model_name,
)
from mcp_client import load_mcp_tools  # noqa: E402
from pocs import poc_subagents  # noqa: E402
from tools.artifacts import submit_formal_rule, submit_norm_cards, submit_request  # noqa: E402
from tools.laya import laya_advise_request  # noqa: E402
from laya_router import augment_user_message, laya_enabled  # noqa: E402

SYSTEM_PROMPT = (HERE / "prompts" / "recipe_driver.md").read_text(encoding="utf-8")

# Lokaal blijven alleen de chain-mode artefactgates + laya-advies; ALLE
# nldt-capabiliteit komt uit MCP (M1).
LOCAL_TOOLS = [laya_advise_request, submit_request, submit_norm_cards, submit_formal_rule]


def build_agent(tools: list):
    return create_deep_agent(
        model=ollama_model(orchestrator_model_name()),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        subagents=poc_subagents(mcp_tools=tools),
    )


async def build_agent_with_mcp():
    mcp_tools = await load_mcp_tools()
    return build_agent(list(mcp_tools) + LOCAL_TOOLS)


def main() -> None:
    check_ollama([orchestrator_model_name(), subagent_model_name()])
    question = augment_user_message(" ".join(sys.argv[1:]) or DEFAULT_QUESTION)
    agent = asyncio.run(build_agent_with_mcp())
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": "nldt-recipes"}},
    )
    # … rest van main ongewijzigd (print + trace) …
```

Behoud de bestaande `DEFAULT_QUESTION`, `HERE`-definitie en de trace-print aan het eind van `main` exact zoals ze waren.

- [ ] **Step 4: Pas `deep-agents/pocs.py` aan** — lees eerst het hele bestand; verander alleen: (a) de signature wordt `def poc_subagents(mcp_tools: list | None = None):`, (b) de utrecht-entry krijgt de MCP-tools toegevoegd (behoud bestaande lokale tools in die entry), via deze helper bovenaan het bestand:

```python
def _mcp(mcp_tools: list | None, names: list[str]) -> list:
    by_name = {getattr(t, "name", ""): t for t in (mcp_tools or [])}
    return [by_name[n] for n in names if n in by_name]
```

en in de utrecht-subagent-dict (het element met `"name": "utrecht"`) krijgt de bestaande `"tools"`-lijst vooraan toegevoegd:

```python
tools=_mcp(mcp_tools, [
    "run_opportunity_map", "propose_scenarios", "run_scenario_sweep",
    "build_world_scene", "inspect_geo_layer", "get_provenance",
    "crosscheck_formal_rule", "search_records", "get_record",
    "describe_process", "execute_process",
]) + [/* de bestaande lokale utrecht-tools blijven hier staan */],
```

Andere subagent-entries blijven in M1 ongewijzigd (Utrecht-first; per-PoC-migratie is een latere tranche).

- [ ] **Step 5: Deprecated-markering** — voeg bovenin de docstring van `tools/recipes.py`, `tools/explain.py` en `tools/geo.py` toe:

```python
"""DEPRECATED (M1, harness-unificatie): vervangen door de nldt-MCP-tools
(catalog :8090 / data :8092 / poc :8093). Nog aanwezig als expliciete
fallback; verwijderd in de M2-cleanup zodra het MCP-pad standaard is.
… (bestaande docstring eronder) …
"""
```

- [ ] **Step 6: Draai alle deep-agents-tests, verwacht PASS** — `cd deep-agents && ../nldt/.venv/bin/python -m pytest tests -q`. Geen netwerk in tests: `test_agent_wiring` importeert `agent` (dotenv + deepagents import), geen MCP-connect.

- [ ] **Step 7: Rooktest met draaiende stack (handmatig)** — start de servers en stel een Utrecht-vraag:

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
.venv/bin/python services/mcp_servers/catalog_server.py & .venv/bin/python services/mcp_servers/data_server.py & .venv/bin/python services/mcp_servers/poc_server.py &
cd ../deep-agents && ../nldt/.venv/bin/python agent.py "Welke recepten zijn er voor Utrecht en wat kost de opportunity-map run? Geef een plan, voer nog niets uit."
kill %1 %2 %3
```

Verwacht: het antwoord noemt `utrecht-opportunity-map` via `search_records`; de run-trace toont MCP-toolnamen (geen `list_recipes`). Bij onbereikbare server: expliciete foutmelding, geen stille wrapper-terugval.

- [ ] **Step 8: Commit**

```bash
git add deep-agents/agent.py deep-agents/pocs.py deep-agents/tools/recipes.py deep-agents/tools/explain.py deep-agents/tools/geo.py deep-agents/tests/test_agent_wiring.py
git commit -m "feat(deep-agents): agent wired op nldt-MCP — lokale tools alleen artefactgates+laya, wrappers gemarkeerd deprecated"
```

### Task 5: M1-acceptatie — contracttest

**Files:**
- Test: `nldt/tests/test_harness_contract.py`

**Interfaces:**
- Consumes: Task 3 (`build_client_config`), Task 2 (geregistreerde MCP-tools).

- [ ] **Step 1: Contracttest** (nldt-side, importeert deep-agents-config via pad-injectie):

```python
# nldt/tests/test_harness_contract.py
from __future__ import annotations

import importlib.util
from pathlib import Path

from services.mcp_servers import data_server, poc_server

DEEP_AGENTS = Path(__file__).resolve().parents[2] / "deep-agents"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, DEEP_AGENTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_deep_agents_targets_only_nldt_mcp_servers() -> None:
    cfg = _load("mcp_client").build_client_config("http://x")
    assert set(cfg) == {"nldt-catalog", "nldt-process", "nldt-data", "nldt-poc"}


def test_state_changing_poc_operations_exist_on_poc_server() -> None:
    for fn in ("run_opportunity_map", "propose_scenarios", "run_scenario_sweep", "build_world_scene"):
        assert hasattr(poc_server, fn), fn


def test_read_only_operations_registered() -> None:
    assert hasattr(poc_server, "get_provenance")
    assert hasattr(poc_server, "crosscheck_formal_rule")
    assert hasattr(data_server, "inspect_geo_layer")
```

- [ ] **Step 2: Draai de hele nldt-suite** — `cd nldt && .venv/bin/python -m pytest tests -q` → alles groen inclusief de nieuwe contracttests.

- [ ] **Step 3: Commit**

```bash
git add nldt/tests/test_harness_contract.py
git commit -m "test(nldt): harness-contract — deep-agents kent alleen de drie nldt-MCP-servers"
```

---

## M2 — llm_hook live (S1/S2)

### Task 6: Gedeelde modelconfig (`nldt/services/common/model_config.py`)

**Files:**
- Create: `nldt/services/common/model_config.py`
- Modify: `deep-agents/models.py` (delegeert; `check_ollama` blijft lokaal)
- Test: `nldt/tests/test_model_config.py`

**Interfaces:**
- Produces: `orchestrator_model_name() -> str` (default `gemma4:31b-mlx`), `subagent_model_name() -> str` (default `gemma4:12b-mlx`), `is_zai(model: str) -> bool`, `build_chat_model(spec: str | None = None, **overrides)` (lazy import; `zai:` → ChatAnthropic, anders ChatOllama) — Task 7 en `deep-agents/models.py` consumeren dit.

- [ ] **Step 1: Falende test**

```python
# nldt/tests/test_model_config.py
import pytest

from services.common import model_config


def test_defaults_are_local_gemma() -> None:
    monkey = pytest.MonkeyPatch()
    monkey.delenv("DEEP_AGENT_MODEL", raising=False)
    monkey.delenv("DEEP_AGENT_SUBMODEL", raising=False)
    assert model_config.orchestrator_model_name() == "gemma4:31b-mlx"
    assert model_config.subagent_model_name() == "gemma4:12b-mlx"


def test_is_zai() -> None:
    assert model_config.is_zai("zai:glm-5.3-flash")
    assert not model_config.is_zai("gemma4:31b-mlx")


def test_cloud_names_refused() -> None:
    with pytest.raises(SystemExit):
        model_config.build_chat_model("gemma4:cloud")


def test_build_chat_model_local_uses_chatollama(monkeypatch) -> None:
    calls = {}

    class FakeOllama:  # dubbele klasse voor de import-shim (geen netwerk)
        def __init__(self, **kwargs):
            calls.update(kwargs)

    import sys, types
    fake = types.ModuleType("langchain_ollama")
    fake.ChatOllama = FakeOllama
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake)
    model_config.build_chat_model("gemma4:31b-mlx", temperature=0)
    assert calls["model"] == "gemma4:31b-mlx"
    assert calls["temperature"] == 0
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_model_config.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer** `nldt/services/common/model_config.py`:

```python
"""Gedeelde modelconfig voor nldt + deep-agents (harness-unificatie M2).

Één plek voor modelnamen en -bouw; alleen lokale Ollama of expliciete
`zai:`-prefix (Z.ai GLM via het Anthropic-compatibele endpoint). Ollama's
betaalde cloud-tier wordt geweigerd.
"""
from __future__ import annotations

import os
from typing import Any

ZAI_ANTHROPIC_URL = "https://api.z.ai/api/anthropic"


def orchestrator_model_name() -> str:
    return os.environ.get("DEEP_AGENT_MODEL", "gemma4:31b-mlx")


def subagent_model_name() -> str:
    return os.environ.get("DEEP_AGENT_SUBMODEL", "gemma4:12b-mlx")


def is_zai(model: str) -> bool:
    return model.startswith("zai:")


def build_chat_model(spec: str | None = None, **overrides: Any):
    name = spec or orchestrator_model_name()
    if "cloud" in name and not is_zai(name):
        raise SystemExit(
            f"Model '{name}' routeert naar Ollama's betaalde cloud — alleen lokale "
            "modellen. Gebruik `zai:glm-...` of een lokaal model uit `ollama list`."
        )
    if is_zai(name):
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise SystemExit("langchain-anthropic ontbreekt in deze omgeving.") from exc
        key = os.environ.get("ZAI_API_KEY")
        if not key:
            raise SystemExit(f"Model '{name}' vereist ZAI_API_KEY.")
        kwargs: dict[str, Any] = dict(
            model=name.removeprefix("zai:"), base_url=ZAI_ANTHROPIC_URL,
            api_key=key, max_retries=2, timeout=300,
        )
        kwargs.update(overrides)
        return ChatAnthropic(**kwargs)
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise SystemExit("langchain-ollama ontbreekt in deze omgeving.") from exc
    kwargs = dict(
        model=name,
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "16384")),
        request_timeout=int(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "600")),
    )
    kwargs.update(overrides)
    return ChatOllama(**kwargs)
```

- [ ] **Step 4: Delegeer in `deep-agents/models.py`** — vervang de body van `orchestrator_model_name`, `subagent_model_name`, `is_zai`, `ollama_model` door delegatie (behoud `check_ollama` en de `.env`-loading in `agent.py` ongewijzigd):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nldt"))
from services.common.model_config import (  # noqa: E402,F401
    build_chat_model as _build,
    is_zai,
    orchestrator_model_name,
    subagent_model_name,
)


def ollama_model(model: str | None = None, **overrides):
    return _build(model or orchestrator_model_name(), **overrides)
```

- [ ] **Step 5: Draai beide suites** — `nldt`: `.venv/bin/python -m pytest tests/test_model_config.py -q` → 4 passed; `deep-agents`: `cd ../deep-agents && ../nldt/.venv/bin/python -m pytest tests -q` → groen (bestaande agent-tests draaien nog steeds via `ollama_model`).

- [ ] **Step 6: Commit**

```bash
git add nldt/services/common/model_config.py nldt/tests/test_model_config.py deep-agents/models.py
git commit -m "feat(nldt): gedeelde modelconfig (model_config.py) — deep-agents/models.py delegeert, cloud-tier geweigerd"
```

### Task 7: `OllamaLLMHook` + `hook_from_env()`

**Files:**
- Modify: `nldt/agents/orchestrator/llm_hook.py` (klasse + factory toevoegen; `rank_recipes`/`nl_to_plan_proposal` ongewijzigd)
- Test: `nldt/tests/test_llm_hook.py`

**Interfaces:**
- Consumes: Task 6 (`model_config.build_chat_model`, `orchestrator_model_name`).
- Produces: `class OllamaLLMHook: propose(prompt: str, schema_hint: str | None = None) -> dict | None` en `hook_from_env() -> OllamaLLMHook | None` (alleen een hook als `NLDT_LLM_HOOK=1`) — Task 8 consumeert `hook_from_env`.

- [ ] **Step 1: Falende test**

```python
# nldt/tests/test_llm_hook.py
from __future__ import annotations

import json

import pytest

from agents.orchestrator import llm_hook
from agents.orchestrator.llm_hook import OllamaLLMHook, hook_from_env


class FakeModel:
    def __init__(self, text: str, fail: bool = False):
        self.text = text
        self.fail = fail
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        if self.fail:
            raise ConnectionError("ollama down")
        return type("Msg", (), {"content": self.text})()


def _hook_with(monkeypatch, model: FakeModel) -> OllamaLLMHook:
    monkeypatch.setattr(llm_hook.model_config, "build_chat_model", lambda **kw: model)
    return OllamaLLMHook()


def test_propose_parses_plain_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel(json.dumps({"order": ["b", "a"]})))
    assert hook.propose("rank", "ids") == {"order": ["b", "a"]}


def test_propose_parses_fenced_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("```json\n{\"order\": [\"x\"]}\n```"))
    assert hook.propose("rank") == {"order": ["x"]}


def test_propose_returns_none_on_model_failure(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("x", fail=True))
    assert hook.propose("rank") is None


def test_propose_returns_none_on_non_json(monkeypatch) -> None:
    hook = _hook_with(monkeypatch, FakeModel("geen json hier"))
    assert hook.propose("rank") is None


def test_hook_from_env_default_off(monkeypatch) -> None:
    monkeypatch.delenv("NLDT_LLM_HOOK", raising=False)
    assert hook_from_env() is None


def test_hook_from_env_on(monkeypatch) -> None:
    monkeypatch.setenv("NLDT_LLM_HOOK", "1")
    monkeypatch.setattr(llm_hook.model_config, "build_chat_model", lambda **kw: FakeModel("{}"))
    assert isinstance(hook_from_env(), OllamaLLMHook)
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_llm_hook.py -q` → ImportError (`OllamaLLMHook` bestaat niet).

- [ ] **Step 3: Implementeer** — voeg bovenin `llm_hook.py` toe (bestaande code ongewijzigd):

```python
import json
import os
import sys

from services.common import model_config

_JSON_FENCE_STARTS = ("```json", "```")


class OllamaLLMHook:
    """Live S1/S2-seam: temperatuur 0, JSON-gedwongen; faalt ALTIJD naar None
    zodat de deterministic paden (tag-overlap-rank, receptverplicht plan)
    de harness blijven dragen. Offline-gate per aanroep."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = model_config.build_chat_model(temperature=0)
        return self._model

    def propose(self, prompt: str, schema_hint: str | None = None) -> dict[str, Any] | None:
        try:
            text = self._get_model().invoke(prompt).content
        except Exception as exc:  # onbereikbare Ollama e.d. — explicit gelogd, geen raise
            print(f"[llm_hook] model onbereikbaar → deterministic fallback ({exc})", file=sys.stderr)
            return None
        text = str(text).strip()
        for fence in _JSON_FENCE_STARTS:
            if text.startswith(fence):
                text = text.strip("`").removeprefix("json").strip()
                break
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            print("[llm_hook] geen JSON in antwoord → deterministic fallback", file=sys.stderr)
            return None
        return parsed if isinstance(parsed, dict) else None


def hook_from_env() -> OllamaLLMHook | None:
    if os.environ.get("NLDT_LLM_HOOK") == "1":
        return OllamaLLMHook()
    return None
```

Let op: `Any` is in het bestand al geïmporteerd (`from typing import Any, Callable, Optional`).

- [ ] **Step 4: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_llm_hook.py -q` → `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add nldt/agents/orchestrator/llm_hook.py nldt/tests/test_llm_hook.py
git commit -m "feat(nldt): OllamaLLMHook — live S1/S2-seam met JSON-gate en altijddeterministische fallback (NLDT_LLM_HOOK=1)"
```

### Task 8: Wire de hook in de catalog-node (S1)

**Files:**
- Modify: `nldt/agents/orchestrator/nodes/catalog.py:35` (alleen de `rank_recipes`-aanroep)
- Test: `nldt/tests/test_llm_hook.py` (uitbreiding)

**Interfaces:**
- Consumes: Task 7 (`hook_from_env`).

- [ ] **Step 1: Falende test** (voeg toe aan `nldt/tests/test_llm_hook.py`):

```python
def test_catalog_node_uses_hook_when_enabled(monkeypatch) -> None:
    from agents.orchestrator.nodes import catalog

    hits = [{"id": "a", "title": "opportunity-map utrecht"}, {"id": "b", "title": "peil-conflict rijnland"}]
    monkeypatch.setattr(catalog, "hook_from_env", lambda: None)
    default_order = [h["id"] for h in catalog.rank_recipes("utrecht", hits)]
    monkeypatch.setattr(
        catalog, "rank_recipes",
        lambda q, hs, hook=None: hs[::-1] if hook is not None else hs,
    )
    monkeypatch.setattr(catalog, "hook_from_env", lambda: object())  # fake live hook
    assert catalog.rank_recipes("utrecht", hits, catalog.hook_from_env()) == hits[::-1]
    assert default_order == ["a", "b"]  # deterministic baseline onveranderd
```

- [ ] **Step 2: Draai, verwacht FAIL** — `catalog` heeft nog geen `hook_from_env`-attribuut.

- [ ] **Step 3: Pas `nodes/catalog.py` aan** — import bovenaan toevoegen en regel 35 vervangen:

```python
from agents.orchestrator.llm_hook import hook_from_env, rank_recipes
```

```python
    hits = rank_recipes(q, hits, hook_from_env())
```

- [ ] **Step 4: Draai de orchestrator-tests** — `.venv/bin/python -m pytest tests/test_llm_hook.py tests/test_orchestrator.py -q` → groen.

- [ ] **Step 5: Commit**

```bash
git add nldt/agents/orchestrator/nodes/catalog.py nldt/tests/test_llm_hook.py
git commit -m "feat(nldt): S1 live — catalog-node rankt recepten via hook_from_env (default uit → deterministic)"
```

Notitie S2: `nl_to_plan_proposal(request, recipe_id, resolved_inputs, llm_hook=…)` is met Task 7 seam-ready maar heeft nog geen call-site in de graph (de planner-node bestaat nog niet); koppeling daarvan hoort bij een toekomstige plan-proposal-node, niet bij dit plan.

### Task 9: M2-smoke-regressie (handmatige verificatie)

- [ ] **Step 1: Offline baseline** — zonder Ollama-wijziging (NLDT_LLM_HOOK uit):
  `cd nldt && .venv/bin/python -m pytest tests -q` → groen.
  `cd ../poc && ../nldt/.venv/bin/python run.py --use-case water` (cache-first) → vergelijk `poc/runs/<nieuw-id>/run_summary.json` met de canonieke `poc/runs/20261004T185116Z-water/run_summary.json`: verdict `pass`, zelfde finale km² (1554.906) en IoU (0.999996) — drift = 0.

- [ ] **Step 2: Live hook smoke** (alleen als Ollama draait): `NLDT_LLM_HOOK=1 .venv/bin/python -c "from agents.orchestrator.llm_hook import hook_from_env, rank_recipes; from services.catalog_adapter.seed import find_records; print([h['id'] for h in rank_recipes('utrecht opportunity map', find_records(q='utrecht'), hook_from_env())])"` → geeft een id-volgorde (deterministisch als Ollama onbereikbaar: stderr-note + tag-overlap-volgorde).

- [ ] **Step 3: Geen commit** (verificatie-stap; run-artefacten zijn cache-gedrag, niet nieuwe outputs — een nieuwe run-directory onder `poc/runs/` wordt alleen gecommit als de repo-conventie dat voorschrijft: check `git status` en volg het bestaande patroon van eerdere smoke-runs).

---

## M3 — Eén journal

### Task 10: Journal-writer in de process-adapter

**Files:**
- Create: `nldt/services/process_adapter/journal.py`
- Test: `nldt/tests/test_process_journal.py`

**Interfaces:**
- Consumes: deep-agents journal-format (`deep-agents/journal.py`): JSON-regel `{ts, kind, agent, summary, ...extra}` met `ts` als `HH:MM:SS` UTC.
- Produces: `journal_process_event(process_id: str, status: str, summary: str, **extra: Any) -> None`, `journal_path() -> Path` (env `NLDT_JOURNAL_PATH`, default `<repo>/deep-agents/runs/live/steps.jsonl`) — Task 11 consumeert.

- [ ] **Step 1: Falende test**

```python
# nldt/tests/test_process_journal.py
from __future__ import annotations

import json

from services.process_adapter import journal as pj


def test_append_writes_deep_agents_format(tmp_path, monkeypatch) -> None:
    path = tmp_path / "steps.jsonl"
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(path))
    pj.journal_process_event("opportunity-map-run", "ok", "verdict pass", durationMs=1234)
    entry = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["kind"] == "process_result"
    assert entry["agent"] == "opportunity-map-run"
    assert entry["summary"] == "verdict pass"
    assert entry["status"] == "ok"
    assert entry["durationMs"] == 1234
    assert len(entry["ts"].split(":")) == 3  # HH:MM:SS


def test_default_path_points_at_deep_agents_live(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("NLDT_JOURNAL_PATH", raising=False)
    assert pj.journal_path().name == "steps.jsonl"
    assert "deep-agents" in str(pj.journal_path())
```

- [ ] **Step 2: Draai, verwacht FAIL** — `cd nldt && .venv/bin/python -m pytest tests/test_process_journal.py -q` → ModuleNotFoundError.

- [ ] **Step 3: Implementeer**

```python
# nldt/services/process_adapter/journal.py
"""Process-trajectories in het deep-agents journal-format (harness-unificatie M3).

Eén trajectory-format voor beide breinen: deep-agents schrijft zijn steps hier
al (`deep-agents/journal.py`); de process-adapter voegt elke process-executie
als `process_result` toe zodat het dashboard de hele keten toont.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_PATH = WORKSPACE / "deep-agents" / "runs" / "live" / "steps.jsonl"


def journal_path() -> Path:
    return Path(os.environ.get("NLDT_JOURNAL_PATH", str(DEFAULT_PATH)))


def journal_process_event(process_id: str, status: str, summary: str, **extra: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "kind": "process_result",
        "agent": process_id,
        "status": status,
        "summary": summary,
    }
    entry.update(extra)
    path = journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
```

- [ ] **Step 4: Draai, verwacht PASS** — `.venv/bin/python -m pytest tests/test_process_journal.py -q` → `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/journal.py nldt/tests/test_process_journal.py
git commit -m "feat(nldt): process-journal — trajectories in deep-agents steps.jsonl-format (NLDT_JOURNAL_PATH override)"
```

### Task 11: Instrument `execute_local` in de process-adapter

**Files:**
- Modify: `nldt/services/process_adapter/handlers.py` (`execute_local`, regel ~394)
- Test: `nldt/tests/test_process_journal.py` (uitbreiding)

**Interfaces:**
- Consumes: Task 10 (`journal_process_event`).

- [ ] **Step 1: Falende test** (voeg toe aan `nldt/tests/test_process_journal.py`):

```python
def test_execute_local_journals_success_and_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    from services.process_adapter.handlers import execute_local

    out = execute_local("compute-area-statistics", {
        "features": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]}},
        ]},
    })
    assert "statistics" in out
    lines = (tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    ok_entry = json.loads(lines[-1])
    assert ok_entry["kind"] == "process_result" and ok_entry["status"] == "ok"

    with __import__("pytest").raises(Exception):
        execute_local("bestaat-niet", {})
    error_entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert error_entry["status"] == "error"


def test_journal_schema_matches_deep_agents_writer(tmp_path, monkeypatch) -> None:
    """Eén format: onze writer gebruikt dezelfde verplichte velden als de
    deep-agents-journal-writer (`deep-agents/journal.py::append`)."""
    monkeypatch.setenv("NLDT_JOURNAL_PATH", str(tmp_path / "steps.jsonl"))
    pj.journal_process_event("x", "ok", "hello")
    from pathlib import Path as _P

    da_journal_src = (_P(__file__).parents[2] / "deep-agents" / "journal.py").read_text(encoding="utf-8")
    assert "def append(" in da_journal_src and '"ts"' in da_journal_src and '"kind"' in da_journal_src
    required = {"ts", "kind", "agent", "summary"}
    entry = json.loads((tmp_path / "steps.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert required <= set(entry)
```

- [ ] **Step 2: Draai, verwacht FAIL** — `execute_local` schrijft nog geen journal.

- [ ] **Step 3: Implementeer** — in `handlers.py` de bestaande `execute_local` (regel 394) vervangen door een instrumenteerde variant; verplaats de bestaande body naar `_execute_local_inner`:

```python
from services.process_adapter.journal import journal_process_event


def execute_local(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    import time

    start = time.monotonic()
    try:
        result = _execute_local_inner(process_id, inputs)
    except Exception as exc:
        journal_process_event(process_id, "error", f"{type(exc).__name__}: {exc}")
        raise
    journal_process_event(
        process_id, "ok", f"process '{process_id}' executed",
        durationMs=int((time.monotonic() - start) * 1000),
    )
    return result


def _execute_local_inner(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if process_id in POC_PROCESS_DEFINITIONS:
        return execute_poc_process(process_id, inputs)
    # … de bestaande dispatch-body ongewijzigd …
```

- [ ] **Step 4: Draai de hele nldt-suite** — `.venv/bin/python -m pytest tests -q` → groen (ook `test_h3_processes`, `test_poc_processes` die `execute_local` aanroepen; het journal schrijft naar de default-locatie — acceptabel, is het live-dashboard-bestand).

- [ ] **Step 5: Commit**

```bash
git add nldt/services/process_adapter/handlers.py nldt/tests/test_process_journal.py
git commit -m "feat(nldt): execute_local geinstrumenteerd — elke process-executie als journal-event (ok/error + duur)"
```

### Task 12: M3-acceptatie + eindverificatie (handmatig)

- [ ] **Step 1: Live keten** — start servers + agent (Task 4 Step 7-commando's), stel de Utrecht-vraag, draai één `run_opportunity_map`, en verifieer dat `deep-agents/runs/live/steps.jsonl` nu zowel agent-steps (`tool_call`, `tool_result`) als `process_result`-regels toont: `tail -5 deep-agents/runs/live/steps.jsonl`.

- [ ] **Step 2: Dashboard** — open `deep-agents/dashboard.html` (of `live.py`): beide soorten regels worden gerenderd; zoniet, pas het dashboard-filter toe op `kind` (klein wijzigingsblok in `live.py`/`dashboard.html` — vermelden in de commit).

- [ ] **Step 3: Eindverificatie beide suites**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt && .venv/bin/python -m pytest tests -q
cd ../poc && ../nldt/.venv/bin/python -m pytest tests -q
```

Verwacht: nldt-suite groen; poc-suite `295 passed, 1 skipped` (ongewijzigd).

- [ ] **Step 4: M2-cleanup (optioneel, aparte commit)** — verwijder de deprecated wrappers `deep-agents/tools/recipes.py`, `tools/explain.py`, `tools/geo.py` én hun imports in `pocs.py`, plus de fallback-vermeldingen; run beide deep-agents-testen opnieuw. Alleen uitvoeren als de rooktest (Step 1) het MCP-pad als standaard heeft bevestigd.

```bash
git add -A deep-agents/
git commit -m "refactor(deep-agents): M2-cleanup — filesystem-wrappers voor nldt-capabiliteit verwijderd"
```

- [ ] **Step 5: Push** — `git push origin main` (of per task-push volgens voorkeur).
