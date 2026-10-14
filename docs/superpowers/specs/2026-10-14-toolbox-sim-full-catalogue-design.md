# toolbox-sim: volledige catalogus lokaal (design)

Datum: 2026-10-14 · Status: goedgekeurd ontwerp (deel A + B) · Opvolger van
`2026-10-04-toolbox-sim-design.md`

## Doel

Alle 20 oplossingen uit de EU LDT Toolbox solution catalogus zijn lokaal
draaibaar of gesimuleerd, zodat niets meer een k8s-cluster vereist. De
bestaande zes sim-diensten (poorten 9191–9196) blijven ongewijzigd; veertien
catalogus-oplossingen komen erbij als stub of uitbreiding, volgens het
bestaande patroon van `toolbox-sim` (FastAPI-app per oplossing,
`require_bearer`-guards, `X-Sim-Provenance` op elke response, deterministische
in-memory state uit fixtures, geen persistatie).

Gebruikersbeslissingen (2026-10-14):

1. **Scope**: volledige catalogus — inclusief de 7 algoritmmodellen en de
   UI-gaten.
2. **Datagrondslag**: echte lokale data waar die bestaat; seeded deterministische
   formules waar dat niet kan; nooit verzonnen waarden zonder herleidbaarheid.
3. **Adapters**: bestaande nldt-adapters gaan de nieuwe capabilities écht
   aanroepen, met tests; oplossingen zonder PoC-rol krijgen géén nieuwe
   adapters (te demonstreren via toolbox-sim zelf).

## Niet-doelen

- Geen echte product-UI's (Keycloak-admin, Superset, DataHub, Decidim-thema's);
  de stubs spreken de contracten, niet de UX-volle diepgang.
- Geen netwerk-lussen: subscription-notificaties en EDC-transfers worden
  deterministisch in-memory afgemaakt, niet echt afgeleverd.
- Geen zware modellen: Pollution-Propagation-klasse blijft een expliciet
  gemarkeerde placeholder op vaste rasters.

## Architectuur

Nieuwe apps in `toolbox-sim/app/`, elk met een `create_app()`-fabriek:

| Poort | App | Catalogus-oplossing |
|---|---|---|
| 9197 | `dataspace_ready.py` | EU LDT Data Space Ready (EDC-stub) |
| 9198 | `algorithms.py` | de 7 algoritmmodellen (één app) |
| 9199 | `participate.py` | EU LDT Participate (Decidim- + Jitsi-vorm) |
| 9200 | `federated_learning.py` | EU LDT Federated Learning |
| 9201 | `ai_notebook.py` | EU LDT AI Notebook |
| 9202 | `data_modeller.py` | EU LDT Data Modeller |
| 9203 | `integrated_environment.py` | EU LDT Integrated Environment |
| 9204 | `cip.py` | EU LDT City Innovation Planner |

- `server.py`: nieuwe `PORTS`-entries; `run_sim.sh --full` start 9191–9204.
  Zonder vlag blijft het huidige gedrag (9191–9196) — bestaande tests en
  gebruik ongewijzigd.
- Pure logica (modelberekeningen, state-machines) staat in gewone functies
  naast de routers, zodat UCS en tests ze zonder HTTP aanroepen.
- Elke nieuwe module krijgt contracttests in `toolbox-sim/tests/`
  (`TestClient(create_app(...))`, zelfde stijl als `test_ucs.py`).

## Uitbreiding bestaande diensten (de 4 capability-gaten)

### Data Platform (broker, :9192)

- **Subscriptions**: `POST/GET/DELETE /cb/ngsi-ld/v1/subscriptions/` —
  in-memory registry van NGSI-LD subscription-objecten (validatie op
  verplichte velden: type, entities/watchedAttributes, notification).
  Deterministische trigger `POST /cb/ngsi-ld/v1/subscriptions/{id}/notify`
  bouwt de notificatie-payload conform NGSI-LD Notification (echte entity-uit
  de broker-state) en zet die in een in-memory outbox; `GET
  /cb/ngsi-ld/v1/subscriptions/{id}/notifications` leest de outbox.
- **Temporal**: `GET /cb/ngsi-ld/v1/temporal/entities/{entityId}` met
  `timerel` (`before|after|between`), `time`, `endTime`, `time_property` —
  antwoordt met `instances[]` uit een nieuwe fixture `dp-temporal.jsonld` die
  `build_fixtures.py` genereert uit de échte lake-silver-reeksen
  (`silver/timeseries/knmi-daily-neerslag-260`, `silver/rijnland/peilen_latest`).
