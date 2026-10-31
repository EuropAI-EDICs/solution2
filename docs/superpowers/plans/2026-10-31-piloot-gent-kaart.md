# Piloot Gent — kaartpanel: route, omleidingen en door-Gent-gewenste route (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voeg aan het Gent-tabblad (sim-tab 5) een kaartpanel toe: de route van het adres waar het kenteken staat geregistreerd (bedrijfsadres uit het KBO/VKBO-open-register) naar het gewenste werkadres, mét innames/werken als omleidingen (GIPOD) en de **door Gent gewenste route** (de variant met de minste hinder). Zoveel mogelijk open data, volgens de repo-broncache-doctrine: netwerk alléén in de expliciete cache-stap; de simulatie blijft volledig offline.

**Architecture:** Drie lagen. (1) **Broncache**: `poc-gent/fetch_sources.py --kaart` haalt per kenteken-persona de bedrijfsadressen (deterministische selectie uit de VKBO-cache), geocoding (Nominatim/OSM, ODbL — BeSt Address blijft het geregistreerde productiepad), routes mét alternatief (OSRM-demo op OSM, ODbL) en de Gentse gemeentegrens (Nominatim-polygoon) op en schrijft `fixtures/source/kaart.json` mét meta (bronnen, licenties, datum). GIPOD-innames komen uit de bestaande mock-cache en krijgen hun punt via de adrescache (productiepad: echte GIPOD-LDES-geometrie, geregistreerd in meta). (2) **Build**: `build_simulation.py build_gent` rekent per persona de kaart uit: WGS84→SVG-projectie, zones uit de echte Gentse lagen, afstand punt-tot-route (omleiding-detectie, buffer 60 m), zone-kruisingen via de bestaande `gis_zones`-helper, en de routekeuze (minste innames op de route; gelijkspel → primair). (3) **Template**: een SVG-panel in `view5` met gemeentegrens, LEZ/autovrij-zones, beide routes (primair blauw, alternatief gestippeld), de gewenste route gemarkeerd, innames-mét-label, start/doel-markers en een legenda; persona's zonder kenteken-record (maria) zien geen kaart.

**Tech Stack:** Python 3.11+ stdlib-only voor `fetch_sources.py` en `build_simulation.py` (urllib voor de cache-stap); simulatie-template zonder externe deps (pure SVG); pytest; `node verify_static.mjs` voor de headless controle.

**Spec:** design §6 (GIS-adapter, FR-23) · F1.5-broncache-doctrine (`source.meta.json`, Modellicentekens, offline runs) · ontwerp §11 sim-tab. Open data: OSM/OSRM (ODbL), Stad Gent LEZ/autovrij (Modellicentie Gratis Hergebruik), VKBO/KBO (open register), GIPOD (Modellicentie Gratis Hergebruik).

## Global Constraints

- Netwerk alléén in `fetch_sources.py --kaart` (expliciete cache-stap, UA-header, rate-limit bewust); build, simulatie en tests blijven offline en deterministisch.
- De routecache vermeldt per onderdeel de bron + licentie + datum in `kaart.json.meta`; BeSt Address en echte GIPOD-LDES-geometrie staan als productiepad geregistreerd.
- Bedrijfsselectie is deterministisch (gesorteerde VKBO-rijen, vaste toewijzing) zodat rebuilds stabiel zijn zolang de broncache niet ververst.
- De "door Gent gewenste route" is een transparante regel (minste **vermijdbare** innames binnen 150 m van de route; innames bij het gedeelde eindpunt zijn onvermijdelijk en tellen niet mee; gelijkspel → primair, kortste) — in de legenda vermeld, geen zwarte doos. *Planamendement (implementer-bevindingen): buffer 60 → 150 m (straatwerken spannen wijd); GIPOD-mock kreeg een derde inname (Veldstraat-grondwerk) zodat de omleidingsmechaniek aantoonbaar differentieert (sanne → alternatief, jeroen → primair); OSRM biedt niet op elk routepaar een alternatief (Sint-Pietersplein-doelen) — het panel toont dan alléén de primaire route.*
- Maria (burger zonder voertuigrecord) krijgt geen kaartpanel; de overige persona's volgen de magda-kentekendekking (wim wordt aangevuld: vertelt over een bestelwagen maar blokkeert vóór prefill — geen run-gedrag gewijzigd).
- Template blijft zonder externe assets; de kaart is pure SVG ingebed in de bestaande data (SEC-05: geen persoonswaarden — bedrijfsnamen zijn open-registerdata).
- Commit per taak, conventional commits (scope `poc-gent` voor de datalaag, `simulation` voor build/template/verifier), Nederlandse samenvatting.

