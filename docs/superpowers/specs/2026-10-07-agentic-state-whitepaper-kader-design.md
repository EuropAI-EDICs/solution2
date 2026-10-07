# Ontwerp — The Agentic State whitepaper-kader: gap-analyse, plan v1.2 en uitdracht

| | |
|---|---|
| **Datum** | 7 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | de whitepaper *The Agentic State* (Ilves e.a., 2025) als overkoepelend verhaalkader over het bestaande Sitra-plan: (1) gap-analyse per 12 functionele lagen met L0–L5-maturiteitsscores, (2) `docs/AGENTIC_STATE_PLAN.md` → v1.2 met het whitepaper-kader ingebouwd, (3) beslissessie "volgende stap" op basis van de gap-analyse, (4) bestaande uitdracht-artifacts (slides NL/EN, bestuurlijke samenvatting, demo) herverteld langs het kader |
| **Buiten scope** | implementatie van de gekozen volgende stap (krijgt eigen spec/plan) · herbouw of herstructurering van het Sitra-plan (aanpak B verworpen) · nieuwe uitdracht-artifacts bouwen (alleen hervertellen van bestaande) · Engelse versie van de gap-analyse zelf · lagen 5/6/11 (crisis, inkoop, financiën) vertalen naar werk — hun afwezigheid is een vastlegging, geen actiepunt |
| **Bronnen** | [The Agentic State](https://agenticstate.org/paper.html) (12 functionele lagen: 6 implementatie + 6 enablement; L0–L5-autonomieclassificatie naar Bornet e.a. 2025) · [`AGENTIC_STATE_PLAN.md`](../../AGENTIC_STATE_PLAN.md) v1.1 (Sitra-building-blocks B1–B14 als operationele methode) · repo-evidence: `deep-agents/`, `poc*/`, `nldt/` (00–25), zusterplatform Omgevingschat (`../omgevingschat-platform-develop`) |
| **Keuzes uit de sessie** | alle vier doelen gekozen (gap-analyse, kader in plan, volgende stap kiezen, verhaal uitdragen) · aanpak **A**: 12 lagen als kader, Sitra als methode — niet B (volledige herstructurering, klassificatierisico) en niet C (minimaal, levert uitdracht niet) · uitdracht = bestaande artifacts hervertellen |

## Context en doel

Het AGENTIC_STATE_PLAN (v1.1) vertaalt het Sitra-vervolgonderzoek (*The Next Right Questions…*, sept 2026) naar dit repo en noemt de whitepaper van Ilves e.a. in de bronnenlijst — maar het 12-laagskader van de whitepaper is nog nergens het leidende kader. De whitepaper beschrijft *waarheen* (functionele lagen waar agentic AI overheidswerk herschikt, met een L0–L5-autonomiematuurmodel); het Sitra-onderzoek beschrijft *hoe* (functie-first, poorten, leerstaat). Die twee zijn complementair, niet concurrerend.

Dit ontwerp legt de whitepaper als overkoepelend vision-frame over het plan, maakt de stand van het repo per laag eerlijk zichtbaar (gap-analyse), kiest uit de top-gaps de volgende stap, en vertelt het verhaal naar buiten toe langs hetzelfde kader. Alles is docs-werk; er verandert geen code.

**De narratieve hook die de gap-analyse naar verwachting oplevert:** dit repo is een L3-agentic workflow in een begrensd domein — precies het autonomieniveau dat de whitepaper aanbeveelt voor gevoelige overheidsdomeinen ("a reliable Level 3 system may beat an unpredictable Level 4"). Het verhaal is niet "wij zijn nog niet ver", maar "wij zitten op het juiste niveau en bouwen het laag voor laag uit, met de poorten van Sitra als beveiliging".

## 1. Deliverable: `docs/AGENTIC_STATE_GAP_ANALYSE.md` (nieuw)

Brugdocument tussen whitepaper, Sitra-plan en repo. Vast stramien per laag, drie onderdelen:

1. **Repo-evidence** — concrete bestanden/PoC's/platformdelen die de laag raakvlak geven (inclusief het zusterplatform Omgevingschat waar van toepassing, expliciet als buiten-repo gemarkeerd);
2. **L0–L5-maturiteitsscore** met onderbouwing (score zonder bewijs is een claim, geen analyse);
3. **Koppeling** naar het Sitra-building-block en de bestaande landingsplaatsen uit plan §3, plus de grootste gap.

Structuur: §1 methode · §2 implementatielagen 1–6 · §3 enablementlagen 7–12 · §4 overzichtstabel (laag | score | sterkste evidence | grootste gap) · §5 top-gaps → prioritering. Voorlopige inschatting (in de analyse zelf met evidence onderbouwd of bijgesteld):

| Laag | Verwachte score | Sterkste evidence | Opvallende gap |
|---|---|---|---|
| 2 Government workflows | **L3** | deep-agents volledige keten (intake → … → explainer) + artifact gates + journal | HITL-interrupts (B8) nog niet geïmplementeerd |
| 7 Agent governance | L2–L3 | cite-or-abstain, PROV, governed agent layer (`nldt/07`, `nldt/12`) | verhaalkracht: bestaat, maar nog niet als zodanig verteld |
| 8 Data & privacy | L2–L3 | medallion lake, DONL-harvest, source monitor, dataspace offers | governed vocabulary / gedeelde betekenis (B6) |
| 9 Tech stack | L2–L3 | lokale modellen, MCP/A2A, vervangbaarheid (B7) | — |
| 1 Service design & UX | L2–L3 | Omgevingschat-platform (buiten repo, productrijp) | proactieve, zelfcomposerende dienstverlening |
| 12 People, culture, leadership | L2 | doctrine "AI stelt voor · pijplijn beslist · mens beslist" (`GENAI_SEAMS`); leerstaat B10 in flight | HITL-implementatie; leerstaat nog niet af |
| 3 Policy- & rule-making | L2 | verordening-fases, beleidskompas, IMRO-conversie | dynamische simulatie, adaptieve regels |
| 4 Compliance & supervision | L2 | V0–V4-validatie, critic, compliance-declaration-schema | continue toezicht, minimal-disclosure/maximal-assurance |
| 5 Crisis response · 6 Procurement · 11 Public finance | **L0** | — | afwezig; 5 en 6 deels terecht out-of-scope voor het RO-domein — dat is óók een vastlegging |

Elke evidence-claim in het definitieve document verwijst naar een bestaand bestand of PoC; de decision-trail memory (in flight, taken 2–6) wordt als in-flight evidence gemarkeerd.

## 2. Deliverable: `docs/AGENTIC_STATE_PLAN.md` → v1.2

Light touch — de Sitra-structuur B1–B14 en de fasering §5 blijven ongemoeid:

- **Nieuwe §0a "Het whitepaper-kader"**: The Agentic State als overkoepelend vision-frame; de twaalf lagen benoemd; positionering vision-frame (whitepaper) vs. methode (Sitra); één koppelingstabel 12 lagen ↔ Sitra-building-blocks ↔ repo-landingsplaatsen (verwijst naar de gap-analyse voor scores).
- **§9 beslispunten**: nieuw beslispunt "volgende stap uit gap-analyse" met de uitkomst van de beslissessie (§3 hieronder).
- **§10 bronnen**: de whitepaper promoveren van een van de bronnen naar primaire bron naast het Sitra-working-paper.
- Kopregel (versie/datum/wijziging) conform bestaand patroon.

## 3. Beslissessie: volgende stap kiezen (na de gap-analyse)

De gap-analyse levert top-gaps met evidence; daarna volgt een beslissessie met Marc (meerkeuze met aanbeveling). Het ontwerp legt de **criteria** vast, niet de uitkomst:

- **whitepaper-alignering** — versterkt de stap een implementatie- of enablementlaag waar het repo al voortgang boekt (momentum meenemen i.p.v. bij nul beginnen)?;
- **Sitra-poortlogica** — draagt de stap aan poort 1–5 (B9) en/of aan B1–B14 in het algemeen?;
- **repo-gereedheid** — ligt er werk klaar of is het nieuwbouw?

Verwachte kandidaten (volgorde bepaalt de gap-analyse): **(a)** HITL/mens-agent-grens (B8, poort 3, bp2op ligt klaar als eerste instantie) · **(b)** functiecatalogus + readyheidskaart fase A (B1–B3) · **(c)** function-baseline + stopcondities (poort 1/5 — de eval-harness is net af, timing is gunstig). De uitkomst wordt een nieuw beslispunt in plan §9 en gaat daarna door de eigen spec/plan-cyclus (buiten scope hier).

## 4. Deliverable: uitdracht — bestaande artifacts hervertellen

Geen nieuwe artifacts; het kader komt ín de bestaande uitdracht:

| Artifact | Aanpassing |
|---|---|
| `docs/slides/2026-09-13-agentic-ai-in-de-ruimtelijke-ordening.md` (+ EN-versie) | sectie toevoegen die het werk langs de 12 lagen positioneert, met de maturity-heatmap (gap-analyse §4) als kernplaat en de L3-in-begrensd-domein-boodschap |
| `nldt/bestuurlijke-samenvatting.md` | 12-lagen-positionering + verwijzing naar de gap-analyse |
| `nldt/simulation/agentic-state-demo.html` | de tien scènes annoteren met de laag (1–12) die elke scène demonstreert |

## 5. Lopend werk en verificatie

- **Decision-trail memory (taken 2–6) loopt door** — de leerstaat is het eerste bewijsstuk van het verhaal (lagen 7 en 12); dit ontwerp onderbreekt niets.
- **Verificatie** (docs-only werk): elke evidence-claim in de gap-analyse wijst naar een bestaand bestand; zelfreview op placeholders, consistentie en scope; commits conform repo-stijl (`docs(…): …`, Nederlands).

## Volgorde van uitvoering

1. gap-analyse (incl. evidence-verificatie per laag);
2. beslissessie volgende stap (AskUserQuestion, aanbeveling klaar);
3. plan v1.2 (met uitkomst beslissessie als beslispunt);
4. uitdracht-artifacts (slides, samenvatting, demo).
