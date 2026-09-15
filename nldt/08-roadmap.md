# 08 — Roadmap

## Phasing

Aligned with [Geonovum nLDT Testbed 2026](https://www.geonovum.nl/index.php/themas/digital-twins) and LDT CitiVERSE EDIC sandbox.

### Phase 0 — Documentation & architecture ✅

| Item | Status |
|------|--------|
| Docs 01–08 | Done |
| JSON Schemas | Done |
| Reference recipe | Done |
| Diagrams | Done |

**Deliverable:** reviewable architecture in `nldt/`.

### Phase 1 — nLDT interfaces ✅ (baseline)

| Item | Status |
|------|--------|
| OGC API Records catalog adapter | Done (`services/catalog_adapter`) |
| OGC API Processes facade | Done (`services/process_adapter`) |
| Cookbook service | Done (`services/cookbook`) |
| Spatial Overlay Analysis E2E | Done (`services/recipe_runner`, `services/cli`) |
| MCP servers | Done (`services/mcp_servers`) |

**Deliverable:** catalog + process + recipe without agent.

### Phase 2 — Hybrid toolbox integration ✅

| Item | Status |
|------|--------|
| UCS process adapter stub | Done (`router.py`, env `UCS_BASE_URL`) |
| Kubeflow adapter stub | Done (`kubeflow_adapter.py`) |
| Marketplace Agent wrapper | Done (`catalog_adapter/marketplace.py`) |
| Data Platform adapter (NGSI-LD) | Done (`services/adapters/data_platform.py`, `data-mcp`) |
| Play & Visualise layer registration | Done (`services/adapters/play_visualise.py`, hybrid hooks) |
| Keycloak service accounts | Done (`services/adapters/keycloak_auth.py`, client_credentials) |

See [06-hybrid-implementation.md](06-hybrid-implementation.md) and [10-toolbox-integration.md](10-toolbox-integration.md).

### Phase 3 — Agentic AI layer ✅ (baseline)

| Item | Status |
|------|--------|
| LangGraph orchestrator | Done (`agents/orchestrator`) |
| Catalog Navigator + Recipe Planner + Critic | Done |
| MCP tool integration (in-process client) | Done |
| Golden-set regression tests | Done (`tests/`) |
| LLM seams (optional `llm_hook`) | Stub done (`agents/orchestrator/llm_hook.py`) |

**Deliverable:** NL request → recipe → execution → validation.

### Phase 4 — Federation & hardening ✅

| Item | Status |
|------|--------|
| Web 3D Context import/export | Done (`services/context3d`, `:8084`) |
| A2A cross-organisation agents | Done (`services/a2a`, `:8085`) |
| EU Marketplace publication | Done (`services/marketplace_publish`, `POST /publish/recipe`) |
| OpenTelemetry observability | Done (`services/common/telemetry.py`, opt-in) |

See [09-federation-and-observability.md](09-federation-and-observability.md).

### Phase 5 — Governed agent layer across all PoCs ✅

> Plan: [12-governed-agent-layer.md](12-governed-agent-layer.md) · **done 2026-09-15**

| Item | Status |
|------|--------|
| Patterns A/B/C + V0–V4 documented | Done (docs 11, 05, 07) |
| Contract bridge (`schemas/poc/`, `validate-artifact`) | **Done** |
| PoC pipelines as OGC Processes | **Done** (`poc_handlers.py`, 9 PoC processes + validate-artifact) |
| Recipes: opportunity-map, scenario, crosstrack, breda, rijnland, eindhoven | **Done** |
| MCP tools (`nldt-poc-mcp` + `list_poc_capabilities`) | **Done** |
| Uniform Critic/HITL/PROV for PoC runs | **Done** (`critic.py`, run artifacts) |
| Eindhoven + Rijnland registration | **Done** (`bp2op-transform`, `rijnland-peil-*`) |

**Deliverable:** `orchestrator.run --recipe breda-scan-qa|utrecht-scenario-sweep|eindhoven-bp2op`
with ValidationReport + PROV; catalog discoverable; per-PoC CLI remains as engine.

### Phase 6 — Data lake & European Data Space 🔲

> Hybrid: lake = storage, Data Space = sharing layer.  
> Plan: [13-data-lake-and-space.md](13-data-lake-and-space.md)

| Item | Status |
|------|--------|
| Medallion zones + accessClass/deny-list | Done (`data/lake-deny.json`, inventory) |
| Lake client fs/S3 + `lake_sync.py` | Done (`services/lake/`, MinIO compose) |
| DuckDB query + inventory Parquet | Done |
| Apache Iceberg warehouse bootstrap | Done (`lake_iceberg_bootstrap.py`) |
| dbt Core (`dbt-duckdb`) marts | Done (`dbt_lake/`) |
| Catalog dataset Records + `lake://` URI | Done |
| Publish process + ODRL stub + mock connector | Done (`lake-publish-dataset`) |
| Uniform Critic/HITL on offers | Open (reuse V4) |
| Production IDS/EDC connector | Open |

**Deliverable:** Utrecht+Breda silver/gold in lake; `lake-publish-dataset` for `open`;
restricted refuses without HITL; dbt marts over inventory.

## Success criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Documentation set covers NLDT + EDIC + agentic layer | ✅ |
| 2 | Catalog + Processes + Recipe E2E without agent | ✅ |
| 3 | Agent via orchestrator: find → execute → validate | ✅ |
| 4 | At least 1 hybrid routing path (UCS stub) | ✅ |
| 5 | Schema-validated outputs + PROV | ✅ |
| 6 | Testbed 2026 phase 2/3 alignment | ✅ (docs + interfaces) |
| 7 | One governed agent layer over ≥2 PoCs via nLDT/MCP | ✅ Phase 5: processes+recipes+MCP+Critic/HITL for Utrecht/Breda/Rijnland/Eindhoven |

## Verification

```bash
cd nldt
PYTHONPATH=. .venv/bin/python -m pytest tests/test_poc_processes.py -q

# PoC process (offline)
PYTHONPATH=. .venv/bin/python -c "
from services.process_adapter.handlers import execute_local
print(execute_local('breda-scan-query', {
  'question': 'waarom scoort Belcrum laag op ruimtelijke waarde?'
})['result']['status'])
"

# Recipe via orchestrator (services running or LocalClient)
PYTHONPATH=. .venv/bin/python -m agents.orchestrator.run \
  --request 'Beantwoord een Breda scan-vraag' \
  --recipe breda-scan-qa \
  --input question='top 3 buurten onbenut dakpotentieel' \
  --auto-approve-hitl
```

## Risks (open)

- OGC API Processes conformance testing against Geonovum plugfest
- UCS `/trigger-process` endpoint is hypothetical — falls back to local
- Production auth not yet implemented

## Next steps

1. **Phase 5** — governed agent layer: [12-governed-agent-layer.md](12-governed-agent-layer.md)
2. **Phase 6** — data lake + Data Space: [13-data-lake-and-space.md](13-data-lake-and-space.md)
3. Deploy adapters on ldtsolutions K8s cluster with production env vars (see [10-toolbox-integration.md](10-toolbox-integration.md))
4. Connect real UCS / Data Platform / P&V endpoints
5. OTLP exporter (Langfuse/Jaeger) instead of console-only spans
6. Geonovum plugfest conformance tests
7. Source monitor (GENAI_SEAMS job 3 / “watching the data”)