---

### Task 1: Broncache `--kaart` (VKBO-bedrijven, geocoding, OSRM-routes, Gent-grens, innames)

**Files:**
- Modify: `poc-gent/fetch_sources.py`
- Create (cache-uitvoer): `poc-gent/fixtures/source/kaart.json`
- Modify: `poc-gent/fixtures/magda.json` (+wim-kentekenrecord)
- Test: `poc-gent/tests/test_kaart_cache.py`

**Interfaces:**
- `bedrijf_toewijzing(vkbo_rijen, persona_ids) -> dict` — deterministische, vaste toewijzing (gesorteerde VKBO-rijen, vaste offsets) van persona → `{naam, adres}`; unit-testbaar zonder netwerk.
- `dun_punten(punten, max_punten=80) -> list` — polylijn verdunnen voor compacte embed; unit-testbaar (behoudt eerste/laatste punt, gelijkmatig).
- `haal_kaart(poc_root) -> dict` — de netwerkstap: geocoding (Nominatim, gedocumenteerde UA, fallback op de bestaande adrescache), OSRM `alternatives=true&overview=simplified&geometries=geojson`, gemeentegrens (`polygon_geojson=1`), innames uit de GIPOD-mock + adrescache-punten; schrijft `fixtures/source/kaart.json` mét meta (per bron: url, licentie, fetchedAt; productiepaden BeSt Address + GIPOD-LDES-WKT). `--kaart` CLI-vlag; `source.meta.json` krijgt een `kaart`-entry.
- Cachevorm: `{"grens": polygoon|null, "bedrijven": {persona: {naam, adres, coord}}, "routes": {persona: {"primaire": {punten, afstand_m, duur_s}, "alternatief": {…}|null}}, "innames": [{id, straat, type, van, tot, coord, bron}], "meta": {…}}`.

- [ ] **Step 1: falende unit-tests** (`test_kaart_cache.py`): `bedrijf_toewijzing` deterministisch en compleet over de kenteken-persona's; `dun_punten` behoudt eindpunten en lengte-begrenzing; cache-metavorm (opgebouwde dict zonder netwerk via monkeypatched fetch).
- [ ] **Step 2: implementeren + cache bouwen** (netwerk). Commit: `feat(poc-gent): broncache kaart — VKBO-bedrijfsadressen, OSRM-routes met alternatief, Gent-grens, innames (open data)`.

### Task 2: Kaartberekening in de build (projectie, omleidingen, routekeuze)

**Files:**
- Modify: `simulation/build_simulation.py` (`build_gent` + kaart-helpers)
- Test: `simulation/test_build_gent.py`

**Interfaces:**
- `_projectie(coordinaten, viewbox)` — WGS84→SVG (cos-lat-breedtecorrectie), inclusief bounding-box over grens+routes+zones.
- `_afstand_tot_route(punt, punten)` — punt-tot-segment in meters (equirectulaire benadering, voldoende op stadsniveau).
- `kies_gewenste_route(routes, innames, buffer_m=60)` → `(gewenste_label, omleidingen: [{id, straat, tot}])` — minste innames binnen de buffer; gelijkspel → primair; unit-testbaar met gesynthetiseerde geometrie.
- `zone_kruisingen(punten, zones)` — sampling tegen de echte zone-polygonen (`gis_zones.point_in_ring`) → `{"lez": bool, "autovrij": bool}`.
- `build_gent` levert per kenteken-persona een `kaart`-blok: `{start: {label, coord}, doel: {label, coord}, routes: [{label, gewenst: bool, punten, afstand_m, duur_s}], innames: [{…, opRoute: bool}], zones: {lez, autovrij}, svg: {viewbox, paden: {grens, lez, autovrij, routes[]}, markers}}` — kant-en-klaar voor de template; maria krijgt géén kaart-blok.

