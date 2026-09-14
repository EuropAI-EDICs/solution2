"""Apache Iceberg warehouse for nLDT lake inventory.

Uses **PyIceberg** ``SqlCatalog`` (SQLite) for real Iceberg table metadata
on the local filesystem warehouse. DuckDB reads via Parquet mirror (always).

Layout::

    data/lake/nldt-poc-lake/iceberg/
      catalog.db                 # SqlCatalog SQLite
      warehouse/                 # Iceberg table files
      mirrors/inventory.parquet  # dbt / DuckDB fast path
      bootstrap.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.lake import (
    DEFAULT_BUCKET,
    NLDT_ROOT,
    duckdb_connect,
    fs_root,
    write_inventory_parquet,
)


def iceberg_root() -> Path:
    root = fs_root() / DEFAULT_BUCKET / "iceberg"
    root.mkdir(parents=True, exist_ok=True)
    return root


def catalog_db_path() -> Path:
    return iceberg_root() / "catalog.db"


def warehouse_path() -> Path:
    p = iceberg_root() / "warehouse"
    p.mkdir(parents=True, exist_ok=True)
    return p


def mirror_inventory_path() -> Path:
    p = iceberg_root() / "mirrors" / "inventory.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _pyiceberg_catalog():
    from pyiceberg.catalog.sql import SqlCatalog

    return SqlCatalog(
        "nldt",
        **{
            "uri": f"sqlite:///{catalog_db_path().resolve().as_posix()}",
            "warehouse": warehouse_path().resolve().as_uri(),
        },
    )


def _inventory_rows(inventory_path: Path) -> list[dict[str, Any]]:
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    rows = []
    for row in data.get("datasets") or []:
        rows.append(
            {
                "id": row.get("id"),
                "poc": row.get("poc"),
                "zone": row.get("zone"),
                "kind": row.get("kind"),
                "accessClass": row.get("accessClass"),
                "lakeKey": row.get("lakeKey"),
                "lakeUri": row.get("lakeUri"),
                "localPath": row.get("localPath"),
                "sha256": row.get("sha256"),
                "bytes": int(row["bytes"]) if row.get("bytes") is not None else None,
                "exists": bool(row.get("exists")),
                "layerCount": int(row["layerCount"]) if row.get("layerCount") is not None else None,
                "license": row.get("license"),
                "sourceId": row.get("sourceId"),
            }
        )
    return rows


def bootstrap_inventory_iceberg(
    *,
    inventory_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Materialize inventory as Parquet mirror + Iceberg table ``lake.inventory``."""
    inv = inventory_path or (NLDT_ROOT / "data" / "lake-inventory.json")
    parquet = write_inventory_parquet(inv)
    mirror = mirror_inventory_path()
    if parquet.resolve() != mirror.resolve():
        mirror.write_bytes(parquet.read_bytes())

    rows = _inventory_rows(inv)
    mode = "parquet_mirror"
    iceberg_meta_location: str | None = None

    try:
        import pyarrow as pa
        from pyiceberg.schema import Schema
        from pyiceberg.types import (
            BooleanType,
            LongType,
            NestedField,
            StringType,
        )

        catalog = _pyiceberg_catalog()
        try:
            catalog.create_namespace("lake")
        except Exception:
            pass

        identifier = "lake.inventory"
        try:
            catalog.drop_table(identifier)
        except Exception:
            pass

        schema = Schema(
            NestedField(1, "id", StringType(), required=False),
            NestedField(2, "poc", StringType(), required=False),
            NestedField(3, "zone", StringType(), required=False),
            NestedField(4, "kind", StringType(), required=False),
            NestedField(5, "accessClass", StringType(), required=False),
            NestedField(6, "lakeKey", StringType(), required=False),
            NestedField(7, "lakeUri", StringType(), required=False),
            NestedField(8, "localPath", StringType(), required=False),
            NestedField(9, "sha256", StringType(), required=False),
            NestedField(10, "bytes", LongType(), required=False),
            NestedField(11, "exists", BooleanType(), required=False),
            NestedField(12, "layerCount", LongType(), required=False),
            NestedField(13, "license", StringType(), required=False),
            NestedField(14, "sourceId", StringType(), required=False),
        )
        table = catalog.create_table(identifier, schema=schema)
        arrow = pa.Table.from_pylist(rows)
        # Align nullability / types loosely via cast where needed
        table.append(arrow)
        iceberg_meta_location = table.metadata_location
        mode = "pyiceberg+parquet"
    except Exception as exc:
        mode = f"parquet_only:{type(exc).__name__}:{exc}"

    duck_mode = "skipped"
    try:
        con = duckdb_connect()
        db = iceberg_root() / "warehouse.duckdb"
        con.execute(f"ATTACH '{db.as_posix()}' AS ice")
        con.execute("CREATE SCHEMA IF NOT EXISTS ice.lake")
        con.execute("DROP TABLE IF EXISTS ice.lake.inventory")
        con.execute(
            f"CREATE TABLE ice.lake.inventory AS SELECT * FROM read_parquet('{mirror.as_posix()}')"
        )
        duck_mode = "duckdb_table"
    except Exception as exc:
        duck_mode = f"error:{exc}"

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "catalogDb": catalog_db_path().as_posix(),
        "warehouse": warehouse_path().as_posix(),
        "table": "lake.inventory",
        "parquet": parquet.as_posix(),
        "mirror": mirror.as_posix(),
        "metadataLocation": iceberg_meta_location,
        "mode": mode,
        "duckdb": duck_mode,
        "rows": len(rows),
        "force": force,
    }
    (iceberg_root() / "bootstrap.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def query_inventory(
    sql: str = (
        "SELECT poc, zone, count(*) AS n, sum(bytes) AS bytes "
        "FROM read_parquet(?) GROUP BY 1, 2 ORDER BY 1, 2"
    ),
):
    con = duckdb_connect()
    return con.execute(sql, [mirror_inventory_path().as_posix()]).fetchall()
