# A2A-simulation — implementatie van het architectuurdocument

Canonical design: **[`architectuur-llm-gedreven-deepagents-met-deterministische-rekentools.md`](architectuur-llm-gedreven-deepagents-met-deterministische-rekentools.md)**  
(A2A [1.0](https://a2a-protocol.org/latest/specification/) + LangChain Deep Agents + nLDT PoC’s + EU LDT Toolbox IM)

## Ontwerp in één zin

> **LLM specificeert → deterministisch rekenblok rekent (A2A of MCP) → LLM interpreteert.**  
> Getallen in rapportages komen nooit uit de LLM-laag.

## Twee lagen in deze map

| Laag | Waar | Transport |
|------|------|-----------|
| **Deepagents (LLM)** | [`orchestrator/`](orchestrator/) — orchestrator + subagents `scenario_analist`, `interpretatie` | in-process `task` |
| **Deterministisch** | PoC-mesh [`agents/`](agents/) `:9181–9186` | **A2A** JSON-RPC |
| **Deterministisch (eigen stack)** | nLDT MCP / process adapter | **MCP** (buiten deze map; zie `nldt/simulation`) |

PoC-A2A-servers zijn **geen** LLM-endpoints. Modus `A2A_SIM_MODE=deep` op de mesh is bewust geblokkeerd; LLM draait in `orchestrator/agent.py`.

## Diagram (repo)

Zie §10.2 in het architectuurdoc (sequence orchestrator → A2A rekenblok → interpretatie).

## Snel starten

```bash
cd a2a-simulation
pip install -r requirements.txt
export PYTHONPATH="${PWD}:${PWD}/../deep-agents:${PWD}/../nldt"

# 1) Deterministische PoC-mesh
./scripts/run_mesh.sh

# 2) Alleen rekenblok (geen LLM)
export A2A_SIM_AUTH=static NLDT_STATIC_TOKENS=sim-toolbox-token
python -m federator.client send rijnland "Run rijnland-peil-conflict demo"

# 3) Volledige architectuur-run (LLM → A2A → LLM)
../deep-agents/.venv/bin/python -m orchestrator.agent \
  "Peilconflict voor Rijnland: plan, A2A-run, interpretatie"

# 4) Demo: meerdere scenario's (start mesh + trace)
../deep-agents/.venv/bin/python -m orchestrator.demo_scenarios --start-mesh
```

**Kan de LLM nu scenario's doorrekenen met deterministische tools?** Ja — mits:
- Ollama draait (`DEEP_AGENT_MODEL` / `DEEP_AGENT_SUBMODEL` geïnstalleerd);
- PoC-mesh bereikbaar (`./scripts/run_mesh.sh` of `--start-mesh`);
- `a2a-sdk` in de **deep-agents** venv: `pip install 'a2a-sdk[http-server]'`;
- zelfde auth-env voor orchestrator en mesh.

Deterministisch = `list_recipes` / `get_recipe` (schema's) + `delegate_to_poc_agent` (A2A artifacts met provenance). Geen getallen uit pure LLM-redenering.

## PoC-mesh (deterministisch)

| Agent | Poort | Default recipe |
|-------|-------|----------------|
| breda | 9181 | `breda-five-value-scan` |
| utrecht | 9182 | `utrecht-opportunity-map` |
| rijnland | 9183 | `rijnland-peil-conflict` |
| eindhoven | 9184 | `eindhoven-bp2op` |
| crosstrack | 9185 | `multi-track-crosstrack` |
| minigim | 9186 | `minigim-gebiedscheck` |

Endpoints: `/.well-known/agent-card.json`, `/a2a/jsonrpc`, `/a2a/rest`.  
Catalogus: [`catalog/poc-agents.json`](catalog/poc-agents.json).

## Modi rekenblok

| `A2A_SIM_MODE` | Gedrag |
|----------------|--------|
| `simulate` (mesh default) | Fixtures + **provenance** in JSON-artifact |
| `nldt` | Proxy naar nLDT orchestrator `:8085` (LangGraph + process adapter) |

### nldt-modus

```bash
# Terminal 1 — stack (PYTHONPATH alleen nldt/)
./scripts/start_nldt_stack.sh

# Terminal 2 — PoC A2A-proxy
./scripts/run_mesh_nldt.sh

# Smoke (terminal 2 of 3)
export A2A_SIM_AUTH=static NLDT_STATIC_TOKENS=sim-toolbox-token
python -m federator.client send rijnland "recipe rijnland-peil-conflict"

# LLM + echte runs
../deep-agents/.venv/bin/python -m orchestrator.demo_scenarios --start-mesh --mode nldt
```

Belangrijk: **`start_nldt_stack.sh` gebruikt `PYTHONPATH=.` in `nldt/`** — zet `a2a-simulation` niet vóór `nldt` bij het starten van `:8085`, anders faalt `agents.orchestrator`.

| Env | Default |
|-----|---------|
| `NLDT_OFFLINE` | `1` |
| `NLDT_A2A_AUTO_HITL` | `1` |
| `NLDT_A2A_URL` | `http://127.0.0.1:8085` |

## Auth (Toolbox IM)

- Agent Card: `securitySchemes.euLdtToolboxBearer`
- Mesh: `A2A_SIM_AUTH=static`, token `NLDT_STATIC_TOKENS` (default `sim-toolbox-token`)
- Federator-cli: **zelfde env** meegeven

## UI — live A2A-demo

```bash
./scripts/run_a2a_demo.sh
# → http://127.0.0.1:9190  (mesh-topologie, A2A-trace, artifact-metrics)
```

Presets: volledige LLM→A2A→LLM-run (Rijnland+Utrecht) of **alleen A2A** (geen Ollama). Optioneel `A2A_DEMO_PORT=9190`.

Static architectuurtekst: [`simulation/index.html`](simulation/index.html) via `/info.html` op de demo-server.

## Tests

```bash
pytest tests/test_mesh.py
```

## Gerelateerd

- [`deep-agents/`](../deep-agents/) — in-process PoC-specialists + recipe tools (MCP-adjacent)
- [`nldt/services/a2a`](../nldt/services/a2a/) — legacy nLDT stub (niet A2A 1.x canonical)
- Architectuur §6: **MCP binnen domein, A2A over grenzen** — PoC-mesh simuleert externe/organisatie-rekenblokken
