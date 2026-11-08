# Ontwerp — DSO-kennisbank via MCP voor toekomstige agents

| | |
|---|---|
| **Datum** | 2026-11-07 |
| **Status** | goedgekeurd ontwerp (aanpak 2: process-façade) |
| **Scope** | de DSO-kennisbank (`nldt/simulation/regelrecht/dso_overlap/out/` + `full_export/` + `tpod/`) ontsluiten via MCP; overige engines (RegelRecht-punttoets als losse engine, Gent, Veenendaal, bp2op-conversie) volgen in een tweede golf |
| **Aansluiting** | [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE](../../POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) · [nldt/05-agentic-ai-layer](../../../nldt/05-agentic-ai-layer.md) · [nldt/12-governed-agent-layer](../../../nldt/12-governed-agent-layer.md) · [GENAI_SEAMS](../../GENAI_SEAMS.md) |
| **Doctrine** | AI stelt voor · engine beslist · mens bevestigt — deze dienst is pure retrieval + deterministische toets; géén LLM in de dienst zelf |

---

## 1. Doel en niet-doelen

**Doel.** Toekomstige agents (deep-agents-orchestrator, externe MCP-clients) laten werken met de DSO-kennisbank zonder ooit DSO-keys, ruwe megabyte-responsies of bestandspaden te zien. Elke bevraging loopt door de process-adapter (jobId + status + prov) en leest uit de gecachte, sha256-gepinde kennisbank; exact één proces mag live naar PRE verversen, met de keys server-side in `.env`.

**Niet-doelen.** Geen LLM- of RAG-laag over de regelteksten (retrieval zonder cite-or-abstain is expliciet ongewenst); geen RegelRecht-engine-executie op vrije inputs (de punttoets draait alléén op de gecachte fixture-punten; engine-ontsluiting is tweede golf); geen registratie-mutaties door agents (nieuwe locaties/instrumenten blijven een menselijke stap via `fixtures/locations.json` en `instruments.py`); geen herschrijving van de bestaande compare/tpod-keten.

## 2. Genomen besluiten

1. **Scope**: DSO-kennisbank eerst (gebruikerskeuze). Bestaande servers op :8090–8093 blijven ongewijzigd.
2. **Bronbeleid**: cache-first; één expliciet refresh-proces mag live (gebruikerskeuze). Keys blijven server-side.
3. **Bouwvariant**: aanpak 2 — OGC-Processes achter een MCP-façade (gebruikerskeuze, afwijkend van de aanbevolen variant 1). Motivatie: uniformiteit met het poc-patroon, jobId/status/prov per bevraging, en hergebruik vanuit recipes zonder herbouw.
4. **Drift-uitslag is een eersterangs-uitvoer**: de refresh verrast de ruwe sha-vergelijking (datumecho's + volgorde ruisen) door een canonieke vergelijking, gebakken uit de drift-analyse van 7 november 2026 (nul inhoudelijke drift tussen 20-10 en 07-11, alle byte-verschillen verklaard door `geldigOp`/`inWerkingOp`/`beschikbaarOp`-echo's en lijstvolgorde).

## 3. Architectuur

```
toekomstige agents ──MCP :8094 (streamable-http, bearer)──▶ nldt-dso-mcp (dso_server.py, façade)
                                                                  │ OGC-Processes-executie
                                                                  │ (NLDT_OFFLINE=1 → lokale job-store)
                                                                  ▼
                                              process_adapter — 9 nieuwe processen (dso_handlers.py)
                                                                  │
                                              services/dso_kb.py — pure lees- en refresh-logica
                                                                  │ leest / schrijft (alléén refresh)
                                              nldt/simulation/regelrecht/dso_overlap/out/ + full_export/
```

