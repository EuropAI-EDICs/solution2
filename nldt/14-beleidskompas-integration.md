# 14 — Beleidskompas integration (GovChat-NL front-door app)

Plan for integrating the **Beleidskompas** policy-assistant app from
[GovChat-NL](https://github.com/jeannotdamoiseaux/GovChat-NL) into the nLDT
architecture — as the first *external* front-door app that consumes nLDT
capabilities through the governed seams.

| | |
|---|---|
| Status | Decided 2026-09-14 (§10) · BK-0 + BK-1 implemented (runbook: govchat/README.md) |
| Source app | [beleidskompas.md (GovChat-NL)](https://github.com/jeannotdamoiseaux/GovChat-NL/blob/main/docs/app-launcher/beleidskompas/beleidskompas.md) |
| Related | [04](04-recipes-and-processes.md) · [05](05-agentic-ai-layer.md) · [07](07-trust-and-governance.md) · [09](09-federation-and-observability.md) · [10](10-toolbox-integration.md) · [12](12-governed-agent-layer.md) · [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) |
| Strategic frame | NLDT App Store 2028 — *modular apps exchanged in existing front doors* ([Q3 2026 report](../NLDT%20Q3%202026%20Quarterly%20Report%20%E2%80%93%20Summary%20in%20English%20%28App%20Store%20Focus%29.md)) |

---

## 1. What we are integrating

### 1.1 GovChat-NL (the platform)

Open-source platform *voor en door Nederlandse overheidsorganisaties*
(700+ users at Provincie Limburg). Three components:

| Component | Role |
|---|---|
| **OpenWebUI** (fork) | Chat UI, authentication (SSO/OIDC, Entra ID), RBAC, PostgreSQL history, **App Launcher** |
| **n8n** | Workflow engine between chat and backends; hundreds of API connectors |
| **LiteLLM** | LLM router across providers (Azure AI, Vertex AI, Mistral, OpenAI, Ollama) |

The **App Launcher** adds per-app access control (e.g. restrict ToeKenner to
grant officers) and per-app model selection (spread LLM load). Current apps:
Versimpelaar (available), **Beleidskompas (in development, with CGI Smartlab)**,
ToeKenner (backlog). Deployment: Docker image or source, local or cloud;
Limburg runs Docker via Elestio on Hetzner under an approved DPIA.
Note: the beleidskompas directory currently contains **documentation and
screenshots only — no code**; the app itself is in development.

### 1.2 Beleidskompas (the app)

A step-by-step assistant for the **policy process** (problem definition →
decision-making → implementation):

1. Start a casus (case) with basic information
2. Work through the process steps — data entry, AI suggestions, check questions
3. Review progress — overview of answers per step
4. **Export a complete policy document (Word/PDF)**

Provincial terminology and frameworks are configurable. It is a
*document-centric, procedural* workflow with AI narration at each step.

## 2. Why this fits the nLDT strategy

- **App Store thesis, proven early.** The Q3 2026 report makes the national
  App Store the scaling engine (target 2028), with the 2026 SMART goal
  *"3+ cities exchange 3+ modular apps in existing viewers/front doors."*
  Beleidskompas is exactly such a modular app in an existing front door —
  integrating it in the testbed demonstrates the thesis before the App Store
  infrastructure exists.
- **Complementary, not overlapping.** Beleidskompas covers the *policy process
  workflow* (drafting, structure, export); nLDT covers *grounded spatial
  analysis* (validated calculation models, maps, scenarios). Neither rebuilds
  the other — *wrap, don't rebuild* in both directions.
- **A concrete driver for Phase D / 5.3–5.4.** An external consumer forces the
  "one governed nLDT/MCP layer" to be real: stable tool surface, uniform
  ValidationReport, auth. Utrecht is both the nLDT pilot city and a GovChat-NL
  community participant (biweekly meeting with Overijssel, Flevoland,
  Meierijstad) — a natural bridge.

## 3. Integration principle

> **Beleidskompas narrates · nLDT computes · the civil servant decides.**

Beleidskompas' LLM never produces its own spatial numbers. Every spatial claim
in the policy document traces to a **recipe run** with a jobId,
**ValidationReport** and PROV bundle. This extends the leitmotif
(*LLMs propose · engines dispose · humans decide*) across an organisational
boundary: governance travels with the data as contracts, because we cannot
enforce code inside a foreign platform.

## 4. Options considered

| Option | Description | Verdict |
|---|---|---|
| **A — Tool consumer via MCP/A2A** | Beleidskompas (via its platform's workflow engine or directly — engine-agnostic, decision 6) mounts nLDT MCP servers or calls the A2A endpoint; each policy step maps to recipes | ✅ **Recommended** — reuses the governed tool surface as built; minimal changes on both sides |
| **B — Catalogued app in the nLDT App Store** | Beleidskompas registered as a new `application` record type in the catalog; twin instance config lists apps; future front doors discover and launch it | ✅ **Phase 2** — strategic payoff (App Store proof), small schema/seed extension; composes with A |
| **C — Plain HTTP from n8n to OGC API Processes** | n8n workflow calls `POST /processes/{id}/execution` directly, pastes results into chat | ⚠️ **Spike only** (BK-0) — fastest connectivity test, but bypasses the agent layer and makes ValidationReport gating easy to skip; not the target architecture |

**Recommendation:** A first, B on top of it, C only as a throwaway smoke test.

## 5. Target architecture

```text
GovChat-NL (province front door)                nLDT testbed
┌────────────────────────────────┐    ┌─────────────────────────────────────┐
│ OpenWebUI (chat, SSO, RBAC)    │    │ Keycloak realm LDT                  │
│  └─ App Launcher               │    │   client: beleidskompas-svc         │
│ Beleidskompas app              │    │ Catalog :8083  (apps + recipes)     │
│  policy steps · Word/PDF       │◀──▶│ MCP: catalog/process/poc/data       │
│ Kestra engine (pluggable)      │MCP │ A2A :8085 · Cookbook :8081          │
│ LiteLLM (narration models)     │A2A │ Cook :8082 (OGC API Processes)      │
└────────────────────────────────┘    │ hybrid_bridge → P&V · Web3D :8084   │
                                      │ ValidationReport + PROV per job    │
                                      └─────────────────────────────────────┘
```

### 5.1 Policy steps → nLDT capabilities

| Beleidskompas step | nLDT capability | Existing recipe / process | Output in beleidskompas |
|---|---|---|---|
| Problem definition · omgevingsanalyse | Five-value scan / overlay | `breda-five-value-scan`, `spatial-overlay-analysis` | Indicators + map layer |
| Location alternatives | Opportunity mapping | `utrecht-opportunity-map` | Opportunity map GeoJSON (P&V layer / Web3D export) |
| Scenario weighing (what-if) | Scenario sweep + author | `utrecht-scenario-sweep`, `utrecht-scenario-author` (S7) | Delta table + what-if viewer link |
| Substantiation Q&A | Grounded Q&A | `breda-scan-qa` → `breda-scan-query` (S4: cite-or-abstain + number gate) | Answer with citations, or recorded refusal |
| Export policy document | Run annex (new, §6) | jobId + ValidationReport + PROV per run | Traceability annex in Word/PDF |

Recipes stay area-based (AOI + layer inputs), so the pattern generalises from
the PoC areas (Utrecht/Breda/Eindhoven/Rijnland) to any province — including
Limburg, beleidskompas' origin.

### 5.2 Contracts used unchanged

- [`schemas/recipe.schema.json`](schemas/recipe.schema.json),
  [`schemas/process-invocation.schema.json`](schemas/process-invocation.schema.json) — invocation stays nLDT-conformant
- [`schemas/validation-report.schema.json`](schemas/validation-report.schema.json) — verdict gate surfaced in the beleidskompas UI
- [`schemas/web3d-context.schema.json`](schemas/web3d-context.schema.json) + `:8084/exports/{id}.geojson` — embeddable maps
- MCP tools ([`services/mcp_servers/`](services/mcp_servers/)): `search_records`, `list_processes`, `execute`, `get_job_status`, `ask_scan`, `propose_scenarios`, …

## 6. Governance extension — seam S9

Beleidskompas adds one new contact point to the
[seam catalogue](../docs/GENAI_SEAMS.md) (S1–S8 exist):

> **S9 — policy-document narration in an external front door.** An external
> platform's LLM drafts policy text that quotes nLDT results. The number-
> grounding gate cannot run *inside* the foreign platform, so governance
> moves to the contract: nLDT returns **grounded artifacts** (numbers,
> citations, ValidationReport, checksums) and beleidskompas must quote only
> from them; the Word/PDF export carries a **run annex** (jobIds,
> ValidationReports, PROV bundles) so any spatial number in the document is
> traceable and re-playable offline. Spot-checks are possible because every
> annex entry re-runs bit-identically.

Known divergence to record honestly: GovChat-NL routes to cloud models
(Azure/Vertex) while the nLDT PoCs run local open models. Because nLDT numbers
remain engine-computed and S9 grounds the narration, the residual risk is
narration-only — but it belongs in the integration's DPIA assessment, not
under the rug.

## 7. Identity and deployment

- **Service identity:** Keycloak client `beleidskompas-svc` (realm `LDT`,
  client_credentials) via [`services/adapters/keycloak_auth.py`](services/adapters/keycloak_auth.py) — same pattern as `nldt-agent`.
- **Prerequisite (roadmap gap):** the FastAPI services currently have **no
  auth middleware**. Before any external platform connects, bearer-token
  enforcement on `:8082/:8083/:8084/:8085` and the MCP servers is a hard
  blocker (folded into BK-1).
- **Topology for the MVP:** run GovChat-NL **locally** (Docker/source) next to
  the testbed — avoids exposing unauthenticated services publicly. Connecting
  to Limburg's instance comes later, behind auth + TLS.
- **Authorization mapping:** GovChat App-Launcher per-app RBAC ↔ nLDT twin
  instance `trustPolicy` (which recipes an app may see/run; `riskLevel: high`
  recipes require HITL approval inside the beleidskompas flow —
  `autoApproveHitl=false` on the A2A path).

## 8. Phased plan

### BK-0 — Connectivity spike (days)

**Status:** done — see [govchat/BK0-FINDINGS.md](govchat/BK0-FINDINGS.md) (bridge engine: Kestra, decision 6).

- Run GovChat-NL locally per their README; `./scripts/start-services.sh`.
- Kestra flow (Option C, throwaway; decision 6): webhook trigger → `POST :8082/processes/fetch-features/execution` on the layer-a example → publish features via `POST :8084/exports` → answer with the GeoJSON export URL. Every execution is kept as a per-task audit record (inputs/outputs per task, replayable) — extending the receipt-trail doctrine to the bridge layer. (The spec originally said n8n and `spatial-overlay-analysis/execution`; that id is a *recipe*, not a process, so the POST would 404 — corrected during execution.)
- Docs-only stance towards GovChat-NL (decision 5, §10): monitor their repo
  for beleidskompas releases; no community contact until the local MVP works.
  License verified from the repo in the meantime (§9): platform code is under
  the Open WebUI License.

**Done when:** a webhook-triggered bridge execution returns an nLDT-produced
export URL (verified `200`), with the execution's task-level I/O as the
audit record; findings written down. Surfacing in OpenWebUI chat is a
recorded human step (needs the front door's admin login).

### BK-1 — Governed MVP via MCP (1–2 sprints)

**Status:** done — see [govchat/README.md](govchat/README.md) (context3d :8084 left public, see §7).

- Beleidskompas mounts the nLDT MCP servers (`nldt-catalog-mcp`,
  `nldt-process-mcp`, `nldt-poc-mcp`) via its platform's engine or directly —
  engine-agnostic (decision 6); tool calls carry the
  `beleidskompas-svc` token. (Stdio remains the default; this phase adds
  MCP-over-streamable-HTTP on :8090–8093 behind the same bearer gate — see
  [govchat/README.md](govchat/README.md); stdio still suits co-located
  clients.)
- Wire two policy steps: omgevingsanalyse (five-value scan / overlay) and
  substantiation Q&A (`breda-scan-qa`, S4 pattern: cite-or-abstain + number
  gate).
- Auth: bearer middleware on services + MCP; Keycloak client provisioned.
- If step mapping needs it: new recipe `beleidskompas-omgevingsanalyse.json`
  in [`recipes/`](recipes/) wrapping existing processes (province AOI as
  input) — schema unchanged.
- Surface the ValidationReport verdict + citations in the beleidskompas UI.
- Tests: extend [`tests/`](tests/) (`test_http_services.py`,
  `test_phase2_adapters.py`) with auth-on cases and an end-to-end MCP call.

**Done when:** a policy question in beleidskompas returns an answer with
jobId, ValidationReport `pass` and citations — no ungated numbers.

### BK-2 — Beleidskompas as catalogued app (App Store proof)

- New catalog record type `application` + new
  `schemas/application.schema.json` (launchUrl, publisher,
  requiredCapabilities/scopes, trustLevel, docsUrl).
- Register beleidskompas in [`services/catalog_adapter/seed.py`](services/catalog_adapter/seed.py); twin instance config gains `apps` next to `recipes`.
- Optional: publish as Marketplace asset via
  [`services/marketplace_publish.py`](services/marketplace_publish.py).

**Done when:** `GET :8083/records?type=application` returns beleidskompas; a
twin instance lists it; demo shows discover → launch → consume-recipes.

### BK-3 — Governance hardening (S9)

- Specify and implement S9 (§6): grounded-artifact contract + **run annex
  generator** attached to the Word/PDF export; rejection/refusal ledger
  visible on both sides.
- HITL for `riskLevel: high` recipes inside the beleidskompas flow; RBAC ↔
  `trustPolicy` mapping implemented.
- OTel: propagate job/correlation IDs across the bridge → nLDT boundary
  ([09-federation-and-observability.md](09-federation-and-observability.md)).

**Done when:** an exported policy document contains zero untraceable spatial
numbers and its annex re-runs offline, bit-identically.

### BK-4 — Federation & Data Space (later; aligns with Phase 6 / EDIC)

- A2A skill `beleidskompas-policy-support` on the
  [`services/a2a/app.py`](services/a2a/app.py) agent card (next to
  `execute-recipe`, `export-3d-context`) so other front doors can federate.
- Provincial data (e.g. Limburg base layers) via the Data Space connector /
  `lake-publish-dataset` ([`schemas/dataspace-offer.schema.json`](schemas/dataspace-offer.schema.json)).
- Evaluate EU Toolbox Marketplace publication (Q4 2026 EDIC cross-border
  marketplace goal).

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Beleidskompas is *in development*; no code yet, interface may shift | Rework in BK-1+ | Couple to nLDT seams (MCP/OGC APIs), never to beleidskompas internals; keep BK-0 findings current via community contact |
| nLDT services lack auth middleware | Hard blocker for external connection | BK-1 starts with bearer enforcement (already a roadmap risk) |
| License: README states none, but the repo LICENSE is the Open WebUI License (modified BSD-3; branding clause with an exception ≤ 50 users / rolling 30 days) | Local-MVP platform reuse is covered; beleidskompas app code (in development) may carry separate terms | Re-check LICENSE when beleidskompas code lands; DPIA scope of the integration remains ours to assess (BK-3) |
| Cloud models (LiteLLM) vs local-model doctrine | Doctrinal divergence in narration layer | S9 grounded-artifact contract; record in DPIA; nLDT numbers stay engine-computed |
| Cross-org governance (who owns the app record, quality marks?) | App Store governance unresolved nationally | Start with testbed-internal registration (BK-2); feed experience into the App Store governance work (Geonovum/PDX) |
| Single-organisation bus factor (Limburg/CGI Smartlab build) | App may stall | Integration targets the GovChat-NL *platform* pattern (app-launcher + a workflow engine — engine pluggable, decision 6), which survives any single app |

## 10. Decisions (2026-09-14)

| # | Decision | Choice |
|---|---|---|
| 1 | BK-1 transport | **MCP** — beleidskompas/n8n mounts the nLDT MCP servers (aligns with Phase 5.3); an HTTP/SSE MCP transport is added only when a hosted GovChat-NL instance connects |
| 2 | MVP topology | **Local GovChat-NL instance** (Docker/source) beside the testbed; nLDT services are not exposed publicly until auth middleware exists |
| 3 | Demo area | **Existing PoC areas** (Utrecht/Breda lake data and recipes); no Limburg AOI data work in the MVP |
| 4 | `application` record type (BK-2) | **After the BK-1 MVP** proves the consumption loop |
| 5 | GovChat-NL engagement | **Docs-only** until the local MVP works, then approach the community (biweekly meeting) with a working demo; license verified from the repo in the meantime (§9) |
| 6 | Bridge/orchestration engine (added mid-execution, 2026-09-14) | **Kestra** — Apache-2.0 (n8n's Sustainable-Use license is not open source), flow-as-code in git, per-task execution I/O records and replay = the auditability the nLDT receipt-trail doctrine demands; doubles as scheduler for the future source monitor. Node-RED rejected (no persisted per-message history); Activepieces rejected (DB-stored builder flows); OpenWebUI-native tool kept as a future option (needs admin login). The nLDT seams (MCP/OGC-HTTP) stay engine-agnostic — any engine can drive them. |

## 11. References

- GovChat-NL: <https://github.com/jeannotdamoiseaux/GovChat-NL> ·
  beleidskompas doc:
  <https://github.com/jeannotdamoiseaux/GovChat-NL/blob/main/docs/app-launcher/beleidskompas/beleidskompas.md> ·
  LICENSE (Open WebUI License, modified BSD-3):
  <https://github.com/jeannotdamoiseaux/GovChat-NL/blob/main/LICENSE>
- nLDT App Store frame: *NLDT Q3 2026 Quarterly Report — Summary in English
  (App Store Focus)* (repo root)
- Kestra (bridge/orchestration engine, decision 6): <https://kestra.io/> ·
  n8n license context (Sustainable Use License): <https://docs.n8n.io/sustainable-use-license/>
- Internal: [04-recipes-and-processes.md](04-recipes-and-processes.md) ·
  [12-governed-agent-layer.md](12-governed-agent-layer.md) ·
  [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) ·
  [`../docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md)
