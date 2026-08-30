# Solutions Architecture — Multi-Agent Opportunity Mapping ("Where can I do what?")

| | |
|---|---|
| Document | `docs/SOLUTIONS_ARCHITECTURE.md` · v1.0 · **2026-08-30** |
| Specializes | `MULTI_AGENT_PLAN.md` v1.2 (§3–§8). That plan is the general spec; this document specializes it for the Utrecht pilot **and fixes the concrete module/data/contract layout** any such pilot follows. It does not repeat the plan — section numbers below link back to it. |
| Pilot instance | Wind turbines (`objectType: windmill ≥3 MW` and `kleine windturbine ≤20/30 m`), province Utrecht (NL) |
| Grounding inputs | Legal recon: `docs/research/legal-facts.md` + `poc/corpus/*.json` (23 sources, 34 cite-verified evidence records) · Geo recon: `docs/research/geo-catalog.md` + `poc/data/sources.json` (71 schema-validated service entries) |
| Papers served | A = `extracted/geoai_cop.md` (emergency-management COP) · B = `extracted/udt_genai.md` (GenAI opportunity finding in UDTs; its future-work section explicitly requests this Utrecht pilot) |

---

## 1. Purpose & scope

**Purpose.** Deliver a general, reproducible solutions architecture that answers *"where can I do what?"* (paper B, research question B1) for spatial activities regulated by an Omgevingsverordening, with every legal claim machine-verifiable, traceable and contestable (paper A, challenge A4). The Utrecht wind-turbine PoC is the **first instantiation**; bos (forest planting) and zon (solar fields) reuse the same pipeline over different evidence corpora and rule sets, and other provinces reuse it by re-pointing the corpus and geo registries at their own instruments and services.

**Scope of this document.** Architecture only: views, module boundaries, data plane, contracts, validation, technology, roadmap, risks, traceability. Implementation detail lives in the PoC code under `poc/`; the norm content lives in `docs/research/legal-facts.md`; the service inventory lives in `docs/research/geo-catalog.md`.

**Relation to `MULTI_AGENT_PLAN.md`.** The plan defines the two-plane architecture (planning/operational), the 12-agent roster (§3.2), the validation levels V0–V4 (§4), the six JSON contracts (§5), the technology recommendation (§6) and the phased roadmap (§7). This document binds each of those to concrete Utrecht facts: which instrument version is pinned, which ArcGIS services feed the Geo Analyst, which modules exist in the PoC today, and which parts remain future work.

**Relation to the papers.** Paper A contributes the opportunity-map generator pattern (A1) whose known failure — one agent drowning in hundreds of policy documents — is answered by the plan's fan-out Norm Analyst; the expert-validation role (A4) becomes the V4 HITL checkpoint. Paper B contributes the "where can I do what?" question (B1), the GML-output requirement (B2), the corpus-quality lesson (B4) and the open-source/transparency constraint (B5), and names this exact pilot (Utrecht geodata + Omgevingsvisie; windmill space, solar fields, forest planting, power-net congestion) as its future work.

**Relation to the EU LDT Toolbox — wrap, don't rebuild.** As plan §3.4 states, domain models stay deterministic services that agents call; the multi-agent layer adds legal interpretation, orchestration and validation (catalogue: https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue). This pilot applies the same principle one level down: the **province's existing authoritative services are wrapped, never re-derived** — the vigerende Omgevingsverordening geometry is consumed from the province's own IMOW-referenced FeatureServer, the consolidated legal text from the CVDR, and the planMER constraint layers from the province's ArcGIS Hub. The PoC adds only what those sources lack: formalized rules, zone algebra, validation and provenance.

---

## 2. Stakeholders and use cases

**Primary question (planning plane).** *"Where in province Utrecht can wind turbines be sited, under which provincial rules, and why?"* — answered as a deterministic, fully-cited zone computation, not a generative guess.

