# poc-nspd fase 3 Implementatieplan — ruimtelijke grounding + what-if scenario's

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Bewuste afwijking (bewezen betrouwbaarder in fase 1/2): de controller implementeert zelf; reviewers blijven subagents aan elke taakpoort.

**Goal:** De scenario-lagen in de viewer zijn nu AOI-brede vlakken (54/56 formele regels "zone-loos gedocumenteerd"). Fase 3 pint de ontbrekende regel-geometrieën (Zeeland Omgevingsverordening-WFS, Mercator gewestplan/RUP), formaliseert de regels met hun operand, en porteert het what-if-scenario-deel (S7: ScenarioSpec + deterministic/hybrid/LLM-author + sweep + gates) van `poc/` naar `poc-nspd/`.

**Architecture:** Deel A (ruimtelijke grounding) hergebruikt de bestaande machinerie: `ZONE_SOURCES`-aliases, cache-first WFS-fetchers, curator-identiteit (`source={docId,article,version,quote,quoteLanguage,uri,retrievedAt}`), V2b, goldens via `NSPD_GOLDEN_FREEZE=1`. Deel B port de Utrecht-machinerie bijna 1-op-1: `pipeline/scenarios.py` + `scenario_author.py` + drie schemas (de 13 track-keys en objectType-enums komen exact overeen), met RD als interne CRS (NSPD-conventie) en de netcongestie-bron als eerste `scenario-basis`.

**Tech Stack:** ongewijzigd (Python 3.13 stdlib-first, pyproj, shapely, jsonschema, pytest; Leia-pin 7351002 ongewijzigd).

**Spec:** `docs/superpowers/specs/2026-10-14-poc-nspd-design.md` §4.3/§4.5; ontwerp-S7: `docs/superpowers/plans/2026-09-17-s7-hybrid-scenario-author.md`. Fase-2-plan: `docs/superpowers/plans/2026-10-14-poc-nspd-fase2.md`.

## Global Constraints

- Al het werk onder `poc-nspd/` (pathspec `-- poc-nspd` bij elke commit); `poc/` en de Leia-submodule blijven onaangeroerd.
- Werken in de hoofdcheckout `/Users/marc/Projecten/ldttoolbox` op `main`; commits direct op main. Servers :5173 (viewer) mogen draaien; geen netwerk in de testsuite (fake transports), wel live probes vóór het pinnen van elke nieuwe bron (bewijs in `data/probe_2026-10-16.json` of `probeEvidence`-veld).
- Cite-or-abstain blijft leidend: een regel wordt alléén geformaliseerd als zijn eigen citaat de operand noemt; bij twijfel blijft hij `ambiguous` (`zone_loos_gedocumenteerd`) — geen interpretatieslaan. Formalisatie wijzigt nooit normcard-teksten of citaten.
- Luid falen; cache-first; goldens: bestaande nooit handmatig herschrijven, alleen regenereren via `NSPD_GOLDEN_FREEZE=1` ná een gereproduceerde run (veldset verdict/output_rules/formalized/rejected/v2bStatus blijft).
- Elke taak laat de volledige suite groen (baseline bij start: 93 passed + 2 skipped + 15 goldens-deselected; goldens via `pytest -m golden`).
- What-if-port: ScenarioSpec-mutaties blijven beperkt tot `drop`/`set_semantics`/`set_buffer_distance_m`; alleen `status=="formalized"`-regels zijn mutabel; control-reproductie-tolerantie 0.001; LLM endpoints uit in de standaard-suite (fake transport in tests).
- Zone-aliases: nieuwe aliases alléén mét live-gepinde bron en probe-bewijs (`zeeland-ovz-wfs`-lagen, `mercator-gewestplan-wfs`).

## Nieuwe ID-conventies fase 3

| alias | bron / typeName | rol | gebruikt door |
|---|---|---|---|
| `windconcl-nl` | `zeeland-ovz-wfs` / `dso:ext_ovz_windnrg_concloc` | inclusion | FR-WIND-01 |
| `stedelijk-nl` | `dso:ext_ovz_bebkom_woonbeb2025` | inclusion | FR-ZON-01, FR-WON-*, FR-WER-* |
| `waterkering-nl` | `dso:ext_ovz_regwkr_dijktraj` | exclusion | FR-WAT-03 |
| `landschap-nl` | `dso:ext_ovz_landsch_vlak` | attention/exclusion | FR-LAN-* |
| `natuurnetwerk-nl` | `dso:ext_ovz_nbp_best_nat2025` | attention | FR-BOS-*, FR-LAN-* |
| `recreatie-nl` | `dso:ext_ovz_verblijfsrec2022` | inclusion/attention | FR-REC-* |
| `kustzone-nl` | `dso:ext_ovz_kustzone2022` | conditional | FR-REC-*, FR-LAN-* |
| `glastuinbouw-nl` | `dso:ext_ovz_glastbconctgbd` | inclusion | FR-LNB-* |
| `grondwater-nl` | `dso:ext_ovz_grwtrbsz` | attention/exclusion | FR-BOD-*, FR-WAT-* |
| `stiltegebied-nl` | `dso:ext_ovz_stlgbd_totaal_2027` | attention | FR-LAN-*, FR-REC-* |
| `vaarweg-nl` | `dso:ext_ovz_vaarwg` | attention | FR-MOB-*, FR-WAT-* |
| `gewestplan-be` | `mercator-gewestplan-wfs` / `lu:lu_gwp_gv` (+`lu_gwp_ov`) | inclusion/exclusion per bestemming | FR-BEW-*, FR-BEZ-*, FR-WER-*, FR-WON-* |

