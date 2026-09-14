# 06 — Hybrid implementation

## Principle

Agents and external clients see **only** nLDT-conformant APIs. Internally the adapter routes to EU LDT Toolbox or standalone backends.

```
Client / Agent (MCP)
        │
        ▼
┌───────────────────┐
│  nLDT Interface   │  Records / Processes / Cookbook
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌───────────────┐
│ Local  │  │ Toolbox       │
│ pygeo  │  │ UCS / DPL /   │
│ stub   │  │ Marketplace   │
└────────┘  └───────────────┘
```

## Process adapter routing

| `backend` | Target | Env vars |
|-----------|--------|----------|
| `local` | In-process Python handlers | — |
| `ucs` | UCS experiment execution | `UCS_BASE_URL`, `UCS_TOKEN` |
| `kubeflow` | KServe inference | `KUBEFLOW_BASE_URL`, `KUBEFLOW_TOKEN` |

Routing in `services/process_adapter/router.py`:

```python
if backend == "ucs":
    return ucs_adapter.execute(process_id, inputs)
return local_handlers.execute(process_id, inputs)
```

The UCS adapter is **stub-ready**: when `UCS_BASE_URL` is not set, it falls back to local with a log warning.

## Catalog adapter routing

| Source | When | Env |
|--------|------|-----|
| Built-in seed records | Always (recipes + local processes) | — |
| Marketplace Agent | `MARKETPLACE_AGENT_URL` set | OAuth via Keycloak optional |

Marketplace wrapper maps TM Forum / agent categories to OGC Records `features[]`.

## Cookbook

Static JSON in `recipes/` + HTTP GET. No toolbox dependency.

## Identity

[`services/adapters/keycloak_auth.py`](services/adapters/keycloak_auth.py) — OAuth2 client_credentials with token cache.

Integration with [`ldtsolutions/repos/tool_5_identity_management`](../ldtsolutions/repos/tool_5_identity_management/):

- Realm `LDT` (or per municipality)
- Service account `nldt-agent` with scopes for catalog, processes, data platform, P&V

## Data Platform

[`services/adapters/data_platform.py`](services/adapters/data_platform.py) + MCP [`services/mcp_servers/data_server.py`](services/mcp_servers/data_server.py).

- Direct broker: `NLDT_NGSI_LD_URL`
- UCS proxy: `NLDT_DATA_PLATFORM_URL`
- Process source: `ngsi-ld://EntityType`

## Play & Visualise

[`services/adapters/play_visualise.py`](services/adapters/play_visualise.py) — dataSource + dataLayer after execution via [`services/hybrid_bridge.py`](services/hybrid_bridge.py).

## Full guide

See [10-toolbox-integration.md](10-toolbox-integration.md).

## Deployment topology (ldtsolutions)

| Service | Dev port | K8s hostname (example) |
|---------|----------|--------------------------|
| Cookbook | 8081 | cookbook.nldt.local |
| Process adapter | 8082 | processes.nldt.local |
| Catalog adapter | 8083 | catalog.nldt.local |
| Context3D | 8084 | context3d.nldt.local |
| A2A agent | 8085 | a2a.nldt.local |

See [`../ldtsolutions/MINIKUBE_ENV_PLAN.md`](../ldtsolutions/MINIKUBE_ENV_PLAN.md) for toolbox K8s context.

## Migration path

1. Local-only (Phase 1) — no toolbox required
2. Marketplace sync (Phase 2) — catalog supplements from EU Marketplace
3. UCS process steps (Phase 2) — heavy models via experiment DAG
4. Full IM auth (Phase 2+) — Keycloak tokens on adapters ✅
