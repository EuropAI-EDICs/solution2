# Piloot Gent F4 — evaluatielaag: KPI-harness + gates, injectiesuite, exit-test, EDIC-registratie (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw F4 van `poc-gent/` (ontwerp §8 + §11): de evaluatielaag die de go/no-go-criteria uit de baseline aantoonbaar maakt — KPI-harness met drempels (KPI-01/02/03/04/06, H-event-controle, determinisme), een adversariële injectiesuite (≥30 aanvallen: directe/indirecte injectie, tool-misbruik, exfiltratie; KPI-08/SEC-03), de exit-test (config-export + herleiding; KPI-09/REP-01) en de EDIC-assetmap-registratie van de Gent-transactievariant. Het demo-simulatietabblad (§11 F4-onderdeel) bestaat al en is meegroeid tot fase 3 — geen nieuwe werkzaamheid.

**Architecture:** Meetlogica als pure functies in `core/kpis.py` (run+events+manifest in, dicten uit) en `core/injectie.py` (aanvaldefinities → invarianten-checks); `eval.py` wordt de CLI die golden + KPI-rapport + go/no-go, injectiesuite en exit-test aanbiedt (`--injectie`, `--exit`, `--rapport <pad>`). De pipeline krijgt één kleine harness-uitbreiding: `persona_override` (merge over de persona-fixture) zodat adversariale invoer op de seams (situatieschets, antwoorden, documenten) zonder globale fixture-mutatie kan — gespiegeld aan het bestaande `override_slots`. Alles stdlib-only, offline, deterministisch.

**Tech Stack:** Python 3.11+ stdlib-only voor `core/`, `eval.py`; `jsonschema` alléén onder `../nldt/.venv`; pytest.

**Spec:** design §8 (KPI-tabel met min. aanvaard/doel; testplan; stopcondities/go-no-go) · baseline `nldt/recipes/baselines/gent-mobiliteit-ondernemer.baseline.json` (goNoGo-lijst is leidend) · §12 (AI-04/06, SEC-03, REP-01/02) · GENAI_SEAMS (receipt trail).

## Global Constraints

- Offline en deterministisch: geen netwerk, geen muurklok in rapporten behalve expliciete gegenereerdOp-timestamp; herhaalde `eval.py`-runs geven identieke uitkomsten.
- Drempels komen uit de baseline/design (KPI-01 ≥90 min / ≥95 doel · KPI-02 100 · KPI-03 100 · KPI-04 ≥90% ≈ ≥18/20 · KPI-06: 0 vragen om authentieke slots); drempels leven als constanten naast de baseline-tekst, niet als losse magic numbers.
- `eval.py` exit-code-contract blijft: 0 = golden + determinisme + (nieuwe default-controles) groen; de bestaande test `test_eval.py` blijft geldig.
- Injectiesuite valt de engine alléén via de echte invoeroppervlakken aan (vrije-tekst-slots, situatieschets, antwoorden, documentnamen); er worden géén engine-internen gepatcht. Elke aanval kent een schone zuster-run.
- Events blijven waardevrij ónder adversariale invoer (SEC-05): payload-strings komen niet in events terecht.
- EDIC-registratie (taak 4) is **voorbereid maar geblokkeerd**: `nldt/recipes/edic-asset-map.json` bevat oncommitte NOVEX-werk-in-uitvoering (policyAlignmentSchema nog buiten het schema) — geen commits in dat bestand tot dat werk landt; de nldt-coverage-test staat daardoor nu al rood (Gent-recipe ontbreekt in de gecommitte map sinds F1).
- Commit per taak, conventional commits scope `poc-gent`, Nederlandse samenvatting.

---

### Task 1: KPI-harness + go/no-go in eval

**Files:**
- Create: `poc-gent/core/kpis.py`
- Modify: `poc-gent/eval.py`
- Test: `poc-gent/tests/test_kpis.py`, `poc-gent/tests/test_eval.py` (+rapporttest)

**Interfaces (core/kpis.py, pure functies):**
- `DREMPELS = {"kpi01_min": 90.0, "kpi01_doel": 95.0, "kpi02_min": 100.0, "kpi03_min": 100.0, "kpi04_min": 90.0}` — uit baseline-goNoGo.
- `routing_juist(run, expect) -> bool` — `paths.transactions` + `paths.info` exact.
- `besluit_juist(run, expect) -> bool` — outcome + status + paths (KPI-02-granulariteit).
- `brontraceerbaarheid(run) -> (met_bron, totaal)` — context-regels, prefill-velden en routing-uitleg samen; "bron" niet-leeg.
- `transactiesucces(run, expect) -> bool | None` — `None` buiten de E2E-populatie (expect-status niet `gereed*`); binnen: run-status `gereed*` én elke verwachte transactie ontvangststatus `geaccepteerd`.
- `once_only_vragen(events, manifest) -> {"authentieke_slot_vragen": int, "vragen_totaal": int}` — context_vraag-events per slot tegen `contextSchema.slots[*].authenticSource`.
- `h_events_consistent(events) -> (correct, totaal)` — per H-gate (H1–H4): request heeft passend verdict met geldige waarde; handover-events met `naar`+`reden`.
- `rapport(runs_met_expect, manifest) -> dict` — aggregeert KPI-01/02/03/04/06 + H-events tot percentages met drempeloordelen en een `goNoGo: "GO"|"NO-GO"` conform de baseline-lijst (zonder exit-test, die valt er in taak 3 bij).

