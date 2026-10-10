# HCS-recipes fase 3 — EN-dish-demo's, bestuurdersdemo-scène, LLM-intake — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fase 3 van spec [`2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md) §6: (A) EN-tweelingen van de vier dish-demo's (de fixtures zijn al tweetalig), (B) één scène "De functie als recipe" in de bestuurdersdemo, (C) de echte LLM-intake via deep-agents als deterministisch gegate aanzet van benadering C.

**Architecture:** (A) `DISH_I18N` krijgt volledige `en`-blokken; `build_dish_pages` genereert per dish een NL- en een EN-pagina (patroon van de key-demo); `menu-data.json`-rijen krijgen EN-titel/KPI-kolommen voor de sibling-kaarten. (B) zelfstandige scène in `agentic-state-bestuurders-demo.html` (bestaande scene-markup, hernummerd). (C) `deep-agents/hcs_intake.py`: LLM stelt intake-vragen voor per persona uit de THK-08-fixture; een deterministische gate toetst alleen-vragen-wat-niet-in-BRP, gewone taal en handover-bij-edge-cases; resultaten als artefacts in `deep-agents/runs/hcs-intake/`. De demo's blijven deterministisch — de LLM-run levert artefacts, geen paginalaad-afhankelijkheid.

**Tech Stack:** Python 3 (`nldt/.venv`), plain HTML/CSS/JS, deep-agents op lokaal Ollama (`deep-agents/.venv` + `nldt/.venv/bin/python` met PYTHONPATH, pytest-marker `llm` per `deep-agents/pytest.ini`).

**Spec:** [`docs/superpowers/specs/2026-10-09-hcs-recipes-pocs-design.md`](../specs/2026-10-09-hcs-recipes-pocs-design.md) §6 fase 3. Fase 1+2 zijn afgerond (executiestatus in de faseplannen).

## Global Constraints

- Python nldt-zijde: `nldt/.venv/bin/python`; tests vanaf repo-root. Deep-agents-zijde: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q` (llm-tests extra met `-m llm` en `LDT_DEEP_AGENTS_ENDPOINT`).
- Stem R1 in beide talen: korte zinnen, geen systeemjargon in de hoofdtoon; canoniek blijven KPI-namen, broncitaten (BRP, PDOK), stepIds/scenario-ids.
- Deterministische demo's: de dish-/key-pagina's veranderen niet van gedrag door Task 3; de LLM-intake produceert uitsluitend artefacts.
- Ollama draait lokaal (modellen beschikbaar); llm-tests zijn `@pytest.mark.llm` + skipif zonder endpoint — de standaardsuite blijft LLM-vrij en groen.
- Bestuurdersdemo: bestaande scene-markup en -klassen; scènes hernummeren waar nodig; geen frameworkwijzigingen.
- Commit-stijl: `feat(nldt): …` / `feat(deep-agents): …` / `docs(nldt): …` Nederlands; alleen eigen taakbestanden; untracked `recipes/` nooit committen.

---

### Task 1: EN-dish-demo's — i18n, menu-data-EN-kolommen, acht pagina's

**Files:**
- Modify: `nldt/simulation/hcs/build_runs.py` (`DISH_I18N` + `en`, `build_dish_pages` per taal)
- Modify: `nldt/simulation/hcs/menu-data.json` (rijen → 8 kolommen: + `title-en`, `kpi-en`)
- Modify: `nldt/simulation/hcs-menu-demo.html` (NIETS — NL-demo blijft 6-koloms lezen; `_menu_siblings` localiseert)
- Generated: `hcs-uam-demo-en.html`, `hcs-grn-demo-en.html`, `hcs-cir-demo-en.html`, `hcs-min-demo-en.html`
- Test: `nldt/tests/test_hcs.py`

**Interfaces:**
- `DISH_I18N[dish]` wordt `{"nl": {...}, "en": {...}}`; `build_dish_pages` genereert voor elke dish twee pagina's (`hcs-<dish>-demo.html` NL, `hcs-<dish>-demo-en.html` EN) met gelokaliseerde i18n, scenario-labels en sibling-kaarten (`_menu_siblings(dish, lang)`).
- `menu-data.json`-rijen: `[code, title-nl, mode, kpi-nl, lens, recipeId, title-en, kpi-en]` (8 kolommen; mode blijft gecanoniseerd NL/EN-neutraal). `_menu_siblings` kiest kolommen per taal; het NL-menu-demo blijft ongewijzigd (leest zijn eigen ingebedde 6-koloms-MENU — géén wijziging nodig).

- [ ] **Step 1: Falende tests**

```python
DISH_EN_PAGES = {d: NLDT_ROOT / "simulation" / f"hcs-{d}-demo-en.html"
                 for d in ("uam", "grn", "cir", "min")}


