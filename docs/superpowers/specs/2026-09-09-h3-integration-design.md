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
- **Join/KNN:** points → containing cells; KNN via `grid_distance` rings with haversine tie-break; neighborhood rings via `grid_disk` (notebook §II.3–II.4).
- **Hierarchy:** parent/children traversal (`cell_to_parent` / `cell_to_children`) for cross-resolution drill-down (notebook §I.2).
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
- **BAG join:** building footprints → centroids → `h3-spatial-join-points` against zone cells (buildings per cell inside/near each track's zone). Data: local GeoJSON buildings input (the registry holds no buildings source today — rijnsweerd-style fixtures and any `--buildings` GeoJSON file; a registry fetch is future work when an ArcGIS-compatible BAG service is configured).
- **Reports/simulation:** hex choropleth as a single-file offline **Leaflet hex map** (`h3-crosstrack.html`) emitted by the crosstrack run, in the same Leaflet idiom as the run reports — no deck.gl, no new CDN dependencies. (Simulation-viewer hex panels and the jinja report-template block are follow-ups once hex artifacts exist.)

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

## 7. Worked examples for the PoCs

Each example shows the process chain, the PoC inputs it consumes, and the planning question it answers. All are deterministic replays over cached process responses.

### 7.1 Groene contour conflict heatmap (crosstrack, zon × bos)

**Question:** *Where* inside the Groene contour (zoekgebied nieuwe natuur, art. 6.4 CVDR704250) does the zonnevelden conflict concentrate — the 94.7% headline says how much, not where.

- **Inputs:** bos-track `zones.json` (Groene contour polygon) + zon-track open-result polygon from the canonical runs.
- **Chain:** `h3-polygon-to-cells` on both (res 8) → per-cell conflict fraction = coverage(zon-open ∩ cell) for cells in the contour → `h3-cells-to-geojson` for the report layer.
- **Output:** `h3-crosstrack.json`, one record per cell:

```json
{
  "cell": "882a100dd3fffff",
  "resolution": 8,
  "in_groene_contour": true,
  "conflict_fraction": 0.83,
  "zon_open_fraction": 0.91,
  "compact_group": "882a100dffffffff"
}
```

- **Use:** Leaflet choropleth in the crosstrack report; compact the high-conflict cells (`compact_cells`) to name the largest contiguous conflict areas; the conflict-free ~5% of cells become the "where can bos still proceed unopposed" shortlist.

### 7.2 BAG buildings per track zone (exposure screening)

**Question:** How many buildings lie inside or near each track's zone — where is the participation/objection pressure (zinhebbenden under Omgevingswet) highest?

- **Inputs:** BAG footprint centroids (registry fetch + cache) + each track's zone cells.
- **Chain:** `h3-spatial-join-points` → per-cell building counts; `h3-knn` for a single building ("which zone cells are nearest to this address").
- **Use:** per-track building-density maps; cells with high counts flag areas where a zoekgebied is unlikely to survive participation. Feeds PoC-1 reports and the simulation KG panels as a new layer.

### 7.3 Scenario spatial-structure comparison (Moran's I)

**Question:** Does a policy variant fragment or consolidate a track's zone? Polygon area alone can't tell a compact from a scattered zone of equal size.

- **Inputs:** baseline + variant zone outputs from `poc/pipeline/scenarios.py` (e.g. `set_buffer_distance_m` on a wind exclusion).
- **Chain:** `h3-polygon-to-cells` per variant → coverage vectors → `h3-morans-i` per variant → per-cell delta map vs baseline.
- **Use:** Moran's I next to area in the scenario comparison table (clustered ≈ +1, scattered ≈ 0); per-cell flip map (open→closed / closed→open) shows *where* the mutation bites. Deterministic author and LLM author (S7/S8) scenarios get the same metrics — no seam changes.

### 7.4 Cross-resolution drill-down (hierarchy)

**Question:** Province overview first, parcel-level detail where it matters.

- **Chain:** res-8 conflict cells (§7.1) → `cell_to_children` at res 9 only for the top-N conflicted cells; keep res-8 `compact_cells` output as the compact store.
- **Use:** interactive drill-down in the report (res 8 everywhere, res 9 inset for hotspots); artifact stays small — compacted res-8 set plus targeted res-9 children, never a full res-9 provincial grid.

### 7.5 Wind search-area proximity rings (KNN)

**Question:** Which buildings fall within screening distance of the wind zoekgebied, banded by ring?

- **Inputs:** wind-track zone cells + BAG centroids.
- **Chain:** zone cells → `grid_disk` rings k = 1…3 around the zone boundary cells → `h3-spatial-join-points` per ring.
- **Use:** distance-band building counts per ring (~cell-size steps) as an early screening table before exact 28992 metric distancing runs; pentagon-cell flags recorded where rings are asymmetric.

### 7.6 Recipe form (nldt side)

The same patterns packaged for agents — `recipes/hex-overlay-analysis.json` applied to the Utrecht AOI: `fetch-features` (AOI layer) → `h3-polygon-to-cells` → `h3-spatial-join-points` (BAG) → `h3-morans-i` — returning one validated, PROV'd artifact set that the LangGraph orchestrator can explain step by step.

## 8. Out of scope

- TensorFlow/hex-convolution classifier (notebook §IV.4) — GenAI/ML stays behind seams per architecture.
- H3 path/corridor analysis (`grid_path`) for ecological connectivity between nature areas — natural future extension of the kernel, not needed by the integration points above.
- deck.gl visualization (future option for `context3d`).
- PostGIS/H3 SQL indexing, Placekey, non-NL CRS support.
- Changes to `ScenarioSpec`, zone algebra semantics, or the authoritative polygon-based results.
