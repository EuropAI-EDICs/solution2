---
name: rijnland-peilen
description: Runs Rijnland water-level (peil) conflict analysis, measured station archives, lake/CDC ingest, and what-if maps via nldt-poc-mcp. Use when the user mentions Rijnland, peilen, water levels, mNAP, boezem, polders, peil conflict, HydroNET, or run_peil_whatif / run_peil_conflict / timeseries-open-ingest for rijnland-peilen.
---

# Rijnland water levels (peilen)

Governed dispose only: MCP tools → processes `rijnland-peil-conflict` / `rijnland-peil-whatif`, plus lake recipe `timeseries-open-ingest` for measured peilen. Do not invent peil deltas outside the engine.

## Water-level datasets (start here)

| Dataset | Use for |
|---------|---------|
| Formal peilgebied + practice deviation (ArcGIS) | Conflict geometry (`run_peil_conflict`) |
| AGOL live polder/boezem stations + HydroNET charts | Measured mNAP; snapshot with `fetch_peilen.py` |
| Local archive `data/peilen/peilen.json` | Growing daily series; `run_peilen.py` maps |
| Lake silver `rijnland-peilen` / CDC | ES discovery + `run_peil_whatif` |

Full catalogue: [datasets.md](references/datasets.md) · registry: `poc-rijnland/data/sources.json`.

## Quick start

1. **Discover** — catalog `search_lake_elasticsearch` (`poc=rijnland`, timeseries) or read `sources.json`.
2. **Conflict** — `run_peil_conflict` (replay) or `run_peil_conflict_live` (CDC lake path).
3. **Measured levels** — refresh archive (`scripts/fetch_peilen.py`), optional lake ingest (`timeseries-open-ingest`).
4. **What-if** — `run_peil_whatif` with `delta_m` (optional `layer=boezem|polders|all`).
5. Expect `jobId`, `status`, `outputs`, `prov`. Cite only artefact numbers.

## Workflow checklist

- [ ] Confirm Rijnland / water-level context (not Breda scan or Utrecht scenario)
- [ ] Prefer replay for tests; live/CDC only when lake data is available
- [ ] Distinguish **levels** (peilen, mNAP) from **quality** (WKP) datasets
- [ ] For what-if: state the delta clearly; do not invent map scores
- [ ] If Critic/HITL fails, stop and report

## References

- [datasets.md](references/datasets.md) — water-level sources
- [inputs.md](references/inputs.md) — tool parameters
- [artifacts.md](references/artifacts.md) — expected outputs
- Architecture: `nldt/20-poc-mcp-skills.md`
- CDC: `nldt/15-cdc-data-lake-pipeline.md`
- PoC README: `poc-rijnland/README.md`
