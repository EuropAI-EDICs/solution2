# Ontwerp: poc-nspd — grensoverschrijdend North Sea Port District-scenario-POC met Leia 3D-viewer

**Datum:** 2026-10-14
**Status:** ontwerp (geaccordeerd door opdrachtgever)
**Referentie:** [virtueel.zeeland.nl/nspd](https://virtueel.zeeland.nl/nspd) (NSPD-instantie van de
[Leia-viewer](https://github.com/leia-project/viewer), Geodan + Provincie Zeeland, MIT);
[NSPD-projectpagina's](https://www.nspd.eu) en [zeeland.nl/onderwerpen/ruimte/north-sea-port-district](https://www.zeeland.nl/onderwerpen/ruimte/north-sea-port-district).

## 1. Doel en succes­criterium

Een nieuwe PoC-directory `poc-nspd/` die planningsvragen voor het hele
**North Sea Port District** (NSPD) beantwoordt met de vraag-gedreven,
gegevensgedragen machinerie van PoC-1 (`poc/`), maar dan **grensoverschrijdend**:

- **NL-kant:** Vlissingen, Terneuzen, Borsele — juridische basis
  Omgevingsverordening Zeeland + Omgevingsvisie Zeeland.
- **BE-kant:** havenrelevante deel van Gent en Zelzate (haven + kanaalzone) —
  juridische basis Vlaamse RUP's, Gewestplan, VCRO en Vlarem II.
- **13 tracks** overgenomen uit PoC-1 (wind, zon, bos, water, bodem, mobiliteit,
  landschap, landbouw, wonen, werken, recreatie, biomassa, energietoets), met
  normsets per jurisdictie.

**Succes­criterium** — de *grensvergelijkende scan*: één vraag (bijv.
*"waar kan duurzame energie binnen het NSPD?"*) produceert in één run:

1. zones aan beide zijden van de grens, als één geojson met per claim het
   attribuut `land` (nl|be) en de normherkomst;
2. één rapport met naast-elkaar-secties (NL ∣ BE) en per claim letterlijk
   citaat + instrument + artikel + versie + URL uit het **eigen** rechtssysteem;
3. één Leia-scène waarin die zones, samen met 3D-gebouwcontext, direct
   visueel zichtbaar zijn.

Na fase 1 moet dit aantoonbaar werkend zijn voor de demo-tracks (wind, zon,
energietoets); fase 2 porteert de overige 10 tracks.

## 2. Context

- **Leia-viewer:** open-source Cesium-digital-twin-viewer (SvelteKit + Cesium,
  MIT), geconfigureerd via één JSON-configbestand (`?url=` of `config.json`);
  laagtypen o.a. `geojson`, `wms`, `wmts`, `3dtiles`, `vectortiles`;
  tools o.a. layermanager, featureinfo, zonalStatistics; geen Cesium-ion-token
  nodig; Docker-ondersteuning. De officiële NSPD-instantie gebruikt
  provincie-eigen 3D-tiles (via Cesium ion) — deze PoC gebruikt open
  alternatieven (3D BAG + GRB-extrusie) zodat geen ion-token nodig is.
- **Blauwdruk PoC-1 (`poc/`):** deterministische orchestrator (intake → Norm
  Analyst → Norm Formalizer → Geo Analyst → zone-engine → Cartographer →
  Critic V0–V4 → Explainer → Report), cite-or-abstain-normcards,
  cache-first ArcGIS-REST- en OGC-API-fetchers, sources-registry,
  scenario-sweep met dataGrounding, golden-regressie, offline pytest-suite.
- **Relatie tot lopend onderzoek:** de ISPRS-paper in `docs/research/`
  (schema-bewuste geo-data-importer, ITC Twente) en de Morales-thesis
  (PoC-6, Rijnland) zijn losse onderzoekslijnen; deze PoC kiest bewust de
  PoC-1-machinerie als basis en de Leia-viewer als presentatielaag.
- **Bestaand spoor `3d-viewer/`:** minimaal Cesium-experiment (3D BAG op
  Utrecht); blijft staan als referentie, wordt niet uitgebreid.

## 3. Alternatieven en keuze

| optie | oordeel |
|---|---|
| **A. nieuwe `poc-nspd/` + vendored/gepinde Leia-frontend** (gekozen) | volgt de repo-conventie (poc-breda, poc-rijnland, …); laat de werkende Utrecht-POC met goldens onaangeroerd; geografische en juridische extensie hebben een eigen plek. |
| **B. `poc/` ombouwen tot multi-regio** | geen codeduplicatie, maar grote refactor van een werkende PoC met frozen goldens en getrackte runs; tegen de conventie in; hoog risico. |
| **C. slanke pipeline eerst, tracks later stapelen** | sneller eerste resultaat, maar stelt de geaccordeerde keuze (alle 13 tracks) uit en levert een tweede, afwijkende machinerie op. |

Front-end-keuze: **Leia zelf configureren** (letterlijk "zoals hier") boven een
eigen Cesium-app (meer controle, maar minder herkenbaar en duplicatie van een
bestaand open-sourceproduct).

## 4. Ontwerp

### 4.1 Directorystructuur

```
poc-nspd/
  README.md
  run.py                 # orchestrator (geport, met --xborder-modus)
  data/
    sources.json         # registry mét jurisdictie + endpointtype + pin-datum
    cache/               # pdok/ geopunt/ zeeland/ vlaanderen/ cbs/
  corpus/                # NL: OV+OV Zeeland; BE: RUP's, Gewestplan, VCRO, Vlarem
  schemas/               # poc-contracten geporteerd + jurisdictie-extensies
  pipeline/
    fetchers/            # pdok.py geopunt.py zeeland_arcgis.py cbs.py
    agents.py            # norm-analyst/formalizer met jurisdictieprofielen
    engine.py geodata.py cartographer.py critic.py explainer.py report.py
    xborder.py           # merge NL+BE → één zoneset + naast-elkaar-rapport
  tracks/                # 13 trackdefinities, normsets per jurisdictie
  scenarios/             # sweep + dataGrounding (zoals poc/)
  tests/                 # offline suite + goldens + e2e-wiring
  runs/ scenario-runs/
  viewer/
    README.md            # hoe Leia start, pin van upstream-commit
  viewer-data/           # door pipeline geschreven: nspd.config.json + lagen
  make_viewer_config.py  # run-output → Leia-config + laagbestanden
```

Leia zelf wordt als **git submodule** onder `viewer/` gepind op een expliciete
upstream-commit; de POC-schrijflaag (`viewer-data/`) staat buiten de submodule
en wordt door Leia geladen via `?url=` (een kleine static server of
`CONFIG_SERVER_URL` volstaat; geen wijzigingen in de Leia-bron).

### 4.2 Juridische basis — twee rechtssystemen

- **NL:** Omgevingsverordening Zeeland + Omgevingsvisie Zeeland via
  CVDR/SDS-BI — zelfde recept als PoC-1 (letterlijk citaat, versie gepind,
  cite-or-abstain).
- **BE:** RUP's voor het havengebied Gent/Zelzate, Gewestplan-voorschriften,
  VCRO-algemene regels en Vlarem II voor zover ruimtelijk relevant; teksten
  via de open Vlaamse publicatiekanalen. Exacte endpoints worden in taak 1
  **gepind** in `data/sources.json` (met retrieved-datum); niet-openbare lagen
  falen **luid**, nooit stil leeg (zelfde discipline als kalibratie plan 2).
- **Instrumenttypen** in het norm-schema: `omgevingsverordening-nl`,
  `omgevingsvisie-nl`, `rup-be`, `gewestplan-be`, `vcro-be`, `vlarem-be`.
  Het Norm Formalizer-profiel per jurisdictie: NL = IMOW-achtige regels
  (zoals Utrecht); BE = stedenbouwkundige voorschriften per bestemming
  (RUP/Gewestplan) plus algemene regels (VCRO/Vlarem).
- Elke normclaim draagt `jurisdictie`; de decision-table krijgt een
  jurisdictie-kolom.

### 4.3 Geodata — twee ecosystemen, cache-first

| jurisdictie | bronnen | type |
|---|---|---|
| nl | PDOK (BGT, BAG, Natura2000), Provincie Zeeland ArcGIS Hub (zones/wind/zon), CBS vierkant 100m (context) | arcgis-rest / ogc-api |
| be | Geopunt WFS (GRB-gebouwen en -percelen, gewestplanzones, SBZ/Natura2000-Vlaanderen), DHM Vlaanderen (hoogte, voor extrusie), OVAM-bodem waar track vereist | wfs |

- Werkbbox: NSPD-kern van haven Gent/Zelzate tot Vlissingen/Borsele; exacte
  coördinaten worden in taak 1 als constante gepind (analoog aan de
  Utrecht-bbox in PoC-1).
- CRS: brondata NL in EPSG:28992 (RD), BE in EPSG:31370 (Lambert72); interne
  verwerking en alle outputs in EPSG:4326 (viewer/Cesium), conversies via
  pyproj.
- Fetchers cache-first (`poc-nspd/data/cache/`), hergebruik van het
  fetcher-patroon uit PoC-1 en kalibratie plan 2 (fixture-gedrag, luid falen).

### 4.4 Grensvergelijkende scan (`pipeline/xborder.py`)

- Input: één uitdaging (bijv. energietransitie) + de tracks uit fase 1.
- Stappen: dezelfde pipeline per jurisdictie op de eigen deelruimte →
  zonesets per land → merge: één zone-geojson, per feature `land`,
  `track`, `norm-herkomst` (instrument + jurisdictie); geen zone-uitvlakking
  over de grens.
- Rapport: naast-elkaar-secties (NL ∣ BE), dezelfde sectievolgorde, één
  decision-table met jurisdictie-kolom; `report.html` blijft file://-werkend
  (Leaflet-map voor het overzicht, link naar de Leia-scène voor 3D).
- Outputs naar de viewer: `viewer-data/layers/<run-id>/zones-nspd.geojson`
  (+ optioneel contextlagen), gestyled per land.

### 4.5 Leia-scène (`make_viewer_config.py`)

- Genereert `viewer-data/nspd.config.json`: camera start op de NSPD-kanaalzone;
  basemap PDOK BRT (nl) + Geopunt-basiskaart (be); themalagen: pipeline-zones
  (geojson, styling per land), havenbedrijven/terreinen, energie-infrastructuur;
  featureinfo en layermanager aan.
- 3D-gebouwcontext: **3D BAG cesium3dtiles** (`data.3dbag.nl`, LoD2.2) voor de
  NL-kant; voor de BE-kant GRB-gebouwvoetafdrukken geëxtrudeerd met
  DHM-hoogten (Leia geojson-extrude); als DHM-extrusie te zwaar blijkt, valt
  fase 1 terug op vlakke BE-gebouwen (beslispunt in taak 8, gedocumenteerd).
- Config-subset die de POC gebruikt wordt lokaal tegen een JSON-schema
  gevalideerd (zie §6) zodat geen browser nodig is om wiring te testen.

### 4.6 Scenario's en dataGrounding

- Scenario-sweep en `basis.dataGrounding` worden geporteerd zoals PoC-1
  (kalibratie plan 2): sources-registry als onderbouwing, provenance-basis
  `norm_variance`/`policy_variant`/`hypothetical`.
- Nieuwe critic-gate **V2b jurisdictie-match**: elke claim moet een bron-id uit
  de *eigen* jurisdictie hebben — een NL-norm mag nooit over BE-grond vallen en
  omgekeerd; overtreding faalt de run luid.

## 5. Foutafhandeling en determinisme

- Cache-first responses; een volledige run reproduceert zonder netwerk
  (fixtures in `tests/`).
- Luid falen voor niet-gepinde of niet-openbare bronnen; geen stille lege
  zones.
- Critic-gates: V0 reproduceerbaarheid en V2 dataGrounding uit PoC-1, plus
  V2b (§4.6). V4 blijft HITL.
- LLM-seams (scenario-author, narrator) propose-only en standaard uit, lokaal
  Ollama — zelfde patroon als PoC-1.

## 6. Testen

- **Offline pytest-suite** met fixtures voor PDOK- én Geopunt-antwoorden en een
  frozen `corpus/`; geen netwerk in CI of standaard-suite.
- **Golden-regressie** voor minimaal één referentierun per jurisdictie
  (kandidaten: wind, zon) — zelfde golden-patroon als PoC-1.
- **E2E-wiring-test:** run → `viewer-data/` → `nspd.config.json` + laagbestanden
  valideren tegen het lokaal geformatiseerde Leia-configschema.
- **Controle-run:** de grensvergelijkende baseline reproduceert bij herhaald
  draaien (≤ 0,1 % verschil, zoals de kalibratie-controle).

## 7. Scope-begrenzing

- BE-zonering beperkt tot het havenrelevante deel van Gent/Zelzate (haven +
  kanaalzone), niet heel Gent.
- Geen Vlaamse vergunningspraktijk (Omgevingsvergunning-assemblage), geen
  Vlarem-detaillijsten tot op emissiegrenswaarden, geen realtime/sensordata.
- De Leia-instantie van virtueel.zeeland.nl is 3D-verkenning; deze PoC voegt
  daar het vraag-gedreven, gerechtvaardigde zoneonderzoek aan toe en claimt
  geen operationele vergunningstool te zijn.
- `poc/` (Utrecht) blijft onaangeroerd: geen gedeelde code-refactors in deze
  PoC; hergebruik gaat via kopie/adapt, zoals de bestaande poc-*-conventie.

## 8. Fasering

**Fase 1 — succes­criterium aantoonbaar:**

1. pinning: bronnen (NL+BE), NSPD-bbox, Leia-submodule op expliciete commit,
   `sources.json`-schema met jurisdictie;
2. normcuratie NL (OV Zeeland, recept PoC-1) — voor wind, zon en energietoets;
3. normcuratie BE (RUP/Gewestplan/VCRO) — voor wind, zon en energietoets;
4. fetchers PDOK + Geopunt cache-first met fixtures;
5. jurisdictieprofielen + schema-extensies (instrumenttypen, jurisdictie-veld);
6. zone-engine + critic V2b voor beide kanten;
7. xborder-merge + naast-elkaar-rapport;
8. Leia-config + lagen + 3D-context (beslispunt DHM-extrusie) + e2e-wiring;
9. goldens + volledige suite groen → grensvergelijkende scan demo-klaar.

**Fase 2 — uitbreiding:**

10. overige 10 tracks porteren op dezelfde machinerie (normcuratie per land);
11. optioneel: crosstrack-conflictoverlay over de grens heen (poc/
    `crosstrack/`-patroon).

## 9. Open punten → gepind (update 2026-10-14, via de Datavindplaats-statusspoor)

- **Vlaamse geo-diensten: gepind en live geverifieerd (2026-10-14).** De oude host
  `geoservices.informatievlaanderen.be` is vervallen (geen DNS). Actueel:
  `geo.api.vlaanderen.be` (GRB WFS HTTP 200; DHMV WMS HTTP 200 met lagen DHMV-I/II;
  3DGRB WMS) en `www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/ows`
  (HTTP 200; SBZ-lagen `nz:nz_n_gevoelige_habitats_sbz_2025` geverifieerd).
  Vinderinstrument: [Datavindplaats](https://www.vlaanderen.be/datavindplaats/catalogus);
  geverifieerde bronlijst: [Geopunt-statuspagina geo-webdiensten](https://www.geopunt.be/status-geo-webdiensten.html).
  Exacte WFS-typeNames volgen in implementatieplan taak 5 (probe-script).
- **Juridische NL-bron: gepind.** Omgevingsverordening Zeeland = CVDR709135
  (lokaleregelgeving.overheid.nl/CVDR709135); consolideerdatum wordt bij het ophalen
  vastgelegd in `corpus/nl/CVDR709135/META.json`.
- **NSPD-werkbbox: gepind.** WGS84 `(3.45, 51.02, 3.88, 51.48)` (haven Gent/Zelzate →
  Vlissingen/Borsele), als constante `bbox.NSPD_BBOX_WGS84`, met RD/Lambert72-afgeleiden
  via pyproj.
- **Haalbaarheid DHM-extrusie voor BE-gebouwen**: blijft een beslispunt in
  implementatieplan taak 12, met vlakke GRB-voetafdrukken als gedocumenteerde fallback.

Implementatieplan: `docs/superpowers/plans/2026-10-14-poc-nspd.md` (fase 1) en
`docs/superpowers/plans/2026-10-14-poc-nspd-fase2.md` (fase 2).

**Status 2026-10-15: fase 2 geïmplementeerd** — alle 13 tracks gecureerd (NL+BE;
`bodem-be` en `biomassa-be` als gedocumenteerde abstentions), 15 goldens, 12
xborder-rapporten. Item 11 (crosstrack-overlay) blijft bewust buiten scope.

**Status 2026-10-16: fase 3a geïmplementeerd (ruimtelijke grounding)** — plan
`docs/superpowers/plans/2026-10-16-poc-nspd-fase3.md` (taken 1–5): Zeeland
OVZ-WFS (10 lagen) + GRUP Zeehavengebied Gent (Mercator gewestelijke RUP, 13
bestemmingszones met client-side filters) gepind; 33 formal rules geformaliseerd
met hun operand (NL: concentratielocaties, stedelijk gebied, dijktrajecten,
badplaatsen, afwegingszone/landschap-markers; BE: 15 GRUP-zone-regels); alle 26
runs PASS met gedifferentieerde zones (wind-nl 12,2 km², zon-nl 22,9 km²,
recreatie-nl 15,9 km²; BE-zones 0,01–1,17 km²); suite 99 + 15 goldens. Fase 3b
(S7 what-if-port) volgt in hetzelfde plan (taken 6–8).
