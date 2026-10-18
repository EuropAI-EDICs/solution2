# LDT Toolbox PoC — "Waar kan ik wat?" in provincie Utrecht (wind · zon · bos · water · bodem · mobiliteit · landschap · landbouw · wonen · werken · recreatie · biomassa · energietoets)

Spec: [`docs/superpowers/specs/2026-10-18-utrecht-nspd-refactor-design.md`](../docs/superpowers/specs/2026-10-18-utrecht-nspd-refactor-design.md) ·
Plan: [`docs/superpowers/plans/2026-10-18-utrecht-nspd-refactor.md`](../docs/superpowers/plans/2026-10-18-utrecht-nspd-refactor.md) ·
Architectuur: [`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md), [`docs/SOLUTIONS_ARCHITECTURE.md`](../docs/SOLUTIONS_ARCHITECTURE.md),
GenAI-naden: [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md)

Voor **dertien objecttypen** (tracks) beantwoordt één deterministische pipeline dezelfde
herleidbare vraag voor provincie Utrecht (NL, **programmeerfase** van het beleid):
*binnen welke zone van de provincie kan een omgevingsplan X toestaan, en welke
juridische normen sluiten daar uit, voorwaardelijk of compensatieplichtig* — elke
claim letterlijk geciteerd (instrument + artikel + versie + verbatim citaat + URL),
elk artefact schema-gevalideerd en provenance-gedragen; vijf uitdagingen dekken de
dertien tracks met elk 3 scenario's per track, waarvan elke mutatie (V2) gegrond is
tegen de baseline-run.

**Status: NSPD-refactor fase 1–3 afgerond.** Tracks zijn declaratief
([`poc/tracks/`](tracks/wind.json), loader `pipeline/track_config.py`; corpus-
regeneratie bewaakt door een byte-identiek-corpus-gate in `tests/test_track_config.py`),
de geo-registry is v2.0 ([`data/sources.json`](data/sources.json): `fetchPolicy` +
`provenance` per bron; probe-bewijs 2026-10-18: 47/48 gebruikte bronnen bereikbaar) en
de sweep kent de `add_zone_rule`-mutatie met V2-gate (twee data-gegronde what-if-sets).
Fase 4 = deze README + prompt-verwijzingen. `poc-nspd/` (grensoverschrijdend port)
is een eigen PoC onder hetzelfde contractpatroon.

## Tracks (waar kan ik wat?)

| track | use case | kernvraag | canonieke run |
|---|---|---|---|
| `wind` | windturbines | waar kunnen turbines ≥3 MW / ≤20 m mast staan? | `runs/20260830T113234Z-wind` — 859.463 km² |
| `zon` | zonnevelden | waar kunnen grond/water-gebonden zonnevelden? | `runs/20260830T142439Z-zon` — 1167.936 km² |
| `bos` | nieuwe natuur / bosaanplant | waar is het zoekgebied nieuwe natuur? | `runs/20260830T142446Z-bos` — 23.924 km² |
| `water` | oeverontwikkeling (watersysteem) | waar begrensen de watersysteem-instructieregels oeverontwikkeling? | `runs/20261004T185116Z-water` — 1554.906 km² |
| `bodem` | bodemactiviteit | waar begrenst de grondwaterbescherming bodemactiviteiten? | `runs/20261004T185509Z-bodem` — 858.927 km² |
| `mobiliteit` | weggebonden ontwikkeling | waar begrensen de mobiliteits-instructieregels ontwikkeling? | `runs/20261005T072839Z-mobiliteit` — 1560.054 km² (all-marker) |
| `landschap` | landschappelijke ingreep | waar begrenzen erfgoed-/landschapsregels ingrepen? | `runs/20261005T070621Z-landschap` — 1425.959 km² |
| `landbouw` | landbouwuitbreiding (incl. glastuinbouw, veenbodembewerking) | waar begrensen de landbouw-instructieregels uitbreiding? | `runs/20261005T094244Z-landbouw` — 2.260 km² |
| `wonen` | woningbouw | waar is woningbouw mogelijk onder de wonen-instructieregels? | `runs/20261005T100258Z-wonen` — 1142.990 km² |
| `werken` | bedrijfsontwikkeling | waar kan kantoor-/detailhandel-/bedrijventerreinontwikkeling? | `runs/20261006T121921Z-werken` — 1017.614 km² |
| `recreatie` | dagrecreatie | waar is dagrecreatie-ontwikkeling mogelijk? | `runs/20261006T114934Z-recreatie` — 186.618 km² |
| `biomassa` | energie uit biomassa | waar kunnen biomassa-installaties (arts. 5.6/5.7)? | `runs/20261006T120133Z-biomassa` — 1560.054 km² (all-marker) |
| `energietoets` | netbelasting (afdeling 5.3) | waar voorwaarden voor netbelastende functies (arts. 5.10/5.11)? | `runs/20261006T171730Z-energietoets` — 1560.054 km² (all-marker) |

Wat de getallen inhoudelijk betekenen (inclusion-compositie, harde exclusies,
conditionele/attention/compensatie-markers, open normen naar V4) staat **declaratief
per track** in [`poc/tracks/<track>.json`](tracks/wind.json) (`headlineNote` +
`limitationsTemplate`) en in het rapport van elke run — niet langer als proza hier.
Grondslag: de **Omgevingsverordening provincie Utrecht** (CVDR704250, geldend
13-10-2025) en de **Omgevingsvisie 2021**, plus de open geo-data van de provincie.

## Uitdagingen (5 uitdagingen × 13 tracks × 3 scenario's)

Het curation-contract staat in
[`poc/scenarios/uitdagingen.json`](scenarios/uitdagingen.json) (getest in
`tests/test_uitdagingen.py`); de featured run-ids per track in `::scenarioRuns`
(alle 13 vers, 2026-10-13/14).

| uitdaging | tracks | per track 3 scenario's, o.a. (Δ vs control) |
|---|---|---|
| Energietransitie | wind, zon, biomassa, energietoets | NNN-uitzondering +322,5 km²; zon Natura-carve verwaarloosbaar (+0,01 km²); biomassa-vestigingsgebied landelijk hard −1245,8 km²; energietoets is ruimtelijk blind (−100 % bij handhaving) |
| Wonen & Werken | wonen, werken | alleen-stedelijk-tegenbeelden (wonen −828,7 km², werken −703,4 km²); detailhandel-verbod over het hele object (WN-03-les als variant, −1007,8 km²) |
| Water & Bodem | water, bodem | overstroombaar gebied hard −1202,1 km²; grondwaterbeschermingsversoepeling +701,1 km² |
| Landschap & Infrastructuur | landschap, mobiliteit | CHS hard −780,7 km²; luchtvaartverbod zonder activity-scope −1014,5 km² |
| Landelijk Gebied & Natuur | bos, landbouw, recreatie | glastuinbouw-tegenbeeld +1121,6 km²; bos-zoekgebied in een 1 km-band +371,5 km² (16,5×); alleen bovenlokale dagrecreatie −104,9 km² |

Elke track toont drie beleidsknoppen: een gedocumenteerde keuze omgedraaid
(`policy_variant`), een geciteerde parameter gevarieerd (`norm_variance`) en een
expliciet niet-juridisch tegenbeeld (`hypothetical`).

## Bronnen (registry v2.0)

[`data/sources.json`](data/sources.json) registreert **122 geo-bronnen** met rol,
`fetchPolicy` (51× `cache` / 71× `service`), query-sjabloon (outSR=28992),
`lastChecked` en `provenance` (`pinned`-datum + evidence-bestand: 86× 2026-08-30,
36× 2026-10-04/05/06). Rollen: 59 exclusion · 22 context · 20 conditional ·
17 inclusion · 3 aoi · 1 scenario-basis. Context- en scenario-basis-bronnen zijn
**nooit** zone-bepalend (`ZONE_CAPABLE_ROLES` in `pipeline/scenarios.py`).

| cluster | # | rollen | fetchPolicy | voorbeelden |
|---|---|---|---|---|
| `agrest-ov-*` — OV-IMOW-zone-aliassen | 46 | 10 inclusion · 20 conditional · 15 exclusion · 1 context | 45× cache | `gebied-windenergie`, `gebied-zonneveld`, `grondwaterbeschermingszone`, `unesco-werelderfgoed-*-limes` |
| `agrest-{energie,visie,uplg}-*` | 6 | 3 inclusion · 3 context | service | `agrest-visie-wind`, `agrest-energie-gebieden-windenergie` |
| `arcgis-{harde,complexe}-belemmeringen-*` | 23 | exclusion | service | Hub-belemmeringen uit de wind-alternatieven |
| `arcgis-*` overig (Hub) | 38 | 20 exclusion · 11 context · 4 inclusion · 3 aoi | 1× cache, rest service | `arcgis-natura2000`, `arcgis-nnn-jun2024`, `arcgis-stilte-*`, `arcgis-provinciegrens` |
| landelijk (CBS/RCE/RWS/ProRail/DINO/PDOK/netbeheerder) | 9 | 8 context · 1 scenario-basis | 5× cache | `cbs-grid-kerncijfers-100m`, `rce-monumenten`, `prorail-spoor`, `netbeheerder-netcongestie` |

Probe (lees-only, `data/probe_sources.py` → `data/probe-sources-2026-10-18.json`):
alle 48 gebruikte bronnen (voorkomend in een `layers.json`-manifest of rol
scenario-basis) live geteld; 47 bereikbaar — de 48e is de request-AOI, geen dienst.

## Run it

Vereist: `python3` (≥ 3.13) met `shapely`, `pyproj`, `geopandas`, `requests`,
`jinja2`, `jsonschema`; `ogr2ogr` optioneel (GML-export degradeert zonder).
Geen API-keys; exit 0 alléén bij pipeline-verdict `pass`.

```bash
python3 poc/run.py                     # wind, cache-first; --out <dir> voor vaste doelmap
python3 poc/run.py --use-case zon      # idem voor zon/bos/water/bodem/mobiliteit/landschap/
                                       #   landbouw/wonen/werken/recreatie/biomassa/energietoets
python3 poc/run.py --refresh           # forceer live her-download van elke laag
python3 poc/run.py --bbox 130000,440000,160000,470000   # optionele EPSG:28992-clip
cd poc && python3 -m pytest tests -q          # offline suite (376 tests, fixtures)
python3 -m pytest tests -m golden -q          # golden-regressie: 13 canonieke tracks vs
                                              #   frozen goldens (pipeline/golden.py) — draai
                                              #   vóór het committen van prompt/model-wijzigingen
python3 -m pytest tests -m llm -q             # LLM-seam-comparators (LDT_NORM_LLM_ENDPOINT
                                              #   resp. LDT_SCENARIO_LLM_ENDPOINT)
```

## Architectuur

`run.py` is de orchestrator (plan §3.2, agent #1): één proces, geen LLM at
runtime — elke "agent" is een deterministische implementatie achter het
agent-interface, met propose-only LLM-benen achter gegate naden (S1/S2,
`pipeline/norm_llm.py`; transport `pipeline/llm_transport.py`).

```
use-cases/<track>.json   tracks/<track>.json   corpus/evidence-<track>.json
        │                 (declaratiever)              │
        ▼                        ▼                     ▼
┌────────────────────────────────────────────────────────────────┐
│ run.py                                                          │  runs/<ts>-<track>/
│  intake → NormAnalyst (cite-or-abstain, deterministische replay)│   ├ request.json, normcards.json,
│  → NormFormalizer (templates; ambige kaarten nooit gokken)      │   │ normcards-rejected.json
│  → GeoAnalyst (ArcGIS REST, beide provincie-dialecten, cache)   │   ├ formalrules.json, layers.json
│  → zone-engine (inclusion ∪ ∩ AOI − exclusions; markers nooit)  │   ├ zones.json/.geojson/.gml, rule-stats.json
│  → Cartographer (RFC 7946 + GML 3.2) → Critic V0–V4             │   ├ validation.json + validation/*.json
│  → Explainer (decision-table + PROV-O) → HTML-rapport           │   ├ decision-table.{json,md}, prov.json
│  → run_summary.json                                             │   └ report.html, run_summary.json
└────────────────────────────────────────────────────────────────┘
        │  baseline-run (zones + formalrules, cached layers, tunings)
        ▼
┌────────────────────────────────────────────────────────────────┐
│ scenarios/run.py — sweep over de baseline                      │  scenario-runs/<ts>-<track>-scen/
│  control eerst (V3: reproduceert baseline ≤ 0,1 %) → mutaties  │   ├ scenario-report.{json,md}, scenarios/*.geojson
│  drop · set_semantics · set_buffer_distance_m · add_zone_rule  │   ├ validation.json, prov.json, run_summary.json
│  (V2-gate) — critic V0–V3, V4 bewust pending                   │   └ proposals*.json, scenario-narrative.md
└────────────────────────────────────────────────────────────────┘
        │  per-track zones (controls, offline)
        ▼
┌────────────────────────────────────────────────────────────────┐
│ crosstrack/run.py — paarsgewijze conflict-overlay               │  crosstrack-runs/<ts>-wzb-xtrack/
│  geen juridische claim toegevoegd/gewijzigd (V2 not_applicable)│   ├ crosstrack-report.{json,md}, conflicts/,
│  H3-hexlagen via nldt h3-* (pipeline/h3step.py)                │   │ shared/, controls/, h3-*
└────────────────────────────────────────────────────────────────┘   └ validation.json, prov.json
```

De zes agent-contracten staan in `poc/schemas/*.schema.json` (draft 2020-12):
`opportunity-map-request`, `norm-card`, `formal-rule`, `zone-result`,
`validation-report`, `decision-table` — plus `scenario-spec` voor de sweep.
Elk artefact dat een fase-grens overgaat wordt tegen zijn schema gevalideerd:
dat is de V0-gate, onafhankelijk herhaald door de Critic (V1 geometrie,
V2 juridische gegrondheid, V3 semantische her-executie via een aparte
geopandas-pad, V4 altijd pending/HITL).

Een run-map lees je zo: `report.html` (startpunt, werkt vanaf `file://`),
`run_summary.json` (headline, tunings, degradations, sha256's),
`decision-table.md` (herleidbaarheid: elke rij linkt een NormCard),
`zones.geojson`/`zones.gml` (GIS-interop), `validation.json` (zes
ValidationReports V0–V4), `prov.json` (agenten, entiteiten, activiteiten,
`hadPrimarySource` per laag), plus de tussenliggende grenzen (`layers.json`,
`normcards*.json`, `formalrules.json`), elk schema-valide.

## Scenario's en what-ifs

Een scenario is een **contract** ([`schemas/scenario-spec.schema.json`](schemas/scenario-spec.schema.json)),
geen prompt: een geordende lijst mutaties over de FormalRules van een baseline-run,
elk met een provenance-`basis` (`norm_variance` / `policy_variant` / `hypothetical`
met verplichte `rationale`). De sweep her-executeert altijd eerst een ongemuteerde
**control** (V3 ≤ 0,1 %), replayt de lagen offline op de opgenomen tunings en gate't
op een scenario-critic.

```bash
python3 poc/scenarios/run.py                      # wind, nieuwste baseline, demo-set
python3 poc/scenarios/run.py --use-case zon       # …voor elke track
python3 poc/scenarios/run.py --author auto        # deterministische auteur
python3 poc/scenarios/run.py --author hybrid      # det-vloer + LLM-verkenner (S7)
LDT_SCENARIO_LLM_ENDPOINT=http://localhost:11434 \
  LDT_SCENARIO_LLM_API=ollama LDT_SCENARIO_LLM_MODEL=qwen3.8:latest \
  python3 poc/scenarios/run.py --use-case zon --author llm --narrator llm
python3 poc/scenarios/compare_authors.py --use-case zon   # golden-set auteur-regressie
```

De 13 canonieke sets tellen exact 3 scenario's per track (het contract uit
`uitdagingen.json` hierboven). Daar **naast** leven de what-if-sets uit
nspd-port fase 3: de mutatie **`add_zone_rule`** voegt een synthetische regel
toe over een gepinde alias-laag uit [`poc/tracks/_zone-aliases.json`](tracks/_zone-aliases.json)
(`netcongestie`, `rce-monumenten`, `rce-iam-archeologie`, `nwb-wegvakken`,
`prorail-spoor`). De V2-gate eist `basis.type=hypothetical` én een
`dataGrounding.sourceId` met rol in `ZONE_CAPABLE_ROLES` (`context` nooit) en
weigert een ruleId die botst met een baseline-regel — nooit een juridische
claim, wél herleidbaar. Twee sets, beide verdict pass (2026-10-18):

```bash
python3 poc/scenarios/run.py --use-case wonen --set poc/scenarios/wonen-whatif.json  # inclusion 500 m rond netcongestie
python3 poc/scenarios/run.py --use-case werken --set poc/scenarios/werken-whatif.json  # exclusion 1 km rond netcongestie
```

LLM-proposals doen niets meer dan de deterministische auteur: `ScenarioSpec`-
voorstellen via hetzelfde schema (`proposedBy` door de naad gestempeld),
mutaties beperkt tot de werkelijke engine-inputs, onverifieerbare voorstellen
landen in `proposals-rejected.json` (`pipeline/scenario_author.py`). Canonical
LLM-run: `scenario-runs/20260831T175842Z-zon-scen/` (10/10 proposals geaccepteerd,
gepubliceerde `scenario-narrative.md`); bevindingen: `docs/GENAI_SEAMS.md` §5.

## Kalibratie

```bash
python3 poc/data/calibrate.py   # CVDR-diff + geo-versheid + zone-drift-gate (≤ 0,1 %)
```

Herhaalbare kalibratieloop over de 13 featured scenario-runs
(`uitdagingen.json::scenarioRuns`): CVDR-diff van de Omgevingsverordening,
geo-versheid per gebruikte laag (goedkope count-checks, cache-first) en
zone-drift-gate gelijk aan V3. Rapport: `data/calibration/<datum>-calibratierapport.{md,json}`;
laatste stand (2026-10-14): 13/13 tracks pass, 56 zone-lagen live geteld, 0
tel-fouten. **Herhaal na het PS-besluit van 18-11-2026** — het rapport draagt
die amendementsvlag.

Landelijke bronnen (CBS-kerncijfers/landgebruik, RCE-monumenten + IAM,
NWB/ProRail, netbeheerder-netcongestie) staan als `context`/`scenario-basis` in
de registry; fetchers in `pipeline/national_data.py` (cache-first). DINO is
bewust **niet gepind** (geen open WFS meer, BRO auth-plichtig) — `fetch_dino_ondergrond`
faalt luid. Contextpagina's per uitdaging:
`python3 poc/pipeline/context_map.py` → `nldt/simulation/utrecht-context-<uitdaging>.html`.

## Limitations (kort — volledig per track in [`poc/tracks/`](tracks/wind.json) + elk rapport)

- **GIO-geometrie**: de DSO-download-API is key-gated (HTTP 401, geverifieerd);
  provinciale zones worden geserveerd via de agrest-IMOW-laag als
  **provenance-alias** van de Bijlage-II join-ids op elke NormCard.
- De provinciale `Gebied windenergie`-polygoon is een aanwijzingsenvelop, geen
  "overal geschikt"-gebied; per-locatietoetsing blijft nodig. Geen operationele
  vergunningstool.
- Onthouden (geen geverifieerd citaat → geen regel): stikstof, nationale
  windlawaai-limieten (Wgh/Bal), tip height/setbacks, Natura 2000 GIO,
  ET_wind-trackinglaag, het amendement 01-01-2027 (in voorbereiding).
- **Gekalibreerde parameters** (in elke `run_summary.json`): input-geometrieën
  2 m Douglas-Peucker (`--input-simplify-m`), zone-coördinaten 6 dp,
  rapport-display 25 m (`--display-tolerance-m`).
- Geen WFS/OGC-API-fallback op de provinciestack (ArcGIS REST only); faalt een
  live laag halverwege, dan degradeert de run beheerst: de betreffende regels
  vervallen, staan in het validatierapport (`needs_human`) en worden nooit gegokt.

## Opdrachten

```bash
# S1/S2-seams: lokaal open model verfijnt claims / stelt formalisaties voor
# (propose-only; luide deterministische fallback + norm-llm-ledger.json in de run-map)
LDT_NORM_LLM_ENDPOINT=http://localhost:11434 LDT_NORM_LLM_API=ollama \
  LDT_NORM_LLM_MODEL=qwen3.8 python3 poc/run.py --use-case wind --norm-analyst llm --formalizer llm
python3 poc/llm/compare_norm_llm.py --use-case wind   # golden-set deterministic vs LLM

# cross-track conflict-overlay (energie vs natuur, deterministisch)
python3 poc/crosstrack/run.py                  # wind,zon,bos
python3 poc/crosstrack/run.py --tracks zon,bos # canoniek: zon×bos 22.665 km² = 94,7 % van
                                               #   het zoekgebied; wind×zon 845.445 km² (98,4 %)

# H3-hexlagen (nldt-brug; zone-waarheid blijft polygonaal)
python3 poc/crosstrack/run.py --tracks zon,bos          # h3-crosstrack.{json,html}
python3 poc/crosstrack/run.py --buildings nldt/examples/hex-points.geojson  # h3-buildings.json
python3 poc/scenarios/run.py --use-case zon --no-h3     # hex-metrics overslaan
POC_H3_OFFLINE= ../nldt/.venv/bin/python tests/make_h3_fixtures.py        # fixtures (in poc/)

# Urban Strategy stiltegebied-screen (wind; art. 9.26 LAeq 40/45 dB blijft ambigu = FR-W-11)
python3 poc/run.py --use-case wind             # schrijft urbanstrategy-stiltegebied.json
python3 poc/run.py --use-case wind --skip-us
#   live RestAPI opt-in: US_LIVE=1 + US_BASE_URL, US_TOKEN, US_BIN — zie
#   docs/POC_URBANSTRATEGY_INTEGRATION.md; fixtures: tests/make_us_fixtures.py

# leerstaat (decision trails) — vanuit nldt/
python3 -m services.memory.consolidate         # observaties → decision-trail-records
python3 -m services.memory.report              # leerrapport (--handle/--promote)
```

**Nieuwe track toevoegen**: (a) `poc/use-cases/<track>.json`
(OpportunityMapRequest, provinciegrens als AOI met bron in `parameters`),
(b) een geverifieerde evidence-shard `poc/corpus/evidence-<track>.json`,
(c) de declaratie [`poc/tracks/<track>.json`](tracks/wind.json) (report-titels,
`headlineNote`, `limitationsTemplate`; enrichment/templates in
`poc/tracks/_enrichment/` en `poc/tracks/_templates/`),
(d) een cite-or-abstain-ledger `poc/corpus/normcards-rejected-<track>.json`,
(e) zone-aliassen in `poc/tracks/_zone-sources.json` en een registry-entry in
`poc/data/sources.json`. `python3 -m pipeline.agents` regenereert de corpora —
de byte-identiek-gate in `tests/test_track_config.py` bewaakt dat de
gedeelde machinerie niets verandert.
