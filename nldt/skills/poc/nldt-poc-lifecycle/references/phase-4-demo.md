# Phase 4 — Interactive demo website

Goal: ship a **static**, shareable explainer that shows architecture + PoC walkthroughs (no live secrets).

## Pattern in this repo

- Hub: `nldt/simulation/index.html`
- Reference implementation: `nldt/simulation/poc-mcp-skills.html`
  - Clickable layers (Host → Skill → Tool → Process → Engine)
  - PoC tabs with Play tours and tool-pick schematics
  - Embedded skill/tool metadata (mirrors `skill://index.json`)

## Build steps

1. **Decide the story** — lifecycle overview, single PoC, or cross-twin comparison.
2. **Copy the composition pattern** — one hero + canvas + detail panel; Fraunces + DM Sans; teal/ink on paper (avoid purple/cream AI clichés and dark dashboards unless asked).
3. **Embed data** — skills, tools, process ids, recipes as JS constants (no fetch to MCP required for the demo).
4. **Tours** — phase or PoC steps that highlight which tool is picked (`tools/call` schematic).
5. **Link** — add entry on `simulation/index.html` and a one-liner in the relevant `nldt/2x-*.md` doc.
6. **Language** — English UI by default for architecture demos unless the user asks for Dutch.

## Checklist

- [ ] Opens via file:// or simple static server (no build step)
- [ ] Keyboard: arrows / Esc for tours
- [ ] Mobile: canvas stacks above panel
- [ ] No API keys, tokens, or live lake credentials in the page
- [ ] Points back to `skill://` URIs and doc 20 for agents

## Optional later

- Wire a thin “open simulation” note in orchestrator run annex
- Mirror skill files into `.cursor/skills` for hosts without SEP-2640 hydration
