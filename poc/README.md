# LDT Toolbox PoC — "Where can I do what?" in province Utrecht (wind · zon · bos · water · bodem · mobiliteit · landschap · landbouw · wonen · biomassa · energietoets)

This is the working proof-of-concept of the multi-agent architecture specified in
[`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) and elaborated in
[`docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md) (read that
document first: module boundaries, contract catalogue, validation levels,
technology and roadmap). Urban Strategy (Scenexus) stiltegebied noise
screening for the Utrecht wind track — decision-support annex for
art. 9.26 / FR-W-11 — is documented in
[`docs/POC_URBANSTRATEGY_INTEGRATION.md`](../docs/POC_URBANSTRATEGY_INTEGRATION.md). It answers, for the province of Utrecht (NL) at the
**programming** policy stage, the same traceable question for **eleven object
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
| `water` | riparian development (watersysteem activities) | where can riparian development stand under the watersysteem instructieregels? | `runs/20261004T185116Z-water` — 1554.906 km² |
| `bodem` | soil activity (ondergrond en bodem) | where is soil activity bounded by the groundwater-protection rules? | `runs/20261004T185509Z-bodem` — 858.927 km² |
| `mobiliteit` | roadside development (bereikbaarheid en mobiliteit) | where is roadside development bounded by the mobility instructieregels? | `runs/20261005T072839Z-mobiliteit` — 1560.054 km² (all-marker) |
| `landschap` | landscape intervention (cultuurhistorie en landschap) | where is landscape intervention bounded by the heritage/landscape rules? | `runs/20261005T070621Z-landschap` — 1425.959 km² |
| `landbouw` | agricultural expansion (landbouw, incl. glastuinbouw en veenbodembewerking) | where is agricultural expansion bounded by the landbouw instructieregels? | `runs/20261005T094244Z-landbouw` — 2.260 km² |
| `wonen` | housing development (wonen, werken, recreëren) | where is housing development possible under the wonen instructieregels? | `runs/20261005T100258Z-wonen` — 1142.990 km² |
| `biomassa` | biomass installations (energie uit biomassa) | where can biomass energy developments stand under arts. 5.6/5.7? | `runs/20261006T120133Z-biomassa` — 1560.054 km² (all-marker) |
| `energietoets` | energy test / netbelasting (afdeling 5.3) | where do arts. 5.10/5.11 condition new functions that load the grid? | `runs/20261006T171730Z-energietoets` — 1560.054 km² (all-marker) |

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
python3 poc/run.py --use-case water    # riparian development (arts. 2.14–2.16)
python3 poc/run.py --use-case bodem    # soil activity (grondwaterzone, art. 3.7 e.a.)
python3 poc/run.py --use-case mobiliteit  # roadside development (arts. 4.7/4.47/4.48/4.65/4.71)
python3 poc/run.py --use-case landschap   # landscape intervention (arts. 7.3/7.3a/7.4/7.9/7.11a/7.12)
python3 poc/run.py --use-case landbouw   # agricultural expansion (arts. 8.1-8.7)
python3 poc/run.py --use-case wonen      # housing development (arts. 9.3-9.29)
python3 poc/run.py --use-case biomassa   # biomass installations (arts. 5.6/5.7)
python3 poc/run.py --use-case energietoets  # energy test / netbelasting (arts. 5.10/5.11)
python3 poc/run.py --refresh           # force live re-download of every layer
python3 poc/run.py --bbox 130000,440000,160000,470000   # optional EPSG:28992 clip
cd poc && python3 -m pytest tests -q                         # offline test suite (274 tests)
```

No API keys are used anywhere (the DSO GIO download API is key-gated and was
verified 401 — see limitations below). Exit code is `0` only when the
Critic/Validator's pipeline-run verdict is `pass`.

## What the pipeline does

`poc/run.py` is the orchestrator (plan §3.2 agent #1). One process, no LLM at
runtime by default — every "agent" is a deterministic implementation behind
the agent interface, with propose-only LLM legs behind gated seams
(`pipeline/norm_llm.py`; S1/S2, see `docs/GENAI_SEAMS.md`):

```bash
# default (offline, byte-identical replay)
python3 poc/run.py --use-case wind

