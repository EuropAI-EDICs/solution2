# Scenario report — SR-20261016T150835Z-wonen-be-20261017T063358Z

- baseline run: `20261016T150835Z-wonen-be` · scenario set: `SSET-wonen-be-nspd-fase3`
- control (unmutated re-execution): **0.005 km²** (baseline run recorded 0.005 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WON-BE-WOONGEBIED-DROP** Woongebied losgelaten (BE) | policy variant (NC-WON-01) | FR-WON-01: drop | 536.017 | +536.012 (+10400662.32%) | 0.000010 | ok |
| **SC-WON-BE-WOONGEBIED-BUF250** Woongebied verbreed met 250 m (BE) | norm variance (NC-WON-01) | FR-WON-01: set_buffer_distance_m→250m | 0.187 | +0.182 (+3523.18%) | 0.027604 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
