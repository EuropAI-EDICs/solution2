# S7 Hybrid ScenarioAuthor — design

**Datum:** 2026-09-17  
**Seam:** S7 ScenarioAuthor (GENAI_SEAMS)  
**Approach:** A — deterministic floor + LLM explorer  
**Scope:** documentatie + hybrid author + nLDT-productisering

## 1. Doel & doctrine

**Doel.** S7 product-klaar maken als *propose-only* seam: deterministic golden
set als vloer, LLM als explorer voor extra coverage, nLDT-pad met
`auto|llm|hybrid`, en documentatie die doctrine plus benchmark-conclusies
vastlegt.

**Doctrine (ongewijzigd).**

- AI proposes → pipeline disposes (schema + grounding) → human decides (HITL
  op high risk).
- Seam stampt `proposedBy`; het model schrijft die identity niet.
- Geen LLM in de evaluatie-/zone-engine; alleen vóór de gate.

**Niet in scope.**

- Breda-parallel herschrijven (`poc-breda/` heeft andere S7-semantiek).
- V4 HITL-implementatie zelf.
- Lake gold write-back van scenario-uitkomsten.
- Model-tuning / prompt-engineering als apart traject.
- Eén end-to-end recipe propose→HITL→sweep (blijft process-keten; later).

## 2. Hybrid author — contract & merge

**Locatie.** `poc/pipeline/scenario_author.py`  
**Nieuwe class.** `HybridScenarioAuthor`  
**Contract (gelijk aan bestaande authors):**

```text
propose(baseline, max_scenarios) → (accepted_specs, rejected_ledger)
```

### Merge-algoritme (det-floor + LLM-explorer)

1. Draai `DeterministicScenarioAuthor.propose` met budget `max_scenarios`.
2. Draai `LLMScenarioAuthor.propose` met hetzelfde budget (intern; vóór merge).
3. **Floor:** alle accepted det-specs gaan eerst in de output (tot budget).
4. **Explorer:** LLM-specs waarvan de dedupe-key **niet** in det zit, worden
   toegevoegd tot het budget vol is.
5. **Dedupe-key:** `(ruleId, mutationKind, mutationParams-canonical)` —
   dezelfde rule met een andere mutatie mag door (echte explorer-waarde).
6. LLM-specs die det al dekt → reject-ledger met reason
   `superseded-by-deterministic`.
7. Beide reject-ledgers worden samengevoegd. Det behoudt eigen `proposedBy`;
   LLM behoudt `llm-proposal#…`.

### Fallback

| Situatie | Gedrag |
|---|---|
| Geen LLM-endpoint / transportfout in **hybrid** | Soft: hybrid = pure det; ledger note `llm-unavailable` |
| Zelfde in mode **llm** | Hard fail (configuratie vereist) |
| Schema-/grounding-reject | Zoals nu: ledger, nooit naar sweep |

### Modes

| Mode | Gedrag | Rol |
|---|---|---|
| `auto` | alleen deterministic | regressie / offline default PoC |
| `llm` | alleen LLM | experiment / compare |
| `hybrid` | floor + explorer | **product-default** in nLDT recipe |

## 3. nLDT-productisering

### Process / handler

`nldt/services/process_adapter/poc_handlers.py` —
`execute_scenario_author_propose`:

- Accepteer `author ∈ {auto, llm, hybrid}` (nu: alleen `auto`).
- Map naar PoC-classes; hergebruik `LDT_SCENARIO_LLM_*` via bestaande
  `LLMTransport`.
- `llm` zonder endpoint → duidelijke `ValueError`.
- `hybrid` zonder endpoint → soft-fallback naar det + `llm-unavailable`.

### Recipe

`nldt/recipes/utrecht-scenario-author.json`:

- Default step-input: `author: "hybrid"`.
- `riskLevel: high` blijft; HITL vóór eventuele sweep.
- Process-inputs mogen `author` overriden (niet hardcode-only).

### MCP

`nldt/services/mcp_servers/poc_tools.py` — `propose_scenarios` geeft
`author` door.

### Critic (licht op propose-stap)

`nldt/agents/orchestrator/nodes/critic.py`:

- Bestaand: heeft accepted? reject-ledger aanwezig?
- Nieuw bij hybrid: evidence dat det-floor ≥ 1 *of* expliciete note
  `all-deterministic-rejected`; tel `llmOnly`-accepted in summary.
- Geen per-spec V2/V3 hier — die blijven bij `scenario-sweep` /
  `evaluate_scenario_run`.

### CLI & compare

- `poc/scenarios/run.py`: `--author hybrid`.
- `poc/scenarios/compare_authors.py`: kolommen `both` / `detOnly` /
  `llmOnly` / `hybridAccepted`; regressie-assert **hybrid ruleId-set ⊇
  deterministic ruleId-set** (floor-invariant).

## 4. Docs, regressie & done-criteria

### Documentatie

- Deze design-spec.
- `docs/GENAI_SEAMS.md` S7: modes `auto|llm|hybrid`, det-floor doctrine,
  benchmark-conclusie (det = planning-waarheid; LLM = explorer), pointer
  naar `compare_authors`.
- Korte statusregel in `nldt/12-governed-agent-layer.md`.
- Eventueel 1–2 zinnen in `docs/SOLUTIONS_ARCHITECTURE.md` (geen herschrijf).

### Regressie

- Unit: dedupe-key, budget (det eerst), `superseded-by-deterministic`,
  `llm-unavailable` → det-only.
- `compare_authors`: floor-invariant; exit ≠ 0 bij schending.
- Smoke: nLDT handler `author=hybrid` met gemockte LLM (geen live model in CI).

### Done wanneer

1. Hybrid in PoC + CLI werkt.
2. nLDT process/recipe/MCP `hybrid` als default.
3. Docs bijgewerkt.
4. Compare/regressie groen zonder verplicht live LLM.

## 5. Kernbestanden

| Pad | Wijziging |
|---|---|
| `poc/pipeline/scenario_author.py` | `HybridScenarioAuthor` + dedupe helpers |
| `poc/scenarios/run.py` | `--author hybrid` |
| `poc/scenarios/compare_authors.py` | hybrid-kolom + floor-assert |
| `nldt/services/process_adapter/poc_handlers.py` | author modes |
| `nldt/recipes/utrecht-scenario-author.json` | default `hybrid` |
| `nldt/services/mcp_servers/poc_tools.py` | author param |
| `nldt/agents/orchestrator/nodes/critic.py` | hybrid evidence |
| `docs/GENAI_SEAMS.md` | S7 update |
| `nldt/12-governed-agent-layer.md` | statusregel |
| tests (bestaande PoC testlocatie) | unit + smoke |

## 6. Beslissingen (vastgelegd)

| # | Beslissing | Alternatief verworpen |
|---|---|---|
| D1 | Approach A: det-floor + LLM-explorer | B parallel union; C alleen fasering |
| D2 | Product-default in nLDT = `hybrid` | `auto` blijft CLI/offline default |
| D3 | Dedupe op `(ruleId, mutationKind, params)` | Alleen `ruleId` (te agressief) |
| D4 | Critic licht op propose; V0–V3 bij sweep | Volle re-validatie in author-recipe |
| D5 | Geen end-to-end propose→sweep recipe in deze iteratie | Latere orchestratie-stap |
