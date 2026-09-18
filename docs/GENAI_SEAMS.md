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

## What the AI actually does — four jobs shipped

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

**3. Watching the data sources** *(MVP done — 2026-09-15; DONL probes added)*

Open data changes without notice. During this build, a source quietly
shrunk from 117,012 trees to 1,000 because of a hidden server setting —
we caught it by reading the source table. The **source monitor**
periodically probes registries (ArcGIS REST **and** data.overheid.nl CKAN),
diffs feature counts / `maxRecordCount` / fields (or CKAN
`metadata_modified` + resource URLs), and drafts a change report +
registry patch proposal; **a human always merges the change** (V4). See
[`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md).

**4. Storing receipts and sharing datasets safely** *(Phase 6 done —
2026-09-15)*

All PoC inputs and outputs land in a **medallion data lake** with three
layers: **bronze** (raw snapshots as received), **silver** (normalised,
ready for software), **gold** (validated run results with receipts).
Publishing to a **European Data Space** offer is a separate, gated step:
open data may be offered automatically; restricted data requires an
explicit human approval (HITL). National open-data metadata from
[data.overheid.nl](https://data.overheid.nl) is harvested into the same
lake as DCAT catalog records — without blindly mirroring every file. See
[`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md) and
[`nldt/18-donl-harvest.md`](../nldt/18-donl-harvest.md).

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

**Done since the last edition (September 2026)**

| Track | What shipped | Doc |
|-------|--------------|-----|
| Breda what-if (S7 on PoC-4) | Value-politics variants, rank-stability | this doc §B4 |
| Source monitor | ArcGIS + DONL probes, human-merge patches | [`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md) |
| Governed agent layer (Phase 5) | One nLDT/MCP front door over all PoCs | [`nldt/12-governed-agent-layer.md`](../nldt/12-governed-agent-layer.md) |
| Data lake + Data Space (Phase 6) | Medallion lake, `lake-publish-offer`, EDC connector | [`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md) |
| DONL harvest | data.overheid.nl CKAN → DCAT lake + pilot publish | [`nldt/18-donl-harvest.md`](../nldt/18-donl-harvest.md) |

**Still open**

1. **Beleidskompas seam S9** — run annex generator exists; Word/PDF
   attachment + number-grounding on the external platform still needs the
   beleidskompas app code ([`nldt/14-beleidskompas-integration.md`](../nldt/14-beleidskompas-integration.md)).
2. **Live Data Space connector** — EDC manifests importable today; point
   `NLDT_EDC_MANAGEMENT_URL` at a real management API when deployed.
3. **eID Wallet identity (BK-3)** — mock wallet paths done; real OpenID4VP
   verifier + Keycloak OID4VCI issuance decision-gated
   ([`nldt/16-eid-wallet-identity.md`](../nldt/16-eid-wallet-identity.md)).
4. **PoC-1 seam S3** — conversational intake (S1/S2 shipped 2026-09-15:
   `--norm-analyst llm` / `--formalizer llm` on `poc/run.py`, gates + ledgers
   in `poc/pipeline/norm_llm.py`, golden-set regression
   `poc/llm/compare_norm_llm.py`; live open-model run still pending).
5. **LLM-authored change prose** for source monitor (reuse S4 number-gate
   pattern; not in MVP).

---

## Technical annex (for engineers)

Condensed reference; full detail in the code and this file's git history
(through `d0dfa17`, September 2026).

**Seam catalogue & status**

