# Scenario report — SR-20260830T142446Z-bos-20260831T074610Z

- baseline run: `20260830T142446Z-bos` · scenario set: `SSET-bos-utrecht-poc1`
- control (unmutated re-execution): **23.924 km²** (baseline run recorded 23.924 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-B-OUDE-BOS-HARD** Oude bosgroeiplaatsen treated as hard exclusion | policy variant (NC-B-03) | FR-B-03: set_semantics→exclusion | 23.911 | -0.014 (-0.06%) | 0.999419 | ok |
| **SC-B-EXPAND-1KM** Zoekgebied expanded by a 1 km band | hypothetical — *not legally grounded* | FR-B-01: set_buffer_distance_m→1000m | 395.396 | +371.471 (+1552.68%) | 0.060507 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
