# nLDT — Comprehensive architecture

Hub document for the **Nederlandse Local Digital Twin** reference implementation
under [`nldt/`](./). Use this page to navigate views, contracts, PoCs, the data
lake / Data Space, and the governed agent layer. Detail lives in the numbered
docs; this file wires them together.

| | |
|---|---|
| Status | Living overview · aligned with Phase 5–6 + beleidskompas/eID-wallet + EuropAI WP4 EDIC handover (2026-09-20) |
| Companion (Utrecht pilot SoA) | [`../docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md) |
| GenAI seams | [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) |
| Multi-agent plan | [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) |
| Roadmap | [`08-roadmap.md`](08-roadmap.md) |

**Leitmotif:** *LLMs propose · engines dispose · humans decide*  
([07-trust-and-governance.md](07-trust-and-governance.md), Data Space HITL in
[13-data-lake-and-space.md](13-data-lake-and-space.md)).

---

## 1. How to read this set

| If you need… | Start here |
|--------------|------------|
| Vision & non-goals | [01-vision-and-scope.md](01-vision-and-scope.md) |
| Triangle + EDIC/Toolbox mapping | [02-reference-architecture.md](02-reference-architecture.md) |
| Building blocks by working group | [03-building-blocks.md](03-building-blocks.md) |
| AppStore → Cookbook → Cook | [04-recipes-and-processes.md](04-recipes-and-processes.md) |
| Agents, MCP, LangGraph | [05-agentic-ai-layer.md](05-agentic-ai-layer.md) |
| EU LDT Toolbox adapters | [06-hybrid-implementation.md](06-hybrid-implementation.md), [10-toolbox-integration.md](10-toolbox-integration.md) |
| V0–V4, PROV, cite-or-abstain | [07-trust-and-governance.md](07-trust-and-governance.md) |
| Phases & success criteria | [08-roadmap.md](08-roadmap.md) |
| 3D / A2A / OTel / Marketplace | [09-federation-and-observability.md](09-federation-and-observability.md) |
| PoC patterns (scenarios, QA) | [11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md) |
| One agent layer over all PoCs | [12-governed-agent-layer.md](12-governed-agent-layer.md) |
| Data lake + Iceberg/dbt + Data Space | [13-data-lake-and-space.md](13-data-lake-and-space.md) |
| GovChat-NL beleidskompas integration (plan) | [14-beleidskompas-integration.md](14-beleidskompas-integration.md) |
| eID Wallet identity layer (plan) | [16-eid-wallet-identity.md](16-eid-wallet-identity.md) |
| Interactive architecture (URL routes) | [`simulation/poc-mcp-skills.html`](simulation/poc-mcp-skills.html) (`?poc=lifecycle\|router\|breda\|edic\|utrecht\|rijnland\|eindhoven`) |
| EuropAI WP4 EDIC handover | [21-europai-edic-handover.md](21-europai-edic-handover.md) · schematic [edic/breda-route-map.md](edic/breda-route-map.md) · tour `?poc=edic` |
| Dual-audience front doors (planners + public, plan) | [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md) |
| DTAS alignment (Digital Twin App Store vision, plan) | [23-dtas-alignment.md](23-dtas-alignment.md) |
| Zicht op Nederland national vision alignment (plan) | [24-zichtopnl-alignment.md](24-zichtopnl-alignment.md) |
| IMB (Inter Model Broker) role mapping | [25-imb-alignment.md](25-imb-alignment.md) |
| Bibliography | [references/bibliography.md](references/bibliography.md) |
| Quick start / ports | [README.md](README.md) |

---

## 2. Context: where nLDT sits

```text
 External standards / programmes          This repo
 ┌─────────────────────────────┐         ┌──────────────────────────────────┐
 │ Geonovum NLDT RA            │         │ nldt/   reference interfaces     │
 │ LDT CitiVERSE EDIC RA       │────────▶│         + agentic layer          │
 │ nLDT Testbed 2026 (phase 2) │         │ poc*/   domain engines (SoT)     │
 │ EU LDT Toolbox catalogue    │         │ docs/   Utrecht solutions arch   │
 └─────────────────────────────┘         │ ldtsolutions/  K8s deploy        │
                                         └──────────────────────────────────┘
```

| External | Link |
|----------|------|
| NLDT Reference Architecture | https://geonovum.github.io/NLDT-Architectuur/ |
| Digital Twin as a Service (Geonovum) | https://www.geonovum.nl/index.php/themas/digital-twins |
| LDT CitiVERSE EDIC RA | https://github.com/Geonovum/ldt-citiverse-edic-ra |
| EU LDT Toolbox Solutions Catalogue | https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue |
| Testbed phase 2 invitation (PDF) | [nldt-testbed2026-phase2-invitation-to-tender.pdf](nldt-testbed2026-phase2-invitation-to-tender.pdf) |

**Wrap, don’t rebuild:** province / water board authoritative services stay
engines; nLDT adds catalog, processes, recipes, agents, validation, lake /
Data Space ([SOLUTIONS_ARCHITECTURE §1](../docs/SOLUTIONS_ARCHITECTURE.md)).

---

## 3. Logical views

### 3.1 nLDT triangle + foundation

From [02-reference-architecture.md](02-reference-architecture.md):

```text
                 Visualisation & UX
                /                \
       Data & sensors ---- Processing & Intelligence
                \                /
                 === Foundation ===
          (catalog, IAM, trust, audit)
```

| Corner | nLDT interface | Primary code |
|--------|----------------|--------------|
| Data | OGC Features / NGSI-LD | [`services/adapters/`](services/adapters/), lake silver |
| Processing | **OGC API Processes**, Recipes | [`services/process_adapter/`](services/process_adapter/), [`recipes/`](recipes/) |
| Visualisation | GeoJSON / Web 3D Context | [`services/context3d/`](services/context3d/), Play & Visualise |
| Foundation | OGC API Records, OIDC / EUDI-wallet identity, PROV | [`services/catalog_adapter/`](services/catalog_adapter/), [`services/common/auth.py`](services/common/auth.py), [`schemas/`](schemas/) |

Diagram: [`diagrams/container-view.mmd`](diagrams/container-view.mmd).

### 3.2 Layer stack (EDIC-aligned)

| Layer | Responsibility | Docs |
|-------|----------------|------|
| Agentic AI | Plan, call tools, HITL | [05](05-agentic-ai-layer.md), [12](12-governed-agent-layer.md) |
| Application | Catalog, Cookbook, Process adapter | [03](03-building-blocks.md), [04](04-recipes-and-processes.md) |
| nLDT interfaces | Records / Processes / Recipe schema | [`schemas/`](schemas/) |
| Implementation | EU Toolbox + PoC engines | [06](06-hybrid-implementation.md), [10](10-toolbox-integration.md) |
| Data plane | Medallion lake + lakehouse | [13](13-data-lake-and-space.md) |
| Infrastructure | Local FS / MinIO / K8s | [docker-compose.lake.yml](docker-compose.lake.yml), [`../ldtsolutions/`](../ldtsolutions/) |

### 3.3 Agentic planes (PoC)

Diagram: [`diagrams/agentic-planes.mmd`](diagrams/agentic-planes.mmd).  
Patterns A/B/C and S4/S7/S8: [11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md),
[`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md).

