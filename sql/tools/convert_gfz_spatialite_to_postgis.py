#!/usr/bin/env python3
"""Convert the GFZ GDE 2023.01 SpatiaLite release into the EU Building Database
PostGIS schema (``exposure`` database, migrations ``sql/0000{0,1,2}_*.sql``).

Reconstructs the manual conversion performed on 2026-08-29 (see SETUP.md,
section "Data import: converted from public SpatiaLite release"). The mapping
is lossless except for two documented schema deviations:

1. ``entities_quadkey_check`` is dropped before load — the 2023.01 model uses
   quadkeys of zoom 15-18 while the official schema assumes zoom 18. 46% of
   the exposure sits below zoom 18 and cannot be losslessly promoted.
2. ``entity_assets.number`` stays REAL (official DDL); precise sums are
   computed as double precision (``sum(number::double precision)``).

Source model (data/NLD.The_Netherlands.db, DOI 10.5880/GFZ.2.6.2023.011):
``Entity`` (residual tiles, zoom 15-18), ``Taxonomy`` (GEM strings),
``Asset`` (entity-taxonomy exposure pairs). ``Building``/``Tile``/
``AssetCountry``/``Metadata`` are empty in this release and are not converted.

Target mapping (verified row-for-row against the live database):

=========================  ====================================================
target                     source
=========================  ====================================================
exposure.sources           one row documenting the release (--source-id, 2)
exposure.entities          Entity: ids + geometry preserved, category=0,
                           iso_3166='NLD', source_id as given
exposure.taxonomies        Taxonomy: ids preserved, category=1,
                           taxonomy = JSON string of taxonomy_string
exposure.assets            synthesized, one per taxonomy id (ascending),
                           attributes.legacy_2023_01 = per-taxonomy
                           double-precision sums of number/structural/night
                           rounded to 2 decimals
exposure.entity_assets     Asset: number preserved (REAL), relative_size=1
exposure.district_assets   Asset aggregated: one row per taxonomy, boundary
                           'NLD', number = sum(number)
sources.boundaries         'NLD' = ST_UnaryUnion(ST_Collect(tiles)) — model
                           coverage, not the exact country outline
exposure.metadata          provenance keys (converted_from, source_doi, ...)
=========================  ====================================================

The SpatiaLite GAIA geometry blobs are parsed in pure Python (the GDE 2023.01
writer emits a non-standard extra byte between the polygon count and the
polygon body; validated against all 329,437 rows and byte-identical
(ST_AsEWKB md5) against the live database). Coordinates are copied 1-on-1 as
little-endian doubles — no float round-trip.

Rebuild verified against the live database (2026-10-14): all row counts,
binary geometry identity, entity_assets content hash, district_assets values,
grand total sum 11,320,734.17 and the 129,193-point 'NLD' boundary are exact.
One of the 111 legacy sum values may differ from the original 2026-08-29
conversion by ±0.01 (tax 7229 sum_structural: 29688834695.43 vs …42) — float
summation-order noise from the original engine; double-precision fsum (used
here) is the correctly-rounded value.

Usage (psycopg3 lives in nldt/.venv)::

    nldt/.venv/bin/python sql/tools/convert_gfz_spatialite_to_postgis.py \\
        --spatialite data/NLD.The_Netherlands.db \\
        --dsn "host=localhost port=5432 dbname=exposure user=contributor"

The DSN needs the ``contributor`` role (~/.pgpass); TRUNCATE requires the
--truncate flag when the target tables are non-empty. ``--dry-run`` checks
the source only (no psycopg needed). Connection defaults come from the
standard PG* environment variables / pgpass when --dsn is omitted.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DSN = "host=localhost port=5432 dbname=exposure user=contributor"
SOURCE_DOI = "https://doi.org/10.5880/GFZ.2.6.2023.011"
SOURCE_NAME = "Global Dynamic Exposure model release 2023.01 (SpatiaLite)"
BOUNDARY_NOTE = (
    "union of converted GDE 2023.01 tiles; approximates model coverage, "
    "not the exact country outline"
)
GAIA_MULTIPOLYGON = 6
GAIA_POLYGON = 3
# Blob layout of the GDE 2023.01 writer (validated on all 329,437 rows):
# [0]=0x00 | [1]=endian | [2:6]=srid | [6:38]=MBR | [38]=0x7C (GAIA_MARK_MBR)
# | [39:43]=class(6) | [43:47]=nb_polygons | [47]=0x69 (writer quirk)
# | [48:52]=polygon class(3) | [52:56]=nb_rings | [56:60]=nb_points | points.
ENTITY_HEADER = 60


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_tile_multipolygon(blob: bytes) -> str:
    """Parse one Entity.geom GAIA blob into hex EWKB (PostGIS dialect,
    nested byte-order marks included). All tiles in this release are
    single-polygon, single-ring MULTIPOLYGONs in EPSG:4326."""
    if blob[0] != 0x00 or blob[-1] != 0xFE:
        raise ValueError("not a GAIA blob (missing 0x00/0xFE marks)")
    endian = "<" if blob[1] == 1 else ">"
    srid = struct.unpack_from(endian + "i", blob, 2)[0]
    if srid != 4326:
        raise ValueError(f"unexpected SRID {srid}, expected 4326")
    if blob[38] != 0x7C:
        raise ValueError(f"unexpected MBR mark {blob[38]:#x}, expected 0x7C")
    geom_class = struct.unpack_from(endian + "i", blob, 39)[0]
    nb_polygons = struct.unpack_from(endian + "i", blob, 43)[0]
    if blob[47] != 0x69:
        raise ValueError(f"unexpected writer byte {blob[47]:#x}, expected 0x69")
    polygon_class = struct.unpack_from(endian + "i", blob, 48)[0]
    nb_rings = struct.unpack_from(endian + "i", blob, 52)[0]
    nb_points = struct.unpack_from(endian + "i", blob, 56)[0]
    if geom_class != GAIA_MULTIPOLYGON or polygon_class != GAIA_POLYGON:
        raise ValueError(
            f"unexpected classes {geom_class}/{polygon_class}, expected 6/3"
        )
    if nb_polygons != 1 or nb_rings != 1:
        raise ValueError(
            f"tile with {nb_polygons} polygons / {nb_rings} rings not supported"
        )
    if len(blob) != ENTITY_HEADER + 16 * nb_points + 1:
        raise ValueError(f"blob length {len(blob)} != 61 + 16 * {nb_points}")

    out = bytearray(b"\x01")
    out += struct.pack("<I", 0x2000_0000 | GAIA_MULTIPOLYGON)
    out += struct.pack("<i", 4326)
    out += struct.pack("<I", nb_polygons)
    out += b"\x01" + struct.pack("<I", GAIA_POLYGON)
    out += struct.pack("<I", nb_rings)
    out += struct.pack("<I", nb_points)
    out += blob[ENTITY_HEADER : ENTITY_HEADER + 16 * nb_points]
    return out.hex()


def open_source(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise SystemExit(f"source not found: {path}")
    con = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = 1")
    return con


def read_source(path: Path) -> dict:
    """Read the SpatiaLite release: counts, per-taxonomy sums, grand total."""
    con = open_source(path)
    for table in ("Entity", "Taxonomy", "Asset"):
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not row:
            raise SystemExit(f"source {path} has no table {table!r}")

    counts = {
        table: con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        for table in ("Entity", "Taxonomy", "Asset")
    }
    log(
        f"source: Entity={counts['Entity']:,} Taxonomy={counts['Taxonomy']:,} "
        f"Asset={counts['Asset']:,}"
    )

    taxonomies = con.execute("SELECT id, taxonomy_string FROM Taxonomy ORDER BY id").fetchall()
    asset_id_by_taxonomy = {tid: i for i, (tid, _) in enumerate(taxonomies, start=1)}

    sums: dict[int, list[float]] = {}
    number_rows: list[list[float]] = [[] for _ in taxonomies]
    for taxonomy_id, number, structural, night in con.execute(
        "SELECT taxonomy_id, number, structural, night FROM Asset"
    ):
        buckets = sums.setdefault(taxonomy_id, [[], [], []])
        buckets[0].append(number)
        buckets[1].append(structural)
        buckets[2].append(night)
        number_rows[asset_id_by_taxonomy[taxonomy_id] - 1].append(number)
    per_taxonomy_raw = {
        tid: (math.fsum(b[0]), math.fsum(b[1]), math.fsum(b[2]))
        for tid, b in sorted(sums.items())
    }
    total_number = round(math.fsum(n for row in number_rows for n in row), 2)
    con.close()
    return {
        "counts": counts,
        "taxonomies": taxonomies,
        "asset_id_by_taxonomy": asset_id_by_taxonomy,
        "per_taxonomy_raw": per_taxonomy_raw,
        "total_number": total_number,
    }


def legacy_attributes_json(raw: tuple[float, float, float]) -> str:
    """assets.attributes JSON with SQL-round scale (2 decimals), matching the
    original conversion's round(x::numeric, 2) → jsonb output."""
    return (
        '{"legacy_2023_01": {"sum_number": %.2f, "sum_structural": %.2f, '
        '"sum_night": %.2f}}' % raw
    )


