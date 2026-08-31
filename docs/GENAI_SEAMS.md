# GenAI Seams — adding LLMs to the deterministic PoCs

**Design rule (inherited from the PoCs, restated):** *LLMs propose, deterministic
engines dispose.* Both PoCs run with no LLM at runtime by construction; the only
sanctioned contact surface is the `llm_hook` seam
(`poc/pipeline/agents.py`, `NormAnalyst(llm_hook=...)`) — "the interface is the
only seam where a model may later *propose*, never *decide*" (`docs/SOLUTIONS_ARCHITECTURE.md`).
This document catalogues every seam where GenAI can be added without giving up
the properties that make the toolbox trustworthy: cite-or-abstain, schema-validated
agent boundaries, V0–V4 validation, PROV on every artifact.

Related: [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) (target multi-agent
architecture), [`../docs/SOLUTIONS_ARCHITECTURE.md`](SOLUTIONS_ARCHITECTURE.md)
(module boundaries, validation levels).

---

## 1. The seam catalogue

Every seam has the same shape:

```
LLM  ──(schema-validated JSON proposal)──▶  deterministic gate  ──▶  engine/critic/human
        temperature 0, structured output      cite-or-abstain /           decides
        PROV: model+prompt+version            schema + grounding
```

| # | seam | PoC | today (deterministic) | GenAI role (proposal only) | gate that stays deterministic |
|---|---|---|---|---|---|
| S1 | Norm harvesting | 1 | curated `poc/corpus/evidence-*.json` shards (~24 cards/track) | fan-out Norm-Card proposals over the *full* CVDR instrument text — the answer to paper A1's known failure ("could not derive the comprehensive set of norms from hundreds of documents") | V2 quote-entailment: every claim must carry a verbatim quote that string-matches the archived instrument; else → abstention ledger |
| S2 | Norm formalization | 1 | `TEMPLATE_SPECS`; 13 ambiguous wind rules → V4, never guessed | propose formalizations (parameter/operator/distance/zoneSemantics) for ambiguous cards, status always `voorgesteld` | template registry remains the only path to an executable rule; a human approves a proposal → it becomes a template |
| S3 | Conversational intake | 1 | fixed `poc/use-cases/<track>.json` | draft an `OpportunityMapRequest` from a policy question in natural language | schema validation + AOI/source resolution |
| S4 | Run-directory Q&A | 1, 2 | static reports | grounded Q&A ("why is this parcel excluded?") over decision-table rows + NormCards; cite row/card ids or abstain | the decision table itself never changes |
| S5 | Knowledgebank matching | 2 | TF-IDF cosine + published-relation boost | LLM re-ranker for the text-driven rows; MC-6 preserved — status stays `voorgesteld` regardless of who scored | V3's independent Jaccard re-scorer keeps measuring disagreement; swap the judge, measure the delta |
| S6 | New-rule drafting | 2 | `needsNewRules` clusters flagged for the jurist | draft candidate *doelregels* for the `gebruik:overig`-style clusters, `reviewTrail` per row | jurist stays on the buttons (MC-6); nothing is `gekoppeld` by AI |
| S7 | **Scenario authoring** | 1 | **implemented Phase A** (see §2) | ScenarioAuthor proposes `ScenarioSpec`s grounded in the corpus (pending amendments, discretionary clauses, abstained topics, cross-track conflicts) | mutations restricted to the engine's actual inputs; V2 basis grounding; V3 control reproduction; V4 pending |
| S8 | Scenario narration | 1 | `scenario-report.md` (deterministic table) | narrate the `ScenarioDelta`s for readers; every number cites a report row | numbers come only from the report; narration carries no new claims |

## 2. Scenario planning — the pattern (Phase A implemented)

Scenario planning is not a mutation of the pipeline; it is a **replay plane over a
canonical run**. A scenario is a *contract*, not a prompt:

```
ScenarioSpec (schema-validated contract)
   basis: baseline | norm_variance | policy_variant | hypothetical
   mutations: drop | set_semantics | set_buffer_distance_m   (per ruleId)
        │
        ▼
unmutated CONTROL re-execution  ──+──▶  per-scenario re-execution
(from the baseline run's cached    │      (poc/pipeline/scenarios.py)
 layers, same tunings, offline)    │
        │                          ▼
        │                   ScenarioReport (schema-validated):
        │                   areas, Δ vs control, IoU vs control,
        │                   mutations applied/skipped, degradations
        ▼                          ▼
V3: control must reproduce     V0–V3 ValidationReport
the baseline run (≤0.1% rel)   (validation.json; V4 pending by design)
```

### 2.1 The `basis` provenance class (the key design point)

