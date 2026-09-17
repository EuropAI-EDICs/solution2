# 12 — Governed agent layer (nLDT/MCP across all PoCs)

> Status: **done** (Phase 5 baseline, 2026-09-15).  
> Source: [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) *What’s next* §3 ·
> slides *Next 3 — nldt/MCP orchestration*.

Patterns and doctrine are in place (docs 05 / 07 / 11). Utrecht, Eindhoven,
Rijnland and Breda share catalog / process / critic / HITL rules via nLDT
Processes + Recipes + MCP. Per-PoC CLIs remain the **engines**; nLDT is the
governed front door.

Doctrine remains: **AI proposes · pipeline disposes · human decides.**

---

## Current state vs. goal

| | Now | Goal |
|---|----|------|
| Orchestration | LangGraph + recipe force / catalog match | ✅ One graph for GIS + PoC recipes |
| Seams S4/S7/S8 | Processes + MCP tools | ✅ Registered; engines stay in PoC packages |
| Critic | Shared `ValidationReport` (V0–V4) | ✅ Same schema; V2 filled per PoC recipe |
| Catalog | GIS + PoC recipes/processes | ✅ tags `poc-*` |
| HITL / PROV | Plan gate + run artifacts | ✅ `riskLevel: high` → needs_human; `prov.json` + reject ledgers |

---

## Build order (Phase 5) — status

### 5.0 — Contract bridge ✅

1. PoC schemas linked under [`schemas/poc/`](schemas/poc/) (symlinks to `poc/schemas/`).
2. `load_schema()` resolves `nldt/schemas/` and `nldt/schemas/poc/`.
3. Process **`validate-artifact`** + module
   [`services/common/artifact_validate.py`](services/common/artifact_validate.py).

### 5.1 — PoC pipelines as Processes ✅

Registered in `services/process_adapter/poc_handlers.py` + catalog seed:

| processId | Status | Notes |
|-----------|--------|-------|
| `opportunity-map-run` | ✅ | replay (default) + execute |
| `scenario-sweep` | ✅ | wraps `poc/scenarios/run.py` |
| `crosstrack-overlay` | ✅ | replay + execute |
| `breda-scan-run` | ✅ | replay + execute |
| `breda-scan-query` | ✅ | S4 offline Q&A |
| `scenario-author-propose` | ✅ | S7 auto\|llm\|**hybrid** (default hybrid) |
| `rijnland-peil-conflict` | ✅ | replay + execute |
| `rijnland-peil-whatif` | ✅ | CDC what-if map |
| `bp2op-transform` | ✅ | Eindhoven `poc-bp2op/run.py` |
| `validate-artifact` | ✅ | Phase 5.0 schema gate |

Tests: `tests/test_poc_processes.py`, `tests/test_phase5_governed.py`.

### 5.2 — Recipes in Cookbook ✅

| recipeId | Status |
|----------|--------|
| `utrecht-opportunity-map` | ✅ (risk high → HITL) |
| `utrecht-scenario-sweep` | ✅ |
| `utrecht-scenario-author` | ✅ |
| `breda-scan-qa` | ✅ |
| `breda-five-value-scan` | ✅ |
| `multi-track-crosstrack` | ✅ |
| `rijnland-peil-conflict` | ✅ |
| `rijnland-peil-whatif` | ✅ |
| `eindhoven-bp2op` | ✅ (risk high → HITL) |

### 5.3 — MCP tool surface ✅

- `services/mcp_servers/poc_server.py` (`nldt-poc-mcp`) — aliases over process execution
- `list_poc_capabilities` on catalog MCP (`find_poc_capabilities` in seed)
- Tools: `run_opportunity_map`, `propose_scenarios`, `run_scenario_sweep`,
  `ask_scan`, `run_value_scan`, `run_crosstrack`, `run_peil_*`, `run_bp2op_transform`

### 5.4 — Critic + HITL uniform ✅

- Every orchestrator run writes `validation-report.json` + `prov.json` under
  `nldt/data/runs/<runId>/`.
- `riskLevel: high` → plan verdict `needs_human` unless `--auto-approve-hitl`.
- Reject ledgers surfaced as `reject-ledger.json` / `proposals-rejected.json`.
- Critic V2 coverage: Breda, Utrecht A/B/C, Rijnland, Eindhoven.

### 5.5 — Remaining PoCs ✅

- `poc-rijnland` → process + recipes (conflict + what-if)
- `poc-bp2op` → process `bp2op-transform` + recipe `eindhoven-bp2op`

Still optional later: async job timeouts for long sweeps; timeseries as separate
Rijnland processes.

---

## What is deliberately *not* in Phase 5

- LLM that writes zones or corpora
- Replacing PoC zone engines with something new
- Source monitor (GENAI_SEAMS “watching data sources”) — **MVP done** · [17-source-monitor.md](17-source-monitor.md)
- Full S1/S2/S3 from Phase C of GENAI_SEAMS annex (norm harvesting fan-out)

---

## Acceptance criteria

1. ✅ `PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run --request "…" --recipe breda-scan-qa --input question=… --auto-approve-hitl` → `ValidationReport.verdict` ∈ {pass, needs_human, fail} + PROV bundle.
2. ✅ Same Critic schema for GIS recipe and PoC recipe (`validation-report.schema.json`).
3. ✅ S7 proposals: reject ledger retained when present (`proposals-rejected.json`).
4. ✅ Catalog `find_records(q="scenario")` / `find_poc_capabilities()` finds PoC recipes.
5. ✅ This file + [08-roadmap.md](08-roadmap.md) mark Phase 5 done.

---

## Relation to existing docs

| Doc | Role |
|-----|------|
| [05-agentic-ai-layer.md](05-agentic-ai-layer.md) | Roster + seams S1–S3 / S7–S8 |
| [11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md) | Patterns (done) |
| **This file** | Runtime unification (**done**) |
| [08-roadmap.md](08-roadmap.md) | Phase 5 |
| [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) | Public “What’s next” |
