# Multi-Agent Architecture Plan & Specification — LDT Toolbox

**Delivering the goals of the two papers with state-of-the-art multi-agent AI techniques**

| | |
|---|---|
| Source papers | `GeoAIbasedsupportforthecommonoperationalpicturefin.docx` (emergency management / COP) · `ExploringtheFeasibilityofGenerativeAI…UrbanDigitalTwinsv1.1.docx` (UDT legislative opportunity finding) |
| Local assets to build on | PostGIS `exposure` DB (EU Building Database schema, NL data), SpatiaLite copy, 3D BAG CesiumJS viewer (`3d-viewer/`), QGIS 4.2, N8N (paper 1's orchestrator) |
| Toolbox alignment | §3.4 maps every solution in the [EU LDT Toolbox Solutions Catalogue](https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue) (20 solutions) onto this architecture — principle: **wrap, don't rebuild** |
| Status | Plan + specification v1.2 |
| Survey basis | Technique survey verified against live web sources (2026-08-30, via z.ai GLM web search over the Anthropic-compatible endpoint). Verified links in §9. |

---

## 1. Goals distilled from the papers

### Paper A — GeoAI support for the common operational picture (emergency management)

- **A1. Opportunity map generator** — N8N-orchestrated chain (tuning agent → RAG over policy/risk documents → parameter derivation → zone elimination → spatial agent → JSON → QGIS). *Known failure: could not derive the comprehensive set of legislative norms from hundreds of policy documents.*
- **A2. 3D geolocation & object classification** — allow/disallow measures near risk objects in 3D (UNESCO fortress case), outputs Blender / JSON / Unity code, supports Heritage Impact Assessment at scale.
- **A3. Virtual Assistant (VA)** — automated situational picture from public + restricted sources; similar-past-incident retrieval; interpretation of governance network maps (BNKs) via hybrid RAG + Knowledge Graph + vector embeddings → machine-readable triples (97–98% accuracy, >2 h → 60 s). KG triples are the *validation mechanism for the professional*.
- **A4. Research challenge (explicit)** — a *generalizable validation solution* that is an integral part of the working process, the agent orchestration architecture, and the government policy cycle (design → programming → permission → monitoring). FAIR; hybrid rule-based + GenAI agents.

### Paper B — GenAI for spatial & regulatory opportunity finding in Urban Digital Twins

- **B1. Research question** — to what extent can an LLM tuned with spatial content answer *"where can I do what?"* for urban planners?
- **B2. GML code generation** — meaningful contours for specific norms (e.g. sound levels) as GML, interoperable with Tygron / ESRI / permit tooling; polygons still lack plan context.
- **B3. Tri-modal cross-referencing** — satellite image / legal text / GML-code triplets (Pixtral era; needed image binding + significant scripting).
- **B4. Data quality** — cleaning/filtering of legacy GML spatial plans 2012–2022 (ruimtelijkeplannen.nl), outdated content, pre-training quality below expectation.
- **B5. Constraints & directions** — open-source models only (transparency), Snellius compute, FAIR + CODIO governance; future: explainability/transparency/contestability, scaling, real-world pilots with Utrecht geodata + Omgevingsvisie; use cases: windmill space, solar fields, forest planting, power-net congestion.

**Combined delivery goal:** a multi-agent system that answers *"where can I do what?"* over legal geodata and 3D city models, where **every legal claim is machine-verifiable, traceable and contestable**, usable both in the slow policy cycle (planning/permitting) and the fast operational cycle (incident COP), with validation woven into the orchestration itself.

---

## 2. State of the art: techniques to adopt (survey)

### 2.1 Orchestration topologies

| Technique | What it is | Why it fits our goals |
|---|---|---|
| **Orchestrator–worker (lead agent + subagents)** | A lead agent decomposes the task, spawns parallel subagents with *isolated contexts*, aggregates results. Anthropic's multi-agent research system (2025) reported ~90% improvement over single-agent on research-eval benchmarks; key lessons: explicit effort budgeting, teach the orchestrator to delegate with *detailed task descriptions*, multiply effort via parallel tool calls. | Directly addresses A1's failure: a single tuning agent over "hundreds of policy documents" drowns. Fan out per-document/per-theme Norm Analyst subagents, then synthesize. |
| **Graph-based state machines** (LangGraph-style: nodes, edges, checkpointing, durable execution) | Explicit workflow graph with state, branching, retries, human-in-the-loop interrupts. | The papers demand auditability and a policy-cycle-embedded process — an explicit graph is legible to civil servants and replayable. Replaces implicit N8N chains with a typed graph (or wraps N8N as the durable backbone). |
| **Evaluator–optimizer (reflection/critique loops)** | A generator agent produces; a critic agent scores against rubrics; loop until pass or budget exhausted (Self-Refine / Reflexion lineage; core of "deep research" systems). | This is the generalizable validation mechanism A4 asks for: *validation as an architectural component*, not an afterthought. |
| **Map-reduce fan-out over corpora** | Partition documents/themes, run identical subagent prompts per shard, reduce. | B4's corpus cleaning and A1's norm harvesting are embarrassingly parallel. |
| **Swarm / handoff topologies** | Lightweight agents hand control to each other (OpenAI Agents SDK). | Useful for the VA (A3) where conversation flows between intake → picture → BNK explanation. Avoid free-form peer-chat for the planning pipeline (higher failure coupling, as Magentic-One's ledger/task-tracker findings show). |

### 2.2 Interoperability & tooling protocols (verified 2026-08-30)

- **MCP (Model Context Protocol)** — open standard for tool/data servers; one year old as of Nov 2025 and widely adopted; the official **MCP Registry** is live (namespace management via DNS verification). Adopt as the *only* way agents touch tools: PostGIS query server, QGIS/OGC-API server, 3D BAG server, document-store server, rule-engine server. One MCP server per capability, reused by every agent and by N8N. *Governance note:* registry admission currently proves only repo/domain ownership — no mandatory code review or audit — so pin server versions and vet them like any other dependency (see risks, §7).
- **A2A (Agent2Agent protocol)** — **v1.0.0 stable specification** under the **Linux Foundation** (Google-contributed, Apache 2.0), 150+ participating organizations, multi-protocol support. Adopt later (Phase 5) when agents from different organizations (province, safety regions, NIPV) must interoperate — exactly the paper's multi-party governance setting.
- **Agent frameworks** — **LangGraph 1.0** (Oct 2025; stability release with **durable execution by default**, human-in-the-loop patterns, short-term memory built in) is the recommendation for the planning pipeline; the OpenAI **Agents SDK** remains actively developed (AgentKit shipped Oct 2025 but its visual Agent Builder was deprecated about a year later — build on the SDK, not the visual builder); Google ADK, CrewAI, AG2/AutoGen, Microsoft Agent Framework as alternates. *Recommendation stands:* LangGraph for checkpointed, HITL-interruptible planning workflows; handoff-style swarms only inside the VA's conversational plane.
- **Agent Skills** (Anthropic, 2025) — folder-based, versioned, progressive-disclosure instruction packages the orchestrator loads on demand. Paper A *explicitly* proposes feeding decision tables into SKILLS as guiding principles — formalize that: every validated norm set is exported as a Skill.

### 2.3 Knowledge & retrieval

- **Agentic RAG** — the agent decides when/what to retrieve, queries tools iteratively, cites what it used.
- **Hybrid KG + vector (the paper's own A3 finding, generalized)** — vector DB for recall over policy text; Knowledge Graph (RDF/OWL triples) for *verifiable structure* (who-must-do-what-where); GraphRAG-style community summaries for corpus-level questions ("which norms apply to windmills near Natura 2000?").
- **Tri-modal binding (B3)** — co-embed text, imagery, and GML code with a shared multilingual multimodal encoder; store bindings as explicit link-records (source-doc §, image chip, geometry id) rather than relying on the VLM's implicit cross-attention.
- **Constrained decoding / structured outputs** — every agent boundary emits JSON validated against a schema; norms become typed records, never free prose.

### 2.4 Verification, evaluation, governance

- **Neuro-symbolic split** — LLMs *extract and propose*; a deterministic rule engine / spatial database *executes and verifies*. Hybrid rule-based + GenAI is exactly the papers' conclusion.
- **SHACL/RDF validation of legal constraints** — formalize norms as shapes/rules over the KG; run as V-level checks.
- **LLM-as-judge with rubrics** + **golden-set regression** in CI (Ragas/DeepEval/promptfoo class tooling, plus custom geo-metrics).
- **Provenance (W3C PROV-O)** — every artifact records which agent, which model version, which documents/articles, which rule versions produced it → contestability (B5) and the professional's KG validation role (A3).
- **Observability** — OpenTelemetry GenAI semantic conventions; Langfuse/LangSmith-class tracing; per-run cost/latency budgets (effort budgeting).
- **HITL interrupts** — checkpointed graph pauses for expert validation (paper A: "the role of the information manager shifts from manual searching to expert validation").

---

## 3. Target architecture

### 3.1 Overview

```
                            ┌────────────────────────────────────────────┐
                            │            ORCHESTRATOR (graph)           │
                            │  plan → dispatch → verify → synthesize     │
                            │  effort/cost budget · checkpoint · HITL    │
                            └───────┬───────────────────────────┬────────┘
        planning plane (slow cycle) │                           │  operational plane (fast cycle / VA)
  ┌─────────────────────────────────┴──────────┐   ┌────────────┴──────────────────────────┐
  │ Norm Analyst (fan-out subagents, RAG+KG)   │   │ Picture Compiler (situational picture)│
  │ Norm Formalizer (norms → typed rules)      │   │ Analogous-Incident Retriever (RAG)    │
  │ Geo Analyst (PostGIS/3D BAG via MCP)       │   │ BNK Reasoner (KG + RAG → triples)     │
  │ Cartographer (GML/GeoJSON/CityJSON)        │   │ Briefing Writer (structured brief)    │
  │ Critic / Validator (evaluator-optimizer)   │   │ VA Critic (latency-bounded check)     │
  │ Explainer (decision tables, PROV, Skills)  │   │                                       │
  └────────────────────────────────────────────┘   └───────────────────────────────────────┘
  ── shared services (MCP servers + stores) ────────────────────────────────────────────────
   postgis-mcp · ogc/qgis-mcp · bag3d-mcp · docstore-mcp (corpus+vector) · kg-mcp (RDF/SHACL)
   rule-engine-mcp · artifact-store · trace-store (OTel) · eval-harness · HITL review queue
```

Two planes, one spine:

- **Planning plane** — Paper B's "where can I do what?" pipeline, embedded in design/programming/permission stages.
- **Operational plane** — Paper A's VA, latency-bounded (< 60 s golden-hour budget), sharing the same Norm/Geo/KG services so legal semantics stay consistent between both cycles (A4's "integral across the policy cycle").

### 3.2 Agent roster (specification summary)

Each agent: plain-JS/Python object implementing `apply(session)` style lifecycle; emits schema-validated JSON; owns nothing global; all side effects logged with PROV.

| # | Agent | Purpose | Key inputs | Key outputs | Tools (via MCP) | Failure guardrails |
|---|---|---|---|---|---|---|
| 1 | **Orchestrator** | Decompose request, allocate effort budget, dispatch subagents, run verify-synthesize loop, trigger HITL | `OpportunityMapRequest` | Execution plan, task graph | trace-store | Max-iteration & token budget; refuses plans lacking a validation node |
| 2 | **Intake** | Clarify ambiguous requests (object type, area, ambition conflicts) | user brief | normalized request JSON | — | Asks ≤ N clarifying questions; defaults logged |
| 3 | **Norm Analyst** (×N fan-out) | Harvest candidate norms/conditions from policy corpus shard or theme | shard/theme query | `NormCard[]` (each with doc id, article, version, quote) | docstore-mcp, kg-mcp | No citation → card dropped; coverage report mandatory |
| 4 | **Norm Formalizer** | Convert NormCards → typed, executable rules | `NormCard[]` | `FormalRule[]` (parameter, operator, distance, zone semantics) | — (pure function + LLM) | Constrained JSON only; ambiguous → flagged, never guessed |
| 5 | **Geo Analyst** | Execute spatial queries / overlays / eliminations; validate geometries | `FormalRule[]`, area-of-interest | `ZoneResult[]` (GeoJSON/GML), provenance of each op | postgis-mcp, bag3d-mcp | All geometry passes ST_IsValid; SQL read-only role (`consumer`) |
| 6 | **Cartographer** | Style/serialize maps; GML 3.2, CityJSON/3D Tiles for the 3D case (A2) | `ZoneResult[]` | GML/GeoJSON/CityJSON + QGIS style / Blender script | ogc/qgis-mcp | Schema-validate; render-check against viewer |
| 7 | **Critic / Validator** | Evaluator–optimizer: score artifact against V0–V4 (§4); loop or reject | full artifact tree | `ValidationReport`, pass/fail + per-check evidence | rule-engine-mcp, kg-mcp | Hard gate: no artifact leaves system without report |
| 8 | **Explainer** | Decision tables, NL justification, provenance bundle, **Skill export** | artifact + report | `DecisionTable`, PROV graph, Skill folder | trace-store | Every table row links ≥1 NormCard |
| 9 | **Picture Compiler** (VA) | Assemble situational picture from public/restricted feeds | incident description | `SituationPicture` | postgis-mcp, docstore-mcp | Source list attached; staleness timestamps |
| 10 | **Analogous-Incident Retriever** (VA) | Find similar past incidents + lessons learned | incident embedding | ranked incidents w/ lessons | docstore-mcp | Similarity threshold; no fabrication — cite or abstain |
| 11 | **BNK Reasoner** (VA) | Map free-text incident → relevant legal frameworks + organizations (KG triples) | incident description | BNK subgraph (triples) + involved-org list | kg-mcp | Only KG-derived answers; every org justified by triple path |
| 12 | **VA Critic** | Latency-bounded spot-check of 9–11 outputs | their outputs | quick `ValidationReport` (V0–V2) | rule-engine-mcp | Budget-aware: degrade gracefully, mark unchecked |

### 3.3 Data plane

| Store | Content | Notes |
|---|---|---|
| PostGIS `exposure` (exists locally) | EU Building Database schema, NL exposure, boundaries | read via `consumer` role through postgis-mcp |
| 3D BAG tiles (exists in `3d-viewer/`) | LoD2.2 3D buildings | bag3d-mcp serves tileset + attribute lookups; feeds A2's 3D case |
| Corpus store | ruimtelijkeplannen.nl 2012–2022 GML + Omgevingsvisie + emergency docs | cleaned by Phase-0 pipeline (B4); versions kept |
| Vector index | text + GML-code + image-chip embeddings (tri-modal binding, B3) | multilingual encoder; binding link-records |
| Knowledge Graph | norms, BNK governance networks, organization triples (A3) | RDF/OWL; SHACL shapes double as validation rules |
| Artifact + trace stores | every intermediate artifact, PROV, OTel spans | replay & audit |

Where an EU LDT Toolbox solution already provides a store or service, the data plane mounts it instead of re-implementing it — see §3.4.

### 3.4 Alignment with the EU LDT Toolbox solutions catalogue

Catalogue: <https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue> (20 solutions, verified 2026-08-30). **Principle: wrap, don't rebuild.** The Toolbox's domain models stay deterministic services that agents call through MCP tool servers; the multi-agent layer adds what they lack — legal interpretation (Norm Analyst/Formalizer), orchestration (Orchestrator), and validation (Critic, V0–V4). This mirrors the papers' hybrid rule-based + GenAI conclusion and keeps the system composed of catalogue-aligned components.

**Platform backbone**

| Solution | What it provides | Role in this architecture |
|---|---|---|
| **EU LDT Integrated Environment** | Unified access point coordinating all Toolbox tools/services | Deployment shell: the Orchestrator's runs, HITL review queue, and validation reports surface here; N8N triggers enter through it |
| **EU LDT Data Platform** | Data foundation — manage/integrate/contextual urban data | Primary data plane; `postgis-mcp` and `docstore-mcp` read from it (the local `exposure` PostGIS is its Building Database slice) |
| **EU Building Database** | EU building/exposure stock | Already installed in this repo (SETUP.md); base layer for Geo Analyst and A2 3D reasoning |
| **EU LDT Data Space Ready** | Secure, standardized trusted data sharing | Gateway for restricted sources (VA incident feeds, safety-region data) and cross-org artifact exchange; backs V2 provenance and A4's FAIR requirement |
| **EU LDT Identity Management** | Identities and authentication | Service + agent identities for A2A federation (Phase 5); signs V4 human validations |

**Domain models — wrapped as MCP tool servers, never rebuilt inside an agent**

| Solution | Model | Consumed by |
|---|---|---|
| Urban Planning Vulnerability Mitigation | **VuLens** — urban vulnerability patterns | Vulnerability overlay in opportunity mapping; VA hazard picture |
| Renovation Strategies | **ReNova** — renovation prioritization under budget | Housing/energy ambition layer in scenario generation (Intake/Orchestrator) |
| Building Environmental Footprint | **EcoBuild Matrix** — building energy performance | Environmental norm facts for Norm Formalizer |
| Neighbourhood Energy Demand Forecasting | **EnergyCast** — electricity demand forecasting | Engine behind paper B's "power-net congestion optimization" use case |
| Pollution Propagation | **AeroSense** — air-pollution behaviour | Emission/air-quality constraint propagation in zone elimination (Geo Analyst) |
| Urban Mobility | **Urban Flow** — traffic and mobility problems | Mobility ambition conflicts (paper B); evacuation routing input (VA) |
| Police Routing Tool | Multi-agent AI digital twin of patrol operations, emergency-response simulation | Emergency-plane sibling: its simulation feeds VA resource-allocation and accumulated-risk scenarios (paper A); an in-catalogue precedent for multi-agent orchestration |

**Modelling & collaboration**

| Solution | What it provides | Role in this architecture |
|---|---|---|
| **EU LDT Data Modeller** | Synthetic data for simulations/predictive modelling | Synthetic scenarios and tri-modal binding augmentation (B3); golden-set fixtures for evals |
| **EU LDT Federated Learning** | Collaborative model training without sharing sensitive data | Tune the open models (paper B constraint) across safety regions without moving restricted incident data |
| **EU LDT AI Notebook** | Unified AI/ML development & run environment | Home of the eval harness, judge models, and golden-set CI (§4) |
| **EU LDT Use Cases & Scenarios** | Use-case and scenario collaboration | Scenario library driving Intake — "windmill space", "solar field", "forest planting" (paper B) live here |

**Engagement & governance**

| Solution | What it provides | Role in this architecture |
|---|---|---|
| **EU LDT Participate** | eParticipation / democratic engagement | Extends V4 beyond expert validation to citizen contestability in the design stage (B5) |
| **EU LDT City Innovation Planner** | Structured performance management for municipal digital transformation | Governs the DSR pilot program; tracks adoption/quality KPIs of the agent system itself |
| **EU LDT Marketplace** | Discovery, validation, deployment hub for LDT solutions | Publication channel for this system's reusable assets (MCP servers, Agent Skills, schema packs); discovery of further tools |
| **EU LDT Play & Visualise** | Visualisation / XR on the twin | Cartographer's front-end tier — the local `3d-viewer` (CesiumJS + 3D BAG) plays this role today |

The six wrapped domain models also define the **extension contract**: any future catalogue solution becomes available to the agents by publishing an MCP server plus a typed tool schema — no agent code changes.

---

## 4. Validation framework (the papers' core research challenge, A4)

Validation is a **graph node class**, not a human afterthought. Five levels run inside the orchestration; each level owns a check family:

| Level | Check | Executor | Failure action |
|---|---|---|---|
| **V0 — Syntactic** | JSON/GML/GeoJSON schema validity | deterministic (schema validators) | auto-repair loop (≤2), then reject |
| **V1 — Geometric** | `ST_IsValid`, topology, CRS, area sanity, IoU vs. expert zones where gold exists | deterministic (PostGIS) | reject to Geo Analyst |
| **V2 — Legal grounding** | every norm card cites doc+article+version; quote-entailment check (LLM-judge with rubric); no orphan rules | LLM-judge + KG lookup | reject to Norm Analyst/Formalizer |
| **V3 — Semantic re-execution** | rule engine independently re-executes FormalRules over KG+PostGIS; results must match pipeline output | deterministic rule engine / SHACL | reject; escalate to human if rules disagree with documents |
| **V4 — Human expert** | checkpointed HITL: professional validates decision table (paper A's "expert validation" role), signs with PROV | human | annotate → becomes gold-set candidate |

**Policy-cycle integration (A4):** the same V-levels attach at each stage — *design* (V0–V2 on scenario maps), *programming* (V1–V3 on opportunity maps), *permission* (V2–V4 full chain + HITL signature), *monitoring* (V1/V3 re-run on data refresh; drift alerts). The **Explainer** exports each validated norm set as an Agent Skill, feeding new prompts exactly as paper A proposes.

### Evaluation plan (DSR, per paper B)

- **Golden sets** (build in Phase 0, grow each DSR iteration):
  - GS-1: the three benchmark maps (wind, solar, forest) with expert zones + the exact norm lists the focus group derived.
  - GS-2: BNK cases with expert-mapped organizations (extend A3's 97–98% measurement).
  - GS-3: GML fixtures — norm → expected contour (sound levels et al.).
- **Metrics**: norm recall/precision vs. gold; zone IoU / boundary F1; citation faithfulness (% claims with valid V2 citations); V3 agreement rate; end-to-end latency (VA target < 60 s; planning minutes-scale); cost/run; HITL correction rate over time.
- **Regression**: eval-harness runs GS-1..3 in CI on every prompt/model/graph change; traces diffed.

---

## 5. Interface specifications (contracts)

All boundaries are JSON with published schemas. Core ones (summarized; full JSON Schema in `schemas/` when implemented):

```jsonc
// OpportunityMapRequest (planning plane entry)
{ "id": "uuid", "objectType": "windmill|solar_field|…", "ambitions": ["energy","…"],
  "areaOfInterest": { "geojson": … , "crs": "EPSG:28992" },
  "policyStage": "design|programming|permission|monitoring",
  "effortBudget": { "maxSubagents": 8, "maxCostEur": 2.0, "maxLatencyS": 900 } }

// NormCard
{ "id": "uuid", "claim": "…", "source": { "docId": "...", "article": "...", "version": "...",
  "quote": "…", "uri": "…" }, "theme": "sound|nature|safety|heritage|…",
  "confidence": 0.0-1.0, "extractedBy": "agent#run" }

// FormalRule
{ "normCardId": "uuid", "parameter": "distance_to_residential", "operator": ">=",
  "value": 300, "unit": "m", "zoneSemantics": "exclusion|inclusion|compensation",
  "appliesTo": { "objectType": "windmill", "context": ["Natura2000"] }, "executableRef": "rule.py@v7" }

// ZoneResult
{ "ruleIds": […], "geometry": { "format": "GML32|GeoJSON|CityJSON", "payload": … , "crs": … },
  "operation": "difference|intersection|buffer", "prov": "…" }

// ValidationReport
{ "artifactId": "uuid", "levels": { "V0": "pass", "V1": {…}, "V2": {…}, "V3": {…}, "V4": "pending" },
  "verdict": "pass|fail|needs-human", "evidence": […], "evaluatorRun": "…" }

// DecisionTable (Explainer output — the paper's trace-back artifact)
{ "columns": ["criterion","norm","source","zone effect"], "rows": [ { "…": …, "normCardId": "uuid" } ] }
```

**Determinism rules**: LLM temperature 0 for Formalizer & Critic; rules re-executed by the deterministic engine are the source of truth; LLM outputs never mutate the KG — only the Phase-0 curation pipeline (with human review) writes norm triples.

---

## 6. Technology stack (recommendation)

| Layer | Choice | Rationale / paper tie |
|---|---|---|
| Orchestration | **LangGraph** (graph, checkpointing, HITL interrupts); keep **N8N** as ops trigger/integration backbone (webhooks, schedules) calling the graph | A1 already N8N; graph adds auditability |
| Tool protocol | **MCP** servers: `postgis-mcp`, `ogc/qgis-mcp`, `bag3d-mcp`, `docstore-mcp`, `kg-mcp`, `rule-engine-mcp` | one capability, one server, reused by agents + N8N |
| Models (open-source constraint, B5) | Planner/Critic: mid-size instruct model (e.g. Qwen/Llama class, vLLM on **Snellius** or local); Norm Analyst: long-context model; VLM: current open multimodal (Pixtral successor class) for B3 | paper B's transparency requirement |
| Embeddings | multilingual text encoder + code encoder for GML; explicit tri-modal binding records | B3 |
| KG / rules | RDFLib or GraphDB; OWL vocab; **SHACL** for V3; simple Python rule engine for FormalRules | A3 KG-as-validation |
| Vector store | pgvector inside existing Postgres cluster | ops simplicity |
| Tracing/eval | OpenTelemetry (GenAI semconv) → Langfuse; eval-harness in CI | §4 |
| Geo front-ends | existing QGIS 4.2 + `3d-viewer` (CesiumJS), converging on **EU LDT Play & Visualise**; GML→Tygron/ESRI export per paper B | reuse; catalogue alignment |
| Deployment & data | **EU LDT Integrated Environment** as the deployment shell; **EU LDT Data Platform** as the data plane; **EU LDT Data Space Ready** for restricted/cross-org feeds | §3.4 backbone |
| Model training & eval env | **EU LDT AI Notebook** for the eval harness/judge models; **EU LDT Federated Learning** for cross-region tuning without moving restricted data | B5 open-source + privacy |
| Asset publication | Reusable outputs (MCP servers, Agent Skills, schema packs) published to the **EU LDT Marketplace**; A2A federation authenticated via **EU LDT Identity Management** | §3.4; Phase 5 |
| Domain models | **VuLens, ReNova, EcoBuild Matrix, EnergyCast, AeroSense, Urban Flow, Police Routing Tool** consumed as MCP tool servers — wrapped, not rebuilt | §3.4 extension contract |

---

## 7. Implementation plan (phased, DSR-style)

**Phase 0 — Foundations (data + gold + observability).**
Clean the GML corpus (semi-automated, B4); build tri-modal binding records, augmented with **EU LDT Data Modeller** synthetic scenarios; stand up postgis-mcp & docstore-mcp on the **EU LDT Data Platform**; wire OTel/Langfuse; construct GS-1/2/3 golden sets with the focus group.
*Exit:* corpus versioned; golden sets frozen v1; any agent run is traceable.

**Phase 1 — Single-agent baseline + validation harness.**
One Norm Analyst + one Geo Analyst answer "where can I do what?" end-to-end naively; V0–V3 checks implemented; eval harness runs in the **EU LDT AI Notebook**; measure against GS-1.
*Exit:* baseline metrics published (the paper's "to what extent" quantified).

**Phase 2 — Multi-agent orchestration (the core).**
Orchestrator–worker fan-out for norm harvesting; Formalizer; Cartographer (GML out); Critic closes the evaluator–optimizer loop; Explainer emits decision tables + PROV + Skill export; first wrapped domain models (VuLens, AeroSense) join as MCP tools.
*Exit:* GS-1 norm recall ≥ expert-derived threshold; V2 faithfulness ≥ target; maps render in QGIS/Play & Visualise.

**Phase 3 — Knowledge Graph + BNK / VA (operational plane).**
BNK triples pipeline (extends A3); Picture Compiler, Analogous-Incident Retriever, BNK Reasoner, VA Critic under a 60 s budget; restricted feeds arrive through **EU LDT Data Space Ready**; Police Routing Tool simulation wired into resource-allocation scenarios; GS-2 evaluation.
*Exit:* VA latency < 60 s p95; BNK org-identification accuracy ≥ 97% on GS-2.

**Phase 4 — 3D pipeline (A2).**
bag3d-mcp; CityJSON/3D Tiles zone overlays rendered via **EU LDT Play & Visualise** (local `3d-viewer` today); compensation-measure reasoning (sound walls etc.); Blender/Unity export; EnergyCast-backed congestion scenario added.
*Exit:* Heritage-Impact-style case reproduced over a large area.

**Phase 5 — Policy-cycle integration & federation.**
Monitoring-stage re-validation on data refresh; A2A federation across province/safety-region agents (AgentCards) authenticated by **EU LDT Identity Management**; Skill library and MCP servers published to the **EU LDT Marketplace**; citizen contestation piloted through **EU LDT Participate**; program KPIs tracked in **EU LDT City Innovation Planner**; DSR evaluation with practitioners; write up.
*Exit:* validation integral across design→monitoring demonstrated; handoff to the future-research agenda the papers call for.

**Risks & mitigations** — norm hallucination (V2/V3 hard gates; cite-or-abstain); corpus staleness (versioned corpus, monitoring re-runs); model upgrades breaking behavior (golden-set CI regression); cost blow-up in fan-out (effort budgets on the Orchestrator); open-model capability gaps (route Critic/VLM to strongest available open model, keep contracts model-agnostic); protocol churn (isolate MCP/A2A behind thin adapters); **MCP server supply chain** (registry admission verifies ownership only — pin versions, vendet, and audit each server like a dependency; keep the rule-engine and KG servers in-house).

---

## 8. Traceability: paper goal → technique → component

| Paper goal | Technique (§2) | Component (§3) |
|---|---|---|
| A1 comprehensive norm derivation | orchestrator–worker fan-out + map-reduce over corpus | Norm Analyst ×N, Orchestrator |
| A1 zone elimination → map | MCP tool use, deterministic spatial ops | Geo Analyst, Cartographer |
| A2 3D measures | 3D Tiles/CityJSON tooling, structured outputs | bag3d-mcp, Cartographer |
| A3 BNK interpretation | hybrid KG+vector, KG-as-validation | BNK Reasoner, kg-mcp |
| A3 situational picture < 60 s | swarm/handoff, latency-bounded critic | VA plane, VA Critic |
| A4 generalizable validation | evaluator–optimizer, SHACL/rule re-execution, PROV, HITL interrupts | Critic/Validator (V0–V4), Explainer |
| A4 policy-cycle integral | checkpointed graph stages mapped to design/programming/permission/monitoring | Orchestrator stage hooks |
| A4 Skills feedback loop | Agent Skills export | Explainer |
| B1 "where can I do what?" | agentic RAG + structured formalization | whole planning plane |
| B2 GML generation | constrained decoding → GML schema; render validation | Formalizer, Cartographer, V0/V1 |
| B3 tri-modal binding | co-embeddings + explicit binding records | docstore-mcp (Phase 0) |
| B4 corpus quality | semi-automated cleaning pipeline + versioning | Phase 0 |
| B5 explainability/contestability | decision tables, PROV, citations, HITL | Explainer, V2/V4 |
| B future use cases (congestion, energy) | wrapped catalogue models as MCP tools | EnergyCast, EcoBuild Matrix, Urban Flow (§3.4) |
| A emergency resource allocation | in-catalogue multi-agent DT simulation | Police Routing Tool via MCP (Phase 3) |
| A4 FAIR cross-org sharing | trusted data-space framework + identities | EU LDT Data Space Ready, Identity Management (Phase 3/5) |
| B5 citizen contestability | eParticipation channel for V4 | EU LDT Participate (Phase 5) |

## 9. References (links verified 2026-08-30)

- **EU LDT Toolbox Solutions Catalogue** (20 solutions) — <https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue>; solutions list — <https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions>; installation guide (automation scripts) linked from the catalogue page.
- Anthropic, *How we built our multi-agent research system* (June 2025) — <https://www.anthropic.com/engineering/multi-agent-research-system>; companion: *Patterns and problems in emerging multiagent systems* — <https://www.anthropic.com/research/multiagent-systems>.
- A2A Protocol — v1.0.0 specification and announcement — <https://a2a-protocol.org/latest/specification/>, <https://a2a-protocol.org/latest/announcing-1.0/>.
- MCP Registry — <https://modelcontextprotocol.io/registry/about>; MCP security analysis — *Securing the Model Context Protocol (MCP): Risks, Controls, and Mitigations* — <https://arxiv.org/html/2511.20920v1>.
- LangGraph v1 — <https://docs.langchain.com/oss/python/releases/langgraph-v1>; LangChain & LangGraph 1.0 alpha announcement — <https://www.langchain.com/blog/langchain-langchain-1-0-alpha-releases>.
- OpenAI AgentKit (Oct 2025) — <https://openai.com/index/introducing-agentkit/>; Agents SDK — <https://developers.openai.com/api/docs/guides/agents>.
- Anthropic, *Effective context engineering for AI agents* and Agent Skills documentation (anthropic.com/engineering, platform.claude.com/docs).
- Microsoft GraphRAG; Reflexion/Self-Refine literature; OpenTelemetry GenAI semantic conventions (opentelemetry.io).
- Papers' own citations: UrbanLLM (Jiang et al., 2024), CityGPT (Feng et al., 2024), I-UDT (Choi & Yoon, 2025), LLM agents for smart-city management (Kalyuzhnaya et al., 2025), Ji & Gao (2023) WKT geometry encoding.
