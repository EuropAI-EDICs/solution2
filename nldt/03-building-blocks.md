# 03 — Building blocks

Overview of function blocks per nLDT working group, with standards and hybrid implementation.

## 1. Data & sensors

| Building block | Standard | Implementation | Agent MCP |
|----------------|----------|----------------|-----------|
| Feature data | OGC API Features | Data Platform, external WFS/AGOL via adapter | `data-mcp` (future) |
| Real-time / IoT | NGSI-LD, SensorThings | Data Platform broker | `data-mcp` |
| Metadata | DCAT-AP, ISO 19115 | Records catalog | `nldt-catalog-mcp` |

**Agent role:** discover datasets via catalog; pull process parameters from Records metadata.

## 2. Compute models & processes

| Building block | Standard | Implementation | Agent MCP |
|----------------|----------|----------------|-----------|
| Process discovery | OGC API Records (`type=process`) | Catalog adapter | `search_records`, `list_processes` |
| Process execution | OGC API Processes | Process adapter → local / UCS / Kubeflow | `execute_process`, `get_job_status` |
| Process chaining | Recipe steps | Cookbook + orchestrator | Recipe Planner |
| Data lake I/O | medallion + `lake://` | Lake client; silver in / gold out — see [13](13-data-lake-and-space.md) | (via process inputs / post-run) |

Conformance: OGC API Processes Part 1 (Core); job polling async execution.

Processes run **outside** the lake (Cook); Iceberg/dbt are analytics over
inventory, not a process executor.

Reference processes in this repo:

- `fetch-features` — fetch GeoJSON (`file://` / `lake://` / URL)
- `spatial-intersection` — intersect two feature collections
- `compute-area-statistics` — area statistics (m²)
- PoC wrappers + `lake-publish-dataset` — see [04](04-recipes-and-processes.md) / [13](13-data-lake-and-space.md)

## 3. Visualisation

| Building block | Standard | Implementation |
|----------------|----------|----------------|
| 2D maps | OGC API Tiles / GeoJSON layers | Play & Visualise |
| 3D scene | 3D Tiles, Web 3D Context | Play & Visualise, `3d-viewer/` (parent) |

**Agent role:** supplies `resultUri` and optionally `visualizationHint` from the recipe; no generative map.

## 4. Foundation — catalog (AppStore)

| Building block | Standard | Service |
|----------------|----------|---------|
| Asset discovery | OGC API Records | `services/catalog_adapter` |
| Recipe registry | Records + `rel=recipe` | Catalog entries → Cookbook URI |
| Marketplace sync | DCAT / TM Forum (EU) | Marketplace Agent wrapper |

## 5. Foundation — orchestration

| Building block | Function | Service |
|----------------|----------|---------|
| Recipe definitions | Cookbook API | `services/cookbook` |
| Step execution | Cook (Processes) | `services/process_adapter` |
| Workflow graph | LangGraph | `agents/orchestrator` |
| Batch pipelines | Airflow | UCS `workflow/` (hybrid) |

## 6. Foundation — identity & trust

| Building block | Standard | Implementation |
|----------------|----------|----------------|
| Authentication | OAuth2 / OIDC | Keycloak (EU LDT IM) |
| Service accounts | Client credentials | Agent MCP backends |
| Provenance | W3C PROV-O | Execution records per job |
| Validation | JSON Schema + V0–V4 | Critic agent, `validation-report.schema.json` |
| HITL | Checkpoint interrupts | LangGraph `interrupt_before` |

## Building-block composition: Digital Twin instance

A **twin instance** is not a monolith but a configuration:

```json
{
  "twinId": "ref-generic-001",
  "catalogEndpoint": "http://localhost:8083",
  "processEndpoint": "http://localhost:8082",
  "cookbookEndpoint": "http://localhost:8081",
  "apps": [
    {
      "recordId": "application-beleidskompas",
      "appId": "beleidskompas",
      "allowedRecipes": ["beleidskompas-omgevingsanalyse", "breda-scan-qa"]
    }
  ],
  "recipes": [
    "spatial-overlay-analysis",
    "beleidskompas-omgevingsanalyse",
    "breda-scan-qa"
  ],
  "trustPolicy": { "defaultRiskLevel": "low", "hitlOnFail": true }
}
```

`apps` lists catalogued applications (catalog record type `application`) the
twin's front door may launch, each scoped to the recipes it may consume —
first example: beleidskompas
([14-beleidskompas-integration.md](14-beleidskompas-integration.md) §8 BK-2).

## Guiding principles (Geonovum)

Ten principles from the nLDT framework — elaborated in [07-trust-and-governance.md](07-trust-and-governance.md):

- Transparency and explainability
- Human oversight (human-in-the-loop)
- Data minimisation and sovereignty
- Interoperability by design
- Reuse over custom build
