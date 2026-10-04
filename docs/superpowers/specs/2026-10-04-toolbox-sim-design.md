# Ontwerp — Toolbox-sim: runnable simulatie van de PoC-relevante EU LDT Toolbox-oplossingen

| | |
|---|---|
| **Datum** | 4 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | `toolbox-sim/` (nieuw), nldt-adapters (uitsluitend env-configuratie), fixtures afgeleid van canonieke run-artefacten |
| **Buiten scope** | zie §9 Non-doelen |
| **Bronnen** | [Solutions catalogue](https://interoperable-europe.ec.europa.eu/collection/ldttoolbox/solutions-catalogue) · [`nldt/10-toolbox-integration.md`](../../../nldt/10-toolbox-integration.md) · adapters [`keycloak_auth.py`](../../../nldt/services/adapters/keycloak_auth.py) / [`data_platform.py`](../../../nldt/services/adapters/data_platform.py) / [`play_visualise.py`](../../../nldt/services/adapters/play_visualise.py) / [`process_adapter/router.py`](../../../nldt/services/process_adapter/router.py) / [`marketplace_publish.py`](../../../nldt/services/marketplace_publish.py) · [`ldtsolutions/MINIKUBE_ENV_PLAN.md`](../../../ldtsolutions/MINIKUBE_ENV_PLAN.md) · [fase-1 NGSI-LD-ontwerp](2026-09-30-ngsi-ld-integration-design.md) · [`a2a-simulation/README.md`](../../../a2a-simulation/README.md) |

## Context en doel

De catalogus telt 20 oplossingen (12 tools + 8 algoritmemodellen). Volledig echt
draaien kost ≈ 104 vCPU / 242 GB (`ldtsolutions/MINIKUBE_ENV_PLAN.md`); op deze
Mac draaien er twee echt (IM, P&V) en is UCS afgebroken-maar-herstelbaar. De
nldt-adapters hebben vijf toolbox-oplossingen al aangesloten (mock-default), en
de EU Building Database wordt al als echte data geconsumeerd (PostGIS
`exposure`-slice).

Twee keuzes uit de brainstormsessie bepalen dit ontwerp:

1. **Vorm: runnable eindpuntsimulatie.** Eén lichtgewicht lokaal proces dat
   instaat voor de PoC-relevante oplossingen en **exact de HTTP-interfaces
   spreekt die de bestaande adapters al aanroepen** — de toolbox-tegenhanger
   van `a2a-simulation/` (dat de PoC-kant van de mesh simuleert). De
   integratielijn (HTTP, OIDC, tenants) wordt echt belopen; de tools zelf
   worden niet nagebouwd.
2. **Scope: evidence-set.** Alleen oplossingen met hard bewijs van PoC-gebruik
   vandaag: IM, P&V, UCS, Data Platform, Marketplace + EU Building Database.
   Alles anders wordt in het catalogusmanifest geregistreerd als *skipped*
   met reden.

Doctrine ongewijzigd: **geen verzonnen getallen** — elke waarde in de sim is
afgeleid van een canoniek run-artefact en draagt herkomst (run-id + sha256).

## Catalogusmanifest — `toolbox-sim/catalogue.json`

Het manifest is het letterlijke antwoord op *"for zolang ze betekenis hebben in
de PoCs"*: alle 20 catalogusoplossingen, elk met `status`, bewijs en/of reden.

| Oplossing | Status | Bewijs / reden |
|---|---|---|
| Identity Management | `simulated` (echte draait ook op k8s, `im.ldt.local`) | `keycloak_auth.py`, realm LDT |
| Data Platform | `simulated` | `data_platform.py` (broker + UCS-proxy + Trino) |
| Play & Visualise | `simulated` (echte draait ook op k8s, `pv.ldt.local`) | `play_visualise.py` (dataSources/dataLayers) |
| Use Cases & Scenarios | `simulated` | `router.py::UCSAdapter` (`trigger-process`) |
| Marketplace | `simulated` | `marketplace_publish.py` (assets + publish) |
| EU Building Database | `consumed-as-data` | PostGIS `exposure`-slice; sim ontsluit hem als entiteitsfeed (§4.6) |
| Integrated Environment | `skipped` | nLDT is zijn eigen voordeur (OGC Records/Processes/Recipes); IE-portaal/asset-registry heeft geen PoC-functie |
| AI Notebook | `skipped` | lokale open modellen (Ollama) bedienen al de propose-benen S1/S2/S7/S8; AIN-stack is zwaar en Linux-only |
| City Innovation Planner | `skipped` | co-creatietool zonder PoC-rol |
| Data Modeller | `skipped` | eigen `@context` + shapes (fase-1 NGSI-LD) dekken de behoefte |
| Data Space Ready | `skipped` | buiten evidence-set deze snede; nldt/13 (EDC/ODRL) dekt het pad |
| Federated Learning | `skipped` | geen PoC-rol |
| Participate | `skipped` | V4/eParticipatie is toekomstspoor, geen adapter |
| Urban Mobility · Pollution Propagation · Renovation Strategies · Vulnerability Mitigation · Police Routing | `skipped` | geen PoC-rol |
| Neighbourhood Energy Demand Forecasting | `skipped` | geen PoC-rol *vandaag*; eerste uitbreidingskandidaat zodra de Utrecht-congestietrack (art. 5.10/5.11) start |

## Architectuur

```text
toolbox-sim/
  README.md
  catalogue.json           manifest: 20 oplossingen → status + bewijs/reden
  requirements.txt         fastapi, uvicorn, httpx (spiegelt nldt-stack)
  run_sim.sh               start alle poorten; --eubd optioneel (PostGIS nodig)
  .env.sim                 adapterconfiguratie: alle nldt-mocks uit, URL's op sim
  build_fixtures.py        canonieke runs → fixture-batches (deterministisch)
  fixtures/                gegenereerd en gecommit: entiteitsbatches, tabellen
  app/
    server.py              multi-port-opstart (asyncio, per oplossing één uvicorn)
    identity.py            IM / OIDC-tokenendpoint
    data_platform.py       NGSI-LD-broker + UCS-proxyvariant + Trino-stub
    play_visualise.py      dataSources / dataLayers
    ucs.py                 trigger-process (replay uit canonieke run)
    marketplace.py         assets-upload + publish + cataloguslijst
    provenance.py          herkomststempels (run-id, sha256) op elk antwoord
  tests/
    test_contracts.py      adapter-aanroepvormen per oplossing
    test_e2e_smoke.py      sim op → recept + hybrid bridge → registraties
```

**Poorten** (vrij ten opzichte van de A2A-mesh 9181–9186 en UI 9190):

| Poort | Oplossing |
|---|---|
| 9191 | Identity Management (OIDC) |
| 9192 | Data Platform — NGSI-LD-broker |
| 9193 | Play & Visualise |
| 9194 | Use Cases & Scenarios |
| 9195 | Marketplace Agent |
| 9196 | EU Building Database-feed (broker-semantiek, tenant `eubd`) |

`.env.sim`-fragment (verzoekt de adapters met `MOCK=false` naar de sim te
schakelen):

```bash
KEYCLOAK_URL=http://127.0.0.1:9191
KEYCLOAK_REALM=LDT
KEYCLOAK_CLIENT_ID=nldt-agent
KEYCLOAK_CLIENT_SECRET=sim-dev-secret
NLDT_NGSI_LD_URL=http://127.0.0.1:9192
NLDT_DATA_PLATFORM_MOCK=false
NLDT_PV_BASE_URL=http://127.0.0.1:9193
NLDT_PV_MOCK=false
UCS_BASE_URL=http://127.0.0.1:9194
UCS_TOKEN=sim-toolbox-token
MARKETPLACE_AGENT_URL=http://127.0.0.1:9195
MARKETPLACE_TOKEN=sim-toolbox-token
MARKETPLACE_MOCK=false
```

## Endpointcontracten

**Contract of record is de adaptercode.** De sim implementeert precies de
aanroepen die §Bronnen-adapters vandaag doen — geen extra eindpunten, geen
afwijkende enveloppen. Wijzigt een adapter, dan is dat de trigger om de sim en
zijn contracttests mee te wijzigen.

### Identity Management (9191)

- `POST /realms/LDT/protocol/openid-connect/token` — form-encoded
  `grant_type=client_credentials&client_id&client_secret` →
  `{"access_token", "expires_in", "token_type": "Bearer"}`.
- Token: HS256-JWT met vaste dev-ongeheim; payload bevat de `groups`-claims
  (`/context-data/<scope>/<role>`, `/data-query/<scope>/<role>`) die
  `data_platform.list_scopes()` decodeert.
- Onbekende client/geheim → `401 invalid_client` — fail-closed, zoals echt
  Keycloak. Bekende clients staan in `fixtures/clients.json`.

### Data Platform (9192)

- Brokermodus: `GET /ngsi-ld/v1/entities?type=&limit=`,
  `GET /ngsi-ld/v1/entities/{id}`, `POST /ngsi-ld/v1/entityOperations/upsert`;
  header `NGSILD-Tenant` gerespecteerd. De broker op 9192 serveert uitsluitend
  de run-batches (default-tenant); gebouwentiteiten leven alleen achter hun
  eigen deur op 9196 (§4.6) — zoals de echte EUBD een standalone database is.
- UCS-proxyvariant: `GET /api/v1/data-platform/entities?scope=&type=&limit=`
  en `GET /api/v1/data-platform/entities/{id}` met `{"data": …}`-envelop.
- Trino-stub: `POST /v1/statement` met `X-Trino-User/-Catalog/-Schema`, met
  `nextUri`-paging, over read-only fixturetabellen (per catalogus/schema een
  JSON-tabel in `fixtures/trino/`); schrijfacties → `403`.

### Play & Visualise (9193)

- `POST /api/dataSources` met payload-vorm
  `{name, sourceConfiguration:{type:"EXTERNAL",url,headers}, securityConfiguration:{…}}`
  → `{id, name, …}`.
- `POST /api/dataLayers` met `{name, dataSource, type:"SCENARIO", configuration}`
  → `{id, name, dataSource, …}`.
- Sessie-persistente ids; `GET /api/dataLayers/{id}` terugleesbaar.

### Use Cases & Scenarios (9194)

- `POST /api/v1/experiments/trigger-process` met `{processId, inputs}` →
  `{outputs: …}`: **replay** van de outputs van de canonieke run die bij dat
  proces hoort (mapping in `fixtures/ucs-processes.json`), gestempeld
  `sim-replay://canonical/<run-id>`.
- Onbekend `processId` → `404`, zodat `UCSAdapter` net als echt op de
  local-fallback valt.

### Marketplace (9195)

- `POST /api/v1/agent/assets` (multipart `file`) → `{id}`.
- `POST /api/v1/agent/assets/{id}/publish` met
  `{name, description, categories, licence}` → antwoord met
  `publishState.offering_id` (deterministisch: `sim-offering-<asset-id>`).
- `GET /api/v1/agent/assets` — cataloguslijst van geüploade assets.

### EU Building Database (9196)

- Broker-semantiek (`GET /ngsi-ld/v1/entities?type=Building`, tenant `eubd`)
  over entiteiten afgeleid van de echte PostGIS `exposure`-slice door
  `build_fixtures.py`. Is de database onbereikbaar, dan faalt de builder
  **hard** — geen verzonnen gebouwen. De feed is optioneel (`run_sim.sh
  --eubd`); zonder hem draaien de andere vijf gewoon.

## Fixtures en herkomst

`build_fixtures.py` leest de canonieke runs — eerste snede
`poc/runs/20260830T113234Z-wind` (+zon/bos) en
`poc-bp2op/runs/20260830-124515-eindhoven`, dezelfde scope als het fase-1
NGSI-LD-ontwerp — en zet artefacten om naar entiteitsbatches volgens het
fase-1 entiteitenmodel (`ldt:OpportunityZone`, `ldt:FormalRule`,
`ldt:NormCard`, `ldt:PipelineRun`; `urn:ldt:<track>:<type>:<bron-id>`). Zo
convergeren sim en het toekomstige `ngsi-ld-export`-proces: valt fase 1, dan
schakelt de fixture-builder over op diens output als bron.

Elke fixture noteert bron-run-id + sha256 per bronartefact; elk HTTP-antwoord
draagt een `X-Sim-Provenance`-header (oplossing + fixture + run-id); hergeneratie
is byte-identiek (deterministische veldvolgorde, gesorteerde entiteits-ids).

## Autorisatiemodel

- Alleen de sim-IM mint tokens (dev-geheim, uitsluitend localhost-verkeer).
- DP/P&V/UCS/Marketplace-eindpunten verlangen `Authorization: Bearer` van een
  geldig sim-token; ongeldig/verlopen → `401`.
- Compatibel met de mesh: het statische token uit `a2a-simulation`
  (`NLDT_STATIC_TOKENS`, `sim-toolbox-token`) wordt als extra geaccepteerde
  principal geregistreerd — `UCS_TOKEN` en `MARKETPLACE_TOKEN` in `.env.sim`
  dragen precies dat token, omdat die adapters een statische bearer sturen in
  plaats van een client-credentials-flow.

## Foutafhandeling

Fail-loud, nooit stilletjes mocken: onbekende client → 401; onbekende
entiteit → 404; onbekend proces → 404 (local fallback is adapterside);
schrijvend SQL → 403; PostGIS onbereikbaar → builder faalt met reden;
ontbrekende fixture → opstart weigert. Elke afwijking komt in het antwoord of
het log met de herkomst van wat wél geserveerd werd.

## Tests en verificatie

1. `test_contracts.py` — per oplossing: de exacte aanroepvorm van de adapter
   (pad, headers, envelop, foutcodes), inclusief `groups`-claim-decodering en
   `NGSILD-Tenant`-filtering.
2. Bestaande `nldt/tests/test_phase2_adapters.py` draait tegen de sim
   (`.env.sim` geladen) in plaats van tegen de in-process mocks.
3. `test_e2e_smoke.py` — sim op → recept uitvoeren met hybrid bridge →
   assert: DP-entiteit opvraagbaar, P&V-dataLayer geregistreerd,
   Marketplace-offering gepubliceerd; alles offline.
4. Fixturedeterminisme: hergeneratie byte-identiek; herkomststempels aanwezig.
5. Bestaande suites (nldt, poc, poc-bp2op, a2a-simulation) blijven onaangetast.

## Fasering

| Fase | Inhoud | Clausule |
|---|---|---|
| 0 | skelet, `catalogue.json`, README, IM-tokenendpoint + contracttests | mergebaar zonder de rest |
| 1 | DP-broker + fixtures Utrecht/Eindhoven + adaptertests tegen sim | |
| 2 | P&V + UCS | |
| 3 | Marketplace + EUBD-feed + e2e-smoke | volledig verhaal offline |
| 4 (optioneel) | verwijzing vanaf `nldt/10-toolbox-integration.md` en de `nldt/simulation`-hub | goedkoop zodra manifest er is |

## Non-doelen

- Geen Kubernetes en geen echte tool-images (dat blijft `ldtsolutions/`).
- Geen echte UI's (P&V-frontend e.d. draaien echt op het cluster of niet).
- Geen NGSI-LD-subscriptions/temporal/registrations — batch + query is de opgave.
- Geen DSR/EDC (nldt/13), geen visuele demopagina (manifest maakt die later
  goedkoop).
- Geen mutatie van PoC-pipelines, corpora of nldt-adapterlogica — alleen
  env-configuratie.

## Risico's

| Risico | Beheersing |
|---|---|
| Interfacedrift t.o.v. de echte toolbox | adaptercode is contract of record; contracttests pinnen de vorm; live `ldttoolbox.app`-env blijft om-schakelbaar |
| Duplicatie met fase-1 NGSI-LD-export | zelfde entiteitenmodel/URI-schema; overschakeling op diens output zodra geïmplementeerd |
| Dev-JWT geeft schijn van veiligheid | duidelijke `sim`-claims + `X-Sim-Provenance`; nergens productie-traffic; geheim alleen lokaal |
| Poort-/procesconflicten met mesh en nldt-diensten | vaste tabel 9191–9196, gedocumenteerd in README naast de bestaande allocaties |
| Fixturegrootte (gebouwen) | EUBD-feed optioneel en aparte poort/tenant; run-batches blijven klein |
| Parallelle agent-sessies in de hoofdwerkmap | uitvoering in geïsoleerde git-worktree op eigen branch (patroon van de NGSI-LD-snede) |
