# De rule graph van de Utrecht-PoC: artikel → NormCard → FormalRule → geolaag → zone

Deze pagina legt de kernketen van de PoC ([`poc/`](../poc/)) uit: hoe een
artikel uit de Omgevingsverordening provincie Utrecht stap voor stap een
kaartbare zone wordt, met behoud van volledige juridische traceerbaarheid.
Achtergrond over modulegrenzen en contracten staat in
[`SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md); waar GenAI in het
spel komt staat in [`GENAI_SEAMS.md`](GENAI_SEAMS.md).

De PoC beantwoordt één vraag — *binnen welke zone van de provincie Utrecht zou
een omgevingsplan X kunnen toestaan, en welke juridische normen sluiten daar
uit, voorwaardelijk of compensatoor?* — via een keten van vijf stappen. Elke
stap is een eigen agent met een eigen schema-gevalideerd contract, zodat alles
terug te traceren is. De keten wordt hier doorlopen met het wind-voorbeeld
(kleine windturbines, art. 5.3); de tracks `zon` en `bos` lopen via exact
dezelfde graf.

```text
artikel (CVDR704250)                         Norm Analyst (cite-or-abstain)
  └─> NormCard        NC-W-03               norm-card.schema.json
        └─> FormalRule FR-W-03              Formalizer (expliciete templates)
              └─> geolaag   gebied_kleine_windturbine (agrest IMOW / GIO-alias)
                    └─> zone  inclusion ∪ ... ∩ AOI − exclusies   engine.py
```

## 1. Artikel — de wettekst

De bron is de **Omgevingsverordening provincie Utrecht** (CVDR704250, geldend
sinds 13-10-2025), aangevuld met de Omgevingsvisie 2021. De Norm Analyst draait
een vooraf geverifieerde juridische reconstructie over de artikeltekst volgens
het principe *"cite or abstain"*: zonder geverifieerde citatie geen regel.
Stikstof, windgeluidnormen (Wgh/Bal) en tiphoogtes zijn bewust *geabstineerd*
— die staan in het afzieningen-ledger
[`poc/corpus/normcards-rejected.json`](../poc/corpus/normcards-rejected.json)
(voor zon en bos: `normcards-rejected-<track>.json`).

## 2. NormCard — de normkaart

Elk relevant artikel(onderdeel) wordt één kaart: `NC-W-03` voor art. 5.3 lid 1.
Een NormCard bevat de claim in gewone taal, maar vooral de bewijslast:

- bron: `docId`, `article`, `version`, **letterlijk Nederlands citaat** en de
  URI naar `lokaleregelgeving.overheid.nl`;
- `legalForce` (bindend), `theme`, `confidence`, `verified`;
- `appliesTo`: objecttype (`wind_turbine`) + context-tags
  (bijv. `ashoogte_le_20m`, `on_or_adjacent_to_existing_building_plot`).

Het contract ligt in
[`poc/schemas/norm-card.schema.json`](../poc/schemas/norm-card.schema.json);
de windkaarten in
[`poc/corpus/normcards-wind.json`](../poc/corpus/normcards-wind.json)
(24 stuks). Zonder geverifieerde citatie of met een onondersteunde claim gaat
een kaart naar het afzieningen-ledger — er wordt nooit een regel verzonnen.

## 3. FormalRule — de uitvoerbare regel

De Norm Formalizer vertaalt een kaart óf naar een machine-uitvoerbare regel,
óf naar status `ambiguous`/`rejected` — nooit gegokt. `FR-W-03` krijgt:

- `zoneSemantics: inclusion`. De overige semantieken: `exclusion`,
  `conditional`, `attention` en `compensation` — de laatste drie zijn
  **markers** die nooit oppervlak wegnemen;
- `conditions`: `hub_height <= 20 m` en locatie op/aansluitend bij een
  bestaand bouwperceel;
- een `zoneSelector` met `zoneIds: ["gebied_kleine_windturbine"]`,
  `selection: within`, en de `gioJoinId` van de GIO uit Bijlage II van de
  verordening als formele herkomst;
- `executableRef: engine.zone.within@poc-v1` — de engine-entrypoint die de
  regel uitvoert.

Open normen (procedureel, te onbepaald om te formaliseren) krijgen status
`ambiguous`, **geen** predicates, en worden naar menselijke review
(validatieniveau V4) gerouteerd. Bij wind zijn dat er 13 van de 24 kaarten.
Het contract:
[`poc/schemas/formal-rule.schema.json`](../poc/schemas/formal-rule.schema.json).

## 4. Geolaag — de geo-analist

De Geo Analyst lost de `zoneIds` op via het `ZONE_SOURCES`-register in
[`poc/run.py`](../poc/run.py): elke zone-naam wijst naar een echte, live laag
van de provincie — de *vigerende verordening* als IMOW-laag op de agrest
ArcGIS-service (`WHERE NAAM='Gebied kleine windturbine'`), of nationale lagen
zoals Natura 2000 op de ArcGIS Hub van de provincie. Kenmerken:

- lagen worden **cache-first** opgehaald (cache onder `poc/data/cache/`);
- het manifest `layers.json` legt per laag `lastChecked` vast én dat de laag
  een **provenance-alias** is van de GIO-join-id die op de NormCard geciteerd
  staat (de DSO-download-API bleek sleutel-afgeschermd, HTTP 401 — daarom
  deze omweg via de open provinciedata);
- afgeleide zones ontstaan in de engine zelf, bijv. de 1500 m-buffer rond
  `Stiltegebied` (aandachtsgebied, art. 9.25 lid 2).

Faalt een live laag midden in een run, dan worden de betreffende regels
gedropt en als `needs_human` in het validatierapport gelogd — er wordt nooit
gefantaseerd.

## 5. Zone — de engine en het resultaat

De Zone engine ([`poc/pipeline/engine.py`](../poc/pipeline/engine.py)) voert
de FormalRules deterministisch uit in EPSG:28992:

```text
inclusiezones (∪) ∩ provinciegrens − harde exclusies (Natura 2000,
ganzenrustgebieden, Natuurnetwerk Nederland)
```

De markers (stiltegebied-conditional, 1500 m aandachtsbuffer,
groene-contour-compensatie) blijven als aparte lagen op de kaart staan en
verwijderen nooit oppervlak. Voor de canonieke windrun
(`poc/runs/20260830T113234Z-wind`): AOI 1560,1 km² → inclusie ∩ AOI
1259,8 km² → **finale zone 859,5 km²**.

De Cartographer schrijft het resultaat als `zones.geojson`/`zones.gml`
(QGIS/Tygron) en de Explainer als beslistabel waarin **elke regelrij
teruggelinkt is aan zijn NormCard** — en die NormCard weer aan artikel +
citaat + URL + versie. `prov.json` traceert de hele graf (agents, entiteiten
met sha256, activiteiten per fase, geo-bronnen met `lastChecked`).

## Waarom deze opbouw

De keten is de traceback-keten:

```text
zone → ruleId (FormalRule) → normCardId (NormCard) → artikel + letterlijk citaat + versie + URI
```

Daarmee is elke polygoon op de kaart juridisch onderbouwd én
machine-verifieerbaar. De Critic/Validator controleert per run: V0 syntactisch
(schema's), V1 geografisch, V2 juridische herkomst (citaties, GIO-aliasing),
V3 semantische her-uitvoering via een onafhankelijk geopandas-pad
(IoU ≥ 0,9999); alleen het oordeel over open normen blijft bewust menselijk
(V4).

Dezelfde graf ligt ook ten grondslag aan:

- **scenario-sweep** ([`poc/scenarios/run.py`](../poc/scenarios/run.py)) —
  regel-mutaties op de FormalRules van een basalerun, altijd voorafgegaan
  door een ongemuteerde controle die de baseline moet reproduceren;
- **cross-track conflictoverlay** ([`poc/crosstrack/run.py`](../poc/crosstrack/run.py)) —
  bijv. zon × bos: 94,7% van het zoekgebied nieuwe natuur (Groene contour)
  ligt tegelijk open voor zonnevelden; de art.-6.5a-lid-3-compensatieplicht
  is de enige juridische buffer tussen beide ambities.

Zie ook: de gespiegelde keten van PoC-2 Eindhoven (bronregel → kennisbank →
omzettabel-rij → coverage) in
[`POC_RULE_GRAPH_EINDHOVEN.md`](POC_RULE_GRAPH_EINDHOVEN.md), en de
RegelRecht-integratie (MinBZK) van beide PoC's in
[`POC_REGELRECHT_INTEGRATION.md`](POC_REGELRECHT_INTEGRATION.md).
