# PoC-6 Rijnland GWT digital twin — Design

**Date:** 2026-10-13
**Status:** Implemented (research → PoC)
**Research input:** [`docs/research/Morales_MA_ITC.pdf`](../../research/Morales_MA_ITC.pdf) — L. R. A. Morales Ortega, *A Digital Twin for Ground Water Table Monitoring*, MSc thesis, ITC University of Twente, 2023 (case: Enschede, 277 Twents Waternet sensors, Unity game engine, IFTTT pump actuation).

## 1. Goal

Apply the thesis framework — **real-time GWT sensor data + rainfall → prediction → visual twin → pump ON/OFF triggers** — to the **Hoogheemraadschap van Rijnland** beheergebied on the existing nLDT PoC stack (no game engine, no IoT hardware; thin package over PoC-1 `pipeline` + PoC-3 `hexmap_time`).

**MVP question:** *Where will the groundwater table in the Rijnland beheergebied cross drought/ingress thresholds in the coming days — and which gemaal action (aan / uit / vasthouden) is advised — from sensor positions + rainfall?*

**Thesis → Rijnland translation**

| Thesis (Enschede 2023) | PoC-6 (Rijnland 2026) |
|---|---|
| 277 GWT sensors, per-sensor CSV poll (20 min) | 270 `Logger grondwater` meetpunten (Rijnland open ArcGIS) + growing local archive |
| KNMI rainfall RH (mm), joined per sensor | open-meteo daily precipitation (archive 90 d + 5 d forecast, keyless) |
| Unity Delaunay mesh (depth→Y), spheres + red beacons | H3 res-8 animated hex map (history → forecast), triggered cells as red beacon overlay |
| `DecisionTreeRegressor` per sensor (Date, Hour, RH → Depth), worst-case max tomorrow, **no accuracy published** | numpy CART regression tree per sensor (lags + rain sums + season → depth t+1), recursive 5-day forecast, **holdout MSE/MAE in the report** |
| Terrain-collision → `WaterpumpON/OFF` via IFTTT → smart plug | explicit depth thresholds → `WaterpumpON/OFF/RetainWater` events + nearest gemaal in `commands.json` (the IFTTT-contract equivalent; actuation itself out of scope) |
| Rec. 3: strategic positioning of sensors & pumps | action-gap analysis: triggered cells whose nearest gemaal is > 2.5 km away |
| What-if: rainfall forecast input | `--rain-scenario-mm N` cloudburst override of the forecast rain, diffed against the base run |
| Annex M governance: open data, aggregate alerts only | provenance + caveat footer in every artifact; commands carry no address-level detail |

## 2. Architecture

Thin package `poc-rijnland-gwt/`, importing:

- `poc.pipeline.geodata` — ArcGIS fetch + dual-CRS cache (PoC-1)
- `poc.pipeline.h3step` — nLDT H3 process bridge, cache-first, `POC_H3_OFFLINE=1`
- `poc-rijnland/rijnland.hexmap_time` — `build_cell_steps` + `render_hexmap_time` (PoC-3 bridge; animated single-file Leaflet page)

```
data/sources.json registry
  → geodata.fetch_layer: rijnland-gemaal (376); gwt.sensors.fetch_layer_attrs: rijnland-logger-grondwater (252 depth loggers — the service returns NULL geometry, so attribute-mode; geodata stays untouched)
  → rain: open-meteo archive (90 d) + forecast (5 d) over a 3×3 grid on the AOI, area mean per day (cache data/rain/)
  → archive: data/gwt/gwt.json — growing per-logger series (see §4 provenance)
  → predict: per-logger CART → depth(t+1); recursive to t+5; holdout MSE/MAE
  → triggers: thresholds → WaterpumpON/OFF/RetainWater + nearest gemaal + gaps → commands.json
  → hexmap: loggers → own H3 cells (h3.latlng_to_cell, default res 7 — the demo-slice loggers form a thin polder corridor where a hull-restricted join collapsed to ~2 cells and dropped 16 loggers; the bridge stays in for h3-cells-to-geojson) → render_hexmap_time (+ beacon overlay)
  → runs/<ts>-gwt-twin/: gwt-twin-report.json/.html, gwt-twin-hexmap.html, commands.json, commands-scenario.json, forecast.json, rain.json
```

