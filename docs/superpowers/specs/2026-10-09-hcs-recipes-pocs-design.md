# Ontwerp — Human-Centred Services recipes als demonstrabele PoC's (EDIC × LDT toolbox)

| | |
|---|---|
| **Datum** | 9 oktober 2026 |
| **Status** | ontwerp; ter review van Marc. Let op: de scope-vraag (welke recipes) bleef onbeantwoord in de sessie; de aanbevolen optie is aangehouden en staat als open punt bij §8 |
| **Scope** | de documenten in `recipes/` (Human-Centred Services Blueprint A1-plate, draft 8 okt 2026 + KPI-framework per recipe) omzetten in **drie demonstrabele PoC's** conform (a) de ldttoolbox recipe-methode (`nldt/04-recipes-and-processes.md`: AppStore → Cookbook → Cook, recipe-schema, OGC API Processes) en (b) de agentic-state-procedure (`docs/AGENTIC_STATE_PLAN.md` v1.2: functie-first, vijf poorten, mens-agent-grens, leerstaat) |
| **Buiten scope** | echte LLM-stappen via deep-agents (fase 3-optie, benadering C) · uitbreiding van de bestuurdersdemo (fase 3-optie) · wijzigingen aan de bron-documenten in `recipes/` · committen van `recipes/` zelf (gebruikersbesluit) · de overige 50 recipes uit het framework |
| **Bronnen** | [`recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf`](../../../recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf) (The Key · Recipe book · MijnServices · Common Ground; vijf stappen; GenAI-testbank G1–G5; anatomy of a recipe; recipe-cyclus; scale path; menu van 53 recipes over vijf dishes) · [`recipes/05_KPI-framework_per-recipe.xlsx`](../../../recipes/05_KPI-framework_per-recipe.xlsx) (KPI's per recipe met output/outcome, outcome-lens Z/L/W, baseline/target/actual, KVI-rollup; sheet *The Key × PDC* met wetsgrondslag, tijdslimiet, partijen, menselijke maat en G-punten per THK) · [`nldt/04-recipes-and-processes.md`](../../../nldt/04-recipes-and-processes.md) · [`docs/AGENTIC_STATE_PLAN.md`](../../AGENTIC_STATE_PLAN.md) v1.2 + gap-analyse · patroonvoorbeld: `nldt/simulation/regelrecht/` (build-script + gegenereerde runs + single-file demo) |

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
| Recipe-formaat zelf ("anatomy of a recipe") | **B11/B12** — herbruikbare capability-kern als open specificatie | uitbreiding `nldt/schemas/recipe.schema.json` met optioneel `service`-blok |
| Recipe-cyclus (design → … → measure & improve) | **B10/B13** — leerstaat en function steward | leerstaat-strip in de demo's; KPI-events rollen terug naar recipe-owner |
| EDIC adopteert plaat, format, testprotocol | adoptiekader | `nldt/recipes/edic-asset-map.json` (bestaat al) |

**Het ontwerp in één zin:** drie life-event/meet-recipes uit de plaat worden echte nldt-recipes (cookbook + catalogus + EDIC-adoptie), draaibaar via één nieuw replay-proces op de bestaande harness, en krijgen drie demo-pagina's in de vertrouwde Mistral-stijl waarin de vijf stappen, de G1–G5-testbank, de mens-agent-grens en de KPI-baseline concreet zichtbaar zijn.

## 1. PoC-keuze (aanbevolen scope)

| PoC | Recipe | Dish | Waarom deze | G-punten | risk |
|---|---|---|---|---|---|
| **HCS-1** | `thk-08-move-home` — "Ik ga verhuizen" | The Key | het blueprint-voorbeeld zelf; dikst gedocumenteerd in *The Key × PDC* (PDC-vraag 8 + 6, Wet BRP/Omgevingswet, vijf externe partijen, mensmaat: adresonderzoek → medewerker, KPI: "moves processed without manual handling", lens Z) | G1 (intake vraagt alleen wat niet in de BRP staat) · G4 (agentic orchestration over partijen) — per sheet; G2/G3/G5 komen in de demo als volledige vijf-stappen-run | medium |
| **HCS-2** | `thk-24-build-renovate` — "Ik wil bouwen of renoveren" | The Key (nieuw) | **de brug naar het RO-domein van deze toolbox**: vergunningcheck via het Omgevingsloket raakt aan de bestaande engines (minigim-gebiedscheck, Breda gebiedsafweging, Utrecht-scenario's) — toont de herbruikbare capability-kern: een life-event-recipe die een bestaande toolbox-recipe als ingredient gebruikt | voorstel: G1 (plan in eigen woorden) · G2 (vergunningcheck/matching) · G3 (documentcheck) — *voorlopig, zie §8* | high |
| **HCS-3** | `grn-01-canopy-measure` — "Ik wil het groendak meten (de 30%)" | 3-30-300 | **breedte**: een meet-recipe (geen life event) die op bestaande processen draait (`fetch-features`, `h3-polygon-to-cells`, `compute-area-statistics`) — bewijst de claim "same recipe format, test protocol and KPI framework for all 53 recipes" over dishes heen; KPI: canopy % per wijk, lens L·W | voorstel: G2 (matching/beeld-analyse) · G5 (proactief signaal bij nieuwe groei-gaps) — *voorlopig, zie §8* | low |

Alternatieven die zijn overwegen en verworpen: alleen THK-08 (max diepgang, maar toont niet de generieke methode), en één recipe per dish (toont generiekiteit, maar alles blijft oppervlakkig en de brug naar het RO-domein ontbreekt).

## 2. Benaderingen

| | A — PoC's volgens het nldt-PoC-patroon **(gekozen)** | B — alleen demo-laag | C — volledig draaiend |
|---|---|---|---|
| Inhoud | recipe-JSON's + baseline + replay-proces + demo's + mappingdoc | drie statische HTML-demo's + indexsectie | A + echte LLM-intake/orkestratie via deep-agents op lokale modellen |
| Conform recipe-methode | ja: cookbook, catalogus, proces, schema | nee — niets landt in de cookbook | ja |
| Conform agentic state | ja: poorten en grenzen zijn data, niet verhaal | alleen als verhaal | ja, plus live demonstratie |
| Kosten/risico | gemiddeld; deterministisch, geen modelafhankelijkheid | laag | hoog; modelkwaliteit wordt een demo-risico |
| Afweging | **biedt beide eisen en blijft demonstrabel zonder LLM** — C blijft beschikbaar als fase 3 | faalt aan beide eisen | uitstelbaar: de waarde van de PoC zit in format/procedure, niet in modelvermogen |

## 3. Architectuur

### 3.1 Recipe-laag (Cookbook + AppStore)

**Schema-uitbreiding.** `nldt/schemas/recipe.schema.json` krijgt één optioneel property `service` (additief; `additionalProperties: false` blijft intact voor bestaande recipes). Het blok is de EDIC-*anatomy of a recipe* 1-op-1 naast de bestaande orchestration-velden:

```
service: {
  dish: "the-key" | "urban-air-mobility" | "3-30-300" | "circular-neighborhoods" | "15-minute-city",
  lifeEventCode: "THK-08"            // optioneel; meet-recipes hebben die niet
  serviceType: "reactive" | "proactive" | "measure" | "value",
  blueprintSteps: [1..5],            // welke van de vijf blueprint-stappen het recipe raakt
  parties: [{ name, role }],         // publiek + privaat, uit The Key × PDC
  legalBasis: [{ basis, timeLimit }],
  humanMeasure: { handover: [..], exceptions: [..] },
  localVariant: "...",               // gemeentelijke beleidsvrijheid
  genAiTestPoints: [{ point: "G1".."G5", description, testCases: [..] }],
  kpis: [{ kpi, kpiType: "output"|"outcome", unit, outcomeLens: "Z"|"L"|"W"|"—",
            baseline, target, dataSource, frequency, kviRollup }]
}
```

**Drie recipes** in `nldt/recipes/` (auto-ontdekt via `list_recipe_ids()` en gevalideerd door de bestaande `load_recipe()`-tests): `thk-08-move-home.json`, `thk-24-build-renovate.json`, `grn-01-canopy-measure.json`. THK-08's steps mappen op `hcs-life-event-run`; THK-24 combineert `hcs-life-event-run` met de bestaande `minigim-gebiedscheck`-recipe als ingredient (laag-risico, generieke gebiedscheck — de V4-mens blijft aan de beoordeling); GRN-01 gebruikt uitsluitend bestaande processen (`fetch-features`, `h3-polygon-to-cells`, `compute-area-statistics`).

**EDIC-adoptie.** Per recipe een asset-entry in `nldt/recipes/edic-asset-map.json` (`assetClass: "hcs-life-event"` resp. `"hcs-measure"`, owner Digital Toolbox/EDIC, readiness, acceptance) — de "WHAT THE EDIC ADOPTS"-kolom van de plaat landt in het bestaande adoptieregister.

**Function-baseline (poort 1 + 5).** Per recipe `nldt/recipes/baselines/<id>.baseline.json` (nieuw schema `nldt/schemas/hcs-baseline.schema.json`): publieke uitkomst, baseline-KPI's (letterlijk uit het xlsx), stopcondities ("bij >x% mens-overnames bij stap 1: pauzeren", go/no-go-criteria uit de testbank). De subdir blijft buiten de recipe-loader (`glob("*.json")` is non-recursief — geen `NON_RECIPE_STEMS`-wijziging nodig).

### 3.2 Proces-laag (Cook)

Nieuw PoC-proces **`hcs-life-event-run`** in `nldt/services/process_adapter/poc_handlers.py` (patroon van de bestaande PoC-processen; journal-events via `execute_local` komen gratis):

- inputs: `recipeId` (thk-08 | thk-24), `persona` (hoofdpersoon of edge case), `mode: replay|execute` — beide deterministisch op fixtures (geen LLM in fase 1);
- output: run-artefact conform nieuw **`nldt/schemas/hcs-run.schema.json`**: `steps[] { stepId: intake|solution|contract|delivery|followup, actor: agent|mens|partij, genAiTestPoint, dataUsed[], consent, handover: null|{reason, to}, kpiEvents[] , prov: {sources[]} }` + `stopConditions[]` (poort 5) + persona + KPI-snapshot.

**Fixtures en build-script.** `nldt/simulation/hcs/fixtures/` (personas incl. edge cases uit testbank-stap 2: lage geletterdheid, andere taal, schulden; partijen; attestaties; per persona gouden uitslagen) + `nldt/simulation/hcs/build_runs.py --stamp <ts>` (patroon `regelrecht/build_runs.py`) → gegenereerde `runs/*.json` die de demo's inlezen.

### 3.3 Agentic-state-laag (de procedure, expliciet)

Per PoC wordt de procedure uit `AGENTIC_STATE_PLAN.md` uitgevoerd, niet alleen geciteerd:

1. **Poort 1** — baseline vóór technologie: `baselines/<id>.baseline.json` uit het xlsx (herontwerp vóór inkoop: de demo toont ook welke stap *verdwijnt*, B5).
2. **Poort 2** — gedeelde betekenis: alleen autoritatieve bronnen met herkomst (BRP/Haal Centraal, EUDI-attestaties; GRN-01: remote sensing) — `dataUsed[]` + `prov.sources[]` per stap.
3. **Poort 3** — mens-agent-grens: per stap `actor` + `handover` in het run-artefact, gevuld uit de *human measure* van de sheet; de G1–G5-testbank draait in de demo als persona-scenario's met uitslagen (accuracy, plain language, once-only, explainability, handover, bias, AI Act risk class) en go/no-go.
4. **Poort 4** — vervangbare architectuur: MijnServices/Common Ground-componenten staan als ingredients/requiredProcesses in het recipe — de demo toont per stap welk vervangbaar component wordt gebruikt.
5. **Poort 5** — bewijs en stopcondities: baselines + testbank-uitslagen + stopcondities in run en demo.

**Leerstaat (B10).** `kpiEvents[]` rollen naar de recipe-owner (recipe-cyclus stap 6); in de demo's zichtbaar als leerstaat-strip (wat gebeurde, waarom, wat moet veranderen, wie beslist, hielp het).

**Mappingdoc.** `docs/HCS_RECIPES_AGENTIC_STATE.md`: de koppeltabel van §0 uitgewerkt met per PoC de grens-tabel — de conformiteitsverklaring richting het agentic-state-plan.

### 3.4 Demo-laag (`nldt/simulation/`, Mistral-donker palet)

| Demo | Taal | Inhoud (scènes) |
|---|---|---|
| `hcs-move-home-demo.html` (+ `-en`) | NL + EN | de vijf blueprint-stappen als één doorlopende run: intake in eigen woorden (G1: alleen vragen wat niet in de BRP staat; edge case → adresonderzoek → medewerker), één samenhangend voorstel (G2), consent-scherm "wie ziet wat" per partij/periode (G3), orkestratie over partijen + attestatie in de wallet (G4), proactieve follow-up + "stuck? mens neemt over" (G5); persona-switcher (incl. edge cases); testbank-paneel; KPI-paneel (baseline/target/actual); leerstaat-strip. Leeft op gegenereerde run-JSON's + in-pagina engine-selftest (patroon regelrecht-demo) |
| `hcs-build-renovate-demo.html` | NL | de brug: plan → vergunningcheck (Omgevingsloket) → **aanroep bestaande gebiedscheck-recipe** → beoordeling (mens-agent-grens: de V4-mens beslist) → besluit met 8-weken-klok; toont capability-kern en hergebruik |
| `hcs-menu-demo.html` | NL | de plaat interactief: zeven lagen × vijf stappen, vijf dishes met recipe-teller (53), KPI-rollup (recipes → KPI's → strategieën → KVI's → self-reliance/liveability/resilience), recipe-cyclus en scale path; **GRN-01 uitgewerkt** als meet-scène met canopy-heat-map (Leaflet-stijl met tile-invert zoals de bestaande donkere kaartdemo's) |

Plus: indexsectie "Human-Centred Services — EDIC recipe PoC's" in `nldt/simulation/index.html` (patroon: story + agent flow + extra's), en rijen in `nldt/simulation/README.md` en `nldt/04-recipes-and-processes.md` (catalogus + korte HCS-paragraaf).

### 3.5 Grenzen van het ontwerp

- Geen nieuwe front-end-stack: single-file HTML met embedded/generated JSON, zelfde palet en scene-patroon als de bestaande demo's.
- Geen LLM: alle agent-stappen zijn deterministische replay-uitvoeringen; de *vorm* (gates, handovers, citatie van bron) is wat gedemonstreerd wordt. Echte LLM-stappen = fase 3 (benadering C).
- De demos dienen twee doelen tegelijk (bestuurlijk verhaal + technisch bewijs) maar delen één bron van waarheid: fixtures → build-script → runs → demo; niets wordt dubbel onderhouden.

## 4. Bestanden

| Actie | Bestand |
|---|---|
| wijzig | `nldt/schemas/recipe.schema.json` (optioneel `service`-blok) |
| nieuw | `nldt/schemas/hcs-run.schema.json`, `nldt/schemas/hcs-baseline.schema.json` |
| nieuw | `nldt/recipes/thk-08-move-home.json`, `thk-24-build-renovate.json`, `grn-01-canopy-measure.json` |
| nieuw | `nldt/recipes/baselines/thk-08-move-home.baseline.json` (+ THK-24, GRN-01) |
| wijzig | `nldt/recipes/edic-asset-map.json` (drie asset-entries) |
| wijzig | `nldt/services/process_adapter/poc_handlers.py` (`hcs-life-event-run`) |
| nieuw | `nldt/simulation/hcs/` — `fixtures/`, `build_runs.py`, gegenereerde `runs/` |
| nieuw | `nldt/simulation/hcs-move-home-demo.html` (+ `-en`), `hcs-build-renovate-demo.html`, `hcs-menu-demo.html` |
| wijzig | `nldt/simulation/index.html`, `nldt/simulation/README.md`, `nldt/04-recipes-and-processes.md` |
| nieuw | `docs/HCS_RECIPES_AGENTIC_STATE.md` |
| nieuw | tests: schema-validatie runs/baselines, replay-determinisme `hcs-life-event-run` |

## 5. Testen en verificatie

1. **Schema:** de bestaande recipe-tests valideren de drie nieuwe recipes automatisch (`load_recipe`); nieuwe tests voor `hcs-run`- en `hcs-baseline`-schema's en de drie baseline-bestanden.
2. **Proces:** replay-determinisme (zelfde inputs → byte-gelijke run behalve stamp), golden-fixtures per persona, in-pagina engine-selftest met vast aantal checks (zoals de regelrecht-selftest 16/16).
3. **Demo's:** build-script reproduceerbaar (`--stamp`); visuele gate via de visual-judge op gerenderde pagina's (palet, leesbaarheid, scènes).
4. **Regressie:** volledige nldt-testsuite groen; bestaande recipes ongewijzigd geldig onder het uitgebreide schema.

## 6. Fasering

- **Fase 1 — THK-08 end-to-end:** schema-uitbreiding, recipe + baseline + EDIC-entry, proces + fixtures + build-script, demo NL/EN, indexsectie, mappingdoc-skelet.
- **Fase 2 — THK-24 + menu:** brug-recipe met hergebruik, brug-demo, menu-demo met GRN-01-scène (GRN-01 recipe + baseline), mappingdoc volledig.
- **Fase 3 (optioneel):** EN-tweeling menu-demo, één scène in de bestuurdersdemo ("de functie als recipe"), echte LLM-intake via deep-agents (benadering C).

Elke fase levert op zichzelf een demonstrabel resultaat; fase 1 is de smalle dwarsdoorsnede waarop 2 terugvalt als tijd of review beperkt is.

## 7. Succescriteria

1. Drie schema-geldige recipes in de cookbook, auto-ontdekt, met EDIC-asset-entries en function-baselines.
2. `run-recipe thk-08-move-home` (en het proces via OGC API Processes) levert een geldig run-artefact met expliciete mens-agent-grens, bronherkomst en stopcondities.
3. Drie demo's in de vertrouwde stijl, bereikbaar vanuit de index, met werkende persona-switcher, testbank-uitslagen en KPI-panelen.
4. De mappingdoc koppelt elk blueprint-element aan Sitra-block, poort, whitepaper-laag en landingsplaats.
5. Test-suite groen; geen wijzigingen aan bestaande recipes.

## 8. Aannames en open punten voor review

1. **Scope-aanname:** de keuzevraag (welke recipes) bleef onbeantwoord; de aanbevolen optie is aangehouden (THK-08 + THK-24 + GRN-01). Alternatieven: alleen THK-08, of één recipe per dish.
2. **G-punten THK-24 en GRN-01** zijn in dit ontwerp voorgesteld (de sheet *The Key × PDC* gaf alleen THK-01…THK-10); bij review bevestigen of corrigeren.
3. **Taal:** NL primair; EN-tweeling alleen voor de THK-08-demo (patroon van de bestaande demo's). Andere verdeling is goedkoop te wijzigen.
4. **`recipes/` in git:** de bron-documenten staan nu untracked; committen is een gebruikersbesluit en valt buiten dit ontwerp.
5. **Recipe-naming:** `thk-08-move-home` volgt het lifeEventCode; alternatief is pure beschrijving (`move-home`). Schema-patroon staat beide toe.
