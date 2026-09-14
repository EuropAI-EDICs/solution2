{{ config(materialized='view') }}

-- Staging: CDC-applied peilen silver (DuckDB MERGE output).
select
  peilgebied_id,
  waterstand_m,
  measured_at,
  source,
  cdc_lsn,
  applied_at
from read_parquet('{{ env_var("NLDT_PEILEN_LATEST_PARQUET", "../data/lake/nldt-poc-lake/iceberg/mirrors/rijnland_peilen_latest.parquet") }}')