- **Registrations**: CRUD op `/cb/ngsi-ld/v1/registrations/` (in-memory,
  cid-manifest-vorm); GET echoït de registry.

### Play & Visualise (:9193)

- `GET /ui/map` — één zelfstandig Leaflet-HTML-antwoord (inline template,
  zelfde kaartstijl als de PoC-rapporten) dat alle geregistreerde
  dataSources/dataLayers uit de sim-state tekent: laag-toggles, popup met
  attributen bij klik, geen externe assets dan CDN Leaflet.
- Koppeling: `nldt/services/adapters/play_visualise.py` krijgt een
  `map_url()`-helper; test controleert dat elke geregistreerde laag in de
  pagina-HTML voorkomt.

### Use Cases & Scenarios (:9194)

- **Authoring**: `POST /api/v1/experiments` (kiest een recipe-sjabloon;
  fixtures/recipes/ bevat kopieën van `nldt/recipes/*.json` via
  `build_fixtures.py`), `GET /api/v1/experiments`,
  `GET /api/v1/experiments/{id}`.
- **Executie**: `POST /api/v1/experiments/{id}/trigger-process` — zelfde
  contract als het bestaande trigger-endpoint; nieuwe `process_id`s voor de 7
  algoritmmodellen worden uitgevoerd via directe aanroep van
  `app.algorithms.run_model(name, inputs)`; run-history in-memory per
  experiment.
- Adapter: `UCSAdapter` blijft werken (contract ongewijzigd);
  `nldt/services/process_adapter/handlers.py` krijgt handlers voor de 7
  model-processen.

### Data Space Ready (:9197)

EDC-connector-stub, twee vlakken:

- **Management API-vorm** (exact wat `dataspace_connector.http_register_offer`
  al post): `POST /v3/policydefinitions`, `POST /v3/assets`,
  `POST /v3/contractdefinitions` — in-memory registry, responses met `@id`.
- **Flow-vorm**: `POST /v2/catalog/request` (contract offers afgeleid uit
  `nldt/data/dataspace/offers/*.json`), `POST /v2/contractnegotiations`
  (antwoordt met status `REQUESTED`; de eerste `GET
  /v2/contractnegotiations/{id}` schakelt de state om naar `CONFIRMED` en
  elke daaropvolgende GET antwoordt `CONFIRMED` — deterministisch),
  `POST /v2/transferprocesses` (status `STARTED`; eerste `GET …/{id}` →
  `COMPLETED` met `destination`-pad naar een fixture-bestand uit de
  lake-inventaris).
- Adapter: `dataspace_connector.py` krijgt `negotiate_and_transfer()` op de
  bestaande http-backend (`NLDT_EDC_MANAGEMENT_URL` wijst naar :9197); tests
  draaien de volledige happy path (register → catalog → negotiate → transfer)
  tegen de stub.

## De 7 algoritmmodellen (:9198)

Contract per model: `GET /models/{name}` (metadata + input-schema),
`POST /models/{name}/run` (inputs → deterministisch resultaat met
`provenance`-blok: databron-pad, formule-id, seed, gegenereerd-op).
Pure functie `run_model(name, inputs) -> dict` is de enige bron van waarheid
(UCS en HTTP-router roepen dezelfde functie aan).

| Model (process_id) | Grondslag | Output |
|---|---|---|
| `neighbourhood-energy-demand` | lake-silver `knmi-daily-neerslag-260` (graaddagen-proxy) × exposure-vloeroppervlak uit de `--eubd`-fixture | kWh per tegel + totaal |
| `building-environmental-footprint` | exposure-assets per GEM-taxonomie (fixture `eubd-buildings`, echte PostGIS-herkomst) | ingebedde-carbon-proxy per taxonomie |
| `renovation-strategies` | zelfde exposure-grondslag, `attributes.legacy_2023_01`-sommen | renovatiepakket-advies per taxonomie |
| `urban-planning-vulnerability` | exposure-tegels × `peilen_latest`-peilstijging | kwetsbaarheidsindex per tegel |
| `urban-mobility` | geen lokale OD-data → seeded OD-matrix (crc32-seed over fixture-zones), expliciet `syntheticSeed` | OD-matrix + modal split |
| `pollution-propagation` | seeded dispersie-kernel op vast raster — placeholder voor het GPU-model, expliciet gemarkeerd | concentratie-raster |
| `police-routing` | seeded responstijd-raster over fixture-zones, expliciet gemarkeerd | responstijd-raster |

