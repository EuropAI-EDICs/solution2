# PoC-6 — Rijnland groundwater-table digital twin (GWT, H3)

**MVP question:** where will the groundwater table in the Rijnland beheergebied
cross drought/ingress thresholds in the coming days — and which gemaal action
(aan / uit / vasthouden) is advised?

Research input: [`docs/research/Morales_MA_ITC.pdf`](../docs/research/Morales_MA_ITC.pdf)
— L. R. A. Morales Ortega, *A Digital Twin for Ground Water Table Monitoring*
(MSc thesis, ITC Twente, 2023; Enschede case: 277 sensors, Unity mesh,
IFTTT pump actuation). The framework — real-time GWT sensor data + rainfall →
prediction → visual twin → pump ON/OFF triggers — is translated to Rijnland on
the existing nLDT stack (no game engine, no IoT hardware). Design + translation
table: [`docs/superpowers/specs/2026-10-13-rijnland-gwt-digital-twin-design.md`](../docs/superpowers/specs/2026-10-13-rijnland-gwt-digital-twin-design.md).

**Stack:** thin wrapper reusing PoC-1/PoC-3 tooling:

- `poc.pipeline.geodata` — ArcGIS fetch + dual-CRS cache (gemaal layer)
- `poc.pipeline.h3step` — nLDT `h3-cells-to-geojson` process (cache-first)
- `poc-rijnland/rijnland.hexmap_time` — animated single-file Leaflet page

---

## Run

```bash
# canonical full-network run (252 loggers, 12 polders)
nldt/.venv/bin/python poc-rijnland-gwt/run.py --full --rain-scenario-mm 30

# demo slice (Leiden area, PoC-3 default bbox)
nldt/.venv/bin/python poc-rijnland-gwt/run.py

# no animated map, custom what-if cloudburst, other thresholds
nldt/.venv/bin/python poc-rijnland-gwt/run.py --no-h3 \
  --rain-scenario-mm 15 --ingress-depth 0.5 --drought-depth 1.4
```

Output under `poc-rijnland-gwt/runs/<ts>-gwt-twin/`:

- `gwt-twin-report.json` / `.html` — KPIs, per-day forecast + trigger counts,
  scenario diff, backtest honesty numbers, command preview, caveat footer
- `gwt-twin-hexmap.html` — animated H3 twin map (30 d history → 5 d forecast,
  red = shallow / ingress risk; slider + play)
- `commands.json` (+ `commands-scenario.json`) — `WaterpumpON` / `WaterpumpOFF`
  + `RetainWater` events per logger/day with the nearest gemaal and distance —
  the IFTTT-webhook-contract equivalent; actuation itself is out of scope
- `forecast.json`, `rain.json` — per-logger forecasts and open-meteo input

Tests (offline, no network):

```bash
cd poc-rijnland-gwt && ../nldt/.venv/bin/python -m pytest tests -q
```

---

## Data (all verified reachable 2026-10-13)

| Role | Source | Notes |
|------|--------|-------|
| Sensors | Rijnland open ArcGIS `Meetlocatie_waterkwantiteit`, `SOORTOBJECT = 'Meetopstelling: Logger grondwater'` — 252 depth loggers, 12 polders | positions + peil/polder context only; the service returns **NULL geometry** (coords in attributes) → attribute-mode fetch in `gwt/sensors.py`; `LIZARDID` is present for the (auth-gated) Lizard series |
| Pumps | Rijnland open ArcGIS `Gemaal` — 329 in extent | nearest-gemaal advice + action-gap analysis (thesis rec. 3) |
| Rain | open-meteo archive (90 d) + forecast (5 d), keyless, 3×3 grid area mean | thesis-equivalent of the KNMI RH(mm) join |
| Depths | `data/gwt/gwt.json` growing archive | **seeded** (see below) |

**Provenance caveat (carried in every artifact):** no open groundwater *series*
resolves for Rijnland today — BRO (`api.bro-data.nl`) and Rijnland Lizard are
credential-gated, grondwaterstanden.nl is defunct. The archive is therefore
**seeded deterministically** from the open sensor metadata + measured
open-meteo rain (`syntheticSeed: true` + formula in the file; parameters
hashed from the logger code, so every run reproduces the same series). When a
BRO/Lizard fetch lands real series, `gwt/archive.merge_real` overwrites the
seed per logger and the pipeline runs unchanged — the same growing-archive
pattern as PoC-3 fase 2d (peilen).

## Prediction & triggers (thesis-faithful, with the gaps filled)

- Interpretable decision tree per logger (pure-numpy CART — the thesis used
  sklearn's `DecisionTreeRegressor` for interpretability): features depth
  lag-1/lag-3, rain 1/3/10-day sums, day-of-year → depth(t+1); recursive 5-day
  forecast on open-meteo forecast rain.
- The thesis published **no accuracy numbers**; the report shows holdout
  MSE/MAE per logger plus a persistence baseline (canonical run: median MSE
  0.0081 m², median skill +0.71, 6/252 loggers lose to persistence).
- The thesis triggered pumps geometrically (GWT mesh touching terrain) and
  named numeric thresholds future work; here they are explicit parameters:
  `--ingress-depth 0.4` → `WaterpumpON`, `--drought-depth 1.2` → `WaterpumpOFF`
  + vasthouden. Defaults, not board policy.
- What-if: `--rain-scenario-mm N` replaces day +1 forecast rain with a flat
  cloudburst; the report diffs base vs scenario trigger counts.

## Evaluation frame (thesis Table 7 SWOT, carried to this PoC)

- **S:** end-to-end framework on open data in one command; interpretable
  per-logger models with backtest numbers; actionable command contract with
  actuator matching; aggregate alerts only (thesis Annex M governance).
- **W:** seeded depths (see caveat); clustered sensor network (52 of the demo
  loggers share one km-tile — multi-filter wells); thresholds are defaults.
- **O:** swap the seed for BRO/Lizard series → real twin; polder-level
  aggregation; couple `commands.json` to Lizard/SOBIEP actuation planning.
- **T:** regulator/privacy sensitivity of geolocated groundwater warnings;
  credential walls on the authoritative series.

## Limits

- Unity 3-D, IoT actuation and the thesis questionnaire evaluation are out of
  scope; the animated H3 map is the twin's "past → current → future" view.
- The hexmap uses the PoC-3 Leaflet convention (unpkg CDN when viewing).
- Depths in m-onder-maaiveld relative to an assumed surface; no AHN coupling.
