# Ontwerp: Utrecht-PoC herbouwd op NSPD-patroon — gefaseerde interne refactor

**Datum:** 2026-10-18
**Status:** ter review
**Verwijzingen:** NSPD-referentie `poc-nspd/` (spec `docs/superpowers/specs/2026-10-14-poc-nspd-design.md`); Utrecht-state na plan 1+2 (uitdagingen 5×13×3, data-kalibratie, 362 tests groen).

## 1. Doel en succescriterium

De Utrecht-PoC-code is een generatie ouder dan de NSPD-PoC: 13 tracks zitten
hardcoded in `poc/run.py` (TRACKS-dict, ±700 regels incl. lambdas), een
ZONE_SOURCES-dict en `poc/pipeline/agents.py` (EVIDENCE_ENRICHMENT ±860 regels
en TEMPLATE_SPECS ±880 regels aan Python-dicten). De NSPD-PoC lost dat patroon
deels op (registry v2.0, probe-bewijs, add_zone_rule what-ifs, strakke README)
en deels niet (zijn agents.py is dezelfde fork).

**Succescriterium:** na deze refactor is elke track in Utrecht declaratief
beschreven in `poc/tracks/<track>.json` (+ bijbehorende bestanden), produceert
`python3 -m pipeline.agents` **byte-identieke** corpus-artefacten, staan de geo-
bronnen in registry v2.0 met probe-bewijs, kunnen scenario's what-if-regels
krijgen over landelijke bronnen (`add_zone_rule`), en is de README NSPD-stijl.
De 13 canonieke runs reproduceren binnen de bestaande golden-toleranties; de
deep-agents-demo werkt ongewijzigd.

## 2. Randvoorwaarden (hard)

- **Gedrag identiek:** golden-regressie (`pytest -m golden`) blijft groen;
  corpus-regeneratie byte-identiek; geen wijzigingen aan engine-semantiek,
  critic-levels of de 39 bestaande scenario's.
- **Demo intact:** live_server, dashboard, scenario_catalog, prompts en de
  Utrecht-specialist blijven werken (de toolpaden van de demo importeren de
  pipeline — hun gedrag verandert niet).
- **Cite-or-abstain blijft staan:** landelijke bronnen worden nooit juridische
  claims; what-ifs zijn altijd `hypothetical` + data-gegrond onder de V2-gate.
- Elke fase is een eigen merge met eigen gate (geen big bang).

## 3. Fase 1 — `poc/tracks/` declaratief

**Huidige staat:** `poc/run.py::TRACKS` (per track: shard, ledger,
report_title, decision_table_id/title, prov_namespace, headline_note,
limitations-**lambda**), `poc/run.py::ZONE_SOURCES`, en in `agents.py` de
dicten `EVIDENCE_ENRICHMENT` (keyed by evidence-id) en `TEMPLATE_SPECS`
(keyed by evidence-id).

**Nieuw:**

```
poc/tracks/<track>.json          # 13 stuks — per-track declaratie (zie veldlijst)
poc/tracks/_enrichment/<track>.json   # EVIDENCE_ENRICHMENT-entries van deze track
poc/tracks/_templates/<track>.json    # TEMPLATE_SPECS-entries van deze track
poc/tracks/_zone-aliases.json    # fase 3 (hier al vastgelegd, aangemaakt in fase 3)
poc/pipeline/track_config.py     # laadmodule (alleen lezer)
```

Veldlijst `<track>.json`: `shard`, `ledger`, `reportTitle`,
`decisionTableId`, `decisionTableTitle`, `provNamespace`, `headlineNote`,
`limitations` (lijst template-strings met placeholders `{ambiguous}`,
`{output_rules}`, `{formalized}` — de loader format't ze; de lambdas
verdwijnen), `zoneAliases` (optioneel, fase 3).

Loader-API (`track_config.py`): `load_track(track_id) -> dict` (zelfde
sleutel-vorm als de huidige TRACKS-entry, limitations al geformatteerd),
`load_enrichment() -> Dict[evidence_id, entry]`,
`load_templates() -> Dict[evidence_id, spec]`, `load_zone_aliases() -> dict`.
`run.py` en `agents.py` worden consumers; de dicten verdwijnen.

