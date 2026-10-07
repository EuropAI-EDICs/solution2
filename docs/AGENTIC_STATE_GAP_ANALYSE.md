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
