{{ config(materialized='table') }}

-- Latest peilen from CDC lake pipeline + freshness vs now().
select
  peilgebied_id,
  waterstand_m,
  measured_at,
  source,
  cdc_lsn,
  applied_at,
  date_diff('second', measured_at, current_timestamp) as freshness_seconds
from {{ ref('stg_rijnland_peilen_cdc') }}
order by measured_at desc nulls last