**Gate fase 1:** (a) `python3 -m pipeline.agents` produceert byte-identieke
`corpus/normcards-<track>.json` en `corpus/formalrules-<track>.json` (diff-test
in de suite); (b) golden-regressie groen; (c) volledige suite groen; (d)
`/api/scenarios` en de world-scene-builds ongewijzigd.

## 4. Fase 2 — registry v2.0 + probe-tooling

**Vorm** (`poc/data/sources.json`): `{"version": "2.0", "sources": [...]}`
met per entry de bestaande sleutels (id, title, serviceUrl, layerId, …)
**plus** `role` (inclusion | exclusion | conditional | attention | compensation
| context | scenario-basis), `fetchPolicy` (`cache` | `service`) en
`provenance: {pinned: "<datum>", evidence: "<bestandsref>"}`. De `note`-velden
gaan in `provenance.note`. Alle 114+8 entries gemigreerd (script-gedreven
migratie, geen handwerk). De `role` van de provinciale lagen wordt afgeleid uit
de layers.json-manifesten van de 13 canonieke runs (zelfde bron kan in
beginsel meerdere rollen dragen — de registry kiest de dominant-gebruikte; de
uitvoerende semantiek blijft in de formalrules/layers-manifesten, zoals bij
NSPD); bronnen die in geen enkel manifest voorkomen krijgen `role: "context"`
met de afleiding genoteerd in `provenance.note`.

**Consumers (migratieverplicht):** `pipeline/geodata.py::load_sources` (leest
entries — contract blijft `{id: entry}`), `pipeline/national_data.py::
_data_grounding_errors` (role-check — ongewijzigd semantiek), `poc/data/
calibrate.py` (leest layers.json-manifesten, niet sources — alleen
versie-vermelding), deep-agents-tools die sources.json lezen (indien aanwezig
— grep-verplichting in de taak). Registry-vorm-test: alle entries hebben
role/fetchPolicy/provenance.

**Probe-tooling** (`poc/data/probe_sources.py` → `poc/data/probe-sources-
<datum>.json`): per bron live feature-count binnen de Utrecht-AOI (zelfde
goedkope count-als-kalibratieloop voor ArcGIS; OGC-API/WFS analogous),
bereikbaarheid + pin-datum; uitkomst als NSPD-stijl evidence-bestand, samen
met de bronnenlijst in de README. Probe is bewust *lees* (verandert geen
cache; --refresh-download hoort bij de fetchers).

**Gate fase 2:** suite groen; dataGrounding-V2-check-tests groen tegen de
v2-registry; probe-evidence committed; README-brontabel bijgewerkt.

## 5. Fase 3 — `add_zone_rule` what-ifs (NSPD-port)

**Mutatie** (scenario-spec `mutations[]`): `{ruleId, action: "add_zone_rule",
zoneId, zoneSemantics: "inclusion"|"exclusion", bufferDistanceM?}` — getrouw
geport uit `poc-nspd/pipeline/scenarios.py` (`_synthetic_zone_rule`,
`apply_mutations`-tak, `load_extra_zone_layers`, `ZONE_CAPABLE_ROLES`):
- synthetische FormalRule: `normCardId: null`, `instrumentType:
  "scenario-hypothetical"`, `synthetic: true`, `geometrySource:
  "national_source"`, buffer in de zoneSelector; engine en rapportage
  verwerken hem ongewijzigd;
- **guards:** ruleId-botsing met een baseline-regel → skipped-rij met
  `v2Error`; zoneId/zoneSemantics verplicht; onbekende alias of ontbrekende/
  corrupte cache → degradatie + regel gedropt (nooit stil);
- **V2-gate:** de scenario-basis moet `hypothetical` zijn én `dataGrounding.
  sourceId` moet de alias-bron zijn met een rol uit `ZONE_CAPABLE_ROLES`
  (`context` is nooit zone-bepalend);
- schema: `action`-enum + `zoneId` in `scenario-spec.schema.json` uitbreiden.

