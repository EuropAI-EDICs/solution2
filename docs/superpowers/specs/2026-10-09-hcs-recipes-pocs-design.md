# Ontwerp — Human-Centred Services recipes als demonstrabele PoC's (EDIC × LDT toolbox)

| | |
|---|---|
| **Datum** | 9 oktober 2026 · v1.1 (herzien na review: meerdere **volwaardige** PoC's per dish — 11 recipes over alle vijf dishes) |
| **Status** | ontwerp; ter review van Marc. Scope is in review vastgesteld: per dish 2–3 recipes als volwaardig PoC. Open punten staan bij §8 |
| **Scope** | de documenten in `recipes/` (Human-Centred Services Blueprint A1-plate, draft 8 okt 2026 + KPI-framework per recipe) omzetten in **elf demonstrabele PoC's** — per dish 2–3 recipes — conform (a) de ldttoolbox recipe-methode (`nldt/04-recipes-and-processes.md`: AppStore → Cookbook → Cook, recipe-schema, OGC API Processes) en (b) de agentic-state-procedure (`docs/AGENTIC_STATE_PLAN.md` v1.2: functie-first, vijf poorten, mens-agent-grens, leerstaat) |
| **Buiten scope** | echte LLM-stappen via deep-agents (fase 3-optie, benadering C) · uitbreiding van de bestuurdersdemo (fase 3-optie) · de overige 42 recipes als volwaardig PoC (zij verschijnen wél als kaarten in de menu-demo) · wijzigingen aan de bron-documenten in `recipes/` · committen van `recipes/` zelf (gebruikersbesluit) |
| **Bronnen** | [`recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf`](../../../recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf) (The Key · Recipe book · MijnServices · Common Ground; vijf stappen; GenAI-testbank G1–G5; anatomy of a recipe; recipe-cyclus; scale path; menu van 53 recipes over vijf dishes) · [`recipes/05_KPI-framework_per-recipe.xlsx`](../../../recipes/05_KPI-framework_per-recipe.xlsx) (KPI's per recipe met output/outcome, outcome-lens Z/L/W, baseline/target/actual, KVI-rollup; sheet *The Key × PDC* met wetsgrondslag, tijdslimiet, partijen, menselijke maat en G-punten per THK; sheet *Recipes* met stappen per recipe) · [`nldt/04-recipes-and-processes.md`](../../../nldt/04-recipes-and-processes.md) · [`docs/AGENTIC_STATE_PLAN.md`](../../AGENTIC_STATE_PLAN.md) v1.2 + gap-analyse · patroonvoorbeeld: `nldt/simulation/regelrecht/` (build-script + gegenereerde runs + single-file demo) |

## 0. Kern van het ontwerp

De blueprint en het KPI-framework passen opmerkelijk precies op de agentic-state-procedure die dit repo al volgt:

| Blueprint-element | Agentic state (Sitra/whitepaper) | Landingsplaats in de toolbox |
|---|---|---|
| Life event ("I want to move home") | **B1** — de functie als gedeeld niveau | nieuw recipe-JSON in `nldt/recipes/` |
| Vijf stappen per recipe (intake → solution → contract → delivery → follow-up) | **B2/−1** — workflow-niveau; mens-agent-grens **binnen** de workflow | steps in het recipe + run-artefact |
| Menselijke maat / handover-punten (bv. "adresonderzoek bij twijfel → medewerker") | **B8 + poort 3** — mens-agent-grens en juridische grens | `service.humanMeasure` in het recipe, uitgevoerd in het run-artefact |
| GenAI-testpunten G1–G5 + testbank (personas incl. edge cases, go/no-go) | **poort 3 + poort 5** — grenzen en bewijs/stopcondities | `service.genAiTestPoints` + testbank-paneel in de demo's |
| KPI-framework (baseline/target/actual, outcome-lens, KVI-rollup) | **poort 1 + poort 5** — baseline vóór technologie; bewijs en stopcondities | `function-baseline.json` per recipe (plan §3, nieuw first-class artefact) |
| MijnServices + Common Ground als ingredients | **B7/B11 + poort 4** — duurzaam werk, vervangbare architectuur | `requiredProcesses`/ingredients van het recipe |
| Recipe-formaat zelf ("anatomy of a recipe") — *zelfde format, testprotocol en KPI-framework voor alle 53* | **B11/B12** — herbruikbare capability-kern als open specificatie | uitbreiding `nldt/schemas/recipe.schema.json` met optioneel `service`-blok |
| Recipe-cyclus (design → … → measure & improve) | **B10/B13** — leerstaat en function steward | leerstaat-strip in de demo's; KPI-events rollen terug naar recipe-owner |
| EDIC adopteert plaat, format, testprotocol | adoptiekader | `nldt/recipes/edic-asset-map.json` (bestaat al) |

**Het ontwerp in één zin:** elf recipes uit alle vijf dishes worden echte nldt-recipes (cookbook + catalogus + EDIC-adoptie + function-baseline), draaibaar via twee nieuwe replay-processen op de bestaande harness, en krijgen zes demo-pagina's in de vertrouwde Mistral-stijl — één per dish plus de interactieve menu-plaat — waarin de vijf stappen, de G1–G5-testbank, de mens-agent-grens en de KPI-baseline concreet zichtbaar zijn.

## 1. PoC-keuze: elf recipes over vijf dishes

Selectiecriteria per dish: (a) best gedocumenteerd in het xlsx (PDC-koppeling, stappen, KPI's), (b) draait op bestaande toolbox-engines (ruimtelijke processen, tijdreeksen, gebiedschecks), (c) samen dekken ze alle serviceTypes af (reactive, proactive, measure, plan, share, system, infrastructure) zodat de generiekiteit van het format zichtbaar wordt.

| Dish | PoC-recipes (2–3 per dish) | Type | Waarom deze | G-punten | risk |
|---|---|---|---|---|---|
| **The Key** (3) | `thk-08-move-home` — "Ik ga verhuizen" | reactive · publiek-privaat | het blueprint-voorbeeld zelf; dikst gedocumenteerd in *The Key × PDC* (PDC-vraag 8 + 6, Wet BRP/Omgevingswet, vijf externe partijen, mensmaat: adresonderzoek → medewerker); de **diepe dwarsdoorsnede** van de vijf stappen | G1 (alleen vragen wat niet in de BRP staat) · G4 (orkestratie over partijen) — per sheet | medium |
| | `thk-24-build-renovate` — "Ik wil bouwen of renoveren" | reactive · publiek-privaat | **de brug naar het RO-domein**: vergunningcheck via het Omgevingsloket hergebruikt de bestaande `minigim-gebiedscheck`-recipe als ingredient (capability-kern in actie); 8-weken-klok; de mens blijft aan de beoordeling | voorstel: G1 (plan in eigen woorden) · G2 (vergunningcheck) · G3 (documentcheck) — *voorlopig* | high |
| | `thk-02-having-a-baby` — "Ik krijg een kind" | reactive → proactive | derde type binnen de dish: **proactief** signaleren (kinderbijslag, toeslagen; G2·G5 per sheet), kettingpartijen (SVB, Belastingdienst, zorgverzekeraar), harde termijn (melding binnen 5 dagen) | G2 · G5 — per sheet | medium |
| **Urban Air Mobility** (2) | `uam-01-medical-logistics` — "Ik wil medische logistiek per lucht" | cargo | ziekenhuis → monster → dronecorridor → lab; outcome-KPI "delivery-time reduction vs road" (lens **W**, resilience); corridors zijn ruimtelijke objecten → demonstrabel met bestaande processen | voorstel: G2 (corridor-matching) · G4 (status-uitleg keten) — *voorlopig* | medium |
| | `uam-09-geofencing-zones` — "Ik wil geofencing & security zones" | infrastructure · security | no-fly- en gevoelige-locatiezones → Identity of Things → handhaving; KPI via geo-registry; **puur ruimtelijk** (`fetch-features` + `spatial-intersection` + `h3-*`) en de tegenhanger van corridors (zones vs routes) | voorstel: G2 (zonedefinitie) · G5 (signaal bij schending) — *voorlopig* | high |
| **3-30-300** (2) | `grn-01-canopy-measure` — "Ik wil het groendak meten (de 30%)" | measure | remote sensing → AI-canopy-map → gap-heat-map per wijk; draait op `fetch-features`, `h3-polygon-to-cells`, `compute-area-statistics`; lens L·W | voorstel: G2 (beeld-analyse) · G5 (proactief signaal bij nieuwe groei-gaps) — *voorlopig* | low |
| | `grn-03-300m-gaps` — "Ik wil de 300-meter-gaten dichten" | plan + green | loopbaarheidsanalyse → groene woestijnen → eerst vergroenen; `h3-grid-disk`-proximityringen + `h3-knn` maken dit deterministisch demonstrabel; lens Z·L | voorstel: G2 (analyse) · G5 (signaal groene woestijnen) — *voorlopig* | low |
| **Circular neighborhoods** (2) | `cir-04-shared-energy` — "Ik wil gedeelde energie" | share · energy | bewoners-eigen opwekking → gedeelde warmte/koude-netwerken → batterij; KPI "energy generated locally" (lens Z·W); **tijdreeksdemonstratie** via de bestaande timeseries-processen | voorstel: G2 (matching opwek-verbruik) · G4 (verdeling/uitleg) — *voorlopig* | medium |
| | `cir-01-circular-condition` — "Ik wil een circulaire ontwikkelingsvoorwaarde" | system | grondtender → circulariteit als harde eis → ontwerp; KPI "circular/reused material %" (lens W); tweede RO-brug (aanbesteding/ruimtelijke ontwikkeling) naast THK-24 | voorstel: G2 (tender-toets) · G3 (bewijsstukken) — *voorlopig* | medium |
| **15-minute city** (2) | `min-01-proximity-analysis` — "Ik wil een nabijheidsanalyse" | measure | isochronen → bereikbare voorzieningen → servicedeserts; KPI "residents within 15 min" (lens Z·L); zelfde meetpatroon als GRN-03 in een ander domein — bewijst dat het meet-recipe generaliseert | voorstel: G2 (analyse) · G5 (signaal deserts) — *voorlopig* | low |
| | `min-04-hub-network` — "Ik wil mijn hub-netwerk plannen" | plan · hub ladder | hubladder (micro → wijk → stadsdeel → stad, de NextPole-ladder van de plaat); KPI "hubs live per tier"; hiërarchische h3-ringdelen per tier | voorstel: G2 (hub-plaatsing) · G5 (proactief signaal dekkingsgat) — *voorlopig* | low |

**Vallen buiten de volwaardige set maar zijn wel zichtbaar:** de overige 42 recipes verschijnen als kaarten (naam, code, type, KPI's, KVI-rollup) in de menu-demo per dish — de recipe-book-hiërarchie menu → dish → recipe is dus volledig zichtbaar, met elf doorklikbare, uitgewerkte voorbeelden. **Scope-klep:** als een fase onder tijdsdruk komt, schuiven `min-04-hub-network` of `cir-01-circular-condition` door naar menu-scène; het The Key-trio is de onherlebbare kern.

## 2. Benaderingen

| | A — PoC's volgens het nldt-PoC-patroon **(gekozen)** | B — alleen demo-laag | C — volledig draaiend |
|---|---|---|---|
| Inhoud | 11 recipe-JSON's + baselines + twee replay-processen + zes demo's + mappingdoc | statische HTML-demo's + indexsectie | A + echte LLM-intake/orkestratie via deep-agents op lokale modellen |
| Conform recipe-methode | ja: cookbook, catalogus, processen, schema | nee — niets landt in de cookbook | ja |
| Conform agentic state | ja: poorten en grenzen zijn data, niet verhaal | alleen als verhaal | ja, plus live demonstratie |
| Kosten/risico | gemiddeld; deterministisch, geen modelafhankelijkheid | laag | hoog; modelkwaliteit wordt een demo-risico |
| Afweging | **biedt beide eisen en blijft demonstrabel zonder LLM** — C blijft beschikbaar als fase 3 | faalt aan beide eisen | uitstelbaar: de waarde van de PoC zit in format/procedure, niet in modelvermogen |

## 3. Architectuur

### 3.1 Recipe-laag (Cookbook + AppStore)

**Schema-uitbreiding.** `nldt/schemas/recipe.schema.json` krijgt één optioneel property `service` (additief; `additionalProperties: false` blijft intact voor bestaande recipes). Het blok is de EDIC-*anatomy of a recipe* 1-op-1 naast de bestaande orchestration-velden:

```
service: {
  dish: "the-key" | "urban-air-mobility" | "3-30-300" | "circular-neighborhoods" | "15-minute-city",
  lifeEventCode: "THK-08",           // optioneel; city-recipes hebben een UAM/GRN/CIR/MIN-code
  serviceType: "reactive" | "proactive" | "measure" | "plan" | "share" | "system" | "infrastructure",
  blueprintSteps: [1..5],            // welke van de vijf blueprint-stappen het recipe raakt (life events)
  parties: [{ name, role }],         // publiek + privaat, uit The Key × PDC (of dish-passend)
  legalBasis: [{ basis, timeLimit }],
  humanMeasure: { handover: [..], exceptions: [..] },
  localVariant: "...",               // gemeentelijke beleidsvrijheid
  genAiTestPoints: [{ point: "G1".."G5", description, testCases: [..] }],
  kpis: [{ kpi, kpiType: "output"|"outcome", unit, outcomeLens: "Z"|"L"|"W"|"—",
            baseline, target, dataSource, frequency, kviRollup }]
}
```

**Elf recipes** in `nldt/recipes/` (auto-ontdekt via `list_recipe_ids()` en gevalideerd door de bestaande `load_recipe()`-tests), zie de tabel in §1. De steps verschillen per serviceType: life events volgen de vijf blueprint-stappen; measure/plan-recipes volgen hun eigen keten uit de *Recipes*-sheet (bv. GRN-01: imagery → canopy map → gap heat-map); THK-24 en CIR-01 koppelen een bestaande toolbox-recipe (`minigim-gebiedscheck`) als ingredient.

**EDIC-adoptie.** Per recipe een asset-entry in `nldt/recipes/edic-asset-map.json` (`assetClass: "hcs-life-event"` resp. `"hcs-city-recipe"`, owner Digital Toolbox/EDIC, readiness, acceptance) — de "WHAT THE EDIC ADOPTS"-kolom van de plaat landt in het bestaande adoptieregister.

**Function-baseline (poort 1 + 5).** Per recipe `nldt/recipes/baselines/<id>.baseline.json` (nieuw schema `nldt/schemas/hcs-baseline.schema.json`): publieke uitkomst, baseline-KPI's (letterlijk uit het xlsx), stopcondities (go/no-go-criteria uit de testbank; per-type drempels, bv. "bij >x% mens-overnames bij stap 1: pauzeren"). De subdir blijft buiten de recipe-loader (`glob("*.json")` is non-recursief — geen `NON_RECIPE_STEMS`-wijziging nodig).

### 3.2 Proces-laag (Cook)

Twee nieuwe replay-processen in `nldt/services/process_adapter/poc_handlers.py` (patroon van de bestaande PoC-processen; journal-events via `execute_local` komen gratis):

1. **`hcs-life-event-run`** — de vijf-stappen-burgerreis (THK-08, THK-02; THK-24 in combinatie met de gebiedscheck-stap). Inputs: `recipeId`, `persona`, `mode: replay|execute`. Output: run-artefact conform **`nldt/schemas/hcs-run.schema.json`**.
2. **`hcs-recipe-run`** — generieke deterministische replay voor de city-recipes (UAM-01/09, GRN-01/03, CIR-01/04, MIN-01/04): de steps komen uit het recipe zelf (zelfde `steps[]`-mechanisme), met per serviceType een vast step-sjabloon en fixtures per scenario (corridor, zone, wijk, hub-netwerk). Zelfde run-artefact-schema.

Run-artefact (beide processen): `steps[] { stepId, actor: agent|mens|partij, genAiTestPoint, dataUsed[], consent, handover: null|{reason, to}, kpiEvents[], prov: {sources[]} }` + `stopConditions[]` (poort 5) + scenario/persona + KPI-snapshot.

**Fixtures en build-script.** `nldt/simulation/hcs/fixtures/` — gedeeld model: personas incl. edge cases (testbank-stap 2: lage geletterdheid, andere taal, schulden), partijen, attestaties; per recipe een scenariobestand (voor city-recipes: wijk/corridor/hub-scenario in plaats van persona) en gouden uitslagen. `nldt/simulation/hcs/build_runs.py --stamp <ts>` (patroon `regelrecht/build_runs.py`) genereert alle `runs/*.json` voor de demo's.

### 3.3 Agentic-state-laag (de procedure, expliciet)

Per PoC wordt de procedure uit `AGENTIC_STATE_PLAN.md` uitgevoerd, niet alleen geciteerd:

1. **Poort 1** — baseline vóór technologie: `baselines/<id>.baseline.json` uit het xlsx (herontwerp vóór inkoop: de demo toont ook welke stap *verdwijnt*, B5).
2. **Poort 2** — gedeelde betekenis: alleen autoritatieve bronnen met herkomst (BRP/Haal Centraal, EUDI-attestaties, remote sensing, grid/meter-data) — `dataUsed[]` + `prov.sources[]` per stap.
3. **Poort 3** — mens-agent-grens: per stap `actor` + `handover` in het run-artefact, gevuld uit de *human measure* van de sheet; de G1–G5-testbank draait in de demo's als scenario-uitslagen (accuracy, plain language, once-only, explainability, handover, bias, AI Act risk class) met go/no-go.
4. **Poort 4** — vervangbare architectuur: MijnServices/Common Ground-componenten staan als ingredients/requiredProcesses in het recipe — de demo's tonen per stap welk vervangbaar component wordt gebruikt.
5. **Poort 5** — bewijs en stopcondities: baselines + testbank-uitslagen + stopcondities in run en demo.

**Leerstaat (B10).** `kpiEvents[]` rollen naar de recipe-owner (recipe-cyclus stap 6); in de demo's zichtbaar als leerstaat-strip (wat gebeurde, waarom, wat moet veranderen, wie beslist, hielp het).

**Mappingdoc.** `docs/HCS_RECIPES_AGENTIC_STATE.md`: de koppeltabel van §0 uitgewerkt met per dish/PoC de grens-tabel — de conformiteitsverklaring richting het agentic-state-plan.

### 3.4 Demo-laag (`nldt/simulation/`, Mistral-donker palet)

**Eén demo per dish plus de menu-plaat** — de recipe-book-hiërarchie (menu → dish → recipe, meerdere recipes per dish) is zo de navigatiestructuur zelf:

| Demo | Taal | Inhoud |
|---|---|---|
| `hcs-key-demo.html` (+ `-en`) | NL + EN | **The Key**: de diepe vijf-stappen-run van THK-08 (intake in eigen woorden G1; één samenhangend voorstel G2; consent "wie ziet wat" G3; orkestratie + wallet-attestatie G4; proactieve follow-up + "stuck? mens neemt over" G5) met persona-switcher incl. edge cases; scène THK-02 (proactief signaal → melding binnen 5 dagen); scène THK-24 (brug: vergunningcheck → minigim-gebiedscheck → menselijke beoordeling, 8-weken-klok); sibling-kaarten van de overige 22 THK-recipes; testbank- en KPI-panelen; leerstaat-strip |
| `hcs-uam-demo.html` | NL | **Urban Air Mobility**: UAM-01 corridor-run (ziekenhuis → lab, tijdswinst vs weg) + UAM-09 geofencing-zones (Leaflet, tile-invert, zones ∩ corridors via bestaande processen); sibling-kaarten UAM-02…08 |
| `hcs-grn-demo.html` | NL | **3-30-300**: GRN-01 canopy-heat-map + GRN-03 300-meter-proximityringen en groei-deserts; sibling-kaarten GRN-02/04/05 |
| `hcs-cir-demo.html` | NL | **Circular neighborhoods**: CIR-04 gedeelde energie met tijdreeksgrafiek + CIR-01 circulaire ontwikkelingsvoorwaarde (tender-flow); sibling-kaarten CIR-02/03/05…09 |
| `hcs-min-demo.html` | NL | **15-minute city**: MIN-01 nabijheidsanalyse/servicedeserts + MIN-04 hubladder per tier; sibling-kaarten MIN-02/03/05 |
| `hcs-menu-demo.html` | NL | **de plaat interactief**: zeven lagen × vijf stappen, vijf dishes met alle 53 recipes als kaarten (code, naam, type, KPI's, KVI-rollup — de elf PoC's gemarkeerd en doorklikbaar), KPI-rollup (recipes → KPI's → strategieën → KVI's → self-reliance/liveability/resilience), recipe-cyclus en scale path |

Plus: indexsectie "Human-Centred Services — EDIC recipe PoC's" in `nldt/simulation/index.html` (patroon: story + agent flow + extra's), en rijen in `nldt/simulation/README.md` en `nldt/04-recipes-and-processes.md` (catalogus + korte HCS-paragraaf). De elf city- en life-event-run-artefacten delen één bron van waarheid: fixtures → build-script → runs → demo.

### 3.5 Grenzen van het ontwerp

- Geen nieuwe front-end-stack: single-file HTML met embedded/generated JSON, zelfde palet en scene-patroon als de bestaande demo's.
- Geen LLM: alle agent-stappen zijn deterministische replay-uitvoeringen; de *vorm* (gates, handovers, citatie van bron) is wat gedemonstreerd wordt. Echte LLM-stappen = fase 3 (benadering C).
- De demo's dienen twee doelen tegelijk (bestuurlijk verhaal + technisch bewijs) maar delen één bron van waarheid; niets wordt dubbel onderhouden.
- Kaarten van de 42 niet-uitgewerkte recipes zijn statische data uit het xlsx (geen runs, geen baselines) — bewust, want "volwaardig" geldt alleen voor de elf.

## 4. Bestanden

| Actie | Bestand |
|---|---|
| wijzig | `nldt/schemas/recipe.schema.json` (optioneel `service`-blok) |
| nieuw | `nldt/schemas/hcs-run.schema.json`, `nldt/schemas/hcs-baseline.schema.json` |
| nieuw | 11 recipes in `nldt/recipes/`: `thk-08-move-home`, `thk-24-build-renovate`, `thk-02-having-a-baby`, `uam-01-medical-logistics`, `uam-09-geofencing-zones`, `grn-01-canopy-measure`, `grn-03-300m-gaps`, `cir-04-shared-energy`, `cir-01-circular-condition`, `min-01-proximity-analysis`, `min-04-hub-network` (alle `.json`) |
| nieuw | 11 baselines in `nldt/recipes/baselines/<id>.baseline.json` |
| wijzig | `nldt/recipes/edic-asset-map.json` (elf asset-entries) |
| wijzig | `nldt/services/process_adapter/poc_handlers.py` (`hcs-life-event-run`, `hcs-recipe-run`) |
| nieuw | `nldt/simulation/hcs/` — `fixtures/`, `build_runs.py`, gegenereerde `runs/` |
| nieuw | `nldt/simulation/hcs-key-demo.html` (+ `-en`), `hcs-uam-demo.html`, `hcs-grn-demo.html`, `hcs-cir-demo.html`, `hcs-min-demo.html`, `hcs-menu-demo.html` |
| wijzig | `nldt/simulation/index.html`, `nldt/simulation/README.md`, `nldt/04-recipes-and-processes.md` |
| nieuw | `docs/HCS_RECIPES_AGENTIC_STATE.md` |
| nieuw | tests: schema-validatie runs/baselines, replay-determinisme beide processen, menu-data consistent met xlsx |

## 5. Testen en verificatie

1. **Schema:** de bestaande recipe-tests valideren de elf nieuwe recipes automatisch (`load_recipe`); nieuwe tests voor `hcs-run`- en `hcs-baseline`-schema's en de elf baseline-bestanden.
2. **Proces:** replay-determinisme voor beide processen (zelfde inputs → identieke run behalve stamp), golden-fixtures per persona/scenario, in-pagina engine-selftest met vast aantal checks (zoals de regelrecht-selftest 16/16).
3. **Demo's:** build-script reproduceerbaar (`--stamp`); menu-data afgeleid uit het xlsx met een consistentietest (53 recipes, KPI-velden matchen); visuele gate via de visual-judge op gerenderde pagina's (palet, leesbaarheid, scènes).
4. **Regressie:** volledige nldt-testsuite groen; bestaande recipes ongewijzigd geldig onder het uitgebreide schema.

## 6. Fasering

- **Fase 1 — The Key end-to-end:** schema-uitbreiding, beide processen, de drie THK-recipes + baselines + EDIC-entries, fixtures + build-script, `hcs-key-demo` NL/EN, menu-demo-skelet, indexsectie, mappingdoc-skelet.
- **Fase 2 — city dishes:** de acht city-recipes + baselines + EDIC-entries + scenario-fixtures + runs, vier dish-demo's, menu-demo volledig (53 kaarten + rollup), mappingdoc volledig.
- **Fase 3 (optioneel):** EN-tweelingen van de overige dish-demo's, één scène in de bestuurdersdemo ("de functie als recipe"), echte LLM-intake via deep-agents (benadering C).

Elke fase levert op zichzelf een demonstrabel resultaat; fase 1 is de smalle dwarsdoorsnede (één dish, alle lagen, twee processen) waarop fase 2 uitbreidt.

## 7. Succescriteria

1. Elf schema-geldige recipes in de cookbook, auto-ontdekt, met EDIC-asset-entries en function-baselines; alle 53 recipes zichtbaar in de menu-demo per dish.
2. `run-recipe thk-08-move-home` en de city-recipes via `hcs-recipe-run` (of OGC API Processes) leveren geldige run-artefacten met expliciete mens-agent-grens, bronherkomst en stopcondities.
3. Zes demo's in de vertrouwde stijl, bereikbaar vanuit de index, met werkende scenario-switcher, testbank-uitslagen en KPI-panelen; de recipe-book-hiërarchie (dish → meerdere recipes) is de navigatiestructuur.
4. De mappingdoc koppelt elk blueprint-element aan Sitra-block, poort, whitepaper-laag en landingsplaats.
5. Test-suite groen; geen wijzigingen aan bestaande recipes.

## 8. Aannames en open punten voor review

1. **Scope:** in review vastgesteld — meerdere volwaardige PoC's per dish; de verdeling 3/2/2/2/2 met de genoemde elf staat ter bevestiging. Scope-klep bij tijdnood: `min-04` of `cir-01` naar menu-scène.
2. **G-punten** van de city-recipes en THK-24 zijn in dit ontwerp voorgesteld (de sheet *The Key × PDC* gaf alleen THK-01…THK-10); bij review bevestigen of corrigeren.
3. **Taal:** NL primair; EN-tweeling alleen voor de The Key-demo (patroon van de bestaande demo's). Andere verdeling is goedkoop te wijzigen.
4. **`recipes/` in git:** de bron-documenten staan nu untracked; committen is een gebruikersbesluit en valt buiten dit ontwerp.
5. **Recipe-naming:** `<code>-<slug>` (bv. `thk-08-move-home`); het schema-patroon staat dit toe. Alternatief is pure beschrijving (`move-home`).
