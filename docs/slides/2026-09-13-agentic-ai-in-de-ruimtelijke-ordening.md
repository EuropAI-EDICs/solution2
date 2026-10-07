---
marp: true
theme: default
paginate: true
title: Agentic AI in de ruimtelijke ordening
description: Overwegingen uit vier PoC's van de LDT-toolbox — AI in the City 2026, Breda
---

<!-- Renderen: `marp docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md -o slides.html`
     of VS Code + Marp for VS Code. Ook leesbaar als platte Markdown. -->

<style>
  section { font-size: 25px; }
  section h2 { font-size: 1.05em; }
  section table { font-size: 0.82em; }
  section pre { font-size: 0.72em; }
  section li { margin: 0.18em 0; }
</style>

<!-- _class: lead -->

# Agentic AI in de ruimtelijke ordening

## Overwegingen uit vier proof-of-concepts

**LDT-toolbox · AI in the City 2026 — Creating Real Value**
Breda, 23–25 september 2026 · indestad.ai

---

## Waarom deze sessie?

De vijf waarden van *AI in the City 2026* zijn het rooster:

| Waarde | Congres-belofte (citaten) |
|---|---|
| **Democratisch** | *"more accessible, faster and more human"* |
| **Ruimtelijk** | *"A city is more than a dataset… amplifies the genius loci"* |
| **Economisch** | *"lower costs, less waste and more output"* |
| **Sociaal** | *"AI always serves human wellbeing"* |
| **Autonoom** | *"People retain control over AI systems"* |

**Vraag:** waar laat je agentic AI toe in ruimtelijk beleid — en waar
**juist niet** — om die beloftes *aantoonbaar* te maken i.p.v. geclaimd?

---

<!-- _class: lead -->

# De kernoverweging

# *LLM's stellen voor,
# deterministische engines beslissen*

---

## De ontwerpregel uit de praktijk

Alle vier de PoC's delen één doctrine (→ `docs/GENAI_SEAMS.md`):

- **Agenten mogen**: vragen vertalen, scenario's voorstellen, resultaat verhalen, bronnen bewaken
- **Agenten mogen níét**: scores berekenen, verdicten vellen, regels wijzigen, herkomst vastleggen

Elke aanraking met een model verloopt via een **naad (seam)** met een vast formaat:

```
LLM ──(schema-gevalideerd JSON-voorstel)──▶ deterministische gate ──▶ engine · critic · mens
        temperatuur 0, gestructureerd          cite-or-abstain +          beslist
        PROV: model + prompt + versie          schema + gronding
```

Wat niet door de gate komt, belandt in een **afkeuringsledger** — nooit in het product.

---

## Vier vertrouwensmechanismen (terugkerend in elke PoC)

1. **Cite-or-abstain** — geen bewering zonder verifieerbare bron; liever onthouden dan gissen
   (CBS-sentinels, juridische citaten, onmappbare vragen)
2. **Schema's op elke grens** — elk artefact dat een stage verlaat is machine-valideerbaar;
   vormdrift van modellen wordt gevangen vóór executie
3. **Validatie V0–V4** — syntaxis → geometrie → gronding → onafhankelijke herschrijving →
   **mens blijft altijd de laatste schakel** (V4 pending *by design*)
4. **PROV-herkomst** — sha256 per artefact, model+prompt per voorstel,
   bron+tijdstempel per cijfer

---

<!-- _class: lead -->

# PoC-4 — Breda
## De vijf-waardenscan: het congresrooster
## als kaart, per buurt

---

## PoC-4: wat het doet

> Waar creëert open data + AI **vandaag al** waarde in Breda — per buurt,
> voor elk van de vijf congreswaarden, elk cijfer herleidbaar?

- **56 buurten / 11 wijken** (CBS 2024) × vier percentielscores + soevereiniteitsmanifest
- 100% sleutelloos: CBS/PDOK + het eigen ArcGIS Hub van Breda (data.breda.nl, geo.breda.nl)
  — wijkdeals, hoofdgroenstructuur, klimaatportaal, 117.012 bomen
- Kanonieke run: verdict **pass**, 0 degradaties, herdraaibaar vanaf schijf

**Trade-off die de data laat zien:** Belcrum — hoogste democratische score (96,3),
laagste ruimtelijke score (19,5). Precies de beleidsdialoog die een tweeling opent.

---

## PoC-4 → de vijf waarden

| Waarde | Indicator | Programma-onderdeel |
|---|---|---|
| Democratisch | voorzieningenafstand + wijkdeels (50/56) | *Residents in the driving seat* |
| Ruimtelijk | groene ruggegraat + kansenkaart | *Green Spaces & Water as backbone* |
| Economisch | dakpotentieel + bedrijvigheid | *AI Walk: Energy savings* (TNO) |
| Sociaal | hitte-aandacht: verharding × 65+ | klimaatadaptatie |
| **Autonoom** | **geen kaart, wel manifest** | *Sovereignty*; *Data continuity* |

