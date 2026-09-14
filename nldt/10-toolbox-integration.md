# 10 — EU LDT Toolbox integration (Phase 2)

Hybrid coupling between nLDT interfaces and the EU LDT Toolbox.

## Overview

```
nLDT services                    EU LDT Toolbox
─────────────────────────────────────────────────
process_adapter ──UCS_BASE_URL──▶ UCS experiments
catalog_adapter ──MARKETPLACE───▶ Marketplace Agent
data_platform   ──NGSI/DPL─────▶ Data Platform broker
play_visualise  ──NLDT_PV_URL──▶ Play & Visualise API
keycloak_auth   ──KEYCLOAK_*────▶ Identity Management
hybrid_bridge   ──post hooks───▶ P&V + Web3D export
```

## Keycloak service accounts

[`services/adapters/keycloak_auth.py`](../services/adapters/keycloak_auth.py) — OAuth2 **client_credentials**.

| Env var | Example |
|---------|---------|
| `KEYCLOAK_URL` | `https://im.ldt.local` |
| `KEYCLOAK_REALM` | `LDT` |
| `KEYCLOAK_CLIENT_ID` | `nldt-agent` |
| `KEYCLOAK_CLIENT_SECRET` | *(service account secret)* |

The token is cached and used by the Data Platform and P&V adapters.

```bash
export KEYCLOAK_URL=https://im.ldt.local
export KEYCLOAK_CLIENT_ID=nldt-agent
export KEYCLOAK_CLIENT_SECRET=...
python -c "from services.adapters.keycloak_auth import get_service_token; print(get_service_token()[:20])"
```

## Data Platform (NGSI-LD)

[`services/adapters/data_platform.py`](../services/adapters/data_platform.py)

Two modes:

1. **Direct broker** — `NLDT_NGSI_LD_URL` + header `NGSILD-Tenant`
2. **Via UCS proxy** — `NLDT_DATA_PLATFORM_URL` → `/api/v1/data-platform/entities`

Mock (default): `NLDT_DATA_PLATFORM_MOCK=true`

### MCP: data-mcp

```bash
python -m services.mcp_servers.data_server
```

Tools: `list_entities`, `entities_to_geojson`

### Process integration

`fetch-features` accepts `ngsi-ld://EntityType` as source:

```bash
PYTHONPATH=. python -m services.cli run-process fetch-features \
  --input source=ngsi-ld://AirQualityObserved
```

## Play & Visualise layer registration

[`services/adapters/play_visualise.py`](../services/adapters/play_visualise.py)

After recipe execution, `hybrid_bridge` automatically registers:

1. GeoJSON → `data/exports/` + public URL via context3d `:8084/exports/{id}.geojson`
2. P&V **dataSource** (EXTERNAL url)
3. P&V **dataLayer** (type SCENARIO)

| Env var | Default |
|---------|---------|
| `NLDT_PV_BASE_URL` | — (mock if empty) |
| `NLDT_PV_MOCK` | `true` |
| `NLDT_EXPORT_PUBLIC_BASE` | `http://localhost:8084/exports` |

Orchestrator flags: `--no-register-pv`, `--no-export-3d`

## Hybrid bridge

[`services/hybrid_bridge.py`](../services/hybrid_bridge.py) — invoked after validation in the orchestrator (`register_hybrid` node).

```python
from services.hybrid_bridge import post_execution_hooks
hooks = post_execution_hooks(execution, run_id="demo")
# hooks["web3dContext"], hooks["visualization"]
```

## Live configuration (ldtsolutions cluster)

Example `.env` fragment:

```bash
UCS_BASE_URL=https://ucs-int.ldttoolbox.app
NLDT_DATA_PLATFORM_URL=https://dpl-int.ldttoolbox.app
NLDT_NGSI_LD_URL=https://dpl-int.ldttoolbox.app/broker
NLDT_PV_BASE_URL=https://pv-int.ldttoolbox.app
NLDT_PV_MOCK=false
NLDT_DATA_PLATFORM_MOCK=false
KEYCLOAK_URL=https://im-int.ldttoolbox.app
KEYCLOAK_CLIENT_ID=nldt-agent
KEYCLOAK_CLIENT_SECRET=...
MARKETPLACE_AGENT_URL=https://marketplace-int.ldttoolbox.app
MARKETPLACE_MOCK=false
```

## Verification

```bash
PYTHONPATH=. pytest tests/test_phase2_adapters.py -q
```
