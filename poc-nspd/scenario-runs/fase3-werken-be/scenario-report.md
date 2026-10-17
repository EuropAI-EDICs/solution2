# Scenario report — SR-20261016T150837Z-werken-be-20261017T063358Z

- baseline run: `20261016T150837Z-werken-be` · scenario set: `SSET-werken-be-nspd-fase3`
- control (unmutated re-execution): **0.412 km²** (baseline run recorded 0.412 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WER-BE-ZEEHAVEN-DROP** Zeehavenbedrijven-zone losgelaten (BE) | policy variant (NC-WER-01) | FR-WER-01: drop | 0.031 | -0.381 (-92.58%) | 0.074194 | ok |
| **SC-WER-BE-PAPIER-DROP** Papierproducent-zone losgelaten (BE) | policy variant (NC-WER-02) | FR-WER-02: drop | 0.381 | -0.031 (-7.42%) | 0.925806 | ok |
| **SC-WER-BE-ZEEHAVEN-BUF500** Zeehavenbedrijven-zone verbreed met 500 m (BE) | norm variance (NC-WER-01) | FR-WER-01: set_buffer_distance_m→500m | 3.417 | +3.005 (+729.88%) | 0.120496 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