**Aliassen** (`poc/tracks/_zone-aliases.json`, aangemaakt in fase 3): zoneId →
`{sourceId, cachePath (relatief aan poc/), role, note}`; begint met de vijf
nationale bronnen die geometrie in hun cache hebben (rce-monumenten —
punten, rce-iam-archeologie, rws-nwb-wegen, prorail-spoor,
netbeheerder-netcongestie). Het CBS-grid en landgebruik hebben bewust géén
geometrie in de cache (plan 2) en zijn dus geen alias-laag; PDOK-uitbreiding
kan later via hetzelfde mechanisme. De alias-lader leest offline uit de
bestaande caches (adaptief: nationale caches liggen onder
`data/cache/national/`, inclusief genest `netcongestie/`); puntlagen
(RCE-monumenten) buffert de engine tot vlakken — zoals NSPD, test gedekt.

**Demo-what-ifs** (nieuwe scenario's, naast de bestaande 39, verdict pass):
1. `SC-WER-NETCONGESTIE-1KM` (werken): exclusion 1 km rond de
   netcongestie-voedingsgebieden — data-gegrond;
2. `SC-WON-NETCONGESTIE-500M-INCLUSIE` (wonen): inclusion binnen 500 m van de
   netcongestiegebieden (herstructureringsdruk rond knelpunten).

De oorspronkelijk overwogen "wonen 250 m rond rijksmonumenten" is niet
uitdrukbaar zonder twee besluiten: `add_zone_rule` kent alleen
inclusion/exclusion (geen attention-semantics, zoals NSPD), en
`rce-monumenten` heeft registry-rol `context` die de V2-gate bewust weigert.
Rol-verhoging van context-lagen is een beleidskeuze, geen code-wijziging, en
blijft dus buiten deze refactor.

**Gate fase 3:** unit-tests voor de mutatie (aanvaard/bots/degradatie), V2-gate
(afgewezen: context-rol, niet-hypothetical basis, vreemde sourceId), twee
nieuwe sweeps verdict pass; bestaande 39 ongewijzigd.

## 6. Fase 4 — README + prompts strakker

- `poc/README.md` 530 → ±350 regels, NSPD-structuur: succescriterium bovenaan,
  uitdagingen/bronnen als tabellen (uit `uitdagingen.json`/registry, niet
  proza), architectuurdiagram (ASCII, NSPD-stijl), opdrachten-sectie; de
  verhalende zone-semantiek per track verhuist naar `poc/tracks/<track>.json`
  (headlineNote) en de limitations-templates — de README linkt erheen.
- `deep-agents/prompts/poc/utrecht.md` + de templates in
  `deep-agents/poc_demos.py` verwijzen naar `poc/tracks/` i.p.v. hardcoded
  opsommingen; geen inhoudelijke prompt-gedragswijziging.

**Gate fase 4:** docs-review (geen dode verwijzingen), deep-agents-suite
groen, README-regelgrens.

## 7. Volgorde en risico's

Fases 1 → 2 → 3 → 4, elk een eigen merge met gate (§3–6). Grootste risico's en
mitigaties: byte-identieke regeneratie (fase 1) wordt per track gediff't vóór
merge; de registry-migratie (fase 2) is script-gedreven met een
vorm-vergelijkingstest (alle oude sleutels behouden); de engine-puntbuffer
(fase 3) dekt de RCE-puntlaag met een eigen test. Achtergebleven NSPD-patronen
(medallion-datalake, DCAT-records, Leia-viewer-koppeling, PDOK-catalogus-probe)
vallen bewust buiten deze refactor — opvolgers, geen scope.

## 8. Out of scope

- Medallion-datalake / DCAT / bronze-silver-gold voor Utrecht.
- PDOK-catalogus-doorlichting zoals NSPD (33 bronnen) — alias-uitbreiding kan
  later via hetzelfde `_zone-aliases.json`-mechanisme.
- Leia/viewer-koppeling voor Utrecht.
- Wijzigingen aan de deep-agents-demostroom (stappen-stroom, modes-aanbod),
  het kalibratie-script of de scenario-engine buiten `add_zone_rule`.
- Nieuwe juridische claims uit landelijke bronnen.
