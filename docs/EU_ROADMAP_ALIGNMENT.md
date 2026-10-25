# EU DT Roadmap Alignment — how the PoC portfolio implements D05.04

| | |
|---|---|
| Document | `docs/EU_ROADMAP_ALIGNMENT.md` · v1.0 · 2026-10-22 |
| Anchor source | *D05.04 Public report on the roadmap for the scale-up of EU AI-powered DT* — CNECT/2022/OP/0098, KK-09-23-370-EN-N, doi [10.2759/345126](https://doi.org/10.2759/345126), last update 14 Aug 2023 ([local PDF](./public%20report%20on%20the%20roadmap%20for%20the%20scale-up%20of%20eu-KK0923370ENN.pdf)) |
| Sibling source | *D05.02 LDT Toolbox detailed specifications* (KK-09-23-368-EN-N, [local PDF](./public%20report%20on%20the%20ldt%20toolbox%20detailed%20specifications-KK0923368ENN.pdf)) — the 20-BB catalogue that [`toolbox-sim/`](../toolbox-sim/README.md) and [`ldtsolutions/`](../ldtsolutions/MINIKUBE_ENV_PLAN.md) implement against |
| Relates to | [`SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) v1.4 · [`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) v1.2 · [`../nldt/08-roadmap.md`](../nldt/08-roadmap.md) (Phase 0–6 done) · [`../nldt/21-europai-edic-handover.md`](../nldt/21-europai-edic-handover.md) (EDIC landing) · [`AGENTIC_STATE_PLAN.md`](AGENTIC_STATE_PLAN.md) v1.2 · [`GENAI_SEAMS.md`](GENAI_SEAMS.md) |
| Status | Strategy — ter review door Marc |

---

## 0. Summary

**The repo is a working, vertically-deep instantiation of what D05.04 plans at EU level.** The report sketches a roadmap for scaling AI-powered Local Digital Twins across Europe in three phases (set-up → scale-up → sustain) and four streams (ecosystem development · toolbox deployment, scale-up & evolution · awareness · community engagement). This portfolio already demonstrates, with reproducible evidence, the things the roadmap only schedules: cross-border deployment (Benelux — the report's assumption AS-7), interoperable building blocks built on open standards (GP-2/AS-4), trustworthy AI ahead of AI Act enforcement (risks R-4/R-5), and a community-engagement catalogue of real front-runner organisations (Utrecht, Eindhoven, Breda, Rijnland, Zeeland/Oost-Vlaanderen).

The alignment is **strongest on the technical streams and weakest on the institutional ones** — which is expected for a PoC portfolio and is exactly what the gap analysis (§7) and strategy (§8) address. In one line per stream:

| D05.04 stream | Portfolio position |
|---|---|
| 1 · AI-powered ecosystem development | Implemented ahead of schedule: EDIC landing work (`nldt/21`), AI Act-compatible trust gates (V0–V4, cite-or-abstain, PROV), open interop standards (OGC, MCP, A2A, ODRL, DCAT-AP) |
| 2 · Toolbox deployment, scale-up & evolution | 8 PoCs across 6 organisation types (province, 2 municipalities, water board ×2, port district NL\|BE, practice standard) + the 20-BB catalogue simulated (`toolbox-sim`) and partially deployed for real (`ldtsolutions`) |
| 3 · Awareness increase | Offline demo surfaces replaying canonical evidence (`nldt/simulation/`, `demo/`), executive briefs NL/EN for provinces and boards |
| 4 · Community engagement | Real co-development: VNG session methods implemented (bp2op), AI in the City Breda, ITC Twente thesis (gwt), MiniGIM/NEPROM practice standard, Zeeland–Oost-Vlaanderen brief |

The strategic recommendation (§10) is to **convert technical alignment into institutional alignment**: publish the alignment as a machine-readable map, bridge the repo's rich correctness-KPIs to the report's adoption/utilisation-KPIs, claim standards/AI-Act conformance explicitly instead of implicitly, and use the NSPD pattern + function-level rollout (agentic-state F1) as the horizontal scale-up vehicles.

---

## 1. What D05.04 prescribes

The report is the EU Commission's roadmap deliverable for scaling AI-powered DTs via the LDT Toolbox. Its instruments, which this document aligns against one by one:

| Instrument | Content (D05.04 ref) |
|---|---|
| **Maturity model** | DUET Digital Twin Maturity Model: L1 Awareness → L2 Experimental → L3 Predictive → L4 Intelligent. Of 135 EU LDT projects analysed, **90% sit at L1–L2, only 9% at L3** (§2.3) — i.e. the Toolbox must lift communities up this ladder |
| **Phases** | Short term *Set-up* (groundwork, L0–1 communities, first tools) → Mid term *Scale-up* (pilot toolbox release, partner with most advanced communities, AI Act/Data Act alignment, standardisation via ITU/MIMs) → Long term *Sustain* (EDIC takes over, self-sustainability, CitiVerse) (§2.1, Fig. 3–6) |
| **Streams** | Four co-dependent streams: AI-powered ecosystem development · LDT Toolbox deployment, scale-up & evolution · Awareness increase · Community Engagement (§1.3, §5.3, Fig. 18) |
| **Ecosystem map** | Four initiative categories: data sharing & lessons learned (DS4SSCC, CitCom.ai TEF, AI4EU, OASC, Living-in.EU); data-sharing environments (DigiNEB, DT4Regions, TEFs); data collection & analytics (Urbanage, Net Zero Cities, ODALA…); inclusiveness & partnership — which **explicitly names Geonovum's Dutch Digital Twins project** as the regional-collaboration exemplar (§2.2 Cat. 4) |
| **Front-runner lessons** | Helsinki & Rotterdam boxes (§2.3): clear vision, open data, experimentation culture, CDO governance, pooling (6Aika), co-creation, CityGML 2.0, innovative procurement; challenges: consistency, standardisation, data quality, interoperability, maintenance/governance, pilots→real use |
| **SCC challenges** | Six: skills & expertise gap · financial constraints · lack of governance model · data privacy & security · lack of available data · lack of centralisation & standardisation (§2.4, Fig. 13) |
| **Guiding principles** | GP-1 activity-based timeline · GP-2 interoperability & diversity of topics · GP-3 collaboration & data-driven focus · GP-4 efficient data handling & user-centric design · GP-5 continuous user engagement · GP-6 optimisation of public/European funding (Table 2) |
| **Assumptions** | AS-1…AS-8 — incl. **AS-7: vertical deployment is local/regional and reaches across country borders, e.g. Benelux country groups** (Table 1) |
| **Risks** | R-1…R-8 with mitigations (Table 3) — maturity scepticism, fast-moving sector, advanced-area concentration, non-linear AI behaviour, ethics/trust, data quality, funding uncertainty, poor data management |
| **Sustainability plan** | Six pillars: strategic · stakeholders ecosystem · financial · environmental · technological · legal (§4); value model driven by **BB Utilisation + Cost Control** with continuous maintenance management and reliability engineering (§4.1, Fig. 16); monitoring process for new technologies (§4.2) |
| **KPIs** | On-time/on-budget delivery · adoption & utilisation · data accuracy & integrity · satisfaction & feedback · stability & performance · post-deployment support, with phase-specific and pillar-specific targets (§5.5) |

**Timeline note (GP-1 applied to ourselves):** the report's indicative dates (2023→2026+) have largely played out — the EDIC exists and this repo already does EDIC handover work (`nldt/21-europai-edic-handover.md`). Following GP-1 ("activity-based, not date-based planning"), this document treats *set-up* as past, positions the portfolio in the *scale-up* window with *sustain* obligations already knocking (EDIC, maintenance value model), and reads D05.04 as a framework rather than a calendar.

---

## 2. The PoC portfolio at a glance

Full inventory evidence lives in the per-PoC READMEs; this table is the alignment-relevant view.

| # | Dir | Target organisation | What it proves | Maturity signals |
|---|---|---|---|---|
| PoC-1 | `poc/` | Provincie Utrecht | "Waar kan ik wat?" — 13 tracks over the Omgevingsverordening with full cite-or-abstain traceability, scenario sweep, cross-track H3 overlay | 15 canonical runs, 35 scenario-runs, 376 offline tests, golden regression, calibration 13/13 tracks, V3 IoU ≥ 0.9998 |
| PoC-2 | `poc-bp2op/` | Gemeente Eindhoven | Bestemmingsplan→omgevingsplan rule-for-rule matching with AI, lawyer decides (VNG "Amsterdams aanpak" methods, method cards MC-1…MC-12) | 32 offline tests, canonical run 2026-08-30 (311 rows, 70 needs_human), durable HITL in deep-agents |
| PoC-3 | `poc-rijnland/` | Hoogheemraadschap Rijnland | Formal peilbesluit vs operational practice conflict (H3), what-if via CDC lake pipeline | 8 runs, MCP tools registered |
| PoC-4 | `poc-breda/` | Gemeente Breda | Five-value open-data scan (AI in the City 2026) per CBS buurt + sovereignty manifest + grounded Q&A seam | 73 tests on QA seam, 6 scans, 84 afweging-runs, live-validated 2026-09-13 |
| PoC-5 | `poc-minigim/` | MiniGIM/NEPROM practice (pilot Breda) | Keyless open data auto-fills the MiniGIM omgevingsanalyse checklist (74 items) + ILS area draft; honest degradation (29 auto / 45 manual) | 24 test files, canonical pass 2026-09-21, fundament migration proven lossless |
| PoC-6 | `poc-rijnland-gwt/` | Hoogheemraadscap Rijnland | Groundwater-table twin with 5-day forecast → pump advice; interpretable decision trees | 3 canonical runs 2026-10-13, holdout skill +0.71, synthetic-seed caveat carried in every artifact |
| Spin-off | `poc-nspd/` | Provincie Zeeland + Oost-Vlaanderen (North Sea Port District) | **Cross-border NL\|BE**: 13 tracks × 2 jurisdictions, one geojson, one report citing both legal systems, one 3D Leia scene | 50 run dirs, 87 tests, 14 frozen goldens, 0.000% reproduction diff, fase 2 done |
| Harness | `poc-fundament/` | — (shared) | MiniGIM harness: fase-manifest, binding executor, honest degradation, dep isolation | 11 test files; two consumers proven identical |

Around them: the **nLDT platform** (`nldt/`, OGC Records/Cookbook/Processes + MCP + A2A + medallion lake + ODRL data space), the **governed agent layer** (`deep-agents/` with artifact gates, run journal, durable HITL, Laya router), the **GenAI seam catalogue** (`docs/GENAI_SEAMS.md`, S1–S11 under "AI proposes · pipeline disposes · human decides"), the **EU Toolbox connection** (`toolbox-sim/` = all 20 BBs simulated; `ldtsolutions/` = real catalogue on K8s, Keycloak + Play & Visualise verified), and **evidence surfaces** (`nldt/simulation/`, `demo/`, bestuurlijke notities).

---

## 3. Per-PoC alignment matrix

| PoC | Primary D05.04 anchors | What it contributes to the roadmap |
|---|---|---|
| PoC-1 Utrecht | Stream 2 (vertical deployment, local scale); GP-4; R-4/R-5 mitigation; DUET L2→L3 | The reference chain *instrument → NormCard → FormalRule → zone → critic → explainer*: the repeatable "how to build a trustworthy AI-powered LDT" pattern the Toolbox can productise. Also the scenario plane (what-if) that lifts L2 communities toward L3 predictive use with HITL guardrails |
| PoC-2 Eindhoven | Stream 4 (built with the community: VNG session); Stream 2; R-1 mitigation (value shown on a concrete municipal pain); mid-term action "partner with most advanced communities" | Proof that EU-style LDT tooling lands on a *real, dated municipal task* (bruidschat conversion), and that HITL ("de jurist beslist", MC-6) is enforceable in an agent pipeline |
| PoC-3 Rijnland | Stream 2 (water-board scale, AS-7 "beyond municipalities"); GP-3 data-driven; DUET L3 | Formal-vs-operational deviation as an LDT use case; CDC lake what-if = the report's "predictive twins" category, built only on keyless open data |
| PoC-4 Breda | Stream 4 (AI in the City conference); GP-5; awareness; sustainability pillars (financial/environmental via 0-keys/local compute; legal via sovereignty manifest) | The **five-value frame is a ready-made adoption/utilisation narrative** for the report's KPI "adoption & utilisation" and its "city guide" action: per-buurt evidence of where open data + AI creates value *today* |
| PoC-5 MiniGIM | Stream 2 (practice-standard integration = vendor-agnostic adoption path); GP-4 user-centric design; R-1 (value without deep maturity) | Adopting an existing sector methodology (NEPROM/MiniGIM) instead of inventing one — exactly the "wrap, don't rebuild" posture D05.04 wants toward existing practice; honest `manual` bindings model the skills-gap challenge instead of hiding it |
| PoC-6 Rijnland GWT | DUET L3→L4 (forecast + actuation advice); §4.2 new-technologies monitoring; R-6 mitigation (baseline + skill metrics, honest synthetic-seed caveat) | Shows the maturity frontier the Toolbox targets (intelligent twins) with interpretability and explicit provenance caveats — the report's R-4 "calibration and validation of AI models" done literally |
| PoC-NSPD | **AS-7 verbatim** (cross-border Benelux); Stream 2 horizontal deployment; GP-2; R-3 mitigation (export pattern beyond the home province) | The single strongest alignment in the portfolio: one question → zones under two legal orders, verbatim citations from both, one 3D scene, Zeeland's own viewer config adopted 1:1. It is also the export vehicle for AS-6 (peripheral regions): the *pattern* travels, the legal content stays local |
| poc-fundament | §4.1 value model (reusable capability core); GP-2 reusability; long-term "reliability engineering" | The harness layer that makes PoC #7+ cheap — the report's cost-control driver implemented as fail-isolation + shared executors + conformance tests |

---

## 4. Alignment by roadmap stream

### 4.1 Stream 1 — AI-powered ecosystem development

- **EDIC/CitiVerse landing, already in motion.** `nldt/21-europai-edic-handover.md` + `recipes/edic-asset-map.json` map repo assets onto the three EuropAI EDICs (LDT CitiVERSE lead, IMPACTS, Digital Commons) with acceptance conditions — the report's long-term handover ("EDIC is expected to have taken on overall responsibility", §2.1) anticipated as a concrete work package, not a hope.
- **AI Act posture.** The report schedules AI Act alignment as a mid-term task (§2.1, Fig. 5 enforcement diamond). The portfolio's trust machinery — cite-or-abstain (V2), independent re-execution (V3), always-pending human sign-off (V4), schema-validated model outputs, public rejection ledgers, PROV+sha256 receipts, local-only models (`deep-agents/models.py` refuses cloud tiers) — is functionally the transparency, human-oversight and data-governance posture the Act demands. What's missing is the *paperwork* (a formal conformity mapping); see gap G2.
- **Standards contribution.** OGC API Records/Processes/Features, Web 3D Context, DCAT-AP-NL 3, ODRL 2.2, W3C PROV, MCP + SEP-2640 skills, A2A 1.0 — the report's "MIMs and standardisation" theme (§2.1 mid-term, §2.4) practised rather than just endorsed. The nLDT AppStore→Cookbook→Cook pattern (`nldt/01`, `nldt/08`) is a candidate MIMs-style profile for legal Digital Twins.
- **Data-space alignment.** Medallion lake + ODRL 2.2 offers + pluggable connector (`nldt/13`, `nldt/26`) mirror the report's DS4SSCC/SIMPL/Data Spaces Support Centre strand; the `edc-manifest` connector is deliberately parked "pending SIMPL" — the same dependency D05.04 names (§2.3 "relevant infrastructure being setup (e.g., SIMPL)").

### 4.2 Stream 2 — Toolbox deployment, scale-up & evolution

- **Vertical deployment (AS-7).** Province (Utrecht, Zeeland), municipalities (Eindhoven, Breda), water board (Rijnland ×2), port district — the local/regional ladder the report demands, with per-organisation data jurisdictions kept honest (pinned CVDR instruments, per-org goldens).
- **Horizontal deployment (AS-7, Benelux).** NSPD runs identical machinery under NL and BE law simultaneously — the report's flagship example of cross-border reach ("country groups such as Benelux") delivered as working software with a bestuurlijk brief for both provinces (`docs/POC_NSPD_BESTUURLIJKE_UITLEG_SCENARIOS-en.md`).
- **The 20-BB catalogue.** `toolbox-sim/` simulates the entire D05.02 catalogue on exact HTTP contracts for adapter testing; `ldtsolutions/` installs the real catalogue locally (Keycloak identity + Play & Visualise verified). This is the "build links with existing toolkits of digital solutions" and "build links with AI-technology-focused solutions" actions of Fig. 18, in code.
- **Scale mechanics = reproducibility.** The report's scale-up risk (R-2: the sector moves; R-6: data quality) is met with pinned sources, sha256-provenance, golden regression, control-replay gates and source-monitor drift probes (`nldt/17`) — scaling by *re-running identically*, not by re-building. "A track is pure configuration over a fixed spine" is the portfolio's scaling law.
- **Evolution/maintenance value model (§4.1).** Recipes and Agent Skills are the utilisation unit (BB-utilisation analogue); keyless open data + local models are the cost-control analogue (near-zero marginal run cost); V0–V4 + goldens are the reliability-engineering loop. The utilisation counter does not exist yet (gap G3).

### 4.3 Stream 3 — Awareness increase

- `nldt/simulation/` — offline, deterministic replay of every PoC including a 29-stop guided tour and NL/EN executive demos: the report's "make the value of LDTs visible" action without any live-infrastructure dependency.
- Bestuurlijke notities for decision-makers: NSPD scenarios brief (NL/EN), DSO/RegelRecht notitie, Q3 quarterly report — the "city guide"-adjacent artefacts aimed at exactly the officials the report's awareness stream targets.
- The Breda five-value scan is itself an awareness instrument: per-neighborhood, source-traceable proof of value for non-technical stakeholders (R-1 mitigation: "inform cities about the value").

### 4.4 Stream 4 — Community engagement

- Every PoC has a named institutional counterpart and most were co-shaped with practice networks: VNG netwerksessie methods implemented verbatim with method cards (PoC-2), AI in the City 2026 (PoC-4), MiniGIM/NEPROM standard (PoC-5), ITC Twente MSc framework (PoC-6), Urban Strategy/Scenexus annex (PoC-1), Provincie Zeeland's viewer config adopted (NSPD). This is the report's "Toolbox built *with* communities, not *for* them" (§3) in the small.
- The agentic-state agenda (`docs/AGENTIC_STATE_PLAN.md`) supplies the missing abstraction the EU-level Tool Development Task Force would need: one shared *function* (F1 "voorbereiden van een ruimtelijke beoordeling") with per-organisation instances, baselines, stop conditions and a learning loop — the portfolio's answer to "community engagement built into the heart of tool development".
- What the portfolio cannot provide is EU-level community governance (Community Organisation membership, mentoring schemes) — institutional landing points recorded in §9.

---

## 5. Point-by-point alignment

### 5.1 Guiding principles

| GP | D05.04 principle | Portfolio evidence |
|---|---|---|
| GP-1 | Activity-based, not date-based planning | Repo roadmaps are phase- and manifest-driven (`nldt/08`, `fase-manifest.json`), never calendar-driven |
| GP-2 | Interoperability & diversity of topics | OGC/MCP/A2A/ODRL/DCAT-AP throughout; 13 topics from wind to groundwater to zoning-conversion |
| GP-3 | Collaboration & data-driven focus | Every artifact number is source-traceable (cite-or-abstain, PROV); six partner organisations across the portfolio |
| GP-4 | Efficient data handling & user-centric design | Keyless open data only; honest `manual` bindings; per-buurt five-value report; decision tables instead of raw zone dumps |
| GP-5 | Continuous user engagement | Deep-agents durable HITL (bp2op jurist ledger), V4-pending workflow, S11 contestation seam (designed), Q&A seam S4 live |
| GP-6 | Optimisation of public/European funding | 100% public data sources; near-zero marginal cost (local models, keyless); assets packaged for EDIC absorption (`edic-asset-map.json`) |

### 5.2 Smart Cities & Communities challenges (Fig. 13)

| Challenge | How the portfolio answers it |
|---|---|
| Skills & expertise gap | MiniGIM honest degradation surfaces exactly which items need experts (45/74 `manual` with pointers); deterministic pipelines + runbooks make the method transferable without hiring specialists |
| Financial constraints | No API keys, no cloud LLM spend, open data only; `toolbox-sim` lets full-stack integration be tested before any infrastructure purchase |
| Lack of governance model | V0–V4 validation spine, GENAI_SEAMS gate catalogue, agentic-state stop conditions and human-agent boundary tables = a working governance model for AI in government |
| Data privacy & security | Sovereignty doctrine: local models, no personal data in decision line, `accessClass` + `lake-deny.json` on the share plane, restricted publish requires HITL |
| Lack of available data | 122-source geo-registry, DONL harvest with download-vs-DataService split, DSO key-gating worked around *and documented* (agrest proxy with provenance caveat), synthetic data only with explicit `syntheticSeed: true` |
| Lack of centralisation & standardisation | One nLDT platform over all PoCs (records/processes/lake), shared schemas, shared fundament harness, goldens pinning behaviour across organisations |

### 5.3 Risks (Table 3)

| Risk | D05.04 mitigation | Portfolio implementation | Residual |
|---|---|---|---|
| R-1 maturity scepticism | Inform cities; city guide/checklist | Five-value scan; bestuurlijke briefs; simulation tour; per-PoC READMEs as draft guide material | Guide not yet distilled into one transferable document (§8 A4) |
| R-2 fast-moving sector | Constant monitoring of the LDT sector | Source monitor drift probes; §4.2-style scanning exists informally (world-model doc, Laya) — no formal scan log | Formalise a quarterly scan note |
| R-3 advanced-area concentration | Awareness for lagging regions | NSPD proves the pattern exports; nothing yet targets a lagging region (G4) | Pick one AS-6 target region |
| R-4 non-linear AI behaviour | Calibration & validation | V3 independent re-execution IoU ≥ 0.98/0.9998; control-replay gates; golden regression; rejection ledgers with real caught hallucinations (`GENAI_SEAMS.md` annex) | — |
| R-5 ethics, trust, security | Security from onset; training | Cite-or-abstain, PROV receipts, local-only models, ODRL access classes, wallet identity layer (W6a real) | W2/W6 wallet backends decision-gated (G8) |
| R-6 data quality | Quality checks, regular updates | Pinned versions + sha256; goldens; source monitor (born from a real 117k-trees incident); calibration loop | Licensed series gaps (HydroNET/BRO/DSO keys) documented as abstentions |
| R-7 funding uncertainty | Financial planning, business case | Near-zero marginal cost design is the de-facto resilience; no formal business case exists | Only relevant at institutional scale |
| R-8 poor data management | Robust data-management process | Medallion lake (bronze forensic → silver normalised → gold validated), DCAT records, CDC pipeline with merge discipline | — |

---

## 6. Maturity positioning

Against the DUET ladder that structures the whole report:

| Ladder | Portfolio position |
|---|---|
| L1 Awareness | Covered as *output*: simulation demos, briefs, five-value scan — artefacts for communities still at L1 |
| L2 Experimental | The PoC engines themselves: deterministic pipelines producing validated zones/reports per organisation |
| L3 Predictive | Scenario planes (Utrecht sweeps, NSPD what-if, Rijnland peil what-if) and the GWT 5-day forecast — prediction with provenance-basis contracts (`baseline\|norm_variance\|policy_variant\|hypothetical`) |
| L4 Intelligent | Approached with brakes on: governed agent layer (deep-agents + Laya) composing plans over the twin, but every LLM contact behind seams S1–S11 with schema gates, and the world-model renderer (Marble) restricted to `hypothetical` + HITL. The agentic-state autonomy scale (L0–L5) independently scores the stack **L3 on government workflows — exactly the level the whitepaper recommends for sensitive domains** |

Strategic reading: the portfolio deliberately *does not* race to L4; it converts each predictive capability into governance artefacts first. That is the correct posture under R-4/R-5 and under the AI Act timeline the report flags — and it should be told as such: the Toolbox's differentiator is not "more intelligent twins" but "intelligent twins you can contest".

---

## 7. Gap analysis

| # | Gap | D05.04 anchor | Note |
|---|---|---|---|
| G1 | Data-space federation not live (`edc-manifest` debt pending SIMPL; no real cross-org exchange yet) | Stream 1; §2.3 SIMPL | Technical prerequisite exists (ODRL offers, lake), the live peer does not |
| G2 | Conformance not formally claimed: no Geonovum plugfest participation (open item in `nldt/08`), no MIMs self-assessment, no AI Act conformity mapping — the gates exist, the paperwork doesn't | Mid-term standardisation actions | Cheapest high-value gap to close |
| G3 | KPI machinery measures correctness (IoU, skill, goldens), not the report's adoption/utilisation/satisfaction KPIs | §5.5 | No recipe/skill usage counters, no feedback loop metrics |
| G4 | Nothing outside NL/BE (AS-6 peripheral countries unaddressed) | AS-6, R-3 | NSPD is the export vehicle; needs one deliberate target |
| G5 | No persistent community governance (Community Organisation / Tool Development Task Force analogues are EU-level; repo only has CONTRIBUTING/maintenance-envelope seeds) | §3 | Out of repo scope alone; name the landing point |
| G6 | Operational-data depth constrained by licensing (HydroNET, BRO, DSO API keys) | R-6 | Honest abstentions; limits L3/L4 depth in water domain |
| G7 | Legal content is NL/BE-specific; the *method* travels, the NormCards don't | GP-2 (diversity of topics) | Openness: water/energy/mobility tracks show the spine is domain-agnostic |
| G8 | Wallet W2 (real OpenID4VP) / W6 (OID4VCI backend) open; OTLP exporter open | Stream 1 identity strand (`nldt/16`) | W6a (Keycloak machine credentials) done |

---

## 8. Strategy

Three horizons, activity-based (GP-1). Each action names the D05.04 element it serves and its repo landing place.

### Horizon A — Consolidate (now; convert implicit alignment into claims)

- **A1 · Machine-readable alignment map.** Publish `recipes/eu-roadmap-alignment.json` in the pattern of `recipes/edic-asset-map.json`: per PoC → streams, principles, challenges, risks, KPIs it evidences. Feeds every funding and EDIC conversation with traceability in the house style.
- **A2 · KPI bridge.** Emit recipe/process/MCP invocation counters from the nLDT control plane into lake gold; generate a quarterly KPI report (same machinery as `scenario-report`) mapping repo metrics → the §5.5 KPI list (see §9). Closes G3 mechanically, not rhetorically.
- **A3 · Conformance notes.** One short note mapping GENAI_SEAMS + V0–V4 to AI Act transparency/human-oversight/data-governance obligations; one MIMs-style self-assessment of the nLDT profile (OGC/MCP/A2A). Then book the Geonovum plugfest slot (open item in `nldt/08`). Closes G2.
- **A4 · City-guide distillation.** Merge the per-PoC runbooks + "five worries" GenAI explainer + MiniGIM checklist into the single "how to set up a trustworthy legal LDT" checklist D05.04's R-1 mitigation calls for (NL/EN). The raw material already exists; nobody has assembled it.

### Horizon B — Scale (6–18 months; the report's scale-up actions in miniature)

- **B1 · Second cross-border instance.** Replicate the NSPD pattern to one more Benelux/EGTC region (AS-7) — proving `poc/` + `poc-nspd/` is a *pattern*, not a place. Simultaneously pick one AS-6-style target (a peripheral EU region) for a scoped pilot of the same pattern (closes G4, R-3).
- **B2 · Function-level rollout.** Install agentic-state function F1 at ≥3 organisations (Utrecht, Breda, Eindhoven are already in-repo) with `function-baseline.json` + stop conditions — the portfolio-scale version of "partner with most advanced communities" and the raw material for later mentoring.
- **B3 · One live data-space share.** Land one real gold dataset + ODRL offer with a real peer over SIMPL-compatible transport (or SIMPL-Lite), retiring the `edc-manifest` debt on a live path. Closes G1.
- **B4 · EDIC contribution.** Move 2–3 recipes through the CitiVERSE acceptance conditions already drafted (`edic/fit-citiverse.md`, `edic/stage-gates.md`) — the report's long-term handover, started early.

### Horizon C — Sustain (18+ months; the report's sustain obligations)

- **C1 · Maintenance value model.** Stand up the §4.1 two drivers for real: BB-utilisation dashboard (recipe/skill/process usage from A2) + cost registry (marginal cost per run ≈ 0; document it) + reliability engineering already embodied by goldens/V3. Turns "reproducibility" into the report's maintenance language.
- **C2 · Mentoring package.** Productise the transferable unit — pinned sources + goldens + runbook + city guide (A4) — as the artefact a mature community hands to a new one (report's long-term "mentoring schemes"). This is also the AS-6 delivery vehicle from B1.
- **C3 · Feedback loop.** Activate S11 (contestation intake) and fold board/province brief feedback into the KPI report — "satisfaction & feedback" measured, not asserted.
- **C4 · Sustainability scoring.** Add per-run energy (local MLX/deterministic compute), compliance-rate and support-response fields to run reports, so the six sustainability pillars of §4 have numbers by default.

---

## 9. KPI bridge

| D05.04 KPI (§5.5) | Portfolio proxy today | To add |
|---|---|---|
| Adoption & utilisation | 6 organisations instantiated; 8 PoC dirs; run counts per PoC | Recipe/process/MCP usage counters → quarterly report (A2) |
| Data accuracy & integrity | V0–V3 gates, IoU ≥ 0.9998, goldens 0.000% diff, source-monitor probes, PROV sha256 | — (already exceeds the report's intent) |
| Satisfaction & feedback | Briefs delivered to Zeeland/Oost-Vlaanderen, boards; conference sessions | S11 contestation intake metrics (C3) |
| Stability & performance | 376/87/73-style offline suites; 47/48 live sources reachable; reproducibility demos | Uptime n/a for offline PoCs — state that framing in the report |
| Post-deployment support | READMEs, rejection ledgers, run journals | Support-response field (C4) |
| Model prediction accuracy | GWT holdout skill +0.71; bp2op match ratio 75% (with 70/311 correctly routed to human); V3 zone reproduction | Track per-release in gold |
| On-time / on-budget | Not formally applicable (no project funding frame); cost control evidenced by design | Cost registry (C1) |
| Pillar KPIs (§5.5) | Legal: compliance gates + V4 ledger; environmental: local/keyless by construction | Energy-per-run, compliance-rate, retention metrics (C4) |

---

## 10. Sources

- D05.04 — *Public report on the roadmap for the scale-up of EU AI-powered DT*, CNECT/2022/OP/0098, KK-09-23-370-EN-N, 14 Aug 2023 (`docs/public report on the roadmap for the scale-up of eu-KK0923370ENN.pdf`)
- D05.02 — *Public report on the LDT Toolbox detailed specifications*, KK-09-23-368-EN-N (`docs/public report on the ldt toolbox detailed specifications-KK0923368ENN.pdf`)
- Repo: `README.md` · `docs/SOLUTIONS_ARCHITECTURE.md` · `docs/MULTI_AGENT_PLAN.md` · `docs/GENAI_SEAMS.md` · `docs/AGENTIC_STATE_PLAN.md` · `docs/AGENTIC_STATE_GAP_ANALYSE.md` · `nldt/00-architecture.md` · `nldt/08-roadmap.md` · `nldt/13/15/17/18/21/23/26` · per-PoC READMEs (`poc*/README.md`) · `toolbox-sim/README.md` · `a2a-simulation/README.md` · `deep-agents/README.md` · `ldtsolutions/MINIKUBE_ENV_PLAN.md`
