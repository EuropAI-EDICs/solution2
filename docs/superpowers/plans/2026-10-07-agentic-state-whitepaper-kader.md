# Agentic State whitepaper-kader — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De whitepaper *The Agentic State* (Ilves e.a., 2025) als overkoepelend verhaalkader landen: gap-analyse per 12 functionele lagen (`docs/AGENTIC_STATE_GAP_ANALYSE.md`), beslissessie "volgende stap" met Marc, `docs/AGENTIC_STATE_PLAN.md` → v1.2, en bestaande uitdracht-artifacts (slides NL/EN, bestuurlijke samenvatting, demo) herverteld langs het kader.

**Architecture:** Docs-only, vier deliverables in vaste volgorde: (1) gap-analyse met per laag evidence → L0–L5-score → koppeling/gap, (2) interactieve beslissessie (door de orchestrator, niet door een subagent), (3) light-touch plan-update die Sitra B1–B14 als uitvoeringsstructuur laat staan, (4) uitdracht-aanpassingen in bestaande artifacts. Geen codewijzigingen.

**Tech Stack:** Markdown, Marp-slides (NL/EN), statische HTML-demo. Verificatie met `grep`/`test -f`-loops; geen testframework nodig.

**Spec:** [`docs/superpowers/specs/2026-10-07-agentic-state-whitepaper-kader-design.md`](../specs/2026-10-07-agentic-state-whitepaper-kader-design.md)

## Global Constraints

- Taal: alle nieuwe/gedocumenteerde tekst in het Nederlands; de EN-slides in het Engels.
- Elke evidence-claim in de gap-analyse verwijst naar een bestaand bestand of een bestaand PoC; bij ontbrekend pad: score aanpassen en dat in de onderbouwing noteren.
- Geen placeholders: geen "TBD", "TODO", "nog invullen".
- Sitra-structuur B1–B14 (§1 en §3 van `AGENTIC_STATE_PLAN.md`) en de fasering (§5) blijven **ongemoeid**; v1.2 is light touch.
- Commit-stijl: `docs(...): …`, Nederlands, conform repo-historie.
- Taak 3 (beslissessie) is interactief: de uitkomst komt van Marc via AskUserQuestion — een subagent mag deze taak niet uitvoeren.
- Werkboom-check vóór elke commit: alleen de bestanden van de eigen taak committen (de untracked decision-trail-bestanden `nldt/schemas/decision-trail.schema.json`, `nldt/services/memory/`, `nldt/tests/test_memory_store.py` horen aan een ander spoor en **niet** bij deze commits).

---

### Task 1: Gap-analyse — scaffold, methode en implementatielagen 1–6

**Files:**
- Create: `docs/AGENTIC_STATE_GAP_ANALYSE.md`

**Interfaces:**
- Consumes: spec §1 (stramien per laag); bron `docs/AGENTIC_STATE_PLAN.md` §1 (B1–B14) en §3 (landingsplaatsen).
- Produces: `docs/AGENTIC_STATE_GAP_ANALYSE.md` met documenttabel, §1 Methode, §2 (lagen 1–6). Task 2 vult §3–§5 aan; Task 3 gebruikt §5; Task 4 verwijst naar het document.

- [ ] **Step 1: Evidence verifiëren**

Run:

```bash
cd /Users/marc/Projecten/ldttoolbox
for p in docs/AGENTIC_STATE_PLAN.md docs/GENAI_SEAMS.md docs/POC_BESTUURLIJKE_SAMENVATTING.md \
  deep-agents/journal.py deep-agents/live_server.py deep-agents/models.py \
  nldt/services/cli.py nldt/recipes nldt/skills/poc nldt/edic nldt/services/a2a nldt/services/mcp_servers \
  nldt/schemas/validation-report.schema.json nldt/schemas/compliance-declaration.schema.json \
  nldt/schemas/dataspace-offer.schema.json \
  nldt/00-architecture.md nldt/07-trust-and-governance.md nldt/12-governed-agent-layer.md \
  nldt/13-data-lake-and-space.md nldt/14-beleidskompas-integration.md nldt/16-eid-wallet-identity.md \
  nldt/17-source-monitor.md nldt/18-donl-harvest.md nldt/SECURITY.md \
  nldt/data/trust-policy.example.json nldt/data/lake-deny.json nldt/bestuurlijke-samenvatting.md \
  nldt/simulation/agentic-state-demo.html \
  poc/pipeline/golden.py poc/tests/test_golden_regression.py \
  poc-bp2op poc-rijnland poc-breda poc-minigim \
  docs/superpowers/plans/2026-10-04-verordening-fase1-water-bodem.md \
  ../omgevingschat-platform-develop; do
  test -e "$p" && echo "OK         $p" || echo "ONTBREEKT  $p"; done
```

Expected: elke regel `OK` (het Sitra-plan zelf is de enige claims-bron die sowieso bestaat; `../omgevingschat-platform-develop` kan ontbreken op machines zonder de zusterrepo — noteer dat dan in de laag-1-tekst als "buiten dit werkstation"). Bij een `ONTBREEKT`-regel voor een ander pad: verwijder die claim uit de betreffende laag-tekst in Step 2 en verlaag de score indien de claim dragend was.

- [ ] **Step 2: Document aanmaken met kop, methode en §2 (lagen 1–6)**

Maak `docs/AGENTIC_STATE_GAP_ANALYSE.md` aan met exact deze inhoud (aanpassingen volgens Step 1-uitkomst):

````markdown
# Gap-analyse — The Agentic State × LDT-toolbox

