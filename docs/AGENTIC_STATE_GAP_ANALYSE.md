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
