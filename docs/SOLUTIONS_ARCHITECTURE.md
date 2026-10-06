# Solutions Architecture — Multi-Agent Opportunity Mapping ("Where can I do what?")

| | |
|---|---|
| Document | `docs/SOLUTIONS_ARCHITECTURE.md` · v1.4 · **2026-09-29** |
| Specializes | `MULTI_AGENT_PLAN.md` v1.2 (§3–§8). That plan is the general spec; this document specializes it for the Utrecht pilot **and fixes the concrete module/data/contract layout** any such pilot follows. It does not repeat the plan — section numbers below link back to it. GenAI seam catalogue (which model roles exist and their gates): `docs/GENAI_SEAMS.md`. Platform layer that now wraps this pilot (and sibling PoCs): `nldt/00-architecture.md`. |
| Pilot instance | Eleven tracks on one instrument (Omgevingsverordening provincie Utrecht, CVDR704250): **wind** (turbines ≥3 MW and ≤20 m hub paths), **zon** (zonnevelden / solar fields), **bos** (nieuwe natuur / forest planting), **water** (riparian development, arts. 2.14–2.16), **bodem** (soil activity, arts. 3.7–3.10), **mobiliteit** (roadside development, arts. 4.7–4.71), **landschap** (landscape intervention, arts. 7.3–7.12), **landbouw** (agricultural expansion, arts. 8.1–8.7), **wonen** (housing development, arts. 9.3–9.29), **werken** (business development, arts. 9.9–9.20), **recreatie** (recreation development, arts. 9.22–9.23), province Utrecht (NL) |
| Grounding inputs | Legal recon: `docs/research/legal-facts.md` + `poc/corpus/*.json` (23 sources, 79 cite-verified evidence records: wind 24 · zon 5 · bos 5 · water 3 · bodem 5 · mobiliteit 5 · landschap 6 · landbouw 6 · wonen 12 · werken 6 · recreatie 2) · Geo recon: `docs/research/geo-catalog.md` + `poc/data/sources.json` (112 schema-validated service entries) |
| Papers served | A = `extracted/geoai_cop.md` (emergency-management COP) · B = `extracted/udt_genai.md` (GenAI opportunity finding in UDTs; its future-work section explicitly requests this Utrecht pilot) |
| Platform status (v1.4) | **nLDT Phase 5–6 done**: governed agent layer (`nldt/12`), medallion data lake + Data Space publish (`nldt/13`), source monitor (`nldt/17`), DONL CKAN harvest (`nldt/18`). Utrecht engines remain SoT under `poc/`. **Scenario-copilot (world model Renderer layer)** ships for Plane B: `world-scene-spec` contract, `world-scene-build` process, demo [`nldt/simulation/utrecht-whatif-demo.html`](../nldt/simulation/utrecht-whatif-demo.html) — design [`docs/POC_WORLD_MODEL_UTRECHT.md`](POC_WORLD_MODEL_UTRECHT.md). |

---

## 1. Purpose & scope

**Purpose.** Deliver a general, reproducible solutions architecture that answers *"where can I do what?"* (paper B, research question B1) for spatial activities regulated by an Omgevingsverordening, with every legal claim machine-verifiable, traceable and contestable (paper A, challenge A4) — and, since v1.2, answers the follow-up question every policy officer asks next: *"what if the rules change?"* through a **scenario plane** in which open models *propose* what-if variants and deterministic engines *dispose* (execute, validate, narrate under gates). Three tracks were instantiated end-to-end first — **wind** (the first instantiation), **zon** (solar fields) and **bos** (new nature / forest planting) — joined since October 2026 by **water** (riparian development under the watersysteem instructieregels), **bodem** (soil activity under the grondwaterbeschermingszone instructieregels), **mobiliteit** (roadside development under the bereikbaarheid-en-mobiliteit instructieregels), **landschap** (landscape intervention under the cultuurhistorie-en-landschap instructieregels), **landbouw** (agricultural expansion under the landbouw instructieregels), **wonen** (housing development under the wonen instructieregels), **werken** (business development under the werken instructieregels) and **recreatie** (recreation development under the recreatie instructieregels), all differing only in evidence shard, formalizer templates, abstention ledger, zone aliases and use-case file (the *track model*, §3.3); other provinces reuse the whole architecture by re-pointing the corpus and geo registries at their own instruments and services.

**Scope of this document.** Architecture only: views, module boundaries, data plane, contracts, validation, technology, roadmap, risks, traceability. Implementation detail lives in the PoC code under `poc/`; the norm content lives in `docs/research/legal-facts.md`; the service inventory lives in `docs/research/geo-catalog.md`.

**Relation to `MULTI_AGENT_PLAN.md`.** The plan defines the two-plane architecture (planning/operational), the 12-agent roster (§3.2), the validation levels V0–V4 (§4), the six JSON contracts (§5), the technology recommendation (§6) and the phased roadmap (§7). This document binds each of those to concrete Utrecht facts: which instrument version is pinned, which ArcGIS services feed the Geo Analyst, which modules exist in the PoC today, and which parts remain future work.

**Relation to the papers.** Paper A contributes the opportunity-map generator pattern (A1) whose known failure — one agent drowning in hundreds of policy documents — is answered by the plan's fan-out Norm Analyst; the expert-validation role (A4) becomes the V4 HITL checkpoint. Paper B contributes the "where can I do what?" question (B1), the GML-output requirement (B2), the corpus-quality lesson (B4) and the open-source/transparency constraint (B5), and names this exact pilot (Utrecht geodata + Omgevingsvisie; windmill space, solar fields, forest planting, power-net congestion) as its future work.

**Relation to the EU LDT Toolbox — wrap, don't rebuild.** As plan §3.4 states, domain models stay deterministic services that agents call; the multi-agent layer adds legal interpretation, orchestration and validation (catalogue: https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue). This pilot applies the same principle one level down: the **province's existing authoritative services are wrapped, never re-derived** — the vigerende Omgevingsverordening geometry is consumed from the province's own IMOW-referenced FeatureServer, the consolidated legal text from the CVDR, and the planMER constraint layers from the province's ArcGIS Hub. The PoC adds only what those sources lack: formalized rules, zone algebra, validation and provenance.

**Relation to nLDT (v1.4).** Since September 2026 the Utrecht pipeline is one **engine** behind the nLDT front door: OGC API Records / Processes / Recipes, LangGraph orchestrator, MCP tools, Critic/HITL/PROV, and a medallion data lake with European Data Space offers (`nldt/`). Sibling engines (Breda five-value scan, Rijnland peilen, Eindhoven bp2op) share the same gates. This document remains the **Utrecht solutions architecture**; the platform hub is [`nldt/00-architecture.md`](../nldt/00-architecture.md). Doctrine is unchanged: *AI proposes · pipeline disposes · human decides* ([`docs/GENAI_SEAMS.md`](GENAI_SEAMS.md)).

---

## 2. Stakeholders and use cases

**Primary question (planning plane).** *"Where in province Utrecht can activity X be realised, under which provincial rules, and why?"* — answered per track as a deterministic, fully-cited zone computation, not a generative guess.

