# Scenario report — SR-20261006T171730Z-energietoets-20261013T182039Z

- baseline run: `20261006T171730Z-energietoets` · scenario set: `SSET-energietoets-utrecht-uitdagingen`
- control (unmutated re-execution): **1,560.054 km²** (baseline run recorded 1,560.054 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **fail** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-ET-TOETS-HARD** Art. 5.10 scope executed as spatial blockage | policy variant (NC-ET-01) | FR-ET-01: set_semantics→exclusion | 0.000 | -1,560.054 (-100.00%) | 0.000000 | ok |
| **SC-ET-GEEN-MOTIVATIE** Art. 5.11 motivation duty dropped | policy variant (NC-ET-03) | FR-ET-03: drop | 1,560.054 | +0.000 (+0.00%) | 1.000000 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
