# poc-nspd — North Sea Port District (grensoverschrijdend scenario-POC + Leia 3D-viewer)

Spec: `docs/superpowers/specs/2026-10-14-poc-nspd-design.md` · Plannen:
[fase 1](../docs/superpowers/plans/2026-10-14-poc-nspd.md) ·
[fase 2](../docs/superpowers/plans/2026-10-14-poc-nspd-fase2.md)

**Status: fase 2 afgerond — alle 13 tracks × 2 jurisdicties.** Het succescriterium (§1) is
aantoonbaar werkend: 26 runs PASS (incl. twee gedocumenteerde abstentions), 87 tests groen
(85 offline + 2 abstention-skips), 15 golden-tests (14 track-referentieruns + controle-run,
reproduceerbaar op 0,000 %) en 13 xborder-rapporten; de wind-demo loopt end-to-end tot in
de Leia-config (zie Opdrachten).

## Doel en succescriterium (spec §1)

Planningsvragen voor het hele **North Sea Port District** beantwoorden met de
vraag-gedreven, gegevens­gedragen machinerie van PoC-1 (`poc/`, Utrecht), maar dan
**grensoverschrijdend**. Het succescriterium is de *grensvergelijkende scan*: één vraag
produceert in één run —

1. zones aan beide zijden van de grens, als één geojson met per feature het attribuut
   `land` (`nl`|`be`) en de normherkomst;
2. één rapport met per-land secties (NL ∣ BE) en per claim letterlijk citaat +
   instrument + artikel + versie + URL uit het **eigen** rechtssysteem;
3. één Leia-scène waarin die zones, samen met 3D-gebouwcontext, direct zichtbaar zijn.

Fase 1 doet dit aantoonbaar voor de demo-tracks (wind, zon, energietoets × nl/be);
fase 2 porteert de overige 10 tracks (zie onderaan).

## Jurisdicties en pinnen

Rechtsbronnen (`corpus/sources.json`, documentregister; `retrievedAt` 2026-10-14):

| land | docId | instrument | versie-pin |
|---|---|---|---|
| nl | S01 | Omgevingsverordening Zeeland | CVDR709135, geldend 02-06-2026 t/m heden |
| be | S02 | GRUP afbakening zeehavengebied Gent — fase 2 (Bijlage II SV) | RUP 2.12_00358_00001 |
| be | S03 | GRUP uitbreiding papierproducerend bedrijf (Bijlage III SV) | RUP zeehavengebied Gent |
| be | S04 | Aanvullende SV gewestplannen (o.a. Gentse en Kanaalzone 08) | toestand 1 jan 2002 |
| be | S05 | VCRO geconsolideerd | geldend 14/10/2026 |

Geo-bronnen (`data/sources.json`, registry v2.0; live-geprobeerd 2026-10-14):

| id | land | type | rol in fase 1 |
|---|---|---|---|
| `pdok-natura2000` | nl | OGC API (`api.pdok.nl/rvo/natura2000`) | exclusion — enige gepinde laag die de zone-algebra fetching |
| `geopunt-grb-wfs` (`GRB:ADP`) | be | WFS | gebouwcontext (vlakke laag in de viewer, zie besluit hieronder) |
| `mercator-sbz-wms` | be | WMS | geregistreerd als exclusion-alias, door geen fase-1-regel gebruikt |
| `pdok-brt-achtergrondkaart` | nl | WMTS | achtergrondkaart viewer |
| `3dbag-lod22-cesium` | nl | 3D Tiles | 3D gebouwcontext viewer |
| `geopunt-dhmv-wms` | be | WMS | context (DHM-extrusie: zie beslispunt fase 2) |
| `cvdr709135-ov-zeeland` | nl | document | juridische pin — NL-rechtsbron (consolideerdatum in `corpus/nl/CVDR709135/META.json`; zie S01 hierboven) |
| `cbs-grid-kerncijfers-100m` | nl | OGC API | scenario-basis (`basis.dataGrounding`, kalibratie plan 2 task 4; niet door fase-1-regels gebruikt) |
| `mercator-ruimtelijk-beleid` | be | WMS | kandidaat RUP/gewestplan-zonering — géén bruikbare coveragelaag als één typeName (probe 2026-10-14) → V4, RUP-zonering via corpus-gebindde AOI |
| `be-rup-corpus` | be | document | juridische pin — Vlaamse RUP-teksten haven Gent/Zelzate (documenten, sha256+META, taak 3) |