| Stakeholder | What they get | Stage |
|---|---|---|
| Provincial policy officer (omgevingsbeleid) | Opportunity map + decision table for `Gebied windenergie` vs. constraint zones; monitoring drift alerts on re-publication | design → monitoring |
| Municipal planner (omgevingsplan) | Which instructieregels (art. 5.3/5.4, 6.x, 7.x, 9.x) bind a location; what an omgevingsplan must motivate | programming → permission |
| RES / regional energy coordinator | Provincial-scale siting envelope minus hard/complex constraints | design |
| Developer / energy cooperative | Screening map + the exact article quotes behind every excluded area | permission |
| GIS analyst | Schema-validated GeoJSON/GML + reproducible cache | all |
| Citizen (future, V4/Participate) | Contestable, traceable justification per zone | design (Phase 5) |

**Use cases.** Wind (this PoC); bos — `Zoekgebied_nieuw_bos_AGO` + Groene contour rules (art. 6.4/6.5, evidence `poc/corpus/evidence-bos.json`); zon — `Gebied zonneveld` (art. 5.5, `evidence-zon.json`); power-net congestion — art. 5.10/5.11 energietoets + grid data (future, plan §3.4 EnergyCast role). The operational plane (paper A's VA, plan §3.1 right column) is **future scope** (Phase 3).

**Policy-cycle stages (plan §4).** Design: ambition/scenario maps (visie-level, non-binding — flagged as such). Programming: opportunity maps from the verordening (this PoC). Permission: per-location rule dossier + V4 signature (Phase 5). Monitoring: re-run V1/V3 on instrument or service refresh — critical because a major verordening amendment is pending (PS 18-11-2026, in werking 01-01-2027, https://zoek.officielebekendmakingen.nl/prb-2026-12.html).

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

### 3.2 Container view — PoC now vs. target

```
  PoC (now)                                    Target (plan §3.3/§6)
  ─────────                                    ─────────────────────
  ┌ one python3 process ──────────────┐        ┌ orchestrator graph (LangGraph 1.0, checkpointed,
  │ poc/run.py       (CLI orchestrator)         HITL interrupts; N8N as ops trigger)
  │ poc/pipeline/*.py (agent-stage mods)        ┌ MCP tool servers ──────────────────────────┐
  │  agents·geodata·engine·cartographer        │ postgis-mcp · ogc/qgis-mcp · bag3d-mcp ·  │
  │  critic·explainer·report·contracts         │ docstore-mcp (corpus+pgvector) · kg-mcp    │
  │ stores on disk:                   │   ──▶  │ rule-engine-mcp · artifact/trace stores    │
  │  poc/corpus/   legal evidence     │        └────────────────────────────────────────────┘
  │  poc/data/     geo registry+cache │        vector index (tri-modal, B3) · KG (RDF/SHACL)
  │  poc/runs/<id> artifacts+PROV     │        EU LDT Integrated Environment (deployment shell)
  │  poc/schemas/  contract pack      │        open-source models (B5) behind llm_hook
  └ stdlib+geo stack, no LLM ─────────┘
```

The PoC deliberately collapses the target's MCP servers into in-process modules with the **same boundaries**: `pipeline/geodata.py` speaks only to `poc/data/sources.json` + cache exactly as a future `ogc-mcp` would. Migration = moving the module behind an MCP server; agent code and contracts do not change.

### 3.3 Component view — PoC pipeline

```
 OpportunityMapRequest (poc/schemas/opportunity-map-request.schema.json)
        │
        ▼
 [Intake] normalize: objectType∈{windmill,kleine_windturbine}, AoI, policyStage
        │  NormCard[] (poc/corpus/evidence-*.json, cite-verified recon output)
        ▼
 [Norm Analyst] fan-out over corpus shards (wind|bos|zon); no-citation → dropped
        │  NormCard[] (norm-card.schema.json)
        ▼
 [Norm Formalizer] NormCards → FormalRule[] (parameter/operator/value/unit/
        │  zoneSemantics; JOIN-id zone keys; ambiguous → flagged)
        ▼                         FormalRule[] (formal-rule.schema.json)
 [Geo Analyst] fetch layers (registry+cache) → make_valid → zone algebra:
        │  inclusion(Gebied windenergie) − harde − complexe belemmeringen …
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

---

## 4. Agent roster → PoC modules (plan §3.2 → files)

Actual layout of the implemented PoC (paths below exist under `poc/`); the schema pack lives in `poc/schemas/`.

| # | Agent (plan §3.2) | PoC module | Deterministic implementation now | LLM hook later |
|---|---|---|---|---|
| 1 | Orchestrator | `poc/run.py` | CLI graph runner: fixed node order, run-id, effort manifest, refuses to emit artifacts without a ValidationReport | plan decomposition |
| 2 | Intake | `poc/run.py` (`load_request`) | request loading + schema validation (objectType map, AoI = province boundary embedded in `poc/use-cases/wind.json` from `Provinciegrens_Utrecht/FeatureServer/0`) | clarifying dialogue |
| 3 | Norm Analyst ×N | `poc/pipeline/agents.py` (`NormAnalyst`) | reads `poc/corpus/evidence-{wind,bos,zon}.json`; every card resolves `sourceId` → `poc/corpus/sources.json`; emits NormCards; optional `llm_hook` callable parameter | per-document norm harvesting |
| 4 | Norm Formalizer | `poc/pipeline/agents.py` (`NormFormalizer`) | curated NormCard→FormalRule mapping (art. 5.4→inclusion `Gebied windenergie`; 9.25 lid 2→1500 m buffer; Harde/Complexe layer buffers as planMER-derived parameters) | propose rules, temp 0 |
| 5 | Geo Analyst | `poc/pipeline/geodata.py` + `poc/pipeline/engine.py` | ArcGIS REST fetcher (registry-driven, cache-first), shapely zone engine, make_valid, PROV per op | query planning |
| 6 | Cartographer | `poc/pipeline/cartographer.py` | GeoJSON/GML writer (ogr2ogr), QGIS-loadable outputs | cartographic design |
| 7 | Critic/Validator | `poc/pipeline/critic.py` | V0–V3 checks of §7 below; evaluator–optimizer loop ≤2 | quote-entailment judge |
| 8 | Explainer | `poc/pipeline/explainer.py` | decision table, PROV-O-flavoured JSON bundle, entity hashing | NL justification |
| — | (view tier) | `poc/pipeline/report.py` + `pipeline/report_template.html` | single-file HTML report (Leaflet map + fallback tables) embedded in the run dir | — |
| — | (contracts) | `poc/pipeline/contracts.py` + `poc/schemas/*.schema.json` | the six agent-boundary schemas of §6, validated at every hop | — |

The `llm_hook` of plan §3.2 is implemented as an optional callable parameter (`NormAnalyst(llm_hook=...)` in `poc/pipeline/agents.py`), **no-op default** (no callable LLM at PoC runtime — environment constraint); every agent records whether a hook answered.

Operational-plane agents 9–12 (Picture Compiler … VA Critic) are **not implemented**; the plan's roster remains their specification (Phase 3).

---

## 5. Data plane

### 5.1 Verified geo sources (the `ogc` data source)

Machine registry: `poc/data/sources.json` (71 entries, roles `inclusion|exclusion|context|aoi`). Key services (all verified live 2026-08-30, details in `docs/research/geo-catalog.md`):

| Role | Source | URL |
|---|---|---|
| **Legal inclusion (authoritative)** | Vigerende Omgevingsverordening as IMOW polygons; `WHERE NAAM='Gebied windenergie'` → 44 feats with `LOCATIE_ID` (`nl.imow-pv26.gebied.*`) + AKN `DOCUMENT_URL` | https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0 |
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

**Authority rules.** The agrest Omgevingsverordening FeatureServer is the only wind-inclusion layer with legal grounding (IMOW ids + AKN document expression `nld@1089`); `ET_wind_gebieden_windenergie/13` is an energy-transition **tracking** layer ("meest kansrijke gebieden"), never presented as the juridische werkingsgebied. The 1166.5 km² province-scale polygon in the OV set is a **designation envelope**, not plantable area — zone algebra must intersect it with `Landelijk gebied` and subtract constraints (Norm Analyst reading of art. 5.4 + toelichting, per legal-facts §5.3). planMER buffer layers carry **policy-derived distances**, not verordening norms — FormalRules that use them are labelled `derivation: planMER`, distinct from `derivation: legal-text` (e.g. the 1500 m Aandachtsgebied from art. 9.25 lid 2, which is legal-text-derived and deterministic).

### 5.2 Corpus store (legal)

`poc/corpus/sources.json` (23 pinned sources with retrieval dates) + `evidence-wind.json` (24), `evidence-bos.json` (5), `evidence-zon.json` (5) — each record with `sourceId`, `instrument` (artikeltekst vs toelichting vs visie kept distinct), verbatim `quote_nl`, `url`. Snapshots under `docs/research/sources/` make V2/V3 reproducible after the instrument changes. Pinned instruments: **Omgevingsverordening provincie Utrecht, CVDR704250 geldend 13-10-2025** (https://lokaleregelgeving.overheid.nl/cvdr704250) and **Omgevingsvisie PS 10-03-2021** (https://www.provincie-utrecht.nl/media/8648). The DSO Omgevingsdocumenten Downloaden API — the only official machine channel for GIO geometry — is key-gated (401 verified; register at https://developer.omgevingswet.overheid.nl/api-register/api/omgevingsdocument-downloaden/); until a key exists the agrest IMOW mirror is the GIO proxy with a provenance caveat recorded in every affected ZoneResult.

### 5.3 Cache layout and future stores

```
poc/data/cache/<source-id>.28992.geojson   # normalized EPSG:28992 twin (metric computation)
poc/data/cache/<source-id>.4326.geojson    # WGS84 / RFC 7946 twin (output serialization)
```

Per-fetch provenance (exact query URL+params, `fetchedAt`, featureCount, sha256 of the response, HTTP status) is recorded per layer in each run's `layers.json` manifest (plus the geo-source registry `poc/data/sources.json`); the cache is re-used only when the instrument version pin and the registry entry are unchanged. Future (plan §3.3): PostGIS `exposure` as zone store behind `postgis-mcp`, pgvector corpus index (`docstore-mcp`), RDF/SHACL KG of norms (`kg-mcp`) whose shapes double as V3 rules.

---

## 6. Interface contracts (plan §5 → `poc/schemas/`)

All agent boundaries emit JSON validated against JSON Schema (jsonschema 4.25.1); V0 runs at **every** hop, not only at the end.

| Contract | Schema file | Summary (full spec: plan §5) | Utrecht specifics |
|---|---|---|---|
| OpportunityMapRequest | `opportunity-map-request.schema.json` | id, objectType, ambitions, areaOfInterest (GeoJSON+crs), policyStage, effortBudget | `objectType` enum extended with `kleine_windturbine`; default AoI = provinciegrens |
| NormCard | `norm-card.schema.json` | claim, source{docId,article,version,quote,uri}, theme, confidence, extractedBy | `article` format `"art. 5.4 lid 1"`; `version` = "CVDR704250 geldend 13-10-2025"; evidence class field (artikeltekst/toelichting/visie) |
| FormalRule | `formal-rule.schema.json` | normCardId, parameter, operator, value, unit, zoneSemantics, appliesTo, executableRef | zone key = Bijlage-II JOIN-id (e.g. `gebied windenergie` → `/join/id/regdata/pv26/2025/giocc2ef601-3b25-4428-8808-e77ae1e47b4d/nld@2025-10-10;846`) with ArcGIS source id as provenance alias; `derivation: legal-text|planMER|assumption` |
| ZoneResult | `zone-result.schema.json` | ruleIds, geometry{format,payload,crs}, operation, prov | CRS EPSG:28992 canonical; every op logs shapely call + inputs' sha256 |
| ValidationReport | `validation-report.schema.json` | artifactId, levels V0–V4, verdict, evidence, evaluatorRun | V3 records the independent re-execution agreement (IoU + relative area delta, thresholds 0.98 / 1%) |
| DecisionTable | `decision-table.schema.json` | columns + rows, each row ≥1 normCardId | columns include zone effect and evidence class; abstained topics listed explicitly |

**Determinism rules (plan §5).** No LLM output mutates rules or the corpus in the PoC (there is no runtime LLM at all); the deterministic engine is the source of truth; the `llm_hook` interface is the only seam where a model may later *propose*, never *decide*.

---

## 7. Validation framework (plan §4 → PoC)

Validation is a graph-node class: the Orchestrator refuses any run whose final artifact lacks a passing report.

| Level | PoC implementation (deterministic) | Failure action |
|---|---|---|
| **V0 syntactic** | jsonschema validation of every artifact crossing an agent boundary; GeoJSON structure + CRS member check | auto-repair ≤2, then reject |
| **V1 geometric** | shapely `is_valid` on all inputs and outputs (`make_valid` mandatory — 8/44 ET and 1/44 OV features invalid as served); pyproj CRS equality (28992); area sanity vs. extent; IoU checks between designation pyramid levels (visie ⊃ OV ⊇ ET, geo-catalog §2.1 numbers as fixtures) | reject to Geo Analyst |
| **V2 legal grounding** | cite-or-abstain, implemented at runtime as: every NormCard resolves to `sources.json` and carries docId+article+version+verbatim `quote_nl`+uri (completeness gate); every FormalRule references ≥1 existing NormCard; abstention register (stikstof, general noise dB, tip height, setbacks — national-law domains, no provincial NormCards issued). Verbatim containment of each `quote_nl` against the snapshot texts (`docs/research/sources/cvdr704250-tekst-extract.txt`, `visie.txt`) was performed at recon time (`docs/research/legal-facts.md` method section) and re-verified against the live sources; runtime re-containment is a Phase-2 hardening item | reject card/rule; log abstention |
| **V3 semantic re-execution** | independent second pass re-computes the zone algebra with a separate implementation (`engine.reexecute_independent`: geopandas `GeoSeries`/`overlay` primitives instead of raw shapely, same FormalRule partition semantics); agreement thresholds IoU ≥ 0.98 and relative area delta ≤ 1%; divergence fails the run (unit-tested with an injected divergent zone) | reject; escalate to human if disagreement persists |
| **V4 human expert** | **pending HITL**: Explainer emits a review bundle (decision table + PROV + map) with `V4: "pending"`; the sign-off queue is the artifact, not a UI yet | annotate → gold-set candidate |

The pluggable judge: the `llm_hook` callable (optional parameter, no-op default in `poc/pipeline/agents.py`) returns `None` today; when an open model is available (Phase 2+) it can supply the quote-entailment rubric check of plan §4 without weakening the deterministic V2 completeness/linkage checks.

---

## 8. Technology & deployment

**PoC runtime (verified on this machine, 2026-08-30).** python3 3.13 · shapely 2.1.2 · pyproj 3.7.2 · geopandas 1.1.3 · fiona 1.10.1 · requests 2.33.1 · jinja2 3.1.6 · jsonschema 4.25.1. CLI tools: `ogr2ogr`, `pdftotext` (both `/opt/homebrew/bin`). **No API keys of any kind; no callable LLM at runtime** — hence every agent is a deterministic implementation behind an interface with an optional `llm_hook`. Deployment = a workspace directory; runs are files under `poc/runs/<run-id>/`.

**Target evolution (plan §6).** Orchestration → LangGraph 1.0 checkpointed graph (https://docs.langchain.com/oss/python/releases/langgraph-v1) with N8N as ops trigger; tools → MCP servers (registry: https://modelcontextprotocol.io/registry/about; pin/vet versions per plan §7 supply-chain risk); federation → A2A v1.0.0 under the Linux Foundation (https://a2a-protocol.org/latest/specification/), Phase 5; models → open-source only (paper B constraint B5), routed behind `llm_hook`; observability → OTel GenAI semconv + Langfuse. The module boundaries of §4 are chosen so this evolution replaces transport, not logic.

---

## 9. Phased roadmap alignment (plan §7)

| Plan phase | Status in this pilot |
|---|---|
| **Phase 0** foundations | Largely done: legal corpus pinned + snapshotted (23 sources, 34 evidence records); geo services catalogued + schema-validated registry (71); golden-set material identified (planMER resterende ruimte, province focus-group analog); missing: tri-modal bindings, OTel wiring, GS-1 formal freeze |
| **Phase 1** single-agent baseline + V0–V3 harness | **This PoC**: full deterministic pipeline (Intake→Explainer) with V0–V3 checks and independent re-execution; planMER `Resterende ruimte` identified as benchmark material but not yet wired in |
| **Phase 2** multi-agent orchestration | Structurally present (fan-out module boundaries, critic loop, contracts) but workers are deterministic, not LLM subagents; remains: real fan-out with open models, Skill export, wrapped VuLens/AeroSense |
| **Phase 3** KG/BNK/VA operational plane | not started |
| **Phase 4** 3D pipeline (A2) | not started (3D BAG viewer exists as front-end seed) |
| **Phase 5** policy-cycle integration & federation | monitoring-stage drift design included (§10); A2A/Participate/Marketplace future |

**Pilot exit criterion (Phase 1):** a wind opportunity map for province Utrecht whose every zone traces to NormCard → CVDR704250 article → geometry service, with V3 agreement recorded — the quantified "to what extent" answer paper B asks for, in deterministic form.

---

## 10. Risks & mitigations

| Risk | Mitigation (this architecture) |
|---|---|
| Legal-text drift on re-publication (amendment PS 18-11-2026, in werking 01-01-2027; prb-2026-12) | Corpus pinning + snapshots; `2e_wijziging_WFL1` draft polygons as change-detection feed; re-run recon + V1/V3 monitoring checks before the date; version field on every NormCard |
| Data staleness / silent service updates | fetch manifests with sha256 + timestamps; cache invalidated only by explicit re-fetch; `lastChecked` surfaced in ZoneResult provenance |
| ArcGIS service churn (deleted `Natura2000_gebieden_buffers_1__3__5_km`, duplicate republishes, truncated names — all observed) | registry-driven fetching with role metadata; duplicates flagged in geo-catalog §2.3 and never registered twice; probes re-runnable (`poc/data/probe_services.py`) |
| Norm hallucination | cite-or-abstain at V2 (quote containment vs. snapshot); abstention register; `derivation` labels separating legal-text, planMER and assumption parameters; no runtime LLM in the PoC at all |
| GIO geometry indirection (DSO API 401) | agrest IMOW mirror as proxy with recorded caveat; apply for DSO key as roadmap item; JOIN-id remains the canonical zone key either way |
| Designation-envelope misreading (1166.5 km² polygon) | envelope semantics enforced in FormalRules (intersect `Landelijk gebied`, subtract constraints); flagged in geo-catalog and legal-facts hand-over |
| Geometry defects as served | `make_valid` mandatory, V1 gate, ring-orientation-adaptive conversion for agrest esri-JSON |
| Large-response truncation on agrest (≳20 MB observed) | where-subsets + pagination + per-page feature-count verification |
| Cost/complexity blow-up in future fan-out | effort budget in OpportunityMapRequest; Orchestrator refuses unbounded plans (plan §3.2 guardrail) |

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
| B pilot (Utrecht, wind/bos/zon) | — | this pilot: wind end-to-end; bos/zon corpora pre-loaded |
| B congestion use case | EnergyCast as MCP tool | art. 5.10/5.11 energietoets formalized as non-spatial condition; grid model Phase 4/5 |
| A4 FAIR cross-org sharing | data space + identities | future Phase 5 (EU LDT Data Space Ready) |
| B5 citizen contestability | eParticipation for V4 | V4 review bundle designed as the contestation artifact |

---

*Maintained alongside `MULTI_AGENT_PLAN.md`. Facts current as of 2026-08-30; the instrument pin (CVDR704250 geldend 13-10-2025) must be re-verified before 18-11-2026.*