# S1/S2 seams: local open model refines claims / proposes formalizations
# (propose-only; needs LDT_NORM_LLM_ENDPOINT, e.g. Ollama; loud deterministic
# fallback + norm-llm-ledger.json in the run dir when unavailable)
LDT_NORM_LLM_ENDPOINT=http://localhost:11434 LDT_NORM_LLM_API=ollama \
LDT_NORM_LLM_MODEL=qwen3.8 python3 poc/run.py --use-case wind \
  --norm-analyst llm --formalizer llm

# golden-set regression deterministic vs LLM (proposals only, cheap)
python3 poc/llm/compare_norm_llm.py --use-case wind
```

S1 (`--norm-analyst llm`) may only refine the English claim + confidence —
citations, legal force and geo bindings are unreachable by construction, and
the seam stamps `extractedBy`. S2 (`--formalizer llm`) proposes formalizations
only for template-less ambiguous cards, gated on zone grounding (registry
aliases / the card's own geo binding) and verbatim quote-numeral grounding;
curated abstentions (template kind ambiguous/reject) are never re-proposed.
Both legs share the S7 transport (`pipeline/llm_transport.py`, temperature 0,
thinking disabled, bounded generation) and reject into ledgers, never guess.

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
- **water** — the final zone is the province boundary minus the single hard
  exclusion `waterbergingsgebied` (art. 2.15 — new development is ruled out
  there, bestaande uitbreidingsrechten excepted; 5.148 km² carved). The
  `vrijwaringszone regionale waterkering` (art. 2.14, 28.011 km² in-AOI) and
  `overstroombaar gebied` (art. 2.16, 1207.173 km² in-AOI) are
  **conditional** markers — the omgevingsplan must protect the waterkering's
  function and differentiate binnendijks/buitendijks objects, but the markers
  never eliminate area. Waterkering-omgevingswaarden (arts. 2.2–2.11) are
  monitoring norms for water boards and are deliberately abstained.
- **bodem** — the final zone is the province boundary minus the
  grondwaterbeschermingszone umbrella: art. 3.7 ('laat geen activiteiten toe
  die een risico vormen voor de winning') and art. 3.9 (verbod on new
  burial facilities) are executed as **hard exclusions** on the shared
  umbrella zone (the full grondwaterbeschermingszone designation,
  701.126 km² in-AOI — a conservative superset of the literal designation
  areas per article). Art. 3.10 ('rekening houden met', the weakest
  take-into-account variant) deliberately stays a **conditional** marker
  routed to V4, and the `gesloten stortplaats` (art. 3.108, 0.373 km²) a
  **context marker** of provincial jurisdiction. Art. 3.8 (waterwingebied
  Bethunepolder, parkeren) has no registered zone alias and stays
  ambiguous → V4.
- **mobiliteit** — an **all-marker track**: no hoofdstuk-4 rule unconditionally
  refuses roadside development itself, so the final zone equals the province
  AOI (1560.054 km²) with five conditional markers. Arts. 4.7
  (beperkingengebied bouwwerken provinciale weg, 7.003 km²) and 4.47/4.48
  (beperkingengebied lokale spoorweg, the live-verified art.-4.46 umbrella of
  Kernzone ∪ Beschermingszone, 0.635 km²) are kan-mits instructieregels;
  art. 4.71 gates geluidgevoelige gebouwen on dB Lden thresholds in the
  Geluidcontour buiten/binnen de bebouwde kom (37.285 km² combined); and
  art. 4.65 (Luchtvaartterrein, 1014.473 km²) is an unconditional verbod of
  the non-permission family but **activity-scoped to aviation**
  (nieuwvestiging luchtvaartterrein voor gemotoriseerde luchtvaartuigen) —
  carried as a marker, never an elimination of roadside-development area.
  The vergunnings-/meldingsketens (beheer, vrij zicht, vaarweg) and the
  [Gereserveerd] basisnet articles (4.67/4.68) are deliberately abstained.
- **landbouw** — the final zone is the province boundary minus three
  niet-toestaan-instructieregels whose refused activity classes sit inside
  agricultural_expansion: the Landbouwstabiliseringsgebied (art. 8.3, no
  expansion of niet-grondgebonden farm plots, 246.818 km²), the Gebied
  glastuinbouw niet toegestaan (art. 8.6, no glasshouse horticulture except
  Ronde Venen relocations to the Polder Derde Bedijking — the designation
  covers 1557.796 km², i.e. the whole province minus the kassenconcentraties)
  and the Gebied beperken bodembewerking (art. 8.7, no veen-exposing
  agricultural soil work, 192.249 km²). Final = **2.260 km²**: legally exact —
  glasshouse expansion is only possible in the kassenconcentraties. The mixed/
  kan-mits/protective rules stay **conditional** markers: agrarische bedrijven
  (art. 8.1, verbod nieuwe bouwpercelen + voorschrift 1,5 ha-bouwpercelen),
  landbouwontwikkelingsgebied (art. 8.2, kan-mits 2,5 ha), concentratiegebied
  glastuinbouw (art. 8.5, plans may not hinder glasshouses). Art. 8.4
  (geitenhouderij) is a province-wide verbod without gebiedsaanwijzing:
  abstained (ALB-01).
- **wonen** — the final zone is the **inclusion composition**: Stedelijk
  gebied (art. 9.17, kan verstedelijking/woningbouw), Kernrandzone (art. 9.10)
  and the Gebied uitbreiding woningbouw onder voorwaarden mogelijk
  (arts. 9.14/9.14a/9.15 — 50-woningen-vitaliteit, flexwoningen, woningbouw
  onder voorwaarden) = **1142.990 km²**. These are the verordeningeigen
  exceptions to the core art.-9.3 verstedelijkingsverbod in het Landelijk
  gebied, which is therefore a **conditional** marker (its tenzij-structuur is
  operationalized by the inclusions; an exclusion would erase the exception
  zones). Art. 9.8 (Gebied recreatiewoning) is object-scoped (omvorming van
  bestaande recreatiewoningen tot permanente bewoning — designation 1245.814
  km² = the landelijk-gebied extent) and likewise a marker, not an exclusion.
  Arts. 9.6/9.12/9.13 (kan-mits wonen) and 9.27/9.29 (rekening-houden
  stiltegebied, fase-1-aliases hergebruikt) are markers; werken/recreatie
  (arts. 9.16-9.23), de [Gereserveerde] 9.21 en de bordenketen zijn onthouden
  (fase-4-heroverweging).
- **landschap** — the final zone is the province boundary minus the two
  werelderfgoed designations whose instructieregels carry the
  niet-toestaan-form in lid 1b: the Hollandse Waterlinies (art. 7.3,
  134.092 km²) and the Neder-Germaanse Limes kernzone (art. 7.3a,
  0.013 km²) — hard exclusions with the aantasten-toets routed to V4 per
  case. The weaker families stay **conditional** markers: the Limes
  bufferzone (art. 7.4, versterkingsplicht + 100 m²/30 cm
  vergunningsverbodprescriptie), the cultuurhistorische hoofdstructuur
  (art. 7.9 on the live-verified umbrella of the five art.-7.8 gebieden,
  847.4 km²), the Landschap-kernkwaliteiten (art. 7.11a, 'onevenredig'
  proportionality on Bijlage XVI, 1411.1 km² umbrella) and the aardkundige
  waarden (art. 7.12, 99.2 km²). The 7.10 verstedelijkingsgateway and the
  borden-activiteitenketen (7.13–7.17) are deliberately abstained.

Reference numbers (canonical runs of 2026-08-30 for wind/zon/bos,
2026-10-04 for water/bodem): wind AOI 1560.054 km² →
inclusion ∩ AOI 1259.841 km² → final 859.463 km² (V3 IoU 0.99994); zon →
Gebied zonneveld ∩ AOI 1167.948 km² → final 1167.936 km² (IoU 0.99998);
bos → Groene contour ∩ AOI 23.924 km² = final (no exclusions; IoU 0.9997);
water → AOI 1560.054 km² − waterbergingsgebied 5.148 km² = final
1554.906 km² (IoU 0.999996); bodem → AOI 1560.054 km² −
grondwaterbeschermingszone 701.126 km² = final 858.927 km² (IoU 0.999979;
the art. 3.10 marker never eliminates area); mobiliteit → final = AOI
1560.054 km², five markers, no exclusions (IoU 0.999997); landschap →
AOI 1560.054 km² − Hollandse Waterlinies 134.092 km² − Limes-kernzone
0.013 km² = final 1425.959 km² (IoU 0.999994); landbouw → AOI −
glastuinbouw-niet-toegestaan ∪ stabiliserings ∪ bodembewerking = final
2.260 km² (IoU 0.999889; ≈ de kassenconcentraties); wonen → inclusion-
compositie stedelijk ∪ kernrand ∪ uitbreiding-woningbouw = final 1142.990
km² (IoU 0.999973; canonical runs of 2026-10-05 for
mobiliteit/landschap/landbouw/wonen).

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

## Scenario planning (deterministic sweep, GenAI-seam Phase A)

[`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) specifies where GenAI enters
the deterministic PoCs; its Phase A is implemented here. A scenario is a
**contract** (`schemas/scenario-spec.schema.json`), not a prompt: an ordered
list of mutations (`drop` / `set_semantics` / `set_buffer_distance_m`) over a
*baseline run's* FormalRules, each with a provenance **basis** —
`norm_variance` (varies a cited rule's parameter), `policy_variant` (flips a
documented discretionary choice) or `hypothetical` (explicitly *not* legally
grounded, `rationale` required — the honest counterpart of the abstention
ledger). The sweep always re-executes an unmutated **control** first (V3:
must reproduce the baseline ≤0.1% rel), replays the baseline's cached layers
offline at its recorded tunings, and gates on a scenario critic (V0–V3
deterministic, V4 pending by design):

