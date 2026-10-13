# Scenario report — SR-20261004T185116Z-water-20261013T142955Z

- baseline run: `20261004T185116Z-water` · scenario set: `SSET-water-utrecht-uitdagingen`
- control (unmutated re-execution): **1,554.906 km²** (baseline run recorded 1,554.906 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WA-OVERSTROOMBAAR-HARD** Overstroombaar gebied treated as hard exclusion | policy variant (NC-WA-03) | FR-WA-03: set_semantics→exclusion | 352.846 | -1,202.061 (-77.31%) | 0.226924 | ok |
| **SC-WA-VRIJWARING-HARD** Vrijwaringszone regionale waterkering treated as hard exclusion | policy variant (NC-WA-01) | FR-WA-01: set_semantics→exclusion | 1,526.895 | -28.011 (-1.80%) | 0.981985 | ok |
| **SC-WA-WATERBERGING-BUFFER-500** Waterbergingsgebied exclusion widened by a 500 m band | norm variance (NC-WA-02) | FR-WA-02: set_buffer_distance_m→500m | 1,535.040 | -19.866 (-1.28%) | 0.987224 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
