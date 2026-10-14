# planning_indicators — gedeelde indicatoren-datasect (globale toolbox-asset)

Vendored kopie van de **Urban Indicators Dataset: Drinking Water, Urban Heat,
and Housing Provision** (Cardenas-Leon, Nourian, Koeva & Pfeffer, ITC
Twente / [DigitalPlanning_Indicators](https://github.com/ivan-cardenas/DigitalPlanning_Indicators))
als **globale asset voor alle PoC's** — bewust niet poc-lokaal, zodat elke
PoC dezelfde indicatoren, dezelfde bronpublicaties en dezelfde citatie
gebruikt.

| veld | waarde |
|---|---|
| release | v1.2 (`VERSION`) |
| upstream-commit bij vendoring | `b81ebfad3c3a3fa6f90ec44cfb95455cc90ba5fa` (2025-12-04) |
| DOI | [10.5281/zenodo.17464468](https://doi.org/10.5281/zenodo.17464468) |
| licentie | **CC BY-NC-SA 4.0** ([tekst](LICENSE), [CITATION.cff](CITATION.cff)) |
| omvang | 280 indicatoren × 3 sectoren, 560 bronpublicaties, 1608 indicator↔paper-koppels |
| dependencies | geen (puur stdlib, offline-first) |

## Inhoud

```
dataset/CSV/   10 relationele tabellen, byte-identiek aan upstream:
               Indicators (280) · MainTable (koppels) · Paper (560) ·
               Objective (17) · Topic (7) · PlanningSector (3: Water Supply,
               Urban Heat Stress, Housing Provision) · System_Parts (19) ·
               Countries · Region · IncomeType
schema.json    upstream relationeel model (reference; zie quirks)
CITATION.cff   upstream citatie-metadata (verbatim)
LICENSE        CC BY-NC-SA 4.0 (verbatim)
loader.py      stdlib-loader: tabellen, joins, search, validate()
tests/         integriteits-suite (PK/FK/joins/provenance)
```

## Gebruik vanuit een PoC

PoC's bridgen naar de repo-root zoals ze dat al doen voor gedeelde code
(`sys.path.insert(0, ROOT)`), daarna is de package een gewone import:

```python
from planning_indicators import (
    indicators, papers_for_indicator, search, validate, CITATION, DOI, LICENSE,
)

# denormalized view: 280 indicatoren met sector/topic/objective/system-part
for ind in search("heat stress", sector="heat"):
    print(ind["name"], "|", ind["units"], "|", ind["sector"])

# literatuuronderbouwing per indicator (via MainTable → Paper, HTML gestript)
refs = papers_for_indicator(75)   # "Reused water"

# publiceer-artefacten: provenance meesturen (licentie vereist attribution)
prov = {"citation": CITATION, "doi": DOI, "license": LICENSE}
```

Integriteit (ook door de CI-suite gedekt):

```bash
python3 -m unittest planning_indicators.tests.test_dataset
```

## Upstream-quirks (data blijft verbatim; de loader absorbeert)

- FK-kolommen zijn float-geformatteerd (`"12.0"`) → int-coercie in joins.
- `Indicators.csv` eindigt op een komma → spookkolom, door de loader verworpen.
- `Paper.Title` bevat HTML (`<div>…</div>`) → `strip_html()`-helper.
- `schema.json`-paden/kolomnamen matchen de echte bestanden niet case-gevoelig,
  en de `research_paper.country_id`-FK bestaat niet in de CSV (Paper heeft
  `Country` als naam) — `loader.FOREIGN_KEYS` bevat de relaties die *wel*
  daadwerkelijk bestaan; `loader.KNOWN_STALE_FKS` registreert de losse eindjes.

## Gebruik per PoC

- **PoC-5 (poc-minigim)**: `tools/indicator_refs.py` — referentielens die per
  sector de literatuurindicatoren + bronpublicaties als prov-rijk JSON-artefact
  zet naast de 74-item Omgevingsanalyse Lijst (additief; verandert niets aan de
  canonieke run).
- **PoC-6 (poc-rijnland-gwt)**: sector *Water Supply* als kennis-context bij de
  grondwater-trigger-adviezen (nog niet ingevlochten — zelfde additieve patron
  als PoC-5).
- **PoC-1 (poc)**: bewust *niet* gekoppeld aan de V2 `dataGrounding`-gate —
  die groundt op ruimtelijke observaties (CBS/PDOK); een literatuurcatalogus is
  kennis-onderbouwing en vraagt, wil PoC-1 die ooit gebruiken, om een eigen
  expliciet grounding-soort (zie
  [ontwerp-spec](../docs/superpowers/specs/2026-10-14-planning-indicators-design.md)).

## Updaten

Vervang `dataset/CSV/` + `schema.json` + `CITATION.cff` door de nieuwe
upstream-release, pin het nieuwe commit-hash in `loader.UPSTREAM_COMMIT`,
werk `VERSION` bij, en laat `test_rij_aantallen_bij_vendoring` vertellen
welke rij-aantallen zijn verschoven — die worden dan gericht bijgewerkt.
