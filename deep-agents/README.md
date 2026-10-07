# Deep Agents — recipe drivers for the nLDT POCs

LangChain [Deep Agents](https://docs.langchain.com/oss/python/deepagents/quickstart)
hosted here drive the nLDT **recipes** for the POCs, fully on **local Ollama
models** — no cloud provider keys. Recipes are the declarative playbooks in
[`../nldt/recipes/`](../nldt/recipes) (`rijnland-peil-conflict`,
`utrecht-world-scene`, `eindhoven-bp2op`, `minigim-gebiedscheck`, …), each
with steps, inputs/outputs and `requiredProcesses` backed by the POC
workspaces (`../poc`, `../poc-breda`, `../poc-rijnland`, `../poc-minigim`,
`../poc-bp2op`).

## Orchestration

An orchestrator agent routes requests to per-POC specialist subagents and
functional specialists from the multi-agent plan ([MULTI_AGENT_PLAN.md](../MULTI_AGENT_PLAN.md))
via the `task` tool (SubAgentMiddleware — todo planning is included automatically):

```
orchestrator (gemma4:31b-mlx)
  ├─ breda         five-value scan, scan QA (seam S4)                    ┐
  ├─ rijnland      peil conflict, what-if, live                          │ POC specialists
  ├─ utrecht       opportunity map, world-scene, scenario author/sweep   │ (prompts/poc/)
  ├─ crosstrack    Plane C wind × solar × forest overlay                 │
  ├─ minigim       gebiedscheck (74-item Lijst-v0.91)                    │
  ├─ eindhoven     bp2op conversion (V4 HITL always pending)             ┘
  ├─ geospecialist layer areas (km²), bboxes, control-vs-scenario deltas ┐
  ├─ normspecialist norm-card corpus search (NC-*, source article)       │
  ├─ critic        deterministic validation gate after every build       │ functional specialists
  ├─ explainer     provenance: spec → scenario → norm card → article     │ (prompts/roles/)
  ├─ intake        vague brief → schema-valid OpportunityMapRequest      │
  └─ formalizer    NormCard (NC-*) → executable FormalRule (FR-*)        ┘
      specialists: gemma4:12b-mlx
```

Build ordering matters: utrecht builds first, then geospecialist + critic fan
out in parallel over the fresh artifacts.

## Layout

```
deep-agents/
  agent.py               # orchestrator entry point (build + run)
  live.py                # streaming runner → runs/live/steps.jsonl
  graph_trace.py         # LangGraph stream (updates+messages, subgraphs) → journal
  live_server.py         # simulation dashboard server (http://127.0.0.1:8765)
  dashboard.html         # the dashboard: dropdowns + live steps + map
  journal.py             # run journal (steps.jsonl) shared by runner + tools
  models.py              # Ollama model factory (base_url, num_ctx, fail-fast check)
  pocs.py                # per-POC subagent registry
  vizassets.py           # local Leaflet copies (no CDN/API key needed)
  tools/recipes.py       # list_recipes / get_recipe tools
  tools/utrecht.py       # world-scene execution + demo render (Utrecht Plane B)
  tools/geo.py           # geospecialist: layer inspection + comparison (km², deltas)
  tools/norms.py         # normspecialist: norm-card corpus search
  tools/validate.py      # critic: schema + sanity gate over built bundles
  tools/explain.py       # explainer: provenance lookup
  tools/intake.py        # intake: request template + OpportunityMapRequest schema gate
  tools/formalize.py     # formalizer: formal-rule corpus + FormalRule schema gate
  prompts/               # recipe_driver.md (orchestrator) + poc/*.md (specialists)
  runs/                  # agent-written artifacts per session (gitignored)
```

## Setup

```bash
cd deep-agents
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # optional: override models / Ollama URL / num_ctx
ollama serve              # if not already running
ollama pull gemma4:31b-mlx && ollama pull gemma4:12b-mlx
```

Models are env-driven and match `ollama list`: `DEEP_AGENT_MODEL`
(orchestrator, default `gemma4:31b-mlx`) and `DEEP_AGENT_SUBMODEL`
(specialists, default `gemma4:12b-mlx`). Any local tool-calling model works —
e.g. `qwen3.6:27b-mlx` as a heavier orchestrator or `gemma4:12b` (non-MLX).

### Tests

```bash
cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q
```

De suite draait met de nldt-interpreter en de deep-agents-site-packages op
`PYTHONPATH`. `langgraph-checkpoint-sqlite` (SqliteSaver voor de
HITL-checkpointer) staat in `deep-agents/.venv` en niet in de
requirements-bestanden.

## Run

One-shot from the CLI:

```bash
python agent.py "Welk recipe hoort bij de Rijnland peil conflict POC en welke inputs nodig?"
python live.py "Bouw de world scene voor scenario run 20260831T074521Z-wind-scen"   # streamed to the journal
```

Or the **simulation dashboard** (dropdown **POC** for all six toolbox POCs,
scenario run where needed, prompting mode per POC, Ollama models; live step
timeline; Utrecht world-scene map when agents build; other POCs show reference
demos from `nldt/simulation/` — fully local):

```bash
.venv/bin/python live_server.py     # → http://127.0.0.1:8765/
```

Modes: *Uitvoeren + visual demo*, *Alleen run plan*, *Kritische toets,
daarna uitvoeren*, *Control vs scenario vergelijking*, *Geo-analyse +
critic-validatie*, *Normketen* (intake → normspecialist → formalizer), and
*Volledige keten* — the whole planning plane in order: intake → norm cards →
formal rule → world-scene build → geo + critic → explainer crosscheck.

**Artifact gates (volledige keten):** intake, normspecialist and formalizer
must SUBMIT their artifacts (`submit_request`, `submit_norm_cards`,
`submit_formal_rule`) — validated, persisted to `runs/live/artifacts/` and
journaled with PASS/FAIL. In keten mode the world-scene build HARD-REFUSES
(`NLDT_REQUIRE_INTAKE=1`) without a submitted, schema-valid request, and the
explainer's `crosscheck_formal_rule` reports whether the engine actually
executed the submitted rule. One simulation at a time; each run journals
every step to `runs/live/steps.jsonl`.

### LangGraph-zichtbaarheid tijdens een run

`live.py` streamt via `graph_trace.run_streamed` met `stream_mode=["updates",
"messages"]` en `subgraphs=True`. In het dashboard en in de terminal zie je:

| `kind` | Betekenis |
|--------|-----------|
| `graph_node` | LangGraph-node (`model`, `tools`, …) per orchestrator of subagent-subgraph |
| `delegate` | Orchestrator delegeert naar een specialist (`task`) |
| `tool_call` / `tool_result` | Van de tools zelf (`tools/*.py` → `journal.append`) |
| `assistant` | Modelantwoord zonder tool calls |
| `done` | Eindantwoord orchestrator |

De balk **LangGraph:** onder de agent-chips toont de laatste actieve node, stap
nummer en subgraph-pad. Agent-chips krijgen een gele rand als die agent net
actief was.

### Begrijpelijke scenario’s (Utrecht / Crosstrack)

De dashboard-dropdown **Scenario** toont geen ruwe run-ids meer als primaire tekst:
`scenario_catalog.py` leest `scenario-report.json` en levert labels (Wind/Zon/Bos,
aantal varianten). Sterretje (★) = aanbevolen demo-runs; onder de dropdown staat een
korte toelichting (vraagtype + voorbeeldvarianten).

### Laya (Apple Silicon MLX)

[Laya](https://www.orcarouter.ai/blog/laya-on-apple-silicon-mlx) is een **typed
decision model** (geen LLM): één MLX-forward pass, milliseconden, ~&lt;1 GiB peak.
Het geeft **routing-advies** (POC, workflow, intake/build/critic) vóór de Ollama-
orchestrator draait.

```bash
pip install laya-mlx   # arm64 macOS only (staat ook in requirements.txt)
# DEEP_AGENT_LAYA=1    # default op Apple Silicon; zet 0 om uit te schakelen
```

- Start van elke `live.py`-run: journal-regel `kind: laya`; hint in de user message **alleen**
  als `primary_poc` én `workflow` confidence ≥ `LAYA_MIN_CONFIDENCE` (default **0.55**).
  Anders: journal “hint onderdrukt”, orchestrator routeert zonder Laya-blok.
- Orchestrator-tool: `laya_advise_request` voor her-classificatie mid-run.
- Dashboard: dropdown **Laya routing (MLX)**; timeline toont groene `laya`-stappen.

Laya vervangt de orchestrator niet — zero-shot scores zijn beperkt; gebruik het als
snelle lokale head naast tool-calling LLM’s.

### Human-in-the-loop (HITL) — de mens-agent-grens

`eindhoven-bp2op` volgt MC-6 (VNG-methode): niets wordt door AI gekoppeld, de
jurist beslist. Het enige interrupt-punt is daarom de tool
`run_bp2op_transform` (`hitl.py::HITL_TOOLS`, decisions `approve`/`reject`).

- **Live-runner:** bij een interrupt journalt `live.py` een `hitl_pending`-
  regel en sluit af met exit-code 2. De `SqliteSaver`-checkpointer
  (`runs/live/checkpoints.sqlite`, thread `nldt-live`) bewaart de run, zodat
  het menselijke verdict — ook over een procesgrens — de run kan hervatten.
- **Dashboard:** de poll (700 ms) toont de pending-kaart met de MC-6-
  toelichting; Goedkeuren/Afkeuren vereist een opmerking (leeg → geweigerd,
  server bevestigt met 400), een 409 betekent "al beslist of andere
  interrupt".
- **Resume:** via de CLI `python resume.py <interruptId> (--approved|
  --rejected) --comment "…" [--operator naam]` (exit 0/3/4) of via de server:
  `POST /api/hitl/verdict` schrijft het verdict eerst duurzaam weg en spawnt
  dan resume.py; `GET /api/hitl/pending` leest authoritair uit de
  checkpoint-state en overleeft daarmee een serverherstart (ledger als
  fallback).
- **Duurzaam ledger:** requests én verdicts landen append-only in
  `runs/live/hitl-verdicts.jsonl` (dubbelweegschrif-contract: server én
  resume.py schrijven elk een record; consumers zijn set-based/last-wins).
- **Dev-flag:** `--auto-approve-hitl` hervat in-process met een machinaal
  verdict, in het ledger expliciet gemarkeerd als `auto: true` (operator
  `dev-flag`).
- **Leerstaat:** pending = open beslis-trail, verdict = afgehandeld met de
  opmerking als didItHelp-materiaal; rapport:
  `cd nldt && PYTHONPATH=. .venv/bin/python -m services.memory.report`.

Bewuste beperking: het recipes-invoke-pad (`agent.py`, thread `nldt-recipes`)
heeft géén checkpointer — interrupts zijn daar niet ondersteund; HITL werkt
uitsluitend in de live-runner. Volledig ontwerp en contract:
[2026-10-07-hitl-mens-agent-grens.md](../docs/superpowers/plans/2026-10-07-hitl-mens-agent-grens.md).

## Next steps

- Wire a `run_recipe` tool to the Cookbook + OGC process backends (per POC).
- Consider a store/checkpointer for multi-turn sessions with shared POC memory.
