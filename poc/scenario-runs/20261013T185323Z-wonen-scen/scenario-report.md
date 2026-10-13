# Scenario report — SR-20261005T100258Z-wonen-20261013T185323Z

- baseline run: `20261005T100258Z-wonen` · scenario set: `SSET-wonen-utrecht-uitdagingen`
- control (unmutated re-execution): **1,142.990 km²** (baseline run recorded 1,142.990 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WN-ALLEEN-STEDELIJK** Housing only within existing urban area | policy variant (NC-WN-01) | FR-WN-04: drop; FR-WN-07: drop; FR-WN-08: drop; FR-WN-09: drop | 314.242 | -828.748 (-72.51%) | 0.274929 | ok |
| **SC-WN-FLEXWONINGEN-DICHT** Flexwoningen route closed | policy variant (NC-WN-08) | FR-WN-08: drop | 1,142.990 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-WN-STILTE-1KM** Stiltegebied protection widened: markers hard, attention at 1 km | hypothetical — *not legally grounded* | FR-WN-11: set_semantics→exclusion; FR-WN-12: set_semantics→exclusion; FR-WN-12: set_buffer_distance_m→1000m | 918.938 | -224.052 (-19.60%) | 0.803978 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
