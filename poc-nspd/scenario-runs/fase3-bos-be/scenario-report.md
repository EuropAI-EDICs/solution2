# Scenario report — SR-20261016T150831Z-bos-be-20261017T063359Z

- baseline run: `20261016T150831Z-bos-be` · scenario set: `SSET-bos-be-nspd-fase3`
- control (unmutated re-execution): **1.171 km²** (baseline run recorded 1.171 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-BOS-BE-BOSKOPPEL-DROP** Boskoppelingsgebied losgelaten (BE) | policy variant (NC-BOS-01) | FR-BOS-01: drop | 536.017 | +534.846 (+45684.27%) | 0.002184 | ok |
| **SC-BOS-BE-BOSKOPPEL-BUF500** Boskoppelingsgebied verbreed met 500 m (BE) | norm variance (NC-BOS-01) | FR-BOS-01: set_buffer_distance_m→500m | 16.565 | +15.394 (+1314.90%) | 0.070677 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
