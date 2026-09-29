# Ontwerp — PoC-simulaties volgens het RegelRecht-principe (fase 1: Utrecht & Eindhoven)

| | |
|---|---|
| **Datum** | 29 september 2026 |
| **Status** | goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | `nldt/simulation/` (demo-omgeving), alleen-lezen bronartefacten uit `poc/` en `poc-bp2op/` |
| **Bronnen** | [POC_RULE_GRAPH.md](../../../docs/POC_RULE_GRAPH.md) · [POC_RULE_GRAPH_EINDHOVEN.md](../../../docs/POC_RULE_GRAPH_EINDHOVEN.md) · [POC_REGELRECHT_INTEGRATION.md](../../../docs/POC_REGELRECHT_INTEGRATION.md) · [2026-09-20-nldt-simulations-all-pocs-design.md](2026-09-20-nldt-simulations-all-pocs-design.md) |

## Context en doel

De simulatiemap bevat statische, handgeschreven HTML-demo's (story's, agent
flows, what-if) voor vier PoC's. De RegelRecht-integratieanalyse concludeert
dat de beide uitgewerkte PoC's (Utrecht: artikel → NormCard → FormalRule →
geolaag → zone; Eindhoven: bronregel → kennisbank → omzettabel-rij →
coverage) aan kunnen sluiten op het landelijke RegelRecht-platform
(wetgeving als gevalideerd YAML-contract, deterministische executie met
uitlegbare trace). Dit ontwerp herinricht de simulaties van beide PoC's
volgens ditzelfde principe — op twee niveaus tegelijk, conform de
besluitvorming:

1. **inhoud**: de demo's vertellen en tonen de RegelRecht-keten
   (artikel → YAML-contract → schema → executie → trace → uitkomst);
2. **opbouw**: de demo-data zelf is niet langer handgemaakt, maar een
   versioned, gevalideerd contract, deterministisch gegenereerd uit echte
   PoC-artefacten, met een mini-engine die live rekent en waarvan de
   correctheid afgedwongen wordt door een golden set.

Besluiten uit de sessing: interpretatie "beide" (inhoud + opbouw); scope
Utrecht en Eindhoven eerst (Breda en Rijnland volgen in fase 2 volgens
hetzelfde patroon); aanpak C (generator + run-contract + eigen mini-engine,
met divergentiebeheersing via golden set).

## Architectuur

```text
nldt/simulation/
  regelrecht-demo.html              gegenereerde single-file demo (?poc=utrecht|eindhoven)
  regelrecht/
    regelrecht-demo.template.html   sjabloon met inline-JSON-placeholders
    simulation-run.schema.json      versioned run-contract, draft 2020-12, "$id …/v1"
    build_runs.py                   deterministische generator (Python, stdlib)
    runs/
      utrecht-wind-art5.3.json      gegenereerd (diffbaar, QA)
      eindhoven-bp2op-art10.2.json  gegenereerd
    engine/
      mini-engine.js                deterministische evaluator (ESM, browser)
      engine-cases.json             golden set (gegenereerd)
```

De generator is de enige schrijfactie; de HTML rendert alleen. Bestaande
PoC-pipelines worden uitsluitend gelezen.

## Het run-contract

`simulation-run.schema.json` (draft 2020-12, versieveld via `$id`, patroon
van de PoC-contracten in `poc/schemas/` en `poc-bp2op/schemas/`):
`$schema`-veld verplicht. Velden:

- `schemaVersion` — `"1"`;
- `runId` — deterministische hash over de bronartefacten (sha256, eerste 8
  tekens); identieke bronnen ⇒ identiek runId;
- `generatedAt` — ISO-datum van de build (enige niet-herhaalbare waarde;
  vastgepind via `--stamp` voor byte-identieke rebuilds);
- `poc` — `"utrecht"` | `"eindhoven"`;
- `instrument` — `title`, `cvdr`, `regulatoryLayer`, `article`;
- `sourceArtifacts[]` — `path` (relatief vanaf repo-root), `role`
  (bijv. `normcard`, `formalrule`, `example-yaml`, `run-summary`,
  `omzettabel`), `sha256`;
- `machineReadable` — de `machine_readable`-sectie uit het voorbeeld-YAML,
  overgenomen door de generator, nooit hertikt;
- `articleQuote` — het letterlijke artikelcitaat (NC-W-03 c.q. BR-001/DR-478);
- `demoCases[]` — `inputs` (parameters + input-feiten), `expectedOutputs`,
  `trace[]` (per stap: `action`, `operation`, `operands`, `result`);
- `abstentions` — `count`, `label`, `source` (Utrecht: 13 ambigue
  FormalRules; Eindhoven: 70 `needs_human`-rijen);