| id | seam (controlled contact point) | PoC | status |
|---|---|---|---|
| S1 | norm harvesting fan-out | 1 | **implemented** (claim/confidence refinement behind `NormAnalyst(llm_hook=…)`, `poc/pipeline/norm_llm.py`; offline-verified — live run pending) |
| S2 | formalization proposals for ambiguous norms | 1 | **implemented** (template-less cards only; zone grounding + quote-numeral grounding gates, rejection ledger; offline-verified — live run pending) |
| S3 | conversational intake | 1 | later |
| S4 | run-artifact Q&A (contract → runner → number-gated narration) | **4** (1 planned) | **live-validated** (`poc-breda/qa.py`, `qa_run.py`; `ScanQuery` schema) |
| S5 | knowledge-bank matching re-rank (swap the judge, measure delta) | 2 | designed; V3 Jaccard re-scorer in place |
| S6 | candidate-rule drafting (`voorgesteld` only; lawyer decides — MC-6) | 2 | designed |
| S7 | scenario authoring (file/auto/llm/**hybrid**; det-floor + LLM-explorer; ledger; control reproduction) | 1 · **4** | **implemented** — hybrid product default in nLDT `utrecht-scenario-author`; PoC `poc/pipeline/scenario_author.py` (`HybridScenarioAuthor`); golden-set via `poc/scenarios/compare_authors.py` (`floorIntact`); Breda parallel in `poc-breda/breda/scenarios.py` (indicator-weight variants) |
| S8 | scenario narration (numeric grounding gate) | 1 | **implemented**; live qwen3.8 run published |
| S9 | policy-document narration in an external front door (grounded-artifact contract; deterministic run annex, schema `run-annex.schema.json`) | — (beleidskompas BK-3) | **generator implemented** (`nldt/services/run_annex.py` + CLI `build-run-annex`); Word/PDF attachment + number-grounding on the foreign platform's text still open (needs beleidskompas app code) |
| SM | source monitor (ArcGIS REST + DONL CKAN continuity probes; human-merge patch) | all | **MVP done** (`services/source_monitor/`, recipe `source-monitor-run`; DONL: `donl_probe.py`, watchlist `donl-pilot`) |
| L6 | lake publish (medallion URI → ODRL offer → EDC connector; Critic V0/V2/V4) | nldt | **done** (`lake-publish-dataset`, recipe `lake-publish-offer`; `services/lake/publish.py`, `dataspace_connector.py`) |
| DONL | national CKAN harvest (data.overheid.nl → bronze + DCAT catalog; download vs DataService split) | nldt | **done** (`services/donl_harvest/`, recipes `donl-harvest-run` / `donl-harvest-publish`) |
| L-TS | cross-twin time-series silver (`timeseries-observation` + ingest wave) | nldt | **done** (`services/timeseries/`, recipe `timeseries-open-ingest`) |
| L-ES | Elasticsearch lake discovery for AI scenarios | nldt | **done** (`services/elasticsearch/`, MCP `search_lake_elasticsearch`, `data_plane` hints → S7 digest) |

**Phase path** — A: scenario contracts + sweep + critic (done) · B: the
S7/S8 seams + ledgers (done) · B2: real local open models + golden-set
regression (done, qwen3.8/3.6 via Ollama) · **S7 product mode = hybrid**:
deterministic proposals are the floor; LLM may only add novel
`(ruleId, mutation)` keys. Det remains planning-truth; LLM is explorer/tolk.
Benchmark: prefer det for coverage regressie; use LLM for extra candidates
under HITL · B3: full Q&A seam on PoC-4,
live end-to-end (done 2026-09-13) · B4: the what-if seam on PoC-4 —
value-politics variants over composition parameters, control bit-identical,
rank-stability output, file/auto/llm authors (done 2026-09-13, live with
qwen3.8 4/4 accepted after `'type'`→`'action'` alias normalization) · C:
S1/S2 (done 2026-09-15, offline-verified via `poc/tests/test_norm_llm.py`;
live qwen run open), S3 + PoC-1 decision-table Q&A + cross-track conflicts (open) · **D:
one governed nLDT/MCP agent layer over all PoCs (done 2026-09-15,
[`nldt/12-governed-agent-layer.md`](../nldt/12-governed-agent-layer.md))**
· **E: medallion data lake + Data Space publish (done 2026-09-15,
[`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md))**
· **F: source monitor MVP + DONL harvest (done 2026-09-15,
[`nldt/17-source-monitor.md`](../nldt/17-source-monitor.md),
[`nldt/18-donl-harvest.md`](../nldt/18-donl-harvest.md))**
· **G: cross-twin time-series silver + Elasticsearch scenario discovery (done 2026-09-18,
[`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md) §TS/ES)**.

**Medallion lake (Phase E/F context)** — bronze = raw snapshot (audit,
replay); silver = normalised inputs for Cook; gold = schema-valid run
artifacts + PROV. Communication: OGC Records → Cookbook → Processes read
`lake://` / `s3://` URIs; Data Space offers are a separate publish step
(never raw MinIO credentials to peers). See
[`nldt/13-data-lake-and-space.md`](../nldt/13-data-lake-and-space.md) § Lake
zones & Communication protocol.

**Key code** — `poc/pipeline/scenarios.py` · `scenario_author.py` (authors,
identity stamping, rejection ledger) · `poc-breda/breda/qa.py` (asker,
runner, number-gate, seam normalization) · `poc-breda/schemas/scan-query.schema.json` ·
`nldt/services/source_monitor/` · `nldt/services/donl_harvest/` ·
`nldt/services/lake/publish.py` · `nldt/services/adapters/dataspace_connector.py` ·
S1/S2: `poc/pipeline/norm_llm.py` + shared transport `poc/pipeline/llm_transport.py`
+ golden-set `poc/llm/compare_norm_llm.py` ·
tests: `poc/tests/test_scenario*.py`, `poc-breda/tests/test_qa.py`,
`poc/tests/test_norm_llm.py`,
`nldt/tests/test_donl_harvest.py`, `nldt/tests/test_phase6_dataspace.py`,
`nldt/tests/test_source_monitor.py`.

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

**S1/S2 lessons (PoC-1, live 2026-09-15, qwen3.8)** — S1: 24/24 claim/
confidence proposals accepted, 0 rejected, zero citation/legal-force/geo
invariant violations across the golden-set comparison
(`poc/llm/compare_norm_llm.py`, stamps in `extractedBy`). S2: the live
surface is empty for the current corpus — *every* verified card in wind/zon/
bos has a curated template, so the seam fires only for new provinces/tracks
whose evidence arrives without templates (its purpose). Observed hazard
(probe): when a card carries no geoBinding, the model obediently *substitutes*
the quote's zone with whichever zone id the allowed list offers (it "maps to
the only allowed option") — the membership gate verifies the id exists, not
that it corresponds to the quote's zone. Mitigations in depth: cards with a
geoBinding restrict proposals to their own zoneIds (preference enforced);
quote-numeral grounding still holds; V2 legal grounding + V4 HITL review the
correspondence; the prompt now always names the exact allowed set (fix, same
day). Residual risk recorded here rather than papered over.

**Data-continuity preconditions** — per-service `maxRecordCount` (fetchers
read it live from service metadata); PDOK CBS WFS ignores `cql_filter`,
has unstable `bbox`+`startIndex` ordering, honours the OGC XML `filter`;
a new CBS year can change the buurt set itself; DONL CKAN exposes
`metadata_modified` and resource URLs (not a blob store — payloads often
live at PDOK/CBS); source monitor diffs ArcGIS feature counts and DONL
catalog drift; registry patches are **never** auto-applied (V4 HITL).

**Lake / Data Space preconditions** — `accessClass` (`open` | `internal` |
`restricted`) on every inventory row; `lake-deny.json` defaults;
`restricted` publish requires `forceHitlApproved`; connector modes
`mock` | `edc-manifest` | `http` (`NLDT_DATASPACE_CONNECTOR`); live EDC
deployment out of band until `NLDT_EDC_MANAGEMENT_URL` is set.
