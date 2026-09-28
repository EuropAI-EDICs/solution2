# nLDT — Agentic Digital Twin

Generic reference implementation of a **Dutch Local Digital Twin (nLDT)** for agentic AI, aligned with Geonovum NLDT architecture, LDT CitiVERSE EDIC and the nLDT Testbed 2026.

## Scope

- **Use-case-agnostic** — no domain-specific regulation in the core
- **Hybrid platform** — nLDT standards (OGC API Records/Processes, Recipes) as external interface; EU LDT Toolbox as implementation where possible
- **Agentic AI** — orchestrator + MCP tool servers; principle *LLMs propose, engines dispose*

## Documentation

| Doc | Topic |
|-----|-------|
| [**00-architecture.md**](00-architecture.md) | **Hub:** comprehensive architecture + links (start here) |
| Interactive architecture | [`simulation/poc-mcp-skills.html`](simulation/poc-mcp-skills.html) (`?poc=…`, including `edic`) |
| [01-vision-and-scope.md](01-vision-and-scope.md) | Vision, goals, scope |
| [02-reference-architecture.md](02-reference-architecture.md) | Triangle + foundation; mapping NLDT ↔ EDIC ↔ EU Toolbox |
| [03-building-blocks.md](03-building-blocks.md) | Building blocks per working group |
| [04-recipes-and-processes.md](04-recipes-and-processes.md) | AppStore / Cookbook / Cook |
| [05-agentic-ai-layer.md](05-agentic-ai-layer.md) | Agents, MCP, LangGraph + PoC planes |
| [06-hybrid-implementation.md](06-hybrid-implementation.md) | Adapter layer to EU LDT Toolbox |
| [07-trust-and-governance.md](07-trust-and-governance.md) | Validation V0–V4, cite-or-abstain, PROV, HITL |
| [08-roadmap.md](08-roadmap.md) | Phasing and success criteria |
| [09-federation-and-observability.md](09-federation-and-observability.md) | Phase 4: 3D Context, A2A, Marketplace, OTel |
| [10-toolbox-integration.md](10-toolbox-integration.md) | Phase 2: Data Platform, P&V, Keycloak |
| [11-poc-patterns-scenarios-qa.md](11-poc-patterns-scenarios-qa.md) | **PoC patterns**: scenarios, QA, cite-or-abstain |
| [12-governed-agent-layer.md](12-governed-agent-layer.md) | **Phase 5:** one nLDT/MCP layer across all PoCs |
| [13-data-lake-and-space.md](13-data-lake-and-space.md) | **Phase 6:** data lake + DuckDB/Iceberg/dbt + Data Space |
| [14-beleidskompas-integration.md](14-beleidskompas-integration.md) | **Plan:** GovChat-NL beleidskompas as first external front-door app |
| [15-cdc-data-lake-pipeline.md](15-cdc-data-lake-pipeline.md) | **Implemented:** CDC lake pipeline + Rijnland peilen what-if map (multi-scenario) |
| [16-eid-wallet-identity.md](16-eid-wallet-identity.md) | **Plan:** EU Digital Identity Wallet identity layer (BK-3 re-scope) |
| [17-source-monitor.md](17-source-monitor.md) | **MVP:** open-data continuity probes + human-merge patches |
| [18-donl-harvest.md](18-donl-harvest.md) | **Implemented:** data.overheid.nl CKAN harvest → lake + Data Space |
| [19-s10-deep-research.md](19-s10-deep-research.md) | **S10:** Deep Research seam — gebruik, CLI, stub vs Deep Agents |
| [20-poc-mcp-skills.md](20-poc-mcp-skills.md) | **Skeleton:** PoC playbooks as Agent Skills over MCP (`skill://`, SEP-2640) |
| [21-europai-edic-handover.md](21-europai-edic-handover.md) | **EuropAI WP4:** asset-push map, EDIC fit statements, CitiVERSE live path |
| [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md) | **Plan:** one governed core, front doors for planners and the public (S11, DA-0…4) |
| [23-dtas-alignment.md](23-dtas-alignment.md) | **Plan:** DTAS alignment — recipes as DTAS modules, module passport, Marketplace (DT-0…4) |

