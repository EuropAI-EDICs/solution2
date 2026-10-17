# Scenario report — SR-20261016T150833Z-wind-be-20261016T152124Z

- baseline run: `20261016T150833Z-wind-be` · scenario set: `SSET-wind-be-nspd-fase3`
- control (unmutated re-execution): **1.171 km²** (baseline run recorded 1.171 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WIND-BE-BOSKOPPEL-DROP** Turbine-rij in het boskoppelingsgebied losgelaten (BE) | policy variant (NC-BEW-01) | FR-BEW-01: drop | 536.000 | +534.829 (+45682.79%) | 0.002184 | ok |
| **SC-WIND-BE-GRENS-DROP** Grensgebied-exclusie losgelaten (BE) | policy variant (NC-BEW-02) | FR-BEW-02: drop | 1.171 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-WIND-BE-BOSKOPPEL-BUF500** Turbine-rij-zone verbreed met 500 m (BE) | norm variance (NC-BEW-01) | FR-BEW-01: set_buffer_distance_m→500m | 16.565 | +15.394 (+1314.90%) | 0.070677 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
