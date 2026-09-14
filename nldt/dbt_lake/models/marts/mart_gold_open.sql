{{ config(materialized='table') }}

-- Gold-zone datasets eligible for Data Space offers (accessClass = open).
select
  id,
  poc,
  lake_uri,
  lake_key,
  sha256,
  bytes
from {{ ref('stg_lake_inventory') }}
where zone = 'gold'
  and access_class = 'open'
  and coalesce(exists_flag, true) = true
