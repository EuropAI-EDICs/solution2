# Rijnland peilen what-if — Breda-stijl kaart (design)

**Vraag.** Hoe laten we een peilen-what-if (CDC → silver) **ruimtelijk** lezen,
in hetzelfde idioom als Breda `what-if.html` (Leaflet + scenario-paneel,
client-side herkleuren), i.p.v. alleen een Δ-tabel waar uniforme scenario’s
overal dezelfde delta tonen?

## Waarom deze afbakening

- Breda: `poc-breda/breda/scenarios.py` → `build_whatif_html` — offline Leaflet,
  paneel met scenario-kaarten, modi die de laag client-side herkleuren.
- Rijnland what-if vandaag: `nldt/services/rijnland_whatif.py` schrijft
  `whatif-diff.html` (tabel) + `peilen-whatif.json` (stations met `x`,`y` en
  `latest.whatIf`). Geen kaart.
- Uniforme Δ (bijv. boezem +5 cm) maakt een Δ-kleurkaart saai; **absolute peilen
  vóór/na** tonen spatiale variatie. Δ-modus blijft beschikbaar voor latere
  lokale/non-uniforme scenario’s.

## Scope v1

**In:**

1. Nieuw artefact `whatif-map.html` per what-if-run (naast `whatif-diff.html`).
2. Builder `build_whatif_map_html(...)` in `nldt/services/rijnland_whatif.py`
   (Breda-idioom, peilen-semantiek — geen fork van five-value jargon).
3. Aanroep vanuit `run_whatif()`; report/summary mag `mapHtml` / pad opnemen.
4. Data uit bestaande run: stations uit scenario-archive + changes.
5. UI:
   - Leaflet 1.9.4 CDN + OSM-tiles (zelfde stack als Breda).
   - Scenario-paneel: klikbare scenario-kaart(en); v1 = één actief scenario
     (payload-structuur al multi-scenario-ready: `scenarios[]` + `perStation`).
   - Map modes: **na** (default) | **vóór** | **Δ**.
   - `circleMarker` per station met peil; touched stations duidelijker
     (rand/weight); untouched optioneel lichter of weggelaten in Δ-modus.
   - Popup: naam, laag, voor → na, Δ m.
   - Legenda op absolute mNAP (vóór/na) of cm-Δ.
   - Doctrine-regel in footer/header.
6. Test: unit test dat HTML `window.__DATA__` + Leaflet-hook bevat en dat
   GeoJSON-punten x/y uit archive krijgen; bestaande what-if-tests blijven groen.
7. Docs: korte vermelding in `nldt/15-cdc-data-lake-pipeline.md` (smoke: open
   `whatif-map.html`).

**Uit (v1):**

- H3 / hexmap_time / peil-conflict herberekening met what-if peilen.
- Meerdere gelijktijdige scenario-varianten in één run (structuur voorbereiden,
  UI mag één tonen).
- Non-uniforme per-station deltas (bestaande `delta_m` blijft; latere scenario’s
  kunnen `stationIds` + aparte runs).
- React/MapLibre; geen wijziging aan Breda-code.
- Live CDC-OLTP schrijven vanuit de kaart (doctrine: pipeline disposes).

## Dataflow

```
scenario (delta_m, layer, …)
    → apply_scenario_to_archive
    → peilen-whatif.json + changes.json
    → build_whatif_map_html(archive, changes, scenario)
         payload: {
           scenarios: [{ id, title, description, delta_m, layer, n }],
           stations: FeatureCollection Point (lon=x, lat=y,
             props: id, name, layer, before, after, delta_m, touched),
           modes: ["after","before","delta"],
           defaultMode: "after"
         }
    → runs/<ts>-peilen-whatif/whatif-map.html
```

Stations zonder `x`/`y` worden overgeslagen (tellen in report optioneel
`stationsMissingCoords`).

## UX (Breda-idioom, peilen-semantiek)

| Breda | Rijnland peilen what-if |
|-------|-------------------------|
| Scenario-kaarten in paneel | Idem; titel/beschrijving/Δ/laag/n stations |
| Modus “waarden onderling” / “volg één waarde” | Modus **na** / **vóór** / **Δ** |
| Buurt-polygons choropleth | Station `circleMarker` (radius ~ peil-schaal of vast + opacity) |
| Popup met waarden | Popup voor → na + Δ |
| Offline CDN Leaflet | Idem |

Kleur: continue schaal over absolute mNAP voor vóór/na (gedeelde domain over
beide, zodat toggle niet “springt”); Δ-modus divergente schaal rond 0
(groen/rood of blauw/oranje — water-neutraal, geen Breda-congreskleuren).

## Bestanden

| Bestand | Wijziging |
|---------|-----------|
| `nldt/services/rijnland_whatif.py` | `build_whatif_map_html`; aanroep in `run_whatif` |
| `nldt/tests/test_rijnland_whatif.py` | assert map artefact |
| `nldt/15-cdc-data-lake-pipeline.md` | smoke-pad map |
| Optioneel recipe/report keys | `mapHtml` in summary |

Geen wijziging aan `poc-breda/`. Optioneel later: CLI-flag `--no-map`.

## Succescriteria

1. Na `rijnland_whatif_peilen.py --delta-m 0.05 --layer boezem` opent
   `whatif-map.html` een kaart met boezemstations; **na**-kleuren variëren
   ruimtelijk (niet één platte Δ-kleur).
2. Toggle vóór ↔ na herkleurt client-side zonder herladen.
3. Δ-modus toont uniforme tint bij +5 cm (verwacht) maar blijft bruikbaar.
4. Zelfde run behoudt tabel + CDC/silver gedrag.
5. Tests groen offline (Leaflet-CDN-foutpad net als Breda: nette fallbacktekst).

## Niet-doelen / latere fasen

- ~~Fase 2: multi-scenario in één HTML~~ — **done**
  ([fase2 design](2026-09-14-rijnland-peilen-whatif-map-fase2-design.md)).
- Fase 3: hex-choropleth of peil-conflict herattach op what-if peilen.
- Fase 4: MCP-tool `open`/`list` artefact-URI voor agents.