Scenario-id's volgen de S7-conventie (`SC-…`, `SSET-…`, `SR-…`); `proposedBy` = `deterministic-scenario-author#poc-nspd-v1` / `hybrid#…` / `llm-proposal#<model>`.

---

### Task 1: Zeeland OVZ-WFS pinnen + fetcher (fetch_ovz_laag)

**Files:**
- Modify: `poc-nspd/data/sources.json` (nieuwe bron `zeeland-ovz-wfs`, endpointType `wfs`, per laag probeEvidence), `poc-nspd/run.py` (ZONE_SOURCES-uitbreiding met de tabel hierboven — alléén lagen met probe-bewijs), `poc-nspd/pipeline/national_data.py` (`fetch_ovz_laag(type_name, cache_name, refresh, transport)`)
- Create: `poc-nspd/tests/test_fetch_ovz.py`, `poc-nspd/data/probe_2026-10-16.json` (live-probe-resultaten)

- [ ] **Stap 1 (live probes):** per laag uit de ID-tabel: GetFeature `resultType=hits` + één `count=3`-GetFeature in de NSPD-bbox (EPSG::28992), HTTP 200 + geometry-non-empty bewijzen; resultaten in `data/probe_2026-10-16.json`. Lagen zonder bewijs worden níet gepind ( alias blijft buiten ZONE_SOURCES).
- [ ] **Stap 2 (failing tests):** `test_fetch_ovz.py` met fake transport: URL-vorm (`typeNames=dso%3A…`, `bbox=<RD>,urn:ogc:def:crs:EPSG::28992`, `count`, `outputFormat=application/json`), cache-hit slaat transport over, geometrie RD→WGS84 (hardcoded mini-voorbeeld), onverwacht antwoord → `GeoDataError`.
- [ ] **Stap 3 (implementatie):** `fetch_ovz_laag` analoog aan `fetch_geopunt_wfs` (zelfde _WFS_COUNT_LIMIT, cache onder `data/cache/nl/ovz/`); ZONE_SOURCES-entries met note + probeEvidence-verwijzing.
- [ ] **Stap 4:** suite groen; registertests groen; commit `feat(poc-nspd): Zeeland OVZ-WFS pinnen + fetch_ovz_laag (fase 3, task 1)`.

### Task 2: NL-formalisatie golf 1 — wind + zon + water (de twee reeds-half-grounded tracks + waterkering)

**Files:** `corpus/formal-rules-nl-{wind,zon,water}.json` (alleen status/zoneSelector/rationale/contextTags), `corpus/normcards-*` onaangeroerd, goldens voor deze runs.

- [ ] FR-WIND-01 → `formalized`, inclusion `windconcl-nl` (citaat: art. 18.17 lid 1 + bijlage XIV-verwijzing; rationale noemt de geometriebron); FR-WIND-02 alléén als het citaat een toetsbare ruimtelijke voorwaarde noemt (zo niet: blijft ambiguous). FR-ZON-01 → inclusion `stedelijk-nl`. FR-WAT-03 → exclusion `waterkering-nl`.
- [ ] Re-runs `wind-nl`, `zon-nl`, `water-nl` (cache-first); zone-vormen zijn náúwelijks nog AOI (bewijs: `areaKm2`显著 < AOI en ≠ Natura-only); goldens freeze voor de drie runs.
- [ ] Suite + goldens groen; commit `feat(poc-nspd): NL-formalisatie golf 1 — concentratielocaties, stedelijk gebied, waterkering (fase 3, task 2)`.

### Task 3: NL-formalisatie golf 2 — overige 9 tracks volgens citaat

**Files:** `corpus/formal-rules-nl-*.json`, goldens.

- [ ] Per track de regels doornemen tegen hun citaat; formaliseren wat dekt (recreatie/landschap/bos/landbouw/wonen/werken/bodem/mobiliteit/biomassa/energietoets); wat niet dekt blijft explicitiet ambiguous. Elke formalisatie: `executableRef engine.zone.<op>@poc-v1`, zoneSelector met nieuw alias, contextTag `geometry_zeeland_ovz`.
- [ ] Re-runs + goldens-freeze; suite groen; commit per track-blok of één commit met tabel in het commitbericht.

### Task 4: BE — gewestplan + RUP pinnen en formaliseren (cap: wat bewijsbaar is)

