# Rijnland peilen what-if map — fase 2 multi-scenario (design)

**Status:** implemented (2026-09-14) — see
[`nldt/15-cdc-data-lake-pipeline.md`](../../../nldt/15-cdc-data-lake-pipeline.md#multi-scenario-map-fase-2--implemented)
and plan
[`../plans/2026-09-14-rijnland-peilen-whatif-map-fase2.md`](../plans/2026-09-14-rijnland-peilen-whatif-map-fase2.md).

**Vraag.** Hoe tonen we **meerdere peilen-scenario’s in één** Breda-stijl
`whatif-map.html`, met een vast demopakket, terwijl de lake-pipeline alleen het
CLI-/process-scenario disposet?

Bouwt voort op v1:
[`2026-09-14-rijnland-peilen-whatif-map-design.md`](2026-09-14-rijnland-peilen-whatif-map-design.md).

## Beslissingen (vast)

| Keuze | Waarde |
|-------|--------|
| Scenario-bron | **B** — vast demopakket onder `nldt/examples/` |
| Lake / CDC | **A** — alleen het actieve CLI/process-scenario → bronze/silver |
| Payload-vorm | **Aanpak 1** — één Point-FC + `byScenario[id]` per station |
| UI | Paneel met meerdere scenario-kaarten; klik → client-side herkleuren |
| Actief scenario | CLI/process-run; in paneel gemarkeerd (lake); default geselecteerd |

## Scope v1 (fase 2)

**In:**

1. Demopakket-bestand:
   `nldt/examples/rijnland-whatif-demo-pack.json` — array `scenarios` met
   2–3 vaste entries (voorstel):
   - `boezem-plus5cm` — layer `boezem`, `delta_m: 0.05`
   - `boezem-minus5cm` — layer `boezem`, `delta_m: -0.05`
   - `polders-plus10cm` — layer `polders`, `delta_m: 0.10`
2. Loader `load_demo_pack(path | default) -> list[dict]` in
   `nldt/services/rijnland_whatif.py`.
3. `build_multi_scenario_map_payload(archive, active_scenario, demo_scenarios)`:
   - Past **elk** scenario (demo + active) toe via bestaande
     `apply_scenario_to_archive` op een **verse** baseline-kopie (niet
     cumulatief).
   - Bouwt Point FeatureCollection: coords + `name`/`layer`/`id` uit baseline;
     `properties.byScenario[scenarioId] = {before, after, delta_m, touched}`.
   - `scenarios[]` meta: id, title, description, delta_m, layer, n (touched),
     `lakeApplied: bool` (true alleen voor active).
   - Dedupe: als active `id` al in demopakket zit, één card; `lakeApplied: true`.
4. Uitbreiden `build_whatif_map_html` (of dunne wrapper) om multi-payload te
   renderen: klik scenario wisselt `actScen`; modi na/vóór/Δ lezen
   `byScenario[actScen]`. Ontbrekende `byScenario` → station niet getekend of
   grijs (baseline).
5. `run_whatif`:
   - Lake-pad ongewijzigd: alleen `active` scenario → CDC/silver/tabel/`peilen-whatif.json`.
   - Map: multi-payload (demo + active).
   - Summary: `mapHtml`, `demoPack`, `scenariosOnMap` (ids).
6. CLI: optioneel `--demo-pack PATH` (default demopakket); `--no-demo-pack`
   → gedrag als v1 (alleen active op de kaart).
7. Tests: pack load; multi-payload heeft ≥2 scenarios; lake apply niet
   aangeroepen voor demo-only ids; HTML bevat alle scenario-ids; bestaand
   single-scenario pad blijft groen met `--no-demo-pack` equivalent in API
   (`include_demo_pack=False`).
8. Docs: korte paragraaf in `nldt/15-cdc-data-lake-pipeline.md`.

**Uit:**

- Meerdere lake-batches / silver voor demoscenario’s.
- Cumulatieve mutaties (scenario B op resultaat van A).
- Hex / peil-conflict herattach (fase 3).
- MCP artefact-tools (fase 4).
- Wijzigingen aan `poc-breda/`.

## Dataflow

```
baseline peilen.json
    ├─ apply(active) → peilen-whatif.json, changes, CDC/silver (if enabled)
    ├─ apply(demo_i) in-memory only → touched counts + per-station deltas
    └─ merge → whatif-map.html
         window.__DATA__ = {
           scenarios: [...demos, active...],  // lakeApplied flags
           geo: FeatureCollection,
           defaultMode: "after",
           defaultScenarioId: active.id,
           modes: ["after","before","delta"]
         }
```

## Payload (contract)

```json
{
  "scenarios": [
    {
      "id": "boezem-plus5cm",
      "title": "...",
      "description": "...",
      "delta_m": 0.05,
      "layer": "boezem",
      "n": 184,
      "lakeApplied": true
    }
  ],
  "geo": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
          "id": "station-id",
          "name": "...",
          "layer": "boezem",
          "byScenario": {
            "boezem-plus5cm": {
              "before": -0.566,
              "after": -0.516,
              "delta_m": 0.05,
              "touched": true
            }
          }
        }
      }
    ]
  },
  "defaultMode": "after",
  "defaultScenarioId": "boezem-plus5cm",
  "modes": ["after", "before", "delta"]
}
```

Stations zonder coords blijven weggelaten. Voor modi: shared absolute domain
over alle `before`/`after` in **alle** scenarios op de kaart (stabiele legenda
bij wisselen); Δ-domain = max |delta| over actief scenario of global maxAbs.

## UX

- Paneel toont alle scenarios; actieve (lake) card heeft badge “lake” / “actief”.
- Default selectie = `defaultScenarioId` (CLI/process).
- Modi na / vóór / Δ ongewijzigd t.o.v. v1, maar waarden uit `byScenario[actScen]`.
- Carto-tegels + jsDelivr Leaflet blijven (geen OSM 403).
- Doctrine-regel in header/footer.

## Bestanden

| Bestand | Rol |
|---------|-----|
| `nldt/examples/rijnland-whatif-demo-pack.json` | Vast demopakket |
| `nldt/examples/rijnland-whatif-boezem-plus5cm.json` | Blijft single-scenario voorbeeld |
| `nldt/services/rijnland_whatif.py` | Pack load, multi-payload, HTML JS, `run_whatif` flags |
| `nldt/scripts/rijnland_whatif_peilen.py` | `--demo-pack` / `--no-demo-pack` |
| `nldt/tests/test_rijnland_whatif.py` | Multi + lake isolation tests |
| `nldt/15-cdc-data-lake-pipeline.md` | Smoke multi-map |

## Succescriteria

1. Eén run opent een kaart met ≥3 scenario-cards (2+ demo + active, na dedupe).
2. Klikken wisselt kleuren client-side zonder herladen.
3. Alleen active scenario heeft CDC-batch / silver (als lake aan); demos niet.
4. `--no-demo-pack` (of API flag) reproduceert v1 single-scenario map.
5. Tests groen offline.

## Niet-doelen / later

- Fase 3: hex / conflict op what-if peilen.
- Fase 4: MCP list/open artefact URI.
- LLM-gegenereerde scenario-variants in het pack.
