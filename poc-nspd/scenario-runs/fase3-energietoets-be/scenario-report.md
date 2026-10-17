# Scenario report — SR-20261016T150839Z-energietoets-be-20261017T063548Z

- baseline run: `20261016T150839Z-energietoets-be` · scenario set: `SSET-energietoets-be-nspd-fase3`
- control (unmutated re-execution): **0.137 km²** (baseline run recorded 0.137 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-BEE-BE-ONDERSTEUNEND-DROP** Zeehavenondersteunende zone losgelaten (BE) | policy variant (NC-BEE-01) | FR-BEE-01: drop | 535.986 | +535.849 (+391023.08%) | 0.000256 | ok |
| **SC-BEE-BE-PAPIER-DROP** Papierzone-exclusie voor energieopslag losgelaten (BE) | policy variant (NC-BEE-03) | FR-BEE-03: drop | 0.137 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-BEE-BE-ONDERSTEUNEND-BUF500** Zeehavenondersteunende zone verbreed met 500 m (BE) | norm variance (NC-BEE-01) | FR-BEE-01: set_buffer_distance_m→500m | 2.970 | +2.833 (+2067.19%) | 0.046146 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
