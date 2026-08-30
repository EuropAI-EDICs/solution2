# EU Building Database — local setup (Postgres.app, PostgreSQL 18)

Setup performed on 2026-08-29 following
`ldt_toolbox_d03_06_eu_ldt_installation_manual_eu_building_database.v3.pdf`,
adapted from Ubuntu to macOS using Postgres.app (PostgreSQL 18.6 with bundled
PostGIS) on localhost:5432.

## What was done

1. **Server**: Postgres.app (PostgreSQL 18.6), port 5432. The Homebrew
   `postgresql@18` service was stopped to keep port 5432 free.
2. **Database**: `exposure` (UTF8) created as superuser `marc`.
3. **Roles** (manual §2.3): login roles `consumer` (read-only) and
   `contributor` (read-write), inheriting from group roles `read_only` /
   `read_write`. Passwords are stored in `~/.pgpass` (entries for
   `localhost:5432` as `consumer` and `contributor`).
4. **Extensions** (manual §2.4): `postgis` and `postgis_sfcgal` enabled in the
   `exposure` database.
5. **Schema import** (manual §2.5): the official EU Building Database release
   dumps are not publicly downloadable (see "Pending" below). As an
   authoritative stand-in for the schema dump, the migrations of the GDE
   `database-exposure` repository (branch `v25.01`) were imported, in order:
   - `sql/00000_prepare_database.sql` — schemas, privileges, role search paths
   - `sql/00001_create_initial_structure_exposure.sql` — `exposure` schema:
     `entities`, `entity_assets`, `assets`, `taxonomies`, `sources`,
     `district_assets`, `metadata`
   - `sql/00002_create_initial_structure_source.sql` — `sources` schema:
     `google_buildings`, `microsoft_buildings`, `boundaries`, `ghsl_*`,
     `tabula`, `oceans_seas`
6. **Post-import grants** (manual §2.5.2) applied.

## Data import: converted from public SpatiaLite release (2023-08-29)

