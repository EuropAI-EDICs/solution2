# PoC-5 — MiniGIM gebiedscheck (Lijst + ILS draft)

**Vraag:** hoe ver kom je met *uitsluitend sleutelloze open data* bij het
automatisch invullen van de [MiniGIM](https://minigim.nl/)-methodiek voor
gebiedsontwikkelaars — de **Omgevingsanalyse Lijst v0.91** (74 checklist-items:
thema × onderdeel × item, met bronregistratie, prioriteit en risico) en de
**ILS v0.8 "Input Grex"** (gebiedsindeling in niveaus 0–3 met IfcExportAs en
EPset_minigim-eigenschappen)?

Dit is PoC-5 van de LDT-toolbox, pilot op **Breda — plangrens Teteringen**
(CBS-buurt BU07581000, 335,2 ha); Eindhoven is gedocumenteerd als vervolg.
Zelfde deugden als PoC-1..4: deterministisch, cache-first,
cite-or-abstain, PROV met sha256, 0 API-sleutels, geen LLM in de beslislijn,
V0–V3-validatie met V4 (mens) pending by design.

Scope-fase 1: **Lijst + ILS draft** (geen IFC-export, geen GREX-financiën —
zie `docs/MINIGIM.md` voor de fase-2-haken).

## Wat de run oplevert (pilot 21-9-2026, verdict `pass`)

| artifact | inhoud |
|---|---|
| `report.html` | alles-in-één rapport: checklist per thema, ILS-draft-tabel, kaart (offline leesbare tabellen; Leaflet via CDN) |
| `omgevingsanalyse.json` | alle 74 Lijst-items met `deliveredStatus` (29 delivered / 45 manual-action), waarden, risicovlaggen en prov per item |
| `ils-draft.json` + `ils-draft.features.28992.geojson` | draft-gebiedsindeling: wegen → *Openbaar > Verhard > wegen* (IFCROAD), water (IFCSITE), groen, verhard onbegroeid terrein, brug (IFCBRIDGE), percelen → *kandidaat-uitgeefbaar* (IFCSITE/IFCSLAB), panden → *Percelen > Bebouwd* (IFCBuilding); incl. `epsetMinigim` per feature |
| `validation.json` | V0 (schema's) / V1 (geometrie) / V2 (bron-gronding) / V3 (replay-determinisme) — exit 0 alleen bij `pass` |
| `prov.json` | gepinde register-sha256's + per bronlaag fetch-manifesten (url's, pagina's, sha256) |
| `layers/` | geclipte bronlagen per checklist-item (EPSG:28992) |

Kerncijfers pilot: 29/74 automatisch geleverd, 45 expliciet `manual-action`
(nooit gefaked), hoog-prioriteit-auto 3/11 — de ontbrekende hoog-prioritaire
items (hoogte, bodem, grondwater, verontreiniging, kabels/leidingen,
bestemmingsplan) krijgen elk een `manualPointer` naar de bevoegde bron.

## Run

```bash
# pilot-plangrens (eerste keer ±3–5 min fetch; daarna cache-first <10 s)
nldt/.venv/bin/python poc-minigim/run.py \
  --aoi poc-minigim/examples/plangrens-breda-teteringen.28992.geojson \
  --label "Breda Teteringen (pilot)"

# eigen plangrens: elke geldige GeoJSON (EPSG:28992 of WGS84) werkt
nldt/.venv/bin/python poc-minigim/run.py --aoi mijn-plangrens.geojson --refresh
```

Via nLDT (replay/execute + PROV + HITL):

```bash
PYTHONPATH=nldt nldt/.venv/bin/python -c "
from services.process_adapter.poc_handlers import execute_minigim_gebiedscheck_run
print(execute_minigim_gebiedscheck_run({'mode': 'replay'}))"
```

Beide transports van het geregistreerde model bewijzen (replay + catalog-check):

    cd poc-minigim && PYTHONPATH=$PWD/../nldt ../nldt/.venv/bin/python tools/verify_transports.py

De generieke mechaniek (fetch, derivaties, binding-executor) staat sinds M2 in
[`poc-fundament/`](../poc-fundament/README.md); deze PoC levert de MiniGIM-bindings,
de proxy-ops en de rapportage. Het bewijs dat de migratie niets veranderde:
`tests/test_golden.py` (canonisch identiek t.o.v. de pre-refactor golden).

## Tests (offline, geen netwerk)

```bash
cd poc-minigim && ../nldt/.venv/bin/python -m unittest discover -s tests
# converter-e2e (vereist openpyxl):
cd poc-minigim && python3 -m unittest tests.test_convert
```

## Literatuur-indicatoren (referentielens, additief)

Naast de 74-item Lijst kan per sector een literatuurreferentielens uit de
globale datasect [`planning_indicators/`](../planning_indicators/README.md)
(Urban Indicators: Drinking Water · Urban Heat · Housing Provision, ITC
Twente, v1.2, CC BY-NC-SA) worden gegenereerd — elk indicator met definitie,
eenheid, berekening en de bronpublicaties waaruit hij is geëxtraheerd,
inclusief prov (DOI, upstream-commit, sha256 per CSV):

```bash
python3 poc-minigim/tools/indicator_refs.py --sector heat   # water|heat|housing
# → runs/indicator-refs/indicator-refs-heat.json
```

Additief-only: raakt de canonieke run-artefacten niet aan.

## Bronregisters (recon 21-9-2026, allemaal sleutelloos)

- Gepinde snapshots: `sources/MiniGIM-omgevingsanalyse-lijst-v0.91.xlsx` en
  `sources/MiniGIM-ILS-v0.8.xlsx` (sha256 in `registry/*.json`); de machine-
  leesbare registries worden gegenereerd door `tools/convert_minigim_xlsx.py`
  (systeem-python3 + openpyxl) en gevalideerd tegen `schemas/*.schema.json`.
- **PDOK OGC API** (BGT-objecten, BRK-percelen, Natura 2000, NWB-wegvakken,
  RCE-punten): paginering uitsluitend via de ondoorzichtige cursor in de
  server-`next`-link — `offset`/`startIndex` worden afgewezen (recon-21-9).
- **PDOK WFS** (BAG pand/vbo, CBS wijken-buurten 2024): OGC-XML-filter
  URL-encoded meesturen (CBS CQL-filter faalt op spaties).
- **BGT levert historische objecten mee** (`eind_registratie` gevuld): de
  runner filtert die client-side weg en rapporteert
  `historicalObjectsFiltered`.
- **Gemeente Breda AGOL/MapServer** (milieuzones, geluidcontouren,
  cultuurhistorie, archeologiebeleid): `where=1=1` + client-side clip;
  geo.breda.nl MapServer ondersteunt géén paginering (cap ~1000 features) —
  gemarkeerd met `layerCapped`.

## Beperkingen & eerlijkheid

- Niveau-0 classificatie (uitgeefbaar/mandelig/openbaar) beschrijft de
  **huidige** situatie; de definitieve gebiedsindeling is ontwerpkeuze →
  `draft: true`, `v4: pending`.
- "Van wie was je?" (eigendom) is wettelijk geen open data → expliciet `null`
  met toelichting in `epsetNote`.
- Onverhard/erf/zand-onbegroeid terrein past niet in ILS v0.8 → expliciet in
  `unassigned` met oppervlakte, niet stiekem weggemapt.
- CBS-cijfers zijn buurtniveau, oppervlaktegewogen naar de plangrens
  (`proxyNote` per item).

## Structuur

```
poc-minigim/
├── sources/          gepinde MiniGIM-xlsx'en (v0.91 Lijst, v0.8 ILS)
├── tools/            convert_minigim_xlsx.py (build-time, openpyxl),
│                     indicator_refs.py (literatuurlens, planning_indicators)
├── registry/         gegenereerde registries + lijst-bindings.json (74/74)
├── schemas/          5 JSON-schema's (registers, bindings, artefacten)
├── data/             sources.json (11 bronnen + quirks), probe-script + bewijs
├── examples/         plangrens-breda-teteringen.28992.geojson (pilot-AOI)
├── minigim/          package: PoC-specifieke laag op poc-fundament
│                     (registry = TaskRegistry-subclass, checklist = BindingExecutor-
│                     subclass + proxy-ops, fetch = compat-shim, ils, report, validate)
├── fase-manifest.json  agent–fase–tool matrix (gegenereerd: tools/gen_fase_manifest.py)
├── modelregister.json  computation-modellen + transports (processes/a2a/in-process,
│                       riskLevel, versie-pinnen) — bewijs: tests/test_modelregister.py
├── tests/            offline unittest-suite (stub-fetch, deterministisch)
└── run.py            orchestrator (runs/<ts>-minigim-gebiedscheck/)
```

Methodiek-mapping en fase-2 (IFC-export, GREX-financiën): zie
[`docs/MINIGIM.md`](../docs/MINIGIM.md).
