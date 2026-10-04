# 24 — Zicht op Nederland alignment: the national multi-year vision as nLDT's frame

The **Meerjarenvisie Zicht op Nederland — Samen datagedreven werken aan de
fysieke leefomgeving** (Beraad voor Geo-informatie, chaired by the
Director-General for Spatial Planning) is the national umbrella under which
the nLDT Testbed 2026, the NLDT programme and the DTAS vision
([23](23-dtas-alignment.md)) all sit. This chapter records the alignment in
**both directions**: what the vision asks and what nLDT already answers
(§1–§2), and what must change in the *vision / werkagenda language* so it
stays honest about 2026 practice (§4). Where [23](23-dtas-alignment.md)
maps the *European* arm, this chapter maps the *national frame*.

| | |
|---|---|
| Status | Plan (2026-10-04) · bidirectional alignment; ZN-1/ZN-2 tracked; bestuurlijk addendum published |
| Source | [Meerjarenvisie Zicht op Nederland](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424) (Beraad voor Geo-informatie, april 2024; platform zichtopnl.nl) |
| Bestuurlijk addendum | [zon-addendum-digitale-tweeling-2026.md](zon-addendum-digitale-tweeling-2026.md) — NL, for programmaraden / GI-beraad |
| Programme context | Werkagenda Zicht op Nederland, sporen *Samenwerking · Doorontwikkeling NGII · Kaderstelling · Condities voor succes*; programmes **ZoN Datafundament** and **ZoN Digitale Tweeling** |
| Related | [01](01-vision-and-scope.md) · [05](05-agentic-ai-layer.md) · [07](07-trust-and-governance.md) · [09](09-federation-and-observability.md) · [13](13-data-lake-and-space.md) · [14](14-beleidskompas-integration.md) · [17](17-source-monitor.md) · [18](18-donl-harvest.md) · [22](22-dual-audience-spatial-planning.md) · [23](23-dtas-alignment.md) · [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) · [bestuurlijke-samenvatting.md](bestuurlijke-samenvatting.md) |
| EuropAI EDIC home | **LDT CitiVERSE** — via the DTAS line ([23](23-dtas-alignment.md)) |

---

## 1. What the vision asks