Hypothetical parameters break cite-or-abstain: a varied buffer distance has no
legal citation, and *pretending it does* would corrupt the toolbox's core
guarantee. The `ScenarioSpec` contract therefore requires every scenario to
declare its evidential status:

| basis type | requires | meaning |
|---|---|---|
| `baseline` | — | reserved for the runner's unmutated control; may not appear in a set file |
| `norm_variance` | `normCardId` + `variedAspect` | varies a parameter of a **cited** rule (e.g. art. 9.25 lid 2's 1500 m attention buffer → 500/3000 m); the citation is real, the varied value is not the instrument's |
| `policy_variant` | `normCardId` | flips a **documented discretionary choice** (e.g. art. 6.3 lid 2 NNN exception granted province-wide; a conditional overlay read as hard exclusion) |
| `hypothetical` | `rationale` | free parameter exploration with **no legal grounding** — the honest counterpart of the abstention ledger (e.g. setback distances are an abstained topic, so a 500 m Natura 2000 setback sweep must say so) |

The V2 grounding check resolves every `normCardId` against the baseline run's
`normcards.json` and every mutation `ruleId` against its `formalrules.json`.
Unknown ids are authoring failures (verdict `fail`), not graceful skips; rules
that the baseline never executes (status `ambiguous`/`rejected`) are skipped
with a recorded reason — never guessed into execution.

### 2.2 What is implemented today (Phases A+B, deterministic by default, offline)

- Contracts: `poc/schemas/scenario-spec|scenario-set|scenario-report.schema.json`
  (+ `validation-report` extended with the scenario artifact types), dataclasses in
  `poc/pipeline/contracts.py`.
- Engine: `poc/pipeline/scenarios.py` — baseline replay from a canonical run dir
  (request + rules + manifest + cached layers + recorded tunings), mutation
  application, per-scenario re-execution through the *unmodified* zone engine,
  control reproduction check, V0–V3 critic (+ narration grounding), PROV bundle.
- Authors: `poc/pipeline/scenario_author.py` — `file` / `auto` / `llm` behind one
  interface, with the rejected-proposals ledger (§2.3).
- Narration: `deterministic_narrative` + `check_narrative_grounding` (seam S8).
- CLI: `python3 poc/scenarios/run.py [--use-case wind|zon|bos] [--author
  file|auto|llm] [--max-scenarios N] [--narrate]` →
  `poc/scenario-runs/<ts>-<track>/` (exit 0 only on verdict `pass`).
- Demo sets grounded in the canonical runs: `poc/scenarios/{wind,zon,bos}.json`.
- Tests: `poc/tests/test_scenarios.py` (25) + `poc/tests/test_scenario_author.py`
  (20), all offline incl. a real-cache e2e.

Canonical first results (baseline runs of 2026-08-30, control reproduces all
three to 0.000000 rel delta):

| track | scenario | basis | final km² | Δ vs control |
|---|---|---|---:|---:|
| wind | control | baseline | 859.463 | — |
| wind | NNN lid-2 exception province-wide | policy_variant | 1181.982 | **+322.519 (+37.5%)** |
| wind | Stiltegebied as hard exclusion | policy_variant | 716.241 | −143.221 (−16.7%) |
| wind | Aandachtsgebied as 500/1500/3000 m exclusion | norm_variance | 644.506 / 525.500 / 333.712 | −214.956 / −333.963 / −525.751 |
| wind | 500 m Natura 2000 setback | hypothetical | 812.541 | −46.922 (−5.5%) |
| zon | control | baseline | 1167.936 | — |
| zon | Groene contour as hard exclusion | policy_variant | 1145.271 | −22.665 (−1.9%) |
| zon | designation at face value (no Natura carve) | hypothetical | 1167.948 | **+0.011** — the carve is measurable but negligible |
| bos | control | baseline | 23.924 | — |
| bos | oude bosgroeiplaatsen as hard exclusion | policy_variant | 23.911 | −0.014 |
| bos | zoekgebied +1 km band | hypothetical | 395.396 | +371.471 (16.5×) |

These are exactly the kind of policy-relevant facts scenario planning exists
for: the NNN discretionary clause is the single largest lever on wind siting
(+37%), silence-area strictness is worth up to −61%, the zon Natura carve is
symbolic (+0.01 km²), and the bos zoekgebied boundary dominates everything.

### 2.3 Phase B — the seam is implemented (still no network by default)

The `ScenarioSpec` contract **is** the seam, and it now has three authors behind
one interface (`poc/pipeline/scenario_author.py`, `propose(baseline,
max_scenarios) -> (accepted, rejected_ledger)`):

| author | what it does | gate |
|---|---|---|
| `--author file` | ships the demo sets (`poc/scenarios/*.json`) | schema + V2 grounding |
| `--author auto` | `DeterministicScenarioAuthor`: derives proposals mechanically from the baseline artifacts — drop/hard-classify every executed rule, half/double every cited buffer, hypothetical 500 m setbacks for un-buffered exclusions (rationale referencing the abstention ledger); effort budget records its cuts | same |
| `--author llm` | `LLMScenarioAuthor`: builds an id-complete digest of the baseline run (formalized rules with articles + footprints, abstention topics, mutation/basis vocabulary), calls an OpenAI-compatible endpoint (`LDT_SCENARIO_LLM_ENDPOINT` / `LDT_SCENARIO_LLM_MODEL`, local open model per paper B, temperature 0), and treats the response as **proposals only** | same, *before* execution: schema-invalid items, hallucinated rule/normCard ids, duplicate ids, object-type mismatches and budget overruns land in `proposals-rejected.json` — the author's cite-or-abstain ledger — and never reach the engine |

Key trust properties of the LLM seam:

- **Identity is stamped by the seam, not the model**: `proposedBy` is always
  overwritten with `llm-proposal#<model>` (any self-claim is recorded in the
  proposal notes), so PROV cannot be spoofed through the prompt.
- **Hallucinated ids cannot fail the run** — they are ledgered, not executed;
  what does execute passes the same V0/V2 gates as every other spec.
- The deterministic author doubles as the **golden-set fixture** for the LLM
  seam: same interface, same gates, zero cost — CI regression compares
  hooked vs unhooked sweeps.

The narration seam (S8) is implemented the same way (`--narrate`):
`deterministic_narrative` renders prose whose every number is f-stringed from
the report rows, and `check_narrative_grounding` gates *any* narrator — every
numeric token in the prose must match a number in the serialized report (at the
token's own precision) and every `SC-/FR-/NC-` id must resolve. A rejected
narration fails the V2 level (`v2-narrative-grounding`) and with it the run
verdict; prose never replaces numbers. An LLM narrator plugs in through the
same `narrator=` callable and must survive the identical check.

What `--author auto` already discovered on the canonical wind baseline (beyond
the demo set's findings): a hypothetical 500 m NNN buffer would cost **−52.2%**
(`SC-FR-W-14-SETBACK500`), and hard-enforcing the NNN *conditional* overlay
(`SC-FR-W-13-HARD`) changes **nothing** (Δ +0.000, IoU 1.0) — the conditional
overlay is fully subsumed by the default NNN exclusion, a non-obvious fact
about the rule set that the sweep makes visible.

The paper-B constraint (open-source models only, transparency) applies to model
*choice*: the hook is model-agnostic, so a local vLLM/Ollama endpoint satisfies
it without touching any contract.

## 3. Guardrails that apply to every seam

- **Structured output, temperature 0** for anything feeding a gate (plan §5
  determinism rules); free-form text only *after* the numbers exist.
- **Cite-or-abstain extended, never bypassed**: proposals carry citations when
  they exist and `basis`/`rationale` declarations when they do not.
- **LLM output never mutates rules, corpora or the KG**; proposals land in
  `voorgesteld`/pending states that only humans (or deterministic gates) promote.
- **PROV per proposal**: model, version, prompt hash — the existing
  `extractedBy`/`formalizedBy`/`proposedBy` fields already anticipate this.
- **Golden-set regression in CI** on every prompt/model change (plan §4):
  GS-1 benchmark maps for PoC-1; the canonical scenario sweeps as fixtures.
- **Effort/cost budgets** on any fan-out seam (S1 especially) per the
  orchestrator spec (plan §3.2).

## 4. Phased path

| phase | content | status |
|---|---|---|
| A | scenario contracts + deterministic sweep + critic + demo sets (S7 skeleton) | **done** — `poc/pipeline/scenarios.py`, `poc/scenarios/` |
| B | the seams themselves: S7 `--author auto|llm` (proposal ledger, identity stamping, pre-execution gating) + S8 `--narrate` (numeric-grounding gate) | **done** — `poc/pipeline/scenario_author.py`, `scenarios.deterministic_narrative` / `check_narrative_grounding` |
| B2 | plug a real local open model into `--author llm` / LLM narrator; golden-set regression comparing LLM vs deterministic author outputs | next (needs an endpoint) |
| C | S1 norm-harvest fan-out, S2 formalizer proposals, S3 conversational intake, S4 run-directory RAG; cross-track conflict discovery (zon compensation vs bos zoekgebied overlap) | later |
