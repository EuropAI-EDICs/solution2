# Scenario report — SR-20261005T070621Z-landschap-20261013T144938Z

- baseline run: `20261005T070621Z-landschap` · scenario set: `SSET-landschap-utrecht-uitdagingen`
- control (unmutated re-execution): **1,560.054 km²** (baseline run recorded 1,425.959 km²; reproduction Δ +134.095 km², rel 0.094039, tolerance 0.001)
- verdict: **fail** (V4 human review pending by design)

| scenario | basis | mutations | final km² | Δ vs control | IoU | status |
|---|---|---|---:|---:|---:|---|
| **SC-LS-CHS-HARD** Cultuurhistorische hoofdstructuur treated as hard exclusion | policy variant (NC-LS-04) | FR-LS-04: set_semantics→exclusion | 1,560.054 | +0.000 (+0.00%) | 1.000000 | degraded |
| **SC-LS-AARDKUNDIG-HARD** Aardkundige waarden treated as hard exclusion | policy variant (NC-LS-06) | FR-LS-06: set_semantics→exclusion | 1,560.054 | +0.000 (+0.00%) | 1.000000 | degraded |
| **SC-LS-LIMES-BUFFER-100** Limes kernzone exclusion widened by a 100 m band | norm variance (NC-LS-02) | FR-LS-02: set_buffer_distance_m→100m | 1,560.054 | +0.000 (+0.00%) | 1.000000 | degraded |

## Control per-level validation

## Degradations

- `layer-cache-missing`  : zone 'gebied_aardkundige_waarden': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-gebied-aardkundige-waarden.28992.geojson' absent — rules referencing it will be dropped this run
- `layer-cache-missing`  : zone 'gebied_cultuurhistorische_hoofdstructuur': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-gebied-cultuurhistorische-hoofdstructuur.28992.geojson' absent — rules referencing it will be dropped this run
- `layer-cache-missing`  : zone 'landschap': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-landschap.28992.geojson' absent — rules referencing it will be dropped this run
- `layer-cache-missing`  : zone 'unesco_werelderfgoed_hollandse_waterlinies': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-unesco-werelderfgoed-hollandse-waterlinies.28992.geojson' absent — rules referencing it will be dropped this run
- `layer-cache-missing`  : zone 'unesco_werelderfgoed_neder_germaanse_limes_bufferzone': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-unesco-werelderfgoed-neder-germaanse-limes-bufferzone.28992.geojson' absent — rules referencing it will be dropped this run
- `layer-cache-missing`  : zone 'unesco_werelderfgoed_neder_germaanse_limes_kernzone': cache file '/Users/marc/Projecten/ldttoolbox-vf2/poc/data/cache/agrest-ov-unesco-werelderfgoed-neder-germaanse-limes-kernzone.28992.geojson' absent — rules referencing it will be dropped this run
- `rule-dropped` CONTROL FR-LS-01: zone layer(s) unavailable this run: unesco_werelderfgoed_hollandse_waterlinies
- `rule-dropped` CONTROL FR-LS-02: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_kernzone
- `rule-dropped` CONTROL FR-LS-03: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_bufferzone
- `rule-dropped` CONTROL FR-LS-04: zone layer(s) unavailable this run: gebied_cultuurhistorische_hoofdstructuur
- `rule-dropped` CONTROL FR-LS-05: zone layer(s) unavailable this run: landschap
- `rule-dropped` CONTROL FR-LS-06: zone layer(s) unavailable this run: gebied_aardkundige_waarden
- `rule-dropped` SC-LS-CHS-HARD FR-LS-01: zone layer(s) unavailable this run: unesco_werelderfgoed_hollandse_waterlinies
- `rule-dropped` SC-LS-CHS-HARD FR-LS-02: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_kernzone
- `rule-dropped` SC-LS-CHS-HARD FR-LS-03: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_bufferzone
- `rule-dropped` SC-LS-CHS-HARD FR-LS-04: zone layer(s) unavailable this run: gebied_cultuurhistorische_hoofdstructuur
- `rule-dropped` SC-LS-CHS-HARD FR-LS-05: zone layer(s) unavailable this run: landschap
- `rule-dropped` SC-LS-CHS-HARD FR-LS-06: zone layer(s) unavailable this run: gebied_aardkundige_waarden
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-01: zone layer(s) unavailable this run: unesco_werelderfgoed_hollandse_waterlinies
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-02: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_kernzone
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-03: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_bufferzone
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-04: zone layer(s) unavailable this run: gebied_cultuurhistorische_hoofdstructuur
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-05: zone layer(s) unavailable this run: landschap
- `rule-dropped` SC-LS-AARDKUNDIG-HARD FR-LS-06: zone layer(s) unavailable this run: gebied_aardkundige_waarden
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-01: zone layer(s) unavailable this run: unesco_werelderfgoed_hollandse_waterlinies
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-02: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_kernzone
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-03: zone layer(s) unavailable this run: unesco_werelderfgoed_neder_germaanse_limes_bufferzone
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-04: zone layer(s) unavailable this run: gebied_cultuurhistorische_hoofdstructuur
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-05: zone layer(s) unavailable this run: landschap
- `rule-dropped` SC-LS-LIMES-BUFFER-100 FR-LS-06: zone layer(s) unavailable this run: gebied_aardkundige_waarden

> Phase A deterministic sweep (docs/GENAI_SEAMS.md): no LLM at runtime; scenario specs are schema-validated contracts authored by deterministic-scenario-author#poc-v0.

> Deltas are measured against the unmutated control re-executed over the baseline run's cached layers (same tunings), not against summary numbers.

> Marker semantics (attention/conditional/compensation) never alter the opportunity zone; set_semantics mutations make that policy choice explicit and visible in the delta.