**Streefbeeld.** Every government organisation, citizen and entrepreneur
working on physical-environment tasks uses *the same coherent, reliable
information* — in a form usable **with and without digital literacy**;
complete, sector-spanning and integral; regionally and nationally
comparable and **optelbaar** (summable to a national picture); predictive
(scenario's) as well as descriptive; above **and below** ground; 3D where
needed; from public and private sources — while public values
(veiligheid, democratie, zelfbeschikking, non-discriminatie, participatie,
privacy, inclusiviteit) are safeguarded *by design*.

**The movement.** From supply-driven to **vraagsturing** (demand-driven
from the societal task); from point solutions to collaboration and
**georganiseerd vertrouwen** (organised trust), governed by the GI-beraad
and programme councils, public-private (GeoSamen).

**The data value chain** (datawaardeketen: inwinnen → ontsloten →
analyseren/visualiseren → gebruiken) with named weak links: missing data
and poor metadata; unwillingness to share and copies instead of *data bij
de bron*; unclear coherence and summability between sources;
**insufficient standardisation of computational models and of how outcomes
are published**; visualisation geared to geo-specialists rather than
administrators, advisers and citizens; use lagging behind supply.

**The national twin system (DTFL).** The crucial doctrinal sentence:

> *"Het nationaal stelsel Digitale Tweeling Fysieke Leefomgeving (DTFL) is
> niet één systeem, maar bestaat uit een geheel van afspraken die het
> mogelijk maken om regionale, thematische of stedelijke DTFL's … te
> kunnen vergelijken en bij elkaar 'op te tellen'. … Nieuwe digitale
> tweelingen kunnen dan gebruik maken van al bestaande functionaliteiten
> en verrijkte brondata en modellen, ongeacht welke leverancier die zij
> gebruiken."*

Standards for visualisation, analysis and simulation models under a
**pas-toe-of-leg-uit** policy; a trustworthy DTFL infrastructure to build
on, vendor-independent.

**Frameworks (kaders).** AI Act + **algoritmeregister** transparency, AVG,
Waardengedreven Digitaliseren, NIS2/BIO, FAIR, European dataspaces
(INSPIRE as forerunner), the Dutch Federatief Datastelsel (data bij de
bron) — plus structural financing as the decisive condition.

---

## 2. The mapping: vision → nLDT

| Vision element | nLDT artifact (exists today) |
|---|---|
| "Zelfde samenhangende informatie, begrijpelijk met én zonder digitale kennis" | [22](22-dual-audience-spatial-planning.md): one deterministic core, graduated narration per audience — the streefbeeld's first bullet is chapter 22's mission statement |
| **Georganiseerd vertrouwen** | The receipt trail: ValidationReport + PROV per job, trustPolicy gates, cite-or-abstain, refusal ledgers ([07](07-trust-and-governance.md)) — trust organised as data, not as goodwill |
| *Inwinnen* (incl. AI for mutation detection) | Source monitor continuity probes + human-merge patches ([17](17-source-monitor.md)); DONL/CKAN harvest ([18](18-donl-harvest.md)); AI mutation-detection itself is future work |
| *Ontsluiten*, data bij de bron | OGC API Records/Processes + DCAT catalogues; Data Space / EDC connector with ODRL offers ([13](13-data-lake-and-space.md)); what-if engines apply deltas **without mutating inputs** |
| *Analyseren* — standardised computational models, standardised outcome publication | **Recipes = the standardised rekenmodellen** (schema-validated, versioned); outcome publication = ValidationReport + PROV + run annex, replayable bit-identically |
| *Optelbaarheid* / comparability | Five-value scan normalises indicators across neighbourhoods; cross-track overlays compare rule sets; cross-twin federation interfaces (A2A, [09](09-federation-and-observability.md)); **ZN-2 MVP:** same formula fingerprint over two fixture areas + weighted combined means ([`poc-breda/optelbaarheid_run.py`](../poc-breda/optelbaarheid_run.py), [design](../docs/superpowers/specs/2026-10-04-zn2-optelbaarheid-design.md)) — live second city still open |
| *Visualiseren*, incl. new forms for administrators/citizens | Web3D context + 3D BAG viewers ([`simulation/`](simulation/)); public lens per [22](22-dual-audience-spatial-planning.md) DA-2 |
| *Gebruiken* — laagdrempelige informatieproducten | Beleidskompas front door ([14](14-beleidskompas-integration.md)); PoC playbooks as Agent Skills ([20](20-poc-mcp-skills.md)) |
| DTFL "niet één systeem, maar afspraken; vergelijken en optellen; leveranciersonafhankelijk" | The nLDT hybrid doctrine itself: open standards (OGC, recipes, MCP) as the interface, EU LDT Toolbox as swappable implementation, federation over unification — and DTAS ([23](23-dtas-alignment.md)) as the European distribution channel |
| Publieke waarden by design | Trust gates + HITL ([07](07-trust-and-governance.md)); wallet identity with selective disclosure ([16](16-eid-wallet-identity.md)); DPIA obligations in [22](22-dual-audience-spatial-planning.md)/[23](23-dtas-alignment.md) |
| FAIR | OGC Records + DCAT-AP metadata, DONL registration, schema-validated contracts |
| Vraagsturing | PoC-first: every recipe answers a named policy question (Utrecht/Breda/Rijnland/Eindhoven), not a data push |
| Integrale gebiedsafweging (multi-value trade-offs in one area) | **Plane D** (Breda): spatial claims on the five-value scan → `gebiedsafweging-report`; human decides (V4). Design: [`docs/superpowers/specs/2026-10-04-breda-gebiedsafweging-plane-d-design.md`](../docs/superpowers/specs/2026-10-04-breda-gebiedsafweging-plane-d-design.md); recipe `breda-gebiedsafweging` |

---

## 3. How the three documents now hang together

```text
 Meerjarenvisie Zicht op Nederland (GI-beraad, 2024)   ← national frame
   └─ Addendum 2026 Digitale Tweeling                  ← werkagenda language update
        └─ programma ZoN Digitale Tweeling (DTFL)
             ├─ nLDT Testbed 2026 / this repo           ← reference implementation
             │    (recipes · engines · governed agent layer · front doors)
             └─ DTAS vision (chapter 23)                ← European arm
                  └─ LDT CitiVERSE EDIC · EU LDT Toolbox Marketplace
```

The streefbeeld sentence "zelfde informatie voor iedereen, begrijpelijk met
en zonder digitale kennis" spans [22](22-dual-audience-spatial-planning.md)
(audiences) and [23](23-dtas-alignment.md) (validated modules as the
sharing mechanism); the datawaardeketen weak links are what chapters
04/07/13/17/18/22 each close; the DTFL doctrine is why the toolbox wraps
standards instead of building a system.

---

## 4. The reverse mapping: what must change in the vision / werkagenda

Do **not** rewrite the 2024 PDF wholesale. Publish a programme addendum
(and update werkagenda indicators) so national language matches what the
reference implementation has proven. Full NL text:
[zon-addendum-digitale-tweeling-2026.md](zon-addendum-digitale-tweeling-2026.md).

| # | 2024 text / emphasis | Change toward project practice | Keep / drop |
|---|---|---|---|
| A | DTFL described only as abstract afspraken + pas-toe-of-leg-uit | Name concrete building blocks: recipes, ValidationReport+PROV, OGC Processes, governed agent layer | Keep doctrine sentence |
| B | AI for analysis “experimenteel of op beperkte schaal” | Governed AI in the chain; *LLMs propose, engines dispose*; numbers never from the LLM | Keep AI Act / ethics framing |
| C | Georganiseerd vertrouwen as governance / willingness | Add trust as **receipt trail** (gates, refusals, PROV) | Keep GI-beraad governance |
| D | “Begrijpelijk met én zonder digitale kennis” without mechanism | **One rekenkern, multiple front doors** (planner / adviser / public) | Keep streefbeeld bullet |
| E | European kaders: dataspace / FDS / INSPIRE only | Add DTAS, EU LDT Toolbox Marketplace, LDT CitiVERSE EDIC as functional distribution | Keep FDS for data-at-source |
| F | Optelbaarheid + algoritmeregister as ambition only | Make **measurable** (ZN-2 cross-area recipe; ZN-1 register-ready export) | Keep as obligations |
| G | Context Contourennotitie / coalitieakkoord 2022–23 | Refresh political/policy references when the addendum is formally adopted | Not a repo task |

### 4.1 What the vision names that nLDT should still adopt (honest additions)

1. **ZN-1 — Algoritmeregister / AI-Act transparency as an export.**
   Per-job provenance already exists internally (model, version, gates,
   refusals). Missing: a per-seam/per-recipe export in
   algoritmeregister-ready form from the seam catalogue + PROV bundles.
2. **ZN-2 — Optelbaarheid as an explicit test.**
   “Summable to a national picture” is stronger than “comparable”. First
   real test: same indicator recipe, same definitions, in two areas
   (e.g. Breda + second city). Folded into DT-4 second-city reuse
   ([23](23-dtas-alignment.md)) to avoid a duplicate track.

---

## 5. What the vision names that stays out of repo scope

- **Ondergrond** (below-ground: soil, cables/pipes, groundwater as
  first-class modelled domain) — the repo is above-ground today (3D BAG,
  water levels as time series); MiniGIM flags ondergrond themes
  `manual-action`. Tracked as a roadmap note, not built.
- **Wet- en regelgeving / financing / governance-beraad** — national
  programme work; the repo's role is evidence (e.g. run annexes as
  audit-ready records), not policy.
