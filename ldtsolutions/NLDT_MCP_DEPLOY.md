# nLDT MCP deploy op ldtsolutions cluster

Manifest: [`../nldt/infrastructure/k8s/nldt-mcp-deploy.yaml`](../nldt/infrastructure/k8s/nldt-mcp-deploy.yaml)

## Vereisten

1. Identity Management (Keycloak realm `LDT`) — service account `nldt-agent`
2. Data Platform: Scorpio (`dp.ldt.local`), Trino (`dq.ldt.local`), MinIO voor lake bucket `nldt-poc-lake`
3. `/etc/hosts` of CoreDNS: zie [`REMOTE_CLUSTER.md`](REMOTE_CLUSTER.md)

## Environment

| Variabele | Waarde |
|-----------|--------|
| `NLDT_LAKE_BACKEND` | `s3` |
| `NLDT_LAKE_ENDPOINT` | DP MinIO (niet AI Notebook MinIO) |
| `NLDT_NGSI_LD_URL` | `https://dp.ldt.local/cb/ngsi-ld/v1` |
| `NLDT_TRINO_URL` | `https://dq.ldt.local` |
| `KEYCLOAK_*` | `nldt-agent` client credentials |

## Deploy

```bash
# Vul secret in
kubectl apply -f ../nldt/infrastructure/k8s/nldt-mcp-deploy.yaml
kubectl -n nldt edit secret nldt-mcp-secrets  # KEYCLOAK_CLIENT_SECRET

# Verify
kubectl -n nldt get pods
curl --resolve catalog.nldt.local:443:<ip> https://catalog.nldt.local/records
```

## MCP servers (stdio)

Lokaal of als sidecar bij orchestrator:

```bash
cd ../nldt
PYTHONPATH=. python -m services.mcp_servers.catalog_server
PYTHONPATH=. python -m services.mcp_servers.process_server
PYTHONPATH=. python -m services.mcp_servers.data_server
PYTHONPATH=. python -m services.mcp_servers.poc_server
```

## Orchestrator smoke test

```bash
PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run \
  --recipe breda-scan-qa \
  --request "Breda scan vraag" \
  --input question="top buurten democratische waarde" \
  --auto-approve-hitl
```

## DONL harvest (data.overheid.nl)

Plan: [`../nldt/18-donl-harvest.md`](../nldt/18-donl-harvest.md)

```bash
cd ../nldt
export NLDT_LAKE_BACKEND=s3
export NLDT_LAKE_ENDPOINT=<DP-MinIO>
export NLDT_LAKE_ACCESS_KEY=...
export NLDT_LAKE_SECRET_KEY=...
export NLDT_LAKE_BUCKET=nldt-poc-lake

PYTHONPATH=. python scripts/donl_harvest.py --metadata-only
PYTHONPATH=. python scripts/build_lake_inventory.py
```

Source monitor watchlist entry `donl-pilot` probes CKAN `metadata_modified` + resource URLs.

## CDC → data lake pipeline (geen RisingWave)

Plan: [`../nldt/15-cdc-data-lake-pipeline.md`](../nldt/15-cdc-data-lake-pipeline.md)

Compose (MinIO + Postgres CDC source):

```bash
cd ../nldt
docker compose -f docker-compose.lake.yml up -d
# wacht tot postgres healthy, daarna:
export NLDT_CDC_SOURCE_URL=postgresql://nldt:nldt@127.0.0.1:5433/nldt_cdc
PYTHONPATH=. python scripts/seed_peilen_oltp.py --limit 50
PYTHONPATH=. python scripts/cdc_capture_peilen.py
PYTHONPATH=. python scripts/cdc_apply_peilen.py
PYTHONPATH=. python scripts/lake_lakehouse_refresh.py --skip-cdc-capture --cdc
```

Offline (zonder Docker):

```bash
PYTHONPATH=. python scripts/lake_lakehouse_refresh.py \
  --cdc-fixture ../poc-rijnland/data/peilen/peilen.json
```

| Env | Meaning |
|-----|---------|
| `NLDT_CDC_SOURCE_URL` | Postgres/Timescale DSN for OLTP CDC |
| `NLDT_CDC_PROFILE` | `local-compose` \| `ldt-timescaledb` |
| `NLDT_STREAM_ALLOW_RESTRICTED` | Allow MCP read of restricted peilen stream |
| `NLDT_PEILEN_LATEST_PARQUET` | Override path for dbt staging |

## Rijnland what-if simulatie

Bridge: scenario delta → CDC bronze/silver → report + peil-conflict replay.

```bash
# CLI
PYTHONPATH=. python scripts/rijnland_whatif_peilen.py \
  --scenario examples/rijnland-whatif-boezem-plus5cm.json

# of snel:
PYTHONPATH=. python scripts/rijnland_whatif_peilen.py --delta-m 0.05 --layer boezem --limit 50

# via process / orchestrator
PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run \
  --recipe rijnland-peil-whatif \
  --request "Simuleer +5cm boezempeilen Rijnland" \
  --input delta_m=0.05 \
  --input layer=boezem \
  --input limit=50 \
  --auto-approve-hitl
```

Artefacten onder `poc-rijnland/runs/<ts>-peilen-whatif/`: `whatif-report.json`, `whatif-diff.html`, `peilen-whatif.json`, CDC batch + silver apply.
