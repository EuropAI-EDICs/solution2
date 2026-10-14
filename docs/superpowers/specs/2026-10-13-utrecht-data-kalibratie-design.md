# Ontwerp: data-kalibratie van de Utrecht-PoC tegen de 5 uitdagingen + landelijke aanvulbronnen

**Datum:** 2026-10-13
**Status:** ter review
**Verwijzing:** bouwt op [2026-10-13-utrecht-uitdagingen-design.md](2026-10-13-utrecht-uitdagingen-design.md) (5 uitdagingen × 13 tracks × 3 scenario's).
**Rol van landelijke data:** scenario-basis voor data-gegronde hypotheticals + contextlaag in rapport/demo. Juridische claims blijven uitsluitend provinciaal (cite-or-abstain onaangetast).

## 1. Doel en probleem

Alle 62 in gebruik zijnde zone-lagen komen uit provinciale bronnen (agrest +
provincie ArcGIS Hub); de laatste versheid-checks dateren van aug-okt 2026, het
wetscorpus van 13-10-2025. Tegen de 5 uitdagingen zijn er drie concrete
kalibratie-problemen:

1. **Versheid**: 78 geregistreerde bronnen zijn in augustus gecheckt, vóór de
   oktober-tracks; de CVDR-snapshot is een jaar oud en er staat een
   verordening-wijziging te wachten (PS-besluit 18-11-2026).
2. **Data-gaps per uitdaging**: de energietoets heeft nul eigen lagen
   (all-marker, zone = provincie); wonen/werken missen vraagdata; het
   Landelijk Gebied heeft geen landgebruiksonderbouwing.
3. **Onderbouwing van hypotheticals**: de niet-juridische scenario's uit de
   uitdagingen-spec zijn nu willekeurig geparametriseerd (bijv. "500 m"),
   terwijl echte data ze geloofwaardiger en onderlegger kan maken.

## 2. Kalibratieloop (provinciaal, elke uitdaging)

Een herhaalbare kalibratie-procedure, script-gedreven, met rapport:

1. **Juridische versheid**: her-fetch CVDR704250 (geldend-per-vandaag), diff
   tegen `poc/corpus/cvdr704250-tekst-extract.txt`; artikel-wijzigingen
   flaggen per track. Her-verificatie van normcards alleen voor getroffen
   artikelen (cite-or-abstain gate blijft).
2. **Geo-versheid**: voor alle 62 gebruikte lagen de `lastChecked`-status
   actualiseren (cache-first: alleen her-download bij wijziging via de
   bestaande ArcGIS-connector); per laag diff-teller (featurecount + bbox +
   sha256 tegen de cache).
3. **Zone-drift**: na her-download de control-zones van de 13 tracks
   her-reproduceren (V3, ≤0,1% rel). Tracks met drift krijgen een her-run en
   nieuwe canonieke baseline; zonder drift blijft de baseline staan (geen
   golden-drift).
4. **Rapport**: `poc/data/calibration/<datum>-calibratierapport.{md,json}` —
   per uitdaging een profiel: bronnen × rol (juridisch / scenario-basis /
   context), lastChecked, wijzigingen, gaps, en de expliciete vlag
   *her-kalibreren na PS-besluit 18-11-2026*.

## 3. Nieuwe landelijke bronnen per uitdaging

| uitdaging | bron | rol | vult gap |
|---|---|---|---|
| energietransitie | Netbeheerder-congestiekaarten (Liander/Enexis/Stedin: ruimte op het net) | scenario-basis + context | energietoets heeft nul eigen lagen |
| energietransitie | CBS 100m-grid elektriciteitsverbruik | context | energiedruk per hex |
| wonen-werken | CBS 100m-grid bevolking + woningen; wijken/buurten kerncijfers | context | vraagdruk achter de aanbodzones |
| water-bodem | BRO/DINO (grondwaterstanden, bodemopbouw); RWS overstromingsrisico | context | ondergrond- en overstromingscontext naast de provinciale markers |
| landschap-infra | RCE monumenten + Indicatieve Archeologische Waarden; NWB-wegen/ProRail-spoor | context | erfgoed- en infrastructuurcontext |
| landelijk-gebied | CBS landgebruik-grid | context | agrarische/natuurlijke ondergrond |

Algemene regels voor alle nieuwe bronnen:

- Ingeschreven in `poc/data/sources.json` met eigen `role: context` of
  `role: scenario-basis` — nooit `inclusion`/`exclusion`/`conditional`
  (die rollen zijn voorbehouden aan geciteerde verordening-zones).
- Elke context-laag draagt in `layers.json`/prov.json een
  `hadPrimarySource`-record met publisher (CBS/RWS/BRO/netbeheerder),
  retrieved-datum en licentie.
- Fetchers volgen het bestaande cache-first-patroon (`pipeline/geodata.py`;
  nieuwe module `pipeline/national_data.py` voor de niet-ArcGIS-bronnen,
  CBS OData-API en DINO-wfs incl.), offline replays via de cache
  (fixtures zoals bij H3/US).

## 4. Data-gegronde hypotheticals (scenario-basis)

- `schemas/scenario-spec.schema.json` krijgt een optioneel veld
  `basis.dataGrounding` (bron-id + retrieved + korte toelichting). Een
  hypothetical *blijft* een hypothetical (niet juridisch onderbouwd), maar
  kan nu data-onderbouwd zijn — de eerlijke tegenhanger van de abstention
  ledger wordt daarmee sterker: *geen norm, wel data*.
- **Flagship**: energietoets-scenario 3 uit de uitdagingen-spec ("provinciale
  netcongestie-zones") wordt data-gegrond: de zone komt uit de
  netbeheerder-congestiekaart i.p.v. een arbitraire parameter. De andere 12
  tracks behouden hun geparametriseerde hypotheticals; hun scenario's zijn
  juridisch-gethemed en dat is precies het verhaal.
- De uitdagingen-spec wordt daarom op één punt aangepast: §4.1 energietoets
  scenario 3 verwijst naar deze spec (dataGrounding in plaats van
  willekeurige zones).

## 5. Contextlaag in de demo

- CBS 100m-grid → aggregatie naar H3-hex via het bestaande nldt-bridge-patroon
  (`pipeline/h3step.py`): per cel bevolking, woningen, energieverbruik als
  `contextStats` in de h3-overlays en het dashboard (zelfde mechanisme als de
  bestaande cellMeta/dayStats-panelen).
- Netcongestie-polygonen als uitschakelbare contextlaag in de
  energietoets/wind/zon-demo's (Leaflet, gedempte stijl, expliciet
  "context — geen juridische zone").
- Report.html krijgt per track een contextsectie (tabel + hexkaart-links);
  de crosstrack-overlay blijft juridisch-zuiver (geen contextlagen).

## 6. Componenten en dataflow

1. `pipeline/national_data.py` (nieuw): fetchers CBS-grid, wijken/buurten,
   BRO/DINO, RCE, NWB/ProRail, netbeheerder-congestie; cache onder
   `poc/data/cache/national/`.
2. Kalibratiescript `poc/data/calibrate.py` (nieuw): voert §2 uit en schrijft
   het rapport; herbruikbaar (ook ná 18-11-2026).
3. `sources.json`: nieuwe entries met rollen; bestaande 114 entries
   onaangetast.
4. Schema: `basis.dataGrounding` (optioneel) + tegenpoolige
   geautoriseerde-sweep-validatie (V2: dataGrounding resolvend t.o.v.
   sources.json, anders reject naar de ledger).
5. Demo: contextStats in h3/dashboard/report; netcongestielaag in de
   energietransitie-demo's.

## 7. Tests

- Kalibratie: versheid-diff-rapport is deterministisch her-runbaar
  (cache-fixture); zone-drift-gate aantoonbaar (fixture met een gewijzigde
  laag → track-vlag).
- Nieuwe fetchers: offline fixtures (CBS OData JSON, DINO-wfs response,
  congestie-polygonen), schema-validatie van de cache-artifacts.
- `dataGrounding`: schema-valid + V2-reject-weg (onbekende bron-id →
  proposals-rejected).
- Bestaande 303 tests + golden-regressie blijven groen zonder zone-drift;
  mét drift volgt de her-run het bestaande golden-proces.

## 8. Out of scope

- Geen juridische claims uit CBS of andere nationale bronnen (geen nieuwe
  inclusions/exclusions).
- Geen uitbreiding van de crosstrack-overlay met contextlagen.
- Geen her-formalisatie van normcards buiten de door de CVDR-diff getroffen
  artikelen.
- Extra provinces/landelijke dashboards — alleen de Utrecht-PoC.

## 9. Vastlegging uitvoering plan 2 (2026-10-14)

Vastlegging van de uitvoering van dit plan; de zusterspec
[2026-10-13-utrecht-uitdagingen-design.md](2026-10-13-utrecht-uitdagingen-design.md)
draagt de vastlegging van plan 1 (aldaar eveneens §9). De kalibratieloop (§2) is
geïmplementeerd (`poc/data/calibrate.py`); de eerste run staat in
`poc/data/calibration/2026-10-14-calibratierapport.{md,json}`: 13/13 tracks
pass (zone-drift ≤0,1%), 56 zone-lagen live geteld, 0 tel-fouten. Pins en
besluiten uit taken 4–8:

- **CBS**: de StatLine-OData-vierkanttabellen bestaan niet meer; gepind op
  PDOK OGC API (2026-10-14) — `vierkant100` (Vierkantstatistieken 100 m,
  jaargang 2024, CQL2-filter `jaarcode=2024`) en INSPIRE `existinglanduse`
  (landgebruik, BBG2017).
- **RCE**: WFS-host `data.geo.cultureelerfgoed.nl/openbaar/wfs` (2026-10-13)
  met `openbaar:rijksmonumentpunten`; de IAM-archeologie is een **substituut**
  (`openbaar:Archeologische_Monumentenkaart_2014`) — IAM zelf heeft geen open
  WFS.
- **DINO niet gepind**: DINOloket biedt geen open WFS meer (asgs-wfs/
  regionaal 404) en BRO-REST is auth-plichtig; `DINO_WFS`/`DINO_TYPENAME`
  staan leeg in `poc/pipeline/national_data.py` en `fetch_dino_ondergrond`
  faalt daardoor luid (RuntimeError) zolang er geen endpoint is gepind — de
  sources.json-note draagt het vervolgstip.
- **Netcongestie = de Landelijke Capaciteitskaart elektriciteitsnet
  'afname'** van Netbeheer Nederland (ArcGIS-item
  `e111e42029af46da8a3a96787c28c444`, gewijzigd 2026-06-24, Esri NL Terms of
  Use): een document-download, dus een **momentopname** (gepind 2026-10-14;
  59 voedingsgebied-polygonen, waarvan 31× code 3 = tekort met wachtrij),
  geen stabiele API; de placeholder-polygoon van de publicatie is uit de
  cache gelaten.
- **Contextpagina's** zijn zelfstandige Leaflet-pagina's per uitdaging
  (`poc/pipeline/context_map.py` → `nldt/simulation/utrecht-context-<id>.
  html`, gelinkt via `simulationPages`) in plaats van embedding in
  `report.html`/de h3-panelen én in plaats van `deep-agents/runs/` (dat
  gitignored is; `nldt/simulation` staat wél in git, dus de pagina's zijn
  reproduceerbaar en direct gelinkt).
- **CBS-grid als legenda-regel**: de 100 m-kerncijfers-cache bevat ~18k
  cellen zonder geometrie; een puntenwolk is onpraktisch en de geometrie is
  niet bewaard, dus de cache-status staat als legenda-regel op de pagina
  (idem landgebruik en DINO).
- **SC-ET-NETCONGESTIE** demoot de AOI-marker (`FR-ET-01`) naar `attention`
  (Δ0) zodat de data-laag zelf de ruimtelijke differentiatie toont; een
  polygon-uitsluiting uit de provinciebrede AOI is niet uitdrukkbaar in de
  bestaande mutatie-vocabulary en is bewust buiten scope gehouden.
  `basis.dataGrounding` verwijst naar `netbeheerder-netcongestie` en is
  V2-gecontroleerd in elke sweep.
- **CVDR-diff is byte-gewijs**: de eerste run meldt `gewijzigd=True` — de
  her-fetch-geojson is geen byte-stabiele output, dus byte-drift is een
  bekende caveat en betekent niet automatisch een artikel-wijziging; de
  artikel-herverificatie volgt pas ná het PS-besluit van 18-11-2026 (de
  amendementsvlag staat in het rapport).