- **Datafundament** (basisregistraties versterken) — source systems'
  responsibility; nLDT consumes and monitors them (17/18).

These belong in the 2024 vision and remain valid; the addendum explicitly
does **not** claim the project closes them.

---

## 6. Decisions

| # | Decision | Choice | Date |
|---|---|---|---|
| 1 | Frame | The Meerjarenvisie ZoN is **the national frame**; DTAS (23) is its European arm; nLDT is a reference implementation of spoor *Doorontwikkeling NGII* / programme *Digitale Tweeling* | 2026-09-28 |
| 2 | Doctrine confirmed | The DTFL sentence ("geheel van afspraken, niet één systeem") is national confirmation of wrap-don't-rebuild / federation | 2026-09-28 |
| 3 | Addition ZN-1 | **Algoritmeregister-ready transparency export** from seam catalogue + PROV (tracked — no phase plan until a registration obligation applies) | 2026-09-28 |
| 4 | Addition ZN-2 | **Optelbaarheid test**: cross-city run of one indicator recipe; folded into DT-4 ([23](23-dtas-alignment.md)) | 2026-09-28 |
| 4b | ZN-2 MVP | Offline two-area fixture proof shipped (`optelbaarheid_run.py`); live second organisation remains DT-4 | 2026-10-04 |
| 5 | Non-goals | Ondergrond modelling, financing, legislation stay **out of repo scope** (§5) | 2026-09-28 |
| 6 | Reverse mapping | Vision/werkagenda updates are recorded in §4 and published as NL addendum [zon-addendum-digitale-tweeling-2026.md](zon-addendum-digitale-tweeling-2026.md); do not rewrite the 2024 PDF in-repo | 2026-10-04 |

---

## 7. References

- Source: [Meerjarenvisie Zicht op Nederland](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424)
  — Beraad voor Geo-informatie / ministerie BZK, april 2024
- Bestuurlijk addendum: [zon-addendum-digitale-tweeling-2026.md](zon-addendum-digitale-tweeling-2026.md)
- European arm: [23-dtas-alignment.md](23-dtas-alignment.md) ·
  audiences: [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md) ·
  trust: [07-trust-and-governance.md](07-trust-and-governance.md) ·
  chain chapters: [13](13-data-lake-and-space.md) · [17](17-source-monitor.md) · [18](18-donl-harvest.md) ·
  seam catalogue: [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md)
