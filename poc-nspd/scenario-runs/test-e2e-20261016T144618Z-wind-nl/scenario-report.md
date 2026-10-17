# Scenario report — SR-20261016T144618Z-wind-nl-20261017T093559Z

- baseline run: `20261016T144618Z-wind-nl` · scenario set: `SSET-wind-nspd-fase3`
- control (unmutated re-execution): **12.180 km²** (baseline run recorded 12.180 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-WIND-NL-CONCLOC-DROP** Concentratielocatiebeleid losgelaten (NL) | policy variant (NC-WIND-01) | FR-WIND-01: drop | 852.177 | +839.997 (+6896.50%) | 0.014293 | ok |
| **SC-WIND-NL-NATURA-BUFFER500** Natura 2000-exclusie verbreed met 500 m (NL) | norm variance (NC-WIND-02) | FR-WIND-03: set_buffer_distance_m→500m | 10.381 | -1.799 (-14.77%) | 0.852260 | ok |
| **SC-WIND-NL-ZONDER-NATURA** Zonder Natura 2000-toets (NL) | hypothetical — *not legally grounded* | FR-WIND-03: drop | 14.015 | +1.835 (+15.07%) | 0.869058 | ok |
| **SC-WIND-NL-WINDKLASSE-GE75** Windklasse ≥ 7,5 m/s opengesteld (NL) | hypothetical — *not legally grounded* | HYP-WINDKLASSE-GE75: add_zone_rule→inclusion | 51.163 | +38.983 (+320.06%) | 0.238062 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
