# Ontwerp: planning_indicators — gedeelde indicatoren-datasect als globale toolbox-asset

**Datum:** 2026-10-14
**Status:** geïmplementeerd
**Bron:** [ivan-cardenas/DigitalPlanning_Indicators](https://github.com/ivan-cardenas/DigitalPlanning_Indicators)
(gepind op upstream-commit `b81ebfad3c3a3fa6f90ec44cfb95455cc90ba5fa`, 2025-12-04,
release v1.2, DOI [10.5281/zenodo.17464468](https://doi.org/10.5281/zenodo.17464468)).

## 1. Doel

De dataset *Urban Indicators: Drinking Water, Urban Heat, Housing Provision*
(Cardenas-Leon, Nourian, Koeva e.a., ITC Twente) is een relationele
literatuur-datasect: **280 indicatoren** (definitie, eenheid, berekening,
systeemonderdeel) across **3 planningsectoren** (Water Supply, Urban Heat
Stress, Housing Provision), ontsloten via koppeltabellen naar **561
bronpublicaties** (BibTeX + Zotero-ID's), 18 doelstellingen (doelstellingen),
7 topics en 19 systeemonderdelen. Licentie **CC BY-NC-SA 4.0**.

Gevraagd: beschikbaar stellen als **globale, gedeelde asset** voor alle PoC's
— niet als poc-lokale kopie. De drie sectoren vallen samen met de
gebiedsontwikkelingsthema's van PoC-5 (MiniGIM) en zijn contextueel relevant
voor de GWT-twin (PoC-6, grondwater ⇒ water supply); de toolbox-cultuur
(cite-or-abstain, PROV, deterministisch, offline-first) vraagt om een
loader met ingebouwde provenance.

## 2. Alternatieven en keuze

| optie | oordeel |
|---|---|
| **A. git submodule** | versie-pin gratis, maar: netwerk nodig bij fresh clone, sleept 4 MB binary formats (.accdb/.ods/PRISMA-PDF's) mee die geen PoC programmatisch leest, import-pad-hoksvrije bridge ontbreekt. |
| **B. volledige upstream-copy** | zelfde nadelen als A zonder submodule-frictie, maar nog steeds ~4 MB dode formats in de repo. |
| **C. vendor de CSV-kern als top-level package** (gekozen) | ~210 KB gecommit: 10 CSV-tabellen + schema.json + CITATION.cff + LICENSE; stdlib-loader met provenance-constanten; past bij offline-first cultuur (PoC-1/2 draaien zonder netwerk) en bij de bestaande `sys.path.insert(ROOT)`-bridge die PoC's al gebruiken voor gedeelde code. |

## 3. Ontwerp

### 3.1 Globale package `planning_indicators/`

```
planning_indicators/
  __init__.py        publieke API (re-export uit loader)
  loader.py          stdlib-csv loader, joins, provenance, validate()
  dataset/CSV/*.csv  10 upstream-tabellen, byte-identiek vendored
  schema.json        upstream tabel/kolom/PK/FK-spec (verbatim)
  CITATION.cff       upstream citatie-metadata (verbatim)
  LICENSE            upstream CC BY-NC-SA 4.0 (verbatim)
  README.md          wat/waarvandaan/hoe-te-gebruiken per PoC
  tests/test_dataset.py   integriteits-suite (stdlib unittest)
```

**Publieke API** ( allemaal puur stdlib — geen nieuwe dependencies):

- Constanten: `SOURCE_URL`, `UPSTREAM_COMMIT`, `DOI`, `VERSION`, `LICENSE`,
  `AUTHORS`, `CITATION` (afdrukbare citatie-string uit CITATION.cff-velden).
- `load_table(name) -> list[dict]` — logische tabelnaam (`indicators`,
  `main_table`, `paper`, `objective`, `topic`, `planning_sector`,
  `system_parts`, `countries`, `region`, `income_type`); kaart op de echte
  bestandsnamen (schema.json-paden zijn case-anders — upstream-quirk).
- `load_all() -> dict[str, list[dict]]`.
- `indicators() -> list[dict]` — denormalized view: indicator + systeemonderdeel-
  + doelstelling- + topic- + sector-naam uitgejoin’d, FK's als int.
- `papers_for_indicator(indicator_id) -> list[dict]` via `main_table` → `paper`.
- `indicator_papers()` — volledige indicator↔paper-join in één keer.
- `search(query) -> list[dict]` — case-insensitive substring over naam+definitie.
- `strip_html(text)` — upstream-quirk: Paper-titels bevatten HTML
  (`<div>…</div>`); stdlib HTMLParser-gebaseerde cleaner.
- `validate() -> list[str]` — integriteitschecks (PK-uniekheid, FK-integriteit
  per schema.json, kolom-dekking); lege lijst = gezond.

**Bekende upstream-quirks die de loader absorbeert** (documenteert in README,
data blijft verbatim):

- FK-kolommen zijn float-geformatteerd (`"12.0"`) → int-coercie in joins.
- `Indicators.csv` heeft een trailende komma → spookkolom (`None`-restkey) →
  verworpen door de loader.
- `Paper.Title` bevat HTML → `strip_html()` als helper (geen mutatie van data).
- schema.json-paden (`dataset/CSV/countries.csv`) matchen de echte
  bestandsnamen (`Countries.csv`) niet case-gevoelig, en enkele kolomnamen/
  FK's kloppen niet met de CSV (bijv. `research_paper.country_id` bestaat
  niet) → de loader hanteert een eigen expliciete relatiekaart
  (`FOREIGN_KEYS`, `KNOWN_STALE_FKS`); schema.json wordt vendored als
  referentie en door `validate()` gebruikt voor kolom-dekking
  (alfnumeriek-genormaliseerd).

### 3.2 Demonstratie-consumer: PoC-5 tool (additief)

`poc-minigim/tools/indicator_refs.py` — offline CLI-tool die voor een
gekozen sector (`water|heat|housing`, optioneel `--query`) de relevante
literatuurindicatoren + bronpublicaties uit de globale package ophaalt en
naar `runs/indicator-refs/` schrijft als JSON met een prov-blok (DOI,
versie, upstream-commit, licentie, sha256 per gebruikte CSV, tijdstempel).
Additief-only: **niets in de canonieke MiniGIM-run (29/74 delivered etc.)
verandert** — de tool is een referentielens naast de 74-item checklist,
niet een beslislijn-invoer. Test: `poc-minigim/tests/test_indicator_refs.py`.

### 3.3 Waarom géén dataGrounding-koppeling in PoC-1

De V2 `dataGrounding`-check ground scenario-bases met **ruimtelijke
observaties** (CBS-vierkant/landgebruik via PDOK, cache-first fetchers in
`poc/pipeline/national_data.py`). Een literatuurcatalogus is
**kennis-onderbouwing**, geen observatie; die door de V2-gate halen zou het
contract van de pas gekalibreerde gate (plan 2, 2026-10-13/14) verwateren.
Als PoC-1 er later gebruik van wil maken, kan dat als nieuw, expliciet
grounding-soort — buiten scope van dit ontwerp.

## 4. Testen

- `planning_indicators/tests/test_dataset.py` (stdlib unittest, ook onder
  pytest draaiend): alle 10 tabellen laden; rij-aantallen binnen
  verwachte bandbreedte (280 indicatoren, ≥550 papers, ≥1600 koppels);
  PK-uniekheid op elke tabel; FK-integriteit (main_table→indicators,
  main_table→paper, indicators→objective, indicators→system_parts,
  objective→topic, topic→planning_sector, countries→region,
  countries→income_type); join-sanity (`papers_for_indicator` non-leeg voor
  een bekende indicator); provenance-constanten compleet; `strip_html`.
- `poc-minigim/tests/test_indicator_refs.py`: tool-run op fixture-uitvoer
  levert sector-gefilterde indicatoren + prov-blok; deterministisch.