| | |
|---|---|
| Document | `docs/AGENTIC_STATE_GAP_ANALYSE.md` · v1.0 · 2026-10-07 |
| Kader | [The Agentic State](https://agenticstate.org/paper.html) (Ilves, Kilian, Parazzoli, Peixoto, Velsberg, 2025): twaalf functionele lagen — zes implementatielagen (1–6) en zes enablement-lagen (7–12) — met een autonomieschaal L0–L5 (naar Bornet e.a. 2025) |
| Methode-kader | [`AGENTIC_STATE_PLAN.md`](AGENTIC_STATE_PLAN.md) v1.1: Sitra-building-blocks B1–B14 als operationele methode (functie-first, poorten, leerstaat) |
| Status | gap-analyse ter onderbouwing van het beslispunt "volgende stap" (plan §9) |

## 1. Methode

Per laag drie vaste onderdelen: **repo-evidence** (bestanden/PoC's, inclusief het zusterplatform
Omgevingschat waar van toepassing, expliciet als buiten-repo gemarkeerd), een **L0–L5-score**
met onderbouwing, en de **koppeling** naar Sitra-block en landingsplaats plus de grootste gap.
Scores zijn momentopnames van dit werkstation (2026-10-07), geen certificering.

De L0–L5-schaal van de whitepaper: **L0** handmatig (mens doet alles) · **L1** regelgebaseerde
automatisering (RPA, scripts) · **L2** intelligente procesautomatisering (ML/NLP + orchestration)
· **L3** agentic workflows (planning/reasoning in een begrensd domein, onder toezicht) ·
**L4** semi-autonoom (autonoom binnen begrensde expertise) · **L5** volledig autonoom (niet
bestaand; research). Het paper: hoger is niet beter — het juiste niveau hangt af van risico,
complexiteit en toezichtbehoefte; *"a reliable Level 3 system may beat an unpredictable
Level 4 in sensitive domains."*

## 2. Implementatielagen (1–6)

### Laag 1 — Public Service Design & UX

- **Evidence:** het zusterplatform Omgevingschat (buiten repo, `../omgevingschat-platform-develop`)
  is een productrijpe chat-front-door met grounded, geciteerde antwoorden op locatiegebonden
  omgevingswet-vragen; in-repo: grounded Q&A in gewoon Nederlands (`poc-breda/qa_run.py`,
  antwoord-gate met afkeuringsledger), dashboards (`deep-agents/live_server.py`) en
  bestuurlijke demo's (`nldt/simulation/`).
- **Score: L2.** Vraag-antwoord met orchestration en citatie is intelligent procesautomatisering;
  de L3-kenmerken uit het paper (proactief, hypergepersonaliseerd, zelfcomposerend) ontbreken.
- **Koppeling/gap:** B11 (herbruikbare kern; Omgevingschat als F1-instantie) en B6 (gedeelde
  betekenis); integratiepatroon in `nldt/14-beleidskompas-integration.md`. Grootste gap:
  proactieve dienstverlening (de dienst komt nog pas ná een vraag).

### Laag 2 — Government Workflows

- **Evidence:** de "volledige keten" in `deep-agents/` (intake → normspecialist → formalizer →
  build → critic → explainer) met artifact gates en run-journal (`deep-agents/journal.py`);
  23 recipes via `nldt/services/cli.py` (OGC API Processes); zes PoC-engines (`poc/`,
  `poc-bp2op/`, `poc-rijnland/`, `poc-breda/`, `poc-minigim/`) als instanties van één functie.
- **Score: L3.** Planning en reasoning in een begrensd domein, onder toezicht (critic + gates +
  V4-mens) — de definitie van L3 uit het paper, in supervised productie/pilot-vorm.
- **Koppeling/gap:** B1/B2 (functie als gedeeld niveau), B8 (mens-agent-grens). Grootste gap:
  HITL-interrupts zijn ontworpen (`AGENTIC_STATE_PLAN` §5 fase C) maar nog niet geïmplementeerd;
  de functielaag (B1) is nog geen expliciet artefact.

### Laag 3 — Policy- & Rule-Making

- **Evidence:** machineleesbare regels met artikel- en versiecitaten in de Utrecht-normketen
  (24 normkaarten per track, 13 bewust ambigue open normen → V4-mens-review);
  conversie bestemmingsplan→omgevingsplan volgens VNG-methode (`poc-bp2op/`, method-kaarten
  MC-1…MC-12); verordening-uitbreiding in vijf gedocumenteerde fases
  (`docs/superpowers/plans/2026-10-04-verordening-fase1-water-bodem.md` e.d.); scenario-naad
  S7/S8: LLM stelt beleidsvarianten voor, deterministische critic evalueert ze over de cache.
- **Score: L2, met L3-aanzet.** Machineleesbaar recht en gereedschap voor regel-conversie zijn
  er; de scenario-seam is een bescheiden vorm van dynamische simulatie. Adaptieve
  regelverfijning en participatory intelligence ontbreken.
- **Koppeling/gap:** B2 (+1-niveau: programmahoudes/verordening), B6. Grootste gap: de lus van
  uitvoering terug naar regelgeving (feedback-driven rule refinement) — raakt de leerstaat (B10).

### Laag 4 — Regulatory Compliance & Supervision

- **Evidence:** validatieketen V0–V4 met onafhankelijke critic (herschrijving als toets);
  schema-gedwongen artefacten (`nldt/schemas/validation-report.schema.json`,
  `nldt/schemas/compliance-declaration.schema.json`); golden-regressie over 13 canonieke
  tracks (`poc/pipeline/golden.py`, `poc/tests/test_golden_regression.py`); bronmonitor
  (`nldt/17-source-monitor.md`) die bronwijzigingen signaleert.
- **Score: L2.** Periodieke, batchgewijze validatie en regressie — krachtig maar geen
  continue supervision. Het paper-principe "minimal disclosure, maximal assurance" via
  cryptografische bewijzen ontbreekt volledig.
- **Koppeling/gap:** B9 (poort 5: bewijs en stopcondities), eval-harness. Grootste gap:
  continuïteit (van periodiek naar doorlopend) en bewijstechniek.

### Laag 5 — Crisis Response

- **Evidence:** geen.
- **Score: L0.** Afwezig — en bewust zo: het domein van de toolbox is ruimtelijke ordening
  (omgevingswet), niet crisisbeheersing.
- **Koppeling/gap:** geen Sitra-block. Vastlegging: buiten scope van de referentie-implementatie;
  geen actiepunt.

### Laag 6 — Public Procurement

- **Evidence:** dataspace-offers als machineleesbare aanbieding van capabilities
  (`nldt/schemas/dataspace-offer.schema.json`); EDIC-conformiteit en requirements-backlog
  (`nldt/edic/`); publicatiekanaal EU LDT Marketplace (`MULTI_AGENT_PLAN.md` §3.4).
- **Score: L0–L1.** Aanbieding van modules is een randvoorwaarde voor marktwerk, maar autonome
  aanbestedingsonderhandeling (het paper-thema van laag 6) is niet aanwezig en niet beoogd.
- **Koppeling/gap:** B12 (GovTech-marktlogica). Vastlegging: out-of-scope; het kanaal
  (marketplace/EDIC) is het enige raakvlak en dat bestaat al.
````

- [ ] **Step 3: Verifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "^### Laag" docs/AGENTIC_STATE_GAP_ANALYSE.md   # Expected: 6
grep -n "TBD\|TODO\|nog invullen" docs/AGENTIC_STATE_GAP_ANALYSE.md  # Expected: geen hits
grep -c "^- \*\*Score" docs/AGENTIC_STATE_GAP_ANALYSE.md  # Expected: 6
```

- [ ] **Step 4: Commit**

```bash
git add docs/AGENTIC_STATE_GAP_ANALYSE.md
git commit -m "docs: gap-analyse agentic-state — methode + implementatielagen 1-6 met evidence en L-scores"
```

---

### Task 2: Gap-analyse — enablementlagen 7–12, overzichtstabel en top-gaps

**Files:**
- Modify: `docs/AGENTIC_STATE_GAP_ANALYSE.md` (§3–§5 toevoegen)

**Interfaces:**
- Consumes: Task 1 (document met §1–§2); decision-trail memory als *in-flight* evidence (spec `2026-10-07-decision-trail-memory-design.md`, taken 2–6 lopen).
- Produces: volledige gap-analyse; §5 (top-gaps) is de input voor Task 3 en bevat de drie kandidaten + criteria + aanbeveling.

- [ ] **Step 1: §3 (lagen 7–12) toevoegen**

Voeg na §2 toe:

````markdown
## 3. Enablement-lagen (7–12)

### Laag 7 — Agent Governance

- **Evidence:** trust & governance met cite-or-abstain en PROV (`nldt/07-trust-and-governance.md`);
  governed agent layer (`nldt/12-governed-agent-layer.md`); identiteit via eid-wallet en
  agent-wallet (`nldt/16-eid-wallet-identity.md`); run-journal (`deep-agents/journal.py`) en
  afkeuringsledgers (elk afgewezen agent-voorstel openbaar en gedocumenteerd); decision-trail
  memory als leerstaat **in flight** (`nldt/services/memory/`, spec
  `docs/superpowers/specs/2026-10-07-decision-trail-memory-design.md` — taken 2–6 lopen).
- **Score: L2–L3.** Verantwoordelijkheid en herleidbaarheid zijn aantoonbaar geregeld
  (herkomst per cijfer, gates per voorstel, journal per stap); de leerstaat voegt het
  institutionele leervlak toe dat het paper zelf als governance-antwoord noemt.
- **Koppeling/gap:** B9/B10/B13. Grootste gap: verhaalkracht — dit bestaat al, maar is nergens
  als governance-laag *verteld* (dit document lost dat op) — en bestuurlijke inbedding van
  herstel/redress (steward, beslispuntenkalender: proces, geen code).

### Laag 8 — Data & Privacy

- **Evidence:** medallion data lake met European Data Space-offers (`nldt/13-data-lake-and-space.md`);
  toegangsontkenningslijst (`nldt/data/lake-deny.json`); DONL-harvest (`nldt/18-donl-harvest.md`);
  bronmonitor met watchlist (`nldt/17-source-monitor.md`); autoritatieve bronnen met
  tijdstempel en herkomst per cijfer (PROV, `lastChecked`).
- **Score: L2–L3.** Beschikbaarheid, uitwisselbaarheid en herleidbaarheid zijn sterk geregeld;
  "gedeelde betekenis" (semantische interoperabiliteit) is het Sitra-begrip dat hier het
  meest ontbreekt.
- **Koppeling/gap:** B6 (governed vocabulary als artefact — fase B in het plan). Grootste gap:
  het vocabulary-artefact (concept → autoritatieve bron → eigenaar → correctieroute); privacy
  is klein in dit domein (DPIA staat al op de bestuurlijke agenda, zie
  `nldt/bestuurlijke-samenvatting.md` vraag 5).

### Laag 9 — Tech Stack

- **Evidence:** model-vervangbaarheid via `deep-agents/models.py` (lokale Ollama/Laya-modellen,
  cloud-tier wordt geweigerd); tools achter contracten en MCP-servers (`nldt/services/mcp_servers/`,
  `nldt/services/a2a/`); recipe/process-contracten model-agnostisch (`nldt/00-architecture.md`,
  `nldt/04-recipes-and-processes.md`); containerisatie (`docker-compose.yml`).
- **Score: L2–L3.** De stapel bestaat, werkt op een cluster en is bewust vervangbaar gehouden
  (B7: "duurzaam werk, vervangbare technologie"). Meer is voor dit domein ook niet nodig:
  het paper ziet de stack als enablement, niet als doel.
- **Koppeling/gap:** B7/B12. Grootste gap: geen wezenlijke — eventueel schaalbaarheid buiten
  pilotschaal, maar dat is een exploitatievraag, geen architectuurgap.

### Laag 10 — Cyber Security & Resilience

- **Evidence:** `nldt/SECURITY.md`; trust-policy (`nldt/data/trust-policy.example.json`);
  wallet-identiteit voor agenten (`nldt/16`); lake-deny (`nldt/data/lake-deny.json`); en de
  gates zelf als inbrengverdediging (schema-gates vangen vormdrift en manipulatie vóór
  executie; afkeuring gaat naar het ledger, nooit het product in).
- **Score: L1–L2.** Basismaatregelen (identiteit, beleid, deny-lists, gates) zijn er; het
  paper-thema — security *ontworpen voor autonome systemen* — is niet expliciet gedesign.
- **Koppeling/gap:** B8 (mens-agent-grens als veiligheidsmechanisme). Grootste gap: een
  expliciete blik op agent-specifieke dreigingen (prompt injection via brondata,
  agent-naar-agent manipulatie) en resilience-gedrag bij falende modellen.

### Laag 11 — Public Finance & Buying Agents

- **Evidence:** geen. Dichtstbij: de bestuurlijke vraag om mandaat en middelen
  (`nldt/bestuurlijke-samenvatting.md`, vraag 3).
- **Score: L0.** Afwezig en bewust out-of-scope voor de referentie-implementatie.
- **Koppeling/gap:** geen. Vastlegging: een organisatie-/procesvraag (financiering van de
  leerperiode), geen repo-opgave.

### Laag 12 — People, Culture & Leadership

- **Evidence:** doctrine "AI stelt voor · pijplijn beslist · mens beslist"
  (`docs/GENAI_SEAMS.md`); bestuurlijke verhaallijnen (`nldt/bestuurlijke-samenvatting.md`,
  `docs/POC_BESTUURLIJKE_SAMENVATTING.md`); playbooks als procedureel geheugen
  (`nldt/skills/poc/`); leerstaat/decision-trail in flight (lagen 7); HITL ontworpen
  (fase C) maar niet geïmplementeerd.
- **Score: L2.** De doctrine en de bestuurlijke laag zijn echt en consequent toegepast;
  wat ontbreekt is precies wat het paper de kern van deze laag noemt: de mens-agent-grens
  die *in de workflow* werkt (HITL) en de leiderschapsleerloop (vier
  leiderschapsverantwoordelijkheden uit het Sitra-onderzoek, B10/B13).
- **Koppeling/gap:** B8/B10/B13/B14. Grootste gap: HITL-implementatie en de
  beslispuntenkalender als proces.

## 4. Overzicht

| # | Laag | Score | Sterkste evidence | Grootste gap |
|---|---|---|---|---|
| 1 | Service design & UX | L2 | Omgevingschat (buiten repo), Q&A-gate Breda | proactieve dienstverlening |
| 2 | Government workflows | **L3** | volledige keten + gates + journal | HITL-interrupts (B8) |
| 3 | Policy- & rule-making | L2 (+L3-aanzet) | normkaarten met citaten, S7/S8 | regel-terugkoppellus |
| 4 | Compliance & supervision | L2 | V0–V4, golden-regressie, bronmonitor | continue toezicht + bewijstechniek |
| 5 | Crisis response | L0 | — | bewust out-of-scope (vastlegging) |
| 6 | Public procurement | L0–L1 | dataspace-offers, EDIC | out-of-scope; kanaal bestaat |
| 7 | Agent governance | **L2–L3** | cite-or-abstain, PROV, journal, leerstaat | verhaalkracht + redress-proces |
| 8 | Data & privacy | **L2–L3** | lake, bronmonitor, DONL, PROV | governed vocabulary (B6) |
| 9 | Tech stack | **L2–L3** | lokale modellen, MCP/A2A, contracten | — (bewust vervangbaar gehouden) |
| 10 | Cyber security | L1–L2 | SECURITY, wallet, gates, lake-deny | agent-specifiek securitydesign |
| 11 | Public finance | L0 | — | out-of-scope (procesvraag) |
| 12 | People & leadership | L2 | GENAI_SEAMS-doctrine, leerstaat | HITL + leiderschapsleerloop |

**Leeswijzer:** het repo is een **L3-agentic workflow in een begrensd domein** — precies het
autonomieniveau dat het paper aanbeveelt voor gevoelige overheidsdomeinen. De enablement-lagen
7/8/9 scoren mee omdat governance, data-herkomst en vervangbaarheid vanaf dag één
meegemaakt zijn; de implementatielagen 5, 6 en 11 zijn bewust niet in scope.

## 5. Top-gaps → volgende stap

De drie gaps die het meest opleveren, gescoord op de criteria uit de beslissessie
(whitepaper-alignering × Sitra-poortlogica × repo-gereedheid):

| Kandidaat | Lagen | Sitra | Repo-gereedheid |
|---|---|---|---|
| **a. HITL / mens-agent-grens** | 2, 10, 12 | B8, poort 3 | hoog: bp2op (V4-altijd-pending) is aangewezen eerste instantie; `interrupt_on` al genoemd als volgende stap in de deep-agents-README |
| **b. Functiecatalogus + readyheidskaart (fase A)** | 2, 12 | B1–B3, poorten 1–2 | middel: materiële aanwezig (6 instanties), maar classificatieproject-risico (waarschuwing Sitra: geen complete catalogus vóór testen) |
| **c. Function-baseline + stopcondities (poort 1/5)** | 4, 7 | B9, B14 | middel-hoog: eval-harness (golden + jobId-correlatie) is net af; baseline-artefact en stopconditieveld zijn nieuw |

**Aanbeveling: a (HITL).** Raakt drie lagen tegelijk, is de randvoorwaarde voor de
fase C/D-demonstrator, heeft de hoogste repo-gereedheid en is het thema dat de whitepaper
het zwaarst weegt: mensen houden de knoppen, aantoonbaar. Let op: de decision-trail memory
(taken 2–6) loopt nog; de gekozen stap start als eigen spec/plan ná afronding daarvan.
````

- [ ] **Step 2: Verifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "^### Laag" docs/AGENTIC_STATE_GAP_ANALYSE.md   # Expected: 12
grep -c "^| [0-9]* |" docs/AGENTIC_STATE_GAP_ANALYSE.md # Expected: 12 (alle rijen van de §4-overzichtstabel)
grep -n "TBD\|TODO\|nog invullen" docs/AGENTIC_STATE_GAP_ANALYSE.md  # Expected: geen hits
grep -c "in flight" docs/AGENTIC_STATE_GAP_ANALYSE.md   # Expected: ≥ 2 (lagen 7 en 12)
```

- [ ] **Step 3: Commit**

```bash
git add docs/AGENTIC_STATE_GAP_ANALYSE.md
git commit -m "docs: gap-analyse agentic-state — enablementlagen 7-12, overzichtstabel, top-gaps met aanbeveling"
```

---

### Task 3: Beslissessie "volgende stap" (interactief — orchestrator, geen subagent)

**Files:**
- Modify: `docs/AGENTIC_STATE_GAP_ANALYSE.md` (§5 afsluiten met de beslissing)

**Interfaces:**
- Consumes: Task 2 (§5 met kandidaten en aanbeveling).
- Produces: het besluit in §6 van de gap-analyse; de tekst voor beslispunt 7 in Task 4.

- [ ] **Step 1: Marc de keuze voorleggen**

Gebruik AskUserQuestion met precies deze opbouw (header `Volgende stap`, één vraag):

> De gap-analyse is klaar. Welke gap pakken we als volgende stap aan? (§5 van
> `docs/AGENTIC_STATE_GAP_ANALYSE.md` bevat de volledige onderbouwing.)

- Optie 1 — **HITL / mens-agent-grens (Aanbevolen)**: "Lagen 2/10/12 · B8 · poort 3. bp2op ligt klaar als eerste instantie; hoogste repo-gereedheid; randvoorwaarde voor de fase C/D-demonstrator."
- Optie 2 — **Functiecatalogus + readyheidskaart (fase A)**: "Lagen 2/12 · B1–B3. Het Sitra-startpunt uit het plan; risico: klassificatieproject vóór testen."
- Optie 3 — **Function-baseline + stopcondities**: "Lagen 4/7 · B9 poort 1/5. Eval-harness is net af, timing gunstig; twee nieuwe artefacten."

- [ ] **Step 2: Besluit vastleggen in de gap-analyse**

Voeg na §5 toe (vul de keuze en eventuele toelichting van Marc letterlijk in):

````markdown
## 6. Besluit volgende stap (2026-10-07)

**Gekozen:** [letterlijke keuze van Marc].

**Toelichting:** [toelichting van Marc, of "geen"]. De stap wordt vastgelegd als beslispunt 7
in `AGENTIC_STATE_PLAN.md` §9 en doorloopt de eigen spec/plan-cyclus ná afronding van de
decision-trail memory (taken 2–6).
````

- [ ] **Step 3: Verifiëren en committen**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "^## 6\. Besluit" docs/AGENTIC_STATE_GAP_ANALYSE.md  # Expected: 1
git add docs/AGENTIC_STATE_GAP_ANALYSE.md
git commit -m "docs: gap-analyse — besluit volgende stap vastgelegd"
```

---

### Task 4: `docs/AGENTIC_STATE_PLAN.md` → v1.2

**Files:**
- Modify: `docs/AGENTIC_STATE_PLAN.md` (kopregel, nieuwe §0a, §9 beslispunt 7, §10 bronnen)

**Interfaces:**
- Consumes: Task 2 (§4-koppelingen), Task 3 (besluit).
- Produces: plan v1.2 als het gecombineerde kader-document (whitepaper-vision + Sitra-methode).

- [ ] **Step 1: Kopregel bijwerken**

Vervang in de documenttabel (regel 5) de versieregel:

```markdown
| Document | `docs/AGENTIC_STATE_PLAN.md` · v1.2 · 2026-10-07 (v1.2: whitepaper-kader als §0a — The Agentic State als vision-frame bovenop de Sitra-methode; beslispunt 7: volgende stap uit gap-analyse) |
```

- [ ] **Step 2: §0a invoegen na §0 Samenvatting (na regel 25, vóór de `---`)**

```markdown
## 0a. Het whitepaper-kader — The Agentic State als vision-frame

De whitepaper *The Agentic State* (Ilves e.a., 2025; launch Tallinn Digital Summit) beschrijft
hoe agentic AI de overheid herschikt langs **twaalf functionele lagen**: zes implementatielagen
(1 service design & UX · 2 government workflows · 3 policy- & rule-making · 4 regulatory
compliance & supervision · 5 crisis response · 6 public procurement) en zes enablement-lagen
(7 agent governance · 8 data & privacy · 9 tech stack · 10 cyber security & resilience ·
11 public finance & buying agents · 12 people, culture & leadership), met een
autonomieschaal **L0–L5**. Kernboodschap: hoger autonomieniveau is niet beter — het juiste
niveau volgt uit risico, complexiteit en toezichtbehoefte; *"a reliable Level 3 system may
beat an unpredictable Level 4 in sensitive domains."*

**Verhouding tot dit plan:** de whitepaper is hier het **vision-frame** (waarheen: de lagen
waarop agentic AI overheidswerk raakt, en op welk autonomieniveau), het Sitra-onderzoek
(B1–B14, dit plan §1/§3) blijft de **methode** (hoe: functie-first, poorten, leerloop). De
gap-analyse ([`AGENTIC_STATE_GAP_ANALYSE.md`](AGENTIC_STATE_GAP_ANALYSE.md)) scoret het repo
per laag: L3 op government workflows, L2–L3 op governance/data/tech-stack, L2 op
rule-making/compliance/people, L0 op crisis/procurement/finance (bewust out-of-scope).

| Whitepaper-laag | Sitra-block | Landingsplaats in de toolbox |
|---|---|---|
| 1 Service design & UX | B6, B11 | Omgevingschat-platform (zusterrepo), `nldt/14`, Q&A-gates |
| 2 Government workflows | B1, B2, B8 | `deep-agents/`-keten, recipes, fase C/D (HITL) |
| 3 Policy- & rule-making | B2, B6 | normkaarten/citaten, `poc-bp2op/`, verordening-fases |
| 4 Compliance & supervision | B9 | V0–V4, eval-harness/golden, `nldt/17` |
| 5 Crisis response | — | niet in scope (vastlegging) |
| 6 Public procurement | B12 | dataspace-offers, `nldt/edic/`, EU-marketplace-kanaal |
| 7 Agent governance | B9, B10, B13 | `nldt/07`, `nldt/12`, journal, decision-trail (leerstaat) |
| 8 Data & privacy | B6 | `nldt/13`, `nldt/17`, `nldt/18`, governed vocabulary (fase B) |
| 9 Tech stack | B7, B12 | `deep-agents/models.py`, MCP/A2A-adapters, contracten |
| 10 Cyber security & resilience | B8 | `nldt/SECURITY.md`, wallet, schema-gates, lake-deny |
| 11 Public finance & buying agents | — | niet in scope (procesvraag, bestuurlijke vraag 3) |
| 12 People, culture & leadership | B8, B10, B13, B14 | `docs/GENAI_SEAMS.md`-doctrine, leerstaat, stewardship |
```

- [ ] **Step 3: Beslispunt 7 toevoegen in §9**

Voeg aan het einde van de genummerde lijst in §9 toe (tekst uit Task 3-uitkomst):

```markdown
7. **Volgende stap uit de gap-analyse** — besluit genomen op 2026-10-07: [letterlijke keuze]; onderbouwing in `AGENTIC_STATE_GAP_ANALYSE.md` §5–§6. Start als eigen spec/plan ná afronding van de decision-trail memory.
```

- [ ] **Step 4: §10 bronnen — whitepaper promoveren**

Zet bovenaan de bronnenlijst in §10, vóór het Sitra-working-paper:

```markdown
- The Agentic State (primaire vision-bron): Ilves, L., Kilian, M., Parazzoli, S. M., Peixoto, T. C., Velsberg, O. (2025) — <https://agenticstate.org/paper.html>
```

en verwijder de oude losse verwijzing `Ilves, L. et al. (2025): *The Agentic State* — <https://agenticstate.org/paper.html>` uit dezelfde lijst (dubbelop).

- [ ] **Step 5: Verifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "v1.2" docs/AGENTIC_STATE_PLAN.md                # Expected: ≥ 2
grep -c "^## 0a\." docs/AGENTIC_STATE_PLAN.md            # Expected: 1
grep -c "agenticstate.org" docs/AGENTIC_STATE_PLAN.md    # Expected: 1 (alleen de gepromoveerde §10-bronregel; de oude losse vermelding is verwijderd en §0a noemt de titel zonder URL)
grep -n "Ilves, L. et al." docs/AGENTIC_STATE_PLAN.md    # Expected: geen hits (oude regel weg)
grep -c "^7\. \*\*Volgende stap" docs/AGENTIC_STATE_PLAN.md  # Expected: 1
grep -c "B10\|B13" docs/AGENTIC_STATE_PLAN.md            # Expected: ongewijzigd ≥ bestaand aantal (§1–§5 niet aangeraakt)
```

- [ ] **Step 6: Commit**

```bash
git add docs/AGENTIC_STATE_PLAN.md
git commit -m "docs(plan): agentic-state-plan v1.2 — whitepaper-kader als §0a, beslispunt 7 (volgende stap), whitepaper als primaire bron"
```

---

### Task 5: Slides NL + EN — 12-lagen-positionering als slide

**Files:**
- Modify: `docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md` (nieuwe slide vóór `## Slot:` op regel ~286; colofon-aanvulling)
- Modify: `docs/slides/2026-09-13-agentic-ai-spatial-planning-en.md` (nieuwe slide tussen `## What agentic AI yields per value…` (eind ~regel 576) en `## Next 1` (regel 577))

**Interfaces:**
- Consumes: Task 2 (§4-overzichtstabel).
- Produces: NL- en EN-decks met één positioneringsslide langs het whitepaper-kader.

- [ ] **Step 1: NL-slide invoegen**

Voeg in het NL-deck direct vóór de slide `## Slot: Creating *Real* Value` in:

````markdown
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
````

- [ ] **Step 2: NL-colofon aanvullen**

Voeg in de laatste slide (`## Colofon & herleiding`) toe aan de bronnenlijst:

```markdown
- Kader: *The Agentic State* (Ilves e.a., 2025, agenticstate.org) · gap-analyse:
  `docs/AGENTIC_STATE_GAP_ANALYSE.md`
```

- [ ] **Step 3: EN-slide invoegen**

Voeg in het EN-deck direct vóór `## Next 1 — the scenario seam for the five-value scan` in:

````markdown
---

<!-- _class: track-neutral -->

## Where this sits in *The Agentic State* framework

*The Agentic State* (Ilves et al., 2025) orders government agentic AI across **twelve
functional layers** — six implementation, six enablement — with an autonomy scale L0–L5.
The toolbox scores strongest exactly where it matters in this domain:

| Layer | Concern | Toolbox |
|---|---|---|
| 2 Workflows | self-orchestrating delivery | **L3** — full chain with gates & critic |
| 7 Governance | accountability & redress | cite-or-abstain · PROV · learning trail |
| 8 Data | shared meaning & provenance | source monitor · authoritative citations |
| 4 Compliance | supervision & assurance | V0–V4 · golden regression |

> **L3 in a bounded domain** is exactly the level the paper recommends for sensitive
> domains: *"a reliable Level 3 system may beat an unpredictable Level 4."*

Full per-layer analysis: `docs/AGENTIC_STATE_GAP_ANALYSE.md` — method: the Sitra gates.
````

- [ ] **Step 4: Verifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "unpredictable Level 4" docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md docs/slides/2026-09-13-agentic-ai-spatial-planning-en.md
# Expected: 2 bestanden, elk 1 hit
grep -n "^## Slot\|Positie in het kader" docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md
# Expected: de Positie-slide staat boven de regel met "## Slot"
```

Optioneel (indien marp geïnstalleerd): `npx @marp-team/marp-cli docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md -o /tmp/slides.html` — Expected: build slaagt. Niet-blokkerend als marp/marp-vscode offline is.

- [ ] **Step 5: Commit**

```bash
git add docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md docs/slides/2026-09-13-agentic-ai-spatial-planning-en.md
git commit -m "docs(slides): positionering langs The Agentic State — 12-lagen-kader + L3-boodschap (NL/EN)"
```

---

### Task 6: Bestuurlijke samenvatting + demo-scènes annoteren

**Files:**
- Modify: `nldt/bestuurlijke-samenvatting.md` (nieuwe sectie na "Vier verhaallijnen", vóór "Wat dit bestuurlijk oplevert" op regel ~29)
- Modify: `nldt/simulation/agentic-state-demo.html` (CSS-regel + laag-tags per scène + bronnenregel titelscène)

**Interfaces:**
- Consumes: Task 2 (§4-scores); Task 4 (gap-analyse bestaat en is gecommit).
- Produces: bestuurlijke samenvatting met kadersectie; demo waarin elke scène zijn whitepaper-laag toont. De EN-demo (`agentic-state-demo-en.html`) is **buiten scope** (volgt in een latere ronde; dit staat in de §6-notitie hieronder).

- [ ] **Step 1: Sectie in de samenvatting invoegen**

Voeg tussen "Vier verhaallijnen" (eind regel 27) en `## Wat dit bestuurlijk oplevert` in:

````markdown
## Positie in het agentic-state-kader

De whitepaper *The Agentic State* (Ilves e.a., 2025) beschrijft twaalf functionele lagen
waarop agentic AI de overheid raakt — zes implementatie- en zes enablement-lagen — met een
autonomieschaal van L0 (handmatig) tot L5 (volledig autonoom). De toolbox is daarop gescoord:
**L3 in een begrensd domein** (agentic workflows met planning en toezicht — exact het niveau
dat het paper voor gevoelige domeinen aanbeveelt), sterk op **governance** (verantwoordelijkheid,
herkomst, leerstaat) en op **data** (autoritatieve bronnen, gedeelde betekenis). Crisisrespons,
inkoop en publieke financiën zijn bewust niet in scope. Volledige onderbouwing per laag:
[`docs/AGENTIC_STATE_GAP_ANALYSE.md`](../docs/AGENTIC_STATE_GAP_ANALYSE.md).
````

- [ ] **Step 2: CSS-regel voor de laag-tag toevoegen**

Zoek in `nldt/simulation/agentic-state-demo.html` het eerste `<style>`-blok en voeg onderaan dat blok toe (letterlijke kleuren, geen var-afhankelijkheid):

```css
.kicker .laag { margin-left:.9rem; padding:.12rem .55rem; border:1px solid rgba(6,6,68,.22);
  border-radius:999px; font-size:.62rem; letter-spacing:.06em; text-transform:uppercase;
  color:#060644; background:rgba(9,159,128,.08); white-space:nowrap; }
```

- [ ] **Step 3: Kicker exact lezen per scène**

```bash
grep -n 'class="kicker"' nldt/simulation/agentic-state-demo.html
```

Expected: 10 regels (één per scène). Noteer de exacte huidige tekst van elke kicker-regel.

- [ ] **Step 4: Laag-tag per scène toevoegen**

Vóór de afsluitende `</p>` van elke kicker, voeg `<span class="laag">…</span>` toe volgens deze mapping:

| Scène (`data-title`) | Laag-tag |
|---|---|
| Titel | (geen tag; alleen bronnenregel, Step 5) |
| Diagnose | `Whitepaper-kader` |
| De functie | `Laag 2 · Workflows` |
| Simulatie | `Laag 2 · 4 — workflows & toezicht` |
| PoC's | `Laag 1 · 2 — dienst & workflow` |
| Vijf poorten | `Laag 7 · 10 — governance & security` |
| Hergebruik | `Laag 8 · 9 — data & stack` |
| Leerloop | `Laag 7 · 12 — governance & mens` |
| Het pad | `Laag 12 · leadership` |
| Vraag aan het bestuur | `Laag 11 · 12 — mandaat & mens` |

Werkvoorbeeld (scène Diagnose; pas de anderen analoog aan op hun eigen exacte kickertekst):

```html
<!-- vóór --> <p class="kicker">1 · De diagnose</p>
<!-- na   --> <p class="kicker">1 · De diagnose<span class="laag">Whitepaper-kader</span></p>
```

- [ ] **Step 5: Bronnenregel titelscène uitbreiden**

Vervang in de titelscène (regel ~274) de bronnenregel:

```html
    <p class="src"><b>Bronnen:</b> <em>The Agentic State</em> (Ilves e.a., 2025,
    agenticstate.org — twaalf lagen, L0–L5) · Sitra — <em>The Next Right Questions on the Path
    to the Agentic State</em> (2026) · <em>docs/AGENTIC_STATE_PLAN.md</em> ·
    <em>docs/AGENTIC_STATE_GAP_ANALYSE.md</em> · <em>docs/POC_BESTUURLIJKE_SAMENVATTING.md</em>.
    Blader met <b>→ / ←</b>.</p>
```

- [ ] **Step 6: Notitie over de EN-demo**

Voeg in de gap-analyse, na de tabel in §4 Overzicht, een regel toe:

```markdown
*Notitie: de Engelstalige demo (`agentic-state-demo-en.html`) volgt in een latere ronde; deze
annotatieronde dekt de Nederlandse demo.*
```

- [ ] **Step 7: Verifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -c "class=\"laag\"" nldt/simulation/agentic-state-demo.html  # Expected: 9 (alle scènes behalve titel)
grep -c "agenticstate.org" nldt/bestuurlijke-samenvatting.md nldt/simulation/agentic-state-demo.html  # Expected: elk ≥ 1
grep -n "AGENTIC_STATE_GAP_ANALYSE" nldt/bestuurlijke-samenvatting.md  # Expected: 1 hit met werkende relatieve link
grep -c "lateren ronde\|latere ronde" docs/AGENTIC_STATE_GAP_ANALYSE.md  # Expected: 1
```

- [ ] **Step 8: Commit**

```bash
git add nldt/bestuurlijke-samenvatting.md nldt/simulation/agentic-state-demo.html docs/AGENTIC_STATE_GAP_ANALYSE.md
git commit -m "docs: bestuurlijke samenvatting + demo geannoteerd met het whitepaper-kader (12 lagen)"
```

---

### Task 7: Eindverificatie + executiestatus

**Files:**
- Modify: `docs/superpowers/plans/2026-10-07-agentic-state-whitepaper-kader.md` (executiestatus onderaan)

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: geverifieerde eindstand + statuscommit conform repo-conventie.

- [ ] **Step 1: Evidence-claims in de gap-analyse herverifiëren**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -o '`[^`]*\.\(md\|py\|json\)`' docs/AGENTIC_STATE_GAP_ANALYSE.md | tr -d '`' | sort -u | while read -r p; do
  [ -e "$p" ] && echo "OK         $p" || echo "ONTBREEKT  $p"; done
```

Expected: alleen `OK`-regels voor paden binnen de repo (`../omgevingschat-platform-develop` is documentatie-vorm en valt buiten deze check — indien het pad letterlijk staat, handmatig controleren). Bij `ONTBREEKT`: de claim in de gap-analyse herstellen (pad corrigeren of tekst aanpassen) en opnieuw committen.

- [ ] **Step 2: Consistentiecheck over de vier deliverables**

```bash
cd /Users/marc/Projecten/ldttoolbox
grep -rn "TBD\|TODO\|nog invullen" docs/AGENTIC_STATE_GAP_ANALYSE.md docs/AGENTIC_STATE_PLAN.md \
  nldt/bestuurlijke-samenvatting.md docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md \
  docs/slides/2026-09-13-agentic-ai-spatial-planning-en.md   # Expected: geen hits
grep -c "12\|twaalf" docs/AGENTIC_STATE_GAP_ANALYSE.md docs/AGENTIC_STATE_PLAN.md  # Expected: hits in beide (het frame)
git log --oneline -8   # Expected: de commits uit Tasks 1–6, elk met alleen de eigen bestanden
```

Extra: `git show --stat HEAD~5..HEAD` — Expected: geen commit raakt `nldt/schemas/decision-trail.schema.json`, `nldt/services/memory/` of `nldt/tests/test_memory_store.py` (andere werkstroom).

- [ ] **Step 3: Executiestatus in dit plan vastleggen**

Voeg onderaan dit plantdocument toe:

```markdown
## Executiestatus

| Taak | Status |
|---|---|
| 1. Gap-analyse scaffold + lagen 1–6 | klaar (commit: …) |
| 2. Gap-analyse lagen 7–12 + top-gaps | klaar (commit: …) |
| 3. Beslissessie volgende stap | klaar (commit: …) |
| 4. Plan → v1.2 | klaar (commit: …) |
| 5. Slides NL/EN | klaar (commit: …) |
| 6. Samenvatting + demo | klaar (commit: …) |
| 7. Eindverificatie | klaar — alle evidence-claims OK, geen placeholders |

Deviaties: [noteer hier afwijkingen van het plan, of "geen"].
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-10-07-agentic-state-whitepaper-kader.md
git commit -m "docs(plans): executiestatus agentic-state whitepaper-kader — 7 taken klaar, eindverificatie groen"
```

## Executiestatus

| Taak | Status |
|---|---|
| 1. Gap-analyse scaffold + lagen 1–6 | klaar (commit: 6dfe9bb) |
| 2. Gap-analyse lagen 7–12 + top-gaps | klaar (commit: 3c7e47e) |
| 3. Beslissessie volgende stap | klaar (commit: 4df44bf) — voorgelegd aan Marc maar niet bevestigd; vastgelegd als VOORSTEL a (HITL), beslispunt 7 in het plan in voorstel-formulering |
| 4. Plan → v1.2 | klaar (commit: fb80958) |
| 5. Slides NL/EN | klaar (commit: c011a0a) |
| 6. Samenvatting + demo | klaar (commit: 8424c96) |
| 7. Eindverificatie | klaar — alle evidence-claims OK, geen placeholders |

Deviaties: (1) beslissessie onbevestigd → voorstel-formulering in gap-analyse §6 en beslispunt 7 (taak 3/4). (2) citatie-uitbreiding "(Ilves e.a., 2025, agenticstate.org)" in de bestuurlijke samenvatting — planstekort: Step 1 verbatim bevatte het domein niet, Step 7 eiste het (taak 6). (3) notitie EN-demo na de §4-leeswijzer i.p.v. direct onder de tabel (taak 6). (4) padcorrectie in de gap-analyse `AGENTIC_STATE_PLAN.md` → `docs/AGENTIC_STATE_PLAN.md` (r.7 en r.220) — ONTBREEKT bij de Step-1-herverificatie, aparte commit e27dcb3 (taak 7). Review-minors niet verwerkt: laag 12 "(lagen 7)"→"(zie laag 7)", "nldt/16"-afkorting, de §0a-samenvatting vlakt score-ranges af ("L2 (+L3-aanzet)"→"L2", "L0–L1"→"L0"), nowrap-overflow risico .laag-tag. (5) slides tonen een 4-laagse selectietabel + verwijzing i.p.v. de volledige maturity-heatmap als kernplaat (spec §4) — 12 rijen is te dicht voor een slide; de volledige tabel blijft in gap-analyse §4.
