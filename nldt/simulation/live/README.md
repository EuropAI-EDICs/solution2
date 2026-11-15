# Live fetch-keten — simulatie die de stappen echt uitvoert

> Spec: [docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md](../../../docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md)

## Starten

```bash
cd nldt
.venv/bin/python simulation/live/server.py     # 127.0.0.1:8095 (env: NLDT_LIVE_SIM_PORT/HOST)
open http://127.0.0.1:8095
```

Klik **▶ Start fetch-keten** — kies eerst een PoC in de switcher. Elke stap
is één **echte MCP-toolcall** (streamable-http over loopback tegen de
gemounte servers `/mcp/{data,dso,catalog,poc}`).

## Chains (zes PoC's uit simulation.html)

De pagina heeft een PoC-switcher; elke chain is een vaste stappenlijst waarin
elke stap één echte MCP-toolcall is:

| Chain | Stappen (kern) | Kaartlagen | Duur |
|---|---|---|---|
| PoC-1 · Utrecht (wind) | capabilities → dso-kb → 2× fetch_geo_layer → NGSI ×2 → `run_opportunity_map(execute, wind)` → `run_artifact(zones.geojson)` | 4 | ~10–60 s (engine) |
| PoC-2 · BP→OP Eindhoven | capabilities → dso-kb → `run_bp2op_transform(execute)` → `run_artifact(omzettabel.json)` | — | seconden |
| PoC-4 · Breda vijf-waarden | capabilities → `run_value_scan(execute)` → `run_artifact(geo-buurten.wgs84.geojson)` | buurtkaart | seconden |
| Gent · EUROPAI-piloot | capabilities → `gent_life_event_run(execute)` → `run_artifact(run.json)` | — | seconden |
| Veenendaal · Spoorzone | capabilities → `veenendaal_gebiedscheck_run(execute)` → `run_artifact(indicators.json)` | — | seconden |
| DSO ↔ RegelRecht | capabilities → dso-kb → `dso_kb_annotations` → `dso_kb_tpod` | — | instant |

`run_artifact` leest pipeline-output (zones, buurtkaart, tabellen) via MCP en
geeft de inhoud inline terug; de `runDir` komt letterlijk uit het resultaat
van de pipeline-stap (`args_uit_vorige`) — geen verzonnen paden. Zware
pipeline-stappen executeren echt (cache-first voor data); de SSE-stream blijft
levend door `asyncio.to_thread` in de tool-lagen.

De kaart vult per stap; de trace toont args, duur en samenvatting. De badge
rechtsboven toont de NGSI-LD-herkomst: **MOCK** (adapter-mock, default) of
**LIVE** (zet `NLDT_NGSI_LD_URL` of `NLDT_DATA_PLATFORM_URL` en zet
`NLDT_DATA_PLATFORM_MOCK=false`).

De server zet `NLDT_OFFLINE=1` voor zichzelf: poc-/dso-tools executeren
in-process via de job-store. ArcGIS/agrest-lagen komen cache-first uit
`../poc/data/cache/` (repo-root `poc/data/cache/`) — offline deterministisch;
`NLDT_LIVE_SIM_BASE` overschrijft de loopback-basis-URL (gebruikt door de
E2E-tests op een vrije poort).

## Tests

```bash
cd nldt && .venv/bin/python -m pytest tests/test_live_sim_*.py -v
```
