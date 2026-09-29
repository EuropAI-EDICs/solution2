# Urban Strategy stiltegebied noise screening — Design

**Date:** 2026-09-29
**Status:** Approved (plan session; delivery B + consumer A)
**Reference:** https://doc.urbanstrategy.nl/ — Scenexus Urban Strategy RestAPI (OpenAPI 3.0, v0.6.4) and noise analytics (SRM-2).

## 1. Context and goal

PoC-1 Utrecht wind abstains from formalizing art. 9.26 stiltegebied LAeq,24h targets (FR-W-11 / NC-W-11) because applying dB thresholds to a location needs an acoustic model. Urban Strategy exposes a RestAPI over the DT store and noise models that produce per-receptor `L_AEQ` / `I_LDEN`.

Goal: integrate Urban Strategy as a **decision-support receptor exceedance screen** over stiltegebied GIO geometry — without changing zone algebra or the pipeline verdict. Offline by default via committed fixtures; live RestAPI behind env credentials.

## 2. Architecture decision

**Same as H3 architecture C:** single implementation in `nldt/` as OGC API Processes; `poc/` consumes via a cache-first process client (`pipeline/usstep.py`). No shared top-level library; no Python-path coupling — the process boundary is the architecture.

Rejected: embedding US SDK in `poc/` (breaks offline replay); installing a local US server for the PoC (out of scope).

Binding constraints: deterministic offline default; CRS 4326 I/O with planar EPSG:28992 point-in-polygon; JSON Schema draft 2020-12; PROV per job; no secrets in repo; US failures degrade, never flip the run verdict; FR-W-11 stays ambiguous (annex only).

## 3. `nldt/` components

### 3.1 Client — `services/common/urbanstrategy_client.py`

- `login(base_url, email, password) -> token`
- `get_bin_collections(base_url, token, bin_id) -> raw store payload`
- `normalize_receptors(raw_or_geojson) -> FeatureCollection` with properties `lAeq`, `iLden`
- `load_fixture(path_or_fixture_uri) -> FeatureCollection` (no network)
- Auth: `US_TOKEN` or `US_EMAIL`+`US_PASSWORD`; live only when `US_LIVE=1`

### 3.2 Kernel — `services/common/us_stiltegebied.py`

Pure function `evaluate(receptors, stille_kern, bufferzone, thresholds=(40, 45))`:
- Reproject points/polygons 4326→28992 for containment
- Classify each receptor: `stille_kern` | `bufferzone` | `outside` (kern wins if both)
- Exceedance when `lAeq > threshold` for that zone
- Return schema-shaped evaluation dict + exceedance FeatureCollection

### 3.3 Processes

| Process id | Function |
|---|---|
| `us-fetch-noise-receptors` | Live RestAPI or `fixture://` → normalized receptor FC |
| `us-stiltegebied-noise-eval` | receptors × stiltegebied polygons → evaluation artifact |

### 3.4 Schema

`nldt/schemas/us-stiltegebied-eval.schema.json` mirrored to `poc/schemas/`.

## 4. `poc/` consumption

`pipeline/usstep.py`: cache under `poc/data/cache/us/<sha256>.json`; `POC_US_OFFLINE=1` forbids subprocess/network. Wind track (after zone engine): write `urbanstrategy-stiltegebied.json`. Combined stiltegebied GIO is screened at the stricter 40 dB threshold when separate stille-kern/bufferzone layers are unavailable; caveat recorded.

Flags: `--skip-us` skips the step; failures append a degradation and continue.

## 5. Honest scope

Slice 1 screens an SRM-2 traffic/industry noise field inside stiltegebied. Turbine-source industry modelling is follow-up; caveats always state this. Legal FormalRules are not auto-rewritten.

## 6. Out of scope

US server install, IMB hub, QGIS connector, demand/traffic/air modules, auto-formalizing FR-W-11.