```bash
python3 poc/scenarios/run.py                     # wind, latest baseline run
python3 poc/scenarios/run.py --use-case zon      # solar fields
python3 poc/scenarios/run.py --use-case bos      # new nature
python3 poc/scenarios/run.py --baseline poc/runs/20260830T113234Z-wind
python3 poc/scenarios/run.py --author auto       # deterministic author derives
                                                 # proposals from the artifacts
python3 poc/scenarios/run.py --author hybrid  # det floor + LLM explorer (S7 product mode)
LDT_SCENARIO_LLM_ENDPOINT=http://localhost:8000/v1 \
    python3 poc/scenarios/run.py --author llm    # GenAI seam: open-model endpoint
                                                 # (proposals only, gated)
python3 poc/scenarios/run.py --narrate           # prose over the report, gated
                                                 # (every number must resolve)
```

Output: `poc/scenario-runs/<ts>-<track>/` — `scenario-report.json` /
`.md` (per-scenario final area, Δ vs control, IoU vs control, mutations
applied/skipped), `scenario-narrative.md` (with `--narrate`), `scenarios/
<SC-id>.geojson` per scenario + `CONTROL.geojson` (WGS84, diffable in QGIS),
`validation.json`, `prov.json`, `run_summary.json`; with `--author auto|llm|hybrid`
also `proposals.json` + `proposals-rejected.json` (the author's
cite-or-abstain ledger: schema-invalid or hallucinated ids are recorded and
never executed). Exit code 0 only on verdict `pass`. Demo sets:
`poc/scenarios/{wind,zon,bos}.json` — headline findings: the NNN lid-2
exception is the largest wind lever (+322.5 km², +37.5%), silence-area
strictness up to −61%, the zon Natura carve is negligible (+0.011 km²), a 1 km
bos zoekgebied band would grow it 16.5×; `--author auto` adds: a hypothetical
500 m NNN buffer costs −52.2%, and hard-enforcing the NNN *conditional*
overlay changes nothing (it is subsumed by the default exclusion).

