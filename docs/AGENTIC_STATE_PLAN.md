# Agentic State Plan — van Sitra-onderzoek naar een referentie-implementatie urban planning

| | |
|---|---|
| Document | `docs/AGENTIC_STATE_PLAN.md` · v1.2 · 2026-10-07 (v1.2: whitepaper-kader als §0a — The Agentic State als vision-frame bovenop de Sitra-methode; beslispunt 7: volgende stap uit gap-analyse) |
| Specialiseert | [`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) v1.2 (algemene multi-agent spec) · [`docs/SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) v1.4 (Utrecht-pilot) · [`nldt/00-architecture.md`](../nldt/00-architecture.md) (platformlaag, Phase 0–6 done) |
| Brononderzoek | Sitra/Agentic State — *The Next Right Questions on the Path to the Agentic State* (working paper, sept 2026) · *First Moves: A Finland-Specific Assessment of Agentic AI Potential in Government* + [First Moves Dashboard](https://firstmovesinteractivedashboard.sitra.fi/) · [Sitra-artikel over de nationale mapping](https://www.sitra.fi/en/articles/a-nationwide-mapping-of-agentic-ai-readiness-in-the-finnish-public-sector-is-here-sitra-suggests-what-should-be-done-next/) |
| Doel | Een **werkbare referentie-implementatie** voor urban planning (ruimtelijke ordening, omgevingswet-domein) waarin de building blocks van het Finse onderzoek **landen conform de LDT toolbox**: dit repo als implementatiesubstraat, de EU LDT Toolbox-catalogus als alignerings- en publicatiekader ("wrap, don't rebuild") |
| Status | Plan — ter review door Marc (zie §9 beslispunten) |

---

## 0. Samenvatting

Het Finse onderzoek levert één kerninzicht: **het niveau waarop je overheidswerk herontwerpt, bepaalt of AI-adoptie tot vernieuwing leidt.** Niet de taak, niet de tool, maar de **functie** — een terugkerende activiteit met een herkenbaar resultaat (aanvraag ontvangen, compleetheid toetsen, besluit voorbereiden) die bij meerdere organisaties in vergelijkbare vorm voorkomt. Sitra stelt voor de komende 18 maanden te zien als een **begrensde leerperiode**: kies één gedeelde functie, beschrijf de baseline, herontwerp werk en data **vóór** technologie-inkoop, en toets of een herbruikbare capability over meerdere organisaties werkt — met vijf poorten als investeringsgate en een expliciete leerloop.

Dit repo heeft alle technische bouwstenen al in huis (deep-agents orchestrator met critic/PROV/artifact gates, zes PoC-engines, nldt-platform met recipes en data lake, V0–V4 validatie). Wat ontbreekt is precies wat Sitra toevoegt: het **functie-niveau** als gedeelde abstractie over de nu organisatie-specifieke PoCs heen.

**Het plan komt daarom neer op vier bewegingen:**

1. **Functiecatalogus + readyheidskaart** (NL-versie van First Moves) voor ruimtelijke-planfuncties over gemeenten/provincies/waterschappen — bepaalt *waar* agentic AI technisch+juridisch+data-matig zinvol is.
2. **Eén gedeelde functie kiezen** via de vier-vragen-toets (waarde, schaal, uitvoerbaarheid, leverbaarheid). Aanbeveling: *voorbereiden van een ruimtelijke beoordeling* (de normketen intake → normspecialist → formalizer → build → critic → explainer), geïnstalleerd voor minimaal drie organisaties die er al in het repo liggen (Utrecht, Breda, Eindhoven, Rijnland).
3. **De vijf Sitra-poorten uitsmeren over de bestaande V0–V4-validatieketen** plus twee nieuwe first-class artefacten: een `function-baseline.json` (poort 1) en stopcondities in de run-reportage (poort 5).
4. **De leerloop bouwen**: een decision trail bovenop het bestaande run-journal, en de herbruikbare capability-kern expliciet maken (wat is gedeeld, wat is organisatie-specifiek) zodat die als open specificatie (recipe/skill/MCP-server) publiceerbaar is.

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

---

## 1. Wat het Finse onderzoek levert: de building blocks

Geëxtraheerd uit het working paper, het artikel en het dashboard (de zes dashboard-dimensies zelf zitten achter een organisatie-poort; benoemd in de tekst zijn *technical readiness* en *legal readiness*, voortbouwend op het WEF/Capgemini *Making Agentic AI Work for Government*-readinessframework).

| # | Building block | Inhoud |
|---|---|---|
| B1 | **Functie als gedeeld niveau** | Terugkerende publieke activiteit met herkenbaar resultaat. Geen organisatie, geen beleidsterrein, geen taak, geen mandaat. Maakt herhaald werk zichtbaar over organisaties heen. |
| B2 | **Vijf niveaus** | +2 publiek doel · +1 portfolio · **0 functie** · −1 operationele workflow · −2 taak. Leiderschap beslist op +2/+1/0; professionals op −1; automatisering op −2. De mens-agent-grens wordt **binnen de workflow** getrokken. |
| B3 | **First Moves-readyheidskaart** | 70 functies × 109 organisaties, gescoord op zes dimensies, per score bronquotes (AI-gegenereerd, expliciet gecaveat). Startpunt, geen investeringsagenda. |
| B4 | **Vier prioriteitsvragen** | Waarde · Schaal · Uitvoerbaarheid · Leverbaarheid — met minimum-evidence per vraag. Technische haalbaarheid alleen is onvoldoende; het startpunt is waarde, niet automatiseringspotentieel. |
| B5 | **Herontwerp vóór technologie** | Volgorde: werk herontwerpen → data & verantwoordelijkheden afspreken → dan pas systemen/AI. Grootste winst kan zijn dat een stap **verdwijnt**, niet versnelt. |
| B6 | **Drie data-essenties** | Digitaal beschikbaar · uitwisselbaar · **gedeelde betekenis** (semantische interoperabiliteit). Voor de demonstrator volstaat een *governed vocabulary*: concepten, autoritatieve bron + eigenaar per gegeven, herkomstregistratie, correctieroute. |
| B7 | **Duurzaam werk, vervangbare technologie** | Stabiele interfaces rond afgesproken functie-concepten; systemen/modellen/leveranciers zijn vervangbaar zonder het publieke werk te herdefiniëren. |
| B8 | **Mens-agent-grens in het workflow** | Per materiële stap: wat mag de agent, wanneer escaleert hij, wie blijft verantwoordelijk, hoe kan een mens het resultaat begrijpen/uitdagen/corrigeren. |
| B9 | **Vijf poorten** vóór technologie een productiviteitsinvestering wordt | 1. Publieke uitkomst + weggehaald werk (baseline) · 2. Gedeelde betekenissen + autoritatieve informatie · 3. Juridische- en mensgrens · 4. Vervangbare architectuur · 5. Bewijs en stopcondities. |
| B10 | **De leerstaat** | Drie leerniveaus (operationeel → organisatorisch → institutioneel); decision trail per signaal (wat gebeurde, waarom, wat moet veranderen, wie beslist, hielp het); vier leiderschapsverantwoordelijkheden. |
| B11 | **Herbruikbare capability-kern, vier lagen** | Aparte diensten → herbruikbare kern (wat écht gemeenschappelijk is) → meerdere interoperabele applicaties/leveranciers → gedeelde publieke digitale infrastructuur (identiteit, registers, uitwisseling, semantische standaarden, notificatie/logging/security). Standaardiseer wat gemeenschappelijk is, maak variatie expliciet. |
| B12 | **GovTech-marktlogica** | Duurzaamste gedeelde asset = de **publieke definitie van het werk zelf** (open specificatie); aggregatie van vraag zonder één dominant systeem of leverancier. |
| B13 | **Governance: function steward** | Benoemde aanjager met begrensd coördinatiemandaat; participatie-overeenkomst; baseline + minimaal één end-to-end maatstaf; afspraken over kosten, variatie, leveranciertoegang en exit; bewijsreview op vooraf bepaalde beslispunten (doorgaan/wijzigen/pauzeren/stoppen/schalen). Verantwoordelijkheid blijft bij de deelnemende organisaties. |
| B14 | **18 maanden als begrensde leerperiode** | Demonstrator = toets van de propositie (helpt functie-denken betere besluiten geven?), niet het bewijs van een vooraf gekozen oplossing. |

## 2. Wat de LDT toolbox al in huis heeft

| Bestaand | Rol in de vertaalslag |
|---|---|
| `MULTI_AGENT_PLAN.md` | Algemene spec: twee planes, 12-agent roster, V0–V4-validatie, zes JSON-contracten (o.a. `OpportunityMapRequest`, `NormCard`, `FormalRule`, `ValidationReport`), fasering, EU-catalogus-alignering (§3.4 "wrap, don't rebuild"). |
| `deep-agents/` | Werkende Deep Agents-orchestrator op lokale Ollama-modellen: POC-specialisten (breda, rijnland, utrecht, crosstrack, minigim, eindhoven) + functionele specialisten (intake, normspecialist, formalizer, geospecialist, critic, explainer), artifact gates (`submit_request`/`submit_norm_cards`/`submit_formal_rule`), run-journal, live dashboard, Laya-routing. "Volledige keten"-mode = al een functie-vormige pipeline. |
| Zes PoC-engines | `poc/` (Utrecht wind/zon/bos), `poc-bp2op/` (Eindhoven bp2op, VNG-methode als method cards), `poc-rijnland/` (peilconflict), `poc-minigim/` + `poc-breda/` (gebiedschecks, five-value scan, Plane D gebiedsafweging, ZN-2 optelbaarheid) — organisatie-specifieke **instanties** van wat onder één functie-dak samen te vatten is. |
| `nldt/` platform | Recipes + OGC API Records/Processes, governed agent layer (`nldt/12`), medallion data lake + European Data Space offers (`nldt/13`), source monitor (`nldt/17`), DONL-harvest (`nldt/18`), eid-wallet-identiteit (`nldt/16`), trust & governance met cite-or-abstain en PROV (`nldt/07`). |
| Doctrine | *AI stelt voor · pijplijn beslist · mens beslist* (`docs/GENAI_SEAMS.md`) — inhoudelijk congruent met Sitra's mens-agent-grens en "agent is geen beslissende instantie". |

**Zusterasset buiten dit repo (zelfde doctrine):** het platform **Omgevingschat** (`../omgevingschat-platform-develop`, pnpm/Turborepo-monorepo) — een productrijpe chat-front-door voor gemeentelijke vakmensen met grounded, geciteerde antwoorden op locatiegebonden omgevingswet-vragen (domeintaal: Chat, Case File, Location Dossier, **Location Items mét stabiele ID's en autoritatieve bron-URL's**, Evidence Sets; Effect-TS chat-runtime; retrieval-eval-infrastructuur in `apps/benchmark-service`). De app **Beleidskompas** daar hergebruikt spatial context, retrieval, evidence en citatie van Omgevingschat voor een andere dienst — een al werkend voorbeeld van Sitra's herbruikbare capability-kern (B11) buiten de toolbox om. Het platform implementeert de functie dus op workflow-/productniveau (−1/−2) zonder de functie-laag, poorten en leerloop die dit plan toevoegt.

**Conclusie van de brugscan:** de toolbox dekt B5–B9 deels inhoudelijk al (cite-or-abstain ≈ gedeelde betekenis + herkomst; critic + PROV ≈ afdwingbare grenzen; lokale modellen + contracten ≈ vervangbaarheid). Het **functie-niveau zelf (B1–B3), de prioriterings- en poortenlogica als artefacten (B4, B9), de leerloop (B10) en de expliciete herbruikbare kern (B11–B12)** zijn de toevoegingen die dit plan landt.

## 3. Kern van de vertaalslag: Sitra building block → landing in de toolbox

| Sitra | Landing conform LDT toolbox | Nieuw/existent |
|---|---|---|
| **B1 Functie** | Functiecatalogus ruimtelijke ordening: `nldt/schemas/function-catalog.json` + dataset (functie, resultaat, workflows, deelnemende organisatietypen, wettelijke basis). Bestaande recipes (23 stuks in `nldt/recipes/`) worden hergetypeerd als **instanties** van functies. | nieuw |
| **B2 Vijf niveaus** | +2 = Omgevingsvisie/beleidsdoelen · +1 = programmahoudes (verordening-fase, RES, ZoN) · **0 = functiecatalogus** · −1 = recipes/processen (stappen, inputs/outputs) · −2 = MCP-tools/deep-agents tools. Documenteren in een nieuw `nldt/26-function-first-layer.md`. | nieuw (doc) |
| **B3 Readyheidskaart** | NL-readyheidsscan RO-functies: scoring-dataset + bronquotes per score (conform cite-or-abstain/V2-patroon) + dashboard-view in `deep-agents/live_server.py` / nldt-simulatie. Voorgestelde dimensies: technisch, juridisch (Awb/Omgevingswet-automatiseringsruimte), data-beschikbaarheid, organisatorische herhaling (aantal organisaties × volume), waarde/hefboom, leverbaarheid. | nieuw (dataset + view) |
| **B4 Vier vragen** | Selectiekader-dict in de catalogus; per kandidaat-functie een `function-case.json` met de vier antwoorden + minimum-evidence. | nieuw (schema) |
| **B5 Herontwerp eerst** | Workflow-schema per functie **vóór** modelkeuze; de bestaande seams/gates-doctrine blijft leidend. Functie-beschrijving krijgt dezelfde status als het juridisch recon-patroon (`docs/research/legal-facts.md`): eerst beschrijven, dan bouwen. | bestaand doctrine + nieuw artefact |
| **B6 Gedeelde betekenis** | Governed vocabulary per functie, uitgebouwd vanuit `NormCard`/`FormalRule`/`world-scene-spec`: concept → autoritatieve bron (BAG/BGT/CVDR/DSO/kadaster) → eigenaar → herkomstregistratie (PROV) → correctieroute. Afgestemd op de domeintaal van het Omgevingschat-platform (Location Item, Evidence Set, Case File); de vertaaltabel Location Item ↔ NormCard is een klein, hoogwaardig koppelwerkitem. | bestaat deels (schemas + PROV); vocabulary als artefact nieuw |
| **B7 Vervangbaarheid** | Al conform: modellen via `models.py` swappen (Ollama/Laya), tools achter MCP/contracten, engines per PoC vervangbaar. Vastleggen als poort-4-check in de critic. | bestaat; check nieuw |
| **B8 Mens-agent-grens** | Per workflow-stap een boundary-record (agent-mag / escaleert / verantwoordelijke / inzagie-correctie). Implementatie: `interrupt_on`-HITL in deep-agents (nu expliciet "next step" in de README; eindhoven-bp2op heeft V4 altijd pending — eerste use case). | deels nieuw (HITL) |
| **B9 Vijf poorten** | Mapping op V0–V4: poort 2 ≈ V2 (juridische grounding + authoritative sources) · poort 3 ≈ V2+V4 (wettelijke bevoegdheid + mens-grens) · poort 4 ≈ architectuur-check (nieuw critic-onderdeel) · **poort 1 ≈ nieuw artefact `function-baseline.json`** (huidige kosten/doorlooptijd/kwaliteit/fouten + welk werk verdwijnt) · **poort 5 ≈ stopcondities** als verplicht veld in run-reportage + eval-harness. | uitbreiding critic + 2 nieuwe artefacten |
| **B10 Leerstaat** | Decision trail bovenop `deep-agents/journal.py` + PROV: per materieel signaal (override, exceptie, vertraging, klacht) een gelogde vijfstappen-record. Drie leerniveaus koppelen aan `nldt/07` governance: operationeel (prompt/stap), organisatorisch (rol/workflow), institutioneel (standaard/funding/regeling). | nieuw (trail) |
| **B11 Herbruikbare kern** | Expliciet maken in de catalogus: per functie *gedeelde kern* (intake-normalisatie, norm-harvest, formalisatie, validatie, provenance, uitleg) vs *organisatie-specifiek* (instrumentversie, gebiedsdefinities, lokaal beleid). De deep-agents functionele specialisten zijn al die kern — catalogus maakt het zichtbaar en bestuurlijk. Buiten het repo geldt hetzelfde patroon: Beleidskompas hergebruikt in het Omgevingschat-platform de capabilities van dat platform voor een andere dienst. | hercodering, geen herbouw |
| **B12 Open specificatie** | Publicatievorm conform repo: recipes (JSON), skills (`nldt/skills/`), MCP-servers, schema-packs — publicatiekanaal EU LDT Marketplace (plan §3.4). Front-door-relatie conform [`nldt/14`](../nldt/14-beleidskompas-integration.md): apps (zoals Omgevingschat/Beleidskompas) consumeren nLDT-capabilities via de governed seams — recipes/MCP als instruments achter de composer van het platform, "wrap, don't rebuild" in beide richtingen. | bestaat als kanaal |
| **B13 Steward** | Repo-zijde: `nldt/CODEOWNERS`-entry + governance-paragraaf in het functie-doc. Organisatie-zijde: participatie-overeenkomst, benoemde steward, beslispuntenkalender — procesdeliverable in fase B/E (buiten code). | nieuw (proces) |
| **B14 Leerperiode** | Fasering hieronder, aansluitend op `nldt/08` "Next tracks (after Phase 6)". | fasevoorstel |

## 4. De demonstrator-functie: kandidaten en keuze

Sitra's selectiecriteria: de functie keert **sectorbreed** terug, bevat **meetbare herhaling en vertraging**, is **te scheiden van het uiteindelijke juridisch bindende besluit**, en heeft beperkte discretionaire ruimte met een duidelijke grens voor menselijk oordeel. Toetsing van de repo-kandidaten op de vier vragen (B4):

| Kandidaatfunctie | Waarde | Schaal | Uitvoerbaarheid | Leverbaarheid | Conclusie |
|---|---|---|---|---|---|
| **F1 Ruimtelijke beoordeling voorbereiden** — welke regels gelden waar, compleetheid van normenstelsel, besluit-dossier met citations (de "Volledige keten": intake → normspecialist → formalizer → build → critic → explainer) | hoog: beslist de doorlooptijd en kwaliteit van àlle ruimtelijke besluiten | hoog: elke gemeente/provincie/waterschap, elke vergunning en elk plan | hoog: volledig in repo aanwezig; te scheiden van het besluit zelf | hoog: 4 organisatie-contexten in repo + het Omgevingschat-platform als bestaande productrijpe instantie | **aanbevolen** |
| F2 Bestemmingsplan→omgevingsplan-conversie (poc-bp2op) | hoog | hoog (~340 gemeenten voor 2032-werkdruk) | middel: VNG-method cards er, V4/HITL nog open | middel: één instantie (Eindhoven) | sterk tweede instantie van dezelfde kern |
| F3 Omgevingsvergunning-aanvraag intake & compleetheidscontrole (directe Sitra-kandidaat "application intake") | hoog | hoog | middel: raakt DSO/meldingsketen, nog geen PoC | middel | politiek aantrekkelijkst, maar nieuwbouw |
| F4 Gebiedscheck/omgevingsanalyse auto-vullen (minigim) | middel-hoog | middel (gebiedsontwikkelaars + gemeenten) | hoog | hoog | goede derde instantie |
| F5 Kansanalyse "waar kan ik wat?" (PoC-1 + crosstrack) | middel (intern analysescherm) | hoog | hoog | hoog | is eigenlijk reeds een instantie van F1 |

**Aanbeveling.** Neem **F1 als de functie** in de catalogus, met F2, F4 en F5 als al-bestaande of snel toe te voegen **instanties** die aantonen dat dezelfde capability-kern (B11) verschillende diensten bedient zonder ze identiek te maken — precies Sitra's propositie. F3 is de logische tweede functie zodra de eerste demonstrator de propositie heeft bevestigd en de DSO-koppeling via nldt is gelegd. Deze keuze is een **open beslispunt** (§9): het plan is zo opgezet dat de catalogus-fase (A) de keuze opnieuw hard maakt met evidence, vóór er gebouwd wordt — conform B5.

**Bestaande instanties van F1.** In het repo: de Utrecht-keten ("Volledige keten"), crosstrack en de overige PoC-engines (F2/F4/F5 hierboven). Buiten het repo: het **Omgevingschat-platform** (`../omgevingschat-platform-develop`) — een productrijpe instantie voor de gemeentelijke kant van F1 (locatiegebonden toepasselingsvragen met citatie en provenance per Location Item). Concreet voor fase A/B: opnemen in de catalogus als instantie met hoge product- en data-maturiteit, en de retrieval-eval-infrastructuur daar (golden sets, `apps/benchmark-service`, plans 007–019) hergebruiken als baseline- en evidence-materiaal voor poort 1 en 5.

## 5. Fasering — 18 maanden begrensde leerperiode

Aansluitend op `nldt/08` (Phase 6 done) en het DSR-faserenpatroon uit `MULTI_AGENT_PLAN.md` §7. Elke fase heeft exit-criteria met expliciete doorgaan/wijzigen/pauzeren/stoppen-beslispunten (B13).

### Fase A (mnd 0–3) — Functiecatalogus & readyheidskaart
- `nldt/schemas/function-catalog.json` + eerste vulling: 10–20 RO-functies (uit de PoCs, VNG/WRO-processen, DSO-aanvraagketen), elk met vijf-niveaus-uitspraak en deelnemende organisatietypen.
- Readyheidsscoring conform B3 (dimensies + bronquotes per score; AI-gegenereerd met caveat, cite-of-laat).
- `function-case.json` per kandidaat: de vier vragen + minimum-evidence; besluit over de demonstrator-functie.
- Inventarisatie van bestaande instanties per functie, in én buiten het repo (inclusief het Omgevingschat-platform als F1-instantie voor gemeenten), met maturiteitsscore.
- Dashboard-view (readyheidskaart) in `deep-agents/dashboard.html` / nldt-simulatie.
- **Exit:** catalogus v1 bevroren; demonstrator-functie gekozen met geschreven onderbouwing.

### Fase B (mnd 2–5) — Baseline & governed vocabulary
- `function-baseline.json` voor de gekozen functie per deelnemende organisatie: volumes, doorlooptijden, fout-/aanvullingspercentages, inspanning (Sitra: "what it currently costs in effort, delay, quality and risk") + **welk werk verdwijnt/verandert** bij succes.
- Governed vocabulary (B6): conceptenlijst, autoritatieve bronnen + eigenaren, herkomst (PROV), correctieroute — uitgebreid vanuit NormCard/FormalRule-schemas en afgestemd op de domeintaal van het Omgevingschat-platform (vertaaltabel Location Item ↔ NormCard).
- Procesdeliverables: participatie-overeenkomst, benoemde function steward, beslispuntenkalender, stopcondities-contract.
- **Exit:** poort 1 en 2 doorlopen en gedocumenteerd; organiserende partijen akkoord.

### Fase C (mnd 4–8) — Workflow-herontwerp & mens-agent-grens
- Workflow-schema per instantie (−1-niveau) mét boundary-records per stap (B8); vaststellen wat gedeeld is vs. varieert.
- Implementatie van HITL-interrupts in deep-agents (`interrupt_on`); bp2op/Eindhoven als eerste volledig V4-gated instantie.
- Poort-3- en poort-4-checks in de critic (juridische bevoegdheidskaart per stap; vervangbaarheidsaudit: model-, leveranciers- en data-exit).
- **Exit:** vijf poorten formeel doorlopen vóór verdere technologie-investering; herontworpen workflows vastgelegd als recipes.

### Fase D (mnd 6–12) — Demonstrator over ≥3 organisaties
- Runs via nldt-recipes met artifact gates aan; PROV/journal volledig; readyheids-/leerdata verzamelen (overrides, excepties, vertragingen, correctieverzoeken).
- Golden sets + eval-harness conform `MULTI_AGENT_PLAN.md` §4 (normrecall, citation-faithfulness, IoU waar van toepassing) — maar aangevuld met de **functionele** maatstaven uit de baseline (doorlooptijd, compleetheid, weggehaald werk).
- Bewijsreviews op de afgesproken beslispunten; stopcondities geëvalueerd en gelogd.
- **Exit:** minimaal drie organisatie-contexten draaien dezelfde kern met expliciete, gerechtvaardigde variatie; besluit doorgaan/wijzigen/stoppen met evidence.

### Fase E (mnd 10–18) — Leren, verpakken, bestuurlijke inbedding
- Decision trail (B10): **vervroegd en geland** in `nldt/services/memory/` (spec
  `docs/superpowers/specs/2026-10-07-decision-trail-memory-design.md`) — automatische observaties
  (journal-errors, HITL-verdicts, ledger-rejects, golden-drift) → durabele, schema-gedwongen
  trail-records met de drie leerniveaus; consolidatie + leerrapport via
  `python -m services.memory.consolidate` / `report`. Fase E houdt restant: menselijke
  observatie-invoer, promotieproces met de beslispuntenkalender, eerste leerrapport over de
  demonstrator.
- Herbruikbare kern publiceerbaar als open specificatie: recipes, skills, MCP-servers, schema-packs; publicatie via EU LDT Marketplace-kanaal (B12).
- Stewardship-voorstel en de 2030-vragen (mandaat, funding, standaarden, toezicht) met de verzamelde evidence als input.
- **Exit:** referentie-implementatie gedocumenteerd (nieuw `nldt/26`-doc + dit plan geüpdateet); leerpakket voor volgende functie (F3).

## 6. Repo-landingsplaatsen (samenvatting paden)

| Deliverable | Pad |
|---|---|
| Functiecatalogus + cases | `nldt/schemas/function-catalog.json` · `nldt/data/functions/` |
| Readyheidsdataset + view | `nldt/data/functions/readiness-*.json` · view in `deep-agents/dashboard.html` |
| Baseline-artefact | `nldt/schemas/function-baseline.json` · per instantie in de recipe-workspace |
| Boundary-records & poortchecks | uitbreiding `deep-agents/tools/validate.py` (critic) + `nldt/07`-extensie |
| Decision trail | uitbreiding `deep-agents/journal.py` + `nldt/agents/orchestrator/nodes/` |
| HITL-interrupts | `deep-agents/agent.py` / live-runner (`interrupt_on`) |
| Architectuurdocument | `nldt/26-function-first-layer.md` (nummer aan te passen aan stand) |
| Plan-document | dit document (`docs/AGENTIC_STATE_PLAN.md`) |
| Bestuurlijke demo | [`nldt/simulation/agentic-state-demo.html`](../nldt/simulation/agentic-state-demo.html) — tien scènes (NL) met gesimuleerde run door de referentieketen en de PoC's als instanties |

## 7. Risico's & mitigaties

| Risico | Mitigatie (conform bron) |
|---|---|
| Gedeelde capability schaalt ook **falen** (één fout, overal) | Monitoring, traceerbaarheid en een veilige stop als design-onderdeel (B4.4-paper); stopcondities als verplicht run-veld; per-instantie variatie expliciet houden. |
| Technologie bepaalt alsnog het werk (poort 4 geschonden) | Poort-volgorde afdwingen: geen model-/leverancierskeuze vóór workflow + vocabulary + baseline zijn vastgelegd; critic-check op vervangbaarheid. |
| Leerloop blijft uit ("goede pilots, slecht institutioneel leren") | Decision trail als verplicht artefact; beslispuntenkalender; leerrapport is fase-exit, geen optioneel verslag. |
| Semantische drift tussen instanties | Governed vocabulary onder stewardship; wijzigingen viazelfde review als norm-wijzigingen (cite-or-abstain). |
| Model-/protocolafhankelijkheid | Bestaand beleid: lokale modellen swappen via `models.py`, MCP/A2A achter dunne adapters, contracten model-agnostisch. |
| Functiecatalogus wordt een klassificatieproject i.p.v. een middel | Sitra-waarschuwing overnemen: geen complete landelijke classificatie vóór testen; catalogus groeit met de demonstrator. |

## 8. Aannames

1. **"Conform de LDT toolbox"** betekent hier: landen in dít repo (ldttoolbox: poc's, deep-agents, nldt) én blijven aansluiten op de EU LDT Toolbox-catalogus zoals `MULTI_AGENT_PLAN.md` §3.4 dat vastlegt.
2. Het domein is het Nederlandse omgevingswet-/ruimtelijke-planpraktijk, zoals heel het repo al doet; de Finse wetsverwijzingen (Finnish Constitution, Administrative Procedure Act) vertalen naar het NL-rechtskader via een juridische recon in het bestaande `docs/research/legal-facts.md`-patroon (cite-or-abstain), niet door hier inline juridische claims te doen.
3. De zes dashboard-dimensies zijn niet publiek geëxtraheerd (toegangspoort); fase A stelt de NL-dimensies vast op basis van het WEF/Capgemini-readinessframework + het artikel (technisch/juridisch benoemd) en documenteert de afwijking.
4. Deelname van echte organisaties (gemeente/provincie/waterschap) is een procesvoorwaarde voor fase B en verder; het repo kan fase A volledig zelfstandig draaien.

## 9. Open beslispunten (voor Marc)

1. **Functiekeuze bevestigen** — F1 (aanbevolen) dan wel F3 (directe Sitra-"application intake") als eerste demonstrator; fase A levert de evidence-gestuurde herbevestiging.
2. **Deelnemende organisaties** — welke 3+ organisatie-contexten doen mee aan fase B–D (Utrecht/Breda/Eindhoven/Rijnland-assets liggen in het repo, maar echte deelname is organisatorisch).
3. **Dashboard-toegang Sitra** — indien een organisatie-account op firstmovesinteractivedashboard.sitra.fi beschikbaar is, dimensies en methodiek daaruit overnemen i.p.v. de voorgestelde afgeleide (aannames-punt 3).
4. **Scope van fase A-dataset** — zelf scannen (AI-gegenereerd + bronquotes, Sitra-stijl) of beperkt tot de PoC-bewezen functies.
5. Commit/push van dit plan achterwege gelaten (werkboom bevat lopende deep-agents-wijzigingen) — zeg het maar als ik het document apart commit.
6. **Koppelingsdiepte met het zusterplatform** — alleen catalogus- en vocabulaire-afstemming (lage drempel, fase A/B) dan wel een echte integratie (nLDT recipes/MCP als instruments achter de Omgevingschat-composer, of Omgevingschat als front-door boven de governed layer); [`nldt/14`](../nldt/14-beleidskompas-integration.md) geeft het integratiepatroon, inclusief de afweging dat de Beleidskompas-variant daar (GovChat-NL) een ander spoor is dan de eigen app in het platform.
7. **Volgende stap uit de gap-analyse** — voorgesteld op 2026-10-07: a (HITL / mens-agent-grens); onderbouwing in `AGENTIC_STATE_GAP_ANALYSE.md` §5–§6. Nog te bevestigen door Marc; start als eigen spec/plan ná afronding van de decision-trail memory.

## 10. Bronnen

- The Agentic State (primaire vision-bron): Ilves, L., Kilian, M., Parazzoli, S. M., Peixoto, T. C., Velsberg, O. (2025) — <https://agenticstate.org/paper.html>
- Sitra working paper: *The Next Right Questions on the Path to the Agentic State* — <https://www.sitra.fi/wp-content/uploads/2026/09/Sitra-%E2%80%93-The-Next-Right-Questions-on-the-Path-to-the-Agentic-State.pdf>
- Sitra-artikel: *A nationwide mapping of agentic AI readiness in the Finnish public sector* — <https://www.sitra.fi/en/articles/a-nationwide-mapping-of-agentic-ai-readiness-in-the-finnish-public-sector-is-here-sitra-suggests-what-should-be-done-next/>
- First Moves Dashboard — <https://firstmovesinteractivedashboard.sitra.fi/>
- WEF, Capgemini & GGT Centre Berlin (2026): *Making Agentic AI Work for Government: A Readiness Framework* — <https://www.weforum.org/publications/making-agentic-ai-work-for-government-a-readiness-framework/>
- Repo: [`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) · [`docs/SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md) · [`nldt/00-architecture.md`](../nldt/00-architecture.md) · [`deep-agents/README.md`](../deep-agents/README.md) · [`docs/GENAI_SEAMS.md`](GENAI_SEAMS.md)
- Zusterrepo: Omgevingschat-platform — `../omgevingschat-platform-develop` (`CONTEXT.md`, `PRODUCT.md`, `CONTEXT-MAP.md`, `plans/`) · integratiepatroon front-door op engines: [`nldt/14-beleidskompas-integration.md`](../nldt/14-beleidskompas-integration.md)
