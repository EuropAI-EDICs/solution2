# 09 — Federation, observability and hardening (Phase 4)

## Web 3D Context (testbed topic 5)

Portable JSON scene document for visualisation clients (Geonovum DTaaS export-import-scenes).

| Component | Location |
|-----------|----------|
| Schema | [`schemas/web3d-context.schema.json`](schemas/web3d-context.schema.json) |
| Export/import logic | [`services/context3d/export_import.py`](services/context3d/export_import.py) |
| HTTP service | [`services/context3d/app.py`](services/context3d/app.py) — port **8084** |

### Export

From recipe execution (intersection GeoJSON + stats):

```bash
PYTHONPATH=. python -m services.cli export-context execution.json --run-id demo01
# Or via HTTP:
curl -X POST http://localhost:8084/export \
  -H 'Content-Type: application/json' \
  -d '{"execution": {...}, "runId": "demo01"}'
```

Document contains: `viewpoint`, `bbox`, `layers[]`, `services[]`, `provenance`, inline GeoJSON in `metadata`.

### Import

```bash
curl -X POST http://localhost:8084/import -H 'Content-Type: application/json' -d @context.json
```

Returns normalised layers + viewpoint for client replay.

## A2A cross-organisation agents

Minimal [A2A](https://a2a-protocol.org/)-compatible agent endpoint for federation (Phase 4 / plan Phase 5).

| Endpoint | Description |
|----------|-------------|
| `GET /agent-card` | Agent Card (skills, auth scheme) |
| `POST /tasks` | Task intake (`execute-recipe`, `export-3d-context`) |

Service: [`services/a2a/app.py`](services/a2a/app.py) — port **8085**

```bash
curl http://localhost:8085/agent-card
curl -X POST http://localhost:8085/tasks -H 'Content-Type: application/json' \
  -d '{"skillId":"execute-recipe","message":"overlay","recipeId":"spatial-overlay-analysis","inputs":{...},"autoApproveHitl":true}'
```

Production: Bearer tokens via EU LDT Identity Management.

## EU Marketplace publication

Publish recipes as assets to Marketplace Agent (upload + publish pattern from UCS).

| Component | Location |
|-----------|----------|
| Publisher | [`services/marketplace_publish.py`](services/marketplace_publish.py) |
| Catalog endpoint | `POST /publish/recipe` on catalog adapter |

```bash
# Mock mode (default without MARKETPLACE_AGENT_URL)
PYTHONPATH=. python -m services.cli publish-recipe spatial-overlay-analysis

# Live
export MARKETPLACE_AGENT_URL=https://marketplace-agent.example
export MARKETPLACE_TOKEN=...
export MARKETPLACE_MOCK=false
PYTHONPATH=. python -m services.cli publish-recipe spatial-overlay-analysis \
  --category urn:ngsi-ld:category:processes
```

## OpenTelemetry

Optional tracing via [`services/common/telemetry.py`](services/common/telemetry.py).

```bash
export NLDT_OTEL_ENABLED=1
PYTHONPATH=. python -m services.process_adapter.app
```

Spans: `process.execute` (process adapter), `recipe.execute` (orchestrator). Without SDK or env flag: no-op.

Future: OTLP exporter to Langfuse/Jaeger; GenAI semconv on orchestrator nodes.

## Start all services

```bash
./scripts/start-services.sh   # 8081–8083
# Extra terminals:
PYTHONPATH=. python -m services.context3d.app   # 8084
PYTHONPATH=. python -m services.a2a.app         # 8085
```

## Success criteria Phase 4

| Item | Status |
|------|--------|
| Web 3D Context import/export | ✅ |
| A2A Agent Card + task endpoint | ✅ |
| Marketplace publish (mock + live-ready) | ✅ |
| OpenTelemetry spans (opt-in) | ✅ |
