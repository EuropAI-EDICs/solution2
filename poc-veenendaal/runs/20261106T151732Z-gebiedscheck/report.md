# Gebiedscheck Spoorzone Veenendaal — 20261106T151732Z-gebiedscheck

*Run 2026-11-06T15:17:32Z · engine `poc-veenendaal/run.py` · doctrine: rekenlaag beslist, mens beslist.*

**Brongebiedsdocument:** [Toekomstbeeld Spoorzone, gemeente Veenendaal, juni 2025](https://www.veenendaal.nl/fileadmin/files/Veenendaal/documenten/Projecten/Spoorzone/Toekomstbeeld_Spoorzone.pdf) (geraadpleegd 2026-11-06).

**Werkgrens:** provisorische bbox (benadering, geen juridische plangrens) — bbox RD [165750, 447700, 168050, 448400] (2300×700 m ≈ 161.0 ha). Station als westelijk anker; strook tussen de Grift (N) en spoor Utrecht-Rhenen (Z), van Rondweg-west tot Rondweg-oost (Toekomstbeeld p.7). Afmetingen gekalibreerd op de genoemde oppervlakte van ~160 ha (p.7/p.14). Het werkelijke gebied is zandloper-vormig (projectpagina veenendaal.nl/spoorzone); een bbox is dus een grove benadering.

## Huidige stand (deterministisch uit BAG/BGT; per bron URL+sha256 in `manifest.json`)

| Indicator | Waarde | Bron |
|---|---:|---|
| Panden bestand (excl. gesloopt/niet gerealiseerd) | 2926 | BAG pand |
| — panden met status gesloopt/niet gerealiseerd | 287 | BAG pand |
| Panden met woonfunctie | 1469 | BAG pand |
| Woningen (som verblijfsobjecten op woonpanden; proxy) | 5555 | BAG pand |
| Pand-vloeroppervlak binnen werkgrens (grondvlak, som) | 255.602 m² | BAG pand |
| Panden met bouwjaar ≥ 2020 | 424 | BAG pand |
| Begroeid terrein binnen werkgrens | 32.83 ha | BGT |
| Onbegroeid (verhard) terrein binnen werkgrens | 50.97 ha | BGT |
| Water binnen werkgrens | 10.15 ha | BGT |
| Spoorlijn binnen werkgrens | 1.8 km | BGT |
| Bomen (vegetatieobject punt) | 31 | BGT |
| Vegetatievlak binnen werkgrens | 1.22 ha | BGT |

**Bouwjaar-verdeling (bestaande panden):** <1965: 811 · 1965-1984: 724 · 1985-1999: 229 · 2000-2019: 738 · ≥2020: 424

## Doelvergelijking (toekomstbeeld ↔ gemeten)

| Onderwerp | Doel (Toekomstbeeld) | Stand/kader |
|---|---|---|
| Wonen | ~4500 nieuw (p.14; inleiding p.3 noemt ~4000) | 5555 bestaand (vbo-proxy) → groei ≈ 0.8× |
| Bouwtempo | 250 woningen/jaar sinds 2020 | verwacht tot 2026: ~1500; proxy gerealiseerd: 424 nieuwe pánden (pand ≠ woning, indicatief) |
| Groen | > 30 ha | huidig begroeid terrein: 32.83 ha (+ vegetatievlak 1.22 ha) |
| Werken | ~2500 nieuwe arbeidsplaatsen | arbeidsplaatsen niet rechtstreeks meetbaar in BAG/BGT (open seam: bron met banenregistratie) |
| Dichtheid | stedelijk; basishoogte 5 lagen, accenten 15 | huidig: 3450 woningen/km²; na realisatie: ~6245 |

## Kwaliteitspoorten

- **V0 structuur**: alle responses FeatureCollection; featureCounts per bron in manifest.
- **V1 geometrie-sanity**: geen afwijkingen.
- **V2 bronherleidbaarheid**: elke indicator verwijst naar collection+URL in manifest.json (sha256 vast).
- **V3 herberekening (tweede implementatie over cache)**: PASS — panden 2926 vs 2926; bouwjaar≥2020 424 vs 424; groen 32.83 vs 32.83; vlaktotalen 94.0 ha ≤ werkgrens 161.0 ha (+2%).

## Beperkingen & vervolg

- Werkgrens is een provisionele bbox; het werkelijke gebied is zandloper-vormig — cijfers zijn
  indicatief tot de officiële gebiedsgrens beschikbaar is (open item, USE_CASE Annex B).
- Woningen zijn een proxy (som `aantal_verblijfsobjecten` op panden met woonfunctie); panden ≠ woningen.
- Bouwjaar ≥ 2020 omvat ook vervangingsbouw; geen uitsplitsing sloop/nieuw zonder historische BAG.
- Volgende stap volgens canvas: omgevingswet-toets (DSO/IMRO) en ontwerpvarianten (nLDT Plane B/D).

*Manifest: `manifest.json` · indicatoren: `indicators.json` · cache: `data/cache/`.*