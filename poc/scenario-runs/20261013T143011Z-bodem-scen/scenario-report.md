# Scenario report — SR-20261004T185509Z-bodem-20261013T143011Z

- baseline run: `20261004T185509Z-bodem` · scenario set: `SSET-bodem-utrecht-uitdagingen`
- control (unmutated re-execution): **858.927 km²** (baseline run recorded 858.927 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-BO-ALLEEN-REKENING-HOUDEN** Groundwater-protection umbrella enforced only as 'rekening houden met' | policy variant (NC-BO-04) | FR-BO-01: drop; FR-BO-03: drop | 1,560.054 | +701.126 (+81.63%) | 0.550575 | ok |
| **SC-BO-STORTPLAATS-HARD** Gesloten stortplaats treated as hard exclusion | policy variant (NC-BO-05) | FR-BO-05: set_semantics→exclusion | 858.555 | -0.373 (-0.04%) | 0.999566 | ok |
| **SC-BO-GWB-BUFFER-500** Grondwaterbeschermingszone exclusion widened by a 500 m band | norm variance (NC-BO-01) | FR-BO-01: set_buffer_distance_m→500m | 596.705 | -262.222 (-30.53%) | 0.694710 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
