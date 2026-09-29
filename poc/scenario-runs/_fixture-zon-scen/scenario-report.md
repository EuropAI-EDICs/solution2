# Scenario report — SR-20260830T142439Z-zon-20260929T183827Z

- baseline run: `20260830T142439Z-zon` · scenario set: `SSET-zon-utrecht-poc1`
- control (unmutated re-execution): **1,167.936 km²** (baseline run recorded 1,167.936 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-Z-GROENE-CONTOUR-HARD** Groene contour treated as hard exclusion (nature first) | policy variant (NC-Z-04) | FR-Z-04: set_semantics→exclusion | 1,145.271 | -22.665 (-1.94%) | 0.980594 | ok |
| **SC-Z-GEEN-NATURA-CARVE** Designation taken at face value (no Natura/ganzenrust carve) | hypothetical — *not legally grounded* | FR-Z-03: drop | 1,167.948 | +0.011 (+0.00%) | 0.999990 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
