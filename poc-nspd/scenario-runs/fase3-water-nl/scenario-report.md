# Scenario report — SR-20261016T144620Z-water-nl-20261017T063351Z

- baseline run: `20261016T144620Z-water-nl` · scenario set: `SSET-water-nl-nspd-fase3`
- control (unmutated re-execution): **997.288 km²** (baseline run recorded 997.288 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WAT-NL-KERING-BUF250** Keringsexclusie verbreed met 250 m (NL) | norm variance (NC-WAT-03) | FR-WAT-03: set_buffer_distance_m→250m | 966.961 | -30.326 (-3.04%) | 0.969590 | ok |
| **SC-WAT-NL-KERING-DROP** Keringsexclusie losgelaten (NL) | policy variant (NC-WAT-03) | FR-WAT-03: drop | 1,000.606 | +3.319 (+0.33%) | 0.996682 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