| Track | objectType | Core zone semantics (canonical runs 2026-08-30; water/bodem 2026-10-04; mobiliteit/landschap/landbouw/wonen 2026-10-05; werken/recreatie 2026-10-06) |
|---|---|---|
| wind | `wind_turbine` | union of the three formalized inclusion zones ∩ AOI 1259.8 km², minus Natura 2000 + ganzenrust (toelichting art. 5.4) and Natuurnetwerk Nederland (art. 6.3) → **859.5 km²**; stiltegebied/NNN conditional, 1500 m attention, Groene contour compensation markers |
| zon | `solar_field` | `Gebied zonneveld` (art. 5.5) ∩ AOI 1167.9 km², minus Natura 2000 + ganzenrust (toelichting art. 5.5) → **1167.9 km²**; Groene contour compensation marker with the ≤25-jaar deadline of art. 6.5a lid 3 |
| bos | `forest_planting` | the Groene contour **zoekgebied nieuwe natuur** (art. 6.4) ∩ AOI = **23.9 km²**, no exclusions (a search area); ≥1:1 compensation ratio (art. 6.5 lid 2 onder d) and oude bosgroeiplaatsen (art. 6.13) as marker/conditional overlays |
| water | `riparian_development` | provincie minus waterbergingsgebied (art. 2.15, 5.148 km²) → **1554.906 km²** (AOI 1560.054 km²); vrijwaringszone waterkering (art. 2.14, 28.011 km²) and overstroombaar gebied (art. 2.16, 1207.173 km²) as conditional markers (V3 IoU 0.999996) |
| bodem | `soil_activity` | provincie minus grondwaterbeschermingszone umbrella (art. 3.7 + art. 3.9 executed as exclusions, 701.126 km² in-AOI; conservative superset of the literal designation areas) → **858.927 km²** (AOI 1560.054 km²); art. 3.10 ('rekening houden met') stays a conditional marker and gesloten stortplaats (art. 3.108, 0.373 km²) a context marker; art. 3.8 ambiguous → V4 (V3 IoU 0.999979) |
| mobiliteit | `roadside_development` | **all-marker track**: no H4 rule unconditionally refuses roadside development, so the final zone equals the AOI **1560.054 km²**; five conditional markers — beperkingengebied bouwwerken provinciale weg (art. 4.7, 7.003 km²), geluidcontour buiten/binnen bebouwde kom (art. 4.71 dB Lden thresholds, 37.285 km²), beperkingengebied lokale spoorweg (arts. 4.47/4.48 on the live-verified art.-4.46 umbrella, 0.635 km²) and luchtvaartterrein (art. 4.65, 1014.473 km² — activity-scoped aviation verbod, never an elimination) (V3 IoU 0.999997) |
| landschap | `landscape_intervention` | provincie minus Hollandse Waterlinies (art. 7.3) and Neder-Germaanse Limes kernzone (art. 7.3a) — the lid-1b niet-toestaan-form executed as exclusions → **1425.959 km²** (AOI 1560.054 km²); Limes bufferzone (art. 7.4, 100 m²/30 cm vergunningsverbodprescriptie), cultuurhistorische hoofdstructuur (art. 7.9 umbrella, 847.4 km²), Landschap-kernkwaliteiten (art. 7.11a 'onevenredig', 1411.1 km²) and aardkundige waarden (art. 7.12, 99.2 km²) conditional markers (V3 IoU 0.999994) |
| landbouw | `agricultural_expansion` | provincie minus three niet-toestaan-instructieregels with activity classes inside the object type → **2.260 km²** (≈ de kassenconcentraties): Landbouwstabiliseringsgebied (art. 8.3, 246.8 km²), Gebied glastuinbouw niet toegestaan (art. 8.6, 1557.8 km² = de hele provincie minus de kassen) and Gebied beperken bodembewerking (art. 8.7 veen, 192.2 km²); agrarische bedrijven (art. 8.1 mengvorm), landbouwontwikkelingsgebied (art. 8.2 kan-mits 2,5 ha) and concentratiegebied glastuinbouw (art. 8.5 protectief) markers; geitenhouderij (art. 8.4, geen gebiedsaanwijzing) abstained (V3 IoU 0.999889) |
| wonen | `housing_development` | **inclusion composition**: Stedelijk gebied (art. 9.17) ∪ Kernrandzone (art. 9.10) ∪ Gebied uitbreiding woningbouw (arts. 9.14/9.14a/9.15) → **1142.990 km²** (AOI 1560.054 km²) — the operationalization of the art.-9.3 verstedelijkingsverbod's tenzij-structuur (the verbod itself a conditional marker); arts. 9.6/9.12/9.13 kan-mits and 9.27/9.29 stiltegebied (fase-1-aliases hergebruikt) markers; art. 9.8 object-scoped marker; werken/recreatie sinds fase 5 eigen tracks (V3 IoU 0.999973) |
| werken | `business_development` | **inclusion composition**: Gebied uitbreiding bedrijventerrein (art. 9.16, 703.4 km²) ∪ Stedelijk gebied (art. 9.18) → **1017.614 km²**; art. 9.20 (detailhandel buiten bestaand winkelgebied, 1550.2 km²) conditional marker after re-adjudication — the verbod is sub-class-scoped (detailhandel only) and an exclusion nullified the 9.16/9.18 openings (consolidated nullification rule); arts. 9.9/9.11 kan-mits and the art.-9.19 kantoren framework (two knooppunten, Reductielocaties, gebiedstransformatie) markers (V3 IoU 0.999959) |
| recreatie | `recreation_development` | **pure inclusion composition**: Gebied bovenlokaal dagrecreatieterrein (art. 9.22, 81.8 km²) ∪ Recreatiezone (art. 9.23, 136.3 km²) → **186.618 km²** — both instructieregels open development explicitly 'In afwijking van Artikel 9.3'; art. 9.23 lid 1 protection and lid 4 integrale visie stay tags (V3 IoU 0.999962) |

| Stakeholder | What they get | Stage |
|---|---|---|
| Provincial policy officer (omgevingsbeleid) | Opportunity map + decision table per track; **scenario copilot** (engine map + Δ km²/IoU after sweep; optional World Labs Marble explore for *hypothetical* variants only, HITL-gated); monitoring drift alerts on re-publication | design → monitoring |
| Municipal planner (omgevingsplan) | Which instructieregels (art. 5.3/5.4, 6.x, 7.x, 9.x) bind a location; what an omgevingsplan must motivate | programming → permission |
| RES / regional energy coordinator | Provincial-scale siting envelope minus hard/complex constraints | design |
| Developer / energy cooperative | Screening map + the exact article quotes behind every excluded area | permission |
| GIS analyst | Schema-validated GeoJSON/GML + reproducible cache | all |
| Citizen (future, V4/Participate) | Contestable, traceable justification per zone | design (HITL / wallet track) |

