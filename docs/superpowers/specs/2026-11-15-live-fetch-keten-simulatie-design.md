# Ontwerp — Live fetch-keten-simulatie in `nldt/simulation/live/`

| | |
|---|---|
| **Datum** | 15 november 2026 |
| **Status** | goedgekeurd in brainstorm (aanpak A); klaar voor implementatieplan |
| **Scope** | Live server + pagina in `nldt/simulation/live/`: fetch-keten via échte MCP-tool-calls, gescripte agent, SSE-trace, kaartweergave; één nieuwe MCP-tool `fetch_geo_layer` |
| **Niet in scope** | Formaliseren/engine/scenario's; LLM-agent; NGSI-LD subscriptions/temporal; multi-user; auth op de demo-server zelf; wijzigingen aan de bevroren `simulation/simulation.html` |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Live-moment | Tijdens het kijken — pijplijnstappen worden dán uitgevoerd (server vereist; geen `file://` single-file meer) |
| Data-fetch | Elke datalink via een echte tool call — MCP (of API), nooit directe interne aanroepen |
| Eerste keten | Alleen de fetch-keten: catalogus → DSO-kennisbank → agrest/ArcGIS-geolagen → NGSI-LD-entities |
| Aansturing | Gescripte agent: vast script, elke stap = één echte MCP `call_tool`, resultaten streamen naar de UI (deterministisch, geen LLM) |
| Plaatsing | `nldt/simulation/live/`, naast de bestaande flow-demo's |
| Architectuur | **A** — één FastAPI-app mount de bestaande MCP-servers (`build_mcp_http_app`) + echte MCP-client over loopback (`streamable-http`) |

## Context

- Aanleiding: NGSI-LD is sinds 14 nov. een geobron voor de PoC-pijplijn (`geodata.fetch_layer` dispatcht op `ngsi-ld://`-bronnen; register-entry `ngsi-ld-dpl-airquality`; tests in `poc/tests/test_geodata_ngsi.py`).
- De bestaande `simulation/simulation.html` is een bevroren replay van canonical runs — bewust onaangeroerd gelaten.
- MCP-servers (FastMCP, `mcp>=1.0.0`) hebben al `streamable-http` achter een bearer-gate (`services/mcp_servers/http_transport.py`, zusters op :8090–8093); `fastapi`/`uvicorn` staan in `nldt/requirements.txt`.
- `data_server` ontsluit al `list_entities` + `entities_to_geojson`; `dso_server`/`dso_tools` de DSO-kennisbank; `catalog_server` registratie-ontdekking.
- Gat: de agrest/ArcGIS-fetch (`poc/pipeline/geodata.py`) is nog niet via MCP ontsloten — alleen `fetch-features` (NGSI-LD) is dat.
- De PoC-pijplijn is standaard deterministisch (LLM-stappen opt-in met fallback); geo-bronnen zijn cache-first, NGSI-LD mock-first — een live run is offline deterministisch uitvoerbaar.

## Architectuur

```text
                        nldt/simulation/live/  (uvicorn, 127.0.0.1:8095)
  ┌──────────────────────────────────────────────────────────────────┐
  │ server.py (FastAPI)                                              │
  │   /mcp/data    ┐   /mcp/dso    ┐   /mcp/catalog    ┐             │
  │   (build_mcp_http_app-mounts; parent-lifespan start alle        │
  │    session-managers; bearer-gate = bestaand gedrag op loopback)  │
  │                                                                  │
  │   POST /api/session        → start fetch-run (session-id)        │
  │   GET  /api/session/:id/events  → SSE-eventstroom               │
  │   GET  /api/layers/:source_id   → WGS84-cache-twin als GeoJSON   │
  │   / (index.html + assets)                                        │
  └──────────────────────────────────────────────────────────────────┘
        ▲ SSE                  ▲ echte MCP call_tool (streamable-http,
        │                      │  loopback via mcp-sdk)
   index.html             agent.py + mcp_client.py + fetch_script.py
   (SVG-kaart + trace)    (gescripte agent: vaste stappenlijst)
                                   │
                                   ▼
   data_server · dso_server · catalog_server · poc_server(+fetch_geo_layer)
        │                    │                          │
        ▼                    ▼                          ▼
   NGSI-LD (mock/broker)  DSO-kb (fs-cache)   poc geodata (cache-first,
                                             agrest/ArcGIS + ngsi-ld://)
```

## Componenten

