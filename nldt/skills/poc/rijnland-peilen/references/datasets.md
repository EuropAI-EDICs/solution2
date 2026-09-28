# Rijnland — available water-level datasets

All ids below are listed in `poc-rijnland/data/sources.json` (English `title` + optional `titleNL`).

## Geometry (conflict)

| Id | Variable | Notes |
|----|----------|-------|
| `rijnland-peilgebied-vigerend` | water_level_target | Formal peil polygons (EPSG:28992) |
| `rijnland-peilafwijking-praktijk` | water_level_deviation | Practice deviations vs formal |

Tools: `run_peil_conflict`, `run_peil_conflict_live`.

## Measured stations & series

| Id | Unit | Notes |
|----|------|-------|
| `rijnland-peilen-agol-polders` | mNAP | Live AGOL FeatureServer — polders |
| `rijnland-peilen-agol-boezem` | mNAP | Live AGOL FeatureServer — boezem |
| `rijnland-peilen-hydronet-charts` | mNAP | ~12-day series via each station `chartUrl` |
| `rijnland-peilen-archive` | mNAP | Local `data/peilen/peilen.json` (daily medians) |

Fetch/merge: `poc-rijnland/scripts/fetch_peilen.py`.  
Render: `poc-rijnland/run_peilen.py` → time page + `hexmap-peilen-tijd.html`.  
Lake ingest (`timeseries-open-ingest`) defaults to **all** stations in the archive (`maxPeilStations` omit/≤0); set a positive integer only to cap for smoke tests.

## Lake / CDC

| Id | Access | Notes |
|----|--------|-------|
| `rijnland-peilen-lake-silver` | restricted | From `timeseries-open-ingest` / `normalize_rijnland_peilen` |
| CDC peilen silver | restricted | What-if deltas via `run_peil_whatif` |

Discover:

```text
search_lake_elasticsearch(q="peil", poc="rijnland", kind="timeseries_series")
search_lake_datasets(poc="rijnland")
```

## Out of scope for “water levels”

- WKP surface-water **quality** monthly series (`rijnland-wkp`, `data/wkp/…`)
- Routine quality monitoring points (`rijnland-meetpunt-waterkwaliteit-routine`)
- Primary watercourses / flow fixtures (`data/flow/…`)

Use those for context or blind-spot analysis, not as peil mNAP sources.