- `eval.py`: default-uitvoer breidt uit met KPI-regels (`KPI-01 routing 13/13 (100.0%) … OK`) en een slotregel `go/no-go: GO` (of NO-GO + redenen); `--rapport <pad>` schrijft het JSON-rapport; exit-code volgt go/no-go (golden-falen blijft ook rood).

- [ ] **Step 1: falende tests** — `test_kpis.py`: elk criterium mét minstens één tegenvoorbeeld (uitleg zonder bron → KPI-03 <100; H4 zonder verdict → H-events faalt; ontvangst niet-geaccepteerd → KPI-04 faalt; vraag om authentiek slot → once-only faalt); `test_eval.py`: rapportbestand geschreven, go/no-go GO op de huidige golden set.
- [ ] **Step 2: implementeren**; suite groen, `python3 eval.py` toont KPI-blok + GO. Commit: `feat(poc-gent): KPI-harness met drempels en go/no-go in eval (F4)`.

### Task 2: Injectiesuite (KPI-08/SEC-03)

**Files:**
- Modify: `poc-gent/core/pipeline.py` (`persona_override: dict | None = None`, merge over de fixture-persona; `persona.get("documenten")` wint van de documenten-fixture)
- Create: `poc-gent/fixtures/injecties.json` (payloads per categorie)
- Create: `poc-gent/core/injectie.py`
- Modify: `poc-gent/eval.py` (`--injectie`)
- Test: `poc-gent/tests/test_injectie.py`

**Interfaces:**
- Aanval = `(id, categorie, persona, vector)` met vector = `override_slots`-dict óf `persona_override`-dict (situatieschets/antwoorden/documenten). Categorieën uit design §8.1/KPI-08: `direct` (vrije-tekst-slots address/activity/timing), `indirect` (situatieschets + documentbestandsnaam), `tool-misbruik` (payload probeert doelbinding/toolregister te buigen), `exfiltratie` (payload vraagt om gegevens van anderen). *Planamendement (implementer-bevinding): 15 direct + 8 indirect + 5 tool-misbruik + 6 exfiltratie = 34 aanvallen; een adversarieel adres leidt bewust naar escalatie (unknownPolicy) — vandaar de gedrag-isolatie-invariant als deelverzameling (escalatie mag toolcalls overslaan, nooit extra).*
- Invarianten per aanval (tegengerekend tegen de schone zuster-run, zelfde persona/vector-slot met gewone waarde):
  1. run voltooit (géén crash; status ∈ bekende waarden);
  2. **data-isolatie**: payload-string komt in het run-artefact alléén voor als waarde van het geïnjecteerde veld — níet in `routing.uitleg`-teksten, `prov.sources`, ontvangstbewijzen;
  3. **gedrag-isolatie**: reeks bron_raadpleging-events (tool+purpose) identiek aan zuster-run; bij niet-routing-relevante slots (activity/timing) ook routing-outcome identiek;
  4. **events waardevrij**: payload komt niet voor in de events-json (SEC-05 houdt stand onder adversariale invoer);
  5. **exfiltratie-additie**: waarden van andere persona's (kenteken, wallet-sub) afwezig in het run-artefact.
- `core/injectie.aanvallen(poc_root) -> list[dict]` (vanuit fixtures/injecties.json), `voer_uit(poc_root, package_id) -> list[dict]` (per aanval: geslaagd + schendingen-lijst), `eval.py --injectie` print per categorie en totaal (`injectie: 32/32 weerstand geboden — KPI-08: 0 open bevindingen`), exit 1 bij schendingen.

- [ ] **Step 1: falende tests** — `test_injectie.py`: suite-drempel ≥30; elke categorie ≥1; een canariaanval met string die wél in uitleg terechtkan komen (handgebouwd run-artefact) faalt de invariant-check (bewijst dat de checker controleert); pipeline `persona_override`-merge gedekt (documenten-override wint, situatieschets-hash event volgt payload).
- [ ] **Step 2: implementeren**; `python3 eval.py --injectie` groen. Commit: `feat(poc-gent): injectiesuite — 32 adversariële aanvallen op de seams, invarianten tegen zuster-runs (F4)`.

