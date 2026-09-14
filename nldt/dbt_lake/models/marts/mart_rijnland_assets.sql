{{ config(materialized='table') }}

-- Rijnland ArcGIS catalog + static bulk snapshot rows from lake inventory.
select
  id,
  kind,
  zone,
  access_class,
  lake_uri,
  lake_key,
  bytes,
  layer_count,
  source_id,
  exists_flag
from {{ ref('stg_lake_inventory') }}
where poc = 'rijnland'
  and (
    kind like 'arcgis%'
    or lake_key like 'bronze/rijnland/arcgis%'
    or kind in ('layer', 'flow', 'wkp', 'restricted-archive', 'manifest')
  )
order by bytes desc nulls last
