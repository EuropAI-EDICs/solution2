# Scenario report — SR-20261016T150845Z-recreatie-be-20261017T063352Z

- baseline run: `20261016T150845Z-recreatie-be` · scenario set: `SSET-recreatie-be-nspd-fase3`
- control (unmutated re-execution): **0.003 km²** (baseline run recorded 0.003 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-REC-BE-RECGEB-DROP** Recreatiegebied losgelaten (BE) | policy variant (NC-REC-01) | FR-REC-01: drop | 536.017 | +536.014 (+19745663.30%) | 0.000005 | ok |
| **SC-REC-BE-RECGEB-BUF500** Recreatiegebied verbreed met 500 m (BE) | norm variance (NC-REC-01) | FR-REC-01: set_buffer_distance_m→500m | 0.891 | +0.888 (+32729.33%) | 0.003045 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