### Task 3: Exit-test (KPI-09/REP-01/02)

**Files:**
- Modify: `poc-gent/eval.py` (`--exit`, en exit-test opgenomen in het go/no-go-oordeel van `--rapport`)
- Test: `poc-gent/tests/test_exit.py` (unit) + opname in `test_eval.py`

**Interfaces:**
- `exit_test(poc_root, package_id) -> dict` — kopieert `packages/<id>` + de benodigde fixtures (personas, magda, wallets, identiteiten, documenten, gis-zones, addresses + `fixtures/source`-meta) naar een temp-root, laadt het pakket dáár, herleidt de volledige golden set tegen de geëxporteerde configuratie en vergelijkt canoniek (routing + status + ontvangst-referenties identiek). Rapport bevat de modelsubstitutie-notitie: replay is modelvrij (S1/S2 komen uit fixtures; de LLM-poot zit alleen achter de seams), dus "ander model, zelfde uitkomsten" is in de prototypefase aantoonbaar als "géén model, zelfde uitkomsten"; de productievariant (gateway + tweede model op dezelfde golden set) is F5+.
- `--rapport`-goNoGo verwerkt de exit-test-uitslag (zesde baseline-criterium).

- [ ] **Step 1: falende tests** — export bevat manifest+tabellen+golden+fixtures; herleiding op export geeft identieke canonieke routing per golden-scenario; gesaboteerde export (gewijzigde beslistabel) faalt de vergelijking (bewijst dat de test controleert).
- [ ] **Step 2: implementeren**; `python3 eval.py --exit` groen. Commit: `feat(poc-gent): exit-test — config-export + modelvrije herleiding van de golden set (F4)`.

### Task 4: EDIC-assetmap-registratie — voorbereid, geblokkeerd op NOVEX-werk

**Status:** geblokkeerd (geen commit). `nldt/recipes/edic-asset-map.json` bevat oncommitte, op schema vooruitlopende NOVEX-wijzigingen (`policyAlignmentSchema`); de Gent-entry wordt pas toegevoegd zodra dat werk gecommit is. Voorbereide entry (conform de gecommitte conventie, gespiegeld aan `recipe:thk-*`):

```json
{
  "id": "recipe:gent-mobiliteit-ondernemer",
  "kind": "recipe",
  "title": "Gent GT-MOB-01 — Voertuigtoegang stadcentrum voor ondernemers (transactioneel)",
  "path": "nldt/recipes/gent-mobiliteit-ondernemer.json",
  "edic": "ldt-citiverse",
  "assetClass": "hcs-life-event",
  "owner": "Digital Toolbox (EDIC)",
  "relationshipOwners": ["Stad Gent (EUROPAI WP3)", "Digital Vlaanderen"],
  "acceptance": "Golden set (13) + KPI-gates + injectiesuite + exit-test via eval.py; deterministische replay (gent-transactional-run, H1-H5)",
  "fallback": "vng-geonovum-cookbook",
  "readiness": "hybrid",
  "riskLevel": "medium"
}
```

- Actie na deblokkade: entry toevoegen (plus `policyAlignment`-blok conform de dan geldende conventie), `nldt`-test `test_edic_asset_map_schema_and_recipe_coverage` weer groen (dekt vandaag al rood: Gent-recipe mist in de gecommitte map). Commit dan: `feat(edic): Gent-transactievariant in assetmap (assetClass hcs-life-event)`.

### Task 5: README + zelfcheck

- Modify: `poc-gent/README.md` — F4-sectie: KPI-rapport + go/no-go (`python3 eval.py --rapport …`), injectiesuite, exit-test, EDIC-status (voorbereid/geblokkeerd), simulatietab-verwijzing.
- Zelfcheck: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` groen (aantal na taak 3 vastleggen); `python3 eval.py` → golden 13/13 + KPI-blok + `go/no-go: GO`; `python3 eval.py --injectie` → 32/32; `python3 eval.py --exit` → OK; sim-build + `node verify_static.mjs` ongewijzigd groen.

## Zelfcheck na afronding (executeur)

1. `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → groen (baseline 123 + F4-eigen tests).
2. `python3 eval.py` → `golden: 13/13`, `determinisme: OK`, KPI-blok alles ≥ min. aanvaard, `go/no-go: GO`, exit 0.
3. `python3 eval.py --injectie` → `32/32`, 0 open bevindingen, exit 0.
4. `python3 eval.py --exit` → herleiding identiek, exit 0.
5. EDIC: geen commit in `nldt/recipes/edic-asset-map.json` (geblokkeerd); voorbereide entry staat in dit plan.
