# Scenario report — SR-20261016T151055Z-wonen-nl-20261016T202432Z

- baseline run: `20261016T151055Z-wonen-nl` · scenario set: `SSET-wonen-nl-pdok`
- control (unmutated re-execution): **1,000.606 km²** (baseline run recorded 1,000.606 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WON-NL-BUITEN-OVERSTROMINGSGEVAAR** Buiten het overstromingsgevarengebied (NL) | hypothetical — *not legally grounded* | HYP-WON-GEEN-GEVARENGEBIED: add_zone_rule→exclusion | 565.849 | -434.758 (-43.45%) | 0.565505 | ok |
| **SC-WON-NL-SEVESO-PROD-500M** 500 m afstand tot Seveso-productie-inrichtingen (NL) | hypothetical — *not legally grounded* | HYP-WON-SEVESO-500M: add_zone_rule→exclusion→500m | 994.005 | -6.601 (-0.66%) | 0.993402 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
