# Rijnland water levels — tool inputs

## `run_peil_conflict`

| Param | Required | Notes |
|-------|----------|-------|
| `mode` | no | Default `replay`. |
| `runDir` | no | Existing run pack. |
| `outDir` | no | Output directory. |
| `bbox` | no | Optional spatial filter. |
| `noH3` | no | Skip heavy H3 when set. |

Process: `rijnland-peil-conflict` · Recipe: `rijnland-peil-conflict`.  
Datasets: formal peilgebied × practice deviation (`sources.json`).

## `run_peil_conflict_live`

Same process id; CDC lake snapshot path. Prefer when demonstrating lake-backed conflict.

## `run_peil_whatif`

| Param | Required | Notes |
|-------|----------|-------|
| `delta_m` | yes | Water-level delta in metres (mNAP). |
| `layer` | no | Default `boezem` (`polders` \| `boezem` \| `all`). |
| `limit` | no | Cap features if needed. |
| `scenarioId` | no | Default `whatif`. |
| `applyToLake` | no | Default true — write scenario to lake path when enabled. |

Process: `rijnland-peil-whatif` · Recipe: `rijnland-peil-whatif`.  
Datasets: lake/CDC peilen silver (+ local archive via ingest).

## Lake ingest (process MCP / orchestrator)

Recipe `timeseries-open-ingest` → process `timeseries-ingest-run` includes `rijnland-peilen` from `poc-rijnland/data/peilen/peilen.json` when present.