De vijfde waarde is bewust geen kaartlaag: **soevereiniteit is aantoonbaar,
niet claimbaar** — 7 criteria met bewijs per run (geen sleutels, geen
vendor-lock, geen LLM in de beslislijn).

---

## PoC-4: agentic AI in de praktijk — grounded Q&A

> "Waarom scoort Belcrum laag op ruimtelijke waarde?"

```
vraag (NL) → asker (parser | LLM) → ScanQuery (schema)
          → deterministische runner → value-scan.json
          → antwoord | LLM-narratie achter de cijfer-gate
```

**Live gevalideerd met lokaal qwen3.8 — drie paden:**

1. **Vormdrift gevangen** — `'Belcrum'` in het `focus`-veld → schema-gate → ledger
2. **Eerlijke onthouding** — onmappbare vraag? Model én parser onthouden zich
3. **Geaccepteerd** — Nederlandse prosa ("19,5", "4.245 inwoners") grondt volledig

→ **Democratische waarde**: vragen in gewoon Nederlands; elk cijfer bestaat écht.

---

## De verrassende les van de Q&A-gate

De eerste live-narratie werd **terecht afgekeurd** — drie overtredingen.
Analyse: het model had foutloos gekopieerd; **de gate zelf had drie bugs**:

- precisieverlies in de eigen cijfercollectie (`:g`-notatie)
- dict-sleutels (`bomen_per_100_inw`) werden niet als gronding geteld
- Nederlandse duizendtallen ("4.245" = 4245) werden als fabricatie gezien

> **Een grounding-gate moet zichzelf eerst deugdelijk testen.**
> Striktheid zonder kalibratie straft eerlijke formulering af — en dan leer je
> je eigen instrument kennen, niet het model.

Elke fix is nu een unittest (73 offline tests).

---

<!-- _class: lead -->

# PoC-1 — provincie Utrecht
## "Waar kan wat?" + het
# scenario-voorstelnaad

---

## PoC-1: waar kan wat — wind · zon · bos

- Vraag: *binnen welke zone kan de verordening X toestaan — elke norm geciteerd
  (instrument · artikel · versie · letterlijk citaat · URL)?*
- Deterministische zone-engine over 24 normkaarten per track; 13 bewust
  *ambigue* open normen → V4 mens-review, nooit gegokt

**Agentic naad (S7/S8) — de meest volwassen in de toolbox:**

- LLM stelt **what-if-scenario's** voor als contract (`ScenarioSpec`), met
  bewijsklasse: `norm_variance` · `policy_variant` · `hypothetical`
- De critic voert ze uit over de cache: hallucinatie van regel-id's → ledger
- Kanonieke run: qwen3.8, **10/10 voorstellen geaccepteerd, elk id echt**

---

## PoC-1: wat de sweep onthult (en waarom een agent waarde toevoegt)

| Beleidsvariant | Effect |
|---|---|
| NNN-lid-2-uitzondering provinciebreed | **+322,5 km² (+37,5%)** wind |
| Stiltegebied als harde uitsluiting | tot −61% |
| 500 m Natura 2000-buffer (hypothetical) | −52,2% |
| Zon: Natura-uitsnijding op face value | **+0,011 km² — symbolisch** |

De agent vindt de varianten die een beleidsmedewerker zou overwegen;
**de engine produceert het getal, de critic de waarheid erover.**

→ **Ruimtelijke waarde**: de genius loci versterken = de eigen regelgeving
en haar vrijheidsgraden eerst echt begrijpen.

---

<!-- _class: lead -->

# PoC-2 — Eindhoven
## van bestemmingsplan naar
# omgevingsplan, mét de jurist
# op de knoppen

---

## PoC-2: kenniswerk — geen vervanging, maar versnelling mét bewaking

- Opgebouwd uit de **VNG-methode** van de Amsterdamse aanpak (Plangids):
  regel-voor-regel matching oud → nieuw, kennisbank van eerdere conversies
- Method-kaarten MC-1…MC-12 uit het archief; elke feature citeert zijn kaart
- GenAI-naden: re-ranking van tekstmatches (S5), **schetsen van doelregels**
  voor open clusters (S6) — status altijd `voorgesteld`

**Harde regel (MC-6):** niets wordt door AI `gekoppeld`; de jurist beslist.

→ **Economische waarde**: meer output uit de 370-plannen-portefeuille,
zónder bestuurlijk risico van delegeerbaarheid.

---

<!-- _class: lead -->

# PoC-3 — Hoogheemraadschap Rijnland
## water, peilen en kwaliteit
# …nóg zonder agent

---

## PoC-3: eerst deterministisch, dan pas agentisch

- Peilbeheer vs. vigerend peilbesluit, KRW-meetnetdekking, gemeten
  waterkwaliteit (11 stoffen), tijdreeksen 2020–2026, H3-hexmaps
  met Moran's I — alle deterministisch, herdraaibaar, offline
