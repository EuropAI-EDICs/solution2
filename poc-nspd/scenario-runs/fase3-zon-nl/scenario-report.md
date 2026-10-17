# Scenario report — SR-20261016T144619Z-zon-nl-20261017T063350Z

- baseline run: `20261016T144619Z-zon-nl` · scenario set: `SSET-zon-nl-nspd-fase3`
- control (unmutated re-execution): **22.858 km²** (baseline run recorded 22.858 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-ZON-NL-STED-DROP** Stedelijk-gebiedbeleid losgelaten (NL) | policy variant (NC-ZON-01) | FR-ZON-01: drop | 852.177 | +829.318 (+3628.12%) | 0.026823 | ok |
| **SC-ZON-NL-NATURA-BUF500** Natura 2000-exclusie verbreed met 500 m (NL) | norm variance (NC-ZON-02) | FR-ZON-02: set_buffer_distance_m→500m | 18.139 | -4.719 (-20.65%) | 0.793529 | ok |
| **SC-ZON-NL-ZONDER-NATURA** Zonder Natura 2000-toets (NL) | hypothetical — *not legally grounded* | FR-ZON-02: drop | 22.880 | +0.022 (+0.10%) | 0.999041 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
