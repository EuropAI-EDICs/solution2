# 22 — Dual-audience spatial planning: one governed core, front doors for planners and the public

Plan for making nLDT-powered spatial planning usable **by city planners and
by the general public** without forking the truth. The approach decision
(one governed scenario core + thin per-audience front doors) was taken
2026-09-28; this chapter records it and sequences the build.

| | |
|---|---|
| Status | Approach decided 2026-09-28 (§10) · nothing audience-facing implemented yet — DA-0 is the first phase · seam **S11** registered (designed) |
| Question answered | *"AI-ondersteunde ruimtelijke ordening die zowel door city planners als door het algemene publiek gebruikt kan worden — welke aanpak?"* |
| Motivation | The [3D Cityplanner (StrateGis) blog](https://3dcityplanner.com/blog/) articulates the dual-audience ambition from the **design** side (parametric variants, instant KPIs). nLDT answers the same ambition from the **regulation** side: "where can what, under which rules, and why" — with receipts |
| Related | [01](01-vision-and-scope.md) · [05](05-agentic-ai-layer.md) · [07](07-trust-and-governance.md) (V0–V4) · [11](11-poc-patterns-scenarios-qa.md) · [12](12-governed-agent-layer.md) · [14](14-beleidskompas-integration.md) (the front-door pattern this reuses) · [16](16-eid-wallet-identity.md) (identity) · [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) B5 (contestability) · [`../ldtsolutions/REMOTE_CLUSTER.md`](../ldtsolutions/REMOTE_CLUSTER.md) (Participate deployed) |
| EuropAI EDIC home | **LDT CitiVERSE** — citizen engagement on the twin ([edic/route-citiverse-first.md](edic/route-citiverse-first.md)) |

---

## 1. What "dual audience" means here

Three audiences, three jobs — **one set of numbers**:

| Audience | Front door | Job |
|---|---|---|
| Planner / geodata professional | GIS, MCP tools, 3D viewers ([`simulation/`](simulation/)) | *author*: mutate rules, run sweeps, export annexes |
| Policy officer | Beleidskompas in GovChat-NL ([14](14-beleidskompas-integration.md)) | *weigh*: narrate runs into the policy process |
| **The public** | Chat in an existing channel + Participate | *ask · view · contest* — and later: *propose* |

For the public this means four verbs, nothing more (§5.2 maps each to an
existing seam):

1. **Ask** — "what is the state of my neighbourhood?", answered grounded
   (cite-or-abstain) or refused on record.
2. **View** — baseline vs scenario, vóór/na/Δ, in a map they already
   understand (P&V / Web3D exports).
3. **Contest** — "I disagree with this outcome" becomes a structured
   evidence record in the policy process, not a forum post.
4. **Propose** (last phase) — a citizen variant enters as a `hypothetical`
   scenario through the same S7 author seam and gates as professional ones.

**Non-goals:** no citizen parametric design tool, no free-form public map
generation, no "simplified citizen model" (§3), no own citizen portal (§10
decision 6).

## 2. Why one core — the trust argument

If the citizen sees different numbers than the planner, the system is dead
on arrival — legally and socially. So the dual audience is solved with
**graduated narration over one deterministic core**, never with a second
engine. This is the existing doctrine, extended one audience further:

> LLMs propose · engines dispose · humans decide (leitmotiv)
> Beleidskompas narrates · nLDT computes · the civil servant decides ([14](14-beleidskompas-integration.md) §3)

The professional already gets NormCards, decision tables and PROV; the
public gets plain Dutch through the **same gates** (`breda-scan-qa`'s
cite-or-abstain + number gate, S8's `check_narrative_grounding`). An answer
without grounding is a refusal — for both audiences alike.

The second leg is the App Store thesis from the Q3 2026 report: *modular
apps exchanged in existing front doors*. The public does not come to a
government portal for spatial planning; nLDT capabilities must mount into
channels citizens already use. BK-1 proved the pattern for civil servants
(MCP-mounted tools behind a foreign chat platform); DA-1 repeats it for
citizens.

## 3. Integration principle

> **One core computes · each audience gets a lens · the wallet proves who
asks · the ledger records who decided.**

Consequences:

- Narration may differ per audience; **numbers, jobId and citations never do**.
- Capability differences are `trustPolicy` data (which tools an actor may
  see/run), not UI promises — the same mechanism that already gates
  `riskLevel: high` recipes behind HITL.
- Agents acting for a citizen are capability-scoped principals under the
  ch. 16 wallet track — accountable, revocable, and recorded in PROV.

## 4. Options considered

| Option | Description | Verdict |
|---|---|---|
| **A — One universal app for both audiences** | 3D Cityplanner-style tool exposed to everyone: parametric editing for pros, simplified mode for citizens | ❌ Too complex for the public, too shallow for professionals, and a single trust bottleneck; also contradicts the front-door thesis |
| **B — Two parallel products** | A pro stack and a separate citizen portal, each with its own engines/simplifications | ❌ Number drift between the two, double maintenance, legally indefensible when versions diverge |
| **C — One governed core + thin per-audience front doors** | Existing engines stay the single source of truth; audiences are roles reaching it through hired channels (chat, beleidskompas, Participate) with `trustPolicy`-scoped capabilities | ✅ **Recommended** — reuses engines, gates, identity and the BK-1 mounting pattern; adds only narration + intake at the edges |
| **D — Wait for the national App Store + NL Wallet** | Build nothing until the 2028 App Store and the NL wallet (early 2027) exist | ⚠️ Absorbed by C: the pluggable verifier ([16](16-eid-wallet-identity.md) option C) and the MCP seams make nLDT front-door-agnostic now; waiting forfeits the testbed's early-RP position |

**Recommendation:** C, with D's timing handled by the pluggable seams
(mock verifier now, protocol-truth when the NL wallet lands).

## 5. Target architecture

```text
 Citizens (existing channels)              Professionals
 ┌──────────────────────────┐   ┌──────────────────────────────┐
 │ Chat front door          │   │ Beleidskompas (GovChat-NL)   │
 │ (municipal site, widget) │   │ GIS / MCP clients · 3D tools │
 └───────────┬──────────────┘   └───────────────┬──────────────┘
             │ ask · view       (author · weigh)│
 ┌───────────▼──────────────────────────────────▼──────────────┐
 │ Auth edge :8087/:8088 — wallet (LoA) / Keycloak (service)    │
 │ → capability token (registry ∩ granted) · trustPolicy gates  │
 ├─────────────────────────────────────────────────────────────┤
 │ One nLDT/MCP layer :8090–8093 — tools scoped per audience:   │
 │   public: breda-scan-qa · peil-whatif-read · narrator(S8)    │
 │   pro:   scenario-author(S7) · sweep · catalog · lake …      │
 ├─────────────────────────────────────────────────────────────┤
 │ Deterministic engines (PoC-1 Utrecht · Breda · Rijnland …)   │
 │ every run: jobId · ValidationReport · PROV · run annex       │
 └───────┬───────────────────────────────────────────┬─────────┘
         │ P&V dataLayer + Web3D :8084 (shared maps) │ evidence records
 ┌───────▼────────────────────────────┐   ┌──────────▼──────────────────┐
 │ Play & Visualise / Web3D exports   │   │ Participate (Decidim, k3s)  │
 │ — the public lens on scenarios     │   │ contestation → policy step  │
 └────────────────────────────────────┘   └─────────────────────────────┘
```

### 5.1 Audience × capability matrix

| Capability | Public | Policy officer | Planner |
|---|---|---|---|
| Ask grounded questions (S4 pattern) | ✅ | ✅ | ✅ |
| View scenarios / what-if maps | ✅ | ✅ | ✅ |
| Contest an outcome (Participate → evidence) | ✅ (wallet-verified) | ✅ | ✅ |
| Author a scenario (S7) | ⛔ until DA-4, `hypothetical` only | via beleidskompas steps | ✅ (all bases) |
| Mutate FormalRules / publish layers | ⛔ | ⛔ | ✅ (HITL at `riskLevel: high`) |

### 5.2 Public intent → existing capability

| Public intent | nLDT capability | Existing asset (used unchanged) |
|---|---|---|
| "Wat is de stand in mijn wijk?" | Five-value scan Q&A | `breda-scan-qa` → `breda-scan-query` (S4: cite-or-abstain + number gate) |
| "Wat als de waterstand +10 cm staat?" | Read-only what-if | `rijnland-peil-whatif` + S8 narrator; multi-scenario map payload already builds vóór/na/Δ |
| "Waar mag X eigenlijk?" | Opportunity-map Q&A | PoC-1 artifacts + decision tables (`spatial-overlay-analysis`, `utrecht-opportunity-map`) |
| "Hier ben ik het niet mee eens" | Contestation intake (S11) | Participate thread ↔ jobId → evidence record → beleidskompas annex |
| "Doe eens mijn variant" (DA-4) | Scenario authoring, `hypothetical` basis | S7 `HybridScenarioAuthor` + proposal ledger + HITL review |

Contracts stay as-is: [`poc-breda/schemas/scan-query.schema.json`](../poc-breda/schemas/scan-query.schema.json)-class
Q&A, [`schemas/validation-report.schema.json`](schemas/validation-report.schema.json),
[`schemas/run-annex.schema.json`](schemas/run-annex.schema.json),
[`schemas/web3d-context.schema.json`](schemas/web3d-context.schema.json),
twin-instance `trustPolicy`.

## 6. Governance extension — seam S11

One new controlled contact point in the
[seam catalogue](../docs/GENAI_SEAMS.md) (S1–S10 exist):

> **S11 — public narration + contestation intake.** Plain-language Q&A and
> scenario explanation for the public, **inside** the nLDT trust boundary:
> narration runs behind the existing number-grounding gates (unlike S9,
> where a foreign platform narrates and governance moves to the contract).
> What crosses the boundary is the grounded answer plus its receipts
> (jobId, citations, ValidationReport) — or a recorded refusal. The intake
> direction turns a public reaction into a **structured evidence record**
> linked to the jobId it contests, consumed by the beleidskompas policy
> step and the run annex.

Known divergence to record honestly: public-facing narration heightens the
obligations the professional track can still postpone — DPIA before any
public pilot, plain-Dutch (B1-level) and WCAG-compliant embedding, and a
cost/abuse posture for open LLM endpoints (§7–9).

## 7. Identity, deployment and abuse posture

- **Ask/view: pseudonymous, no account.** No identity needed; abuse
  controlled by rate limits, question-type caching and the public refusal
  ledger. Data minimisation by construction.
- **Contest: wallet-verified.** Extends [16](16-eid-wallet-identity.md):
  minimum LoA (+ optionally a residency attestation via selective
  disclosure) so contestation is attributable without identity proliferation.
- **Author (DA-4): delegated or verified**, always HITL-reviewed before
  publication; every proposal lands in the ledger, accepted or not.
- **Auth is a precondition, not a phase deliverable:** BK-1 shipped bearer
  enforcement on the services and MCP-over-HTTP; DA-0 re-verifies the
  posture specifically for public exposure (read-surface inventory, no
  AOI uploads, per-tool rate limits).
- **Local open models for public narration** (qwen via Ollama — the S8
  precedent). If a hosting front door routes to cloud models, the S9
  grounded-artifact contract applies and the divergence goes in the DPIA.

## 8. Phased plan

### DA-0 — Public-exposure posture audit (days)

- Re-verify bearer enforcement on `:8082–8085` and MCP `:8090–8093` from an
  unauthenticated vantage point; inventory the tool surface a public token
  may reach (ask/view only); add per-tool rate limits and a cost ceiling
  for narration calls.

**Done when:** an unauthenticated caller reaches nothing, and a
public-scoped token reaches exactly the §5.1 ask/view row — verified by a
test in [`tests/`](tests/).

### DA-1 — Citizen Q&A front door (1–2 sprints)

- Mount the nLDT MCP servers behind a chat front door in an existing
  channel (BK-1 pattern; engine-agnostic per decision 6 of [14](14-beleidskompas-integration.md)).
- Expose only S4-class tools + the S8 narrator behind the existing gates;
  answers carry jobId and citations, or are recorded refusals.
- Plain-Dutch prompt register for S11 narration; DPIA draft started.

**Done when:** a citizen question in the front door returns a grounded
answer (jobId + citations, ValidationReport `pass`) or a refusal from the
ledger — zero ungated numbers, zero stored personal data.

### DA-2 — What-if viewing (1 sprint)

- Publish baseline + scenarios via the P&V adapter
  ([`services/adapters/play_visualise.py`](services/adapters/play_visualise.py),
  dataLayer type `SCENARIO`) and Web3D exports (:8084); embed a scenario
  switcher in the front door (productise the
  [`simulation/rijnland-whatif-demo.html`](simulation/rijnland-whatif-demo.html)
  pattern: one jobId family, vóór/na/Δ recolour).

**Done when:** a citizen can compare baseline vs scenario for their area
and every number on screen traces to one replayable jobId family.

### DA-3 — Contestation loop on Participate (1–2 sprints)

- Scenario publication creates a Participate thread (Decidim — already
  deployed on the testbed cluster); reactions import as structured
  evidence records linked to the contested jobId; the beleidskompas policy
  step and run annex surface them. This closes **B5/V4 citizen
  contestability** from [`MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md).

**Done when:** a wallet-verified contestation entered in Participate
appears as a traceable evidence record in the policy-document annex — and
the "you said, we did" link back is part of the published thread.

### DA-4 — Citizen-authored scenarios (later; gate on DA-1–3 evidence)

- Open S7 to the public: `hypothetical` basis only, `HybridScenarioAuthor`
  with the deterministic floor intact, everything into the proposal
  ledger, HITL review before any publication; scenarios are labelled
  explicitly as **not legally grounded**.

**Done when:** a citizen proposal survives review, runs as a what-if next
to the official variants, and rejected proposals remain visible in the
ledger with reasons.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Participation-washing — reactions vanish into a forum | Trust collapse; worse than no participation | DA-3 makes evidence records first-class artefacts (jobId-linked, annex-visible); the "you said, we did" loop is a done-when, not a nice-to-have |
| Public chat misused for disinformation | Ungrounded "the AI says" claims | Cite-or-abstain everywhere; no free-form generation; public refusal ledger; numbers always engine-computed |
| Load/cost of an open narration endpoint | Denial-of-wallet | Local open models, question-type caching, rate limits + ceiling (DA-0) |
| Cloud models in a hosting front door vs local doctrine | Doctrinal drift in the narration layer | S9 grounded-artifact contract; divergence in the DPIA ([14](14-beleidskompas-integration.md) §9 precedent) |
| "Simplified citizen model" creep | Number drift — the fatal flaw this chapter exists to prevent | §3 principle is a hard rule: narration differs, numbers never; matrix in §5.1 |
| Beleidskompas app code still absent | DA-3 annex-side wiring waits on it | S11 does not depend on beleidskompas: nLDT-side narration and evidence records work standalone |
| Legal misreading of citizen scenarios | "The twin approved my plan" | DA-4 labels every public scenario `hypothetical`/non-binding; publication only after HITL review |
| Accessibility and language | Audience excluded in practice | Plain Dutch (B1) + WCAG for embedded viewers as DA-1 acceptance criteria |

## 10. Decisions (2026-09-28)

| # | Decision | Choice |
|---|---|---|
| 1 | Architecture | **Option C** — one governed core + thin per-audience front doors; A and B rejected (§4) |
| 2 | Public capability order | **ask → view → contest → propose** (DA-1…4); authoring is last and permanently `hypothetical`-only |
| 3 | Contestation channel | **EU LDT Participate** (Decidim, already deployed) — no custom forum |
| 4 | Public identity | **Pseudonymous by default**; wallet LoA (+ selective disclosure) only for contestation; extends [16](16-eid-wallet-identity.md) |
| 5 | Narration vs numbers | **No separate citizen model, ever** — plain language behind the same gates (S4/S8) |
| 6 | Channel strategy | **No own citizen portal** — mount into existing front doors (App Store thesis, [14](14-beleidskompas-integration.md) pattern) |
| 7 | Seam registration | **S11** (public narration + contestation intake) added to the catalogue as *designed* |

## 11. References

- 3D Cityplanner blog (StrateGis) — the design-side articulation of the
  dual-audience ambition this chapter answers from the regulation side:
  <https://3dcityplanner.com/blog/>
- Front-door pattern and options style: [14-beleidskompas-integration.md](14-beleidskompas-integration.md)
- Identity: [16-eid-wallet-identity.md](16-eid-wallet-identity.md) ·
  Trust: [07-trust-and-governance.md](07-trust-and-governance.md) ·
  Contestability origin: [`../MULTI_AGENT_PLAN.md`](../MULTI_AGENT_PLAN.md) B5 ·
  Participate deployment: [`../ldtsolutions/REMOTE_CLUSTER.md`](../ldtsolutions/REMOTE_CLUSTER.md) ·
  Seams: [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md)