- **`nldt/services/dso_kb.py`** — pure functies: instrumenten/locaties resolven (hergebruik `dso_overlap/instruments.py`), artefacten lezen, filteren, begrenzen; `refresh()` importeert en roept `dso_overlap.compare.compare_instrument()` en de tpod-herbouw in-process aan; `canonieke_drift()` vergelijkt oud↔nieuw. Alle functies nemen paden injecteerbaar (`out_dir`-parameter) — het `poc_readops.py`-testpatroon.
- **`nldt/services/process_adapter/dso_handlers.py`** — negen procesdefinities (`id`, titel, inputs, outputs, `sideEffect`) + execute-functies die `dso_kb` aanroepen; registratie in het procesregister naar het patroon van `poc_handlers.py` (definitie-blok + handler-map).
- **`nldt/services/mcp_servers/dso_tools.py`** — `DSO_TOOLS`: toolnaam → `process_id` + beschrijving (gedeeld met tests; `poc_tools.py`-patroon).
- **`nldt/services/mcp_servers/dso_server.py`** — `nldt-dso-mcp`, `@mcp.tool()` per tool, façade-executie via `PROCESS_URL` (of lokale job-store bij `NLDT_OFFLINE=1`), `NLDT_MCP_TRANSPORT=streamable-http` → poort **8094**, zelfde bearer/auth (`headers.py`) als de zusterservers.
- **Registratie/docs**: `deep-agents/mcp_client.py` (`"nldt-dso": :8094/mcp`), `nldt/05-agentic-ai-layer.md`, `nldt/00-architecture.md` (poortbereik 8090–8093 → 8094).

## 4. Processen en tools (1:1 gespiegeld)

| Proces (tool) | Inputs | Uitvoer | Side-effect |
|---|---|---|---|
| `dso-kb-overview` (`dso_kb_overview`) | — | instrumenten × locaties, freshness (`fetchedAt`, sha256-16), dekkingscijfers, aanwezige artefacten per paar | nee |
| `dso-kb-annotations` (`dso_kb_annotations`) | `instrument`, `locatie?`, `artikel?`, `detail?` (default samenvatting) | per artikel: wId, regeltekst-samenvatting, activiteiten, gebieden, locatieRefs; counts | nee |
| `dso-kb-document-structure` (`dso_kb_document_structure`) | `instrument`, `wIdPrefix?`, `maxItems?` (default 100) | vlakke componentreeks (soort, wId, titel, diepte) | nee |
| `dso-kb-tpod` (`dso_kb_tpod`) | `instrument`, `locatie?` | wId-anchoring, geoFeiten, activiteiten, gebiedsaanwijzingen, pons-status | nee |
| `dso-kb-toets` (`dso_kb_toets`) | `instrument`, `locatie?`, `artikel?` | punttoets-uitkomsten: feit/afwezigheid/scenario/onthouding per `execution.input` | nee |
| `dso-kb-overlap` (`dso_kb_overlap`) | `instrument`, `locatie?`, `status?`, `pagina?` (100/pagina) | coverage + per-artikel statusrijen | nee |
| `dso-kb-gios` (`dso_kb_gios`) | `instrument`, `identificatie?` | GIO-inventaris uit het officiële uitwisselpakket (identificatie, gmlBestand, sha) | nee |
| `dso-kb-point-in-gio` (`dso_kb_point_in_gio`) | `instrument`, `x`, `y` (EPSG:28992), `identificatie?` | punt-in-polygoon per GIO (hergebruik `tpod/geo.py`); zonder `identificatie` alle GIO's | nee |
| `dso-kb-refresh` (`dso_kb_refresh`) | `instrument`, `locatie?`, `metTpod?` (default ja: herbouwt tpod-index, toets én geo-validatie) | oude/nieuwe sha's, **canonieke drift-uitslag**, verse dekkingscijfers | **ja** — schrijft alléén naar `dso_overlap/out/` (gitignored) |

Antwoordvorm per MCP-tool conform poc-server: `{tool, processId, jobId, status, outputs, prov}`.

## 5. Canonieke drift-uitslag (specificatie)

Vóór vergelijking worden beide responses genormaliseerd: alle lijsten recursief sorteren; uit HAL-hrefs de parameters `geldigOp`, `inWerkingOp`, `beschikbaarOp` verwijderen. Daarna per categorie vergelijken en rapporteren:

- **regelteksten**: wId-set (+ Nieuw/vervallen wIds expliciet);
- **regelsVoorIedereen / instructieregels**: per identificatie de multiset `(activiteitRef, locatieRefs, symboolcode)`;
- **locaties / gebiedsaanwijzingen**: per identificatie het volledig genormaliseerde record;
- **documentstructuur**: de vlakke componentreeks `(soort, wId, titel)` in documentvolgorde;
- **GIO's**: per bestandsnaam de sha256 uit de pakket-index.

Uitvoer: `"inhoudelijkeDrift": "geen"` óf een lijst gewijzigde wIds/identificaties per categorie. Byte-sha's blijven ernaast gerapporteerd (als bewijs van verversing), maar zijn géén drift-signaal.

## 6. Bronbeleid en security