- `humanOnTheButtons` — `"v4_pending"` (constante; er bestaat geen andere
  toegestane waarde — het schema dwingt dit af via enum);
- `validations[]` — `level` (V0–V4), `verdict`, `evidence`.

## De generator (`build_runs.py`)

Python 3, stdlib-only (yaml/json alleen lezen; de nldt-venv biedt `pyyaml`
en `jsonschema` voor de validatiestappen — de PoC's draaien hier al op).
Invoer (alleen-lezen, paden vast):

| PoC | artefact | rol |
|---|---|---|
| Utrecht | `docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml` | example-yaml |
| Utrecht | `poc/corpus/normcards-wind.json` | normcard (NC-W-03 citaat + versie) |
| Utrecht | `poc/corpus/formalrules-wind.json` | formalrule (FR-W-03 + 13 ambigue) |
| Utrecht | `poc/runs/20260830T113234Z-wind/run_summary.json` | run-summary (kerncijfers) |
| Eindhoven | `docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml` | example-yaml |
| Eindhoven | `poc-bp2op/runs/20260830-124515-eindhoven/{bronregels,doelregels,omzettabel,kennisbank}.json` | bron-/doelregel, omzettabel-rij OT-001, kennisbank KB-031 |

Stappen: (1) artefacten lezen + sha256; (2) beide YAML's her-valideren tegen
het regelrecht-schema v0.7.1 (vastgepinde versie; lokaal cachebestand, geen
netwerk nodig); (3) `demoCases` opbouwen volgens het vaste gevalschema en
met de ingebouwde **Python-referentie-executor** outputs en traces
berekenen; (4) run-JSON's schrijven en tegen `simulation-run.schema.json`
validieren; (5) `engine-cases.json` (golden set) schrijven; (6) de template
vullen met de run-JSON's als inline `<script type="application/json">`-blokken
en als `regelrecht-demo.html` wegschrijven.

Het vaste gevalschema — de volledige inputruimte die de demo-UI kan
aannemen: **Utrecht** 3 × 2 × 2 = 12 gevallen (ashoogte ∈ {19, 20, 21} m —
onder/op/boven de grens; bouwperceel ∈ {aan, uit}; Gebied kleine windturbine
∈ {binnen, buiten}); **Eindhoven** 2 × 2 = 4 gevallen (strijd met het
tijdelijk deel ∈ {ja, nee}; IWT-vergunningvoorschriften ∈ {ja, nee}).
Golden set in totaal: **16 gevallen**; de selftest-badge rapporteert "16/16".

Faalcondities (alle met exit ≠ 0 en duidelijke melding): ontbrekend
artefact, YAML niet schema-valide, referentie/golden-inconsistentie,
run-JSON niet schema-valide, niet-byte-identieke her-run zonder `--stamp`.
Gewijzigde artefacten zijn géén faalconditie — hergeneratie is juist de
bedoeling; de sha's in `sourceArtifacts` maken elke wijziging zichtbaar en
diffbaar.

De Python-referentie-executor implementeert dezelfde operatiesubset als de
mini-engine (hieronder) en is de norm voor de golden set.

## De mini-engine (`mini-engine.js`)

ESM-module, pure functies, geen dependencies. Ondersteunde constructies —
precies de subset die de twee voorbeeld-YAML's gebruiken, niets meer:

- operaties: `AND` (`conditions[]`), `EQUALS`, `LESS_THAN_OR_EQUAL`,
  `IF` (`cases[]` met `when`/`then`, `default`);
- operanden: letterlijke waarden (boolean/getal/string) en `$naam`-referenties
  naar parameters en inputs;
- entrypoint: `evaluate(execution, inputs) → { outputs, trace[] }`, waarin
  elke trace-stap de uitgevoerde operatie, de operanden en de uitkomst
  vastlegt (het trace-principe: elke conclusie toont zijn tussenstappen).

Divergentiebeheersing: bij het laden van de pagina voert de engine de
golden set uit; 16/16 geslaagd geeft een groene badge in de header, elke
afwijking een rode banner én geblokkeerde interactie (de controls worden
uitgeschakeld). De golden set zelf is gegenereerd door de Python-referentie
— de JS-engine bewijst conformiteit bij elke paginalading, niet bij
wederzijds vertrouwen.

## De demo-pagina

Single-file (inline data, werkt vanaf `file://`), huisstijl van de bestaande
demo's (paper/ink/teal, DM Sans/Fraunces), PoC-keuze via `?poc=` conform het
bestaande tour-patroon. Structuur per PoC:

1. **Ketenbalk** — artikel → NormCard/bronregel → `machine_readable` YAML →
   schema-validatie → executie → trace → uitkomst. Elke stap aanklikbaar,
   toont het echte fragment: letterlijk citaat, executiesectie uit het
   voorbeeld-YAML, validatiestatus ("VALID — regelrecht-schema v0.7.1").
2. **Interactielab** — Utrecht: ashoogte-slider (0–40 m), toggles bouwperceel
   en Gebied kleine windturbine → live `toegestaan_kleine_windturbine` met
   drie oplichtende AND-condities; Eindhoven: toggles strijd met het
   tijdelijk deel en IWT-vergunningssituatie → live
   `regels_hoofdstuk_van_toepassing` met IF/cases-trace. De lab-cases zijn
   aangevuld op/afgedekt door de golden set: elke interactiestand die de UI
   kan aannemen zit in `demoCases` of is daar deterministisch uit af te
   leiden.
3. **Eerlijkheidspaneel** — onthoudingen (13 c.q. 70, met bronvermelding),
   de altijd-pendente jurittoets (V4), bronartefactenlijst met sha256, en de
   engine-selftest-badge.

## Aanpassingen bestaande pagina's

- `poc-utrecht.html` en `poc-eindhoven.html`: één nieuwe sectie "RegelRecht:
  van artikel naar uitvoerbare regel" met de keten in het kort en een link
  naar de demo (per PoC met het juiste `?poc=`-deep-link);
- `index.html`: de demo opgenomen in de hub-sectie van beide PoC's;
- `simulation/README.md`: de nieuwe pagina, de generator en het run-contract
  gedocumenteerd (inclusief build-commando).

## Foutafhandeling

Build-tijd: hard gates zoals bij de generator beschreven. Run-tijd: alles
inline (geen fetch, dus geen file://-beperkingen); selftest-faaluur → rode
banner + uitgeschakelde controls; ontbrekend inline-JSON-blok (kapotte
build) → expliciete foutmelding in de pagina in plaats van een leeg scherm.

## Tests

`nldt/tests/test_simulation_regelrecht.py` (unittest, draait in de
bestaande nldt-testsuite):

1. generator is idempotent: twee runs met dezelfde `--stamp` zijn
   byte-identiek;
2. beide run-JSON's zijn schema-valide tegen `simulation-run.schema.json`;
3. elke `demoCase` reproduceert exact in de Python-referentie (outputs én
   trace-vorm);
4. elke `sourceArtifacts`-sha256 klopt tegen het bestand op schijf;
5. mini-V2: `articleQuote` is letterlijk aanwezig in het bronartefact
   (NC-W-03 `quote` c.q. `bronregels.json` `tekst`, na
   whitespace-normalisatie);
6. `humanOnTheButtons == "v4_pending"` en het schema verwerp elke andere
   waarde.

## Bestandslijst en bouwvolgorde

1. `nldt/simulation/regelrecht/simulation-run.schema.json` — nieuw;
2. `nldt/simulation/regelrecht/build_runs.py` — nieuw (incl.
   Python-referentie-executor);
3. `nldt/simulation/regelrecht/engine/mini-engine.js` — nieuw;
4. `nldt/simulation/regelrecht/regelrecht-demo.template.html` — nieuw;
5. gegenereerd: `runs/utrecht-wind-art5.3.json`,
   `runs/eindhoven-bp2op-art10.2.json`, `engine/engine-cases.json`,
   `../regelrecht-demo.html`;
6. secties in `poc-utrecht.html`, `poc-eindhoven.html`, `index.html`;
7. `simulation/README.md` en `nldt/tests/test_simulation_regelrecht.py`.

## Non-doelen

- Geen eigen engine-taal: alleen de vier operaties die de voorbeeld-YAML's
  gebruiken; iets anders in een YAML is een faalconditie, geen feature.
- Geen Breda/Rijnland in deze fase (zelfde patroon, fase 2).
- Geen echte integratie met de Rust/WASM-RegelRecht-engine — dat is fase 2
  van de integratieroadmap, geen demo-onderdeel.
- Geen schrijfacties op de PoC-pipelines of hun corpora.

## Risico's

| Risico | Beheersing |
|---|---|
| Mini-engine wijkt af van de echte RegelRecht-semantiek | golden set gegenereerd door Python-referentie; browser-selftest bij elke paginalading; subset bewust minimaal |
| Demo-data veroudert t.o.v. de PoC-artefacten | sha256-gates in de generator en de unittests; her-run is één commando |
| Voorbeeld-YAML's wijzigen (nieuwere schema-versie) | generator her-valideert tegen v0.7.1 en faalt expliciet bij afwijking |
| file://-beperkingen | alles inline; geen fetch, geen externe assets behalve de bestaande fonts (graceful fallback) |
