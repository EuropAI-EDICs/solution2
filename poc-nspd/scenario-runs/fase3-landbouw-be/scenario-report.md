# Scenario report — SR-20261016T150844Z-landbouw-be-20261017T063358Z

- baseline run: `20261016T150844Z-landbouw-be` · scenario set: `SSET-landbouw-be-nspd-fase3`
- control (unmutated re-execution): **0.894 km²** (baseline run recorded 0.894 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LNB-BE-AGRKOPPEL-DROP** Agrarisch koppelingsgebied losgelaten (BE) | policy variant (NC-LNB-01) | FR-LNB-01: drop | 536.017 | +535.123 (+59832.34%) | 0.001669 | ok |
| **SC-LNB-BE-AGRKOPPEL-BUF500** Agrarisch koppelingsgebied verbreed met 500 m (BE) | norm variance (NC-LNB-01) | FR-LNB-01: set_buffer_distance_m→500m | 7.352 | +6.458 (+722.06%) | 0.121653 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
