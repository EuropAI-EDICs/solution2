# 19 — S10 Deep Research (gebruik)

Seam **S10** laat een optionele research-harness (stub of LangChain Deep Agents)
een **`ResearchBrief`** voorstellen vóór scenario-authoring (S7).  
De brief is **propose-only**: geen scans, geen mutaties, geen eigen identity-claim.

> **AI proposes. The pipeline disposes. A human decides.**  
> S10 = research-intern; S7/engines = beslissing over wat er echt gedraaid wordt.

## Wat S10 wel en niet doet

| Wel | Niet |
|-----|------|
| Schema-gevalideerde `ResearchBrief` | Buurtscores berekenen |
| `suggestedSeriesIds` / `suggestedMutationHints` voor S7-digest | Mutaties toepassen of year-sweeps bouwen |
| Identity stempelen: `deep-research#stub` of `deep-research#deepagents` | Model laten claimen wie het is |
| Rejection ledger bij schema-fail + stub-fallback | Orchestrator / Critic vervangen |

Contract: [`schemas/research-brief.schema.json`](schemas/research-brief.schema.json)  
Code: [`agents/seams/deep_research.py`](agents/seams/deep_research.py)

## Waar S10 in de keten zit

In de Breda LangGraph-plane:

```text
deep_research (S10) → horizon_inputs → author_floor (S7) → author_llm (S7)
  → merge_and_gate → run_scenarios → pathways → assemble
```

- Zonder `--deep-research` / `enable_deep_research=false`: node is no-op (skip in what-if-sim).
- Met S10 aan: brief komt in state/`report.researchBrief`; series-hints worden aan `lake_hints` geplakt voor S7.

Bron: [`agents/breda_scenario/graph.py`](agents/breda_scenario/graph.py).

## Snel starten

### 1. Alleen stub (geen Deep Agents-package)

Voldoende voor CI, demo en what-if-pipeline-sim:

```bash
cd nldt
python -m agents.breda_scenario.run --stub --deep-research
```

Of programmatisch:

```python
from agents.seams.deep_research import propose_research_brief

brief, rejected = propose_research_brief(
    "Breda five-value horizon 2050",
    lake_series_hints=[{"seriesId": "cbs-kwb-demo"}],
    force_stub=True,
)
assert brief and brief["proposedBy"].startswith("deep-research#")
assert rejected == []
```

`force_stub=True` of `NLDT_OFFLINE=1` → altijd deterministische stub-brief.

### 2. Via Breda LangGraph (stub mode + S10)

```bash
cd nldt
python -m agents.breda_scenario.run \
  --stub \
  --deep-research \
  --research-topic "Breda heat, ageing and solar to 2050" \
  --out /tmp/breda-s10-stub
```

Output-summary bevat `hasResearchBrief: true`. Het stub-report schrijft naar `--out` als gezet.

### 3. Live dispose + S10 (poc-breda engines)

```bash
cd nldt
python -m agents.breda_scenario.run --live \
  --baseline ../poc-breda/runs/<ts>-breda-scan \
  --out ../poc-breda/scenario-runs/<ts>-breda-graph \
  --deep-research \
  --what-if
```

Vereist: scan-run met `value-scan.json`, CBS-lagen in cache.  
LLM-S7 nog steeds via bestaande env (`LDT_SCENARIO_LLM_*`) — los van S10.

### 4. Optionele Deep Agents-harness (live research)

Standaard blijft S10 op de **stub**. Voor de open research-harness:

```bash
pip install deepagents   # optioneel; staat gecommentarieerd in requirements.txt
export NLDT_DEEP_RESEARCH=1
# NLDT_OFFLINE mag niet 1 zijn

python -c "
from agents.seams.deep_research import propose_research_brief
brief, rejected = propose_research_brief('Breda 2050 value debates')
print(brief['harness'], brief['proposedBy'], len(rejected))
"
```

Gedrag:

1. Probeer `create_deep_agent` → JSON `ResearchBrief`.
2. Schema-gate faalt → ledger-entry + **loud fallback** naar stub-brief.
3. Package ontbreekt / env uit → direct stub.

Deep Agents is **geen** kern-orchestrator; alleen S10-hinter achter de gate.

## Velden in `ResearchBrief`

| Veld | Rol |
|------|-----|
| `briefId` | `RB-…` id |
| `topic` | Onderzoeksvraag |
| `findings[]` | `claim`, optioneel `sourceHint`, `confidence` 0–1 |
| `suggestedSeriesIds[]` | Lake/timeseries-ids als hint (geen fetch door S10) |
| `suggestedMutationHints[]` | `aspect` ∈ social_rule / spatial_weights / economic_weights / access_min / other + `rationale` |
| `citations[]` | Optionele bronstrings |
| `proposedBy` | **Altijd** door de seam gezet |
| `harness` | `stub` \| `deepagents` \| `offline` |

## Koppeling met S7 en what-if

- S7 LLM-author mag series/hints uit de brief gebruiken als digest-input (via `lake_hints`); de floor blijft deterministisch.
- In `scenario-report.json`: `researchBrief` (+ optioneel `researchRejected`).
- What-if-kaart: LangGraph-strook toont **S10 Research** groen als brief aanwezig; **Play pipeline** vertelt de stap.

Demo-run met brief:  
`poc-breda/scenario-runs/20260918T140500Z-breda-s7-2050/`.

## Tests

```bash
cd nldt
python -m pytest tests/test_breda_scenario_graph.py -q
```

Dekking: stub schema-pass, schema-reject → stub-fallback, graph met/zonder S10, live-pad gemockt.

## Checklist voor een “echte” S10-run

1. [ ] `--deep-research` of `enable_deep_research=True`
2. [ ] Duidelijke `--research-topic`
3. [ ] Stub OK voor demo; voor harness: `deepagents` + `NLDT_DEEP_RESEARCH=1`
4. [ ] Report bevat `researchBrief.proposedBy` met prefix `deep-research#`
5. [ ] Geen mutaties/scores uitsluitend op basis van de brief zonder S7-gate + dispose
6. [ ] What-if: Play pipeline → stap S10 controleerbaar

## Gerelateerd

- Doctrine: [`docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) (catalogus S10)
- Agent-laag: [`05-agentic-ai-layer.md`](05-agentic-ai-layer.md)
- Breda CLI: `python -m agents.breda_scenario.run --help`
