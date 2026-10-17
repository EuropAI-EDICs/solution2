# Scenario report — SR-20261016T151056Z-recreatie-nl-20261017T063352Z

- baseline run: `20261016T151056Z-recreatie-nl` · scenario set: `SSET-recreatie-nl-nspd-fase3`
- control (unmutated re-execution): **15.883 km²** (baseline run recorded 15.883 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-REC-NL-BADPLAATSEN-DROP** Badplaatsenbeleid losgelaten (NL) | policy variant (NC-REC-01) | FR-REC-01: drop | 1,000.606 | +984.724 (+6199.96%) | 0.015873 | ok |
| **SC-REC-NL-BADPLAATSEN-BUF500** Badplaatsen verbreed met 500 m (NL) | norm variance (NC-REC-01) | FR-REC-01: set_buffer_distance_m→500m | 30.577 | +14.694 (+92.52%) | 0.519433 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
