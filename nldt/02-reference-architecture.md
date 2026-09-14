# 02 — Reference architecture

> Navigation hub with all views and links: [`00-architecture.md`](00-architecture.md).

## nLDT triangle model + foundation

Geonovum uses a **triangle model** (Walter Lohman, TNO) with a central **Foundation**:

```
                    Visualisation & UX
                   /                \
                  /                  \
         Data & sensors ---- Processing & Intelligence
                   \                  /
                    \                /
                     === Foundation ===
              (management, trustworthiness, identity)
```

| Corner | Function | Standards (nLDT) |
|--------|----------|------------------|
| Data & sensors | Sources, dynamic data | OGC API Features, NGSI-LD, SensorThings |
| Processing | Compute modules, AI, simulation | **OGC API Processes**, Recipes |
| Visualisation | 2D/3D, dashboards | 3D Tiles, Web 3D Context Document |
| Foundation | Catalog, IAM, audit | OGC API Records, OAuth2/OIDC, PROV |

## Layers (EDIC + nLDT)

| Layer | EDIC pattern | nLDT realisation |
|-------|--------------|------------------|
| Agentic AI | AI & Analytics (pipeline) | LangGraph orchestrator, MCP tools |
| Application | Shared services | Catalog, Cookbook, Process adapter |
| nLDT interfaces | Semantic interoperability | Records, Processes, Recipe schema |
| Implementation | Toolbox-based (ABB/SBB) | EU LDT UCS, DPL, P&V, IM |
| Infrastructure | Federated, infra-agnostic | K8s (ldtsolutions), local dev |

## Mapping NLDT ↔ EDIC ↔ EU Toolbox

| nLDT working group | EDIC business domain | EU LDT Toolbox | nLDT interface |
|--------------------|---------------------|----------------|----------------|
| Data & sensors | Context awareness | Data Platform | OGC Features / NGSI-LD |
| Compute models | Processing services | UCS + AI Notebook | OGC API Processes |
| Visualisation | Visualisation | Play & Visualise | Layer URI / 3D Context |
| Foundation catalog | Data exchange | Marketplace Agent | OGC API Records |
| Foundation orchestration | Orchestration | Airflow (UCS) | Recipe + LangGraph |
| Foundation identity | Integration | Identity Management | OIDC |
| Foundation trust | Maturity / governance | Run artifacts | PROV + ValidationReport |

## Agentic extension

The agentic layer sits **above** the nLDT interfaces — agents never talk directly to UCS internals:

```
User / Agent orchestrator
        │
        ▼ MCP (catalog, process, data, viz)
        ▼
┌───────────────────────────────────────┐
│  OGC API Records │ Processes │ Recipe │
└───────────────────────────────────────┘
        │
        ▼ Adapters
┌───────────────────────────────────────┐
│  Marketplace │ pygeoapi │ UCS │ DPL  │
└───────────────────────────────────────┘
```

## Three agentic planes (PoC patterns)

Besides generic **recipe orchestration** (LangGraph), the architecture includes three
legal-spatial planes from the Utrecht PoC — see
[11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md):

| Plane | Pattern | Core agents / QA |
|-------|---------|------------------|
| **A Opportunity-map** | Cite-or-abstain → NormCard → FormalRule → Zone → DecisionTable | Norm Analyst, Formalizer, Zone engine, Critic V0–V4 |
| **B Scenario-sweep** | AI proposes variants (S7); engine computes Δ/IoU | Scenario Author + Scenario Critic (control reproduction) |
| **C Crosstrack** | Pairwise conflict overlay between tracks | Crosstrack Critic (V2 N/A; V4 = arbitration) |

Rule: **AI proposes. Pipeline disposes. Human decides.** LLMs never touch zones,
rules, or maps — only proposals on a fixed schema (+ reject ledger).

## Processing pipeline (EDIC Pattern 7)

```
Data Sources → Integration → Semantic Enrichment → Processing
    → AI & Analytics → Visualisation → Decision Support → Action
```

In this implementation:

- **Processing** = OGC API Processes + (PoC) Zone Engine
- **AI & Analytics** = agent orchestration + GenAI seams S1–S3 (recipes) and S7–S8 (scenarios/narrative)
- **Decision Support** = Critic V0–V4 + DecisionTable + HITL (V4)

## Diagrams

- [diagrams/container-view.mmd](diagrams/container-view.mmd) — container view
- [diagrams/agentic-planes.mmd](diagrams/agentic-planes.mmd) — planes A/B/C + LangGraph