def test_dish_en_pages_generated_and_dutch_free():
    dutch_markers = {"uam": "De snelste veilige route wordt bepaald",
                     "grn": "Nieuwe luchtfoto's worden opgehaald",
                     "cir": "Opwek en verbruik van alle buurtleden worden gekoppeld",
                     "min": "Alle dagelijkse voorzieningen worden op de kaart gezet"}
    for d, path in DISH_EN_PAGES.items():
        text = path.read_text()
        assert 'window.DISH_LANG = "en"' in text
        for marker in ("__DISH_DATA__", "__DISH_LANG__"):
            assert marker not in text
        assert dutch_markers[d] not in text  # stapteksten in het Engels


def test_menu_data_has_english_columns():
    data = json.loads((HCS_ROOT / "menu-data.json").read_text())
    for dish, rows in data.items():
        for row in rows:
            assert len(row) == 8 and row[6] and row[7], f"{row[0]} mist EN-kolommen"
```

- [ ] **Step 2: Draai — moet falen** (EN-pagina's bestaan niet; rijen hebben 6 kolommen)

- [ ] **Step 3: menu-data naar 8 kolommen**

Voeg per rij kolom 7 (`title-en`) en 8 (`kpi-en`) toe. Vertaal alle 53 titels en KPI-teksten in de R1-stem. De 25 THK-rijen hebben in de blueprint EN origineeltitels (gebruik die: "I want to marry", "I'm having a baby", … — bron: sheet *KPI framework*, kolom *Recipe (customer journey)*); de city-titels:

- UAM-01 "I want medical logistics by air" / KPI-en "Delivery-time reduction vs road" — **KPI-namen zijn al Engels: kolom 8 = kolom 4 voor alle city-rijen waar kolom 4 al de EN KPI-naam is.** Let op: in fase 2 zijn de menu-KPI-teksten bewust Nederlands vertaald ("Tijdswinst vergeleken met de weg") — kolom 8 krijgt de Engelse formulering ("Deliveries faster than the road"). THK: kolom 8 = Engelse KPI-formulering (bv. THK-08 "Moves processed without manual handling" — die is in menu-data de NL-tekst? Nee: fase 2 menu-data rij 4 is de NL KPI-tekst; kolom 8 wordt de EN KPI-naam uit het xlsx).
- Volledige EN-titellijst city: UAM-02 "I want last-mile parcel delivery" · UAM-03 "I want autonomous inspection & monitoring" · UAM-04 "I want drone-supported emergency response" · UAM-05 "I want an innercity air taxi" · UAM-06 "I want a city-to-city flying-car link" · UAM-07 "I want international air-mobility links" · UAM-08 "I want to govern my airspace (U-space)" · UAM-09 "I want geofencing & security zones" · GRN-01 "I want to measure canopy (the 30%)" · GRN-02 "I want a tree inventory (the 3)" · GRN-03 "I want to close the 300 m gaps" · GRN-04 "I want a digital twin of my greening" · GRN-05 "I want to capture & sell nature credits" · CIR-01 "I want a circular development condition" · CIR-02 "I want material passports" · CIR-03 "I want circular procurement" · CIR-04 "I want shared energy" · CIR-05 "I want shared mobility (micro & more)" · CIR-06 "I want shared food" · CIR-07 "I want shared goods" · CIR-08 "I want neighbourhood drinks & community life" · CIR-09 "I want residents to co-run the neighbourhood" · MIN-01 "I want a proximity analysis" · MIN-02 "I want mixed-use zoning" · MIN-03 "I want active mobility" · MIN-04 "I want to plan my hub network" · MIN-05 "I want to reallocate street space" — KPI-en per rij: korte EN formulering van de NL tekst (bv. CIR-04 "Energy generated locally", MIN-01 "Residents within 15 min of daily needs" — de xlsx-namen waar beschikbaar, anders eigen EN-formulering in dezelfde stem).
- THK-rijen: titels = de EN blueprint-origineeltitels (THK-01 "I want to marry" … THK-25 "I want support with parenting", per sheet *KPI framework*); KPI-en = de xlsx-KPI-naam (bv. THK-01 "Lead time notice → marriage registered", THK-14 "Non-take-up: entitled but receiving nothing").

- [ ] **Step 4: DISH_I18N + build_dish_pages tweetalig**

1. Herstructureer `DISH_I18N` naar `DISH_I18N[dish] = {"nl": {...}, "en": {...}}`. Het `en`-blok van uam (volledig; grn/cir/min overerven via `dict(DISH_I18N[dish]["en"], …)`-patroon met eigen titel/lede/eyecatcher):

```python
"en": {
    "eyecatcher": "Human-Centred Services · dish: Urban Air Mobility",
    "title": "Into the air — without clogging the city",
    "lede": "Two recipes from this dish, run as a deterministic replay: what happens, who decides, and where the information comes from.",
    "foot": "HCS phase 2 · build {stamp} · runs validated against hcs-run.schema.json · doctrine: AI proposes · pipeline decides · human decides",
    "testbank": "What we tested before this went live", "tbOk": "go", "tbCheck": "not yet tested", "tbFail": "no go",
    "kpiPanel": "What we aim to achieve — measured from day one", "kpiSub": "Every recipe measures whether life actually gets better.",
    "kpi": "KPI", "kpiType": "Type", "dataSource": "Source", "siblings": "Other recipes in this dish",
    "actor": "Who acts", "consent": "Consent", "handover": "A human takes over", "sources": "Where this information comes from",
    "actorNames": {"agent": "the system (under supervision)", "mens": "a human", "partij": "the organisation involved"},
    "consentNames": {"n.v.t.": "not needed", "gevraagd": "asked", "gegeven": "given", "geweigerd": "refused"},
    "vizTarget": "target:",
    "axisNames": {"accuracy": "accuracy", "plain language": "plain language", "once-only": "ask only once",
                   "explainability": "explainable", "human handover": "human takes over",
                   "bias": "bias", "AI Act risk class": "AI Act risk class"},
}
```

   grn: title "Measure the green, then grow it" · lede "Two 3-30-300 recipes: how much canopy does your district have, and who lives further than 300 metres from truly good green?" · eyecatcher "… dish: 3-30-300". cir: title "Sharing is the new owning" · lede "Two circular recipes: shared energy in the neighbourhood and circularity as a hard requirement for new build." · eyecatcher "… dish: Circular neighborhoods". min: title "Everything you need daily, close by" · lede "Two 15-minute-city recipes: which district falls outside reach of amenities, and where do the hubs go?" · eyecatcher "… dish: 15-minute city".

2. `build_dish_pages(stamp)` per dish over `{"nl": spec["file"], "en": spec["file-en"]}` heen (voeg `file-en` toe aan `DISH_DEFS`); per taal: i18n-blok kiezen, runs via `execute_hcs_recipe_run(..., lang=lang)`, scenario-labels via `localize(sc["label"], lang)`, siblings via `_menu_siblings(dish, lang)`, template-placeholders `__DISH_DATA__`, `__DISH_ID__`, `__DISH_LANG__`, `__BUILD_STAMP__`.

3. Template `dish-demo.template.html` drie kleine aanpassingen: lees `window.DISH_LANG` (naast DISH_ID); gebruik `D[DISH_LANG]`-velden; taalkruislink in de topbar (NL-pagina linkt `-en.html` en omgekeerd, zelfde patroon als key-demo `.lang`). `renderHeader` en `renderSiblings`/`renderScenarios` gebruiken de gelokaliseerde velden.

4. `_menu_siblings(dish, lang="nl")`: kies title/kpi-kolom per taal (nl: 1/3, en: 6/7).

- [ ] **Step 5: Genereren, testen, determinisme**

```bash
nldt/.venv/bin/python nldt/simulation/hcs/build_runs.py --stamp 20261009T120000Z
# verwacht: 8× OK run + 8× OK dish (4 nl + 4 en)
nldt/.venv/bin/python -m pytest nldt/tests/test_hcs.py nldt/tests/test_poc_processes.py -v
```

Tweede build → byte-identiek. Daarna de pagina-HTML in de Node-DOM-harness nalopen (zelfde methode als fase 2): badge 10/10 op alle acht pagina's, geen uitzondering.

- [ ] **Step 6: Commit**

```bash
git add nldt/simulation/hcs/build_runs.py nldt/simulation/hcs/menu-data.json nldt/simulation/hcs/dish-demo.template.html nldt/simulation/hcs-uam-demo.html nldt/simulation/hcs-uam-demo-en.html nldt/simulation/hcs-grn-demo.html nldt/simulation/hcs-grn-demo-en.html nldt/simulation/hcs-cir-demo.html nldt/simulation/hcs-cir-demo-en.html nldt/simulation/hcs-min-demo.html nldt/simulation/hcs-min-demo-en.html nldt/tests/test_hcs.py
git commit -m "feat(nldt): EN-tweelingen voor de vier dish-demo's — menu-data met EN-kolommen, i18n per dish"
```

---

### Task 2: Bestuurdersdemo-scène "De functie als recipe"

**Files:**
- Modify: `nldt/simulation/agentic-state-bestuurders-demo.html` (nieuwe scène 10; Vraag→11, Colofon→12)
- Test: `nldt/tests/test_hcs.py` (markers)

**Interfaces:**
- Scène insert vóór `<!-- 10 · VRAAG -->`; kicker "10 · De functie als recipe"; oude "10 · Vraag aan het bestuur" → "11 · Vraag aan het bestuur"; colofon-kicker → "12 · Colofon" (controleer de huidige colofon-nummering en hernummer).

- [ ] **Step 1: Falende test**

```python
BESTUURDERS_DEMO = NLDT_ROOT / "simulation" / "agentic-state-bestuurders-demo.html"


