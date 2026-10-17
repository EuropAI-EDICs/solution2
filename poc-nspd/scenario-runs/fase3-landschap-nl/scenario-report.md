# Scenario report — SR-20261016T145649Z-landschap-nl-20261017T063352Z

- baseline run: `20261016T145649Z-landschap-nl` · scenario set: `SSET-landschap-nl-nspd-fase3`
- control (unmutated re-execution): **1,000.606 km²** (baseline run recorded 1,000.606 km²; reproduction Δ +0.000 km², rel 0.000000, tolerance 0.001)
- verdict: **pass** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LAN-NL-AFWEGING-STRENG** Afwegingszone als harde uitsluiting (NL) | policy variant (NC-LAN-01) | FR-LAN-01: set_semantics→exclusion | 974.596 | -26.010 (-2.60%) | 0.974004 | ok |
| **SC-LAN-NL-MARKERS-DROP** Landschapsmarkers losgelaten (NL) | policy variant (NC-LAN-01) | FR-LAN-01: drop; FR-LAN-02: drop | 1,000.606 | +0.000 (+0.00%) | 1.000000 | ok |

## Control per-level validation

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