A Phase-B LLM ScenarioAuthor may only do what the deterministic author does
today — emit `ScenarioSpec` proposals (`proposedBy: "llm-proposal#…"`, stamped
by the seam, not the model) through the same schema; mutations are restricted
to the engine's actual inputs, V2 grounds every `normCardId`/`ruleId` against
the baseline run, and unverifiable proposals land in `proposals-rejected.json`
(`poc/pipeline/scenario_author.py`).

B2 (live open model, local Ollama) is wired: `--narrator llm` has the same
numeric-grounding gate with a loud deterministic fallback
(`narrative-rejected.md`); connect with

```bash
export LDT_SCENARIO_LLM_ENDPOINT=http://localhost:11434   # Ollama base
export LDT_SCENARIO_LLM_API=ollama                        # native API: think:false works
export LDT_SCENARIO_LLM_MODEL=qwen3.8:latest
python3 poc/scenarios/run.py --use-case zon --author llm --narrator llm
python3 poc/scenarios/compare_authors.py --use-case zon   # golden-set author regression
```

Canonical LLM-authored run: `poc/scenario-runs/20260831T175842Z-zon-scen/`
(qwen3.8, 10/10 proposals accepted — every id real; the model's Dutch
narration passed every grounding gate and is published as
`scenario-narrative.md`; the rejection path — id drift, sign-fold
magnitudes, verdict assertions — is covered by 169 offline tests).
Findings and lessons: `docs/GENAI_SEAMS.md` §5.

