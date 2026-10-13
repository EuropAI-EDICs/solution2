# Scenario report — SR-20261006T114934Z-recreatie-20261013T180757Z

- baseline run: `20261006T114934Z-recreatie` · scenario set: `SSET-recreatie-utrecht-uitdagingen`
- control (unmutated re-execution): **186.618 km²** (baseline run recorded 186.618 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-RC-ALLEEN-DAGRECREATIE** Only bovenlokale dagrecreatieterreinen remain open | policy variant (NC-RC-02) | FR-RC-02: drop | 81.692 | -104.926 (-56.23%) | 0.437749 | ok |
| **SC-RC-DAGRECREATIE-BUFFER-500** Dagrecreatieterrein designation expanded by a 500 m band | norm variance (NC-RC-01) | FR-RC-01: set_buffer_distance_m→500m | 267.207 | +80.589 (+43.18%) | 0.698402 | ok |
| **SC-RC-DAGRECREATIE-ALLEEN-AANDACHT** Dagrecreatieterrein opening demoted to attention marker | policy variant (NC-RC-01) | FR-RC-01: set_semantics→attention | 136.346 | -50.271 (-26.94%) | 0.730619 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
