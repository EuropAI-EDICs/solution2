# H3 Methodology Integration — Design

**Date:** 2026-09-09
**Status:** Approved (brainstorming session)
**Reference:** https://h3geo.org/docs — Uber H3 hexagonal hierarchical geospatial index.
Example notebook studied: [uber/h3-py-notebooks `urban_analytics.ipynb`](https://github.com/uber/h3-py-notebooks/blob/master/notebooks/urban_analytics.ipynb) (Toulouse bus-stop analytics; h3-py v3 API — ported to v4 names here).

## 1. Context and goal

The repo's PoCs (`poc/`: wind/zon/bos tracks on Omgevingsverordening Utrecht; scenario plane; cross-track overlay) and the generic platform (`nldt/`: OGC API Processes/Records/Recipes, LangGraph orchestrator, MCP) are polygon-based (shapely, EPSG:28992 compute / EPSG:4326 output). There is no gridded index in use today (only quadkeys in the EU Building Database schema).

Goal: integrate the **full H3 methodology** — hex aggregation & conflict overlay, spatial joins & KNN (BAG buildings), spatial autocorrelation (Moran's I, no ML), and hex visualization — as a **deterministic reporting/aggregation layer over polygon zone truth**. The shapely zone algebra and its polygon-based results remain authoritative; H3 never replaces zone truth.

## 2. Architecture decision

**Approach C — H3 lives only in `nldt/` as OGC API Processes; the PoCs consume it as processes.** Single implementation, platform-building. The known risk (PoC offline replay determinism) is mitigated by a **cache-first process client** in `poc/` (§4): committed cache fixtures make PoC replays and unittest runs fully offline.

Rejected alternatives: parallel native implementations unified by contracts (duplication), and a shared top-level library (couples the deliberately self-contained surfaces; `poc/` has no install step).

Binding constraints (from SOLUTIONS_ARCHITECTURE / GENAI_SEAMS): deterministic and offline-capable by default; CRS discipline 28992-compute / 4326-output (H3 is WGS84-native → documented reprojection seam); schema validation at every hop (V0); PROV per operation; immutable hashed run artifacts; no new runtime network dependencies; library is h3-py **v4 API** (`polygon_to_cells`, `cell_to_boundary`, `grid_ring`, `grid_distance`, `compact_cells` — the notebook's v3 `polyfill`/`geo_to_h3`/`hex_ring` names are ported).

## 3. `nldt/` H3 process suite

### 3.1 Kernel — `nldt/services/common/h3kit.py`

Deterministic kernel on `h3` (v4) + existing shapely geo kernel:

- **Coverage:** polygon (GeoJSON, 4326) → cell set via `polygon_to_cells` (center-in-polygon semantics, i.e. the notebook's `polyfill` behavior) → per-cell **coverage fraction** = area(cell ∩ polygon) / area(cell), computed planar in EPSG:28992 (consistent with `services/common/geo.py`'s 28992 assumption). Input polygons `make_valid`-ed first with provenance recorded. Optional `compact` (notebook §III.3).
- **Join/KNN:** points → containing cells; KNN via `grid_distance` rings with haversine tie-break (notebook §II.3–II.4).
- **Autocorrelation:** global Moran's I from scratch over `grid_ring` neighborhoods + permutation significance test (notebook §IV.3). No PySAL, no TensorFlow.

### 3.2 Processes (in `process_adapter/handlers.py`, `backend: local`)

| Process id | Notebook section | Function |
|---|---|---|
| `h3-polygon-to-cells` | §II, III.3 | GeoJSON polygon(s) + resolution → cell set with coverage fractions (+ optional compact) |
| `h3-cells-to-geojson` | §III.2 | cell set → boundary GeoJSON (map layers) |
| `h3-spatial-join-points` | §II.4 | points + cell set/polygon → per-point cell IDs + per-cell counts |
| `h3-knn` | §II.3 | point + candidates + k → nearest by grid distance |
| `h3-morans-i` | §IV.3 | cell values → global Moran's I + permutation significance |

Resolution is an explicit input with default **res 8** (≈ 0.74 km² avg cell, province scale); res 9 (≈ 0.10 km²) for conflict detail. Resolution is always recorded in outputs.

### 3.3 Wiring

- Dependency: `h3>=4.1` in `nldt/requirements.txt`.
- Catalog seed records (`catalog_adapter/seed.py`); MCP exposure via `process_server.py`; orchestrator discovery — no agent code changes.
- Reference recipe `recipes/hex-overlay-analysis.json`: `fetch-features → h3-polygon-to-cells → h3-spatial-join-points → h3-morans-i`, mirroring `spatial-overlay-analysis.json`.
- PROV per operation (`common/prov.py`); JSON-Schema-validated inputs/outputs at every hop.
- Output contract schema: `nldt/schemas/h3coverage.schema.json` (draft 2020-12): cell IDs, resolution, coverage fractions, counts, Moran's I result.

## 4. `poc/` consumption — cache-first process client

New pipeline step `poc/pipeline/h3step.py`, the only bridge:

1. Check `poc/data/cache/h3/<sha256-of-inputs>.json` — hit ⇒ return (offline, deterministic replay; same pattern as the geodata dual-CRS cache).
2. Miss ⇒ invoke the nldt process via the existing CLI as a subprocess (`python3 nldt/services/cli.py`, JSON on stdin/out). No service running required; no Python-path coupling; the process boundary is the architecture. A `--refresh-h3` flag forces live re-invocation.
3. Response → cache + immutable hashed PROV'd artifact in the run directory (process id, h3 version, inputs hash, resolution).

All `poc/` unit tests run against committed cache fixtures — the existing offline test suite stays offline and green without `nldt/` or network.

### 4.1 Integration points (H3 as reporting layer over polygon truth)

- **Crosstrack:** after the existing overlay, discretize the Groene contour (zoekgebied nieuwe natuur) and the zon-open result → per-cell conflict fraction artifact `h3-crosstrack.json`. The canonical polygon-based headline (94.7%) stays authoritative; the hex layer shows *where* conflict concentrates.
- **Scenarios:** per-scenario hex coverage → per-cell delta vs baseline + Moran's I as spatial-structure comparison metric. `ScenarioSpec` unchanged (computed from existing zone outputs; S7/S8 seams unaffected).
- **BAG join:** building footprints → centroids → `h3-spatial-join-points` against zone cells (buildings per cell inside/near each track's zone). Provincial extract via the existing registry pattern (`data/sources.json` + cache); rijnsweerd fixture for tests.
- **Reports/simulation:** hex layers as GeoJSON cell boundaries through the **existing Leaflet** template with a choropleth ramp — no deck.gl, no new CDN dependencies; single-file offline report property preserved. (deck.gl `H3Hexagon` noted as a future `context3d` option.)

### 4.2 Contracts

The nldt `h3coverage.schema.json` is mirrored into `poc/schemas/` so both surfaces validate the same shape; H3 cell IDs become a new identifier type (quadkey precedent in the EU Building Database schema).

## 5. Error handling

- Invalid polygons → `make_valid` with provenance note (engine pattern).
- Unknown or mixed-resolution cell sets → schema rejection.
- Pentagon cells → handled by `grid_ring` neighborhoods; flagged in outputs.
- Empty cell sets (polygon below resolution) → valid, recorded outcome, not an error.

## 6. Testing

- `nldt/tests/test_h3_processes.py` (pytest): determinism (sorted cell sets); coverage-fraction invariants; Moran's I on synthetic grids (clustered ≈ +1, checkerboard ≈ −1, random ≈ 0); CRS-seam tolerance vs h3-py's own cell-area values; rijnsweerd join fixture.
- `poc/tests/test_h3step.py` + extensions to `test_crosstrack.py` / `test_scenarios.py` (unittest, fixtures only, offline).

## 7. Out of scope

- TensorFlow/hex-convolution classifier (notebook §IV.4) — GenAI/ML stays behind seams per architecture.
- deck.gl visualization (future option for `context3d`).
- PostGIS/H3 SQL indexing, Placekey, non-NL CRS support.
- Changes to `ScenarioSpec`, zone algebra semantics, or the authoritative polygon-based results.
