# Where AI may help in spatial planning — and where it must never decide

*Written for non-technical readers: elected officials, policy makers,
programme teams. Engineers: the condensed technical reference is in the
annex at the bottom; the full technical edition of this document lives in
git history (up to commit `ae6a5d4`).*

This document explains how our four proofs-of-concept (Utrecht, Eindhoven,
Rijnland, **Breda**) let language models help with spatial-planning work —
without ever letting them make the decision.

---

## The one rule

> **AI proposes. The pipeline disposes. A human decides.**

A language model is excellent at reading, writing, summarising and
suggesting. It is not a source of truth: it can sound confident about
something that is not there. So in everything we built, the model has the
role of an *assistant that hands in written proposals* — and deterministic
software, plus ultimately a person, decides what happens with them.

Think of a highly eager intern with a perfect memory and no sense of
responsibility. You want that intern researching and drafting. You never
want them signing.

---

## Five natural worries — and the five answers built into the toolbox

| The worry | What we built |
|---|---|
| *"The AI will just make things up."* | Every claim must carry a verifiable source — a legal article quoted word for word, an official statistic. No source? Then the system **refuses** (we call it *cite-or-abstain*), and the refusal itself is recorded, so nothing is silently guessed. |
| *"It will quietly change things."* | The model cannot touch data, rules or maps. It can only hand in proposals on a **fixed form** (a strict digital contract). Anything off-form is automatically rejected and filed. |
| *"Who checks the result?"* | An automatic checker validates every step; an independent re-run must reproduce the same answer; and the final word always rests with **a human** — a lawyer, an official. That last checkpoint is never skipped, by design. |
| *"Can we still verify this in two years?"* | Every number keeps its **receipt**: which source, fetched when, checked by whom, in which version. Every result can be re-played from disk, offline. |
| *"Are we making ourselves dependent on Big Tech?"* | The models run **locally** (open models, no cloud vendor), the data is 100% public (CBS, PDOK, the municipality's own open data), and no API key is needed anywhere. |

---

## What the AI actually does — three jobs, one pending

**1. Answering questions in plain language** *(working — demonstrated live
in Breda, 13 September 2026)*

> *"Why does Belcrum score low on spatial value?"*

The model translates the question into a strictly formatted query. Our
software — not the model — looks up the answer in the official scan. The
model then phrases the answer, and a **number-check** verifies that every
figure in its text literally occurs in the data. If one number does not
match, the answer is refused and replaced by the plain automatic version.
Residents and officials get answers in ordinary Dutch (or English), with
sources — and the system says so openly when the data simply isn't there.

**2. Proposing what-if scenarios** *(working — province of Utrecht)*

> *"What if the silence-area rule were interpreted strictly province-wide?"*

The model proposes policy variants a policy maker would realistically
weigh. Deterministic software then calculates the consequences — in square
kilometres, on the map — and the proposal must always declare what it is
based on: a **real legal rule being varied**, a **documented policy
choice being flipped**, or a **pure hypothesis** (no legal basis claimed,
and it says so). Real example from Utrecht: one discretionary clause, read
differently, moves the wind opportunity zone by **322 km² (+37.5%)**. That
is a fact a council needs before deciding — not after.

**3. Watching the data sources** *(MVP done — 2026-09-15)*

Open data changes without notice. During this build, a source quietly
shrunk from 117,012 trees to 1,000 because of a hidden server setting —
we caught it by reading the source table. The **source monitor**
periodically probes registries (ArcGIS REST), diffs feature counts /
`maxRecordCount` / fields, and drafts a change report + registry patch
proposal; **a human always merges the change** (V4). See
[`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md).
---

## What the AI never does

- It never **calculates** scores or areas.
- It never issues a **verdict** on whether a result passes.
- It never **changes** rules, corpora, maps or its own instructions.
- It never takes the **final decision** — that stays with a named human.
- It never works **unlogged**: every proposal records which model, which
  prompt version, which moment.

---

## The safety valves, in one paragraph each

**The contract.** Every model output must arrive on a fixed digital form
(a schema). Like a form at a counter: fill it in properly or it goes back.
This one rule blocks most chaos before it starts.

**The gate.** Behind the counter sits an automatic check: does every
quoted source really exist? Does every identifier occur in our data? Is
every number in the story literally in the result? Anything failing goes
to the **rejection ledger** — a public list of refused proposals, with
reasons. Refusals are results, not failures to hide.

**The control re-run.** Before any variant is believed, the software
re-executes the unchanged original and must get exactly the known answer
back. Only then are new numbers trusted.

**The receipt trail.** Every number in every report traces to a source
with a date; every result file carries a checksum. Re-playable in two
years, offline, by anyone. When wallet mode is on, "checked by whom"
becomes concrete: executor and approver identity are wallet-anchored —
the job record carries the wallet-verified executor claims and, where a
human approved the run, the approver's claims too (see
[nldt/16-eid-wallet-identity.md](../nldt/16-eid-wallet-identity.md));
which executions are allowed is decided by trust-policy gates, not UI
promises.

---

## Lessons we learned the hard way (plain words)

1. **The checker was wrong, not the AI.** Our first live-validated answer
   was rejected for "three fabricated numbers". Investigation: the model
   had copied everything correctly; our own checking routine truncated
   decimals, ignored part of the data, and didn't understand Dutch
   thousands separators ("4.245" = four thousand). Lesson: **test the
   examiner before you trust its verdicts.** Every fix became a permanent
   automatic test.
2. **Refusing is a feature.** When a question doesn't fit what the data
   can answer, both the human-made parser and the AI refuse — in the same
   public log, with a reason. We also had to teach the AI *when not to
   refuse*: "why"-questions are exactly the questions it should answer.
3. **Models reshape the form.** They fill in a neighbourhood name where a
   category belongs, add fields, reformat numbers. Predictable repairs are
   done automatically — strictly by our software, never by guessing — and
   everything else is rejected.
4. **The question itself is stamped by our software.** The AI may not
   rephrase or replace the question it is answering — the record always
   shows the question that was actually asked.

---

## What's next

1. **The what-if seam for the Breda five-value scan** — *working since
   13 September 2026*: the proven pattern applied to value politics. First
   findings: the access threshold (4→6 of 6 services) changes *nothing*
   (the indicator is robust — CBS supplies all six distances everywhere);
   wijkdeals as a hard democratic floor shifts all 56 neighbourhoods;
   doubling green or dropping the trees counter each shift 52. The
   rank-stability output shows which neighbourhoods stay top/bottom across
   every weighting — the robust answer a council can build on.
2. **The source monitor** — continuity of open data as a monitored process
   — ***done (MVP)*** · [`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md).
3. **One governed agent layer** over all four PoCs, so the same rules
   apply everywhere (the nldt/MCP architecture) — ***done*** (Phase 5,
   2026-09-15). Processes, recipes, MCP (`nldt-poc-mcp`), uniform
   Critic/HITL/PROV, and Eindhoven/Rijnland registration: see
   [`nldt/12-governed-agent-layer.md`](../nldt/12-governed-agent-layer.md).

---

## Technical annex (for engineers)

Condensed reference; full detail in the code and this file's git history
(through `ae6a5d4`).

**Seam catalogue & status**

| id | seam (controlled contact point) | PoC | status |
|---|---|---|---|
| S1 | norm harvesting fan-out | 1 | later (deterministic base done) |
| S2 | formalization proposals for ambiguous norms | 1 | later |
| S3 | conversational intake | 1 | later |
| S4 | run-artifact Q&A (contract → runner → number-gated narration) | **4** (1 planned) | **live-validated** (`poc-breda/qa.py`, `qa_run.py`; `ScanQuery` schema) |
| S5 | knowledge-bank matching re-rank (swap the judge, measure delta) | 2 | designed; V3 Jaccard re-scorer in place |
| S6 | candidate-rule drafting (`voorgesteld` only; lawyer decides — MC-6) | 2 | designed |
| S7 | scenario authoring (file/auto/llm; ledger; control reproduction) | 1 · **4** | **implemented on both** (`poc/pipeline/scenario_author.py`; `poc-breda/breda/scenarios.py` — indicator-weight variants over `indicators.DEFAULT_PARAMS`, bit-identical control) |
| S8 | scenario narration (numeric grounding gate) | 1 | **implemented**; live qwen3.8 run published |
| S9 | policy-document narration in an external front door (grounded-artifact contract; deterministic run annex, schema `run-annex.schema.json`) | — (beleidskompas BK-3) | **generator implemented** (`nldt/services/run_annex.py` + CLI `build-run-annex`); Word/PDF attachment + number-grounding on the foreign platform's text still open (needs beleidskompas app code) |

**Phase path** — A: scenario contracts + sweep + critic (done) · B: the
S7/S8 seams + ledgers (done) · B2: real local open models + golden-set
regression (done, qwen3.8/3.6 via Ollama) · B3: full Q&A seam on PoC-4,
live end-to-end (done 2026-09-13) · B4: the what-if seam on PoC-4 —
value-politics variants over composition parameters, control bit-identical,
rank-stability output, file/auto/llm authors (done 2026-09-13, live with
qwen3.8 4/4 accepted after `'type'`→`'action'` alias normalization) · C:
S1/S2/S3, PoC-1 decision-table Q&A, cross-track conflicts, source monitor
(later) · **D: one governed nLDT/MCP agent layer over all PoCs
([`nldt/12-governed-agent-layer.md`](../nldt/12-governed-agent-layer.md) —
open)**.

**Key code** — `poc/pipeline/scenarios.py` · `scenario_author.py` (authors,
identity stamping, rejection ledger) · `poc-breda/breda/qa.py` (asker,
runner, number-gate, seam normalization) · `poc-breda/schemas/scan-query.schema.json` ·
tests: `poc/tests/test_scenario*.py` (45), `poc-breda/tests/test_qa.py` (25).

**B2 lessons (PoC-1, live)** — thinking-mode must be disabled via the
native Ollama transport; benign shape drift is normalized deterministically;
the gate catches real drift (hallucinated ids, exact-float mismatches,
verdict assertions); narrate only after the final verdict exists; number
matching folds sign (and, since B3, format).

**B3 lessons (PoC-4, live)** — gate-collection bugs precede model blame
(`:g` precision, dict keys, thousands separators); letter-boundary token
extraction; deterministic templates gate-clean by construction (no
boilerplate digits, no list markers); seam stamps question + identity;
abstention calibrated via a worked query taxonomy; parser and LLM abstain
symmetrically into one ledger.

**Data-continuity preconditions** — per-service `maxRecordCount` (fetchers
read it live from service metadata); PDOK CBS WFS ignores `cql_filter`,
has unstable `bbox`+`startIndex` ordering, honours the OGC XML `filter`;
a new CBS year can change the buurt set itself.
