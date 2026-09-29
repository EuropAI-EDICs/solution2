---
name: utrecht-scenario
description: Authors and sweeps Utrecht spatial scenarios (S7 hybrid propose + S8 sweep) via nldt-poc-mcp. Use when the user mentions Utrecht scenarios, Plane B, propose_scenarios, scenario sweep, hybrid author, or S7/S8.
---

# Utrecht scenario (Plane B)

Dispose only through MCP tools → `scenario-author-propose` / `scenario-sweep`. Deterministic proposals are the floor; LLM may only add novel keys under HITL.

## Quick start

1. Propose scenarios (product default **hybrid**):

   - Tool: `propose_scenarios`
   - Required: `baselineRunDir`
   - Optional: `author` (`hybrid` default), `maxScenarios`

2. Run a sweep:

   - Tool: `run_scenario_sweep`
   - Required: `useCase` (e.g. wind / zon / bos)
   - Optional: `baselineRunDir`, `author`, `scenarioSetPath`, `outDir`, `noH3`

3. Optional — scenario-copilot (world model Renderer contract):

   - Tool: `build_world_scene`
   - Required: `scenarioRunDir` (output of sweep)
   - Optional: `hitlApproved` (Marble explore URL for **hypothetical** scenarios only)
   - Demo: `nldt/simulation/utrecht-whatif-demo.html` · doc: `docs/POC_WORLD_MODEL_UTRECHT.md`

4. Keep reject ledgers; do not resurrect rejected `(ruleId, mutation)` pairs without human approval.

## Workflow checklist

- [ ] Confirm Utrecht Plane B (not Breda scan or opportunity-map Plane A)
- [ ] Provide a real `baselineRunDir` for propose
- [ ] Prefer `author=hybrid` unless the user asks for file/auto/llm-only
- [ ] After sweep, report Critic/HITL and cite only artefact numbers

## References

- [inputs.md](references/inputs.md)
- [artifacts.md](references/artifacts.md)
- Architecture: `nldt/20-poc-mcp-skills.md`
- S7 doctrine: `docs/GENAI_SEAMS.md`