def test_bestuurdersdemo_hcs_scene():
    text = BESTUURDERS_DEMO.read_text()
    assert 'data-title="De functie als recipe"' in text
    assert "11 · Vraag aan het bestuur" in text
    for rid in ("thk-08-move-home", "grn-01-canopy-measure", "hcs-recipe-run"):
        assert rid in text
    assert text.count('class="scene"') == 12  # 11 scènes + colofon → 13? pas aan op feitelijke telling
```

Let op: bepaal de feitelijke scene-telling eerst (`grep -c 'class="scene"'`) en pin die.

- [ ] **Step 2: Scène invoegen** (vóór `<!-- 10 · VRAAG -->`, bestaande klassen: kicker/h2/lede/kaart/src)

```html
  <!-- 10 · HCS -->
  <section class="scene" data-title="De functie als recipe">
    <p class="kicker"><span class="streep"></span> 10 · De functie als recipe</p>
    <h2>De functie is nu een <span>artefact</span> — elf recipes uitgewerkt, 53 op het menu</h2>
    <p class="lede">De Human-Centred Services-blueprint (EDIC-basisplaat) is in de toolbox geland:
    life events en city-recipes als uitvoerbare recipes met mens-agent-grens, GenAI-testbank,
    KPI-baseline en leerstaat als data. Elf van de 53 recipes op het menu zijn als PoC uitgewerkt —
    van "ik ga verhuizen" tot de hubladder van de 15-minutenstad.</p>
    <div class="stappen">
      <div class="stap"><span class="nr">recipe</span><br/><b>thk-08-move-home</b> — vijf stappen,
      persona's met edge cases, overname bij adresonderzoek</div>
      <div class="stap"><span class="nr">recipe</span><br/><b>grn-01-canopy-measure</b> — meet-recipe
      op bestaande processen, steekproefcontrole door een medewerker</div>
      <div class="stap"><span class="nr">recipe</span><br/><b>hcs-recipe-run</b> — één deterministisch
      replay-proces voor alle city-recipes, met taalparameter</div>
    </div>
    <p class="note"><strong>Waar het landt:</strong> recipes in de cookbook (<code>nldt/recipes/</code>),
    function-baselines als poort 1+5, EDIC-adoptie in de asset-map, testbank en leerstaat in de demo's —
    zelfde aanpak over alle vijf dishes heen.</p>
    <p class="src"><b>Zie zelf:</b> <a href="hcs-key-demo.html">The Key-demo</a> ·
    <a href="hcs-menu-demo.html">menu (53 recipes)</a> ·
    <a href="../../docs/HCS_RECIPES_AGENTIC_STATE.md">koppeltabel agentic state</a>.</p>
  </section>
