{{ config(materialized='table') }}

-- Latest observation per series from the generic timeseries silver layer.
select
  series_id,
  poc,
  variable,
  unit,
  observed_at,
  value,
  source_id,
  access_class,
  date_diff('second', observed_at, current_timestamp) as freshness_seconds
from (
  select
    *,
    row_number() over (partition by series_id order by observed_at desc nulls last) as rn
  from {{ ref('stg_timeseries_observations') }}
)
where rn = 1
order by observed_at desc nulls last
