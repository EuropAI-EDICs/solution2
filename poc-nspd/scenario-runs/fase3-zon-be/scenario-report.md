# Scenario report — SR-20261016T150840Z-zon-be-20261017T063350Z

- baseline run: `20261016T150840Z-zon-be` · scenario set: `SSET-zon-be-nspd-fase3`
- control (unmutated re-execution): **0.445 km²** (baseline run recorded 0.445 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-ZON-BE-HERN-DROP** Hernieuwbaar-energiegebied losgelaten (BE) | policy variant (NC-BEZ-01) | FR-BEZ-01: drop | 536.007 | +535.562 (+120436.02%) | 0.000830 | ok |
| **SC-ZON-BE-HERN-BUF1000** Hernieuwbaar-energiegebied verbreed met 1.000 m (BE) | norm variance (NC-BEZ-01) | FR-BEZ-01: set_buffer_distance_m→1000m | 6.484 | +6.039 (+1358.01%) | 0.068590 | ok |
| **SC-ZON-BE-BOUWVRIJ-DROP** Bouwvrije strook-exclusie losgelaten (BE) | policy variant (NC-BEZ-02) | FR-BEZ-02: drop | 0.445 | +0.000 (+0.00%) | 1.000000 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
