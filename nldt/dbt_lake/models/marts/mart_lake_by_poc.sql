{{ config(materialized='table') }}

-- Lake footprint by PoC (bytes + dataset rows from inventory).
select
  poc,
  count(*) as dataset_count,
  sum(coalesce(bytes, 0)) as total_bytes,
  sum(case when zone = 'bronze' then coalesce(bytes, 0) else 0 end) as bronze_bytes,
  sum(case when zone = 'silver' then coalesce(bytes, 0) else 0 end) as silver_bytes,
  sum(case when zone = 'gold' then coalesce(bytes, 0) else 0 end) as gold_bytes,
  sum(case when access_class = 'restricted' then 1 else 0 end) as restricted_datasets,
  sum(case when access_class = 'open' then 1 else 0 end) as open_datasets
from {{ ref('stg_lake_inventory') }}
group by 1
order by total_bytes desc
