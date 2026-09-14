# 07 — Trust and governance

## Validation levels (V0–V4)

Taken from [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) §4. Same
**vocabulary** for nLDT recipes and PoC opportunity-map / scenario / crosstrack
— with **different V2/V3 interpretations** per plane. See
[11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md).

| Level | Check | nLDT recipes | PoC opportunity-map | PoC scenario-sweep | Crosstrack |
|-------|-------|--------------|---------------------|--------------------|------------|
| **V0** | Syntactic | AgentPlan, Recipe, outputs | All boundary schemas | `scenario-report` | report-schema |
| **V1** | Geometric | GeoJSON validity | CRS, area sanity | geometry per row | geometry-validity |
| **V2** | Grounding | Recipe/process ids in catalog | **Legal**: quote + doc + article; orphans | mutation↔ruleId, basis↔NormCard | `not_applicable` |
| **V3** | Replay | Optional stats tolerance | IoU ≥ 0.98, area Δ ≤ 1% | control Δ ≤ **0.1%** | per-track control |
| **V4** | Human | HITL when `riskLevel: high` | Always `pending` | Scenario choice = human | Arbitration = human |

Hard gate: no `recipe-execution` / pipeline-run artifact leaves the
orchestrator without a `ValidationReport` with `verdict`.

Verdict rollup: **fail** on V0–V3 fail; **needs_human** on skipped checks or
degradations; V4 does not block programming runs but remains visible.

## Cite-or-abstain (legal QA)

For legal claims (PoC plane A, simulation corpus):

1. No NormCard without `docId` + `article` + `version` + verbatim `quote` + `uri`
2. Abstentions → `*-rejected.json` ledger (auditable)
3. Formalizer never guesses predicates for open norms → `ambiguous` → V4
4. DecisionTable: every row links `normCardId` (contestability)

## Critic implementation

### nLDT recipes — `agents/orchestrator/nodes/critic.py`

- V0: `jsonschema.validate` against schemas in `nldt/schemas/`
- V1: `validate_geojson()` helper
- V2: catalog preflight (process + recipe ids)
- V3: optional for generic recipes (stats tolerance)
- V4: `pending` until HITL approve

### PoC pipeline — `poc/pipeline/critic.py`

- Version: `critic-validator#deterministic-v0-v3-poc1`
- Six ValidationReports: request, norm-card-set, formal-rule-set,
  zone-result-set, decision-table, **pipeline-run**
- V3 via independent re-execution (`engine.reexecute_independent`)

### PoC scenario — `poc/pipeline/scenarios.py`

- V2: mutation rule-ids + basis NormCard-ids (+ narrative grounding S8)
- V3: **control reproduction** stricter (rel Δ ≤ 0.001)

## PROV provenance

Every process execution generates:

```json
{
  "activity": "nldt:ProcessExecution/spatial-intersection",
  "agent": "nldt:ProcessAdapter/local",
  "generated": "nldt:JobResult/<jobId>",
  "used": ["nldt:Input/layer-a", "nldt:Input/layer-b"],
  "startedAtTime": "2026-08-31T12:00:00Z",
  "endedAtTime": "2026-08-31T12:00:01Z"
}
```

Orchestrator run bundles PROV in `runs/<runId>/provenance.json`.
PoC runs: `prov.json` with stages, agents, geo `lastChecked`, GIO join-ids.

## Human-in-the-loop

Triggers:

- `AgentPlan.requiresHitl === true`
- `recipe.riskLevel === "high"`
- `ValidationReport.verdict === "needs_human"`
- PoC: open norms (`ambiguous`), scenario choice, crosstrack arbitration

LangGraph: `interrupt_before=["execute_steps"]` when HITL is required.

Dev: auto-approve via `--auto-approve-hitl` flag.

## Guiding principles nLDT

| Principle | Measure |
|-----------|---------|
| Transparency | Explainer + PROV + process descriptions in catalog |
| Contestability | Evidence refs / NormCard links in ValidationReport & DecisionTable |
| Human oversight | HITL; no autonomous high-risk or final legal decision |
| Cite-or-abstain | No claim without source; reject ledger instead of silently guessing |
| Data minimisation | Inputs only what the recipe / FormalRule requires |
| Interoperability | OGC APIs as the only external interface (nLDT); PoC schemas as legal contracts |

## MCP supply chain

- Pin MCP server versions in `requirements.txt`
- Vend in-house servers (`services/mcp_servers/`)
- No arbitrary tool registration in orchestrator

## Audit

Log fields per run:

- `runId`, `recipeId`, `agentPlanId`, `validationVerdict`
- Process job ids, durations
- PoC: reject-ledger counts, rule-stats, scenario Δ/IoU
- Optional: export to trace store (OTel, Phase 4)
