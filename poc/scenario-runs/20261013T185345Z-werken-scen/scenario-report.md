# Scenario report — SR-20261006T121921Z-werken-20261013T185345Z

- baseline run: `20261006T121921Z-werken` · scenario set: `SSET-werken-utrecht-uitdagingen`
- control (unmutated re-execution): **1,017.614 km²** (baseline run recorded 1,017.614 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WE-DETAILHANDEL-HARD** Detailhandel verbod executed over the whole object | policy variant (NC-WE-06) | FR-WE-06: set_semantics→exclusion | 9.830 | -1,007.783 (-99.03%) | 0.009660 | ok |
| **SC-WE-ALLEEN-STEDELIJK** Business development only within existing urban area | policy variant (NC-WE-03) | FR-WE-03: drop | 314.242 | -703.372 (-69.12%) | 0.308802 | ok |
| **SC-WE-BEDRIJVENTERREIN-BUFFER-500** Bedrijventerrein designation expanded by a 500 m band | hypothetical — *not legally grounded* | FR-WE-03: set_buffer_distance_m→500m | 1,386.075 | +368.462 (+36.21%) | 0.734168 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
