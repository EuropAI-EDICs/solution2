# Scenario report — SR-20261006T121921Z-werken-20261018T103010Z

- baseline run: `20261006T121921Z-werken` · scenario set: `SSET-werken-whatif-netcongestie`
- control (unmutated re-execution): **1,017.614 km²** (baseline run recorded 1,017.614 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WER-NETCONGESTIE-1KM** Bedrijventerreinen 1 km rond netcongestie uitgesloten | hypothetical — *not legally grounded* | SC-WER-AZR-1: add_zone_rule→exclusion→1000m | 145.892 | -871.722 (-85.66%) | 0.143367 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