---

## 4. AppStore → Cookbook → Cook

Canonical Testbed mapping ([04-recipes-and-processes.md](04-recipes-and-processes.md)):

| Role | Function | Implementation | Default port |
|------|----------|----------------|--------------|
| **AppStore** | Discover assets | [`catalog_adapter`](services/catalog_adapter/) (OGC API Records) | `:8083` |
| **Cookbook** | Recipe definitions | [`cookbook`](services/cookbook/), [`recipes/*.json`](recipes/) | `:8081` |
| **Cook** | Execute process steps | [`process_adapter`](services/process_adapter/) (OGC API Processes) | `:8082` |

```text
Agent / CLI
    │  search Records
    ▼
Catalog (AppStore) ──rel=recipe──▶ Cookbook GET /recipes/{id}
    │
    │  each step.processId
    ▼
Process adapter (Cook) ──▶ poc_handlers / GIS / H3
    │
    ▼
PoC engine (authoritative calculation)
```

**Contracts**

| Schema | Path |
|--------|------|
| Recipe | [`schemas/recipe.schema.json`](schemas/recipe.schema.json) |
| Process invocation | [`schemas/process-invocation.schema.json`](schemas/process-invocation.schema.json) |
| Validation report | [`schemas/validation-report.schema.json`](schemas/validation-report.schema.json) |
| Agent plan | [`schemas/agent-plan.schema.json`](schemas/agent-plan.schema.json) |
| Web 3D Context | [`schemas/web3d-context.schema.json`](schemas/web3d-context.schema.json) |
| Data Space offer (ODRL stub) | [`schemas/dataspace-offer.schema.json`](schemas/dataspace-offer.schema.json) |
| Application (App Store record) | [`schemas/application.schema.json`](schemas/application.schema.json) |
| Wallet claims (EUDI / agent) | [`schemas/wallet-claims.schema.json`](schemas/wallet-claims.schema.json) |
| Run annex (seam S9 receipts) | [`schemas/run-annex.schema.json`](schemas/run-annex.schema.json) |