## Cross-track conflict overlay (energy vs nature, deterministic)

[`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) phase C's cross-track conflict
discovery, deterministic base: re-executes each track's **unmutated control**
from its baseline run (cached layers, recorded tunings, offline) and overlays
the opportunity zones — pairwise conflicts plus each track's claim on shared
instrument zones. No legal claim is added, dropped or mutated (V2
`not_applicable` by design); V3 verifies every control reproduces its
baseline; V4 (arbitration) stays pending by design.

```bash
python3 poc/crosstrack/run.py                    # wind,zon,bos
python3 poc/crosstrack/run.py --tracks zon,bos   # just the Groene contour pair
```

Output: `poc/crosstrack-runs/<ts>-wzb-xtrack/` — `crosstrack-report.json`/`.md`,
`conflicts/<a>-x-<b>.geojson`, `shared/<zone>/<track>.geojson`,
`controls/<track>.geojson` (the exact inputs the conflicts were computed
from), `validation.json`, `prov.json`, `run_summary.json`. Exit 0 only on
verdict `pass`. Canonical run (`20260831T094204Z-wzb-xtrack`):

- **zon × bos: 22.665 km² — 94.7% of the zoekgebied nieuwe natuur is
  simultaneously open to zonnevelden** (the art.-6.5a-lid-3 compensation duty
  is the only legal buffer between the two ambitions; matches
  `SC-Z-GROENE-CONTOUR-HARD` exactly, as the bos final zone *is* the contour);
- wind × bos: 22.657 km² (94.7% of the zoekgebied) — the contour is claimed
  by both energy tracks;
- wind × zon: 845.445 km² (98.4% of the wind zone) — the two energy ambitions
  compete on nearly identical ground.

## H3 hex overlays (nldt bridge)

Zone truth stays polygon-based; H3 is a reporting layer computed by the
`nldt` h3-* OGC processes via `pipeline/h3step.py` (cache-first under
`poc/data/cache/h3/`, offline replays via `POC_H3_OFFLINE=1`).

- `python3 poc/crosstrack/run.py --tracks zon,bos` — per-cell zon×bos
  conflict on the Groene contour (`h3-crosstrack.json` + Leaflet
  `h3-crosstrack.html`; e.g. 34 cells, 92.5% weighted conflict share vs
  the 94.7% polygon headline)
- `python3 poc/crosstrack/run.py --buildings nldt/examples/hex-points.geojson` —
  buildings-per-zone-cell join (`h3-buildings.json`)
- `python3 poc/scenarios/run.py --use-case zon` — per-scenario Moran's I +
  cell deltas (`control.h3`, scenario-row `h3`); `--no-h3` skips the hex
  overlays (omit `--buildings` too for a fully hex-free crosstrack run)
- fixtures: `POC_H3_OFFLINE= ../nldt/.venv/bin/python tests/make_h3_fixtures.py` (in `poc/`)

## Urban Strategy stiltegebied screen (wind)

Art. 9.26 LAeq thresholds (40/45 dB) stay legally ambiguous as FR-W-11; the
wind track adds a **decision-support** receptor exceedance screen via nldt
`us-*` processes and `pipeline/usstep.py` (cache-first under
`poc/data/cache/us/`, offline via `POC_US_OFFLINE=1`).

```bash
python3 poc/run.py --use-case wind          # writes urbanstrategy-stiltegebied.json
python3 poc/run.py --use-case wind --skip-us
POC_US_OFFLINE= ../nldt/.venv/bin/python tests/make_us_fixtures.py   # in poc/
```

Live RestAPI (opt-in): `US_LIVE=1` plus `US_BASE_URL`, `US_TOKEN` (or
email/password), `US_BIN`. See
[`docs/POC_URBANSTRATEGY_INTEGRATION.md`](../docs/POC_URBANSTRATEGY_INTEGRATION.md).

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
`schemas/opportunity-map-request.schema.json` already covers solar fields,
forest planting, riparian development and soil activity. `python3 -m
pipeline.agents` regenerates the deterministic
per-track corpora (`normcards-<track>.json` / `formalrules-<track>.json`).
