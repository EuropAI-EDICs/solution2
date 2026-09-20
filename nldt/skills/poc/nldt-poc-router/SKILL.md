---
name: nldt-poc-router
description: Routes agents to the right nLDT PoC Agent Skill and MCP tools (Breda, Utrecht, Rijnland, Eindhoven). Use when the user asks which PoC to run, how to start a scan/scenario/what-if, or when discovering nldt-poc-mcp capabilities.
---

# nLDT PoC router

Doctrine: **AI proposes · pipeline disposes · human decides.** Read a companion skill, then call MCP tools on `nldt-poc-mcp`. Do not invent dispose paths outside process jobs.

## Quick start

1. Prefer catalog tool `list_poc_capabilities` (on `nldt-catalog-mcp`) for process/recipe ids.
2. Load the matching skill below via `resources/read` on its `skill://…/SKILL.md` URI.
3. Call only the tools that skill lists. Expect `jobId`, `ValidationReport`, and PROV from the process layer.

## Skill map

| Need | Skill URI |
|------|-----------|
| Breda five-value scan / S4 Q&A | `skill://nldt/poc/breda-scan/SKILL.md` |
| Utrecht scenario author + sweep (S7/S8) | `skill://nldt/poc/utrecht-scenario/SKILL.md` |
| Utrecht opportunity map (Plane A) | `skill://nldt/poc/utrecht-opportunity-map/SKILL.md` *(reserved — fill later)* |
| Utrecht crosstrack (Plane C) | `skill://nldt/poc/utrecht-crosstrack/SKILL.md` *(reserved)* |
| Rijnland peilen | `skill://nldt/poc/rijnland-peilen/SKILL.md` *(reserved)* |
| Eindhoven bp2op | `skill://nldt/poc/eindhoven-bp2op/SKILL.md` *(reserved)* |

Index: `skill://index.json`.

## Checklist

- [ ] Identify PoC from user intent (city / plane / artefact type)
- [ ] Read the PoC skill before the first tool call
- [ ] Pass required inputs; use `mode=replay` for offline/CI
- [ ] Surface HITL when recipe `riskLevel` is high
- [ ] Cite numbers only from returned artefacts (cite-or-abstain)
