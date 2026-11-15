# Ontwerp — Live-sim voor alle PoC's uit `simulation.html`

| | |
|---|---|
| **Datum** | 15 november 2026 |
| **Status** | goedgekeurd in brainstorm (benadering A); klaar voor implementatieplan |
| **Scope** | Uitbreiding van de live fetch-keten (`nldt/simulation/live/`) naar zes PoC-chains uit simulation.html: pipeline-stappen per PoC via MCP, switcher in de UI, twee nieuwe process-wrappers (Gent, Veenendaal), nieuwe tool `run_artifact`, async-executie via `asyncio.to_thread` |
| **Niet in scope** | Scenario-sweep/crosstrack als chain-stappen; Rijnland/NSPD/minigim; parallelle sessies; NL/EN-toggle in de live-pagina; wijzigingen aan de bevroren `simulation/simulation.html` |
| **Basis** | [2026-11-15-live-fetch-keten-simulatie-design.md](2026-11-15-live-fetch-keten-simulatie-design.md) — server, mounts, event-protocol en UI-pattern blijven ongewijzigd |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Live-scope | Pipeline-stappen per PoC via bestaande MCP-processen; dunne wrappers voor Gent/Veenendaal |
| Live-diepte | Alles echt executeren (execute-modus), cache-first voor data — geen replay op bevroren runs |
| UI-vorm | PoC-switcher (chips) in de bestaande live-pagina; één server, één entree |
| Architectuur | **A** — chain-registry in de live-sim; stap-model ongewijzigd (één tool call per stap) |

## Context

- `simulation.html` toont zes PoC's: tab 1 PoC-1 Utrecht (wind·zon·bos), tab 2 PoC-2 BP→OP Eindhoven, tab 4 Breda vijf-waarden, tab 5 Gent EUROPAI-piloot, tab 6 Veenendaal Spoorzone, tab 7 DSO↔RegelRecht.
- MCP-dekking vandaag: Utrecht (`opportunity-map-run`, `fetch-geo-layer`, `crosstrack-overlay`), Eindhoven (`bp2op-transform`), Breda (`breda-scan-run`), DSO↔RR (`dso_server`-tools, al gemount). Gent en Veenendaal: niets geregistreerd.
- Executor-contracten geverifieerd: `opportunity-map-run` (mode replay\|execute, useCase wind\|zon\|bos), `bp2op-transform` (mode, useCase=eindhoven, outDir), `breda-scan-run` (mode → subprocess `poc-breda/run.py`), Gent `poc-gent/run.py` (argparse: `--package gent-mobiliteit-ondernemer`, `--persona sanne`, `--auth eudi`; deterministische replay fase 1+2+3), Veenendaal `poc-veenendaal/run.py` (`main(refresh=False)` als aanroepbare functie).
- Beperking uit de eindreview van de fetch-keten: sync-executors blokkeren de event loop — bij multi-seconde pipeline-stappen wordt dit de norm; `asyncio.to_thread` is daarom onderdeel van dit ontwerp.

## Architectuur

```text
  index.html (chips: Utrecht · Eindhoven · Breda · Gent · Veenendaal · DSO↔RR)
        │ POST /api/session {chain}          GET /api/chains
        ▼
  server.py ── SessionStore (contract ongewijzigd: één actief)
        │
  chains.py (registry: id, label, stappen)  ← verving fetch_script.py-rol
        │ ScriptedAgent(client, stappen=CHAIN[id])
        ▼
  McpLoopbackClient ─ echte MCP call_tool (loopback-mounts, ongewijzigd)
        │
        ├─ catalog.list_poc_capabilities
        ├─ dso.dso_kb_overview / dso_kb_annotations / dso_kb_tpod
        ├─ poc.fetch_geo_layer (Utrecht-zones)
        ├─ poc.list_entities / entities_to_geojson (NGSI)
        ├─ poc.opportunity-map-run (execute, wind)        [bestaand]
        ├─ poc.bp2op-transform (execute, eindhoven)       [bestaand]
        ├─ poc.breda-scan-run (execute)                   [bestaand]
        ├─ poc.gent-life-event-run (execute)              [NIEUW proces]
        ├─ poc.veenendaal-gebiedscheck-run (execute)      [NIEUW proces]
        └─ poc.run_artifact(run_dir, artifact)            [NIEUWE tool → inline geojson]
```

Alle offline-toolpaden wrappen hun sync-executor in `asyncio.to_thread`, zodat de SSE-stream levend blijft tijdens lange stappen.

## Componenten

### `chains.py` — chain-registry (vervangt `fetch_script.py` volledig)
- `fetch_script.py` wordt hernoemd/vervangen door `chains.py`: de bestaande `STAPPEN`-lijst wordt de `utrecht`-chain (opgeschoond: de twee losse NGSI-stappen en de `fetch_geo_layer`-stappen blijven, de oude catalog/dso-stappen blijven), aangevuld met de vijf nieuwe chains.
- `agent.ScriptedAgent` behoudt `stappen=None` → nu default de `utrecht`-chain uit chains.py; de server geeft de gekozen chain door.
- Declaratief: per chain `{id, label, stappen}`; stap-model identiek aan de fetch-keten (`label`, `server`, `tool`, `args`, `samenvatting`, optioneel `laag`).
- Zes chains (exacte artifact-paden worden in de planning geverifieerd tegen executor-outputs):

