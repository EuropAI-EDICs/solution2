# Ontwerp: Harness-lab — de harness als versie-bare variant (harness2-methode, eigen rechter)

| | |
|---|---|
| **Datum** | 25 oktober 2026 |
| **Status** | geïmplementeerd (motor + deep-agents-adapter + voorbeelden; llm-probe geverifieerd op lokale Ollama) |
| **Vraag** | "Kan [google-research/harness2](https://github.com/google-research/harness2) gebruikt worden voor onze poc-harness?" — antwoord: niet als dependency (andere laag, geen custom benchmarks, OpenCode/Codex-substraat, Vertex/Gemini-pinnen), maar de *methode* wel: propose–probe–compose op onze eigen harness, geoordeeld door onze eigen deterministische rechter. Optie A uit de analyse. |
| **Verwijzingen** | [harness2](https://github.com/google-research/harness2) + paper arXiv 2610.14224 (propose–probe–compose, meta-harness) · [2026-10-18 fundament/minigim-harnas](2026-10-18-poc-fundament-minigim-harnas-design.md) (register-patroon BB13, fase-manifest, V-cultuur) · [2026-10-06 harness-unificatie](2026-10-06-utrecht-harness-unificatie-design.md) ("de model is de motor, de harness is het product") · `poc-fundament/README.md` (gebruik) |
| **Buiten scope (deze iteratie)** | poc-nspd seam-adapter (A/B op scenario_author/norm_llm-prompts via injectable `llm_call` — volg-iteratie) · LLM-assisted proposer (varianten voorstellen met een model — `fase-2-haak` in het register) · `toolGrants`-adoptie (loopt via de manifest-generatoren, bewust geweigerd in `adopt`) · cross-poc register-federatie |

---

## 1. Doel en succescriterium

De agent-harness (orchestrator-prompt, slotgate-toolgrants, model-pinnen) is
vandaag impliciet: wijzigingen gaan rechtstreeks in de live-bestanden, zonder
pinning, zonder bewijs en zonder terugdraaispoor. De harness-lab maakt de
harness expliciet versie-baar:

1. **Propose** — een variant is een declaratief JSON-document
   (`harness-variant.schema.json`): component-wijzigingen (prompt-swap,
   grant-patch, model-pin) t.o.v. de actieve baselijn.
2. **Probe** — de variant wordt *in-memory* op de echte wiring toegepast
   (productiebestanden blijven aan) en door een taskset met deterministische
   checks geleid; elke probe schrijft `probe-evidence.json` met sha256-PROV
   van variant, taskset en componenten.
3. **Compose** — `probe-report.md`: vergelijkingsmatrix over varianten.
4. **Adopt** — de menselijke knop: alleen met voldoend bewijs (verdict
   `pass`, modus `llm`, sha's ongewijzigd sinds de probe) promoveert een
   variant naar `actief` in het harnessregister; de voorganger wordt
   `verworpen` en houdt zijn eigen sha256 (terugdraaien = oude inhoud
   reconstrueren).

Succescriterium: een harness-wijziging is nooit meer "gewoon even in de
prompt aangepast" — er ligt dan een gepinde, geprobeerde, geregistreerde
variant met evidence, of het is geen adoptie.

## 2. De mapping harness2 → lab

| harness2 | lab | verschil |
|---|---|---|
| 8 bewerkbare harness-componenten | 3: `prompt`, `toolGrants`, `modelPin` | onze agent-laag kent geen skills/plugins-laag |
| probe op eigen benchmarks (LAB/JobBench/WorkBuddy) | probe op eigen tasksets (`routing-kern.json` e.d.) | wij hébben ground truth; zij niet |
| LLM-jury (contrastief oordelen) | deterministische checks (`delegatesTo`, `answer(Not)Contains`, `slotgate(Allows\|Forbids)`, …) | sterker signaal, geen jury-drift |
| meta-harness met geleerde lessen | `harnessregister.json` met `probeEvidence` + `prov` | lessen staan bij de adoptie, niet in een aparte lerende laag |
| K-recursie, parallel/sequentially | één probe-ronde per run | experiment, geen optimizer |

Twee modi per probe: **fake** (gescripte `GenericFakeChatModel`-stub door de
échte graaf — offline, deterministisch, bewijst de montuur: wiring accepteert
de variant, checks en evidence-machinerie werken) en **llm** (echt model via
`check_ollama` — bewijst gedrag: `delegatesTo` wordt dan een échte
routeringsassertie). Adoptie vereist llm-bewijs; `--allow-fake` bestaat
alleen voor montuur-tests.

## 3. Bouwstenen

- **Motor** `poc-fundament/fundament/harnesslab.py` — luide loaders
  (schema + unieke ids + precies-één-`actief`-per-target), evidence-
  builder/schrijver (canon-volatiles: `probeId`, `startedAt`, `durationS`,
  `runDir`), byte-deterministische rapportrenderer, adoptiepoort. Importeert
  alleen stdlib + lazy jsonschema (`test_deps` blijft groen); adapters zijn
  geïnjecteerd, nooit geïmporteerd.
- **Schema's** `poc-fundament/schemas/{harnessregister,harness-variant,probe-taskset}.schema.json`.
- **CLI** `poc-fundament/tools/harness_lab.py` — `scaffold` (baselijn pinnen:
  register + identiteits-variant), `probe` (varianten × taskset), `adopt`
  (menselijke knop). Exit 0 = elke probe *uitgevoerd*; verdicts zijn data.
- **Adapter** `deep-agents/harness_lab_adapter.py` — het enige lab-onderdeel
  dat de agent-laag aanraakt: `apply_variant` (zuiver), `apply_grants`
  (slotgate + allow/deny; allow verbreedt alleen binnen de pre-slotgate
  toolset van de agent), task-uitvoerders (static/route/standalone; llm-
  standalone restricted tot catalog-lees-tools zodat een probe nooit een
  pijplijn-run kan starten), per-probe isolatie (journal → probe-map,
  env-pinnen teruggemaakt in `finally`).
- **Register** `deep-agents/harnessregister.json` — baselijn: 13 prompts +
  2 model-pinnen; conformance (`deep-agents/tests/test_harnessregister.py`)
  bewijst sha's, dekking (elke prompt op disk is gepind) en pin-gelijkheid
  met `model_config`-defaults.

## 4. Bewijskeuzes

- **static-taken** draaien altijd (ook in llm-modus): de slotgate-wiring is
  de goedkoopste harde bewijslast van een grant-variant.
- **Evidence is canon-deterministisch**: twee fake-probes van dezelfde
  variant × taskset zijn na canon gelijk (getest) — evidence is dus zelf
  golden-compareerbaar, in de geest van M2/M5.
- **Adoptie van een prompt schrijft de variant door naar het live
  promptbestand** — adoptie is echt, niet alleen boekhouding; de wiring leest
  prompts van disk, dus na adoptie draait de volgende run op de variant. De
  verworpen voorganger draagt de oude sha256, dus de oude inhoud is bit-exact
  reconstrueerbaar.
- **modelPin-adoptie is boekhouding**: de env-var moet apart gezet worden
  waar runs starten (live_server); de notitie in de entry zegt dit.

## 5. Eerste bevindingen (uit de verificatie-run)

De eerste llm-probe (gemma4:31b-mlx orchestrator + gemma4:12b-mlx
specialisten, 162 s) faalde één taak: de voorbeeld-taskset vroeg in het
Engels maar verwachtte het Nederlandse "recepten" — taal-brosse verwachting,
geen harness-defect. Precies wat een probe moet laten zien: de rechter is
strenger dan de intuitie. Taskset gecorrigeerd (vraag + verwachting in
dezelfde taal); routing- en delegatie-checks passeerden direct.

## 6. Risico's en tegmaatregelen

- **Probe-start pijplijn-runs?** — llm-standalone is restricted tot
  `list_recipes`/`get_recipe` (file-based, read-only); route-grafen draaien
  met `tools=[]` (alleen de `task`-tool); journal geïsoleerd per probe.
- **Register en disk lopen uiteen** — conformance-test faalt op sha-mismatch
  en stuurt naar her-scaffold; adoptie vereist sha-gelijkheid tussen evidence
  en variantbestand.
- **Adoptie als boekhouding zonder gedrag** — alleen llm-verdict `pass`
  adopteert; fake vereist expliciete `--allow-fake` en wordt zo zichtbaar in
  de evidence.
