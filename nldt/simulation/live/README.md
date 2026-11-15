# Live fetch-keten — simulatie die de stappen echt uitvoert

> Spec: [docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md](../../../docs/superpowers/specs/2026-11-15-live-fetch-keten-simulatie-design.md)

## Starten

```bash
cd nldt
.venv/bin/python simulation/live/server.py     # 127.0.0.1:8095 (env: NLDT_LIVE_SIM_PORT/HOST)
open http://127.0.0.1:8095
```

Klik **▶ Start fetch-keten**. De gescripte agent doorloopt zes stappen, elke
stap is één **echte MCP-toolcall** (streamable-http over loopback tegen de
gemounte servers `/mcp/{data,dso,catalog,poc}`):

1. `catalog.list_poc_capabilities` — wat is beschikbaar?
2. `dso.dso_kb_overview` — regels-instrumenten in het gebied
3. `poc.fetch_geo_layer("agrest-ov-gebied-windenergie")` — inclusion-zone wind (cache-first)
4. `poc.fetch_geo_layer("arcgis-et-wind-gebieden")` — kaartlaag wind (cache-first)
5. `data.list_entities("AirQualityObserved")` — NGSI-LD entities
6. `data.entities_to_geojson("AirQualityObserved")` — naar GeoJSON (inline laag)

De kaart vult per stap; de trace toont args, duur en samenvatting. De badge
rechtsboven toont de NGSI-LD-herkomst: **MOCK** (adapter-mock, default) of
**LIVE** (zet `NLDT_NGSI_LD_URL` of `NLDT_DATA_PLATFORM_URL` en zet
`NLDT_DATA_PLATFORM_MOCK=false`).

De server zet `NLDT_OFFLINE=1` voor zichzelf: poc-/dso-tools executeren
in-process via de job-store. ArcGIS/agrest-lagen komen cache-first uit
`../poc/data/cache/` (repo-root `poc/data/cache/`) — offline deterministisch;
`NLDT_LIVE_SIM_BASE` overschrijft de loopback-basis-URL (gebruikt door de
E2E-test op een vrije poort).

> Bekende beperking v1: LIVE-/refresh-stappen blokkeren momenteel de event
> loop van de server (sync adapter-aanroepen) — bij live broker/refresh
> stokt de SSE kort; het offline/cache/mock-pad is instant en heeft dit
> niet.

## Tests

```bash
cd nldt && .venv/bin/python -m pytest tests/test_live_sim_*.py -v
```
