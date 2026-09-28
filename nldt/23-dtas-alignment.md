# 23 — DTAS alignment: nLDT as reference implementation of the Digital Twin App Store vision

The Dutch NLDT programme (Ministry of Housing and Spatial Planning, VRO) has
published **"The Dutch Vision on a European Digital Twin App Store (DTAS) —
Building a European network of local digital twins"**. This chapter records
how that vision and nLDT converge, and sequences the moves that turn the
testbed into a demonstrable DTAS reference implementation. The vision itself
names the testbed's core concept: *"Explicitly developing proven modules as
**recipes** enables other cities or regions to adopt and adapt them using
their own contextual data."*

| | |
|---|---|
| Status | Plan (2026-09-28) · alignment analysis done, five moves decided (§9); DT-0…DT-4 not started · builds on [21](21-europai-edic-handover.md) (EDIC handover) and [14](14-beleidskompas-integration.md) BK-4 (Marketplace) |
| Source | [The Dutch Vision on a European Digital Twin App Store](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=3167953) (zichtopnl.nl, 2026) |
| Programme contact | Lianne Sleebos (NLDT programme manager, VRO) · Nico Spijkers (DT Physical Environment, VRO) — per the document |
| Related | [01](01-vision-and-scope.md) · [04](04-recipes-and-processes.md) (AppStore) · [07](07-trust-and-governance.md) (V0–V4) · [13](13-data-lake-and-space.md) (Data Space) · [17](17-source-monitor.md) · [21](21-europai-edic-handover.md) · [22](22-dual-audience-spatial-planning.md) · [recipes/edic-asset-map.json](recipes/edic-asset-map.json) · [`../ldtsolutions/REMOTE_CLUSTER.md`](../ldtsolutions/REMOTE_CLUSTER.md) |
| EuropAI EDIC home | **LDT CitiVERSE** — the vision explicitly proposes the EDIC as DTAS orchestrator |

---

## 1. What DTAS asks for

The vision's diagnosis — isolated pilots, bespoke solutions, vendor lock-in,
insufficient transparency, reproducibility and legal soundness — and its
answer, in three components:

