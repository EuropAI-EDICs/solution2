# LDT Toolbox PoC — "Where can I do what?" in province Utrecht (wind · zon · bos)

This is the working proof-of-concept of the multi-agent architecture specified in
[`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) and elaborated in
[`docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md) (read that
document first: module boundaries, contract catalogue, validation levels,
technology and roadmap). It answers, for the province of Utrecht (NL) at the
**programming** policy stage, the same traceable question for **three object
types** (tracks), all on the same instrument and pipeline:

> Within which zone of the province could an omgevingsplan allow **X**, and
> which legal norms exclude, condition or compensate there — with every legal
> claim cited (instrument + article + version + verbatim quote + URL) and every
> artifact schema-validated and provenance-traced?

| track | use case | core question | canonical run |
|---|---|---|---|
| `wind` | wind turbines | where can turbines ≥3 MW / ≤20 m hub stand? | `runs/20260830T113234Z-wind` — 859.463 km² |
| `zon` | solar fields (zonnevelden) | where can ground/water-mounted solar fields stand? | `runs/20260830T142439Z-zon` — 1167.936 km² |
| `bos` | new nature / forest planting | where is the zoekgebied for new nature? | `runs/20260830T142446Z-bos` — 23.924 km² |

Grounding: the **Omgevingsverordening provincie Utrecht** (CVDR704250, geldend
13-10-2025) and the **Omgevingsvisie 2021**, plus the province's open geo data
(agrest Omgevingsverordening IMOW service + province ArcGIS Hub). Paper B's
future-work pilot (Utrecht geodata + Omgevingsvisie, windmill-space use case) is
exactly this PoC.

## Run it (no install, stdlib + the verified toolchain)

Requirements already on this machine: `python3` (3.13) with `shapely`,
`pyproj`, `geopandas`, `requests`, `jinja2`, `jsonschema`; `ogr2ogr` at
`/opt/homebrew/bin` (optional — GML export degrades gracefully without it).

```bash
python3 poc/run.py                     # wind use case, cache-first
python3 poc/run.py --use-case zon      # solar fields (zonnevelden, art. 5.5)
python3 poc/run.py --use-case bos      # new nature / forest planting (art. 6.4)
python3 poc/run.py --refresh           # force live re-download of every layer
python3 poc/run.py --bbox 130000,440000,160000,470000   # optional EPSG:28992 clip
python3 -m unittest discover -s poc/tests               # offline test suite (100 tests)
```

No API keys are used anywhere (the DSO GIO download API is key-gated and was
verified 401 — see limitations below). Exit code is `0` only when the
Critic/Validator's pipeline-run verdict is `pass`.

## What the pipeline does

