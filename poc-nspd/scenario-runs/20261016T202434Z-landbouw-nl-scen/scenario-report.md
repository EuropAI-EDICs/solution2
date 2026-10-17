# Scenario report — SR-20261016T151054Z-landbouw-nl-20261016T202434Z

- baseline run: `20261016T151054Z-landbouw-nl` · scenario set: `SSET-landbouw-nl-pdok`
- control (unmutated re-execution): **1,000.606 km²** (baseline run recorded 1,000.606 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LNB-NL-ALLEEN-GEWASPERCELEN** Alleen binnen BRP-gewaspercelen (NL) | hypothetical — *not legally grounded* | FR-AOI-01: drop; HYP-LNB-GEWASPERCELEN: add_zone_rule→inclusion | 201.254 | -799.353 (-79.89%) | 0.201129 | ok |
| **SC-LNB-NL-BUITEN-CDDA** Buiten nationaal beschermde gebieden (NL) | hypothetical — *not legally grounded* | HYP-LNB-GEEN-CDDA: add_zone_rule→exclusion | 829.109 | -171.497 (-17.14%) | 0.828606 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