- DSO_API_KEY / RP_API_KEY blijven in de gitignored `.env`; alléén `dso_kb.refresh()` leest ze (via het bestaande `dso_overlap/client.py`); geen enkele tool-uitvoer bevat keys of volledige headers.
- Bearer-authenticatie identiek aan :8090–8093 (`NLDT_MCP_BEARER_TOKEN` / wallet-bearer via `headers.py`).
- `NLDT_OFFLINE=1`: alle leesprocessen werken gewoon (cache), `dso-kb-refresh` weigert met uitleg (poc-server-conventie).
- Nieuwe locaties/instrumenten: bewuste menselijke stap buiten MCP (`fixtures/locations.json`, `instruments.py`); het refresh-proces valideert dat de gevraagde combinatie bestaat.
- Uitvoerbegrenzing: default max 100 rijen, hard maximum 500; vervolg via `pagina`/filters; de ruwe annotatie-respons (≥1,6 MB) komt nooit ongefilterd door.

## 7. Foutafhandeling

| Geval | Gedrag |
|---|---|
| onbekend `instrument`/`locatie` | fout mét de geldige lijst |
| artefact ontbreekt in cache | fout + verwijzing naar `dso-kb-refresh` (of de CLI) |
| DSO/RP HTTP-fout tijdens refresh | vertaalde fout: status + url; géén body-lek; cache blijft ongewijzigd (schrijven pas na succesvolle fetch) |
| uitvoer boven begrenzing | afgekapt + `volgendePagina`-verwijzing |

## 8. Testing

1. **Unit `dso_kb`**: fixture-subset van de echte cache (klein, in-repo, gesneden uit de huidige out/ — incl. één oud/nieuw-paar voor de drift-test); pad-injectie, geen netwerk.
2. **Drift-test**: op het fixturepaar moet de canonieke vergelijking "geen" zeggen ondanks verschillende byte-sha's; op een gemanipuleerd paar (één gewijzigde activiteitRef) moet precies dat ene wId worden gerapporteerd.
3. **Proces-contract**: alle negen definities geregistreerd, inputs/outputs-schema consistent, handlers draaien offline.
4. **Façade**: `DSO_TOOLS` ↔ procesdefinities ↔ tool-handlers consistent (naar bestaande poc-server-tests).
5. **Offline-refresh**: `NLDT_OFFLINE=1` → refresh weigert, leesprocessen slagen.
6. **Smoke (optioneel, gemarkeerd netwerk)**: server op :8094, één tool-aanroep, jobId geverifieerd.

## 9. Bouwvolgorde

1. `services/dso_kb.py` + unit-tests (incl. drift-fixtures)
2. `process_adapter/dso_handlers.py` + registratie + contract-tests
3. `mcp_servers/dso_tools.py` + `dso_server.py` + façade-tests
4. deep-agents-registratie + docs (`nldt/05`, `nldt/00`, deep-agents README-vermelding)
5. end-to-end-smoke en verversen van de runbook-verwijzingen (offline commando's blijven ongewijzigd werken)

## 10. Toekomst (buiten scope, tweede golf)

RegelRecht-engine-executie als eigen proces (toets op vrije feiten achter de bestaande gates); Gent-/Veenendaal-/bp2op-onderdelen achter dezelfde façade; GIO-symdiff-validatie van de agrest-mirror als proces; publicatie van de tools als Agent Skills op de server (SEP-2640-patroon van poc-mcp).

---

## Errata / versmallingen na uitvoering (2026-11-08)

Tijdens de uitvoering (plan `docs/superpowers/plans/2026-11-07-dso-kb-mcp.md`) zijn vier afwijkingen van deze spec bewust gerealiseerd:

1. **§3 refresh draait via subprocess**, niet in-process: betere isolatie en `.env`-afhandeling door de bestaande CLI's; functiecontract ongewijzigd.
2. **§5 drift rapporteert vier categorieën** (regelteksten, regels, locaties, gebiedsaanwijzingen); documentstructuur en GIO-sha's zijn bewust níét meegenomen — de annotatie-respons is de drift-drager.
3. **§7 refresh-foutcontract is pragmatisch**: een mislukte compare kan de cache deels hebben vernieuwd (de CLI's schrijven per artefact); de fout verschijnt als stderr-staart in het fout-resultaat. "Cache ongewijzigd bij fout" geldt alléén voor de fetch-zelf-mislukt-fase vóór schrijven.
4. **§4 uitvoerdetails zijn smaller** per tool (geen regeltekst-samenvatting/locatieRefs per artikel in annotations-detail; geen fetchedAt in overview) — de cache-meta's blijven via sha's beschikbaar.