def iter_entities(path: Path, source_id: int):
    """Yield entity COPY rows: (id, quadkey, iso_3166, category, source_id,
    building_id, attributes, taxonomy, geometry-hex, geometry3d)."""
    con = open_source(path)
    for entity_id, quadkey, _osm_id, blob in con.execute(
        "SELECT id, quadkey, osm_id, geom FROM Entity ORDER BY id"
    ):
        yield (
            entity_id,
            quadkey,
            "NLD",
            0,
            source_id,
            None,
            None,
            None,
            parse_tile_multipolygon(blob),
            None,
        )
    con.close()


def iter_entity_assets(path: Path, asset_id_by_taxonomy: dict[int, int]):
    """Yield entity_assets COPY rows: (entity_id, asset_id, number, relative_size)."""
    con = open_source(path)
    for entity_id, taxonomy_id, number in con.execute(
        "SELECT entity_id, taxonomy_id, number FROM Asset ORDER BY entity_id, taxonomy_id"
    ):
        yield (entity_id, asset_id_by_taxonomy[taxonomy_id], number, 1)
    con.close()


def copy_rows(cur, sql: str, rows, what: str) -> int:
    n = 0
    with cur.copy(sql) as copy:
        for row in rows:
            copy.write_row(row)
            n += 1
            if n % 100_000 == 0:
                log(f"  {what}: {n:,}")
    log(f"  {what}: {n:,}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spatialite", type=Path, default=Path("data/NLD.The_Netherlands.db"))
    ap.add_argument("--dsn", default=DEFAULT_DSN, help="psycopg DSN (default: %(default)s)")
    ap.add_argument("--source-id", type=int, default=2,
                    help="exposure.sources id for the release row (original conversion used 2)")
    ap.add_argument("--truncate", action="store_true",
                    help="TRUNCATE the target tables first (required when non-empty)")
    ap.add_argument("--schema", default="exposure", help="target schema (default: %(default)s)")
    ap.add_argument("--dry-run", action="store_true", help="read the source only, write nothing")
    ap.add_argument("--no-verify", action="store_true", help="skip post-load verification")
    args = ap.parse_args()

    src = read_source(args.spatialite)
    if args.dry_run:
        log("dry-run: nothing written. per-taxonomy legacy sums:")
        for tid, raw in src["per_taxonomy_raw"].items():
            log(f"  taxonomy {tid}: {legacy_attributes_json(raw)}")
        log(f"grand total sum(number) = {src['total_number']:,.2f} (expect 11,320,734.17)")
        return 0

    import psycopg

    with psycopg.connect(args.dsn) as conn:
        with conn.transaction():
            cur = conn.cursor()
            tables = [
                f"{args.schema}.entity_assets",
                f"{args.schema}.district_assets",
                f"{args.schema}.assets",
                f"{args.schema}.taxonomies",
                f"{args.schema}.entities",
                f"{args.schema}.metadata",
                "sources.boundaries",
                f"{args.schema}.sources",
            ]
            if args.truncate:
                cur.execute(f"TRUNCATE {', '.join(tables)} CASCADE")
                log("target truncated")

            def count(table: str) -> int:
                return cur.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

            nonempty = [t for t in tables if count(t)]
            if nonempty:
                raise SystemExit(
                    f"target tables not empty: {', '.join(nonempty)} — rerun with --truncate"
                )

            # Documented deviation 1: the 2023.01 quadkeys have length 15-18.
            cur.execute(
                f"ALTER TABLE {args.schema}.entities "
                "DROP CONSTRAINT IF EXISTS entities_quadkey_check"
            )
            cur.execute(
                "SET LOCAL work_mem = '512MB'"
            )

            cur.execute(
                f"INSERT INTO {args.schema}.sources (id, name, uri, publication_date) "
                "VALUES (%s, %s, %s, %s)",
                (args.source_id, SOURCE_NAME, SOURCE_DOI, datetime(2023, 1, 1)),
            )
            tax_rows = [
                (tid, 1, json.dumps(tax_string), None)
                for tid, tax_string in src["taxonomies"]
            ]
            copy_rows(
                cur,
                f"COPY {args.schema}.taxonomies (id, category, taxonomy, attributes) FROM STDIN",
                tax_rows,
                "taxonomies",
            )

            log("entities: parsing GAIA blobs → hex EWKB")
            copy_rows(
                cur,
                f"COPY {args.schema}.entities "
                "(id, quadkey, iso_3166, category, source_id, building_id, "
                "attributes, taxonomy, geometry, geometry3d) FROM STDIN",
                iter_entities(args.spatialite, args.source_id),
                "entities",
            )

            asset_rows = [
                (
                    asset_id,
                    "NLD",
                    tid,
                    None,
                    None,
                    legacy_attributes_json(src["per_taxonomy_raw"][tid]),
                    None,
                )
                for asset_id, (tid, _) in enumerate(src["taxonomies"], start=1)
            ]
            copy_rows(
                cur,
                f"COPY {args.schema}.assets "
                "(id, iso_3166, taxonomy_id, tabula_taxonomy_id, "
                "average_net_floor_area, attributes, baseline_attributes) FROM STDIN",
                asset_rows,
                "assets",
            )

            copy_rows(
                cur,
                f"COPY {args.schema}.entity_assets "
                "(entity_id, asset_id, number, relative_size) FROM STDIN",
                iter_entity_assets(args.spatialite, src["asset_id_by_taxonomy"]),
                "entity_assets",
            )

            # boundaries first: district_assets.boundary_id carries a FK to
            # sources.boundaries(id) (added at the end of sql/00002).
            cur.execute(
                "INSERT INTO sources.boundaries (id, total_builtup_area, attributes, geometry) "
                "SELECT 'NLD', NULL, %s::jsonb, "
                f"ST_UnaryUnion(ST_Collect(geometry)) FROM {args.schema}.entities",
                (json.dumps({"note": BOUNDARY_NOTE}),),
            )
            log("boundaries: 'NLD' = ST_UnaryUnion(ST_Collect(entities.geometry))")

            district_rows = [
                # unrounded double-precision sum; the REAL column casts to float4
                # exactly like the original conversion (e.g. 58889.202… → 58889.203)
                (asset_id, "NLD", src["per_taxonomy_raw"][tid][0])
                for asset_id, (tid, _) in enumerate(src["taxonomies"], start=1)
            ]
            copy_rows(
                cur,
                f"COPY {args.schema}.district_assets (asset_id, boundary_id, number) FROM STDIN",
                district_rows,
                "district_assets",
            )

            conversion_date = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            metadata_rows = [
                ("conversion_date", conversion_date, "date of SpatiaLite to PostGIS conversion"),
                ("converted_from", "GDE release 2023.01 SpatiaLite (NLD.The_Netherlands.db)",
                 "source of converted rows"),
                ("license", "see data_licenses table of source release",
                 "source release licensing terms"),
                ("schema_deviation",
                 "entities_quadkey_check dropped: source model uses quadkeys of length 15-18, "
                 "official schema assumes 18",
                 "re-add when importing official EU Building Database dumps"),
                ("source_doi", SOURCE_DOI, "publication of source release"),
            ]
            copy_rows(
                cur,
                f"COPY {args.schema}.metadata (tag_key, tag_value, tag_comment) FROM STDIN",
                metadata_rows,
                "metadata",
            )
            log("committing…")

        if args.no_verify:
            log("verification skipped (--no-verify)")
            return 0

        log("verifying against source…")
        cur = conn.cursor()
        loaded = {
            t: count(t)
            for t in (
                f"{args.schema}.entities",
                f"{args.schema}.taxonomies",
                f"{args.schema}.assets",
                f"{args.schema}.entity_assets",
                f"{args.schema}.district_assets",
                "sources.boundaries",
            )
        }
        checks = [
            ("exposure.entities",
             loaded[f"{args.schema}.entities"] == src["counts"]["Entity"],
             f"{loaded[f'{args.schema}.entities']:,} == {src['counts']['Entity']:,}"),
            ("exposure.taxonomies",
             loaded[f"{args.schema}.taxonomies"] == src["counts"]["Taxonomy"],
             f"{loaded[f'{args.schema}.taxonomies']:,} == {src['counts']['Taxonomy']:,}"),
            ("exposure.assets",
             loaded[f"{args.schema}.assets"] == len(src["taxonomies"]),
             f"{loaded[f'{args.schema}.assets']:,} == {len(src['taxonomies']):,}"),
            ("exposure.entity_assets",
             loaded[f"{args.schema}.entity_assets"] == src["counts"]["Asset"],
             f"{loaded[f'{args.schema}.entity_assets']:,} == {src['counts']['Asset']:,}"),
            ("exposure.district_assets",
             loaded[f"{args.schema}.district_assets"] == len(src["taxonomies"]),
             f"{loaded[f'{args.schema}.district_assets']:,} == {len(src['taxonomies']):,}"),
            ("sources.boundaries", loaded["sources.boundaries"] == 1, "1 == 1"),
        ]
        cur.execute(f"SELECT sum(number::double precision) FROM {args.schema}.entity_assets")
        loaded_total = round(cur.fetchone()[0], 2)
        checks.append((
            "sum(number::double precision)",
            abs(loaded_total - src["total_number"]) < 0.005,
            f"{loaded_total:,.2f} == {src['total_number']:,.2f}",
        ))
        cur.execute("SELECT ST_NPoints(geometry), ST_IsValid(geometry) FROM sources.boundaries")
        npoints, valid = cur.fetchone()
        checks.append(("sources.boundaries geometry", valid and npoints > 0, f"{npoints:,} points"))

        ok = True
        for name, passed, detail in checks:
            log(f"  {'PASS' if passed else 'FAIL'}  {name}: {detail}")
            ok &= passed
        log(f"conversion {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
