# CitiVERSE live path — reference recipe `spatial-overlay-analysis`

Adapters exist ([10-toolbox-integration.md](../10-toolbox-integration.md)).
Laptop defaults are **mock**. This is the runbook to flip them to the EU LDT
Toolbox on `*.ldttoolbox.app` without rebuilding UCS, Marketplace, P&V or IM.

Engines stay local. The Toolbox is consumed.

## 1. Readiness

```bash
cd nldt
PYTHONPATH=. python -m scripts.edic_live_readiness
# 0 = all required Toolbox connections live
# 2 = mock or hybrid (expected without cluster secrets)
```

Required for status `live`: `UCS_BASE_URL`, Marketplace non-mock,
Play & Visualise non-mock, Keycloak URL that is not localhost.
**Optional:** Data Platform (only if sources are `ngsi-ld://`);
`NLDT_NLAIF_ROUTE` / `NLDT_LLM_BASE_URL` — only S7/S8 LLM seams, never zone
engines.

## 2. Environment (ldtsolutions / int)

```bash
export UCS_BASE_URL=https://ucs-int.ldttoolbox.app
export NLDT_DATA_PLATFORM_URL=https://dpl-int.ldttoolbox.app
export NLDT_NGSI_LD_URL=https://dpl-int.ldttoolbox.app/broker
export NLDT_PV_BASE_URL=https://pv-int.ldttoolbox.app
export NLDT_PV_MOCK=false
export NLDT_DATA_PLATFORM_MOCK=false
export KEYCLOAK_URL=https://im-int.ldttoolbox.app
export KEYCLOAK_REALM=LDT
export KEYCLOAK_CLIENT_ID=nldt-agent
export KEYCLOAK_CLIENT_SECRET=...   # from Toolbox IM, never committed
export MARKETPLACE_AGENT_URL=https://marketplace-int.ldttoolbox.app
export MARKETPLACE_MOCK=false
export MARKETPLACE_TOKEN=...        # IM bearer
export NLDT_A2A_URL=https://<nldt-host>/a2a
```

`GET /agent-card` then reports `authentication.productionIdentity=true` and
`provider.edic=ldt-citiverse`. Localhost is not a production identity.

## 3. Execute the reference recipe

Local engines (always valid, including framing demo without cluster):

```bash
PYTHONPATH=. python -m services.cli run-recipe spatial-overlay-analysis \
  --aoi-file examples/aoi.geojson \
  --input layerAUri=file://$PWD/examples/layer-a.geojson \
  --input layerBUri=file://$PWD/examples/layer-b.geojson
```

Orchestrator with hybrid hooks (P&V + Web3D) when env is live:

```bash
PYTHONPATH=. python -m agents.orchestrator.run \
  --request 'Intersect two layers in the AOI' \
  --recipe spatial-overlay-analysis \
  --input layerAUri="$LAYER_A" \
  --input layerBUri="$LAYER_B" \
  --aoi-file examples/aoi.geojson
```

Publish to Marketplace **with** ValidationReport + PROV (EDIC acceptance):

```bash
PYTHONPATH=. python -m services.cli publish-recipe spatial-overlay-analysis \
  --validation-report path/to/validation-report.json \
  --provenance path/to/provenance.json
```

The payload always includes `edic.destination` from
[`../recipes/edic-asset-map.json`](../recipes/edic-asset-map.json).

## 4. City-facing module

Do not invent a second skill family. The capacity-building annex is
[skills/poc/nldt-poc-lifecycle/references/edic-city-onboarding.md](../skills/poc/nldt-poc-lifecycle/references/edic-city-onboarding.md):
Discover → Lake → Scenarios → Demo with Critic/HITL mandatory.

## 5. What this path does not do

- Does not stand up a new marketplace or orchestrator.
- Does not send zone geometry through an LLM.
- Does not require NLAIF for overlay statistics.