### PDOK-catalogus (2026-10-16): 33 extra NL-bronnen, gepind en in de nldt-datalake

`data/probe_pdok_catalog.py` heeft de PDOK-catalogus (`api.pdok.nl/index.json`, 130 OGC
API's, als-ontvangen onder `data/bronze/pdok-catalog/`) doorgelicht: 46 kandidaat-API's
live geprobeerd binnen de NSPD-bbox (`data/probe_pdok_catalog_2026-10-16.json`). Daaruit
zijn 33 bronnen gepind in `data/sources.json` (`tracks`, `role`, `fetchPolicy`): 27 met
`fetchPolicy: cache` (gedownload via `fetch_pdok_layers.py` → `data/cache/` dual-CRS +
`data/bronze/pdok/<id>/<stamp>/` ruwe pagina's; beide git-ignored) en 6 service-only
(basisregistraties, te omvangrijk voor een bbox-dump; on-demand met CQL2-`filter`).

| track(s) | bron-id (collectie) | rol | features in bbox |
|---|---|---|---|
| wind | `pdok-windsnelheden-100m` | scenario-basis | 3 klassevlakken (6,5–8 m/s) |
| water, wind, wonen | `pdok-hwh-waterkeringen` (IMWA `waterkering`, Scheldestromen) | attention (lijnen; bufferen) | 111 |
| water | `pdok-hwh-peilgebieden`, `-gemalen`, `-sluizen`, `pdok-rsa-rwzi` | scenario-basis / context | 303 / 33 / 2 / 5 |
| water, wonen, werken | `pdok-ror-overstromingsgevaar` (ROR `hazard_area`) | attention | 1 |
| mobiliteit, water | `pdok-nwb-vaarwegvakken`, `pdok-prorail-spooras`, `pdok-hoofdwegen-omgevingslawaai` | attention / context | 122 / 402 / 831 |
| landbouw, biomassa | `pdok-brp-gewaspercelen` (BRP `brpgewas`) | inclusion-kandidaat FR-LNB-* | 24 385 |
| bodem, wonen, landschap | `pdok-funderingsproblematiek`, `pdok-fysisch-geografische-regios` | attention | 5 046 / 20 |
| biomassa, energietoets | `pdok-reststromen-biogas`, `-houtachtig`, `pdok-restwarmte-industrie`, `pdok-omgevingswarmte-wko-buurt` | scenario-basis | 7 / 7 / 51 / 137 |
| werken, energietoets, wonen | `pdok-rev-seveso-{productie,energie,afval,opslag}` (REV/Brzo-inrichtingen) | scenario-basis — vult de havenbedrijven/energie-infra-gap (§Beperkingen) | 8 / 1 / 1 / 3 |
| bos, landschap, wind | `pdok-wetlands` (Ramsar), `pdok-cdda` | exclusion | 15 / 10 699 |
| landschap, wonen, recreatie | `pdok-rce-cultuurhistorie` (beschermde gezichten) | attention | 96 |
| wonen, werken, context | `pdok-cbs-buurten-2025`, `pdok-cbs-bevolkingskernen-2021`, `pdok-bestuurlijke-gemeenten` | scenario-basis / context | 176 / 47 / 7 |
| service-only | `pdok-top10nl-terrein`, `pdok-bgt-begroeidterreindeel`, `pdok-bag-pand`, `pdok-kadastrale-percelen`, `pdok-nwb-wegvakken`, `pdok-cbs-bbg2017` | context | on-demand |

Dialect-bevindingen (vastgelegd in `pipeline/geodata.py`): GoKoala pagineert via
`links[rel=next]` (offset/startIndex → HTTP 400); de REV/Seveso-dienst levert én
verwacht **lat,lon**-volgorde (registry `axisOrder: "latlon"`, bbox lon,lat geeft 0
treffers). Niet gepind (0 features in bbox of ongeschikt): Omgevingswet-geometrieën
(items 404 per omgeving), IMWA-zoneringen/keringsecties (Scheldestromen levert ze
niet), ROR-risicogebied, nationale parken, hoofdspoorwegen/agglomeraties omgevingslawaai,
KRM. BBG2017 is bewust service-only (2 480 ongeknipte vlakken = 217 MB per CRS).

De geformaliseerde regels gebruiken deze lagen niet (de OVZ-operanden komen uit de
OVZ-kaartbijlagen zelf; een nieuwe norm-operand vraagt de curatie-flow hieronder). Ze
zijn wél **what-if-operanden**: `run.py:ZONE_SOURCES` kent 23 PDOK-aliassen
(`windklasse-ge75-nl`, `gewaspercelen-nl`, `overstromingsgevaar-nl`, `seveso-*-nl`,
`restwarmte-industrie-nl`, `wetlands-nl`, `cdda-nl`, …; context-rollen bewust niet) en
de scenario-engine heeft de mutatie **`add_zone_rule`** (`pipeline/scenarios.py`): een
`hypothetical` voegt een synthetische regel over een alias-laag toe (inclusion/
exclusion, optionele buffer). De V2-gate eist `basis.type=hypothetical` én
`basis.dataGrounding.sourceId` gelijk aan de alias-bron (rol ≠ context), en weigert een
ruleId die met een baseline-regel botst — nooit een juridische claim, wél herleidbaar.
De scenario-runner laadt die alias-lagen offline uit de pipeline-cache en seedt de
`aoi`-zone uit de request-AOI (AOI-brede baselines met FR-AOI-01 draaien zo zonder
degradatie); de engine buffert puntlagen (restwarmtebronnen, gemalen) tot vlakken in
beide paden (shapely + geopandas-V3).

Vijf scenario-sets rekenen er nu op (`scenarios/*.json`, alle verdict pass, H3-metrics
aan; `scenario-runs/20261016T20*`):

| set | scenario | finale zone (control) |
|---|---|---|
| wind-nl | SC-WIND-NL-WINDKLASSE-GE75 — windklasse ≥ 7,5 m/s als extra inclusie | 51,2 km² (12,2) |
| wonen-nl | SC-WON-NL-BUITEN-OVERSTROMINGSGEVAAR · SC-WON-NL-SEVESO-PROD-500M | 565,8 · 994,0 km² (1000,6) |
| landbouw-nl | SC-LNB-NL-ALLEEN-GEWASPERCELEN (FR-AOI-01 drop + BRP-inclusie) · SC-LNB-NL-BUITEN-CDDA | 201,3 · 829,1 km² (1000,6) |
| werken-nl | SC-WER-NL-RESTWARMTE-1KM (1 km rond 51 restwarmtebronnen) · SC-WER-NL-GEEN-SEVESO-500M | 33,5 · 994,0 km² (1000,6) |
| bos-nl | SC-BOS-NL-ZONDER-WETLANDS · SC-BOS-NL-ALLEEN-CDDA | 853,2 · 171,5 km² (1000,6) |

In de Leia-viewer verschijnen ze automatisch als what-if-groepen (`_what_if`), en
16 PDOK-lagen staan als groep "PDOK-bronlagen" (cache-gedreven WGS84-kopieën, > 2 MB
display-gesimplificeerd 5 m; gewaspercelen/CDDA bewust niet — on-demand via de dienst).
Alles staat in de nldt-datalake (medallion: bronze = ruwe pagina's + catalogus-
snapshot, silver = dual-CRS lagen + registry + corpus, gold = runs/xborder/scenario) met
per PDOK-bron een DCAT-record (`catalog/dcat/<id>.json`, `nldt:poc=nspd`) — zie
Opdrachten stap 0.

AOI: NSPD-bbox 3.45–3.88°E / 51.02–51.48°N (`bbox.py`), gesplitst op 3.73°E in een
NL- en BE-helft (`use-cases/make_aoi.py`, EPSG:28992). Leia-submodule `viewer/` (MIT,
onaangetast) gepind op commit `73510022e708bc1042a4fd0e88cec27e4857434d`.

## Architectuur

```
use-cases/*.json          corpus/normcards-<land>-<track>.json     (curatie, taak 6/7)
        │                 corpus/formal-rules-<land>-<track>.json
        ▼                          ▼
┌─────────────────────────────────────────────────┐
│ run.py  (per track: <wind|zon|energietoets>-<nl|be>)│   runs/<ts>-<track>/
│ intake → NormAnalyst → NormFormalizer (+FR-AOI-01)  │   ├ request/normcards/formalrules.json
│ → V2b jurisdictie-gate → GeoAnalyst (cache-first)   │   ├ layers/zones.json → zones.geojson/.gml
│ → zone-engine → Cartographer → Critic V0–V3 (+V4)   │   ├ decision-table.{json,md}, validation/
│ → Explainer → HTML-rapport → run_summary.json       │   └ prov.json, report.html, run_summary.json
└─────────────────────────────────────────────────┘
        │  zones.json + decision-table.json per land
        ▼
┌─────────────────────────────────────────────────┐
│ pipeline/xborder.py  (merge + naast-elkaar-rapport) │   xborder-runs/<track>/
│ load_run → merge_xborder → write_xborder_report     │   ├ zones-<track>-nspd.geojson  (land=nl|be)
└─────────────────────────────────────────────────┘   └ report-xborder.html (NL ∣ BE-secties)
        │  zones-<track>-nspd.geojson
        ▼
┌─────────────────────────────────────────────────┐
│ make_viewer_config.py  (run-output → Leia-config)   │   viewer-data/  (git-ignored)
│ per-land zonelagen + BRT/Geopunt + 3D BAG + GRB     │   ├ nspd.config.json
└─────────────────────────────────────────────────┘   └ layers/*.geojson
        │  ?url=http://localhost:8000/nspd.config.json
        ▼
   viewer/ (Leia, SvelteKit + Cesium)  ←  python3 -m http.server 8000 -d viewer-data
```

Zone-semantiek fase 1 (taak 9): alle inclusion-regels van de fase-1-shards zijn zone-loos
(V4-markers). De run gebruikt daarom de request-AOI als inclusion-union via de
deterministische orchestrator-basisrule **FR-AOI-01** (`run_summary.inclusionBasis=aoi`);
alleen de gepinde exclusions worden uitgevoerd (NL: natura2000-nl via PDOK; BE: geen
gepinde exclusies → finale zone = BE-AOI). FR-AOI-01 is een uitvoeringsconstructie, geen
inhoudelijke norm, en telt bewust mee in de golden-tellingen (zie teststrategie).

3D-context BE-gebouwen (taak-12-besluit, `data/grb_extrusie_besluit.json`): GRB-gebouwen
als **vlakke laag** (DescribeFeatureType `GRB:ADP` heeft geen hoogteveld; DHM-extrusie
vergeert de POC-tijd) — laag `grb-gebouwen`, `defaultOn: false`, herbeoordeling fase 2.

## Curatie-flow (taak 6/7-patroon)

Per land + track bestaat een corpus-trio: `corpus/normcards-<land>-<track>.json`
(cite-or-abstain NormCards met letterlijk citaat, instrument, versie, URL, confidence),
`corpus/formal-rules-<land>-<track>.json` (executable FormalRules met `normCardId`-
koppeling en `zoneSelector`) en `corpus/evidence-<land>-<track>.json` (extractie-bewijs).
Afwijzingen uit de analysefase staan in `corpus/normcards-rejected-<land>.json`.
Bronnen eerst vastleggen in `corpus/sources.json` (documentregister, met `retrievedAt`)
en `data/sources.json` (geo-registry, met probe-bewijs in `data/probe_*.json`); zone-
aliases die een FormalRule gebruikt moeten in `run.py`:`ZONE_SOURCES` op een gepinde
registry-bron staan (acceptatie-eis taken 6/7). Een nieuwe track = nieuw corpus-trio +
`TRACKS`-regel in `run.py` + use-case via `use-cases/make_aoi.py`.

## Opdrachten

Interpreter: `poc-nspd/.venv` (`python3` = `.venv/bin/python` hieronder). Werk vanaf
`poc-nspd/`. Alle fetches zijn cache-first (`data/cache/`); `--refresh` forceert
opnieuw downloaden.

```bash
# 0. PDOK-bronnen (2026-10-16): catalogus proberen → lagen ophalen → nldt-datalake
python3 data/probe_pdok_catalog.py          # live; schrijft data/probe_pdok_catalog_<datum>.json
python3 fetch_pdok_layers.py                # cache-first; --refresh / --ids <id …>; bronze + fetched-bewijs
(cd ../nldt && PYTHONPATH=. .venv/bin/python scripts/lake_sync.py --poc nspd \
   && PYTHONPATH=. .venv/bin/python scripts/pdok_catalog_records.py \
   && PYTHONPATH=. .venv/bin/python scripts/build_lake_inventory.py)
#    → nldt/data/lake/nldt-poc-lake/{bronze,silver,gold}/nspd/ + catalog/dcat/pdok-*.json
#    what-if-sweeps op de PDOK-lagen (add_zone_rule; offline uit de cache, baseline = nieuwste run):
for uc in wind-nl wonen-nl landbouw-nl werken-nl bos-nl; do python3 scenarios/run.py --use-case $uc; done
#    H3-metrics draaien via de nldt-CLI met déze interpreter: .venv heeft httpx + h3 nodig
#    (anders degradeert elk scenario met h3-metrics-error; verdict blijft onaangetast).

# 1. run — één track end-to-end (exit 0 = Critic-verdict pass)
python3 run.py --use-case wind-nl            # --out <dir> voor een vaste doelmap
python3 run.py --use-case wind-be
#    tracks: {wind,zon,energietoets}-{nl,be}; --bbox voor een clip; --refresh voor live

# 2. xborder-merge + naast-elkaar-rapport (twee runs van één track, NL + BE)
python3 -m pipeline.xborder runs/<ts>-wind-nl runs/<ts>-wind-be xborder-runs/wind --track wind

# 3. Leia-config + lagen (hoofdtrack = camera + standaard aan; álle tracks naast
#    run-dir — xborder-runs/*/ — komen als scenario-groep mee, incl. rapport per track)
python3 fetch_netcongestie_layer.py      # eenmalig: Capaciteitskaart 'afname' → cache + viewer-laag
python3 make_viewer_config.py --track wind --run-dir xborder-runs/wind

# 4. viewer starten (aparte terminals; viewer/ is de onaangetaste Leia-submodule)
#    Let op: Leia leest de query-parameter ?config= (niet ?url= — de upstream-README noemt
#    die verkeerd), en in Vite-dev-modus is ?url= zelfs gereserveerd. De robuuste route:
#    zet de config + lagen op de viewer-eigen origin:
cp viewer-data/nspd.config.json viewer/static/config.json
mkdir -p viewer/static/layers && cp viewer-data/layers/*.geojson viewer/static/layers/
mkdir -p viewer/static/reports && cp viewer-data/reports/*.html viewer/static/reports/
(cd viewer && printf 'APP_URL=http://localhost:5173\nCONFIG_SERVER_URL=http://localhost:5173\n' > .env \
 && npm install && npm run dev -- --port 5173)
#    open: http://localhost:5173/?config=http://localhost:5173/config.json
#    (productie-variant: `npm run build --adapter=static` → python3 -m http.server 8010 -d viewer/build
#     → http://localhost:8010/?config=http://localhost:8010/config.json)
#
#    Bekende eigenschap van deze Leia-pin (commit 7351002): na het laden staan de lagen
#    wél in de laagbeheer-bibliotheek, maar materialiseren ze pas op de globe ná eenmalig
#    uit+aan vinken van de laag-checkbox (Links de tweede tool-knop = Lagenbeheer →
#    groep openklappen → checkbox 2× klikken). Daarna stromen PDOK-tiles, zones en
#    3D BAG direct in. (Vers geopende tabs materialiseren vaak ook zonder deze dans.)
#
#    NOOIT de pagina herladen in de in-app browser van ZCode: één reload laat de
#    Cesium-scène permanent zwart renderen (WebGL-context in WKWebView). Sluit het
#    tabblad en open een nieuw tabblad met dezelfde URL — dat werkt altijd.
#
#    De zones-lagen tonen alleen de eindzones (ZR-final-*) van de pijplijn; de
#    tussenstappen (inclusion_union/intersection/difference) zijn AOI-breed en
#    stapelden zich voorheen tot een bijna dekkend oranje vlak (demo 2026-10-15).
#
#    Leia-stijlcontract voor geojson-lagen (geojson-layer.ts): kleur uitsluitend via
#    settings.style {fill, stroke}; transparantie via laag-opacity 0-100 (hex-alpha
#    wordt door withAlpha() overschreven, zonder opacity = vol-dekkend); contouren
#    verschijnen alleen bij style.stroke; strokeWidth weglaten (upstream-bug).
#
#    Referentielagen (2026-10-16): de Leia-config van de NSPD-viewer van Provincie
#    Zeeland (https://virtueel.zeeland.nl/nspd → /prod/config/nspd.config.json) staat
#    in data/reference/ en wordt door make_viewer_config.py 1-op-1 overgenomen
#    (53 lagen, 9 groepen; tool layerLibrary ontsluit ze). Uitgesloten: map5.nl-
#    topokaarten (betaalde klantsleutel van de provincie). Niet werkend vanaf onze
#    origin: "3D Gebouwen België" — de tileset op virtueel.zeeland.nl is origin-
#    vergrendeld (CORS); de laag staat in de bibliotheek met die uitleg. Standaard
#    aan: GRB Vlaanderen (detailkaart mét gebouwvoetafdrukken), Begrenzing NSPD.
#    NB: de fase-1-laag "GRB gebouwen" is hernoemd naar "GRB percelen" — GRB:ADP
#    zijn administratieve percelen (CAPAKEY/CANU), geen gebouwen.
#
#    Scenario-lagen (AI scenario planning): groep "Scenario-zones (AI-pipeline)"
#    met per track een geneste groep (Zones <track> NL/BE, alleen ZR-final-*); de
#    hoofdtrack staat aan. Fase 3 (2026-10-16) heeft de regel-geometrie gepind en
#    de meeste regels geformaliseerd — de zones zijn écht gedifferentieerd:
#    wind-nl 12,2 km² (concentratielocaties − Natura 2000), zon-nl 22,9 km²
#    (stedelijk gebied −), recreatie-nl 15,9 km² (badplaatsen Vlissingen/Breskens),
#    water-nl 997 km² (AOI − dijktrajecten); BE: GRUP-zones (bos 1,17 km², zon
#    0,44 km², werken 0,41 km², …).Tracks met alléén markers/procedurele normen
#    (o.a. biomassa/bodem/landschap) blijven gelabeld "(AOI-breed)" — eerlijk:
#    hun waarde zit in de normtabellen, rapport linkt naar reports/<track>.html.
#    Groep "Scenario-bronlagen (regel-operanden)": Natura 2000 NL, SBZ Vlaanderen,
#    Zeeland OVZ-lagen (via de pipeline-cache), DHM Vlaanderen II hillshade en
#    Netcongestie afname NL (ArcGIS Capaciteitskaart → fetch_netcongestie_layer.py,
#    geclipt+gesimplificeerd; zelfde cache als pipeline.national_data.load_netcongestie).
#    What-if scenario's (S7, fase 3b): groep "What-if scenario's (S7)" — per
#    use-case de nieuwste geslaagde scenario-run (scenario-runs/*/scenario-
#    report.json) als CONTROL (aan, grijs) + elk scenario met Δ en IoU in de
#    titel (groen = ruimte erbij, rood = eraf). Sweep draaien met:
#      .venv/bin/python scenarios/run.py --use-case wind-nl --author file --no-h3
#    (sets: scenarios/wind-nl.json, wind-be.json; LLM via --author llm/hybrid met
#    LDT_SCENARIO_LLM_ENDPOINT; H3-metrics optioneel zonder --no-h3).
```

Demo-artefacten van fase 1 zitten in de repo: de zes smoke-runs onder `runs/20261014T*`
en de wind-xborder-merge onder `xborder-runs/wind/` (`report-xborder.html` + 
`zones-wind-nspd.geojson`). `viewer-data/` wordt lokaal gegenereerd en is git-ignored.

## Teststrategie

```bash
.venv/bin/python -m pytest            # 39 offline tests (fixtures, geen netwerk)
.venv/bin/python -m pytest -m golden  # 4 golden-regressie-tests (cache-first, traag)
```

- **Offline suite** (`pytest.ini`: `-m "not golden and not llm"`): contracts, corpus-,
  gate-, engine-, xborder- en viewer-config-tests — allemaal op fixtures/tmp.
- **Golden-regressie** (`tests/test_golden_nspd.py`, marker `golden`): draait de
  volledige pipeline voor wind-nl, wind-be, zon-nl, zon-be en vergelijkt een bewust
  beperkte veldset tegen `pipeline/goldens-nspd/<track>.json`: `verdict`
  (run_summary), `output_rules` / `formalized` / `rejected` (tellingen uit
  formalrules.json — inclusief **+1 orchestrator-constructie FR-AOI-01** in
  `output_rules` én `formalized`), en `v2bStatus` (apart hard op `pass` geëist).
  Vluchtige velden (o.a. FR-AOI-01's dag-stamp `formalizedAt`, runId, generatedAt,
  hashes) staan bewust buiten de vergelijking.
- **Freezen of her-frozen** na een bewuste gedragswijziging:
  `NSPD_GOLDEN_FREEZE=1 .venv/bin/python -m pytest -m golden` — zonder die env-var
  faalt een ontbrekende golden hard (TDD: eerst rood, dan freeze, dan groen).
- **Reproduceerbaarheid**: tweemaal `wind-nl` draaien geeft identiek
  `headline.finalOpportunityKm2` (gecontroleerd: 852,177 km², verschil 0,000 %,
  eis ≤ 0,1 %). De tweede run raakt het netwerk niet: `geodata.fetch_layer` is
  cache-first (geldige cache → geen registry-consultatie), daarom heeft `run.py`
  bewust geen `--offline`-vlag nodig.

## Beperkingen (spec §7 + fase-1-runbeperkingen)

- BE-zonering beperkt tot het havenrelevante deel van Gent/Zelzate (haven + kanaalzone),
  niet heel Gent.
- Geen Vlaamse vergunningspraktijk (Omgevingsvergunning-assemblage), geen
  Vlarem-detaillijsten tot op emissiegrenswaarden, geen realtime/sensordata.
- Screening-artifact op programmeerfase: geen operationele vergunningstool; per-locatie
  toetsing blijft nodig; de Leia-instantie van virtueel.zeeland.nl blijft 3D-verkenning.
- Fase-1-zone-semantiek: inclusion = request-AOI (`inclusionBasis=aoi`, FR-AOI-01); de
  provinciale GIO/DSO-downloadketen en de BE RUP-deelgebieden/gewestplan-SZ-geometrieën
  zijn niet aan de zone-algebra gekoppeld (geen gepinde open-data-alias) → V4.
- Het xborder-rapport heeft bewust geen Leaflet-kaart: elke rij/feature draagt `land`;
  het 3D-overzicht loopt via de Leia-scène (spec §4.4-interpretatie).
- Havenbedrijven/energie-infrastructuur-themalagen (spec §4.5) zijn niet opgenomen: geen
  open, pinbare geobron beschikbaar; bewuste gap — `make_viewer_config.py --track`
  werkt voor elke track.
- Rapport-kaartgeometrie is display-versimpeld (Douglas-Peucker, tolerance in
  `run_summary.tunings`); autoritatieve geometrie: `zones.geojson`/`zones.gml`.
- Herdraai de juridische recon én de pipeline na een nieuwe consolidatie van de genoemde
  instrumenten (NL: CVDR709135; BE: RUP/gewestplan/VCRO).
- `poc/` (Utrecht) blijft onaangeroerd: hergebruik via kopie/adapt (poc-*-conventie).

## Fase 2 — afgerond: alle 13 tracks

Fase 2 (plan `docs/superpowers/plans/2026-10-14-poc-nspd-fase2.md`) voegde de overige
tien tracks toe op dezelfde machinerie. Curatie verloopt config-gedreven via
`fase2_curatie.py` (citaten machinaal uit de extractor-kandidaten; `quote_guard.py`
verifieert letterlijkheid van álle kaarten in de suite).

| track | kaarten NL | kaarten BE | | track | kaarten NL | kaarten BE |
|---|---|---|---|---|---|---|
| wind | 2 | 4 | | landbouw | 2 | 2 |
| zon | 2 | 3 | | wonen | 2 | 1 |
| energietoets | 2 | 3 | | werken | 2 | 2 |
| bos | 3 | 2 | | recreatie | 2 | 2 |
| water | 3 | 2 | | biomassa | 2 | **0 (abstention)** |
| bodem | 3 | **0 (abstention)** | | mobiliteit | 3 | 2 |
| landschap | 2 | 2 | | | | |

- **Abstentions** (cite-or-abstain): `bodem-be` en `biomassa-be` hebben géén dragende
  bepaling in het BE-havencorpus — gedocumenteerd in de rejected-ledgers, runs draaien
  op de FR-AOI-01-constructie (alleen de request-AOI).
- **Goldens**: 14 track-referentieruns (`wind/zon/bos/water/bodem/mobiliteit/landschap/
  landbouw/wonen/werken/recreatie/biomassa`-nl + wind/zon-be) plus de controle-run-
  reproduceerbaarheidstest; freeze via `NSPD_GOLDEN_FREEZE=1`.
- **Xborder-rapporten**: 12 tracks onder `xborder-runs/` (zon via hetzelfde commando
  genereerbaar); naast-elkaar NL ∣ BE-tabellen met de decision-rows per land.
- Buiten scope (opvolgplan): crosstrack-conflictoverlay over de grens, DHM-extrusie van
  BE-gebouwen (taak-12-besluit). De scenario-sweep met `basis.dataGrounding` is er
  inmiddels (PDOK-catalogus 2026-10-16: `add_zone_rule`, vijf data-grounded sets).
