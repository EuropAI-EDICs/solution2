# 12 — Governed agent layer (nLDT/MCP across all PoCs)

> Status: **still to build.**  
> Source: [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) *What’s next* §3 ·
> slides *Next 3 — nldt/MCP orchestration*.

Patterns and doctrine are in place (docs 05 / 07 / 11). What **does not** exist: one
orchestration path in which Utrecht, Eindhoven, Rijnland and Breda run the same
catalog/process/critic/HITL rules via nLDT MCP — instead of per-PoC
CLIs and seams.

---

## Current state vs. goal

| | Now | Goal |
|---|----|------|
| Orchestration | Per PoC: `poc/run.py`, `poc-breda/qa_run.py`, … | One LangGraph + MCP |
| Seams S4/S7/S8 | In-package (`poc-breda/breda/qa.py`, `scenario_author.py`) | Registered as **processes/tools** the planner may compose |
| Critic | PoC-owned + nLDT-recipe-owned | Same V0–V4 contract; V2 filled per artifactType |
| Catalog | GIS recipes only (`spatial-overlay`, `hex-overlay`) | + opportunity-map, scenario-sweep, scan Q&A, crosstrack |
| HITL / PROV | Fragmentary | Checkpoint per step, one audit-trail shape |

Doctrine remains: **AI proposes · pipeline disposes · human decides.**

---

## Build order (Phase 5)

### 5.0 — Contract bridge (1–2 days)

1. Mirror/share PoC schemas the agent layer must know:
   `norm-card`, `formal-rule`, `decision-table`, `scenario-spec`,
   `scenario-report`, `validation-report` (extend artifactTypes).
2. Document one `ValidationReport` vocabulary (already in doc 07) —
   implementation: shared validator module or process `validate-artifact`.

### 5.1 — PoC pipelines as Processes ✅ (baseline)

Registered in `services/process_adapter/poc_handlers.py` + catalog seed:

| processId | Status | Notes |
|-----------|--------|-------|
| `opportunity-map-run` | ✅ | replay (default) + execute |
| `scenario-sweep` | ✅ | wraps `poc/scenarios/run.py` |
| `crosstrack-overlay` | ✅ | replay + execute |
| `breda-scan-run` | ✅ | replay + execute |
| `breda-scan-query` | ✅ | S4 offline Q&A |
| `scenario-author-propose` | ✅ | S7 auto author |
| `rijnland-peil-conflict` | ✅ | replay + execute (`poc-rijnland/run.py`) |

Recipes: `breda-scan-qa`, `utrecht-scenario-sweep`, `utrecht-opportunity-map`,
`utrecht-scenario-author`, `rijnland-peil-conflict`. Tests: `tests/test_poc_processes.py`.

Lake touchpoint (Phase 6): Processes remain Cook outside the lake; silver via
`lake://` / cache; gold via sync/post-run. See
[13-data-lake-and-space.md](13-data-lake-and-space.md#ogc-processes-in-the-lake-pipeline).

Still open in 5.1+: timeout/job-async for long sweeps; MCP tool aliases (5.3).

### 5.2 — Recipes in Cookbook ✅ (baseline)

| recipeId | Status |
|----------|--------|
| `utrecht-opportunity-map` | ✅ |
| `utrecht-scenario-sweep` | ✅ |
| `utrecht-scenario-author` | ✅ |
| `breda-scan-qa` | ✅ |
| `rijnland-peil-conflict` | ✅ |
| `breda-five-value-scan` | open (use process `breda-scan-run` directly) |
| `multi-track-crosstrack` | open |

Planner (S2) may find these recipes via tags (`legal`, `scenario`, `scan`,
`poc-utrecht`, `poc-breda`, `poc-rijnland`).

### 5.3 — MCP tool surface

Extend or add new server `nldt-poc-mcp`:

| Tool | Maps to |
|------|---------|
| `list_poc_capabilities` | Catalog filter tags=poc-* |
| `run_opportunity_map` | process `opportunity-map-run` |
| `propose_scenarios` | process `scenario-author-propose` (S7) |
| `ask_scan` | process `breda-scan-query` (S4) |

Orchestrator remains the only one that **composes**; PoC code remains the engine.

### 5.4 — Critic + HITL uniform

- Every recipe run writes `ValidationReport` + `prov.json` under
  `nldt/data/runs/<runId>/` (same layout as spatial-overlay).
- `riskLevel: high` → `interrupt_before=["execute_steps"]`.
- Reject ledgers (`*-rejected.json`) become run artifacts, not only
  PoC-local files.

### 5.5 — Remaining PoCs (Eindhoven, Rijnland)

- `poc-rijnland` → ✅ process + recipe `rijnland-peil-conflict` (water-level conflict;
  timeseries/levels as separate processes still open)
- `poc-bp2op` → process `bp2op-transform` (or substeps) — open

---

## What is deliberately *not* in Phase 5

- LLM that writes zones or corpora
- Replacing PoC zone engines with something new
- Source monitor (GENAI_SEAMS “watching data sources”) — separate track
- Full S1/S2/S3 from Phase C of GENAI_SEAMS annex (norm harvesting fan-out)

---

## Acceptance criteria

1. `python -m agents.orchestrator.run --recipe breda-scan-qa …` ends with
   `ValidationReport.verdict` ∈ {pass, needs_human, fail} and PROV bundle.
2. Same Critic schema for GIS recipe and PoC recipe.
3. S7 proposal that fails schema → `proposals-rejected` artifact; no sweep.
4. Catalog `GET /collections/records?q=scenario` finds ≥1 PoC recipe.
5. Documentation: GENAI_SEAMS “What’s next §3” can move to **done** (or partial)
   with a link to this file + a run example.

---

## Relation to existing docs

| Doc | Role |
|-----|------|
| [05-agentic-ai-layer.md](05-agentic-ai-layer.md) | Roster + seams S1–S3 / S7–S8 |
| [11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md) | Patterns (done) |
| **This file** | Runtime unification (open) |
| [08-roadmap.md](08-roadmap.md) | Phase 5 |
| [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) | Public “What’s next” |
