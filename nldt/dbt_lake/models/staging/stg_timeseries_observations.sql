{{ config(materialized='view') }}

-- Staging stub: generic silver timeseries observations (JSONL mirrors).
-- Path override: NLDT_TIMESERIES_OBS_GLOB (default under lake FS root).
select
  seriesId as series_id,
  poc,
  variable,
  unit,
  cast(observedAt as timestamp) as observed_at,
  value,
  sourceId as source_id,
  accessClass as access_class
from read_json_auto(
  '{{ env_var("NLDT_TIMESERIES_OBS_GLOB", "../data/lake/nldt-poc-lake/silver/timeseries/**/observations.jsonl") }}',
  format='newline_delimited',
  ignore_errors=true
)