**Files:** `data/sources.json` (`mercator-gewestplan-wfs`: `lu:lu_gwp_gv`, `lu_gwp_ov`; optioneel GRUP-zonelaag), `corpus/formal-rules-be-*.json`, goldens.

- [ ] Probe gewestplan-lagen (GetFeature in NSPD-bbox, Lambert72); attribuut-onderzoek (bestemmingscodes) gedocumenteerd; mapping-tabel bestemming→regel in de rationale. Formaliseren alléén waar citaat+bestemming kloppen (bijv. FR-BEW-03 windmolenpark-zone uit GRUP indien geometrie bestaat; FR-WER-01 industrieterrein-vlakken); rest blijft ambiguous.
- [ ] Re-runs BE + goldens; commit `feat(poc-nspd): BE-formalisatie — gewestplan/RUP-operands (fase 3, task 4)`.

### Task 5: Re-runs, xborder, viewer-regeneratie, doc

- [ ] Alle 26 runs (13×2) vers (cache-first), 15 goldens her-bevroren, 13 xborder-merges, `make_viewer_config` regenereert (scenario-lagen nu gedifferentieerd; "(AOI-breed)"-labels alleen waar nog waar); README-fase-3-status + spec-statusregel; screenshot-verificatie scenario-lagen in viewer.
- [ ] Commit `feat(poc-nspd): fase 3a — ruimtelijke grounding, alle 26 runs vers, viewer-scenario's gedifferentieerd`.

### Task 6: S7-port — scenario-machinerie naar poc-nspd

**Files:**
- Create: `poc-nspd/pipeline/scenarios.py`, `poc-nspd/pipeline/scenario_author.py`, `poc-nspd/schemas/scenario-spec|scenario-set|scenario-report.schema.json` (enums: NSPD-tracks/objectTypes; id-patterns ongewijzigd), `poc-nspd/scenarios/run.py`, `poc-nspd/scenarios/compare_authors.py`, `poc-nspd/tests/test_scenarios.py`, `poc-nspd/tests/test_scenario_author.py`
- Modify: `poc-nspd/data/sources.json` (netcongestie `role: "scenario-basis"` — al context; check de V2-data-grounding-check leest rol uit sources.json), `poc-nspd/pipeline/contracts.py` (+SCHEMA_NAMES)

- [ ] Port volgens het exploratierapport (engine, control-reproductie, critic V0–V3, authors file/auto/llm/hybrid, ledger, narratie-gate met fallback); CRS intern RD (pyproj 4326↔28992; BE-AOI's in RD-frame zoals de pipeline).
- [ ] Tests: gemuteerde executie op synthetische lagen met gepinde km²-waarden (CONTROL/DROP/BUFFER/MARKER), skip-met-reden voor ambiguous, unknown ruleId = fail, fake-transport LLM/hybrid, narratie-gate magnitude-fold.
- [ ] Suite groen; commit `feat(poc-nspd): S7-port — scenario-engine, authors, gates (fase 3, task 6)`.

### Task 7: Demo-scenario-sets + sweep end-to-end (wind)

**Files:** `poc-nspd/scenarios/wind.json` (+ 2–3 extra tracks), scenario-runs onder `poc-nspd/scenario-runs/`.

- [ ] Shipped set: per geformaliseerde NL-regel de det-vormen (DROP, SETBACK500, HALF/DOUBLE) als `basis: policy_variant/norm_variance`; één `hypothetical` met `basis.dataGrounding: netcongestie` (V2-check groen). Baseline = task-5 wind-nl-run.
- [ ] `python3 -m scenarios.run --use-case wind --author hybrid --max-scenarios 10 --narrate` → scenario-report pass, CONTROL-geojson + per-scenario geojson; narratie door de gate.
- [ ] Commit `feat(poc-nspd): fase 3b — what-if-sweep wind end-to-end (fase 3, task 7)`.

### Task 8: What-if in de viewer + afsluiting

**Files:** `poc-nspd/make_viewer_config.py` (groep "What-if scenario's" onder "scenario": CONTROL + per scenario geojson + delta in title/description), `poc-nspd/README.md`, spec-status, `.superpowers/sdd/progress.md`.

- [ ] Viewer: scenario-runs uitlezen (laatste pass per track), lagen genereren; camera op de hoofdzone. Screenshot-verificatie: scenario-versus-control zichtbaar verschillend.
- [ ] Suite + goldens groen; commit `feat(poc-nspd): fase 3 afgerond — what-if-scenario's in de viewer`; documentatie-update.

## Scope-notitie

- Buiten scope blijft: crosstrack-overlay (spec §8 item 11), DHM-extrusie, LLM-endpoints in de standaard-suite, de viewerlaag van `world_scene`/deep-agents (S7-port levert geojson + markdown; Leia-integratie via make_viewer_config in task 8).
- Als task 4 (BE) vastloopt op attribuut-onderzoek: netjes afkappen met gedocumenteerde abstentions; NL-track differentiatie is het demokritieke pad.