### `server.py` — één FastAPI-app
- Mount `data_server`, `dso_server`, `catalog_server` als sub-apps via `build_mcp_http_app` op `/mcp/data`, `/mcp/dso`, `/mcp/catalog` (poc_server voor `fetch_geo_layer`, mount `/mcp/poc`).
- Parent-lifespan start de session-managers van alle gemounte servers (gemounte ASGI-apps krijgen geen lifespan-events; zelfde patroon als `http_transport.py`).
- Standaard bind `127.0.0.1`, poort `8095` (env `NLDT_LIVE_SIM_PORT`/`NLDT_LIVE_SIM_HOST`).

### `mcp_client.py` — echte MCP-client
- Wrapper rond de `mcp`-python-sdk (`streamablehttp_client`); elke scriptstap is een echte `call_tool` over het MCP-protocol naar de eigen loopback-mounts.

### `agent.py` + `fetch_script.py` — gescripte agent
- `fetch_script.py`: declaratieve stappenlijst (server, tool, args, laag-label, samenvattingsfunctie) — data, geen vertakking.
- `agent.py`: doorloopt de lijst, emits events per stap. Geen LLM, geen condities: de deterministische garantie ("no invented numbers") blijft overeind.

### Nieuwe MCP-tool `fetch_geo_layer` (in `poc_server`/`poc_tools`)
- `fetch_geo_layer(source_id, bbox?, refresh?)` → wrapper rond `poc/pipeline/geodata.fetch_layer` (poc op `sys.path`, zoals `dso_kb` al doet).
- Retourneert een compacte samenvatting: `featureCount`, provenance (o.a. `protocol`, `entityType`, `dataPlatformMock`), cache-paden van beide twins — níét de geometrie zelf.
- De UI leest de GeoJSON via `/api/layers/{source_id}` (WGS84-twin uit de cache). Tool-antwoorden blijven klein en protocol-vriendelijk.

## Fetch-script v1 (vaste volgorde)

| # | Stap | Tool |
|---|------|------|
| 1 | "Wat is beschikbaar?" | `catalog.list_poc_capabilities` |
| 2 | Regels-instrumenten voor het gebied (o.a. Utrecht CVDR704250) | `dso.dso_kb_overview` |
| 3 | Inclusion-zone wind (44 features, cached) | `poc.fetch_geo_layer("agrest-ov-gebied-windenergie")` |
| 4 | Externe kaartlaag wind (cached) | `poc.fetch_geo_layer("arcgis-et-wind-gebieden")` |
| 5 | NGSI-LD-sensorkpunten (mock of live broker) | `data.list_entities("AirQualityObserved")` → `data.entities_to_geojson` |

Elke stap is zichtbaar als tool call in de trace en voegt een laag toe aan de kaart.

## Events (SSE-protocol)

| Event | Payload |
|---|---|
| `step_started` | `{index, label, server, tool, args}` |
| `tool_result` | `{index, ok, duration_ms, summary}` |
| `layer_ready` | `{source_id, laagtype}` (UI laadt `/api/layers/{source_id}`) |
| `run_done` | `{per-stap status, totaal}` |
| `error` | `{stap, melding}` — run stopt; herstart is goedkoop (cache-first/mock maken stappen direct) |

## UI (`index.html`, geen build-step)

- Stijl van de bestaande demos: donker, eigen SVG-kaartprojectie, geen externe dependencies.
- Links de **tool-call trace** (args, duur, status, uitklapbaar); rechts de **kaart** waarop lagen stap-voor-stap verschijnen (provinciegrens → zones → sensorkpunten).
- Prominente **MOCK/LIVE-badge** zodra de NGSI-LD-stap `dataPlatformMock: true` rapporteert — de simulatie liegt nooit over herkomst.

## Foutafhandeling

- Broker niet geconfigureerd → adapter-mock (badge MOCK).
- agrest onbereikbaar → cache-first vangt af (volledig offline bruikbaar).
- Stap faalt → `error`-event, run stopt, pagina biedt herstart.
- Server bindt standaard op `127.0.0.1`.

## Testing

`nldt/tests/test_live_sim_*.py`:
- Script-stappen tegen een gemockte MCP-client: event-vorm en volgorde deterministisch.
- `fetch_geo_layer`-tool met mock-adapter (patroon van `poc/tests/test_geodata_ngsi.py`).
- SSE-endpoint smoke via `httpx.TestClient`.
- Geen netwerk nodig in tests.

## Uitbreidingspad (na v1)

Formaliseren/engine/scenario's als vervolgstappen in hetzelfde script-model (elke stap = tool call); NGSI-LD subscriptions/temporal als aparte live-dimensies; LLM-agent als alternatieve driver achter dezelfde event-protocol.
