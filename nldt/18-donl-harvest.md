# 18 — DONL harvest (data.overheid.nl)

> Status: **implemented** (2026-09-15).  
> Aligns with [13-data-lake-and-space.md](13-data-lake-and-space.md) Phase 6 + EU Data Spaces publication.

[data.overheid.nl](https://data.overheid.nl) exposes ~20k datasets via **CKAN Action API**.
This module harvests curated packages into the nLDT medallion lake as **DCAT-AP-NL 3** catalog
records, with optional file downloads and Data Space offers.

---

## Architecture

```text
DONL CKAN API
    │ package_search / package_show
    ▼
services/donl_harvest/
    ├── ckan.py           CKAN client
    ├── dcat_map.py       CKAN → DCAT-AP-NL
    ├── distributions.py  download vs DataService split
    └── harvest.py        bronze + catalog/dcat + silver manifests
    ▼
nldt-poc-lake (FS or MinIO)
    ├── bronze/donl/…
    ├── catalog/dcat/…
    └── silver/donl/services/…
    ▼
lake-publish-dataset → EDC-manifest / Data Space offer
```

---

## API

| Endpoint | Use |
|----------|-----|
| `https://data.overheid.nl/data/api/3/action/package_search` | Discovery (paginate) |
| `https://data.overheid.nl/data/api/3/action/package_show` | Full dataset + resources |
| `https://data.overheid.nl/dataset/{name}/rdf` | Optional DCAT-RDF per dataset |

---

## Configuration

| File | Role |
|------|------|
| [`data/donl-watchlist.json`](data/donl-watchlist.json) | Curated pilot datasets |
| [`data/donl-harvest-registry.json`](data/donl-harvest-registry.json) | Source-monitor snapshot (auto-refreshed on harvest) |
| [`data/lake-deny.json`](data/lake-deny.json) | `donl` accessClass defaults (`open`) |

Per-dataset flags in watchlist:

- `metadataOnly: true` — skip file downloads (WFS/WMS/Atom services)
- `metadataOnly: false` — download CSV/ZIP/GPKG distributions (max 50 MiB/file default)

---

## CLI

```bash
cd nldt
PYTHONPATH=. python scripts/donl_harvest.py
PYTHONPATH=. python scripts/donl_harvest.py --metadata-only
PYTHONPATH=. python scripts/donl_harvest.py --package demo-donl-dataset --out /tmp/harvest.json
```

---

## Processes & recipes

| Id | Role |
|----|------|
| `donl-harvest-run` | OGC process: harvest watchlist or single package |
| `donl-harvest-run` (recipe) | Cookbook wrapper |
| `donl-harvest-publish` (recipe) | Harvest + `lake-publish-dataset` (pilot E2E) |

Optional process inputs:

- `publishDatasetId` — after harvest, publish DCAT `lakeUri` as Data Space offer
- `accessClass` — default `open` for DONL open data

---

## Source monitor

Watchlist entry `donl-pilot` in [`data/source-monitor-watchlist.json`](data/source-monitor-watchlist.json)
probes:

- CKAN `metadata_modified` drift
- `resourceCount` changes
- Resource URL reachability (HEAD/Range GET, first 5 URLs)

Replay fixtures: [`data/source-monitor/fixtures/donl/`](data/source-monitor/fixtures/donl/).

```bash
PYTHONPATH=. python -m services.source_monitor.cli run --mode replay
```

---

## Cluster (LDT Toolbox)

1. Deploy Data Platform MinIO bucket `nldt-poc-lake` ([`../ldtsolutions/NLDT_MCP_DEPLOY.md`](../ldtsolutions/NLDT_MCP_DEPLOY.md))
2. `export NLDT_LAKE_BACKEND=s3 NLDT_LAKE_ENDPOINT=…`
3. Run harvest from orchestrator or CronJob
4. Publish offers via `NLDT_DATASPACE_CONNECTOR=edc-manifest` or live EDC/DSR

---

## Non-goals

- Full mirror of all ~20k DONL datasets
- Blind WFS/WMS feature dumps (use on-demand extract to silver)
- FSC/Digikoppeling G2G (separate federated path)
