{{ config(materialized='table') }}

select
  poc,
  zone,
  access_class,
  count(*) as dataset_count,
  sum(coalesce(bytes, 0)) as total_bytes
from {{ ref('stg_lake_inventory') }}
group by 1, 2, 3
order by 1, 2, 3