---

## 5. OGC Processes and the data lake pipeline

**Important:** Processes are **not** executed inside Iceberg/dbt. The lake is
storage + catalog; Cook runs engines. Full write-up:
[13 § OGC Processes in the lake pipeline](13-data-lake-and-space.md#ogc-processes-in-de-lake-pipeline).

Diagram: [`diagrams/data-lake-space.mmd`](diagrams/data-lake-space.mmd).

```text
 Ingest (offline)          Runtime                         Analytics
 ───────────────           ───────                         ─────────
 ArcGIS/PDOK/WKP    →  bronze/silver
                            │
                     lake:// or file:// cache
                            │
 Recipes / Agent  →  OGC Processes (Cook)  →  PoC engines
                            │
                            ▼
                         gold (+ PROV)
                            │
                     inventory → Iceberg → dbt marts
                            │
                     lake-publish-dataset → Data Space offers
```

| Concern | Mechanism | Code |
|---------|-----------|------|
| Resolve lake inputs | `lake://` / `s3://` in `_load_source` | [`handlers.py`](services/process_adapter/handlers.py) |
| PoC wrappers | `execute_*` | [`poc_handlers.py`](services/process_adapter/poc_handlers.py) |
| Gold after recipe | `NLDT_LAKE_POST_RUN` → `upload_execution_gold` | [`hybrid_bridge.py`](services/hybrid_bridge.py), [`publish.py`](services/lake/publish.py) |
| Sync working set → lake | idempotent sha256 | [`lake_sync.py`](scripts/lake_sync.py), [`sync.py`](services/lake/sync.py) |
| Publish offer | process `lake-publish-dataset` | [`handlers.py`](services/process_adapter/handlers.py), [`dataspace_connector.py`](services/adapters/dataspace_connector.py) |

### Registered Cook processes (selection)

| processId | Doc / notes |
|-----------|-------------|
| GIS + H3 family | [04](04-recipes-and-processes.md) |
| `opportunity-map-run`, `scenario-*`, `crosstrack-overlay` | Utrecht · [12](12-governed-agent-layer.md) |
| `breda-scan-run`, `breda-scan-query` | Breda S4 · [11](11-poc-patterns-scenarios-qa.md) |
| `rijnland-peil-conflict` | Rijnland peil · recipe [`recipes/rijnland-peil-conflict.json`](recipes/rijnland-peil-conflict.json) |
| `rijnland-peil-whatif` | Peilen what-if → CDC lake + multi-scenario Leaflet map · [15](15-cdc-data-lake-pipeline.md) |
| `lake-publish-dataset` | Data Space · [13](13-data-lake-and-space.md) |

Tests: [`tests/test_poc_processes.py`](tests/test_poc_processes.py),
[`tests/test_lake.py`](tests/test_lake.py).

---

## 6. Data lake & lakehouse

Detail: [13-data-lake-and-space.md](13-data-lake-and-space.md).  
dbt project: [`dbt_lake/README.md`](dbt_lake/README.md).

### Medallion zones

| Zone | Content | Example keys |
|------|---------|--------------|
| **bronze** | Raw snapshots | `bronze/rijnland/arcgis/…`, WKP zips |
| **silver** | Normalized dual-CRS / manifests | `silver/utrecht/geo/…` |
| **gold** | Validated runs + PROV | `gold/{poc}/run/{runId}/…` |

Object layout also under `nldt/data/lake/` when `NLDT_LAKE_BACKEND=fs`.

### accessClass → Data Space

| Class | Publish |
|-------|---------|
| `open` | May become public offer |
| `internal` | Participant policy |
| `restricted` | No auto-offer; HITL (`forceHitlApproved`) |

Config: [`data/lake-deny.json`](data/lake-deny.json) ·
Inventory: [`data/lake-inventory.json`](data/lake-inventory.json).

### Lakehouse stack

| Layer | Tech | Entry |
|-------|------|-------|
| Object store | FS / MinIO | [`docker-compose.lake.yml`](docker-compose.lake.yml) |
| Table format | **Apache Iceberg** (PyIceberg SqlCatalog) | [`services/lake/iceberg.py`](services/lake/iceberg.py) |
| Query | **DuckDB** | [`services/lake/__init__.py`](services/lake/__init__.py) |
| Transforms | **dbt Core** + `dbt-duckdb` | [`dbt_lake/`](dbt_lake/) |

One-shot refresh:

```bash
cd nldt && PYTHONPATH=. python scripts/lake_lakehouse_refresh.py
```

Scripts: [`build_lake_inventory.py`](scripts/build_lake_inventory.py),
[`lake_iceberg_bootstrap.py`](scripts/lake_iceberg_bootstrap.py),
[`lake_lakehouse_refresh.py`](scripts/lake_lakehouse_refresh.py),
[`fetch_arcgis_static.py`](../poc-rijnland/scripts/fetch_arcgis_static.py)
(Rijnland ArcGIS → bronze).

---

## 7. PoC engines (source of truth)

| PoC | Path | nLDT surface |
|-----|------|--------------|
| Utrecht opportunity / scenario / crosstrack | [`../poc/`](../poc/) | processes + recipes · [SOLUTIONS_ARCHITECTURE](../docs/SOLUTIONS_ARCHITECTURE.md) |
| Breda five-value scan | [`../poc-breda/`](../poc-breda/) | `breda-scan-*` |
| Rijnland peil conflict + peilen what-if (CDC) | [`../poc-rijnland/`](../poc-rijnland/) | `rijnland-peil-conflict`, `rijnland-peil-whatif` · ArcGIS lake bronze · [15](15-cdc-data-lake-pipeline.md) |
| Eindhoven BP2OP | [`../poc-bp2op/`](../poc-bp2op/) | process + recipe `eindhoven-bp2op` ([12 §5.5](12-governed-agent-layer.md)) |

Governed agent layer plan: [12-governed-agent-layer.md](12-governed-agent-layer.md).  
Simulation UX (not production agent): [`simulation/`](simulation/) —
interactive architecture with routes
[`poc-mcp-skills.html`](simulation/poc-mcp-skills.html)
(`?poc=breda`, `?poc=edic` for the CitiVERSE-first map with Breda as city illustration).

---

## 8. Agentic AI & trust

| Topic | Doc | Code |
|-------|-----|------|
| Orchestrator (LangGraph) | [05](05-agentic-ai-layer.md) | [`agents/orchestrator/`](agents/orchestrator/) |
| MCP servers | [05](05-agentic-ai-layer.md) | [`services/mcp_servers/`](services/mcp_servers/) |
| Critic V0–V4, HITL | [07](07-trust-and-governance.md) | PoC `critic` + ValidationReport schema |
| Cite-or-abstain / S4–S8 | [11](11-poc-patterns-scenarios-qa.md), [GENAI_SEAMS](../docs/GENAI_SEAMS.md) | per-PoC seams |
| A2A / OTel | [09](09-federation-and-observability.md) | [`services/a2a/`](services/a2a/), telemetry |
| **Wallet identity (EUDI + EBW) & trust gates** | [16](16-eid-wallet-identity.md) | [`services/auth_wallet/`](services/auth_wallet/), [`services/agent_wallet/`](services/agent_wallet/), [`services/common/trust_policy.py`](services/common/trust_policy.py) |
| Beleidskompas front-door app | [14](14-beleidskompas-integration.md) | [`govchat/`](govchat/) |

Principle for lake publication and agent proposals: same HITL gate —
restricted Data Space offers require explicit approval
([13](13-data-lake-and-space.md)).

---

## 9. Hybrid EU LDT Toolbox

| Toolbox capability | nLDT adapter | Doc |
|--------------------|--------------|-----|
| Data Platform (NGSI-LD) | [`adapters/data_platform`](services/adapters/) | [10](10-toolbox-integration.md) |
| Play & Visualise | [`adapters/play_visualise`](services/adapters/) | [10](10-toolbox-integration.md) |
| Identity (Keycloak) | env / OIDC · wallet convergence W2/W6 ([16](16-eid-wallet-identity.md)) | [10](10-toolbox-integration.md) |
| Marketplace | [`marketplace_publish.py`](services/marketplace_publish.py) | [09](09-federation-and-observability.md) |
| Post-run hooks | [`hybrid_bridge.py`](services/hybrid_bridge.py) | [06](06-hybrid-implementation.md) |
| Cluster deploy | — | [`../ldtsolutions/`](../ldtsolutions/), skill `ldt-toolbox-deploy` |

---

## 10. Runtime map (dev)

| Service | Module | Port |
|---------|--------|------|
| Cookbook | `services.cookbook.app` | 8081 |
| Processes | `services.process_adapter.app` | 8082 |
| Catalog | `services.catalog_adapter.app` | 8083 |
| Web 3D Context (deliberately public exports) | `services.context3d.app` | 8084 |
| A2A | `services.a2a.app` | 8085 |
| Wallet auth edge (W1) | `services.auth_wallet.app` | 8087 |
| Agent virtual wallet (W5) | `services.agent_wallet.app` | 8088 |
| MCP over streamable-HTTP | `services.mcp_servers.*` (`NLDT_MCP_TRANSPORT`) | 8090–8093 |

Auth: `NLDT_AUTH_MODE=off|static|keycloak|wallet` ([`services/common/auth.py`](services/common/auth.py));
trust gates: `NLDT_TRUST_POLICY_FILE` ([`services/common/trust_policy.py`](services/common/trust_policy.py)).
Agent identity (W6a, real Keycloak credentials): `NLDT_WALLET_VERIFIER=mock|keycloak`
(edge verifier), `NLDT_AGENT_WALLET_BACKEND=mock|keycloak` + per-agent
`NLDT_AGENT_*_CLIENT_SECRET` (virtual wallet), registry
`NLDT_AGENT_CREDENTIALS_FILE` ([`16 §W6a`](16-eid-wallet-identity.md));
provision with [`scripts/provision_agent_clients.py`](scripts/provision_agent_clients.py).
External (local Docker): Kestra bridge `:8086` ([`govchat/`](govchat/)), OpenWebUI `:8080`,
MinIO (optional lake) `9000/9001` ([`docker-compose.lake.yml`](docker-compose.lake.yml)).

Start: [`scripts/start-services.sh`](scripts/start-services.sh) ·
[README quick start](README.md#snel-starten).

CLI: `PYTHONPATH=. python -m services.cli …`

---

## 11. End-to-end sequences (index)

| Flow | Where described |
|------|-----------------|
| Recipe without agent | [04](04-recipes-and-processes.md), README CLI |
| Agent find → execute → validate | [05](05-agentic-ai-layer.md), [08 verification](08-roadmap.md) |
| Process ↔ lake I/O | [13 § OGC Processes](13-data-lake-and-space.md#ogc-processes-in-de-lake-pipeline) |
| Lakehouse refresh | [13 § Lakehouse](13-data-lake-and-space.md#lakehouse-stack-duckdb--iceberg--dbt-core) |
| Publish Data Space offer | process `lake-publish-dataset` · [13 § Data Space](13-data-lake-and-space.md#data-space-participant) |
| Utrecht wind/solar/forest opportunity map | [SOLUTIONS_ARCHITECTURE](../docs/SOLUTIONS_ARCHITECTURE.md) |
| Rijnland peil conflict | [`../poc-rijnland/README.md`](../poc-rijnland/README.md) · process `rijnland-peil-conflict` |
| Rijnland peilen what-if (CDC + scenario map) | [15](15-cdc-data-lake-pipeline.md) · process `rijnland-peil-whatif` · MCP tool `run_peil_whatif` |

---

## 12. Roadmap snapshot

| Phase | Theme | Doc |
|-------|-------|-----|
| 1–2 | Catalog, Processes, Recipes, Toolbox hooks | [08](08-roadmap.md), [10](10-toolbox-integration.md) |
| 3–4 | Federation, 3D, A2A, OTel | [09](09-federation-and-observability.md) |
| **5** | Governed agent layer over PoCs | [12](12-governed-agent-layer.md) |
| **6** | Data lake + Data Space + lakehouse | [13](13-data-lake-and-space.md) ✅ |
| **6b** | CDC pipeline in the lake (Rijnland peilen) | [15](15-cdc-data-lake-pipeline.md) |
| **BK** | Beleidskompas front-door app (BK-0…BK-2 done; BK-3 = wallet track) | [14](14-beleidskompas-integration.md) |
| **W** | eID Wallet identity (W1/W3/W5 done, mock; **W6a done: real Keycloak agent credentials**; W2/W6 real backend) | [16](16-eid-wallet-identity.md) |
| **SM** | Source monitor (open-data continuity) | [17](17-source-monitor.md) ✅ |
| **DONL** | data.overheid.nl CKAN harvest → lake + Data Space | [18](18-donl-harvest.md) ✅ |

Open highlights: OTLP exporter ([08](08-roadmap.md)); wallet W2 (real OpenID4VP
verifier) + W6 (Keycloak OID4VCI issuance) — decision-gated on toolbox IM
([16](16-eid-wallet-identity.md)).
Phase 5, Phase 6, and the source-monitor MVP are **done** — see
[12](12-governed-agent-layer.md), [13](13-data-lake-and-space.md),
[17](17-source-monitor.md).

---

## 13. Repository map

```text
ldttoolbox/
├── nldt/                          ← this architecture package
│   ├── 00-architecture.md         ← YOU ARE HERE
│   ├── 01…13-*.md                 ← topic docs
│   ├── diagrams/*.mmd
│   ├── schemas/
│   ├── services/                  ← adapters + lake + processes
│   ├── agents/orchestrator/
│   ├── recipes/
│   ├── govchat/                  ← beleidskompas/wallet runbook + bridge artifacts
│   ├── dbt_lake/
│   ├── data/lake/                 ← FS lake + iceberg warehouse
│   └── tests/
├── poc/  poc-breda/  poc-rijnland/  poc-bp2op/
├── docs/SOLUTIONS_ARCHITECTURE.md · GENAI_SEAMS.md
├── MULTI_AGENT_PLAN.md
└── ldtsolutions/                  ← K8s / toolbox deploy
```

---

## 14. Related parent-repo documents

| Document | Role |
|----------|------|
| [`../docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md) | Utrecht multi-track solutions architecture (modules, V0–V4, FAIR/Data Space A4) |
| [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) | GenAI seam catalogue & gates |
| [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) | General multi-agent plan |
| [`../poc-rijnland/README.md`](../poc-rijnland/README.md) | Rijnland PoC-3 |
| [`../poc-breda/`](../poc-breda/) | Breda scan PoC |
| [`../poc/`](../poc/) | Utrecht opportunity / scenario / crosstrack |

---

*Maintained with the nLDT numbered docs. Prefer linking here from README and
onboarding; keep deep design in 01–13, the Utrecht SoA, and the EuropAI EDIC
handover ([21](21-europai-edic-handover.md)).*
