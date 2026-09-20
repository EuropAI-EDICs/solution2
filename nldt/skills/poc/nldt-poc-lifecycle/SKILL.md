---
name: nldt-poc-lifecycle
description: Universal end-to-end workflow for any nLDT PoC — discover/research open datasets, ingest and convert into the medallion data lake, explore scenarios and use cases, then ship an interactive demo site. Use when starting a new PoC, onboarding a twin, researching data sources, lake ingest, scenario design, or building a simulation/demo HTML.
---

# nLDT PoC lifecycle (universal)

Doctrine: **AI proposes · pipeline disposes · human decides.**

This skill is the **default entry** for any city/domain PoC (Breda, Utrecht, Rijnland, Eindhoven, …). It chains four phases. After phase 3, hand off to a domain skill (`breda-scan`, `utrecht-scenario`, `rijnland-peilen`, …) for specialised tools.

```
Discover → Lake ingest/convert → Scenarios/use-cases → Interactive demo
```

Do **not** skip Critic/HITL. Do **not** write zones or lake silver/gold outside registered processes.

## Quick start

1. Read this skill fully, then open the phase reference you need.
2. Call catalog tools first (`search_records`, `search_lake_elasticsearch`, `list_poc_capabilities`).
3. Dispose only via process MCP / recipes (or poc tools that alias them).
4. For demos, extend `nldt/simulation/` (pattern: `poc-mcp-skills.html`) — static HTML, no secrets.

| Phase | Goal | Reference |
|-------|------|-----------|
| 1 Discover | Research datasets & continuity | [phase-1-discover.md](references/phase-1-discover.md) |
| 2 Lake | Ingest, convert, publish | [phase-2-lake.md](references/phase-2-lake.md) |
| 3 Scenarios | Use cases & what-if | [phase-3-scenarios.md](references/phase-3-scenarios.md) |
| 4 Demo site | Interactive explainer | [phase-4-demo.md](references/phase-4-demo.md) |
| EDIC city onboarding | CitiVERSE capacity module | [edic-city-onboarding.md](references/edic-city-onboarding.md) |

## Workflow checklist

- [ ] **1 Discover** — query catalog + Elasticsearch; note `accessClass`; run source-monitor if URLs are fragile
- [ ] **2 Lake** — bronze snapshot → silver convert → optional gold/publish (`lake-publish-offer` needs HITL for restricted)
- [ ] **3 Scenarios** — pick domain skill; propose/sweep/scan/what-if; keep reject ledgers
- [ ] **4 Demo** — interactive HTML under `nldt/simulation/`; link from `simulation/index.html`; English UI unless user asks otherwise
- [ ] Cite only artefact numbers; surface ValidationReport / PROV

## MCP servers involved

| Server | Role in this lifecycle |
|--------|------------------------|
| `nldt-catalog-mcp` | Discovery: records, lake datasets, ES search, `list_poc_capabilities` |
| `nldt-process-mcp` | Dispose: execute recipes/processes (DONL, timeseries, lake-publish, source-monitor, PoC engines) |
| `nldt-poc-mcp` | PoC tool aliases + **this** skill catalogue (`skill://`) |
| `nldt-data-mcp` | Optional live data-platform entities/streams |

## Hand-off to domain skills

| After you know the domain… | Open |
|----------------------------|------|
| Breda five-value / Q&A | `skill://nldt/poc/breda-scan/SKILL.md` |
| Utrecht S7/S8 scenarios | `skill://nldt/poc/utrecht-scenario/SKILL.md` |
| Rijnland peilen | `skill://nldt/poc/rijnland-peilen/SKILL.md` |
| Which specialised skill? | `skill://nldt/poc/nldt-poc-router/SKILL.md` |

Index: `skill://index.json`.

## Trust

- Skills = untrusted instructions. Lake mutations and scans only through processes.
- Restricted lake offers refuse without HITL.
- Demo pages embed **static** skill/tool metadata — never live credentials.
