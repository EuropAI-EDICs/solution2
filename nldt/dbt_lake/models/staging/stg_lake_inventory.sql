{{ config(materialized='view') }}

-- Staging: flatten lake inventory Parquet (Iceberg mirror).
select
  id,
  poc,
  zone,
  kind,
  "accessClass" as access_class,
  "lakeKey" as lake_key,
  "lakeUri" as lake_uri,
  "localPath" as local_path,
  sha256,
  bytes,
  "exists" as exists_flag,
  "layerCount" as layer_count,
  license,
  "sourceId" as source_id
from read_parquet('{{ env_var("NLDT_LAKE_INVENTORY_PARQUET", "../data/lake/nldt-poc-lake/iceberg/mirrors/inventory.parquet") }}')
