# Scenario report — SR-20261005T094244Z-landbouw-20261013T180746Z

- baseline run: `20261005T094244Z-landbouw` · scenario set: `SSET-landbouw-utrecht-uitdagingen`
- control (unmutated re-execution): **2.260 km²** (baseline run recorded 2.260 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LB-STABILISERING-OPEN** Landbouwstabiliseringsgebied no longer excluded | policy variant (NC-LB-03) | FR-LB-03: drop | 2.260 | +0.000 (+0.00%) | 1.000000 | ok |
| **SC-LB-BEDRIJVEN-HARD** Gebied agrarische bedrijven treated as hard exclusion | policy variant (NC-LB-01) | FR-LB-01: set_semantics→exclusion | 0.002 | -2.258 (-99.91%) | 0.000911 | ok |
| **SC-LB-GLASTUIN-OVERAL** Glastuinbouw designation taken at face value (no kassenconcentraties limit) | hypothetical — *not legally grounded* | FR-LB-05: drop | 1,123.902 | +1,121.642 (+49631.24%) | 0.002011 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