One command: `nldt/.venv/bin/python poc-rijnland-gwt/run.py [--full] [--rain-scenario-mm 30] [--forecast-days 5] [--no-h3]`.

## 3. Data sources

| id | Content | Access |
|----|---------|--------|
| `rijnland-logger-grondwater` | 252 groundwater depth-logger meetpunten + polder/peil context (zomer/winterpeil, flex band) | `Meetlocatie_waterkwantiteit/MapServer` `where=SOORTOBJECT = 'Meetopstelling: Logger grondwater'`; NULL geometry → attribute-mode fetch (XCOORDINAAT/YCOORDINAAT) |
| `rijnland-meteo-neerslag` | 121 rain-gauge locations (context; no open series) | same service, `where=TYPEMETING='neerslag'` |
| `rijnland-gemaal` | 376 pump stations (capacity, coordinates) | `Gemaal/MapServer` |
| `open-meteo-archive` / `open-meteo-forecast` | daily precipitation (mm) past / forecast | keyless REST, verified reachable |
| `rijnland-gwt-archive` | per-logger daily depth series (m onder maaiveld) | local `data/gwt/gwt.json` |

**Not reachable (recon 2026-10-13):** BRO grondwaterstanden (`api.bro-data.nl` DNS/auth), Rijnland Lizard timeseries (`rijnland.lizard.net` auth-gated; the meetpunten carry a `LIZARDID` ready for it), grondwaterstanden.nl (defunct → haskoning.nl). Same situation as PoC-3 fase 2d (peil history); same answer: growing archive + documented fetch hook.

## 4. Archive provenance (honest surrogate)

Because no open GWT series resolves today, `archive.py` **seeds** the archive deterministically from the open sensor metadata + measured rain (seasonal sinusoid + rain-response + recession; parameters hashed from the logger code so runs are reproducible), clamped to plausible polder depths (0.2–2.5 m onder maaiveld, shallow in veenweide near the peil band). The archive JSON carries `"syntheticSeed": true` with the reason and the regeneration recipe; the report and every map print the caveat. When BRO/Lizard credentials arrive, `scripts/fetch_gwt.py` merges real series over the seed and the same pipeline runs unchanged — that is the exact growing-archive pattern of PoC-3 fase 2d.

## 5. Prediction & triggers

- **Features** per logger/day: depth lag-1, depth lag-3 (mean), rain 1/3/10-day sums, day-of-year (sin/cos). **Target:** depth t+1. numpy CART (variance reduction, max_depth 4, min leaf 8) — deliberate re-implementation of the thesis's interpretable decision tree, no sklearn dependency.
- **Forecast:** recursive day-ahead using the open-meteo forecast rain; `--rain-scenario-mm N` replaces forecast rain with a flat cloudburst on day +1.
- **Backtest:** holdout = last 20% of each logger's series; report MSE/MAE (thesis published none — explicit improvement) + persistence baseline for honesty.
- **Thresholds** (explicit, configurable — the thesis's "identification of thresholds" future work): ingress if depth ≤ `--ingress-depth 0.4` m → `WaterpumpON`; drought if depth ≥ `--drought-depth 1.2` m → `WaterpumpOFF` + `RetainWater`; else Monitor. Nearest gemaal (RD euclidean) attached when ≤ `--gemaal-radius-m 2500`, else the cell is an **action gap**.

## 6. Success criteria

- One CLI run writes report JSON/HTML + animated hex map + `commands.json`; scenario diff visible in the report.
- Offline unit tests pass without network (no H3 dependency in tests).
- Honest provenance: seed caveat in archive, report footer, README.
- Root README lists PoC-6.

## 7. Limits

- Depths are seeded, not measured (see §4); prediction quality numbers are therefore relative (model vs persistence), not absolute truth.
- Thresholds are configurable defaults, not board policy.
- Unity 3-D, IoT actuation and the thesis's questionnaire evaluation are out of scope; the SWOT in the README is the PoC's own evaluation frame for a follow-up expert session.