**Use cases.** Wind, zon, bos, water, bodem, mobiliteit, landschap, landbouw, wonen, werken and recreatie — all eleven implemented end-to-end (canonical runs `poc/runs/20260830T113234Z-wind`, `…T142439Z-zon`, `…T142446Z-bos` (2026-08-30), `poc/runs/20261004T185116Z-water`, `…T185509Z-bodem` (2026-10-04), `poc/runs/20261005T072839Z-mobiliteit`, `…T070621Z-landschap`, `…T094244Z-landbouw`, `…T100258Z-wonen` (2026-10-05) and `poc/runs/20261006T121921Z-werken`, `…T114934Z-recreatie` (2026-10-06), all verdict **pass**; V3 IoU 0.99994 / 0.99998 / 0.9997 / 0.999996 / 0.999979 / 0.999997 / 0.999994 / 0.999889 / 0.999973 / 0.999959 / 0.999962 respectively); power-net congestion — art. 5.10/5.11 energietoets + grid data — is the next track candidate (plan §3.4 EnergyCast role). The operational plane (paper A's VA, plan §3.1 right column) is **future scope** (Phase 3).

**Scenario & cross-track use cases (v1.2).** On top of the three baseline tracks, the scenario plane serves two deliberation questions at the **programming** stage, deterministically:

- *"What if?"* — scenario sweeps mutate the formalized rule set (drop a rule, flip its zoneSemantics, vary a cited buffer distance) under a provenance contract (`baseline | norm_variance | policy_variant | hypothetical`; hypotheticals are stamped **NOT legally grounded**), re-execute the full zone algebra per variant against cached layers, and report deltas/IoU vs. a re-executed control. Scenario authors: deterministic (offline golden set), optional LLM, and **hybrid** (det floor + LLM explorer; nLDT recipe default) — proposals pass the same schema + grounding gates before anything executes (seam S7, `docs/GENAI_SEAMS.md`). Canonical LLM-authored run: `poc/scenario-runs/20260831T175842Z-zon-scen/` (10/10 proposals grounded; the model's narration passed every gate).
- *"Show me the scenario"* (v1.4 **scenario-copilot**) — after a sweep, a **Renderer-facing** `WorldSceneSpec` bundle (`world-scene-specs.json`) references engine GeoJSON (`scenarios/CONTROL.geojson` + per-scenario finals) for Leaflet/Cesium views; structured Marble prompts are derived from `ScenarioReport` rows only (no LLM zone geometry, REQ-05). Generative **World Labs Marble** (Stanford HAI Renderer category; see [`docs/POC_WORLD_MODEL_UTRECHT.md`](POC_WORLD_MODEL_UTRECHT.md)) is enabled **only** for `hypothetical` basis types and only after operator HITL (`hitlApproved` / `MARBLE_HITL_APPROVED`). km², IoU and legal claims never pass through Marble.
- *"Where do the tracks collide?"* — the cross-track overlay re-executes each track's unmutated control and quantifies pairwise conflicts plus claims on shared instrument zones. Canonical finding (`poc/crosstrack-runs/20260831T094204Z-wzb-xtrack/`): **94.7% of the zoekgebied nieuwe natuur is simultaneously open to zonnevelden** — the art.-6.5a-lid-3 compensation duty is the only legal buffer between the two provincial ambitions; wind × zon compete on 845.4 km².

**Policy-cycle stages (plan §4).** Design: ambition/scenario maps (visie-level, non-binding — flagged as such). Programming: opportunity maps from the verordening (this PoC). Permission: per-location rule dossier + V4 signature (HITL / wallet track open). Monitoring: source monitor + re-run V1/V3 on instrument or service refresh — critical because a major verordening amendment is pending (PS 18-11-2026, in werking 01-01-2027, https://zoek.officielebekendmakingen.nl/prb-2026-12.html); ArcGIS + DONL continuity probes ship as `source-monitor-run` ([`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md)).

---

## 3. Architecture views

### 3.1 Context view

```
  ACTORS                          THIS SYSTEM (planning plane PoC)              EXTERNAL SYSTEMS
  ───────                         ────────────────────────────────              ────────────────
  policy officer  ─┐                                                          provincie-utrecht.nl
  municipal        │   request ("where can I do what?")                        ├─ omgevingsvisie/verordening hub
  planner          ├─▶ [ Orchestrator → agents → zones+tables ] ◀─ fetch ─────├─ CVDR consolidated regeling
  developer        │   artifacts (GeoJSON/GML/HTML/PROV)                       │   lokaleregelgeving.overheid.nl/cvdr704250
  GIS analyst     ─┘                                                          ├─ officielebekendmakingen.nl (prb-…)
                                                                             └─ DSO omgevingswet.overheid.nl (key-gated)
                                                                             ArcGIS open data (no keys)
                                                                             ├─ geo-point.provincie-utrecht.nl (Hub)
                                                                             ├─ services.arcgis.com/m4kxECHTi6Dj9hfa (AGOL org)
                                                                             ├─ agrest.geodata-utrecht.nl (IMOW legal FS)
                                                                             └─ geoservices.provincie-utrecht.nl
                                                                             local assets
                                                                             ├─ PostGIS `exposure` (EU Building Database slice)
                                                                             ├─ 3d-viewer/ (CesiumJS + 3D BAG)
                                                                             └─ QGIS 4.2
```

Legal sources are consumed **read-only and version-pinned** (snapshot under `docs/research/sources/`); geo sources are consumed through the query mechanics verified in geo-catalog §1 (AGOL: `f=geojson&outSR=28992`, pagination via `resultOffset`, simplification via `maxAllowableOffset`; agrest: `f=json&returnGeometry=true`, pages of 1000; no WFS/OGC-API anywhere on the stack).

### 3.2 Container view — PoC engine vs. nLDT platform (v1.3)

```
  PoC engine (unchanged SoT)                 nLDT platform (done Phase 5–6)
  ──────────────────────────                 ──────────────────────────────
  ┌ one python3 process ──────────────┐      ┌ AppStore · Cookbook · Cook ─────────────┐
  │ poc/run.py       (CLI orchestrator)       │ catalog_adapter :8083 (OGC Records)     │
  │ poc/pipeline/*.py (agent-stage mods)      │ cookbook :8081 · process_adapter :8082  │
  │  agents·geodata·engine·cartographer       │ LangGraph orchestrator + MCP tools      │
  │  critic·explainer·report·contracts        │ Critic / HITL / PROV (shared schemas)   │
  │  scenarios·scenario_author·crosstrack     └──────────────────────────────────────────┘
  │ stores on disk:                   │              │
  │  poc/corpus/   legal evidence     │              ▼
  │  poc/data/     geo registry+cache │      ┌ Medallion data lake ─────────────────────┐
  │  poc/runs/<id>        artifacts   │      │ bronze · silver · gold · catalog/dcat    │
  │  poc/scenario-runs/<id>  sweeps   │      │ FS or MinIO (NLDT_LAKE_BACKEND)          │
  │  poc/crosstrack-runs/<id> overlays│      │ Iceberg + DuckDB/dbt lakehouse           │
  └ stdlib+geo stack; core offline ───┘      │ lake-publish → ODRL offer → EDC connector│
        ▲ propose-only (temperature 0, gated) └──────────────────────────────────────────┘
        └─ optional local open model (Ollama)         ▲
                                                      │ harvest / monitor
                                      data.overheid.nl CKAN · ArcGIS registries
```

The PoC still collapses MCP into in-process modules with the **same boundaries**
(`pipeline/geodata.py` ↔ registry+cache). Migration path is **done for the
front door**: recipes `utrecht-opportunity-map`, `utrecht-scenario-sweep`,
`utrecht-world-scene`, `utrecht-crosstrack` call the engine via OGC Processes; silver/gold sync into
the lake; publish is gated (`accessClass` + HITL). Detail:
[`nldt/12-governed-agent-layer.md`](../nldt/12-governed-agent-layer.md),
[`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md).

### 3.3 Component view — PoC pipeline (track-generic)

```
 OpportunityMapRequest (poc/schemas/opportunity-map-request.schema.json)
        │
        ▼
 [Intake] normalize: objectType∈{wind_turbine, solar_field, forest_planting,
        │  riparian_development, soil_activity, …},
        │  AoI, policyStage — per-track use case in poc/use-cases/<track>.json
        │  NormCard[] (poc/corpus/evidence-<track>.json, cite-verified recon output)
        ▼
 [Norm Analyst] fan-out over corpus shards (wind|zon|bos|water|bodem|mobiliteit|landschap|landbouw|wonen|werken|recreatie); no-citation → dropped
        │  NormCard[] (norm-card.schema.json)
        ▼
 [Norm Formalizer] NormCards → FormalRule[] (per-track template table in
        │  agents.py: parameter/operator/value/unit/zoneSemantics; JOIN-id zone
        │  keys; untemplated → ambiguous, never guessed)
        ▼                         FormalRule[] (formal-rule.schema.json)
 [Geo Analyst] fetch layers (registry+cache) → make_valid → zone algebra,
        │  per track:  wind: ∪(windenergie ∪ kleine-windturbine ∪ landelijk)
        │                 ∩ AOI − natura2000+ganzenrust − NNN
        │              zon:  ∪(zonneveld) ∩ AOI − natura2000+ganzenrust
        │              bos:  ∪(groene contour) ∩ AOI   (zoekgebied, no exclusions)
        ▼                         ZoneResult[] (zone-result.schema.json)
 [Cartographer] style + serialize GeoJSON (EPSG:28992+4326) / GML3.2 / HTML index
        │
        ▼
 [Critic/Validator] V0 schema · V1 geometry · V2 legal grounding · V3 re-execution
        │  loop ≤2 repairs, else reject            ValidationReport (…report.schema.json)
        ▼
 [Explainer] DecisionTable (every row → NormCard) + PROV bundle + run manifest
                                DecisionTable (decision-table.schema.json) → poc/runs/<id>/
```

**Track model.** A track is pure configuration over a fixed spine — no pipeline
code branches on the track beyond a registry lookup. `run.py::TRACKS` binds, per
track: the evidence shard, the cite-or-abstain ledger, report title /
decision-table id / PROV namespace, the headline semantics note and
track-specific limitations; `agents.py` carries the per-card enrichment and
formalizer templates (keyed by evidence id; cards without a template are flagged
ambiguous, never guessed); `run.py::ZONE_SOURCES` maps zone keys to registry
aliases. Adding a track = new use-case file + evidence shard + templates +
ledger + zone aliases (recipe in `poc/README.md`); agent roster, contracts,
validation levels and artifacts are unchanged.

### 3.4 Scenario plane & cross-track overlay (v1.2)

```
  canonical baseline run poc/runs/<id>/  (validated artifacts, cached layers)
         │
         ▼
  [ScenarioAuthor] ─── propose-only ────  optional local open model (S7)
         │  auto (det) | llm | hybrid (det floor + LLM explorer; nLDT default)
         │  ScenarioSpec[] — every spec schema-validated; every ruleId/normCardId
         │  resolved against the baseline; identity stamped by the seam
         │  ("llm-proposal#<model-slug>", never by the model); rejects →
         │  proposals-rejected.json ledger (schema-invalid / unknown ids /
         │  duplicates / object-type mismatch / budget cuts)
         ▼
  [Scenario Sweep] deterministic engine re-executes control + variants
         │  mutations limited to drop | set_semantics | set_buffer_distance_m
         │  on status=formalized rules; provenance basis contract
         │  (baseline | norm_variance | policy_variant | hypothetical)
         ▼                         ScenarioReport (scenario-report.schema.json)
  [Narrator] deterministic OR open model (S8) — gated prose:
         │  every number resolves to the report (sign-fold for magnitudes),
         │  every SC-/FR-/NC- id exists, verdict assertions must agree with
         │  the report; rejection → loud deterministic fallback + ledger
         ▼                         scenario-narrative.md (+ narrative-rejected.md)
  [WorldSceneBuild] (v1.4, optional) `poc/pipeline/world_scene.py` + process
         │  `world-scene-build` — Renderer view contract only; reads ScenarioReport
         │  + per-scenario GeoJSON paths; emits world-scene-specs.json (+ PROV entity)
         │  Marble explore URL: hypothetical + HITL only; engine stamp otherwise
         ▼                         WorldSceneSpec[] (world-scene-spec.schema.json)
  [ScenarioCopilot UI] `nldt/simulation/utrecht-whatif-demo.html` — Leaflet engine
         │  view (control vs variant, Δ from report); Marble button when gated
  [CrossTrack] (poc/pipeline/crosstrack.py) re-executes every track's control
         │  and overlays finals: pairwise conflicts + shared-zone claims
         ▼                         crosstrack-report.schema.json
```

The invariant across all three extensions: **models propose, deterministic
engines dispose** (`docs/GENAI_SEAMS.md` S1–S9, SM, L6, DONL; S7/S8
implemented and verified against a live qwen3.8 — findings and gate lessons
in its technical annex). Nothing a model emits reaches a zone computation,
an artifact or the prose without a deterministic gate deciding first.

---

## 4. Agent roster → PoC modules (plan §3.2 → files)

Actual layout of the implemented PoC (paths below exist under `poc/`); the schema pack lives in `poc/schemas/`.

| # | Agent (plan §3.2) | PoC module | Deterministic implementation now | LLM hook later |
|---|---|---|---|---|
| 1 | Orchestrator | `poc/run.py` | CLI graph runner: fixed node order, run-id, effort manifest, refuses to emit artifacts without a ValidationReport | plan decomposition |
| 2 | Intake | `poc/run.py` (`load_request`) | request loading + schema validation (objectType map, AoI = province boundary embedded in `poc/use-cases/{wind,zon,bos}.json` from `Provinciegrens_Utrecht/FeatureServer/0`) | clarifying dialogue |
| 3 | Norm Analyst ×N | `poc/pipeline/agents.py` (`NormAnalyst`) | reads `poc/corpus/evidence-{wind,zon,bos}.json`; every card resolves `sourceId` → `poc/corpus/sources.json`; emits NormCards with per-track `objectType`; optional `llm_hook` callable parameter | **implemented (S1)**: claim/confidence refinement via `poc/pipeline/norm_llm.py` (`--norm-analyst llm`), gated + ledgered, identity-stamped |
| 4 | Norm Formalizer | `poc/pipeline/agents.py` (`NormFormalizer`) | curated per-track NormCard→FormalRule template table (wind 9 formalized/13 ambiguous/2 rejected; zon 3/0/2 — e.g. art. 5.5→inclusion `Gebied zonneveld`, art. 6.5a lid 3→≤25-jaar compensation; bos 3/1/1 — e.g. art. 6.4→inclusion `Groene contour`, art. 6.15 velling thresholds deliberately procedural→V4) | **implemented (S2)**: gated proposals for *template-less* ambiguous cards (`--formalizer llm`); zone grounding + quote-numeral grounding; curated abstentions never re-proposed |
| 5 | Geo Analyst | `poc/pipeline/geodata.py` + `poc/pipeline/engine.py` | ArcGIS REST fetcher (registry-driven, cache-first), shapely zone engine, make_valid, PROV per op | query planning |
| 6 | Cartographer | `poc/pipeline/cartographer.py` | GeoJSON/GML writer (ogr2ogr), QGIS-loadable outputs | cartographic design |
| 7 | Critic/Validator | `poc/pipeline/critic.py` | V0–V3 checks of §7 below; evaluator–optimizer loop ≤2 | quote-entailment judge |
| 8 | Explainer | `poc/pipeline/explainer.py` | decision table, PROV-O-flavoured JSON bundle, entity hashing | NL justification |
| 8b | Scenario Author (seam S7) | `poc/pipeline/scenario_author.py` | `DeterministicScenarioAuthor` + `LLMScenarioAuthor` + **`HybridScenarioAuthor`** (det floor + LLM explorer; nLDT default); alias normalization; schema-gated | — (this *is* the LLM leg; propose-only) |
| 8c | Scenario Sweep + Narrator (seam S8) | `poc/pipeline/scenarios.py` | re-executes control + variants through the same engine; `check_narrative_grounding` gates prose on numbers (sign-fold), ids and verdict assertions; deterministic narrator grounded by construction; `run_scenario_set` narrates only after the final verdict exists | narration via local open model, same gate, loud fallback (`narrative-rejected.md`) |
| 8d | World scene / scenario-copilot (Renderer) | `poc/pipeline/world_scene.py`; nldt `marble_client.py`; MCP `build_world_scene` | deterministic `ScenarioReport` → `WorldSceneSpec[]`; geoLayerRefs point at engine GeoJSON only; Marble URL spike (explore link, not zone algebra); **does not** import into `engine.py` / `critic.py` | — (Marble is optional human-triggered explore; not an agent seam) |
| 8e | Cross-Track Orchestrator | `poc/pipeline/crosstrack.py` | control re-execution per track (V3 reproduction gate), pairwise conflict + shared-zone overlay, markdown report; V2 not-applicable by design (no legal claim mutated); canonical finding: zon × bos 94.7% of the zoekgebied | — (deterministic by design; no seam) |
| 8f | Water track (verordening-uitbreiding fase 1) | `poc/pipeline/agents.py` (WA-01…03 enrichment + formalizer templates) · `run.py::TRACKS["water"]` · `poc/corpus/evidence-water.json` | arts. 2.14–2.16 instructieregels formalized (3/3 rules executed): `waterbergingsgebied` hard exclusion (art. 2.15), vrijwaringszone waterkering (2.14) and overstroombaar gebied (2.16) conditional markers; omgevingswaarden (arts. 2.2–2.11) abstained as monitoring norms; canonical run `poc/runs/20261004T185116Z-water` (pass, V3 IoU 0.999996 after the engine V3-seeding fix) | — (deterministic track configuration; no seam) |
| 8g | Bodem track (verordening-uitbreiding fase 1) | `poc/pipeline/agents.py` (BO-01…05 enrichment + formalizer templates) · `run.py::TRACKS["bodem"]` · `poc/corpus/evidence-bodem.json` | art. 3.7 ('laat geen activiteiten toe') and art. 3.9 (verbod new burial facilities) executed as hard exclusions on the shared grondwaterbeschermingszone umbrella (701.126 km² in-AOI, conservative superset) since the engine V3-seeding fix; art. 3.10 ('rekening houden met') deliberately a conditional marker (weakest take-into-account variant, V4); gesloten stortplaats (art. 3.108) context marker; art. 3.8 ambiguous → V4 (4/5 rules executed); canonical run `poc/runs/20261004T185509Z-bodem` (pass, final 858.927 km², V3 IoU 0.999979) | — (deterministic track configuration; no seam) |
| 8h | Mobiliteit track (verordening-uitbreiding fase 2) | `poc/pipeline/agents.py` (MO-01…05 enrichment + formalizer templates) · `run.py::TRACKS["mobiliteit"]` · `poc/corpus/evidence-mobiliteit.json` | **all-marker formalization**: arts. 4.7 and 4.47 kan-mits instructieregels, arts. 4.48/4.71 dB Lden-threshold rules and art. 4.65 (Luchtvaartterrein) — an unconditional verbod but activity-scoped to aviation (nieuwvestiging luchtvaartterrein voor gemotoriseerde luchtvaartuigen), which sits outside the roadside_development object type, so all five are conditional markers and the final zone equals the AOI; the spoorweg alias is the live-verified art.-4.46 umbrella (Kernzone ∪ Beschermingszone, symdiff 0.0000 km²); vergunnings-/meldingsketens and the [Gereserveerd] basisnet articles abstained; canonical run `poc/runs/20261005T072839Z-mobiliteit` (pass, final = AOI 1560.054 km², V3 IoU 0.999997) | — (deterministic track configuration; no seam) |
| 8i | Landschap track (verordening-uitbreiding fase 2) | `poc/pipeline/agents.py` (LS-01…06 enrichment + formalizer templates) · `run.py::TRACKS["landschap"]` · `poc/corpus/evidence-landschap.json` | arts. 7.3/7.3a lid-1b niet-toestaan-form executed as hard exclusions on the Hollandse Waterlinies (134.092 km²) and Neder-Germaanse Limes kernzone (0.013 km²) with the aantasten-toets routed to V4 (BO-01 idiom — the activity scope sits inside landscape_intervention, the exact mirror of the MO-05 decision); art. 7.4 (100 m²/30 cm vergunningsverbodprescriptie), art. 7.9 (CHS umbrella of the five art.-7.8 gebieden, live-verified symdiff 0.000004 km²), art. 7.11a ('onevenredig' on the Landschap umbrella of the five art.-7.11 landschappen, symdiff 0.0000 km²) and art. 7.12 conditional markers; the 7.10 verstedelijkingsgateway and the borden-activiteitenketen (7.13–7.17) motivatedly abstained; canonical run `poc/runs/20261005T070621Z-landschap` (pass, final 1425.959 km², V3 IoU 0.999994) | — (deterministic track configuration; no seam) |
| 8j | Landbouw track (verordening-uitbreiding fase 3) | `poc/pipeline/agents.py` (LB-01…06 enrichment + formalizer templates) · `run.py::TRACKS["landbouw"]` · `poc/corpus/evidence-landbouw.json` | arts. 8.3/8.6/8.7 niet-toestaan-instructieregels with refused activity classes inside agricultural_expansion executed as hard exclusions (Landbouwstabiliseringsgebied 246.8 km², Gebied glastuinbouw niet toegestaan 1557.8 km² — the whole province minus the kassenconcentraties, Gebied beperken bodembewerking veen 192.2 km²) → final 2.260 km² (≈ de kassenconcentraties, legally exact); arts. 8.1 (mengvorm verbod+voorschrift), 8.2 (kan-mits 2,5 ha) and 8.5 (protective anti-hindrance) conditional markers; art. 8.4 geitenhouderij (province-wide verbod, no gebiedsaanwijzing) abstained (ALB-01); required an engine payload-repair fallback (buffer0 after linework make_valid refusal on rounded-degenerate multipolygons — regression-tested on the exact 37-part kassen-sliver fixture); canonical run `poc/runs/20261005T094244Z-landbouw` (pass, V3 IoU 0.999889) | — (deterministic track configuration; no seam) |
| 8k | Wonen track (verordening-uitbreiding fase 3) | `poc/pipeline/agents.py` (WN-01…12 enrichment + formalizer templates) · `run.py::TRACKS["wonen"]` · `poc/corpus/evidence-wonen.json` | **inclusion composition**: Stedelijk gebied (9.17), Kernrandzone (9.10) and the Gebied uitbreiding woningbouw (9.14/9.14a/9.15) as INCLUSION zones — the operationalization of the art.-9.3 verstedelijkingsverbod's verordening-brede tenzij-structuur (the verbod itself a conditional marker: an exclusion would erase the exception zones, engine applies inclusion-then-exclusion); art. 9.8 re-adjudicated at the canonical run as an OBJECT-scoped verbod (omvorming van bestaande recreatiewoningen; designation = 1245.8 km² landelijk-gebied extent) — conditional marker, not an exclusion; arts. 9.6/9.12/9.13 kan-mits and 9.27/9.29 stiltegebied (fase-1-aliases hergebruikt) markers; werken/recreatie (9.16-9.23), [Gereserveerde] 9.21 and the 9.7 enclaves-gap abstained with heroverwegingsnotities (AWN-03/04/06/07/10/11); canonical run `poc/runs/20261005T100258Z-wonen` (pass, final 1142.990 km², V3 IoU 0.999973) | — (deterministic track configuration; no seam) |
| 8l | Werken track (verordening-uitbreiding fase 5) | `poc/pipeline/agents.py` (WE-01…06 enrichment + formalizer templates) · `run.py::TRACKS["werken"]` · `poc/corpus/evidence-werken.json` | **inclusion composition**: art. 9.16 (bedrijventerrein-uitbreidingsgebied) and art. 9.18 (Stedelijk gebied, fase-3-alias hergebruikt) as INCLUSION zones → final 1017.614 km²; art. 9.20 (detailhandel buiten bestaand winkelgebied, 1550.2 km²) first executed as an exclusion but re-adjudicated at the canonical run — the verbod is SUB-CLASS-scoped (detailhandel only) and the area exclusion nullified the 9.16/9.18 openings (final collapsed to 9.830 km²): conditional marker, consolidated nullification rule (WN-03-idiom); arts. 9.9/9.11 kan-mits markers and the art.-9.19 kantoren framework (two knooppunten, Reductielocaties tot 2029, gebiedstransformatie; the zone-loze lid-1-2 restriction in the tags per the 8.4-precedent); objectType enum extended in BOTH artifact schemas (norm-card appliesTo + formal-rule appliesTo); canonical run `poc/runs/20261006T121921Z-werken` (pass, V3 IoU 0.999959) | — (deterministic track configuration; no seam) |
| 8m | Recreatie track (verordening-uitbreiding fase 5) | `poc/pipeline/agents.py` (RC-01…02 enrichment + formalizer templates) · `run.py::TRACKS["recreatie"]` · `poc/corpus/evidence-recreatie.json` | **pure inclusion composition**: art. 9.22 (Gebied bovenlokaal dagrecreatieterrein) and art. 9.23 (Recreatiezone) — both instructieregels open development explicitly 'In afwijking van Artikel 9.3' → final 186.618 km²; art. 9.23 lid 1 (bescherming bestaande voorzieningen) and lid 4 (integrale visie/beeldkwaliteitsparagraaf) stay tags; no exclusions, no markers; canonical run `poc/runs/20261006T114934Z-recreatie` (pass, V3 IoU 0.999962) | — (deterministic track configuration; no seam) |
| — | (view tier) | `poc/pipeline/report.py` + `pipeline/report_template.html`; `nldt/simulation/` | single-file HTML report per run (Leaflet map + fallback tables) embedded in the run dir; **Utrecht what-if demo** for Plane B copilot; simulation hub replays all PoCs for communication/teaching | — |
| — | (contracts) | `poc/pipeline/contracts.py` + `poc/schemas/*.schema.json` | the six agent-boundary schemas of §6 plus scenario-plane schemas (scenario-spec / scenario-set / scenario-report / crosstrack-report / **world-scene-spec**), validated at every hop | — |

The `llm_hook` of plan §3.2 is implemented as an optional callable parameter (`NormAnalyst(llm_hook=...)` in `poc/pipeline/agents.py`), **no-op default** (the core track pipeline stays fully offline); every agent records whether a hook answered. Since v1.2 the *scenario plane* has a live-model leg behind its own gated seams (S7/S8): a local open model (Ollama `qwen3.8:latest`, temperature 0, `think:false` via the native API, bounded `num_predict`) proposes scenarios and narrates reports — propose-only, schema- and grounding-gated before anything executes or is published. Golden-set regression between the deterministic and LLM authors: `poc/scenarios/compare_authors.py`. Since 2026-09-15 the *norm plane* has its own legs (S1/S2): `poc/run.py --norm-analyst llm --formalizer llm` activates them behind `LDT_NORM_LLM_*` (same transport semantics, extracted into `poc/pipeline/llm_transport.py`); S1 refines only claim/confidence (citations untouchable by construction, `extractedBy` seam-stamped), S2 proposes formalizations only for template-less ambiguous cards with zone-grounding and quote-numeral-grounding gates (`poc/pipeline/norm_llm.py`); any transport failure falls back loudly to the deterministic output, ledgered in `norm-llm-ledger.json`; golden-set regression: `poc/llm/compare_norm_llm.py`.

Operational-plane agents 9–12 (Picture Compiler … VA Critic) are **not implemented**; the plan's roster remains their specification (Phase 3).

---

## 5. Data plane

### 5.1 Verified geo sources (the `ogc` data source)

Machine registry: `poc/data/sources.json` (78 entries, roles `inclusion|exclusion|conditional|context|aoi`). Key services (all verified live 2026-08-30, details in `docs/research/geo-catalog.md`):

| Role | Source | URL |
|---|---|---|
| **Legal inclusion (authoritative)** | Vigerende Omgevingsverordening as IMOW polygons; `WHERE NAAM='Gebied windenergie'` → 44 feats with `LOCATIE_ID` (`nl.imow-pv26.gebied.*`) + AKN `DOCUMENT_URL`; same service: `NAAM='Gebied zonneveld'` → 44 feats (art. 5.5, zon inclusion); `NAAM='Waardevolle Houtopstanden - oude bosgroeiplaatsen'` → 700 feats (art. 6.13, bos conditional; note: the service's `returnCountOnly` ignores `where` — counts are derived by paging) | https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0 |
| Legal inclusion (visie, non-binding) | Omgevingsvisie designation "Ruimte voor windenergie…" (1481.45 km²) | https://agrest.geodata-utrecht.nl/rest/services/Omgevingsvisie/FeatureServer/0 |
| Hard exclusions (planMER, pre-baked buffers 81/92/241/300/400 m) | Natura 2000+81 m (L32), geluidsgevoelige objecten +300/400 m (L23/25), hoogspanningsnet +241 m (L28), ganzenrustgebieden (L16/17), bebouwde kom (L11), bestaande turbines (L13) | https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/Harde_belemmeringen/FeatureServer |
| Complex exclusions | NNN+81 m (L39), weidevogelkerngebied+81 m (L57), stiltegebied (L51), NHW-zonering (L35/36) | https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/Complexe_belemmeringen/FeatureServer |
| V3 benchmark material (not yet wired in) | planMER V1 harde (L1) / complexe (L2) belemmeringen + **Resterende ruimte** (L4) | https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/Onderzoekslocaties_planMER_windenergie/FeatureServer |
| Status/context | ET wind voortgang (44 feats), Kansrijke gebieden (27), turbines in procedure (11) | …/ET_wind_gebieden_windenergie/FeatureServer/13 · …/Kansrijke_gebieden_windenergie/FeatureServer/0 · …/Windturbines_in_procedure/FeatureServer/12 |
| Change detection (2027 drift) | Draft 2e-wijziging wind/zon polygons | …/Omgevingsverordening_aanpassingen_2e_wijziging_WFL1/FeatureServer/59+60 |
| Other constraint layers | stiltegebied_{stillekern,bufferzone,aandachtsgebied}/0, Hollandse_Waterlinie/22+23, NNN_jun2024/0, Natura2000_gebieden/0, ow_bwp_* (grondwater, overstroombaar, aardkundig), stikstof (UPLG ontwerp 83/84/86), Zoekgebied_nieuw_bos_AGO/0 | all under https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/ |
| AOI | Provinciegrens, gemeenten | …/Provinciegrens_Utrecht/FeatureServer/0 · …/Gemeenten_provincie_Utrecht/FeatureServer/0 |
| Discovery | Hub site + search API; internal server | https://geo-point.provincie-utrecht.nl/pages/open-data · https://geo-point.provincie-utrecht.nl/api/v3/search?q=… · https://geoservices.provincie-utrecht.nl/arcgis/rest/services |

(AGOL base = `https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/`, org "utrecht".)

**Authority rules.** The agrest Omgevingsverordening FeatureServer is the only zone source with legal grounding for the track inclusion/overlay zones (IMOW ids + AKN document expression `nld@1089`: Gebied windenergie, Gebied zonneveld, Groene contour, Waardevolle Houtopstanden - oude bosgroeiplaatsen, …); `ET_wind_gebieden_windenergie/13` is an energy-transition **tracking** layer ("meest kansrijke gebieden"), never presented as the juridische werkingsgebied. The 1166.5 km² province-scale polygon in the OV set is a **designation envelope**, not plantable area — zone algebra must intersect it with `Landelijk gebied` and subtract constraints (Norm Analyst reading of art. 5.4 + toelichting, per legal-facts §5.3; the same envelope logic applies to the Gebied zonneveld designation). planMER buffer layers carry **policy-derived distances**, not verordening norms — FormalRules that use them are labelled `derivation: planMER`, distinct from `derivation: legal-text` (e.g. the 1500 m Aandachtsgebied from art. 9.25 lid 2, which is legal-text-derived and deterministic).

### 5.2 Corpus store (legal)

`poc/corpus/sources.json` (23 pinned sources with retrieval dates) + per-track evidence shards `evidence-wind.json` (24), `evidence-zon.json` (5), `evidence-bos.json` (5), `evidence-water.json` (3), `evidence-bodem.json` (5), `evidence-mobiliteit.json` (5), `evidence-landschap.json` (6), `evidence-landbouw.json` (6), `evidence-wonen.json` (12), `evidence-werken.json` (6), `evidence-recreatie.json` (2) — each record with `sourceId`, `instrument` (artikeltekst vs toelichting vs visie kept distinct), verbatim `quote_nl`, `url` — and their deterministic replay outputs `normcards-<track>.json` / `formalrules-<track>.json` (regenerated by `python3 -m pipeline.agents`, unit-tested for replay determinism). Cite-or-abstain ledgers per track: `normcards-rejected.json` (wind, 8 abstentions), `normcards-rejected-zon.json` / `normcards-rejected-bos.json` (6 each — e.g. zon abstains on rooftop solar as outside the object definition; bos on stikstof and Natuurbeheerplan-type selection). Snapshots under `docs/research/sources/` make V2/V3 reproducible after the instrument changes. Pinned instruments: **Omgevingsverordening provincie Utrecht, CVDR704250 geldend 13-10-2025** (https://lokaleregelgeving.overheid.nl/cvdr704250) and **Omgevingsvisie PS 10-03-2021** (https://www.provincie-utrecht.nl/media/8648). The DSO Omgevingsdocumenten Downloaden API — the only official machine channel for GIO geometry — is key-gated (401 verified; register at https://developer.omgevingswet.overheid.nl/api-register/api/omgevingsdocument-downloaden/); until a key exists the agrest IMOW mirror is the GIO proxy with a provenance caveat recorded in every affected ZoneResult.

### 5.3 Cache layout and future stores

```
poc/data/cache/<source-id>.28992.geojson   # normalized EPSG:28992 twin (metric computation)
poc/data/cache/<source-id>.4326.geojson    # WGS84 / RFC 7946 twin (output serialization)
```

Per-fetch provenance (exact query URL+params, `fetchedAt`, featureCount, sha256 of the response, HTTP status) is recorded per layer in each run's `layers.json` manifest (plus the geo-source registry `poc/data/sources.json`); the cache is re-used only when the instrument version pin and the registry entry are unchanged. Scenario-plane artifacts live beside them: `poc/scenario-runs/<id>/` (report+markdown, per-scenario GeoJSON incl. `CONTROL`, optional **`world-scene-specs.json`** for copilot, proposal + rejection ledgers, narrative + rejection ledger, validation, PROV) and `poc/crosstrack-runs/<id>/` (conflicts, shared-zone claims, controls, validation, PROV) — all replayable offline from the cache. Static demo fixture: `poc/scenario-runs/_fixture-zon-scen/` + embedded slice in `nldt/simulation/fixtures/utrecht-whatif-data.json`.

### 5.4 Medallion data lake & Data Space (v1.3)

Utrecht working sets remain the **engine cache**. The nLDT lake is the
**canonical technical store** for sharing, inventory and lakehouse analytics
([`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md)):

| Zone | Meaning for this pilot | Typical keys |
|------|------------------------|--------------|
| **bronze** | Unchanged source snapshots (ArcGIS/PDOK/DONL bytes as received) | `bronze/utrecht/…`, `bronze/donl/…` |
| **silver** | Normalised dual-CRS GeoJSON, `sources.json`, service manifests | `silver/utrecht/layers/…`, `silver/utrecht/meta/…` |
| **gold** | Schema-valid run / scenario / crosstrack artifacts + PROV | `gold/utrecht/{run,scenario,crosstrack}/…` |

**Communication protocol.** Agents and Cook resolve `file://`, `lake://nldt-poc-lake/{key}` or `s3://…` the same way. Discovery uses OGC Records; execution uses OGC Processes; cross-org sharing uses an ODRL offer via the pluggable connector (`mock` \| `edc-manifest` \| `http`) — peers do not get raw MinIO credentials. Default `accessClass` for Utrecht silver/gold is `open`; peilen-class restricted assets (other PoCs) require HITL.

**National discovery.** Curated harvest from [data.overheid.nl](https://data.overheid.nl) (CKAN → DCAT-AP-NL catalog records; downloads vs WFS/WMS as DataService) lands in the same lake ([`nldt/18-donl-harvest.md`](../nldt/18-donl-harvest.md)). DONL is a metadata hub, not a blob store.

**Time-series + discovery search.** Cross-twin silver observations (`silver/timeseries/…`) plus Elasticsearch index `nldt-lake-v1` power MCP `search_lake_elasticsearch` and optional S7 `lakeSeriesHints` (propose-only). Compose: `docker-compose.lake.yml` service `elasticsearch`.

**Continuity.** Source monitor probes ArcGIS registries used by this pilot and DONL `metadata_modified` / resource URLs; patch proposals are never auto-applied ([`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md)).

**Ops.** `scripts/lake_sync.py --poc utrecht` · `build_lake_inventory.py` · optional MinIO (`NLDT_LAKE_BACKEND=s3`) · recipe `lake-publish-offer` for Data Space offers. Future KG/pgvector stores (plan §3.3) remain optional behind MCP; they are not required for the lake path.

---

## 6. Interface contracts (plan §5 → `poc/schemas/`)

All agent boundaries emit JSON validated against JSON Schema (jsonschema 4.25.1); V0 runs at **every** hop, not only at the end.

| Contract | Schema file | Summary (full spec: plan §5) | Utrecht specifics |
|---|---|---|---|
| OpportunityMapRequest | `opportunity-map-request.schema.json` | id, objectType, ambitions, areaOfInterest (GeoJSON+crs), policyStage, effortBudget | `objectType` enum: `wind_turbine`, `solar_field`, `forest_planting`, `biomass_installation`, `energy_storage`; default AoI = provinciegrens; per-track instances `poc/use-cases/{wind,zon,bos}.json` |
| NormCard | `norm-card.schema.json` | claim, source{docId,article,version,quote,uri}, theme, confidence, extractedBy | `article` format `"art. 5.4 lid 1"`; `version` = "CVDR704250 geldend 13-10-2025"; evidence class field (artikeltekst/toelichting/visie) |
| FormalRule | `formal-rule.schema.json` | normCardId, parameter, operator, value, unit, zoneSemantics, appliesTo, executableRef | zone key = Bijlage-II JOIN-id (e.g. `gebied windenergie` → `/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846`) with ArcGIS source id as provenance alias; `derivation: legal-text|planMER|assumption` |
| ZoneResult | `zone-result.schema.json` | ruleIds, geometry{format,payload,crs}, operation, prov | CRS EPSG:28992 canonical; every op logs shapely call + inputs' sha256 |
| ValidationReport | `validation-report.schema.json` | artifactId, levels V0–V4, verdict, evidence, evaluatorRun | V3 records the independent re-execution agreement (IoU + relative area delta, thresholds 0.98 / 1%) |
| DecisionTable | `decision-table.schema.json` | columns + rows, each row ≥1 normCardId | columns include zone effect and evidence class; abstained topics listed explicitly |
| ScenarioSpec | `scenario-spec.schema.json` | id, name, objectType, basis{type, normCardId?, variedAspect?, rationale?, provenanceNote}, mutations[] (drop / set_semantics / set_buffer_distance_m), proposedBy | basis enum `baseline|norm_variance|policy_variant|hypothetical` with per-type required fields; `proposedBy` pattern forces seam-stamped identity (model never names itself); hypotheticals must carry a NOT-legally-grounded provenanceNote |
| ScenarioSet | `scenario-set.schema.json` | scenarios[], control semantics, optional degradations | authored sets in `poc/scenarios/{wind,zon,bos}.json`; auto/llm-authored sets serialized alongside their ledgers |
| ScenarioReport | `scenario-report.schema.json` | per-scenario outcome rows (finalAreaKm2, delta vs control, IoU, status), control reproduction block, verdict | control re-executed from the baseline run's cached layers + recorded tunings; deltas measured against that control, never the baseline summary |
| CrossTrackReport | `crosstrack-report.schema.json` | tracks[], conflicts[] (pair, areaKm2, shareOfTrackFinal, geometryFile), sharedZones[] (per-track claims), verdict | V2 not-applicable by design (no legal claim mutated); V3 reproduction gate per track control |
| WorldSceneSpec | `world-scene-spec.schema.json` | per-scenario Renderer contract: provenanceBasis, headline Δ km², mutationSummary, geoLayerRefs (control + scenario paths), optional marblePrompt / exploreUrl; groundingStamp `engine-only` \| `marble-explore-not-legal` | built only from ScenarioReport rows; Marble enabled when `basis.type=hypothetical` **and** HITL; never feeds V2/V3 |

**Determinism rules (plan §5).** No LLM output mutates rules or the corpus; the deterministic engine is the source of truth; the `llm_hook` interface and, since v1.2, the scenario seams (S7/S8) are the only places where a model may *propose* — never *decide*. Every scenario proposal passes the schema and grounding gates before execution; every narration passes the numeric/id/verdict grounding gates before publication, with a loud deterministic fallback otherwise.

---

## 7. Validation framework (plan §4 → PoC)

Validation is a graph-node class: the Orchestrator refuses any run whose final artifact lacks a passing report.

| Level | PoC implementation (deterministic) | Failure action |
|---|---|---|
| **V0 syntactic** | jsonschema validation of every artifact crossing an agent boundary; GeoJSON structure + CRS member check | auto-repair ≤2, then reject |
| **V1 geometric** | shapely `is_valid` on all inputs and outputs (`make_valid` mandatory — 8/44 ET and 1/44 OV features invalid as served); pyproj CRS equality (28992); area sanity vs. extent; IoU checks between designation pyramid levels (visie ⊃ OV ⊇ ET, geo-catalog §2.1 numbers as fixtures) | reject to Geo Analyst |
| **V2 legal grounding** | cite-or-abstain, implemented at runtime as: every NormCard resolves to `sources.json` and carries docId+article+version+verbatim `quote_nl`+uri (completeness gate); every FormalRule references ≥1 existing NormCard; per-track abstention ledgers (wind: stikstof, general noise dB, tip height, setbacks — national-law domains; zon: national solar-field rules, rooftop solar outside the Bijlage-I object definition, energy test; bos: stikstof, NNN-addition procedure, Natuurbeheerplan type selection — no provincial NormCards issued). Verbatim containment of each `quote_nl` against the snapshot texts (`docs/research/sources/cvdr704250-tekst-extract.txt`, `visie.txt`) was performed at recon time (`docs/research/legal-facts.md` method section) and re-verified against the live sources; runtime re-containment is a Phase-2 hardening item | reject card/rule; log abstention |
| **V3 semantic re-execution** | independent second pass re-computes the zone algebra with a separate implementation (`engine.reexecute_independent`: geopandas `GeoSeries`/`overlay` primitives instead of raw shapely, same FormalRule partition semantics); agreement thresholds IoU ≥ 0.98 and relative area delta ≤ 1%; divergence fails the run (unit-tested with an injected divergent zone) | reject; escalate to human if disagreement persists |
| **V4 human expert** | **pending HITL**: Explainer emits a review bundle (decision table + PROV + map) with `V4: "pending"`; the sign-off queue is the artifact, not a UI yet | annotate → gold-set candidate |

The pluggable judge: the `llm_hook` callable (optional parameter, no-op default in `poc/pipeline/agents.py`) returns `None` today; when an open model is available (Phase 2+) it can supply the quote-entailment rubric check of plan §4 without weakening the deterministic V2 completeness/linkage checks.

**Scenario-plane validation (v1.2).** The same levels, extended to the what-if surface: V0 validates every `ScenarioSpec`/`ScenarioSet`/`ScenarioReport`/`CrossTrackReport` against its schema (LLM proposals included — schema-invalid ones are ledgered, never executed); V2 grounds every mutated `ruleId` against the baseline run's formal rules, every `basis.normCardId` against its norm cards, and gates narrations on numbers (sign-folded for magnitude phrasing), SC-/FR-/NC- ids, and verdict assertions (prose may only use pass/fail words that agree with the report's own verdict — a rule born from a real qwen3.8 fabrication); V3 re-executes the control from cached layers + recorded tunings (rel tolerance 0.001; observed 0.000000 for all tracks) and gates every cross-track control the same way; V4 stays pending by design — scenario choice and cross-track arbitration are human programming-stage decisions, stated in every report.

---

## 8. Technology & deployment

**PoC runtime (verified on this machine, 2026-08-31).** python3 3.13 · shapely 2.1.2 · pyproj 3.7.2 · geopandas 1.1.3 · fiona 1.10.1 · requests 2.33.1 · jinja2 3.1.6 · jsonschema 4.25.1. CLI tools: `ogr2ogr`, `pdftotext` (both `/opt/homebrew/bin`). **No API keys of any kind; the core track pipeline runs fully offline** — every agent is a deterministic implementation behind an interface with an optional `llm_hook`. The scenario plane adds an optional **local open-model leg** (paper B constraint B5): Ollama serving `qwen3.8:latest` (also verified: `qwen3.6:27b-mlx`) via its native `/api/chat` (the OpenAI-compat layer ignores `think:false` and lets reasoning-mode models burn the completion budget), temperature 0, `num_predict` 4096, configured by `LDT_SCENARIO_LLM_ENDPOINT` / `_API` / `_MODEL` / `_TIMEOUT`. Deployment = a workspace directory; runs are files under `poc/runs/<run-id>/`, sweeps under `poc/scenario-runs/`, overlays under `poc/crosstrack-runs/`.

**Target evolution (plan §6) — status v1.3.** Orchestration → **LangGraph done** (`nldt/agents/orchestrator`, checkpointed HITL); tools → **MCP servers done** (`nldt/services/mcp_servers`, poc-mcp); federation → A2A stub done (`nldt/services/a2a`), Participate/Marketplace live endpoints still out of band; models → open-source only (paper B constraint B5), routed behind `llm_hook` / Ollama; observability → OTel API present, OTLP exporter still open; **data plane** → medallion lake + Iceberg/dbt + Data Space connector **done** (`nldt/13`). Module boundaries of §4 still hold: evolution replaces transport, not zone algebra.

---

## 9. Phased roadmap alignment (plan §7 ↔ nLDT)

| Plan / nLDT phase | Status in this pilot |
|---|---|
| **Phase 0** foundations | Largely done: legal corpus pinned + snapshotted (23 sources, 42 evidence records across five tracks); geo services catalogued + schema-validated registry (78); golden-set material identified (planMER resterende ruimte, province focus-group analog); missing: tri-modal bindings, GS-1 formal freeze |
| **Phase 1** single-agent baseline + V0–V3 harness | **Done, ×11 tracks**: full deterministic pipeline (Intake→Explainer) with V0–V3 checks and independent re-execution for wind, zon and bos (all verdict pass; canonical runs 2026-08-30), since the fase-1 verordening-uitbreiding for water and bodem (both verdict pass; canonical runs 2026-10-04; the V3 seeding fix made AOI-seeded exclusions independently verified), since the fase-2 verordening-uitbreiding for mobiliteit and landschap (both verdict pass; canonical runs 2026-10-05), since the fase-3 verordening-uitbreiding for landbouw and wonen (both verdict pass; canonical runs 2026-10-05; the payload-repair fallback made micro-sliver inclusion/exclusion results survivable) and since the fase-5 verordening-uitbreiding for werken and recreatie (both verdict pass; canonical runs 2026-10-06; fase 4 runs parallel on its own branch); planMER `Resterende ruimte` identified as benchmark material but not yet wired in |
| **Phase 1b** scenario plane + GenAI seams | **Done**: deterministic scenario sweeps with provenance-basis contracts (`poc/pipeline/scenarios.py`); seam catalogue S1–S9 / SM / L6 / DONL (`docs/GENAI_SEAMS.md`); S7 author + S8 narrator seams verified against a live local open model (B2: qwen3.8); cross-track conflict overlay; **scenario-copilot (v1.4)**: world-scene-spec + `utrecht-world-scene` recipe + what-if demo |
| **Phase 2** multi-agent orchestration (plan) | **Superseded by nLDT Phase 5 (done 2026-09-15)**: one governed agent layer — Processes + Recipes + MCP + Critic/HITL/PROV for Utrecht/Breda/Rijnland/Eindhoven ([`nldt/12`](../nldt/12-governed-agent-layer.md)). Still open inside seams: S1–S3 on PoC-1 text, S9 Word/PDF on beleidskompas |
| **Phase 3** KG/BNK/VA operational plane | not started (KG/pgvector remain future MCP stores) |
| **Phase 4** 3D / federation (plan) | **Partial**: Web 3D Context + A2A stubs in nLDT ([`nldt/09`](../nldt/09-federation-and-observability.md)); full CityJSON/3D measures still open |
| **nLDT Phase 6** data lake + Data Space | **Done (2026-09-15)**: medallion lake, `lake-publish-offer`, pluggable EDC connector, DuckDB/Iceberg/dbt ([`nldt/13`](../nldt/13-data-lake-and-space.md)); DONL harvest ([`nldt/18`](../nldt/18-donl-harvest.md)); source monitor MVP ([`nldt/17`](../nldt/17-source-monitor.md)). Live EDC management API still out of band |
| **Policy-cycle HITL / wallet** | V4 sign-off queue exists as artifact; eID Wallet mock paths done, real OpenID4VP decision-gated ([`nldt/16`](../nldt/16-eid-wallet-identity.md)) |

**Pilot exit criterion (Phase 1):** opportunity maps for province Utrecht — wind, zon and bos — whose every zone traces to NormCard → CVDR704250 article → geometry service, with V3 agreement recorded per track (IoU 0.99994 / 0.99998 / 0.9997) — the quantified "to what extent" answer paper B asks for, in deterministic form, for three of the four use cases paper B names (congestion remaining). **Platform exit (v1.3):** those maps (and sibling PoC gold) are discoverable as OGC Records with `lakeUri`, publishable as Data Space offers under Critic/HITL, and continuity-monitored against silent registry drift.

---

## 10. Risks & mitigations

| Risk | Mitigation (this architecture) |
|---|---|
| Legal-text drift on re-publication (amendment PS 18-11-2026, in werking 01-01-2027; prb-2026-12) | Corpus pinning + snapshots; `2e_wijziging_WFL1` draft polygons as change-detection feed; re-run recon + V1/V3 monitoring checks before the date; version field on every NormCard |
| Data staleness / silent service updates | fetch manifests with sha256 + timestamps; cache invalidated only by explicit re-fetch; `lastChecked` surfaced in ZoneResult provenance; **source monitor** diffs ArcGIS feature counts / `maxRecordCount` / fields and DONL `metadata_modified` + resource URLs — human merges registry patches (V4), never auto-applied (`nldt/17`) |
| ArcGIS service churn (deleted `Natura2000_gebieden_buffers_1__3__5_km`, duplicate republishes, truncated names — all observed) | registry-driven fetching with role metadata; duplicates flagged in geo-catalog §2.3 and never registered twice; probes re-runnable (`poc/data/probe_services.py`); watchlist-driven `source-monitor-probe` |
| Norm hallucination | cite-or-abstain at V2 (quote containment vs. snapshot); abstention register; `derivation` labels separating legal-text, planMER and assumption parameters. **Empirically exercised (v1.2)**: the scenario gates caught a real model drift set — hallucinated scenario id, truncated/mismatched numbers, a fabricated verdict claim and a quoted placeholder verdict — each rejection ledgered with deterministic fallback (`docs/GENAI_SEAMS.md` §5); the gates, not the model's good behaviour, are the mitigation |
| Generative world model *visual plausibility trap* (Stanford HAI 2026) | Renderer output (World Labs Marble) is **never** a zone source: engine GeoJSON + ScenarioReport metrics are the only map truth; Marble gated to hypothetical + HITL; `groundingStamp` and demo watermarks; see [`docs/POC_WORLD_MODEL_UTRECHT.md`](POC_WORLD_MODEL_UTRECHT.md). Physical dynamics annex (SRM-2) remains a separate explicit Simulator path via Urban Strategy ([`docs/POC_URBANSTRATEGY_INTEGRATION.md`](POC_URBANSTRATEGY_INTEGRATION.md)) |
| GIO geometry indirection (DSO API 401) | agrest IMOW mirror as proxy with recorded caveat; apply for DSO key as roadmap item; JOIN-id remains the canonical zone key either way |
| Designation-envelope misreading (1166.5 km² polygon) | envelope semantics enforced in FormalRules (intersect `Landelijk gebied`, subtract constraints); flagged in geo-catalog and legal-facts hand-over |
| Geometry defects as served | `make_valid` mandatory, V1 gate, ring-orientation-adaptive conversion for agrest esri-JSON |
| Large-response truncation on agrest (≳20 MB observed) | where-subsets + pagination + per-page feature-count verification |
| Cost/complexity blow-up in future fan-out | effort budget in OpportunityMapRequest; Orchestrator refuses unbounded plans (plan §3.2 guardrail) |
| Over-publishing restricted lake assets | `accessClass` + `lake-deny.json`; `lake-publish-dataset` refuses `restricted` without HITL; ODRL offer Critic V0/V2/V4 (`nldt/13`) |
| Blind national open-data mirror | DONL harvest is curated watchlist + metadata-first; WFS/WMS registered as DataService, not dumped (`nldt/18`) |

---

## 11. Traceability matrix (paper goal → plan technique → this architecture)

Extends plan §8 with the PoC column.

| Paper goal | Plan technique (§2/§8) | Component in this architecture |
|---|---|---|
| A1 comprehensive norm derivation | orchestrator–worker fan-out + map-reduce | `pipeline/agents.py (NormAnalyst)` over sharded `poc/corpus/evidence-*.json`; LLM fan-out later behind `llm_hook` |
| A1 zone elimination → map | deterministic spatial ops via tools | `pipeline/geodata.py` + `pipeline/engine.py` shapely overlay over agrest OV + Harde/Complexe layers; `pipeline/cartographer.py` outputs |
| A2 3D measures | 3D Tiles/CityJSON tooling | future Phase 4; `3d-viewer/` as front-end seed |
| A3 BNK interpretation | hybrid KG+vector | future Phase 3 (`kg-mcp` seam: `poc/corpus` → RDF) |
| A3 situational picture <60 s | latency-bounded swarm | out of PoC scope |
| A4 generalizable validation | evaluator–optimizer, re-execution, PROV | `critic.py` V0–V3 (§7) + PROV bundle in every `poc/runs/<id>` |
| A4 policy-cycle integral | graph stage hooks | `policyStage` in the request contract; monitoring drift design (§10) |
| A4 Skills feedback loop | Agent Skills export | Explainer emits Skill-shaped bundle in Phase 2 |
| B1 "where can I do what?" | agentic RAG + formalization | the whole PoC pipeline (§3.3), deterministic first |
| B2 GML generation | constrained outputs → GML | `cartographer.py` GML 3.2 writer + V0/V1 gates |
| B3 tri-modal binding | co-embeddings + link records | future Phase 0 completion (binding-record schema reserved) |
| B4 corpus quality | cleaning + versioning | pinned corpus + snapshots + evidence classes (`docs/research/sources/`) |
| B5 explainability/contestability | decision tables, PROV, citations | `explainer.py`; every row → NormCard; abstention register |
| B pilot (Utrecht, wind/bos/zon) | — | this pilot: wind, zon and bos end-to-end on one pipeline (canonical runs 2026-08-30, all pass) |
| B1+ "what if the rules change?" | scenario planning behind gated seams | scenario plane (§3.4): deterministic sweeps + provenance-basis contracts; open-model author/narrator (S7/S8) propose-only, schema+grounding gated, verified live on qwen3.8 |
| B1++ "help me see the scenario" | spatial intelligence / world model (Renderer) | scenario-copilot (v1.4): `WorldSceneSpec` + Leaflet demo + optional Marble explore; Simulator stays `engine.py`; governance per HAI brief ([`docs/POC_WORLD_MODEL_UTRECHT.md`](POC_WORLD_MODEL_UTRECHT.md)) |
| B1+ "where do ambitions collide?" | deterministic overlay over re-executed controls | cross-track conflict engine (`poc/pipeline/crosstrack.py`): pairwise + shared-zone claims; canonical finding zon × bos 94.7% |
| B congestion use case | EnergyCast as MCP tool | art. 5.10/5.11 energietoets formalized as non-spatial condition; grid model Phase 4/5 |
| A4 FAIR cross-org sharing | data space + identities | **Done (nLDT Phase 6)** — medallion lake + Data Space participant (`nldt/13`); ODRL offers + pluggable EDC connector (`mock`/`edc-manifest`/`http`); live EDC management API out of band; DONL as national discovery (`nldt/18`) |
| B5 citizen contestability | eParticipation for V4 | V4 review bundle designed as the contestation artifact; wallet-anchored executor/approver claims when wallet mode is on (`nldt/16`) |
| Data continuity (ops) | monitoring swarm | Source monitor MVP (`nldt/17`) — ArcGIS + DONL probes, human-merge patches |

---

*Maintained alongside `MULTI_AGENT_PLAN.md`, `docs/GENAI_SEAMS.md`, `docs/POC_WORLD_MODEL_UTRECHT.md` and `nldt/00-architecture.md`. Facts current as of **2026-09-29** (v1.4: scenario-copilot / world-scene layer on Plane B). The instrument pin (CVDR704250 geldend 13-10-2025) must be re-verified before 18-11-2026.*
