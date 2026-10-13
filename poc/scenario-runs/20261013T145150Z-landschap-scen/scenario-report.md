# Scenario report — SR-20261005T070621Z-landschap-20261013T145150Z

- baseline run: `20261005T070621Z-landschap` · scenario set: `SSET-landschap-utrecht-uitdagingen`
- control (unmutated re-execution): **1,425.959 km²** (baseline run recorded 1,425.959 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LS-CHS-HARD** Cultuurhistorische hoofdstructuur treated as hard exclusion | policy variant (NC-LS-04) | FR-LS-04: set_semantics→exclusion | 645.265 | -780.694 (-54.75%) | 0.452513 | ok |
| **SC-LS-AARDKUNDIG-HARD** Aardkundige waarden treated as hard exclusion | policy variant (NC-LS-06) | FR-LS-06: set_semantics→exclusion | 1,342.005 | -83.953 (-5.89%) | 0.941125 | ok |
| **SC-LS-LIMES-BUFFER-100** Limes kernzone exclusion widened by a 100 m band | norm variance (NC-LS-02) | FR-LS-02: set_buffer_distance_m→100m | 1,425.833 | -0.126 (-0.01%) | 0.999912 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
