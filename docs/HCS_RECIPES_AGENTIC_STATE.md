# HCS-recipes × Agentic State — koppeltabel

| | |
|---|---|
| Document | `docs/HCS_RECIPES_AGENTIC_STATE.md` · v1.0 · 2026-10-09 · fase 1: The Key; fase 2 (UAM, 3-30-300, Circular, 15-minute city) vult de city-tabellen aan |
| Bronnen | [`recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf`](../recipes/01_Human_Centred_Services_Blueprint_EN_A1.pdf) · [`recipes/05_KPI-framework_per-recipe.xlsx`](../recipes/05_KPI-framework_per-recipe.xlsx) |
| Kaders | [`AGENTIC_STATE_PLAN.md`](AGENTIC_STATE_PLAN.md) v1.2 (Sitra B1–B14, vijf poorten) · [The Agentic State](https://agenticstate.org/paper.html) (12 lagen, L0–L5) |
| Scope | de conformiteitsverklaring van de HCS-recipe-PoC's: elk blueprint-element gekoppeld aan Sitra-block, poort, laag en landingsplaats in dit repo |

## 1. Blueprint-element → agentic state → landingsplaats

| Blueprint-element | Sitra-block | Poort | Whitepaper-laag | Landingsplaats |
|---|---|---|---|---|
| Life event als gedeeld niveau | B1 | — | 2 Government workflows | `nldt/recipes/thk-*.json` (`service.lifeEventCode`) |
| Vijf stappen (intake → follow-up) | B2 (−1 workflow) | — | 2 | steps in het run-artefact van `hcs-life-event-run` (`hcs-run.schema.json`) |
| Menselijke maat / handover | B8 | 3 | 2, 7 | `service.humanMeasure` + `steps[].actor`/`handover` |
| GenAI-testbank G1–G5 + personas | B8, B9 | 3, 5 | 4 Compliance | `service.genAiTestPoints`, testbank-paneel in de demo's |
| KPI-framework (baseline/target/actual) | B9 | 1, 5 | 11→n.v.t., 12 | `recipes/baselines/<id>.baseline.json` |
| Herontwerp vóór technologie ("welke stap verdwijnt") | B5 | 1 | 2 | `baselines[].disappearingStep` |
| Gedeelde betekenis: BRP, EUDI, PDC, autoritatieve bronnen | B6 | 2 | 8 Data & privacy | `steps[].prov.sources[]` |
| MijnServices + Common Ground als ingredients | B7, B11 | 4 | 9 Tech stack | `requiredProcesses`, `fixtures/common.json` |
| Recipe-formaat zelf (anatomy) | B11, B12 | 4 | 9 | `service`-blok in `nldt/schemas/recipe.schema.json` |
| Recipe-cyclus, measure & improve | B10, B13 | 5 | 12 People | `learningState[]` + leerstaat-strip in de demo's |
| EDIC adopteert plaat, format, testprotocol | B13 (steward) | — | 6 Procurement (kanaal) | `nldt/recipes/edic-asset-map.json` |

## 2. Mens-agent-grens per The Key-PoC (poort 3)

| Recipe | Stap | Actor | Overname-moment (uit The Key × PDC) |
|---|---|---|---|
| THK-08 | intake / delivery | agent → mens | Adresonderzoek bij twijfel → medewerker Burgerzaken |
| THK-08 | follow-up | agent → mens | Schuldsignaal → wijkteam sociaal domein (THK-14) |
| THK-02 | intake / delivery | agent → mens | Erkenning, buitenlandse ouder → medewerker |
| THK-24 | solution | agent → mens | Beschermd gezicht → vergunningverlener (uitgebreide procedure) |
| THK-24 | delivery | **mens** | Beoordeling en besluit altijd door de vergunningverlener (doctrine) |

## 3. Stopcondities en go/no-go (poort 5)

Per recipe in `nldt/recipes/baselines/<id>.baseline.json` — zelfde regels als de
testbank-assen (accuracy, plain language, once-only, explainability, human handover,
bias, AI Act risk class). De demo's tonen de uitslagen per persona.

## 4. Positie in het plan

Deze PoC's zijn de eerste *function-instanties* van het AGENTIC_STATE_PLAN (beslispunt
"volgende stap"): de functie als expliciet artefact (B1), baselines als first-class
artefacten (poort 1) en stopcondities in de run-reportage (poort 5) — precies de twee
nieuwe artefacten die het plan §3 noemt.
