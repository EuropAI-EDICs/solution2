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
oppervlakte (`deelgebieden.json`; 7 provisionele zone-vakken uit
`data/gebied.json`, Σ zones = toedeling). De simulatie toont de genomen vlakken
op de kaart (amber = verhard → bouw, rood = groen verdwijnt) en de
per-deelgebied-tabel per scenario. Kernbevindingen uit de canonieke sweep:
tempo 150/jaar → +10 jaar uitloop (doel pas 2050); nieuwbouw op groen wist het
groen in Stationsgebied/Engelenburg West/Het Ambacht volledig (14,8 ha over
gebiedsbreed); compacte 15-lagen-verdichting concentreert zich op
Stationsgebied + Engelenburg West en laat 't Goeie Spoor vrijwel onaangetast.

## Wat de check doet

1. **Werkgrens** uit `data/gebied.json` — provisionele bbox (±161 ha, gekalibreerd
   op de door het Toekomstbeeld genoemde ~160 ha; gebied is in werkelijkheid
   zandloper-vormig). Anker: station Veenendaal-Centrum via PDOK Locatieserver.
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

- Werkgrens is een **benadering**; officiële gebiedsgrens is niet gepubliceerd.
  Zodra die er is: vervang de bbox in `data/gebied.json` door een GeoJSON-polygon
  met bronvermelding — de engine rekent op wat `gebied.json` biedt.
- Woningen zijn een proxy op pandniveau (panden ≠ woningen).
- Oppervlaktemeetkunde via schoenlac-formule in EPSG:28992 (planair, meters);
  geen shapely-afhankelijkheid (stdlib + requests volstaan).

## Vervolg volgens canvas (open)

- Omgevingswet-toets op het gebied (IMRO/GIO via DSO — key-gated, cf. Utrecht-piloot).
- Ontwerpvarianten als Plane B-scenario's; gebiedsafweging wonen/groen/werken als
  Plane D spatial claims (Breda-patroon).
- ILS/ICDD-afspraken voor ontwerpleveringen (BIM/GEO) conform canvas §11.