1. **An open digital infrastructure** based on European standards, aligned
   with European Data Spaces design principles ("build once, reuse many
   times over").
2. **A catalogue of validated modules** — datasets, computational models,
   visualisations — tested for quality, legal soundness and reliability.
3. **A federated ecosystem** respecting local autonomy under a "no wrong
   door" principle, orchestrated by an independent entity within
   **LDT CitiVERSE EDIC**, building on the EU LDT Toolbox, DS4SSCC,
   Citycom.ai and the EU Interoperability Framework.

Architecturally three layers: modular platform infrastructure →
infrastructure-compliant functional modules → an appstore mechanism with
**user- and expert-based accreditation** (intended to become a publicly
governed framework). Every module passes six validation criteria:

| # | DTAS criterion |
|---|---|
| 1 | Technical compatibility and reliability |
| 2 | Transparency and explainability of algorithms and underlying logic |
| 3 | Legal and ethical compliance (e.g. GDPR) |
| 4 | Reproducibility and traceability of outcomes |
| 5 | Operational management (lifecycle, maintenance) |
| 6 | User experience and feedback |

Critical modules may face peer review or independent audits; the academic
community is invited to help build the QA framework. The vision's value
story covers public authorities (validated modules, *parametric
policy-making* with harmonised parameters/indicators), companies (a
scalable European market with clear admission criteria) and **citizens**
(transparency, accessible visual information, participation).

## 2. Why nLDT already is a DTAS reference implementation in embryo

| DTAS building block | nLDT artifact (exists today) |
|---|---|
| Open infrastructure on European standards | OGC API Records/Processes + recipes + MCP as the external interface; EU LDT Toolbox as implementation (*wrap, don't rebuild*); all 11 Toolbox tools deployed on k3s ([`../ldtsolutions/REMOTE_CLUSTER.md`](../ldtsolutions/REMOTE_CLUSTER.md)) |
| Catalogue of validated modules | The AppStore ([04](04-recipes-and-processes.md)): `catalog_adapter` (OGC API Records), recipe schemas, `application` record type (BK-2), [`services/marketplace_publish.py`](services/marketplace_publish.py) |
| Validation criteria 1–5 | V0–V4 with ValidationReport + PROV ([07](07-trust-and-governance.md)); cite-or-abstain, NormCards, decision tables; golden-set regression; **bit-identical replay** + run annex — reproducibility/traceability exceeds what the vision asks |
| Federated ecosystem / no wrong door | A2A :8085; EDC Data Space connector ([13](13-data-lake-and-space.md)); external front doors mounted via MCP ([14](14-beleidskompas-integration.md), [22](22-dual-audience-spatial-planning.md)) |
| Orchestration in LDT CitiVERSE EDIC | [21-europai-edic-handover.md](21-europai-edic-handover.md) + [`recipes/edic-asset-map.json`](recipes/edic-asset-map.json): per-asset owner / relationshipOwners / acceptance / fallback / readiness — already a proto-accreditation dossier |
| Parametric policy-making | The what-if seams: rules and `DEFAULT_PARAMS` as explicit, mutable, provenance-tracked parameters (S7/S8; Breda indicator weights) |
| Citizens: transparency & participation | [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md) (S11, Participate, dual-audience front doors) |
| Cross-domain model composition (water + traffic → evacuation) | Cross-track overlay (wind × zon × bos) and the five-value scan's multi-indicator composition — partial, same direction |

Criterion 6 (user feedback) is the one validation criterion with **no
repo-side counterpart yet** — DT-3 closes it.

## 3. Integration principle

> **A recipe is a DTAS module · its receipts are the accreditation
> evidence · the EDIC asset map is the module passport · the EU LDT
> Toolbox Marketplace is the first catalogue.**

No parallel DTAS registry is created: the asset map gains DTAS criteria
fields, and the same record serves testbed governance, EDIC handover and
(accordingly) DTAS accreditation — one source, many consumers.

## 4. Options considered

| Option | Description | Verdict |
|---|---|---|
| **A — Wait for DTAS governance to settle** | Build nothing DTAS-specific until the accreditation framework and orchestrator exist | ❌ Forfeits the early-contributor position; the vision asks Member States to co-shape validation *now* |
| **B — Position as DTAS reference implementation** | Extend existing artifacts (asset map → module passport; Marketplace publication; V0–V4 as quality-framework input) so every recipe is accreditation-ready | ✅ **Recommended** — zero new infrastructure, converts existing doctrine into DTAS evidence |
| **C — Build a DTAS-specific product/channel** | A separate DTAS catalogue or portal for the testbed | ❌ Contradicts *wrap, don't rebuild* and the front-door thesis; duplicate of the Toolbox Marketplace channel |

**Recommendation:** B.

## 5. Target state — the five moves

1. **Positioning.** nLDT recipes are DTAS modules; the Q3 2026 SMART goal
   ("3+ cities exchange 3+ modular apps in existing front doors") is the
   DTAS proof target. Chapters 14 and 22 are DTAS workstreams (professional
   and citizen front doors), not side tracks.
2. **Module passport.** [`recipes/edic-asset-map.json`](recipes/edic-asset-map.json)
   gains one `dtas` block per asset with the six criteria as statuses:
   `technical` / `transparency` / `legalEthical` / `reproducibility` /
   `operations` / `userFeedback`, each `pass | partial | open` with an
   evidence pointer (ValidationReport artefact, DPIA reference, source
   monitor watchlist, feedback endpoint). Honest statuses only — a `legalEthical:
   open` is a valid, useful answer. Passports cite RA capability names from
   [edic/ra-capability-map.json](edic/ra-capability-map.json) so DTAS
   metadata and the EDIC Reference Architecture share one vocabulary
   (see [edic/ra-conformity.md](edic/ra-conformity.md)).
3. **Real Marketplace publication.** Concretise BK-4: publish 2–3 recipes
   via [`services/marketplace_publish.py`](services/marketplace_publish.py)
   to the actual EU LDT Toolbox Marketplace, payload = recipe +
   ValidationReport + PROV bundle. First genuine DTAS catalogue entries
   through the existing European channel.
4. **V0–V4 → DTAS quality framework.** Offer the validation framework as
   NL input to the emerging accreditation framework, via the [21](21-europai-edic-handover.md)
   EDIC handover (the vision: *"Through active participation in LDT
   CitiVERSE EDIC, countries can jointly shape validation frameworks,
   assessment procedures and governance structures."*).
5. **Close the two honest gaps.** (a) User-feedback loop on catalog
   records (criterion 6); (b) second-city reuse proof — beleidskompas/
   Limburg is the natural first candidate ([14](14-beleidskompas-integration.md) §8 BK-4);
   the "Rotterdam → Barcelona" story must become a recorded adoption, not
   an assertion.

## 6. Phased plan

### DT-0 — Module passport (1 sprint)

- Extend the asset map schema + seed with the `dtas` block for every
  recipe; statuses derived from existing evidence only.

**Done when:** every recipe asset carries six criterion statuses with
evidence pointers, schema-validated at seed, no criterion invented without
an artefact behind it.

### DT-1 — Marketplace publication (BK-4 concretised)

- Register/publish 2–3 flagship recipes (`spatial-overlay-analysis`,
  `breda-five-value-scan`, `rijnland-peil-whatif`) on the real EU LDT
  Toolbox Marketplace with ValidationReport + PROV payloads.

**Done when:** entries are findable in the Toolbox catalogue and a third
party can re-run the recipe from the entry alone.

### DT-2 — Quality-framework input via EDIC

- Package V0–V4 + the receipt-trail doctrine (PROV, replay, refusal
  ledgers) as the NL contribution to the DTAS validation/accreditation
  framework; submit along the [21](21-europai-edic-handover.md) handover.

**Done when:** the contribution is delivered into the EDIC DTAS working
context and its provenance (this repo, these tests) is traceable.

### DT-3 — User-feedback loop (criterion 6)

- Add feedback capture to catalog records (rating + free text, moderated),
  consumed by the passport's `userFeedback` status; beleidskompas policy
  steps and S11 contestation records are first-class feedback sources.

**Done when:** a user reaction on a catalog entry updates the passport and
is visible to the asset owner.

### DT-4 — Second-city reuse proof

- One recipe adopted by a second organisation outside the testbed
  (beleidskompas/Limburg preferred), recorded as an adoption case with
  what-was-adjusted notes.

**Done when:** the Q3 SMART goal has its first concrete data point:
module X reused by organisation Y with Z adjustments.

## 7. What is *not* solved at repo level (tracked, not built)

- **European harmonisation of policy parameters/indicators** — an EDIC/
  Member State negotiation; nLDT keeps parameters explicit and exported so
  harmonisation has something to map onto.
- **Marketplace federation / no-wrong-door governance** — depends on the
  DTAS orchestrator decision; nLDT's OGC Records + A2A surfaces are the
  federation-ready interfaces.
- **The accreditation framework itself** — publicly governed, still
  evolving per the vision; this repo supplies evidence (passports) and a
  candidate methodology (V0–V4), not the governance.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| DTAS governance still evolving ("accreditation process is still evolving") | Passport fields may diverge from the eventual framework | Keep the `dtas` block small and mapped to the vision's six criteria verbatim; version it |
| Marketplace publication requires EU-side registration/approval | DT-1 slips on external dependencies | Start registration early; mock-publisher tests continue regardless (BK pattern) |
| Overclaiming validation status | Trust damage — worse than an honest `open` | Passport statuses only from existing artefacts; `open` is a first-class answer (§5, move 2) |
| National programme priorities shift (contacts at VRO) | DTAS momentum stalls nationally | The alignment stands on standards and the EDIC handover, not on one programme's calendar |
| "Legal soundness" reads as legal certainty | Misunderstanding of what a recipe guarantees | Frame criterion 3 as GDPR/DPIA *status*, never as legal advice; beleidskompas S9 pattern applies |

## 9. Decisions (2026-09-28)

| # | Decision | Choice |
|---|---|---|
| 1 | Relation to DTAS | **Option B** — position nLDT as DTAS reference implementation; A and C rejected (§4) |
| 2 | Canon | **A recipe = a DTAS module**; no separate module concept introduced |
| 3 | Passport | **Extend [`edic-asset-map.json`](recipes/edic-asset-map.json)** with a `dtas` block — one registry, many consumers; no parallel DTAS registry |
| 4 | First catalogue channel | **EU LDT Toolbox Marketplace** via `marketplace_publish.py` (concretises BK-4 / Q4 2026 goal) |
| 5 | Quality framework | **Offer V0–V4 + receipt trail as NL input** to DTAS accreditation via the EDIC handover |
| 6 | Gaps at EDIC level | Indicator harmonisation, marketplace federation, accreditation governance are **tracked (§7), not built locally** |

## 10. References

- Source vision: [The Dutch Vision on a European Digital Twin App Store
  (DTAS)](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=3167953)
  — zichtopnl.nl; contacts L. Sleebos / N. Spijkers (VRO)
- NLDT App Store frame: *NLDT Q3 2026 Quarterly Report — Summary in
  English (App Store Focus)* (repo root)
- Internal: [04](04-recipes-and-processes.md) · [07](07-trust-and-governance.md) ·
  [13](13-data-lake-and-space.md) · [21](21-europai-edic-handover.md) ·
  [22](22-dual-audience-spatial-planning.md) ·
  [`recipes/edic-asset-map.json`](recipes/edic-asset-map.json) ·
  [edic/route-citiverse-first.md](edic/route-citiverse-first.md)
- EU anchors named by the vision: EU LDT Toolbox, DS4SSCC, Citycom.ai,
  EIF, INSPIRE, Digital Decade / DGA / AI Act / DSA / DMA —
  [references/bibliography.md](references/bibliography.md)
