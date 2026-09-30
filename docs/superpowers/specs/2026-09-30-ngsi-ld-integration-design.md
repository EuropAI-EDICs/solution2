# Ontwerp — NGSI-LD-integratie in de LDT-toolbox (fase 1: Utrecht + Eindhoven)

| | |
|---|---|
| **Datum** | 30 september 2026 |
| **Status** | goedgekeurd in brainstormsessing; wacht op review van dit document |
| **Scope** | `nldt/services/ngsild/` (nieuw), OGC-proces + recept in `nldt`, exports van de canonieke runs van PoC-1 (Utrecht) en PoC-2 (Eindhoven) |
| **Bronnen** | [ngsi-ld.org](https://ngsi-ld.org/) (ETSI GS CIM 009/006, API 1.8.1) · [nldt/02-reference-architecture.md](../../../nldt/02-reference-architecture.md) · [nldt/edic/ra-conformity.md](../../../nldt/edic/ra-conformity.md) · [POC_RULE_GRAPH.md](../../../docs/POC_RULE_GRAPH.md) · [POC_RULE_GRAPH_EINDHOVEN.md](../../../docs/POC_RULE_GRAPH_EINDHOVEN.md) |

## Context en doel

De nldt-referentiearchitectuur en de EDIC-conformiteitsclaim noemen NGSI-LD
(ETSI GS CIM 009/006) als open interface voor contextinformatie — maar geen
enkele PoC spreekt het vandaag. Dit ontwerp sluit die kloof met een
**toolbox-brede adapter** (keuze C uit de sessie): één OGC-proces dat
PoC-run-artefacten omzet naar NGSI-LD-entiteiten, zodat elke track (nu
Utrecht en Eindhoven; later Breda en Rijnland via hetzelfde recept) zijn
uitvoer als linked-data-graaf kan publiceren. De validatie is
**offline-first** (keuze: JSON-LD-geldigheid + shapes + round-trip, altijd
in de suite) met een **optionele broker-e2e** die alleen draait als Docker
beschikbaar is (keuze uit de sessie).

## Architectuur

```text
nldt/
  recipes/ngsi-ld-export.json           recept (backend: local)
  services/process_adapter/handlers.py  + DESCRIBE/execute van "ngsi-ld-export"
  services/ngsild/
    __init__.py                         public API: export_run(track, run_dir, out_dir)
    context.py                          context.jsonld (ldt:-termen) + urn-namescheme + URL's
    context.jsonld                      het eigen @context (gecommit)
    etsi-core-context.jsonld            vastgepinde kopie ETSI-core-context (gecommit)
    utrecht.py                          run-artefacten → entiteiten
    eindhoven.py                        run-artefacten → entiteiten
    validate.py                         pyld-expansie (offline loader) + shape-checks + round-trip
    shapes/                             entity-shapes (draft 2020-12, per type één bestand)
    docker-compose.yml                  Scorpio all-in-one (uitsluitend voor de e2e)
```

Het OGC-proces `ngsi-ld-export` heeft inputs `runDir` (bestaande run-map),
`track` (`utrecht`|`eindhoven`) en `outDir`; output het batchbestand en een
klein exportrapport. Aanroepbaar via de bestaande CLI (`python -m
services.cli`, cwd = nldt-root) en via het recept met `LocalClient`
(process_client-override, bestaand testpatroon).

## Het entiteitenmodel

Eén eigen JSON-LD-context met de `ldt:`-namespace (Smart Data Models-stijl),
gecommit als `context.jsonld` met canonieke URL
`https://ldttoolbox.local/ngsi-ld/context.jsonld` (hosting op een echte URL
is expliciet vervolgwerk, geen onderdeel van deze snede). Entiteiten
gebruiken `@context: [<eigen context>, <ETSI-core-context>]`. URI-scheme:
`urn:ldt:<track>:<type>:<bron-id>` (bijv. `urn:ldt:utrecht:zone:ZR-final`,
`urn:ldt:eindhoven:row:OT-001`) — afleidbaar, stabiel, deterministisch.

**Utrecht — de bestaande traceerketen wordt de graaf:**

| entiteittype | bronartefact | kernvelden | relaties |
|---|---|---|---|
| `ldt:OpportunityZone` | `zones.json` (per ZoneResult) | `location` (GeoJSON WGS84), `areaKm2`, `operation` (letterlijk uit artefact), `ldt:zoneRole` (afgeleid uit de zone-id: `final` / `inclusion` / `exclusion` / `marker`) | `ldt:derivedFromRule` → FormalRule; `ldt:generatedBy` → PipelineRun |
| `ldt:FormalRule` | `formalrules.json` | `ruleType`, `zoneSemantics`, `status` | `ldt:groundedIn` → NormCard |
| `ldt:NormCard` | `normcards-wind.json` | `article`, `quote` (letterlijk), `legalForce`, `theme` | `ldt:cites` → CVDR-artikel-URI |
| `ldt:PipelineRun` | `run_summary.json` | `runId`, `verdict`, `generatedAt` | — (anker) |

Geen zwevende randen: elk `ruleId` op een zone moet naar een FormalRule
wijzen die in de batch zit, elke FormalRule naar zijn NormCard, elke NormCard
naar de CVDR-uri uit het artefact.

**Eindhoven — de conversiegraaf:**

| entiteittype | bronartefact | kernvelden | relaties |
|---|---|---|---|
| `ldt:ConversionRow` | `omzettabel.json` (per rij) | `status` (enum zonder `gekoppeld`), `needsHumanReden` | `ldt:hasBronRegel` → BronRegel; `ldt:suggestsDoelRegel` → DoelRegel; `ldt:basedOnKennisbank` → KennisbankRelatie (indien hit) |
| `ldt:BronRegel` | `bronregels.json` | `locator` (hoofdstuk/artikel), `permalink`, `statusInBron` | `ldt:partOfInstrument` → omgevingsplan-URI |
| `ldt:DoelRegel` | `doelregels.json` | idem | idem |
| `ldt:KennisbankRelatie` | `kennisbank.json` | `relationType` (bijv. `vervangt`), `source` (GMB-publicatie) | — |

De matchscore komt als property `ldt:score` op de relatie-instantie
`ldt:suggestsDoelRegel` (properties op relationships zijn toegestaan in het
NGSI-LD-informatiemodel, ETSI GS CIM 006).

## Validatie — drie lagen, offline eerst

1. **JSON-LD-geldigheid**: expansie én compaction met `pyld` (nieuwe
   dependency in `nldt/requirements.txt`; pure Python) via een offline
   document-loader die de canonieke URL's van het eigen context en de
   ETSI-core-context serveert uit de commit-cache — geen netwerk nodig.
2. **Entity-shapes**: één jsonschema-contract (draft 2020-12,
   `additionalProperties: false`, naar het patroon van `nldt/schemas/`) per
   entiteittype; afgedwongen in het proces (fail-loud) én in de tests.
3. **Round-trip**: batch exporteren → opnieuw inlezen → identieke graaf
   (aantallen entiteiten per type, alle uri's, alle relatieparen).

Canoniek bewijs: de exports van beide canonieke runs
(`poc/runs/20260830T113234Z-wind` en
`poc-bp2op/runs/20260830-124515-eindhoven`) worden gegenereerd en
gecommit onder `nldt/ngsi-ld/` (volgende sectie).

## Uitvoer en artefacten

- `nldt/ngsi-ld/utrecht-wind-20260830.jsonld` en
  `nldt/ngsi-ld/eindhoven-bp2op-20260830.jsonld` — genormaliseerde
  NGSI-LD-entiteitenbatches, gesorteerd op entiteit-id, byte-identiek
  hergenereerbaar (deterministische veldvolgorde).
- `nldt/ngsi-ld/<track>-…-export-report.json` — aantallen per type,
  validatieresultaat per laag, sha256 van elk bronartefact.
- Documentatie: paragraaf in `nldt/10-toolbox-integration.md` (aansluiten
  bij de bestaande NGSI-LD-vermeldingen) en een regel in beide PoC-README's
  onder de artefactenlijst.

## Foutafhandeling

Het proces faalt hard (exit ≠ 0) met een rapport met reden bij: ontbrekend
artefact; artefact dat niet valideert tegen zijn PoC-contract (her-check
binnen de adapter); mislukte JSON-LD-expansie; shape-overtreding;
niet-herleidbare verwijzing (zwevende rand); round-trip-afwijking. De
adapter leest uitsluitend — mutatie van PoC-pipelines of corpora is
uitgesloten.

## Optionele broker-e2e (docker-gated)

`docker-compose.yml` start Scorpio all-in-one (één container met Postgres;
image-tag bij implementatie vastgepind). De e2e (`nldt/tests/`, unittest):
(0) daemon-check `docker info` — niet bereikbaar ⇒ **skip** met melding,
nooit fail; (1) compose up + health-wait; (2) batch-UPSERT van de Utrecht-
batch naar `/ngsi-ld/v1/entityOperations/upsert`; (3) GET per id voor een
steekproef entiteit; (4) GET by type `ldt:OpportunityZone`; (5)
verificatie dat de `derivedFromRule`-ids van de opgehaalde zone overeenkomen
met het batchbestand; (6) compose down. Geen live broker in de normale
suites.

## Tests

`nldt/tests/test_ngsild.py`:

1. shape-tests per entiteittype (geldig voorbeeld + afgewezen voorbeeld,
   incl. de enum-zonder-`gekoppeld` op `ldt:ConversionRow.status`);
2. export van beide canonieke runs: aantallen per type afgeleid uit de
   bronartefacten zelf (zones conform `zones.json`; 24 NormCards;
   24 FormalRules; 311 ConversionRows), unieke urn's, deterministische
   her-generatie byte-identiek;
3. offline JSON-LD-expansie/compaction van beide batches;
4. round-trip-identiteit per batch;
5. het OGC-proces end-to-end via het recept (LocalClient);
6. de docker-gated broker-e2e (skip zonder daemon).

Bestaande suites (nldt, poc, poc-bp2op) blijven onaangetast; de adapter
voegt alleen pyld als dependency toe.

## Non-doelen

- Geen subscriptions, temporal API of registrations — batch-export is de
  opgave.
- Geen hosting van het `@context` op een publieke URL (canonieke URL + 
  lokaal bestand nu; hosting is vervolg).
- Geen Breda/Rijnland in deze snede — zelfde recept, latere snede.
- Geen schrijfacties op PoC-pipelines of corpora.

## Risico's

| Risico | Beheersing |
|---|---|
| Naamsconflict tussen eigen `ldt:`-termen en Smart Data Models | eigen namespace, geen herdefinitie van SDM-termen; termenlijst klein en gedocumenteerd in context.py |
| JSON-LD-processor gedraagt zich online (netwerkafhankelijk) | offline document-loader met commit-cache; test draait zonder netwerk |
| Broker-image verschilt tussen machines | tag vastgepind in compose; e2e skip zonder daemon |
| Entiteitexplosie (percelen/per-regel-entiteiten te groot) | batches per run, niet per object; grofmazige entiteiten (zone/regel/rij), geometrie als GeoJSON-waarde op `location` |
| Parallelle agent-sessies in de hoofdwerkmap | uitvoering in geïsoleerde git-worktree op eigen branch (patroon van de RegelRecht-simulatiesnede) |
