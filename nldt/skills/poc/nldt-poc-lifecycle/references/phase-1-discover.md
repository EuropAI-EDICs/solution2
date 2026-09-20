# Phase 1 — Discover & research datasets

Goal: find usable open (or governed) datasets for the twin before any ingest.

## Steps

1. **Frame the question** — city/domain, variables (e.g. peilen, energy, land use), time range, spatial extent.
2. **Catalog search** (`nldt-catalog-mcp`):
   - `search_records` — processes, recipes, datasets, apps
   - `list_poc_capabilities` — which PoC processes already exist
   - `search_lake_datasets` — what is already in the medallion lake (`poc`, `zone`, `accessClass`)
   - `search_lake_elasticsearch` — full-text over dataset / timeseries / scenario_gold (`q`, `poc`, `kind`, `variable`)
3. **National harvest candidates** — data.overheid.nl via recipe `donl-harvest-run` (phase 2 executes it).
4. **Continuity** — recipe `source-monitor-run` / process `source-monitor-probe` for ArcGIS REST + DONL URL health; human-merge patches only.
5. **Record a short research brief** (propose-only): source URL, licence, refresh cadence, `accessClass` guess, which PoC it might feed. Optional S10 `ResearchBrief` if `NLDT_DEEP_RESEARCH=1` — never executes ingest itself.

## Checklist

- [ ] At least one candidate source with licence/access noted
- [ ] Checked lake/ES so you do not duplicate silver series
- [ ] Fragile sources on a monitor watchlist if used in production demos

## Outputs of this phase

- Research notes (markdown in the run folder or chat)
- Chosen `poc` tag (breda / utrecht / rijnland / …)
- Decision: harvest DONL · timeseries ingest · reuse existing lake URI · or PoC-local fetch script