Zonder echte grondslag beschikbaar (geen `--eubd`, lake weg) antwoorden de
modellen `503` met een duidelijke `missing_ground`-error — nooit stille
synthetische waarden waar echte data hoort.

## De overige 6 oplossingen

- **Participate (:9199)** — Decidim-vorm: `GET/POST /api/proposals`,
  `GET /api/meetings` (seeded uit één fixture); Jitsi-vorm: `POST /rooms` →
  deterministische room-URL + meta-pagina.
- **Federated Learning (:9200)** — `POST /rounds` (ronde aanmaken),
  `POST /rounds/{id}/updates` (per-gemeente updates = deterministische
  aggregaten uit lake-data, bijv. gemiddelde peilstijging),
  `GET /rounds/{id}/result` (geaggregeerde metrics).
- **AI Notebook (:9201)** — `POST /notebooks` (sessie), `POST /pipelines/runs`
  — voert een deterministische transformatie over lake-fixtures uit
  (bijv. tellen + aggregeren) en geeft artefact-paden + metrics terug;
  `GET /pipelines/runs/{id}`.
- **Data Modeller (:9202)** — `GET/POST/DELETE /models` (LinkML-achtige
  modeldocumenten, seeded uit `nldt/schemas/`), `POST /models/{name}/validate`
  (jsonschema-validatie van een instantie-document, bevindingen terug).
- **Integrated Environment (:9203)** — `GET /solutions` (live status van álle
  sim-oplossingen), `GET /catalogue` (OGC API Records-vorm over
  `lake-inventory.json`), `GET /metrics` (Prometheus-vorm van sim-state).
- **City Innovation Planner (:9204)** — `GET/POST /scenarios`,
  `GET/POST /scenarios/{id}/contributions` (in-memory, seeded).

## Adapters en tests (nldt-kant)

- `data_platform.py`: `create_subscription`/`list_subscriptions`/
  `delete_subscription`/`trigger_notify`/`get_notifications`,
  `get_temporal_entity`, `create_registration` — met tests in
  `nldt/tests/` tegen de sim (bestaand `test_phase2_adapters.py`-patroon).
- `dataspace_connector.py`: `negotiate_and_transfer()` op de http-backend.
- `process_adapter/handlers.py`: handlers voor de 7 `process_id`s (route naar
  UCSAdapter; local fallback blijft bestaan).
- `play_visualise.py`: `map_url()`-helper + HTML-bevattingscheck.

## Documentatie en afsluiting

- `catalogue.json`: alle 20 oplossingen → `simulated` of `consumed-as-data`,
  met bewijs-paden (module + tests) en bij de algoritmmodellen de
  grondslag/seed-notitie.
- `toolbox-sim/README.md`: poorttabel 9191–9204, `--full`-documentatie.
- Addendum in `2026-10-04-toolbox-sim-design.md`: §9 non-goals (geen
  subscriptions/temporal/registrations, geen live EDC) komen te vervallen;
  resterende non-goals (geen echte UI's, geen zware modellen) blijven staan.
- Nieuwe fixtures via `build_fixtures.py`: `dp-temporal.jsonld`,
  `fixtures/recipes/`, participatie-seed; deterministisch en gecommit.

## Fasering (voor het implementatieplan)

1. Data Platform-capabilities + adapter-methoden + tests
2. Play & Visualise kaartviewer + adapter-helper + test
3. Algorithms-app (7 modellen, grondslag uit lake/PostGIS) + UCS-authoring +
   process_adapter-handlers + tests
4. Data Space Ready-stub + `negotiate_and_transfer()` + happy-path-test
5. Overige 6 oplossingen (Participate, FL, AIN, DM, IE, CIP) + tests
6. `server.py`/`run_sim.sh --full`, `catalogue.json`, README, design-addendum,
   volledige testrun

## Teststrategie

- Per nieuwe module: TestClient-contracttests (auth-guard, provenance-header,
  happy path + één foutpad, determinisme: twee keer dezelfde request →
  byte-gelijke payload).
- Adaptertests: gegen de draaiende sim (of in-process TestClient via
  asgi-transport), inclusief één negatief pad per adapter.
- E2E-smoke uitbreiden: `--full` start alles; één request per nieuwe poort
  slaagt; `catalogue.json`-test controleert 20/20 gedekt.