```

(Controleer of `.stappen`/`.stap` in dit bestand bestaat; zo niet, gebruik de kaartklassen die wél in de stylesheet staan — rapporteer de keuze.)

- [ ] **Step 3: Hernummeren + tests groen**

- [ ] **Step 4: Commit**

```bash
git add nldt/simulation/agentic-state-bestuurders-demo.html nldt/tests/test_hcs.py
git commit -m "feat(nldt): bestuurdersdemo-scène 'De functie als recipe' — HCS-recipes als functielaag"
```

---

### Task 3: LLM-intake via deep-agents (benadering C — aanzet)

**Files:**
- Create: `deep-agents/hcs_intake.py`
- Create: `deep-agents/tests/test_hcs_intake.py`
- Modify: `deep-agents/README.md` (korte sectie)
- Artifacts (gerund, niet gecommit unless waardevol): `deep-agents/runs/hcs-intake/*.json`

**Interfaces:**
- `load_thk08_personas() -> list[dict]` — leest `nldt/simulation/hcs/fixtures/life-events/thk-08-move-home.json` en projecteert per persona: id, edge, bekende BRP-velden (vast: naam, BSN, huidig adres, nieuw adres, verhuisdatum is het enige vraagpunt), handover-trigger uit de fixture (intake-handover per persona, gelokaliseerd nl).
- `gate_intake(result: dict, persona: dict) -> dict` — deterministische toets met drie checks, elk `{check, passed, reason}`: (1) `only-new-questions` — geen vraag overlapt bekende BRP-velden (vraag-tekst matcht op veld-sleutelwoorden: naam/bsn/adres → fail); (2) `plain-language` — geen jargon-woorden (lijst: "bsn", "brp", "zaak", "api", "attestatie" als vraagwoord) en vragen ≤ 120 tekens; (3) `edge-handover` — edge-persona's (ahmed) móéten een handover geven; niet-edge-persona's mogen geen handover hebben. Retour: `{"persona", "passed", "checks": [...]}`.
- `run_intake(persona_id, model=None) -> dict` — bouwt een kleine deep-agent (`create_deep_agent`, model via `models.ollama_model()`), system prompt: HCS-intake-assistent THK-08 (Nederlands, gewone taal, alleen vragen wat niet in de BRP staat, bij twijfel over het adres → aanbeveling tot overname); antwoord strikt als JSON `{"asks": ["..."], "handover": {"reason": "..."} | null}`; parse-faal → abstention (`{"asks": [], "handover": null, "abstained": true, "raw": ...}`); daarna `gate_intake`. Schrijft artefact naar `deep-agents/runs/hcs-intake/<stamp>-<persona>.json`.
- CLI: `python hcs_intake.py --persona sanne [--model gemma4:31b] [--all]`.

- [ ] **Step 1: Offline tests voor de gate (altijd draaiend)**

`deep-agents/tests/test_hcs_intake.py` — gate-tests met vaste voorbeelden: alleen-verhuisdur-vraag passeert; vraag naar naam faalt `only-new-questions`; jargonvraag ("Wat is uw BSN?") faalt `plain-language`; ahmed zonder handover faalt `edge-handover`; sanne mét handover faalt `edge-handover`; `load_thk08_personas` levert 4 persona's met edges. Zelfde run-conventie als de andere deep-agents-tests (PYTHONPATH-prefix).

- [ ] **Step 2: LLM-test met marker (skipif zonder endpoint)**

```python
@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get("LDT_DEEP_AGENTS_ENDPOINT"), reason="alleen met echt endpoint")
def test_llm_intake_sanne_passes_gate():
    from hcs_intake import run_intake
    result = run_intake("sanne")
    assert result["gate"]["passed"], result["gate"]
```

(patroon `test_hitl_llm.py`; endpoint-env in `.env`/shell — Ollama draait lokaal met `gemma4:31b` beschikbaar; kies het model via `models.ollama_model()`-default.)

- [ ] **Step 3: Implementeer `hcs_intake.py`** — volg de interfaces hierboven; hergebruik `models.ollama_model()`, `create_deep_agent` zoals `agent.py` dat doet (minimale tools: géén — pure antwoordgeneratie met JSON-uitvoer); schrijf artefacts met stamp.

- [ ] **Step 4: Verificatie**

```bash
cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_hcs_intake.py -q
# offline gate-tests groen; daarna expliciet met model:
LDT_DEEP_AGENTS_ENDPOINT=http://localhost:11434 PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests/test_hcs_intake.py -m llm -q
# en één echte run:
../nldt/.venv/bin/python hcs_intake.py --all --model gemma4:31b
```

Expected: gate-tests groen; llm-test groen op het draaiende model (bij falen: gate-rapport is het resultaat — een rode gate is een geldig, rapporteerbaar uitkomst, geen testdefect; de test eist óók dat het antwoord parseert als JSON); vier artefacts in `runs/hcs-intake/`.

- [ ] **Step 5: README + commit**

```bash
git add deep-agents/hcs_intake.py deep-agents/tests/test_hcs_intake.py deep-agents/README.md
git commit -m "feat(deep-agents): HCS-LLM-intake — LLM stelt vragen voor, deterministische gate toetst poort 3"
```

---

### Task 4: Docs, visuele gate en afronding

- [ ] **Step 1:** index.html — vier EN-links in de HCS-sectie (per dish-kaart of als extra kaarten; kies de nette variant conform bestaande markup); README-rijen (EN-pagina's + LLM-intake); 04-doc HCS-paragraaf één zin over de LLM-intake.
- [ ] **Step 2:** volledige nldt-suite + deep-agents-suite (offline) groen.
- [ ] **Step 3:** visuele gate: vier EN-dish-pagina's (volledig Engels op canonieke namen na, badge 10/10) + bestuurdersdemo met nieuwe scène (palet/layout ongewijzigd, scène leest als de buren). Brave headless + judge; bij timeout controller-inspectie (conventie).
- [ ] **Step 4:** slot-commit + executiestatus in dit plan.

## Buiten dit plan

Echte Leaflet/PDOK-kaarten i.p.v. SVG-schema's · HITL-interrupt koppelen aan de intake-handover (de infra bestaat: `deep-agents/hitl.py` + live-server) · uitbreiding naar meer persona's/recipes in de LLM-intake.
