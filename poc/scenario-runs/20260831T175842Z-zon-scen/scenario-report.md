# Scenario report — SR-20260830T142439Z-zon-20260831T175842Z

- baseline run: `20260830T142439Z-zon` · scenario set: `SSET-llm-qwen3.8:latest`
- control (unmutated re-execution): **1,167.936 km²** (baseline run recorded 1,167.936 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-01-EXCLUSION-BUFFER-500** Extended exclusion buffer for Natura 2000 and goose rest areas | norm variance (NC-Z-03) | FR-Z-03: set_buffer_distance_m→500m | 1,103.261 | -64.675 (-5.54%) | 0.944624 | ok |
| **SC-02-COMPENSATION-BUFFER-200** Mandatory green contour compensation buffer | norm variance (NC-Z-04) | FR-Z-04: set_buffer_distance_m→200m | 1,167.936 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-03-INCLUSION-SEMANTICS-EXCLUSION** Reclassify solar field zone as exclusion | policy variant (NC-Z-02) | FR-Z-02: set_semantics→exclusion | 314.251 | -853.685 (-73.09%) | 0.000000 | ok |
| **SC-04-EXCLUSION-SEMANTICS-INCLUSION** Reclassify protected areas as inclusion | policy variant (NC-Z-03) | FR-Z-03: set_semantics→inclusion | 1,245.803 | +77.866 (+6.67%) | 0.937497 | ok |
| **SC-05-COMPENSATION-SEMANTICS-EXCLUSION** Reclassify green contour as exclusion | policy variant (NC-Z-04) | FR-Z-04: set_semantics→exclusion | 1,145.271 | -22.665 (-1.94%) | 0.980594 | ok |
| **SC-06-DROP-COMPENSATION** Remove green contour compensation requirement | policy variant (NC-Z-04) | FR-Z-04: drop | 1,167.936 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-07-DROP-EXCLUSION** Remove Natura 2000 and goose rest area exclusion | policy variant (NC-Z-03) | FR-Z-03: drop | 1,167.948 | +0.011 (+0.00%) | 0.999990 | ok |
| **SC-08-INCLUSION-BUFFER-100** Solar field zone inclusion buffer | norm variance (NC-Z-02) | FR-Z-02: set_buffer_distance_m→100m | 1,228.525 | +60.588 (+5.19%) | 0.950682 | ok |
| **SC-09-EXCLUSION-BUFFER-1000** Extended exclusion buffer for protected areas | norm variance (NC-Z-03) | FR-Z-03: set_buffer_distance_m→1000m | 1,039.458 | -128.478 (-11.00%) | 0.889995 | ok |
| **SC-10-COMPENSATION-BUFFER-500** Extended green contour compensation buffer | norm variance (NC-Z-04) | FR-Z-04: set_buffer_distance_m→500m | 1,167.936 | +0.000 (+0.00%) | 1.000000 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
