# Design: nLDT simulations for all PoCs

**Date:** 2026-09-20  
**Status:** approved  
**Approach:** A — architecture tours + lightweight PoC story pages

## Goal

Extend `nldt/simulation/` so every governed PoC (Breda, Utrecht, Rijnland, Eindhoven)
has a discoverable static demo, and the MCP Skills architecture tour covers all four
domain PoCs (plus lifecycle/router).

## Non-goals

- Copying full Leaflet/Cesium run reports into `simulation/`
- Live MCP, lake, or ArcGIS fetches from the demo pages
- New Agent Skill for Eindhoven (tool/process already exist; skill remains reserved)
- Rewriting existing platform demos (building-agent, 3D BAG, agent-flow, overlay mock)

## Architecture

```
simulation/
  index.html              # Hub: PoC stories + platform demos
  poc-mcp-skills.html     # Architecture tour (+ Eindhoven tab, ?poc=)
  poc-breda.html          # Story: five-value scan
  poc-utrecht.html        # Story: opportunity / S7 scenarios
  poc-rijnland.html       # Story: peil conflict + what-if
  poc-eindhoven.html      # Story: bp2op transform + V4 HITL
  README.md               # Updated catalogue
```

Visual language: same tokens as `poc-mcp-skills.html` (paper/teal/Fraunces/DM Sans).
English UI for architecture + PoC stories (phase-4-demo default).

## Hub (`index.html`)

Two sections:

1. **PoC stories** — four cards (Breda, Utrecht, Rijnland, Eindhoven). Each card:
   - PoC name (brand-level)
   - One-sentence question
   - Links: story page · `poc-mcp-skills.html?poc=<id>` · skill:// hint in footer text
2. **Platform demos** — existing entries (MCP Skills+Recipes, building, 3D, flow, overlay)

## Architecture tour changes (`poc-mcp-skills.html`)

| Change | Detail |
|--------|--------|
| Tab | **Eindhoven bp2op** |
| `POC_TOOLS.eindhoven` | `run_bp2op_transform` → process `bp2op-transform`, recipe `eindhoven-bp2op` |
| `TOURS.eindhoven` | host → router/skill → tool pick → process → engine `poc-bp2op/` |
| Query | `?poc=breda\|utrecht\|rijnland\|eindhoven\|lifecycle\|router` selects tab on load |
| Skill list | Note Eindhoven as reserved / router-routed (tool exists without dedicated skill dir) |

## PoC story pages (shared pattern)

Each page is self-contained (no shared build step). Structure:

1. **Hero** — PoC name dominant; one headline; one supporting sentence; CTA (Play + link to architecture tour)
2. **Stage** — step rail + detail panel (kicker / title / body / trust / paths / skill·tool·process·recipe)
3. **Canonical numbers** — small embedded constants from READMEs (not full GeoJSON)
4. **Footer** — path to engine package, recipe id, doc 20

### Page content

| Page | Question | Play steps | Canonical numbers (examples) |
|------|----------|------------|------------------------------|
| Breda | Where does open data + AI create value across five congress values? | skill `breda-scan` → `run_value_scan` → `ask_scan` → artifacts | 5 values · 56 buurten · cite-or-abstain |
| Utrecht | Where can wind / solar / forest stand under the provincial ordinance? | skill `utrecht-scenario` → `propose_scenarios` → `run_scenario_sweep` | 3 tracks · S7 hybrid · Plane A/B/C |
| Rijnland | Where does practice deviate from formal peil? What-if deltas? | `run_peil_conflict` → ingest hint → `run_peil_whatif` | mNAP · CDC · risk high on what-if |
| Eindhoven | BP → OP rule matching with jurist checkpoint | `run_bp2op_transform` → bands → V4 pending | method cards MC-1…MC-12 · V4 always pending |

Controls: Play / Next / Reset (same mental model as architecture tour). No Cesium/Leaflet required.

## Docs

- `nldt/simulation/README.md` — list hub + four PoC stories + platform demos
- `nldt/20-poc-mcp-skills.md` — one-liner pointing at PoC story pages
- `nldt/skills/poc/nldt-poc-lifecycle/references/phase-4-demo.md` — checklist update

## Success criteria

- [ ] Hub lists all four PoCs with working links
- [ ] Eindhoven tour plays in `poc-mcp-skills.html`
- [ ] `?poc=` deep-links work
- [ ] Four story pages open via `file://` or `python -m http.server`
- [ ] No secrets / live credentials in HTML
- [ ] README + doc 20 + phase-4-demo updated
