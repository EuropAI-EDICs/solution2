# Phase 2 — Ingest & convert in the data lake

Goal: land raw data in **bronze**, normalise to **silver**, optionally publish **gold** / Data Space offers.

Doctrine: dispose only via registered processes/recipes. Prefer `NLDT_OFFLINE=1` replay for CI.

## Primary recipes / processes

| Intent | Recipe | Process |
|--------|--------|---------|
| Harvest data.overheid.nl → lake + DCAT | `donl-harvest-run` / `donl-harvest-publish` | `donl-harvest-run` |
| Cross-twin timeseries (Rijnland/KNMI/CBS Breda, …) | `timeseries-open-ingest` | `timeseries-ingest-run` |
| Publish dataset offer (ODRL / EDC) | `lake-publish-offer` | `lake-publish-dataset` |
| Source continuity probe | `source-monitor-run` | `source-monitor-probe` |

Execute via **process MCP** (`execute` / recipe run) or orchestrator:

```bash
PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run \
  --recipe timeseries-open-ingest --auto-approve-hitl
```

## Conversion rules

1. **Bronze** — immutable raw snapshot (audit/replay).
2. **Silver** — schema-normalised tables/GeoJSON/parquet for Cook; tag `poc=…`.
3. **Gold** — schema-valid run artefacts / scenario packs.
4. Re-run `search_lake_elasticsearch` after ingest so scenario authors can discover series.
5. Restricted `accessClass` → `lake-publish-offer` must stop for HITL.

## Checklist

- [ ] Ingest job `status=successful` + PROV
- [ ] Lake inventory / ES shows new series or dataset
- [ ] Deny-list / accessClass respected
- [ ] No ad-hoc writes outside `services/lake/` and registered handlers

## Docs

- `nldt/13-data-lake-and-space.md`
- `nldt/15-cdc-data-lake-pipeline.md`
- `nldt/18-donl-harvest.md`
- `nldt/17-source-monitor.md`