`poc/run.py` is the orchestrator (plan §3.2 agent #1). One process, no LLM at
runtime — every "agent" is a deterministic implementation behind the agent
interface with a pluggable hook (`NormAnalyst(llm_hook=...)`) for future
deployment:

| stage | module | output artifacts (in the run dir) |
|---|---|---|
| Intake — load + validate `OpportunityMapRequest` | `run.py` | `request.json` |
| Norm Analyst — deterministic replay of the verified legal recon (cite-or-abstain) | `pipeline/agents.py` | `normcards.json`, `normcards-rejected.json` (abstention ledger) |
| Norm Formalizer — NormCards → FormalRules (explicit templates; ambiguous/rejected rules never carry predicates) | `pipeline/agents.py` | `formalrules.json` |
| Geo Analyst — fetch every zone layer referenced by a formalized rule (ArcGIS REST, cache-first, both province dialects) | `pipeline/geodata.py` | `layers.json` (manifest with lastChecked + GIO alias provenance), cache under `data/cache/` |
| Zone engine — deterministic FormalRule execution (inclusion union ∩ AOI − exclusions; markers never alter the zone) | `pipeline/engine.py` | `zones.json` (ZoneResult contract), `rule-stats.json` |
| Cartographer — RFC-7946 GeoJSON + GML 3.2 (ogr2ogr, graceful degradation) | `pipeline/cartographer.py` | `zones.geojson`, `zones.gml` + `zones.xsd`, `report_input.json` |
| Critic/Validator — V0 syntactic, V1 geometric, V2 legal grounding, V3 semantic re-execution (independent geopandas path), V4 always pending (HITL) | `pipeline/critic.py` | `validation.json` + `validation/*.json` (one ValidationReport per artifact set) |
| Explainer — DecisionTable (every row links a NormCard) + PROV-O-flavoured bundle | `pipeline/explainer.py` | `decision-table.json`, `decision-table.md`, `prov.json` |
| Report — single-file HTML with Leaflet layer switcher + fallback tables | `pipeline/report.py` + `pipeline/report_template.html` | `report.html` |
| run summary | `run.py` | `run_summary.json` (headline numbers, tunings, degradations, artifact hashes) |

The six agent-boundary contracts live in `poc/schemas/*.schema.json`
(draft 2020-12): `opportunity-map-request`, `norm-card`, `formal-rule`,
`zone-result`, `validation-report`, `decision-table` (plan §5). Every artifact
that crosses a stage boundary is validated against its schema — that is the V0
gate, enforced again independently by the Critic.

## Reading a run directory (`poc/runs/<timestamp>-wind/`)

- `report.html` — **start here**. Works when opened directly from disk
  (`file://`). Interactive Leaflet map (final zone, inclusion, per-exclusion
  cumulative zones, attention/conditional/compensation markers, AOI boundary,
  layer switcher; geometry display-simplified), plus always-available fallback
  tables: zone statistics, the full decision table, the validation report with
  every check, all 24 norm cards with verbatim Dutch quotes and source links,
  the abstention ledger, provenance (stages, agents, geo sources with
  lastChecked) and limitations.
- `run_summary.json` — headline numbers, per-rule footprints, tuned parameters,
  degradations, sha256 of every artifact.
- `decision-table.json` / `.md` — the trace-back artifact: 24 rows (one per
  rule), columns criterion / norm / source / zone effect / ruleId / normCardId /
  condition / note.
- `zones.json` — the `ZoneResult[]` contract (WGS84 payloads, per-zone
  provenance narrative); `zones.geojson` / `zones.gml` for GIS interop
  (QGIS/Tygron, paper B goal B2); `rule-stats.json` for per-rule footprints.
- `validation.json` — six ValidationReports (request, norm-card-set,
  formal-rule-set, zone-result-set, decision-table, pipeline-run), each with
  V0–V4 level results and per-check evidence.
- `prov.json` — agents (name+version), entities (with sha256), activities
  (per stage, with timestamps), wasGeneratedBy / wasDerivedFrom, and
  `hadPrimarySource` records for each geo layer including its `lastChecked`
  and the GIO join-id it aliases.
- `layers.json`, `normcards*.json`, `formalrules.json`, `request.json`,
  `report_input.json` — the intermediate boundaries, each schema-valid.

## Zone semantics per track (what the numbers mean)

- **wind** — the final zone is the union of the **formalized inclusion zones**
  (`Gebied windenergie` ≥3 MW path, art. 5.4; `Gebied kleine windturbine`
  ≤20 m path, art. 5.3; `Landelijk gebied` scope, arts. 9.2/9.3), clipped to
  the province boundary, minus the **hard exclusions** (Natura 2000 +
  ganzenrustgebieden per the art.-5.4 toelichting; Natuurnetwerk Nederland
  default exclusion per art. 6.3 with discretionary lid-2 exceptions).
  `Stiltegebied` (art. 9.28) and the NNN (art. 6.2) are **conditional**
  overlays, the 1500 m `Aandachtsgebied stiltegebied` (art. 9.25 lid 2) an
  **attention** buffer and the `Groene contour` (art. 6.5) a **compensation**
  obligation — markers that never eliminate area. 13 further rules are
  intentionally *ambiguous* (open norms) and are routed to V4 human review.
- **zon** — the opportunity zone is the `Gebied zonneveld` designation
  (art. 5.5 lid 1), clipped to the province, minus Natura 2000 and
  ganzenrustgebieden (toelichting art. 5.5 — same geographic reading as wind;
  the designation already avoids most of those areas, so the carve is small).
  The `Groene contour` carries the art.-6.5a lid 3 **compensation** marker:
  new compensating nature realised within 25 years of panel placement —
  zonnevelden in the contour are implicitly temporary. The three proviso's of
  lid 1 (landscape integration, soil/water quality, opruimplicht) are
  procedural, never executed. Rooftop solar is outside the object definition.
- **bos** — the opportunity zone is the `Groene contour` itself: the
  provincial **zoekgebied nieuwe natuur** (art. 6.4 lid 1, voluntary
  conversion, NNN addition after realisation). The ≥1:1 compensation ratio
  (art. 6.5 lid 2 onder d) is a marker on the contour, and the `Waardevolle
  Houtopstanden - oude bosgroeiplaatsen` (art. 6.13) a **conditional** overlay;
  the deterministic art.-6.15 velling-exemption thresholds govern forest
  management, not siting, and stay routed to V4.

Reference numbers (canonical runs of 2026-08-30): wind AOI 1560.054 km² →
inclusion ∩ AOI 1259.841 km² → final 859.463 km² (V3 IoU 0.99994); zon →
Gebied zonneveld ∩ AOI 1167.948 km² → final 1167.936 km² (IoU 0.99998);
bos → Groene contour ∩ AOI 23.924 km² = final (no exclusions; IoU 0.9997).

## Limitations (short list — full list in every report)

- **GIO geometry**: the DSO download API is key-gated (HTTP 401, verified);
  provincial zones are served from the province's own *vigerende verordening*
  open data (agrest IMOW layer, with AKN/IMOW ids) as **provenance aliases**
  of the Bijlage-II join-ids cited on each NormCard.
- The province-scale `Gebied windenergie` polygon is a designation envelope,
  not a "suitable everywhere" area; per-location assessments (clustering,
  removal duty, noise, grid) still apply.
- Abstained (no verified citation → no rule): stikstof, national wind-noise
  limits (Wgh/Bal), tip height/setbacks, Natura 2000 GIO, ET_wind tracking
  layer, the pending 01-01-2027 amendment (PS decision expected 18-11-2026 —
  re-run the recon before that date).
- **Tuned parameters** (recorded in every `run_summary.json` and in the engine
  provenance per layer): input geometries simplified at 2 m Douglas-Peucker
  (province-scale GEOS overlays are intractable at full source resolution; final
  area shifts ~0.002%), zone payload coordinates rounded to 6 dp with
  validity-repair provenance, report display geometry simplified at 25 m.
  Both are CLI flags (`--input-simplify-m`, `--display-tolerance-m`).
- No WFS/OGC-API fallback exists on the province stack; the connector is
  ArcGIS REST only. If a live layer fails mid-run the orchestrator degrades
  gracefully: the affected rules are dropped, recorded in the validation report
  (`needs_human`), never guessed.

## Adding use cases

A track is the combination of (a) an `OpportunityMapRequest` instance in
`poc/use-cases/<track>.json` (the province boundary as AOI with its source
recorded in `parameters`), (b) a verified evidence shard
`poc/corpus/evidence-<track>.json`, (c) curated enrichment + formalizer
templates in `pipeline/agents.py` (`EVIDENCE_ENRICHMENT` / `TEMPLATE_SPECS`,
keyed by evidence id — cards without a template are flagged ambiguous, never
guessed), (d) a cite-or-abstain ledger `poc/corpus/normcards-rejected-<track>.json`,
and (e) zone aliases in `run.py::ZONE_SOURCES` for any new zone layer plus a
registry entry in `poc/data/sources.json`. The `objectType` enum in
`schemas/opportunity-map-request.schema.json` already covers solar fields and
forest planting. `python3 -m pipeline.agents` regenerates the deterministic
per-track corpora (`normcards-<track>.json` / `formalrules-<track>.json`).
