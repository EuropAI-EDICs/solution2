# Ontwerp — Utrecht-harness unificatie: deep-agents als planningvlak op de nldt-execution harness

| | |
|---|---|
| **Datum** | 6 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | één toolbron voor de deep-agents-agent (nldt MCP ipv filesystem-wrappers), live `LLMHook` voor S1/S2, één gedeeld journal-format; Utrecht eerst, patroon herbruikbaar voor de andere PoC's |
| **Buiten scope** | memory-architectuur (artikelcomponent 3), surface-adapters (Slack/Teams/…), sandbox code-execution, model routing, OTel/Langfuse + CI-evals op GS-1..3 (volgende mijlpaal, zie [`AGENTIC_STATE_PLAN.md`](../../AGENTIC_STATE_PLAN.md)) |
| **Bronnen** | [het harness-artikel](https://medium.com/data-science-collective/the-harness-is-the-product-how-agents-are-actually-built-in-2026-4b751480f60c) (Tkachuk, okt 2026: "the harness is the product") · [`docs/SOLUTIONS_ARCHITECTURE.md`](../../SOLUTIONS_ARCHITECTURE.md) · [`docs/GENAI_SEAMS.md`](../../GENAI_SEAMS.md) (S1–S11) · [`MULTI_AGENT_PLAN.md`](../../../MULTI_AGENT_PLAN.md) (twee-vlakken-architectuur) · [`nldt/12-governed-agent-layer.md`](../../../nldt/12-governed-agent-layer.md) · `deep-agents/README.md` |
| **Keuzes uit de sessie** | aanpak: **gelaagd (aanpak 1)** — deep-agents blijft het conversatieve brein, nldt blijft de execution harness; mijlpaal 1 is het MCP-contract; gates/credentials blijven harness-enforced, nooit model-chosen |

## Context en doel

De repo heeft twee agent-stacks die deels hetzelfde werk doen:

- **`deep-agents/`** — LangChain Deep Agents op lokale Ollama (`models.py`: `gemma4:31b-mlx` orchestrator, `gemma4:12b-mlx` subagenten, optioneel `zai:`-routing via Z.ai). Orchestrator fan-out via SubAgentMiddleware naar per-PoC-specialisten (`pocs.py`), met streaming journal + dashboard (`journal.py`, `live.py`, `dashboard.html`). De tools (`tools/*.py`) lezen en draaien de PoC-artefacts **rechtstreeks op het filesystem** (bv. `tools/utrecht.py` kopieert runs naar `deep-agents/runs/` en voert recepten lokaal uit; `tools/recipes.py` leest receptbestanden zelf).
- **`nldt/`** — LangGraph-orchestrator (`agents/orchestrator/graph.py`) mét gates/HITL-routing, vier MCP-servers (catalog :8090, process :8091, data :8092, poc :8093) en een process-adapter die de PoC-engines als authoritatieve eenheden aanroept (`services/process_adapter/poc_handlers.py`). De `poc_server.py` is een thin façade: 10 coarse operations + SEP-2640 `skill://`-resources.

Daarmee doen beide stacks dezelfde operaties op twee manieren — "twee hersens, één lichaam". Dit ontwerp verenigt ze volgens het harness-principe van het artikel: **het model is de motor, de harness is het product**. Concreet betekent dat hier: alleen de harness (nldt) houdt credentials, gates, goedkeuringen en provenance; het brein (deep-agents) vraagt operaties aan en voert niets zelf uit. De PoC-pipeline met V0–V4 is al de "operation layer" waar het artikel naar streeft — deze unificatie stopt de agent erachter in plaats van eromheen.

## Doelplaat — vier lagen

| Laag | Wat | Bestaat al? |
|---|---|---|
| **Surface** ("deur") | deep-agents dashboard + live streaming (`live.py`, `dashboard.html`) | ✅ |
| **Planningvlak** (brein) | deep-agents orchestrator + utrecht-subagent + specialisten (`models.py` als enige modelbron) | ✅ |
| **Operations** (MCP) | de vier nldt-servers als **enige** toolbron: catalog :8090, process :8091, data :8092, poc :8093 (operations + skills) | ✅, maar deep-agents gebruikt ze nog niet |
| **Execution harness** | OGC process-adapter → PoC-engines (authoritatief) met V0–V4-gates, HITL-verdicts, `prov.json` | ✅ |

Ontwerpregel (artikelcomponent 7, credential/policy gateway): het pad is altijd *intentie → operatie → policy → risicotier → uitvoeren of wachten*. deep-agents mag lezen en aanvragen; alles wat state verandert loopt door de process-adapter die de risicotiers afdwingt (`riskLevel: high` → `needs_human`).

## Data flow — één Utrecht-vraag

Vraag: *"Waar kan bedrijfsontwikkeling in het Landelijk gebied?"*

1. laya-router augment de vraag (`laya_router.py`, bestaand pad).
2. Orchestrator zoekt het recept: catalog-MCP :8090 → `utrecht-opportunity-map`; S1-ranking via de live `LLMHook` (mijlpaal 2) met deterministic tag-overlap als fallback.
3. Orchestrator roept de operatie aan op poc-MCP :8093 (`run_opportunity_map`); de façade stuurt door naar de process-adapter :8082, die `poc/run.py` als subprocess draait.
4. Gates draaien in de pipeline (V0–V3 in `poc/pipeline/critic.py`, V4 = pending/HITL); artefacten + `prov.json` ontstaan op de canonieke plek (`poc/runs/`), niet in een deep-agents-werkmap.
5. Resultaat + rapport stromen terug; deep-agents vat samen mét citaatverplichting (elke claim met instrument + artikel + versie + URL uit het rapport).
6. High-risk acties komen terug als **pending action**: gestructureerd approve/reject dat de gepauzeerde graph-state hervat — harness-enforced, niet model-chosen.

## Mijlpalen

### M1 — MCP-contract (eerste mijlpaal, onafhankelijk van het brein)

- Inventariseer `deep-agents/tools/*.py` tegen het MCP-aanbod; per tool: **vervangen** (MCP-breed), **verhuizen** (als lees-operatie toevoegen aan data-/poc-server), of **houdbaar** (PoC-lokale visualisatie, bv. Leaflet-rendering in `tools/utrecht.py`).
  - `list_recipes`/`get_recipe` → catalog-MCP :8090.
  - Runs en scenario's → poc-MCP :8093 (`run_opportunity_map`, `propose_scenarios`, `run_scenario_sweep`, …).
  - `inspect_geo_layer` → toevoegen als **read-only** operatie op data-server :8092; `crosscheck_formal_rule` en `get_provenance` → als read-only operaties op poc-server :8093 (die is de PoC-façade).
- Nieuw `deep-agents/mcp_client.py`: één client (langchain-mcp-adapters of dunne httpx-laag) die alle vier de servers laadt en de operations als tools aan de agent exposeert.
- De bestaande wrappers blijven tijdelijk bestaan als expliciet gemarkeerde fallback (`deprecated: harness-unificatie M2-verwijdering`), zodat werk-zoals-nu doorloopt.
- Na M1: **MCP onbereikbaar = expliciete fout in het agent-antwoord**, geen stille wrapper-fallback meer.

### M2 — llm_hook live (S1/S2)

- Implementeer `LLMHook` in `nldt/agents/orchestrator/llm_hook.py` (nu een no-op stub) met de modelconfig uit `deep-agents/models.py` als **gedeelde bron** (of die config verhuizen naar `nldt/services/common/` — beslissing in het implementatieplan; eis: één plek die beide kanten importeren).
- S1: `rank_recipes`-re-ranking; S2: `nl_to_plan_proposal`. Temperatuur 0, schema-gedwongen output, offline-gate: Ollama onbereikbaar → bestaande deterministic pads (tag-overlap-rank, receptverplicht plan).
- Rejection ledger (`norm-llm-ledger.json`-patroon) blijft de plek waar afgekeurde LLM-proposals zichtbaar zijn.

### M3 — één journal

- De process-adapter schrijft trajectories in het deep-agents journal-format (`journal.py`) — of deep-agents leest het nldt-format; keuze valt in het implementatieplan op basis van wat het minste verplaatst. Het dashboard leest één format.
- Dit is de lichte variant van artikelcomponent 12 (observability): één gedeeld trajectory-formaat, nog géén OTel/Langfuse — dat is de volgende mijlpaal samen met GS-1..3-regressie.

## Gates, fouten en HITL

- Risicotiers blijven in de harness; deep-agents kan ze niet omzeilen ( filesystem-toegang tot state-changing paden vervalt bij M1; lees-toegang tot `poc/runs/` mag voor inspectie).
- Rejection ledgers blijven het zichtbare spoor van weigeringen (cite-or-abstain-doctrine).
- Foutgedrag na M1: onbereikbare MCP-server → foutmelding mét herstelsuggestie in het agent-antwoord; onbereikbare Ollama → deterministic fallback met vermelding in het antwoord.

## Testing

- Bestaande suites blijven groen: `poc/tests/` (295 passed/1 skipped na de fase-4-fusie), `nldt/tests/` (orchestrator, critic, trust gates).
- M1: contract-test — elke door de agent aanroepbare operatie resolvet tegen een MCP-server; geen state-changing filesystem-bypass meer; read-only-uitzonderingen expliciet gewhitelist.
- M2: llm_hook-tests met stub-responses (patroon van `poc/tests/test_norm_llm.py`): deterministisch gedrag zonder netwerk, fallback-pad, schema-gedwongen output.
- M3: journal-schema-test (één format, beide bronnen schrijven validate documenten).
- Smoke-regressie: één GS-baseline-run vóór en na M2 (IoU/km²-drift = 0 — dezelfde invariante als `compare_norm_llm.py`).

## Risico's en alternatieven

- **Twee frameworks** (deepagents + langgraph) blijven bestaan; beide draaien op langchain-core, en de scheiding is functioneel (planning vs. execution) in plaats van accidenteel.
- Alternatief 2 (nldt wint, deep-agents wordt dev-lab) en alternatief 3 (alleen MCP-contract nu) zijn in de sessie overwogen en verworpen; alternatief 3 is bewust als mijlpaal 1 in dit ontwerp opgenomen.
- Modelrisico: alles blijft lokaal (Ollama) tenzij expliciet `zai:`-prefix wordt gebruikt; cloud-routing weigeren blijft default (`models.py`-doctrine).
