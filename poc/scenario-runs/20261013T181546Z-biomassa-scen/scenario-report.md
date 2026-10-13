# Scenario report — SR-20261006T120133Z-biomassa-20261013T181546Z

- baseline run: `20261006T120133Z-biomassa` · scenario set: `SSET-biomassa-utrecht-uitdagingen`
- control (unmutated re-execution): **1,560.054 km²** (baseline run recorded 1,560.054 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-BM-LANDELIJK-HARD** Vestigingsgebied landelijk treated as hard exclusion | policy variant (NC-BM-01) | FR-BM-01: set_semantics→exclusion | 314.245 | -1,245.809 (-79.86%) | 0.201432 | ok |
| **SC-BM-STEDELIJK-HARD** Vestigingsgebied stedelijk treated as hard exclusion | policy variant (NC-BM-02) | FR-BM-02: set_semantics→exclusion | 1,245.812 | -314.242 (-20.14%) | 0.798570 | ok |
| **SC-BM-BUFFER-500** Rural designation exclusion widened by a 500 m band | hypothetical — *not legally grounded* | FR-BM-01: set_buffer_distance_m→500m | 1,560.054 | +0.000 (+0.00%) | 1.000000 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
