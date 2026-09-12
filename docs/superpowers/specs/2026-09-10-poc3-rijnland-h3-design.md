# PoC-3 Rijnland H3 — Design

**Date:** 2026-09-10  
**Status:** Approved (brainstorming → plan)  
**Gallery:** [Rijnland op de kaart (Filter Gallery)](https://rijnland.maps.arcgis.com/apps/instant/filtergallery/index.html?appid=cc74a510ca1644d78dfb914e09cb1b5a)

## 1. Goal

PoC-3 answers water-authority planning questions over the **Hoogheemraadschap van Rijnland** beheergebied, using public ArcGIS REST layers from the Rijnland gallery and the existing **nldt H3** process suite (via the PoC-1 `h3step` bridge).

**MVP question:** *Where does practical peilbeheer diverge from the formal (vigerend) peilbesluit?*

**Phase 2 (deferred):** KRW water-quality clustering (Moran's I on H3) on the same package stack.

## 2. Architecture

**Thin package** `poc-rijnland/` that imports:

- `poc.pipeline.geodata` — ArcGIS REST fetch + dual-CRS cache
- `poc.pipeline.h3step` / `h3report` — cache-first H3 processes + Leaflet heatmap

No NormCards, no opportunity-map engine, no simulation tab in MVP.

```
Rijnland sources.json → geodata.fetch_layer (cache under poc-rijnland/data/cache/)
  → peilgebied (vigerend) ∪ peilafwijking (praktijk)
  → h3-polygon-to-cells (res 8) + restrictCells
  → peil-conflict report + h3-peil-conflict.json/.html
```

## 3. Conflict definition

1. Discretise the **vigerend peilgebied** union into H3 cells (res 8, centre-in-polygon).
2. Compute peilafwijking coverage on **exactly those cells** (`restrictCells`).
3. Per cell: `conflictFraction` = peilafwijking coverage fraction; `inZoneFraction` = peilgebied coverage fraction.
4. Headline: coverage-weighted conflict share (%); polygon areas remain authoritative — H3 is decision support.

Same pattern as PoC-1 crosstrack zon × Groene contour.

## 4. Data sources (MVP)

| id | Service | Layer |
|----|---------|-------|
| `rijnland-peilgebied-vigerend` | `…/Peilgebied_vigerend_besluit/MapServer` | 0 `PeilgebiedVigerend` |
| `rijnland-peilafwijking-praktijk` | `…/Peilafwijking_praktijk/MapServer` | 0 `PeilafwijkingGebied` |

Host: `rijnland.enl-mcs.nl`, CRS EPSG:28992, `f=geojson` supported, OID `OBJECTID2`.

## 5. Offline / determinism

- Geo cache: `poc-rijnland/data/cache/<id>.28992.geojson` (+ `.4326` twin)
- H3 cache: shared `poc/data/cache/h3/` via `h3step`
- Tests: `POC_H3_OFFLINE=1` + committed fixtures / bbox subset

## 6. Phase 2 — KRW monitoring coverage (implemented 2026-09-10)

Recon finding: the KRW-status water-body layers (KRW/MapServer 1–3) are
published empty and no measured water-quality values are exposed anywhere
in the Rijnland ArcGIS catalog. The live layer is MeetLocatie_Waterkwaliteit
(29,050 points, `WS_TYPEMETING`-discriminated). Phase 2 therefore measures
**monitoring coverage ∩ peil conflict**:

1. routine meetnet points (`WS_TYPEMETING = 'routine meetnet waterkwaliteit'`)
   → `h3-spatial-join-points` on the peilgebied cell grid → per-cell density
2. Moran's I on that density via `h3-morans-i`
3. blind spot = conflict cell with zero routine monitoring in the cell AND its
   `grid_disk(1)` neighbourhood → `h3-krw-blindspots.html` + `h3-krw-monitoring.json`

Caveat carried in every artifact: this is monitoring coverage, not measured
water quality. Original (spec-time) intent "peil conflict ∩ poor KRW" lands
when measured values become available.

## 6b. Phase 2b — measured water quality (implemented 2026-09-10)

Measured values DO exist at the national portal: the Waterkwaliteitsportaal
download API (`https://wkp.rws.nl/api/v1/data-downloads`, subject 15
"Meetgegevens" under Oppervlaktewaterkwaliteit) serves Rijnland's full
surface-water measurement set per year. `scripts/fetch_wkp.py` pulls a year
and aggregates to per-location annual medians (fixture with provenance under
`data/wkp/`). `rijnland/water_quality.py` joins locations onto the peilgebied
grid (`h3-spatial-join-points`), takes the per-cell median, scales against
the P10–P90 of all location medians (direction-aware per parameter: low
zuurstof = bad, high chloride = bad — no invented legal norms), and runs
Moran's I on the scaled values (`h3-morans-i`). Default chloride 2025:
143 locations / 124 cells, P10–P90 60–298 mg/l, Moran's I 0.70 (p=0.005).
Note: Power BI embeds expose no data API; the portal API is the same
request the downloadmodule UI makes. 2026 currently returns 6 rows.

## 6c. Phase 2c — time series 2020–2026 (implemented 2026-09-11)

`fetch_wkp.py --monthly` buckets every measurement (2020–2026, ~1.44M rows)
per parameter per month (median, P25–P75, n, nLocations across the whole
beheergebied). `run_timeseries.py` renders `rijnland/timeseries_report.py`'s
single-file page: parameter selector, monthly median with spread band,
centred 12-month rolling trend, month-of-year climatology panel, and a play
cursor sweeping the period (the "simulation"). Vanilla SVG/JS only — fully
offline, no CDN. 2026 shown as partial year in the provenance footer.

## 7. Success criteria (MVP)

- One CLI run writes report + H3 artifact + stitched NL-legend heatmap HTML
- Offline unit tests pass without network
- Root README lists PoC-3

## 6d. Phase 2d — water levels (implemented 2026-09-11)

Recon: measured peil history is not openly served — AGOL live layers carry
current values only, the public HydroNET efsserviceprovider chart endpoint
serves a fixed ~12-day window (verified: no range params, no alternative
endpoints), and HydroNET/RWS-waterinfo APIs need accounts. Delivered: a
growing archive instead — `fetch_peilen.py` snapshots all 315 stations
(polders+boezem, latest value + 12-day chart series → daily stats, merged
into `data/peilen/peilen.json`); `run_peilen.py` renders the timeseries
page (station selector, mediaan-polders/boezem aggregates, min–max band,
play cursor). The 2020–2026 window becomes reachable with HydroNet
credentials or by re-running the fetch forward in time.

## 6e. Phase 2e — animated hex maps (implemented 2026-09-12)

`hexmap_time.py`: one Leaflet page per time-stepped phenomenon — slider +
play cursor recolour the hexes per step (median over each cell's
locations; grey = no measurement that step). Quality: monthly steps
2020–2026, fixed P10–P90 colour scale (comparable frames), direction-aware
per parameter. Peilen: daily steps, deviation from each station's period
median in cm, symmetric scale. Bridge-only H3 (join + cells-to-geojson),
degree-tolerant coordinate intake (AGOL peil archive stores WGS84).
`fetch_wkp.py --monthly` now also emits per-location monthly medians
(aligned arrays) and caches year-zips on disk with retry/skip-year
tolerance for the portal's slow days.
