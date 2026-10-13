# Scenario report — SR-20261005T072839Z-mobiliteit-20261013T150114Z

- baseline run: `20261005T072839Z-mobiliteit` · scenario set: `SSET-mobiliteit-utrecht-uitdagingen`
- control (unmutated re-execution): **1,560.054 km²** (baseline run recorded 1,560.054 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-MO-GELUID-HARD** Geluidcontouren treated as hard exclusion for roadside development | policy variant (NC-MO-02) | FR-MO-02: set_semantics→exclusion | 1,522.785 | -37.269 (-2.39%) | 0.976111 | ok |
| **SC-MO-WEG-HARD** Beperkingengebied provinciale weg treated as hard exclusion | policy variant (NC-MO-01) | FR-MO-01: set_semantics→exclusion | 1,553.051 | -7.003 (-0.45%) | 0.995511 | ok |
| **SC-MO-LUCHTVAART-ONVOORWAARDELIJK** Luchtvaartverbod executed without its activity scope | policy variant (NC-MO-05) | FR-MO-05: set_semantics→exclusion | 545.590 | -1,014.464 (-65.03%) | 0.349725 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
