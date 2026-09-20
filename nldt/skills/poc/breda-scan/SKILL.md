---
name: breda-scan
description: Runs Breda five-value spatial scans and cite-or-abstain Q&A over scan artefacts via nldt-poc-mcp. Use when the user mentions Breda, five-value scan, scan Q&A, S4 ask_scan, or breda-scan-run/query.
---

# Breda scan

Governed dispose only: MCP tools → processes `breda-scan-run` / `breda-scan-query`. Do not recompute indicators outside the engine.

## Quick start

1. Run a scan (replay unless live data is required):

   - Tool: `run_value_scan`
   - Typical: `mode=replay` or omit `runDir` for seeded replay

2. Ask grounded questions against a run:

   - Tool: `ask_scan`
   - Required: `question`
   - Optional: `runDir`, `asker` (`auto` default)

3. Expect JSON with `jobId`, `status`, `outputs`, `prov`. Numbers in narration must appear in artefacts.

## Workflow checklist

- [ ] Confirm city/context is Breda (not Utrecht scenario sweep)
- [ ] Prefer replay for tests; execute only when lake/baseline is available
- [ ] For Q&A: pass the same `runDir` as the scan you want cited
- [ ] If Critic/HITL fails, stop and report — do not invent scores

## References

- [inputs.md](references/inputs.md) — tool parameters
- [artifacts.md](references/artifacts.md) — expected outputs
- Architecture: `nldt/20-poc-mcp-skills.md`
- Patterns: `nldt/11-poc-patterns-scenarios-qa.md`
