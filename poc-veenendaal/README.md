# poc-veenendaal — Spoorzone Veenendaal gebiedscheck

Eerste instantie van het [sjabloon gebiedsontwikkeling-PoC](../docs/TEMPLATE_GEBIEDSONTWIKKELING_POC.md):
een deterministische gebiedscheck die het **Toekomstbeeld Spoorzone** (gemeente
Veenendaal, juni 2025) toetsbaar maakt tegen de **huidige stand** uit landelijke
registraties (BAG + BGT via PDOK).

| | |
|---|---|
| Canvas | [`docs/USE_CASE_VEENENDAAL_SPOORZONE.md`](../docs/USE_CASE_VEENENDAAL_SPOORZONE.md) |
| Gebiedsdefinitie + doelen | [`data/gebied.json`](data/gebied.json) (werkgrens, ankers, doelen uit het Toekomstbeeld) |
| Patronen | nLDT Plane A-licht (gebiedscheck) · voeding voor Plane B (varianten) en Plane D (gebiedsafweging) — [`nldt/11`](../nldt/11-poc-patterns-scenarios-qa.md) |
| Doctrine | *AI stelt voor · rekenlaag beslist · mens beslist* ([`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md)) — deze engine is volledig deterministisch, geen LLM in de rekenketen |

## Gebruik

```bash
cd poc-veenendaal
python3 run.py            # cache-first; eerste run haalt ~7 PDOK-collections
python3 run.py --refresh  # forceer herfetch (nieuwe bevraagtijdstippen + sha256)
python3 scenarios.py      # scenario-sweep (Plane B-achtig) → scenario-runs/<ts>-sweep/
nldt/.venv/bin/python zones.py  # deelgebied-uitsnede → sttr-runs/<ts>-zones/
nldt/.venv/bin/python kennisgraaf.py  # kennisgraaf/v1 → sttr-runs/<ts>-kennisgraaf/
```

Uitvoer per run in `runs/<UTC-ts>-gebiedscheck/`: `report.md` (mensleesbaar),
`indicators.json` (machine), `manifest.json` (per bron: URL, parameters,
featureCount, sha256, fetchedAt). Broncache in `data/cache/*.geojson`.

## Scenario-sweep (programmamutaties, Utrechts model)

`scenarios.py` rekent curated programmavarianten deterministisch door tegen de
nulmeting (geen LLM, geen juridische zone-algebra — daarvoor is een IMRO/DSO-track
nodig): **tempo** (150/250/350 woningen per jaar), **bouwvoorkeur**
(nieuwbouw op verhard vs. groen vs. gemengd) en **dichtheid** (grondvlak per
woning 40 m² bij 5-lagen basis / 25 m² bij 15-lagen accenten). Elke variant
krijgt een provenance-basis (`baseline | policy_variant | hypothetical`), een
rationale en expliciete aannames (in `manifest.json`); de uitkomsten
(jaar-van-4.500, uitloop vs 2040, groen/verhard-eindstand, groendoel-uitspraak,
dichtheid) worden gerapporteerd met delta's t.o.v. de control en V3-invarianten.

**Ruimtelijke toedeling + deelgebieden:** de engine wijst het benodigde
grondvlak toe aan hele actuele vlakken (afstand tot het station oplopend,
bij gelijke afstand grootste eerst) en splitst de toedeling per deelgebied op
oppervlakte (`deelgebieden.json`; 7 provisionele zone-polygonen uit
`data/gebied.json` die de werkgrens exact tegelen, Σ zones = toedeling). De
simulatie toont de genomen vlakken op de kaart (amber = verhard → bouw, rood =
groen verdwijnt) en de per-deelgebied-tabel per scenario. Kernbevindingen uit
de canonieke sweep (20261112, polygon-werkgrens): op de gecorrigeerde
zandloper-grens staat het groen al op 25,96 ha — de >30 ha-belofte is een
échte opgave (≈ +4 ha), niet alleen te behouden; bouwen-op-groen daalt verder
naar 7,96 ha (−18 ha); tempo 150/jaar → +10 jaar uitloop (doel pas 2050);
compacte 15-lagen-verdichting neemt 26,4 ha verhard in (−11 ha t.o.v. basis)
en laat de groenvoorraad onaangetast.

## Het loket over de Spoorzone (STTR — officiële toepasbare regels)

`sttr.py` legt de derde kennisbank-laag over het gebied: de officiële toepasbare
regels (STTR/DMN) die het Omgevingsloket aan Veenendaal stelt — **vragen, geen
besluit**. Twee sporen, bewijs-gebonden (kader: [POC_STTR_IMTR_KANSEN](../docs/POC_STTR_IMTR_KANSEN.md)):

- **locatie-gebonden** — de 20 geoVerwijzing-vragen uit de RTR zijn via het
  omgevingsplan-uitwisselpakket (AKN via Presenteren `regelingen/_zoek` op het
  station-anker; pakket via de downloaden-API) níet hard koppelbaar: 18 verwijzen
  naar een leveranciers-identificatiefamilie die niet in het plan zit, 2 naar
  OP-gebieden zonder geometrie in dit pakket — per status eerlijk gerapporteerd.
  Wél wordt het hele pakket gesweept: **27 van 83 officiële GIO-lagen snijden de
  polygon-werkgrens** (2026-11-12; op de oude bbox waren het er 30 — gasleiding-,
  open-landschap- en waterbergingslagen vielen weg met het oost-overschot), o.a.
  regels tijdelijk deel + ecologisch/landschapswaarden (elk exact de hele werkgrens,
  161,6 ha), bebouwingscontour houtkap/jacht (160,8 ha), **boringsvrije zone +
  grondwaterbeschermingszone (90,6 ha — 56% van het gebied; op de oude bbox leek
  dat 60,8 ha: het westelijke deel inclusief 't Franse Gat Noord ligt er ook in)**,
  archeologie mét diepte-/oppervlaktemaxima en beschermde bomen — elk met
  STOP-FRBRWork.
- **programma-gebonden** — 7 bewijs-gebonden koppelingen (spoorlijn in gebied →
  `WegSpoorwegAanleggenWijz`; 4.500 woningen → bouw-activiteiten; bomen/vegetatie
  → `HoutopstandVellen`; …) met de officiële loket-vragen per activiteit eronder
  (bijv. 89 vragen voor bijbehorende bouwwerken, incl. de achtererf-animaties).

```bash
nldt/.venv/bin/python sttr.py               # live: Presenteren + downloaden-API (DSO_API_KEY)
nldt/.venv/bin/python sttr.py --skip-live   # offline: alleen STTR-cache + programma-sporen
nldt/.venv/bin/python sttr_kruising.py      # scenario-toedeling ∩ GIO-lagen (offline, cache)
```

Uitvoer in `sttr-runs/<ts>-loketvragen/` en `sttr-runs/<ts>-kruising/`
(`report.md` · `loketvragen.json`/`kruising.json` · `manifest.json`); caches in
`data/cache/` (gitignored). Canonieke runs: `20261112T210133Z-loketvragen` en
`20261112T210144Z-kruising` (op de polygon-werkgrens). Tests:
`nldt/tests/test_poc_veenendaal_sttr.py`.

**Scenario-kruising** (`sttr_kruising.py`): de sweep wijst per variant hele
BGT-vlakken toe; de kruising snijdt die genomen vlakken met de officiële
GIO-lagen — een **geometrisch feit, geen toets** (raakt ≠ verboden). Kernuitkomsten
canonieke run (polygon-werkgrens): bouw-op-groen raakt **90 beschermde
bomen-objecten** (bouw-op-verhard: 38); de 18,3-ha-verhard-varianten liggen
vrijwel volledig in de **boringsvrije zone + grondwaterbeschermingszone**
(18,34 ha van de toedeling — de spoorzone zit in het grondwaterbeschermingsgebied);
DICHT-15 is overal het zuinigst (24 bomen · 15 monumenten); tempo-varianten delen
de toedeling met BOUW-OP-VERHARD (tempo verandert oppervlak, geen ligging). De hub (tab 6) toont dit als negende stap
"het loket" met een eigen telemetry-kaart — en zes van de GIO-lagen zijn daar
als **klikbare kaart-overlays** opgenomen (tijdelijk deel, ecologisch,
boringsvrije zone, archeologie, beschermde bomen, gemeentelijke monumenten).

## Deelgebied-uitsnede (`zones.py` — "wat ligt en wat geldt er, per deelgebied")

Per deelgebied-zone uit `data/gebied.json` twee kanten in één rapport: de **nulmeting**
(BAG/BGT via de engine uit `run.py`, zelfde zwaartepuntregel) en de **regel-lagen**
(GIO's uit het omgevingsplan-pakket die de zone snijden, met overlap + dekking% —
geometrisch feit, geen toets). V-checken bewaken dat Σ zones ≡ gebiedscheck.
Canonieke run: `sttr-runs/20261112T210519Z-zones/`. Kerninzicht: de
grondwaterbeschermingszone dekt 't Franse Gat Noord, 't Goeie Spoor en het
Stationsgebied volledig (en Het Ambacht voor 46%) — het groen zit juist in de twee
oostelijke zones (Stads- en sportpark 7,6 ha + Overgangszone 9,1 ha = 65% van het
groen), die búiten de grondwaterzone liggen.

## Kennisgraaf/v1 (`kennisgraaf.py` — het DSO-beeld als herbouwbare graaf)

Afgeleide projectie met contract `kennisgraaf/v1`: 380 knopen (gebied · 7 zones ·
regeling · 83 GIO-lagen · 185 RTR-bestanden met geldigheid · 96 activiteiten ·
7 programma-feiten mét bewijs) en 408 relaties (o.a. 118 zone→GIO-overlappingen
met ha+dekking%), alles herleidbaar naar sha256-vaste bronruns. De 20 STTR-
geoVerwijzingen zijn níet hard te leggen aan GIO's — dat staat expliciet als
`koppelgaten` in het contract (géén rtr→gio-edges). Canonieke run:
`sttr-runs/20261112T211256Z-kennisgraaf/`. Tests:
`nldt/tests/test_poc_veenendaal_kennisgraaf.py`.

## Wat de check doet

1. **Werkgrens** uit `data/gebied.json` — provisionele **GeoJSON-polygon**
   (zandloper-vorm, 161,6 ha ≈ de door het Toekomstbeeld genoemde ~160 ha) op
   de assengrenzen uit het document (p.7): de Grift (N) · spoor Utrecht-Rhenen
   (Z-west) · waterlijn Grift-zuidtak (Z-oost) · Rondweg-West (W) · Rondweg-Oost
   (O) · 't Franse Gat Noord als uitzondering ten zuiden van het spoor. Beide
   assen lopen NW-ZO diagonaal; de engine trianguleert de ring (earcut) en
   clipt vlakken per driehoek — exact ook voor concave grenzen. Anker: station
   Veenendaal-Centrum via PDOK Locatieserver.
2. **Ophalen** (cache-first, sha256 + bevraagtijdstip vast): BAG `pand`; BGT
   `begroeidterreindeel` · `onbegroeidterreindeel` · `waterdeel` · `spoorbaandeel` ·
   `vegetatieobject_punt` · `vegetatieobject_vlak`.
3. **Indicatoren huidige stand**: pandenbestand, sloopstatussen, woningen-proxy
   (som `aantal_verblijfsobjecten` op woonfunctie-panden), grondvlak-oppervlak,
   bouwjaar-verdeling incl. realisatie sinds 2020 (programmastart), groen/verhard/
   water/spoor in ha, bomenaantal.
4. **Doelvergelijking** tegen het Toekomstbeeld (±4.500 woningen, >30 ha groen,
   250 woningen/jaar, stedelijke dichtheid).
5. **Poorten**: V0 (structuur) · V1 (vlaktotalen ≤ werkgrens) · V2 (elk getal →
   bron-URL in manifest) · V3 (tweede, onafhankelijke aggregatiepassage over de cache).

## Beperkingen (bewust)

- Werkgrens is een **benadering op assengrenzen** (geen juridische plangrens);
  de officiële gebiedsgrens is niet gepubliceerd. Zodra die er is: vervang de
  polygon in `data/gebied.json` — de engine rekent op wat `gebied.json` biedt
  (GeoJSON-polygon of bbox). De zuid-oostelijke waterlijn en de zuidrand van
  't Franse Gat Noord zijn de zachtste randen (gekalibreerd op ~160 ha, p.7).
- Panden horen bij het gebied als hun **zwaartepunt** binnen de werkgrens ligt.
- Woningen zijn een proxy op pandniveau (panden ≠ woningen).
- Oppervlaktemeetkunde via schoenlac-formule in EPSG:28992 (planair, meters);
  geen shapely-afhankelijkheid (stdlib + requests volstaan; earcut-triangulatie
  voor concave grenzen is een eigen stdlib-poort met som-zelfcheck).

## Vervolg volgens canvas (open)

- ~~Omgevingswet-toets op het gebied (IMRO/GIO via DSO — key-gated, cf. Utrecht-piloot)~~
  — eerste instantie geleverd door `sttr.py` (lokale GIO-lagen + officiële loket-vragen,
  hierboven); verdieping: echte gebiedsgrens, RCE-monumentenlaag, koppeling STTR-vragen ↔ GIO's
  zodra de leveranciers-locatie-identificaties aan het omgevingsplan hangen.
- Ontwerpvarianten als Plane B-scenario's; gebiedsafweging wonen/groen/werken als
  Plane D spatial claims (Breda-patroon).
- ILS/ICDD-afspraken voor ontwerpleveringen (BIM/GEO) conform canvas §11.
