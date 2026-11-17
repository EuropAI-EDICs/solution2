# Gebiedscheck Spoorzone Veenendaal — 20261116T082448Z-gebiedscheck

*Run 2026-11-16T08:24:48Z · engine `poc-veenendaal/run.py` · doctrine: rekenlaag beslist, mens beslist.*

**Brongebiedsdocument:** [Toekomstbeeld Spoorzone, gemeente Veenendaal, juni 2025](https://www.veenendaal.nl/fileadmin/files/Veenendaal/documenten/Projecten/Spoorzone/Toekomstbeeld_Spoorzone.pdf) (geraadpleegd 2026-11-06).

**Werkgrens:** provisionele polygon op de assengrenzen uit het Toekomstbeeld (zandloper-vorm; geen juridische plangrens) — GeoJSON-polygon RD (39 hoekpunten, 1 ring, ≈161.6 ha; fetch-venster bbox [165340, 447490, 167820, 448950]). Toekomstbeeld p.7: gebied tussen Rondweg-west en Rondweg-oost, van de Grift (N) tot het spoor Utrecht-Rhenen (Z), met 't Franse Gat noord als uitzondering ten zuiden van het spoor; 't Goeie Spoor omschreven als 'gebied tussen de Grift en het spoor' (p.10). Spoorlijn en Grift lopen bij Veenendaal NW-ZO diagonaal (geverifieerd 2026-11-11 tegen BGT spoor, OSM-watergang + BAG openbareruimte 'Grift', PDOK Locatieserver); de zandloper knijpt bij het station (~250 m loodrecht) en verbreedt naar west (~350 m) en oost. Zuidgrens volgt het spoor tot x≈166.290 (waar het spoor naar het ZO afbuigt) en daarna de waterlijn ten zuiden van Het Ambacht/Overgangszone. 't Franse Gat Noord: strook ten zuiden van het spoor tot de wijklijn (y≈447.900). Som = 161,6 ha ≈ 'ongeveer 160 hectare' (p.7). Eerdere werkgrens (bbox 2.300×700 m, tot x=168.050) liep voorbij Rondweg-oost en miste het westelijke deel inclusief 't Franse Gat Noord — gecorrigeerd na kaartcheck p.7/p.10-11 (opdracht 2026-11-11).

## Huidige stand (deterministisch uit BAG/BGT; per bron URL+sha256 in `manifest.json`)

| Indicator | Waarde | Bron |
|---|---:|---|
| Panden bestand (excl. gesloopt/niet gerealiseerd) | 3103 | BAG pand |
| — panden met status gesloopt/niet gerealiseerd | 969 | BAG pand |
| Panden met woonfunctie | 1435 | BAG pand |
| Woningen (som verblijfsobjecten op woonpanden; proxy) | 4557 | BAG pand |
| Pand-vloeroppervlak binnen werkgrens (grondvlak, som) | 248.973 m² | BAG pand |
| Panden met bouwjaar ≥ 2020 | 323 | BAG pand |
| Begroeid terrein binnen werkgrens | 25.96 ha | BGT |
| Onbegroeid (verhard) terrein binnen werkgrens | 37.69 ha | BGT |
| Water binnen werkgrens | 10.34 ha | BGT |
| Spoorlijn binnen werkgrens | 1.8 km | BGT |
| Bomen (vegetatieobject punt) | 17 | BGT |
| Vegetatievlak binnen werkgrens | 0.85 ha | BGT |

**Bouwjaar-verdeling (bestaande panden):** <1965: 1529 · 1965-1984: 643 · 1985-1999: 216 · 2000-2019: 392 · ≥2020: 323

## Doelvergelijking (toekomstbeeld ↔ gemeten)

| Onderwerp | Doel (Toekomstbeeld) | Stand/kader |
|---|---|---|
| Wonen | ~4500 nieuw (p.14; inleiding p.3 noemt ~4000) | 4557 bestaand (vbo-proxy) → groei ≈ 1.0× |
| Bouwtempo | 250 woningen/jaar sinds 2020 | verwacht tot 2026: ~1500; proxy gerealiseerd: 323 nieuwe pánden (pand ≠ woning, indicatief) |
| Groen | > 30 ha | huidig begroeid terrein: 25.96 ha (+ vegetatievlak 0.85 ha) |
| Werken | ~2500 nieuwe arbeidsplaatsen | arbeidsplaatsen niet rechtstreeks meetbaar in BAG/BGT (open seam: bron met banenregistratie) |
| Dichtheid | stedelijk; basishoogte 5 lagen, accenten 15 | huidig: 2819 woningen/km²; na realisatie: ~5604 |

## Kwaliteitspoorten

- **V0 structuur**: alle responses FeatureCollection; featureCounts per bron in manifest.
- **V1 geometrie-sanity**: geen afwijkingen.
- **V2 bronherleidbaarheid**: elke indicator verwijst naar collection+URL in manifest.json (sha256 vast).
- **V3 herberekening (tweede implementatie over cache)**: PASS — panden 3103 vs 3103; bouwjaar≥2020 323 vs 323; groen 25.96 vs 25.96; vlaktotalen 74.0 ha ≤ werkgrens 161.6 ha (+2%).

## Beperkingen & vervolg

- Werkgrens is een provisionele polygon op de assengrenzen uit het Toekomstbeeld
  (Grift/spoor/Rondwegen; zandloper-vorm) — geen juridische plangrens; cijfers zijn
  indicatief tot de officiële gebiedsgrens beschikbaar is (open item, USE_CASE Annex B).
- Panden horen bij het gebied als hun zwaartepunt binnen de werkgrens ligt;
  panden die de rand snijden tellen dus niet mee.
- Woningen zijn een proxy (som `aantal_verblijfsobjecten` op panden met woonfunctie); panden ≠ woningen.
- Bouwjaar ≥ 2020 omvat ook vervangingsbouw; geen uitsplitsing sloop/nieuw zonder historische BAG.
- Volgende stap volgens canvas: omgevingswet-toets (DSO/IMRO) en ontwerpvarianten (nLDT Plane B/D).

*Manifest: `manifest.json` · indicatoren: `indicators.json` · cache: `data/cache/`.*