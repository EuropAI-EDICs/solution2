# PoC-3 — Rijnland water levels & peil conflict (H3)

**MVP question:** where does operational water-level management deviate from the
formal (*vigerend*) peil decision in the Hoogheemraadschap van Rijnland area?

**Stack:** thin wrapper reusing PoC-1 H3 tooling:

- `poc.pipeline.geodata` — fetch + dual-CRS cache
- `poc.pipeline.h3step` / `h3report` — nLDT H3 processes + Leaflet heatmap

Design: [`docs/superpowers/specs/2026-09-10-poc3-rijnland-h3-design.md`](../docs/superpowers/specs/2026-09-10-poc3-rijnland-h3-design.md).

Agent skill: `skill://nldt/poc/rijnland-peilen/SKILL.md`.

---

## Available water-level datasets

| Id | Kind | Access | Role | Path / service |
|----|------|--------|------|----------------|
| `rijnland-peilgebied-vigerend` | Formal peil area polygons | Open ArcGIS REST | Reference (legal target) | `data/sources.json` → MapServer Peilgebied_vigerend_besluit |
| `rijnland-peilafwijking-praktijk` | Practice deviation polygons | Open ArcGIS REST | Conflict vs formal | MapServer Peilafwijking_praktijk |
| `rijnland-peilen-agol-polders` | Live station levels (polders) | Open AGOL FeatureServer | Current mNAP + chart URL | ArcGIS Online layer (see `scripts/fetch_peilen.py`) |
| `rijnland-peilen-agol-boezem` | Live station levels (boezem) | Open AGOL FeatureServer | Current mNAP + chart URL | ArcGIS Online layer |
| `rijnland-peilen-hydronet-charts` | ~12-day station series | Public HydroNET chart HTML | Short history per station | Via each station `chartUrl` |
| `rijnland-peilen-archive` | Growing daily archive | Local fixture | Time series (mNAP) | `data/peilen/peilen.json` |
| `rijnland-peilen` (lake) | Silver timeseries observations | Lake / ES (`poc=rijnland`) | Discovery + CDC what-if | `timeseries-open-ingest` → `normalize_rijnland_peilen` |
| CDC peilen silver | Latest + what-if scenarios | Lake parquet / Iceberg | Governed what-if | `nldt` CDC capture/apply + `rijnland-peil-whatif` |

**Not water levels** (related context only): WKP surface-water **quality** (`data/wkp/…`), KRW monitoring points, primary watercourses / flow fixtures.

**Limits:** multi-year open peil history is not published. Full 2020–2026 history needs a HydroNET account or RWS Waterinfo key. Re-run `fetch_peilen.py` (e.g. weekly) to extend the local archive forward.

Filter gallery (browse): [Rijnland Filter Gallery](https://rijnland.maps.arcgis.com/apps/instant/filtergallery/index.html?appid=cc74a510ca1644d78dfb914e09cb1b5a).

---

## What-if water-level map (nLDT CDC — implemented)

Simulate peil shifts (e.g. boezem +5 cm) via the nLDT lake pipeline — not by writing to ArcGIS. Output includes a multi-scenario Leaflet map:

```bash
cd ../nldt
PYTHONPATH=. .venv/bin/python scripts/rijnland_whatif_peilen.py \
  --delta-m 0.05 --layer boezem --no-conflict --no-lake
open ../poc-rijnland/runs/<ts>-peilen-whatif/whatif-map.html
```

Panel: demo pack (boezem ±5 cm, polders +10 cm) + active CLI scenario; only the active scenario lands in CDC/silver. Docs: [`nldt/15-cdc-data-lake-pipeline.md`](../nldt/15-cdc-data-lake-pipeline.md#rijnland-what-if-implemented).

MCP: `run_peil_whatif` → process `rijnland-peil-whatif`.

---

## Run — peil conflict

```bash
# demo slice (Leiden / Haarlemmermeer bbox, default)
nldt/.venv/bin/python poc-rijnland/run.py

# full Rijnland (heavier)
nldt/.venv/bin/python poc-rijnland/run.py --full --out /tmp/rijnland-peil

# polygon headline only, no H3
nldt/.venv/bin/python poc-rijnland/run.py --no-h3
```

Output under `poc-rijnland/runs/<ts>-rijnland-peil/`:

- `peil-conflict-report.json` / `.md`
- `h3-peil-conflict.json` + `h3-peil-conflict.html`
- `h3-krw-monitoring.json` + `h3-krw-blindspots.html` (phase 2; `--no-krw` to skip)
- `h3-waterkwaliteit.json` + `h3-waterkwaliteit.html` (phase 2b quality; `--no-wq` / `--parameter`)

Offline H3 replay: `POC_H3_OFFLINE=1` (uses `poc/data/cache/h3/`).

MCP: `run_peil_conflict` / `run_peil_conflict_live`.

---

## Measured water levels (archive + time maps)

```bash
# snapshot AGOL live + HydroNET ~12-day charts → merge into archive
nldt/.venv/bin/python poc-rijnland/scripts/fetch_peilen.py
nldt/.venv/bin/python poc-rijnland/scripts/fetch_peilen.py --dry-run

# time-series page + animated hex map (daily deviation vs station median, cm)
nldt/.venv/bin/python poc-rijnland/run_peilen.py
```

Ingest to lake silver (restricted observations):

```bash
cd nldt
PYTHONPATH=. NLDT_OFFLINE=1 python -m agents.orchestrator.run \
  --recipe timeseries-open-ingest --auto-approve-hitl
```

Discover: catalog `search_lake_elasticsearch` with `poc=rijnland`, `kind=timeseries_series`, `variable` related to peil / mNAP.

---

## Water quality time series (context — not levels)

```bash
nldt/.venv/bin/python poc-rijnland/scripts/fetch_wkp.py --monthly --from-year 2020 --to-year 2026
nldt/.venv/bin/python poc-rijnland/run_timeseries.py
```

See phase notes below for KRW monitoring coverage vs peil conflict.

---

## Tests

```bash
cd poc-rijnland && ../nldt/.venv/bin/python -m unittest discover -s tests -v
```

Optional live fixtures (small Leiden bbox):

```bash
../nldt/.venv/bin/python tests/make_fixtures.py
```

---

## Phase notes (implemented)

### Animated hex maps

`rijnland/hexmap_time.py` — per-timestep cell colour (slider + Play), offline Leaflet. Quality: `run_timeseries.py` → `hexmap-tijd.html`. Levels: `run_peilen.py` → `hexmap-peilen-tijd.html` (daily deviation vs station median, cm). AGOL peil coordinates are WGS84 (degree-tolerant renderer).

### Water levels — polders & boezem

Measured history is not openly bulk-published. AGOL gives current values; HydroNET charts give a fixed ~12-day window. `fetch_peilen.py` snapshots all stations (polders + boezem) into `data/peilen/peilen.json`; re-runs grow the archive.

### Water quality 2020–2026 & KRW coverage

WKP portal download for Oppervlaktewaterkwaliteit; KRW status layers are empty in the MapServer — routine monitoring points are used for “conflict without monitoring” blind spots (`h3-krw-blindspots.html`).