The official data dump (`data.sql`) ships with an EU Building Database release
and is not published online (request via the LDT Toolbox portal,
info@ldttoolbox.eu). To have data to explore in the meantime, the public GDE
release 2023.01 (https://doi.org/10.5880/GFZ.2.6.2023.011) was converted for
the Netherlands into the official schema.

**Source**: `data/NLD.The_Netherlands.db` (449 MB, untracked — see
`.gitignore`). The 2023.01 model differs from the current exposure model: it
has `Entity` (all 329,437 rows are residual tiles, mixed zoom 15–18),
`Taxonomy` (37 GEM taxonomy strings), and `Asset` (6.47M entity–taxonomy
exposure pairs). `Building`, `Tile`, `AssetCountry`, `Metadata` are empty in
this release.

**Mapping applied**:

| Target | Source | Notes |
| --- | --- | --- |
| `exposure.sources` | — | one row documenting the release (DOI, name) |
| `exposure.entities` | `Entity` | ids + geometry preserved, `category=0`, `iso_3166='NLD'` |
| `exposure.taxonomies` | `Taxonomy` | ids preserved, `taxonomy` = JSON string of `taxonomy_string`, `category=1` |
| `exposure.assets` | one per taxonomy | synthesized for `'NLD'`; `attributes.legacy_2023_01` keeps per-taxonomy sums of `number`/`structural`/`night` |
| `exposure.entity_assets` | `Asset` | `number` preserved, `relative_size=1` |
| `exposure.district_assets` | `Asset` aggregated | one row per taxonomy for boundary `NLD` |
| `sources.boundaries` | union of tiles | `NLD` = union of converted tile geometries (model coverage, not exact outline) |
| `exposure.metadata` | — | provenance keys (`converted_from`, `source_doi`, `schema_deviation`, …) |

**Verified**: row counts match the source exactly (329,437 / 37 / 6,471,084);
`sum(number::double precision)` = 11,320,734.17, identical to the source sum;
consumer (read-only) can run spatial queries.

### Known deviations from the official schema

1. **`entities_quadkey_check` dropped** — the official schema requires
   18-character (zoom 18) quadkeys; the 2023.01 model uses zooms 15–18, and
   46% of the exposure sits in tiles below zoom 18, which cannot be
   losslessly promoted. Re-add the constraint when importing official dumps:
   ```sql
   ALTER TABLE exposure.entities ADD CONSTRAINT entities_quadkey_check
     CHECK (char_length(quadkey) = 18);
   ```
2. `entity_assets.number` is `REAL` (official DDL); sum it as
   `sum(number::double precision)` — plain `sum(number)` aggregates in float4
   and drifts ~0.5% over 6.5M rows.
3. Buildings (`category=1`) are absent by design of this release — it only
   contains the residual tile model.

## SpatiaLite copy: `data/exposure.db`

A SpatiaLite version of the converted data (manual §3: same structure as
PostGIS, table names unqualified) is exported from the `exposure` PostGIS
database to `data/exposure.db` (238 MB, untracked). Tables: `entities`,
`boundaries` (both MULTIPOLYGON, SRID 4326, with R*Tree spatial indexes),
`entity_assets`, `assets`, `taxonomies`, `sources`, `district_assets`,
`metadata`. `entities.geometry3d` is omitted (NULL throughout this data).

Note: the Homebrew `gdal` is built **without** libspatialite and cannot write
SpatiaLite files; the export uses the ogr2ogr bundled with QGIS
(`/Applications/QGIS-final-4_2_1.app/Contents/MacOS/ogr2ogr`). Exporting
geometry layers standalone prints a harmless `Cannot find proj.db` warning —
the data and SRIDs are written correctly.

SpatiaLite function notes vs PostGIS: use `PtDistWithin` instead of
`ST_DWithin`, and `CAST(number AS REAL)` for precise sums. The file was
verified with libspatialite 5.1.0 (`mod_spatialite.dylib`): counts match
PostGIS, the Utrecht spot query returns identical results, and the total
exposure sum equals the source (11,320,734.17).

## 3D buildings viewer: `3d-viewer/`

The converted exposure data has no building geometries (residual tile model
only). For real Dutch 3D buildings, `3d-viewer/index.html` is a single-file
CesiumJS page that streams the **3D BAG** (TU Delft, CC-BY-4.0) nationwide
LoD2.2 3D Tiles — no download, no API key:

```sh
cd 3d-viewer && python3 -m http.server 8765
# open http://localhost:8765
```

Tileset source: `https://data.3dbag.nl/v20250903/cesium3dtiles/{lod12,lod13,lod22}/tileset.json`
(CORS open). A LoD selector is on-screen. QGIS ≥ 3.34 can add the same
tileset URL directly as a 3D Tiles Layer and view it in a 3D Map View.
Verified rendering LoD2.2 roof geometry over Utrecht Centraal.

### QGIS "Tiled Scene" notes (QGIS 4.2)

- QGIS 4 renamed the feature: **Browser panel → Tiled Scene → New Cesium 3D
  Tiles Connection** (no "Add 3D Tiles Layer" menu item).
- LoD2.2 may fail with tinygltf "Invalid byteLength" errors — some tiles
  exceed 2 MiB and QGIS's fetch/parse truncates them. The 3DBAG files
  themselves are valid (all 82 Utrecht tiles verified). Workarounds:
  - Use the lighter `lod13`/`lod12` tileset URLs (smaller tiles).
  - Use the local validated mirror (Utrecht subtree, 82 tiles, 98 MB):
    `http://localhost:8765/mirror/lod22/tileset.json` (requires the
    `3d-viewer` http.server; tiles outside Utrecht still load from origin).
  - Clear QGIS network cache (Settings → Options → Network) and retry.

## Pending: official data import (manual §2.5.1)

Once you obtain the official release files:

```sh
/Applications/Postgres.app/Contents/Versions/18/bin/psql -d exposure -f /path/to/data.sql
```

If the release also includes its own `schema.sql`, drop and recreate the
database first (manual §5, FAQ) so the official schema and data stay in sync:

```sh
psql -d postgres -c "DROP DATABASE exposure;" \
  -c "CREATE DATABASE exposure ENCODING 'UTF8';"
# then re-run steps 4-6 above and import schema.sql + data.sql
```

An alternative data source is the public 2023.01 SpatiaLite release at
https://doi.org/10.5880/GFZ.2.6.2023.011 (per-country `.db` files with the
same table structure), which could be converted to inserts.

## Connecting

| Field    | Value                                      |
| -------- | ------------------------------------------ |
| Host     | localhost                                  |
| Port     | 5432                                       |
| Database | exposure                                   |
| Read-only user  | consumer   (password in `~/.pgpass`) |
| Read-write user | contributor (password in `~/.pgpass`) |

QGIS: Layer → Add Layer → Add PostGIS Layers → New, using the values above
(manual §2.6).