## Code

```
nldt/
├── schemas/              JSON Schema contracts (+ web3d-context)
├── services/
│   ├── catalog_adapter/  OGC API Records (Marketplace wrapper)
│   ├── process_adapter/  OGC API Processes facade
│   ├── cookbook/         Recipe definitions API
│   ├── context3d/        Web 3D Context import/export (:8084)
│   ├── a2a/              A2A agent endpoint (:8085)
│   ├── adapters/       Data Platform, P&V, Keycloak
│   ├── hybrid_bridge.py Post-execution toolbox hooks
│   ├── marketplace_publish.py
│   └── mcp_servers/      catalog, process, data MCP servers
├── agents/orchestrator/  LangGraph orchestrator
├── agents/breda_scenario/ Breda what-if LangGraph (+ S10)
├── agents/seams/         GenAI seams (S10 deep research)
├── skills/poc/           Agent Skills for PoC MCP tools (SEP-2640)
├── recipes/              Reference recipes + edic-asset-map.json
├── edic/                 EuropAI WP4 EDIC fit statements and declarations
└── simulation/           Mock demo visualisation (HTML)
```
## External references

- [NLDT Reference Architecture](https://geonovum.github.io/NLDT-Architectuur/)
- [Digital Twin as a Service (Geonovum)](https://www.geonovum.nl/index.php/themas/digital-twins)
- [LDT CitiVERSE EDIC RA](https://github.com/Geonovum/ldt-citiverse-edic-ra)
- [nldt-testbed2026-phase2-invitation-to-tender.pdf](nldt-testbed2026-phase2-invitation-to-tender.pdf)
- [EU LDT Toolbox Solutions Catalogue](https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue)
- [EuropAI WP4 EDIC handover](21-europai-edic-handover.md)

Related in this repo: [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md), [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md), [`../ldtsolutions/`](../ldtsolutions/).

## Quick start

```bash
cd nldt
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Services (separate terminals, or all at once)
./scripts/start-services.sh

# Or manually:
python -m services.cookbook.app          # :8081
python -m services.process_adapter.app   # :8082
python -m services.catalog_adapter.app   # :8083
python -m services.context3d.app         # :8084
python -m services.a2a.app               # :8085

# End-to-end without agent
PYTHONPATH=. python -m services.cli run-recipe spatial-overlay-analysis \
  --aoi-file examples/rijnsweerd/aoi.geojson \
  --input layerAUri=file://$(pwd)/examples/rijnsweerd/layer-a.geojson \
  --input layerBUri=file://$(pwd)/examples/rijnsweerd/layer-b.geojson

# Fetch 3D BAG data for Rijnsweerd
python scripts/fetch_3dbag_rijnsweerd.py

# Marketplace publish (mock) + 3D context export
PYTHONPATH=. python -m services.cli publish-recipe spatial-overlay-analysis
```

## Agent identity (W6a — real Keycloak credentials)

Agents get governed, revocable identities via the testbed Keycloak (EU LDT
Identity Management): a secret-free registry
([`data/agent-clients.json`](data/agent-clients.json)), an idempotent
provisioning script, per-agent `client_credentials` tokens in the virtual
wallet (:8088) and an RFC 7662-verifying edge backend (:8087) whose
effective capabilities are the registry ∩ granted Keycloak roles. Details:
[`16-eid-wallet-identity.md`](16-eid-wallet-identity.md) §W6a.

```bash
# 1. Provision (Keycloak Admin API; prints the env var for each secret)
PYTHONPATH=. python scripts/provision_agent_clients.py --dry-run
PYTHONPATH=. python scripts/provision_agent_clients.py --rotate-secret

# 2. Run the edges with real verification
export NLDT_WALLET_VERIFIER=keycloak NLDT_AGENT_WALLET_BACKEND=keycloak
export NLDT_AGENT_BELEIDSKOMPAS_SVC_CLIENT_SECRET=…   # from step 1

# 3. Mint an nLDT token for a capability (trust gates enforce it downstream)
curl -X POST localhost:8088/token -H 'content-type: application/json' \
  -d '{"capability": "breda-scan-query"}'
```

## Licence

Same as parent repo `ldttoolbox`.
