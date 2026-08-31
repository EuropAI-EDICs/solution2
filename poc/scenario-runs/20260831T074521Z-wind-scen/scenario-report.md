# Scenario report — SR-20260830T113234Z-wind-20260831T074521Z

- baseline run: `20260830T113234Z-wind` · scenario set: `SSET-wind-utrecht-poc1`
- control (unmutated re-execution): **859.463 km²** (baseline run recorded 859.463 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-W-NNN-EXCEPTION** art. 6.3 lid 2 exception granted province-wide | policy variant (NC-W-14) | FR-W-14: drop | 1,181.982 | +322.519 (+37.53%) | 0.727136 | ok |
| **SC-W-STILTE-HARD** Stiltegebieden treated as hard exclusion | policy variant (NC-W-12) | FR-W-12: set_semantics→exclusion | 716.241 | -143.221 (-16.66%) | 0.833359 | ok |
| **SC-W-AANDACHT-500** Aandachtsgebied stiltegebied enforced as 500 m exclusion | norm variance (NC-W-10) | FR-W-10: set_semantics→exclusion; FR-W-10: set_buffer_distance_m→500m | 644.506 | -214.956 (-25.01%) | 0.749895 | ok |
| **SC-W-AANDACHT-1500** Aandachtsgebied stiltegebied enforced as 1500 m exclusion | policy variant (NC-W-10) | FR-W-10: set_semantics→exclusion; FR-W-10: set_buffer_distance_m→1500m | 525.500 | -333.963 (-38.86%) | 0.611428 | ok |
| **SC-W-AANDACHT-3000** Aandachtsgebied stiltegebied enforced as 3000 m exclusion | norm variance (NC-W-10) | FR-W-10: set_semantics→exclusion; FR-W-10: set_buffer_distance_m→3000m | 333.712 | -525.751 (-61.17%) | 0.388279 | ok |
| **SC-W-NATURA-SETBACK** 500 m setback around Natura 2000 / ganzenrustgebieden | hypothetical — *not legally grounded* | FR-W-08: set_buffer_distance_m→500m | 812.541 | -46.922 (-5.46%) | 0.945405 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
