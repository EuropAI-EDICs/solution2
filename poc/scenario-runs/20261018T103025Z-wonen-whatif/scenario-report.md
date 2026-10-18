# Scenario report — SR-20261005T100258Z-wonen-20261018T103026Z

- baseline run: `20261005T100258Z-wonen` · scenario set: `SSET-wonen-whatif-netcongestie`
- control (unmutated re-execution): **1,142.990 km²** (baseline run recorded 1,142.990 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WON-NETCONGESTIE-INCLUSIE-500M** Woningbouw binnen 500 m van netcongestie toegestaan | hypothetical — *not legally grounded* | SC-WON-AZR-1: add_zone_rule→inclusion→500m | 1,465.891 | +322.901 (+28.25%) | 0.779723 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