- [ ] **Step 1: falende tests** — projectie houdt punten binnen de viewbox; afstand-tot-route klopt op bekende gevallen (punt óp segment → ~0); routekeuze: primair met inname binnen buffer + alternatief schoon → alternatief gewenst mét omleiding-notitie; beide schoon → primair; zone-kruising op echte route sanne (Korenmarkt → LEZ+autovrij `True`); ieder kenteken-persona heeft een kaart-blok met beide routes.
- [ ] **Step 2: implementeren**; suite groen. Commit (scope `simulation`): `feat(simulation): kaartberekening Gent-tab — projectie, omleiding-buffer, door-Gent-gewenste route, zone-kruisingen`.

### Task 3: SVG-kaartpanel in de template

**Files:**
- Modify: `simulation/template.html` (view5: kaartpanel + legenda + omleidingsregels + bronregel)
- Modify: `simulation/verify_static.mjs` (kaartpanel aanwezig; persona-switch ververst de SVG)

**Interfaces:**
- Panel onder de gesprekskaarten (alleen bij `p.kaart`): SVG met gemeentegrens, LEZ/autovrij-vlakken (halftoon), primaire route (blauw), alternatief (grijze stippellijn), gewenste route gemarkeerd (dikker + badge "door Gent aangeraden"), inname-punten (driehoekjes mét id/straat in de tooltip en als regel eronder), start/doel-markers mét label; legenda met alle symbolen; bronregel (OSM/OSRM ODbL · Stad Gent zones Modellicentie · VKBO-open-register · GIPOD-mock, productiepaden BeSt Address/GIPOD-LDES).
- Omleidingsregels: per inname op de niet-gekozen route "omleiding: <straat> (<type>, tot <datum>)"; afstand/duur per route vermeld.
- Verifier: na persona-switch bestaat `#kaart5 svg` (voor kenteken-persona's) en wisselen de route-paden; maria → geen kaart-element.

- [ ] **Step 1: handmatige smoke** — build + `node verify_static.mjs` exit 0 met kaartasserts.
- [ ] **Step 2: implementeren + rebuild**. Commit (scope `simulation`): `feat(simulation): kaartpanel Gent-tab — route, omleidingen, door-Gent-gewenste route uit open data`.

### Task 4: Docsync + zelfcheck

- Modify: `poc-gent/README.md` (kaart-cache-stap `--kaart` + bronnen), eventueel planamendementen.
- Zelfcheck: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` groen; `cd ../simulation && ../nldt/.venv/bin/python build_simulation.py && node verify_static.mjs` groen mét kaart; `python3 eval.py` ongewijzigd GO (kaart raakt de engine niet).

### Nabestelling (gebruikerswensen, zelfde dag)

De eerste oplevering is naar gebruikerswens bijgesteld (commit volgt direct):
1. **Stap-opbouw**: de kaart bouwt zich op met de replay — de basisweergave
   (zones + startlocatie uit de personagegevens) staat er vanaf het begin en
   óók na een reset (vaste constate van de gebruiker: bij reset leek de kaart
   te verdwijnen); vanaf de routing-stap tekenen de routes (met
   tekenanimatie), innames en het doel zich in. De verifier controleert de
   tussenstanden incl. de reset (6 → 6 → ≥15 → 6 openingstags).
2. **Zoom**: bounding box over routes/markers/innames (relatieve marge), niet
   meer de hele gemeente; grens en zones vullen randvullend uit de viewbox.
3. **Layout**: kaartpanel staat náást de agentlog (tweekoloms grid, sticky),
   niet langer eronder.

## Zelfcheck na afronding (executeur)

1. poc-gent-suite groen (143 + kaart-cache-units).
2. Sim-build + verifier groen; het Gent-tabblad toont per kenteken-persona de kaart met beide routes, gemarkeerde gewenste route, innames en zones; maria zonder kaart.
3. `fixtures/source/kaart.json` bevat meta met bronnen/licenties/datums; runs en evaluatie ongewijzigd (engine onaangeroerd).