- 4.079 stationsdagen, ±1,44 mln meetrijen → het **canonieke artefact eerst**

**Overweging — de belangrijkste van dit deck:**

> Agentic AI is pas verantwoord **bovenop** een deterministische basis.
> Zonder reproduceerbaar fundament wordt elk antwoord van een agent een
> geloofszaak — met fundament wordt het een auditeerbare redenering.

→ **Sociale waarde**: waterveiligheid en hitte-adaptatie verdragen geen
onverifieerbare tussenstappen; hier dient AI het welzijn via betrouwbare cijfers.

---

## De overwegingen op een rij

| # | Overweging | In de PoC's aangetoond |
|---|---|---|
| 1 | Voorstellen ≠ beslissen — seams overal | Q&A-gate, ScenarioSpec, MC-6 |
| 2 | Cite-or-abstain boven giswerk | CBS-sentinels, 13 ambague normen |
| 3 | Schema's óók voor agent-output | `'Belcrum'` in `focus` → ledger |
| 4 | Identiteit stempelt de seam, niet het model | `llm-proposal#qwen3.8` |
| 5 | Mens blijft eindbeslisser (V4) | jurist, bestuurder, congres |
| 6 | Lokale, open modellen | Ollama/qwen — geen vendor |
| 7 | Herkomst per cijfer | PROV, sha256, lastChecked |
| 8 | Bron-continuïteit is werk | maxRecordCount-les PoC-4 |

---

## Wat agentic AI de vijf waarden oplevert — en kost

| Waarde | Winst | Te bewaken |
|---|---|---|
| Democratisch | vragen in gewoon Nederlands | antwoord-gate, geen advies-roll |
| Ruimtelijk | beleidsvarianten verkend | voorstellen, geen besluiten |
| Economisch | uren uit repetitief werk | jurist ondertekent |
| Sociaal | adaptatie data-gedreven | determinisme vóór agent |
| Autonoom | lokale modellen, open data | manifesten per run bewijzen |

**Geen van de vijf waarden is een optelsom** — het profiel per buurt
is het product, niet één stadsrapportcijfer.

---

## Positie in het kader van *The Agentic State*

De whitepaper *The Agentic State* (Ilves e.a., 2025) rangschikt agentic AI voor de overheid in
**twaalf functionele lagen** — zes implementatie, zes enablement — met autonomieschaal L0–L5.
De toolbox scoort daarop sterk precies waar het in dit domein toe doet:

| Laag | Kern | Toolbox |
|---|---|---|
| 2 Workflow | zelf-orchestrerende uitvoering | **L3** — volledige keten met gates & critic |
| 7 Governance | verantwoordelijkheid & herstel | cite-or-abstain · PROV · leerstaat |
| 8 Data | gedeelde betekenis & herkomst | bronmonitor · autoritatieve citaten |
| 4 Compliance | toezicht & bewijs | V0–V4 · golden-regressie |

> **L3 in een begrensd domein** is het niveau dat het paper aanbeveelt voor gevoelige
> domeinen: *"a reliable Level 3 system may beat an unpredictable Level 4."*

Volledige analyse per laag: `docs/AGENTIC_STATE_GAP_ANALYSE.md` — methode: de Sitra-poorten.

---

## Slot: Creating *Real* Value

Real value in ruimtelijke ordening is **controleerbaar**:

- elk cijfer herleidbaar naar bron met tijdstempel
- elk agent-voorstel door een gate — of openbaar afgekeurd
- elke run her-speelbaar vanaf schijf (exit 0 = pass)

> De vraag is niet *of* AI een laag in de stad wordt,
> maar **wie de knoppen houdt**. Deze vier PoC's tonen hoe je
> dat aantoonbaar regelt — beginnend in Breda.

**Vervolg:** scenario-naad voor de vijf-waardenscan · bronmonitor-agent ·
nldt/MCP-orchestratie.

---

## Colofon & herleiding

- LDT-toolbox: `poc/` (Utrecht) · `poc-bp2op/` (Eindhoven) ·
  `poc-rijnland/` · `poc-breda/` — alle runs herdraaibaar & offline
- Doctrine: `docs/GENAI_SEAMS.md` · architectuur: `nldt/05-agentic-ai-layer.md`
- Breda-scan: `poc-breda/runs/20260913T152919Z-breda-scan/report.html`
  (56 buurten, verdict pass) · Q&A: `poc-breda/qa_run.py --demo`
- Citaten congresprogramma: indestad.ai/en/#programme (geraadpleegd 13-9-2026)
- 185 (Utrecht) + 32 (Eindhoven) + 33 (Rijnland) + 73 (Breda) = **323 offline
  tests**; geen API-sleutels; lokale modellen (qwen3.8 via Ollama)
- Kader: *The Agentic State* (Ilves e.a., 2025, agenticstate.org) · gap-analyse:
  `docs/AGENTIC_STATE_GAP_ANALYSE.md`
