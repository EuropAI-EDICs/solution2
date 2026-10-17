# Scenario report — SR-20261016T151051Z-bos-nl-20261016T202513Z

- baseline run: `20261016T151051Z-bos-nl` · scenario set: `SSET-bos-nl-pdok`
- control (unmutated re-execution): **1,000.606 km²** (baseline run recorded 1,000.606 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-BOS-NL-ZONDER-WETLANDS** Buiten Ramsar-wetlands (NL) | hypothetical — *not legally grounded* | HYP-BOS-GEEN-WETLANDS: add_zone_rule→exclusion | 853.226 | -147.381 (-14.73%) | 0.852708 | ok |
| **SC-BOS-NL-ALLEEN-CDDA** Alleen binnen nationaal beschermde gebieden (NL) | hypothetical — *not legally grounded* | FR-AOI-01: drop; HYP-BOS-BINNEN-CDDA: add_zone_rule→inclusion | 171.497 | -829.109 (-82.86%) | 0.171392 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