| Chain | Stappen (tool-kern) | Lagen |
|---|---|---|
| utrecht | capabilities → dso_kb_overview → 2× fetch_geo_layer → NGSI ×2 → opportunity-map-run(execute, wind) → run_artifact(zones) | 2 zone-lagen + NGSI-punten + zones-laag |
| eindhoven | capabilities → dso_kb_overview → bp2op-transform(execute) → run_artifact | resultaat-laag |
| breda | capabilities → breda-scan-run(execute) → run_artifact(geo-buurten) | buurt-laag (56 features, inline) |
| gent | capabilities → gent-life-event-run(execute) → run_artifact | pakket-kaartlaag |
| veenendaal | capabilities → veenendaal-gebiedscheck-run(execute) → run_artifact | zonering-laag |
| dsorr | dso_kb_overview → dso_kb_annotations(utrecht-domplein) → dso_kb_tpod | geen kaartlagen (tekst-trace) |

### Nieuwe process-wrappers (poc_handlers, poc-server-patroon)
- **`gent-life-event-run`**: subprocess `poc-gent/run.py --package gent-mobiliteit-ondernemer --persona sanne --auth eudi`; outputs: samenvatting (fases 1+2+3 status) + pakket-pad/run-dir.
- **`veenendaal-gebiedscheck-run`**: aanroep `poc-veenendaal.run.main(refresh=False)` in-process; outputs: samenvatting + run-dir.
- Beide volgen het `fetch-geo-layer`-patroon: dun, PoC-engine blijft autoriteit, offline-deterministisch.

### Nieuwe tool `run_artifact(run_dir, artifact)` (poc_server + poc_tools)
- Leest één bestand uit een run-dir en geeft de inhoud inline terug (JSON/GeoJSON als tekst). Beveiliging: pad-resolutie onder de opgegeven `run_dir` (geen `..`-ontsnapping), bestand moet bestaan, grootte-plafond (bijv. 5 MB) — tool-antwoord blijft protocol-vriendelijk.
- Doel: pipeline-resultaten (zones, buurtkaart, Gent-kaart) komen via een echte tool call als inline `layer_ready`-geojson, conform "elke datalink via MCP".

### Async-executie
- `poc_server._run_poc_tool` (offline-tak), `data_server.list_entities/entities_to_geojson` en de `dso_server`-lokale-uitvoering wrappen sync-aanroepen in `asyncio.to_thread`.
- Sequentiële script-stappen = geen intra-sessie-gelijktijdigheid; single-active-sessie-contract blijft.

## API

| Endpoint | Wijziging |
|---|---|
| `POST /api/session` | body `{chain: "<id>"}` (default `utrecht`); onbekende chain → 400 |
| `GET /api/chains` | nieuw: `[{id, label, stepCount}]` voor de switcher |
| `GET /api/session/{sid}/events` | ongewijzigd (zelfde vijf eventnamen) |
| `GET /api/layers/{source_id}` | ongewijzigd (Utrecht cache-twins) |

## UI

- Chips-rij bovenaan met de zes chains; actieve chip gemarkeerd; start-knop start de geselecteerde chain.
- Trace/kaart/badge werken ongewijzigd; chains zonder kaartlagen (dsorr) laten de kaart leeg met een korte notitie.
- Lange stappen: de trace toont de lopende stap als "• wacht" (gedrag ontstaat vanzelf doordat `tool_result` pas na afloop komt).

## Timing en foutafhandeling

- Alles echt executeren, cache-first voor data: Utrecht ~10-60 s (engine), Breda/Eindhoven/Gent/Veenendaal seconden, DSO↔RR instant.
- Stap faalt → bestaand `error`-event, run stopt; herstart met dezelfde of andere chain direct mogelijk (sessie-slot vrij na afloop — fix-golf uit de fetch-keten).
- `to_thread` geeft geen intra-sessie-gelijktijdigheid (sequentieel script).

## Testing

Uitbreiding van de testfamilie (`nldt/tests/test_live_sim_*.py`):
- chains-registry: elke chain resolvet uitsluitend naar geregistreerde tools; stap-tellingen en lagen-vormen deterministisch.
- twee nieuwe processen: offline-executie met geïsoleerde uitvoer (tmp/outDir), contract van samenvatting + run-dir.
- `run_artifact`: tmp-run-dir, pad-ontsnapping geweigerd, plafond geweigerd, geldige artifact inline.
- to_thread: event-stroom blijft levend tijdens een traag-gestubde stap (fake client met sleep; SSE-lezer krijgt step_started vóór tool_result zonder proces-blokkade).
- sessie: chain-parameter, default, 400 bij onbekende chain.
- UI: switcher-naalden (`id="chain-switcher"`, chips, `/api/chains`).
- E2E per chain over echte MCP-loopback; zware execute-stappen worden in de E2E gestub/aangestuurd via de bestaande offline-modus en geïsoleerde uitvoer (exacte strategie per chain in het plan).

## Uitbreidingspad (na v1)

`asyncio.to_thread`-patroon generaliseren naar de live (non-offline) pads; Rijnland/NSPD/minigim-chains; scenario-sweep/crosstrack als extra utrecht-stappen; SSE keep-alive voor lange stappen.
