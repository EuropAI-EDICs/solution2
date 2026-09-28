# Recipes used in the PoC lifecycle

Recipes live under `nldt/recipes/*.json`. They are the **Cookbook** contracts: steps →
processes → engines, with `riskLevel` driving HITL.

## Mental model

| Concept | Verb | Example |
|---------|------|---------|
| Skill | teach | `nldt-poc-lifecycle` |
| MCP tool | call once | `run_value_scan` |
| Process | dispose unit | `breda-scan-run` |
| Recipe | orchestrate | `breda-five-value-scan` |

Prefer **recipe** runs when you need ValidationReport + PROV + HITL in one plan.
PoC MCP tools are fine for focused dispose once the skill named the process.

## Phase map

### 1 Discover

| Recipe | risk | Why |
|--------|------|-----|
| `source-monitor-run` | **high** | Probe ArcGIS/DONL continuity; registry patch needs human merge |

Catalog tools (`search_records`, `search_lake_elasticsearch`, `list_poc_capabilities`) are
not recipes — they only discover.

### 2 Lake ingest / convert / publish

| Recipe | risk | Process | Notes |
|--------|------|---------|-------|
| `donl-harvest-run` | medium | `donl-harvest-run` | CKAN → bronze + DCAT |
| `donl-harvest-publish` | **high** | harvest + offer | HITL for Data Space |
| `timeseries-open-ingest` | medium | `timeseries-ingest-run` | Peilen **all stations** by default; WKP; KNMI; CBS |
| `lake-publish-offer` | **high** | `lake-publish-dataset` | Restricted refuses without HITL |

### 3 Scenarios / use cases

| Recipe | risk | Domain |
|--------|------|--------|
| `breda-five-value-scan` / `breda-scan-qa` | medium | Breda |
| `utrecht-scenario-author` / `utrecht-scenario-sweep` | **high** | Utrecht |
| `utrecht-opportunity-map` | **high** | Utrecht Plane A |
| `multi-track-crosstrack` | **high** | Utrecht Plane C |
| `rijnland-peil-conflict` | medium | Rijnland conflict |
| `rijnland-peil-conflict-live` | **high** | Rijnland CDC snapshot |
| `rijnland-peil-whatif` | **high** | Rijnland CDC what-if |
| `eindhoven-bp2op` | **high** | Eindhoven transform |

### 4 Demo site

No recipe — static HTML under `nldt/simulation/` (see [phase-4-demo.md](phase-4-demo.md)).

## CLI

```bash
PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run \
  --recipe <recipe-id> --auto-approve-hitl
```

Pass recipe inputs as `--input key=value` where supported by the orchestrator CLI.
