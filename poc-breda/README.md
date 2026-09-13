# PoC-4 — Breda vijf-waardenscan (AI in the City 2026)

**Vraag:** waar creeert open data + AI *vandaag al* waarde in gemeente Breda —
per buurt, voor elk van de **vijf waarden** van het congres
[*AI in the City 2026 — Creating Real Value*](https://www.indestad.ai/en/#programme)
(23–25 september 2026, Breda): **democratische, ruimtelijke, economische,
sociale en autonome waarde** — met elk cijfer herleidbaar naar een naamrijke
open bron met retrievedatum, en elke kaartlaag gekoppeld aan een
programmeonderdeel?

Dit is PoC-4 van de LDT-toolbox: het domein *sociaal-ruimtelijke
buurtstatistiek*, met dezelfde deugden als PoC-1/3 (deterministisch,
cite-or-abstain, PROV, offline-testbaar) en een nieuwe datasoort (CBS-statistiek
+ gemeentelijke klimaatlagen).

Design: [`docs/superpowers/specs/2026-09-13-poc4-breda-five-value-scan-design.md`](../docs/superpowers/specs/2026-09-13-poc4-breda-five-value-scan-design.md).

## De vijf waarden → data → programma

| waarde | indicator per buurt (0–100, percentiel binnen Breda) | data | beantwoordt (programma) |
|---|---|---|---|
| Democratisch | voorzieningentoegankelijkheid (gem. afstand tot huisarts, supermarkt, basisschool, kinderdagverblijf, bibliotheek, treinstation) + wijkdeals-aanwezigheid | CBS 2024, `Wijkdeals` (data.breda.nl) | *Residents in the driving seat*; *Demo: Autonomous and democratic* |
| Ruimtelijk | groene ruggegraat: Hoofdgroenstructuur-dekking + afstand tot openbaar groen + bomen per 100 inwoners + kansenkaart-omschrijving | `Hoofdgroenstructuur`, `Bomen`, `Klimaatportaal kansenkaart` (geo.breda.nl), CBS | *Green Spaces and Water as the backbone of the city* (workshop van de gemeente zelf) |
| Economisch | onbenut dakpotentieel ((1−zonnestroom%)×eengezins-aandeel) + bedrijvigheid per km² | CBS 2024 | *AI Walk: Energy savings and impact on infrastructure* (TNO); *Pitches: Economic* |
| Sociaal | hitte-aandacht: % verharding × aandeel 65+ — waar levert klimaatadaptatie de meeste sociale meerwaarde | `Klimaatportaal hitte` (geo.breda.nl), CBS | *Social value*; *Green Spaces and Water* |
| Autonoom | **geen kaartlaag** maar het aantoonbare soevereiniteitsmanifest: 100% publieke bronnen, 0 API-sleutels, 0 vendor-locks, deterministisch, PROV met sha256, geen LLM in de beslislijn | de architectuur zelf | *Sovereignty* (City Deal on AI); *Data sovereignty and -continuity* (KPN); *From European AI strategy…* (LDT CitiVERSE EDIC); *Is your city ready for AI?* (OECD) |

## Run

```bash
# volledige scan (eerste keer: ~2–4 min fetch; daarna cache-first)
nldt/.venv/bin/python poc-breda/run.py

python3 poc-breda/run.py --refresh     # forceer live her-download
python3 poc-breda/run.py --no-bomen    # sla de 117k-boomlaag over
```

Output onder `poc-breda/runs/<ts>-breda-scan/`: **`report.html`** (offline
Leaflet-kaart met waardelaag-switcher + wijkdeals/groen/kansen-overlays,
waardekaarten met programma-citaten, soevereiniteitsmanifest, bronnen,
beperkingen), `value-scan.json` (schema-gevalideerd scan-artifact),
`validation.json` (V0-schema + V1-sanity; exit 0 alleen bij verdict `pass`),
`prov.json`, `layers.json`, `report.md`, `run_summary.json`,
`geo-buurten.wgs84.geojson` / `overlays.wgs84.geojson` (GIS-interop).

## Tests (offline)

```bash
cd poc-breda && ../nldt/.venv/bin/python -m unittest discover -s tests -v
```

## Data & recon-bevindingen (13-9-2026, allemaal sleutelloos)

- **CBS wijken/buurten 2024 WFS** (PDOK): ±400 statistiekvelden per buurt.
  Quirk: `cql_filter` wordt genegeerd; `bbox`+`startIndex` heeft een
  **instabiele sorteervolgorde** (overlappende windows missen features); de
  standaard **OGC-XML `filter`** op `gemeentenaam='Breda'` werkt wél exact.
- **CBS 2024 hanteert voor Breda een grove herindeling: 11 wijken / 56
  buurten, zonder aparte water-buurten** (geverifieerd tegen de wijkenlaag) —
  de volumecheck in de validator is daarop afgestemd (≥ 40).
- **data.breda.nl** is een ArcGIS Hub (org *gemeente-breda*, 69 open services)
  op `services-eu1.arcgis.com`; **geo.breda.nl/server1** host het
  klimaatportaal (hitte/wateroverlast/kansen). Beide: `f=geojson` + `outSR
  28992` + `resultOffset`-paging — dus hergebruikt de PoC de
  ArcGIS-REST-fetcher uit PoC-1 (`poc/pipeline/geodata.py`). Les uit de eerste
  canonieke run: `maxRecordCount` verschilt **per service** (Bomen=1000,
  Wijkdeals=2000, Hoofdgroenstructuur=20000) en te hoog gevraagde pages stoppen
  de GeoJSON-paging stil na één pagina — de fetcher leest de limiet daarom
  live uit de service-metadata (registerwaarde als offline-fallback).
- Sentinels (`< -90000`, CBS-verduistering) worden **nooit** geimputeerd;
  ontbrekende inputs staan per buurt geregistreerd in `validation.json` en in
  de kaart-popup.

## Grounded Q&A over een run (GenAI-seam, S4-analoog)

`qa_run.py` beantwoordt Nederlandse vragen over een canonieke run — *LLMs
propose, deterministic engines dispose* (`docs/GENAI_SEAMS.md`): de vraag wordt
een schema-gevalideerd `ScanQuery`-voorstel (deterministische parser met
cite-or-abstain, of LLM via dezelfde `LDT_SCENARIO_LLM_*`-env als PoC-1), een
deterministische runner leest alleen `value-scan.json`, en de LLM-narratie
moet door de numerieke grounding-gate (elk cijfer resolvet — teken-gevouwen,
volle precisie, Nederlandse duizendtallen; geen buurten buiten de rijen) —
anders afkeuring + deterministische fallback. Gehallucineerde buurten,
vormdrift en onmappbare vragen landen in `query-rejected.json`, nooit in de
runner.

```bash
# deterministisch + offline (standaard)
nldt/.venv/bin/python poc-breda/qa_run.py --run poc-breda/runs/<ts>-breda-scan \
    --question "waarom scoort Belcrum laag op ruimtelijke waarde?"
nldt/.venv/bin/python poc-breda/qa_run.py --run <run> --demo       # golden set
nldt/.venv/bin/python poc-breda/qa_run.py --run <run> --interactive

# met lokale LLM's (Ollama, zelfde env-conventie als PoC-1)
LDT_SCENARIO_LLM_ENDPOINT=http://localhost:11434 LDT_SCENARIO_LLM_API=ollama \
LDT_SCENARIO_LLM_MODEL=qwen3.8:latest \
nldt/.venv/bin/python poc-breda/qa_run.py --run <run> \
    --question "..." --asker llm --narrator llm
```

Uitgang per vraag: `qa/answer.{json,md}` (query, rijen, antwoord,
identiteitsstempel `llm-proposal#<model>` door de seam) of `qa/query-rejected.json`.
Live gevalideerd met qwen3.8 (13-9-2026): vormdrift (`'Belcrum'` in `focus`)
door de schema-gate gevangen, eerlijke onthouding gerespecteerd, en een
Nederlandse narratie met duizendtallen/komma-decimalen geaccepteerd — de
rejection-paden zijn gedemonstreerd én offline getest (73 tests).

## What-if-naad (scenario's over de samenstelling, S7-analoog)

`scenario_run.py` herhaalt eerst een **ongemuteerde control** die de
baseline bit-identiek moet reproduceren; pas dan worden varianten geloofd.
Een scenario is een **contract** (`schemas/value-scenario.schema.json`),
geen prompt: mutaties over de samenstel-parameters (drempels, regels,
gewichten, input-selectie) met verplichte bewijsklasse —
`indicator_variance` · `policy_variant` (alléén de gedocumenteerde
samenstelkeuzes `deals_rule`/`social_rule`) · `hypothetical` (rationale
verplicht).

```bash
nldt/.venv/bin/python poc-breda/scenario_run.py --run poc-breda/runs/<ts>-breda-scan
… --author auto     # deterministische auteur (golden set, 6 voorstellen)
… --author llm      # LDT_SCENARIO_LLM_* (voorstel-only, ledger, naad-stempel)
```

Uitgang `poc-breda/scenario-runs/<ts>-breda-scen/`: `scenario-report.json`
/ `.md` (per scenario: buurten Δ, grootste rangverschuivers; plus
**rank-stabiliteit**: welke buurten top-5/onderste-5 blijven over alle
runs), `run_summary.json`. Canonieke run (auto, 2026-09-13, control
identiek): toegankelijkheidsdrempel 4→6 verandert **niets** (CBS geeft
overal 6/6 afstanden — de indicator is robuust); wijkdeals als
democratische vloer verschuift **alle 56** buurten; groen dubbel tellen en
bomen weglaten verschuiven elk 52 buurten; LLM-auteur (qwen3.8) kreeg 4/4
door na naad-normalisatie van de `'type'`-i.p.v.-`'action'`-alias
(PoC-1-les §5.2) — de voorstellen spiegelen de gouden set: de engine, niet
de auteur, beslist.

## Wat het rapport laat zien (canonieke run)

- `runs/20260913T*-breda-scan/report.html` — start hier.
- Percentielscores zijn **relatief binnen Breda** (0 = laagste, 100 = hoogste
  van de 56 buurten); geen absolute normen, geen Optelbare Stadscore —
  verschillende waarden zijn geen optelsom.
- De **autonome waarde** is bewust geen kaart: soevereiniteit is aantoonbaar
  (manifest met bewijsstukken per criterium), niet claimbaar als cijfer.

## Beperkingen (kort — volledige lijst in elk rapport)

CBS-buurtstatistiek is afgerond/geheimgehouden (kleine buurten → ontbrekende
inputs); klimaatportaal-lagen zijn wijk-/gebiedsniveau (join via
grootste-oppervlakte-overlap); dakpotentieel is een proxy, geen 3D-dakanalyse
(BAG/AHN-variant is vervolgstap); bomenlaag telt alleen gemeentelijk openbaar
groen. H3-cellen, scenario-mutaties en een LLM-seam zitten niet in deze PoC
(YAGNI — zie design).
