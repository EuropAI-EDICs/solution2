# Phase 3 — Explore scenarios & use cases

Goal: turn lake-backed evidence into governed what-if / scan / transform runs.

## Pick a domain path

Use `list_poc_capabilities` then open the matching skill:

| Use case family | Skill | Key poc-mcp tools |
|-----------------|-------|-------------------|
| Five-value spatial politics (Breda) | `breda-scan` | `run_value_scan`, `ask_scan` |
| Policy scenario author + sweep (Utrecht) | `utrecht-scenario` | `propose_scenarios`, `run_scenario_sweep` |
| Peil conflict / measured levels / CDC what-if (Rijnland) | `rijnland-peilen` | `run_peil_conflict*`, `run_peil_whatif` (+ lake ingest) |
| Opportunity map / crosstrack / bp2op | router → reserved skills / tools | `run_opportunity_map`, `run_crosstrack`, `run_bp2op_transform` |

Optional hinter: S10 Deep Research (`NLDT_DEEP_RESEARCH`) → `ResearchBrief` hints only for S7 — never dispose.

## Scenario exploration loop

1. **Baseline** — replay or lake-backed run for the twin.
2. **Propose** — hybrid author default (det floor + LLM explorer) where S7 applies.
3. **Dispose** — sweep / scan / what-if via tools → processes.
4. **Critic** — ValidationReport V0–V4; keep reject ledgers.
5. **Narrate** — cite-or-abstain (S4/S8); no invented numbers.
6. **Feed lake** — gold scenario packs may be indexed for ES discovery (`kind=scenario_gold`).

## Checklist

- [ ] Domain skill read before first poc tool call
- [ ] Inputs grounded in lake or baseline `runDir`
- [ ] HITL respected when `riskLevel: high`
- [ ] Artefacts retained under run dirs / `nldt/data/runs/`

## Docs

- `docs/GENAI_SEAMS.md`
- `nldt/11-poc-patterns-scenarios-qa.md`
- `nldt/12-governed-agent-layer.md`
- Domain skills under `nldt/skills/poc/`
