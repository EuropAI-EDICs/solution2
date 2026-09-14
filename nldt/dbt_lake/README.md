# dbt Core (dbt-duckdb) over nLDT lake

Transforms inventory / gold metadata into marts for catalog and Data Space
eligibility. Does **not** replace PoC engines.

## Setup

```bash
pip install dbt-core dbt-duckdb duckdb
# from nldt/
PYTHONPATH=. python scripts/build_lake_inventory.py
PYTHONPATH=. python scripts/lake_iceberg_bootstrap.py
cd dbt_lake
dbt deps --profiles-dir .   # if packages.yml present
dbt run --profiles-dir .
```

## Models

| Model | Purpose |
|-------|---------|
| `stg_lake_inventory` | Flatten inventory Parquet (Iceberg mirror) |
| `mart_datasets_by_access` | Counts by poc/zone/accessClass |
| `mart_gold_open` | Gold datasets safe for public offers |
| `mart_lake_by_poc` | Byte footprint per PoC / zone |
| `mart_rijnland_assets` | Rijnland ArcGIS + peil/WKP inventory rows |
| `stg_rijnland_peilen_cdc` | CDC-applied peilen silver (Parquet mirror) |
| `mart_peil_latest` | Latest waterstand + `freshness_seconds` |

Refresh everything:

```bash
cd nldt && PYTHONPATH=. python scripts/lake_lakehouse_refresh.py
# with CDC fixture (offline):
PYTHONPATH=. python scripts/lake_lakehouse_refresh.py \
  --cdc-fixture ../poc-rijnland/data/peilen/peilen.json
```
