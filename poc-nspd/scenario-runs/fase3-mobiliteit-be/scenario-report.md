# Scenario report — SR-20261016T150842Z-mobiliteit-be-20261017T063359Z

- baseline run: `20261016T150842Z-mobiliteit-be` · scenario set: `SSET-mobiliteit-be-nspd-fase3`
- control (unmutated re-execution): **0.090 km²** (baseline run recorded 0.090 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-MOB-BE-WEGEN-DROP** Wegeninfra-zone losgelaten (BE) | policy variant (NC-MOB-01) | FR-MOB-01: drop | 0.029 | -0.061 (-67.41%) | 0.325749 | ok |
| **SC-MOB-BE-WEGEN-BUF250** Wegeninfra-zone verbreed met 250 m (BE) | norm variance (NC-MOB-01) | FR-MOB-01: set_buffer_distance_m→250m | 0.994 | +0.904 (+999.38%) | 0.091002 | ok |
| **SC-MOB-BE-ONTS-DROP** Havenontsluitingsweg losgelaten (BE) | policy variant (NC-MOB-02) | FR-MOB-02: drop | 0.061 | -0.029 (-32.59%) | 0.674251 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
