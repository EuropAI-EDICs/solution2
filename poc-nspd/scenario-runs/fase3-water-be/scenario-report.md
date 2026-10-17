# Scenario report — SR-20261016T150847Z-water-be-20261017T063351Z

- baseline run: `20261016T150847Z-water-be` · scenario set: `SSET-water-be-nspd-fase3`
- control (unmutated re-execution): **0.004 km²** (baseline run recorded 0.004 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WAT-BE-CAPTATIE-DROP** Watercaptatiezone losgelaten (BE) | policy variant (NC-WAT-01) | FR-WAT-01: drop | 536.017 | +536.013 (+14001685.46%) | 0.000007 | ok |
| **SC-WAT-BE-CAPTATIE-BUF500** Watercaptatiezone verbreed met 500 m (BE) | norm variance (NC-WAT-01) | FR-WAT-01: set_buffer_distance_m→500m | 0.494 | +0.490 (+12803.51%) | 0.007754 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
