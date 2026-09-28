# 24 — Zicht op Nederland alignment: the national multi-year vision as nLDT's frame

The **Meerjarenvisie Zicht op Nederland — Samen datagedreven werken aan de
fysieke leefomgeving** (Beraad voor Geo-informatie, chaired by the
Director-General for Spatial Planning) is the national umbrella under which
the nLDT Testbed 2026, the NLDT programme and the DTAS vision
([23](23-dtas-alignment.md)) all sit. This chapter records the alignment:
what the vision asks of the information supply chain, what nLDT already
answers, and what it honestly adds to the roadmap. Where [23](23-dtas-alignment.md)
maps the *European* arm, this chapter maps the *national frame*.

| | |
|---|---|
| Status | Plan (2026-09-28) · alignment recorded; two concrete additions tracked (§6) — no dedicated build phases |
| Source | [Meerjarenvisie Zicht op Nederland](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424) (Beraad voor Geo-informatie, 2024; platform zichtopnl.nl) |
| Programme context | Werkagenda Zicht op Nederland, sporen *Samenwerking · Doorontwikkeling NGII · Kaderstelling · Condities voor succes*; programmes **ZoN Datafundament** and **ZoN Digitale Tweeling** |
| Related | [01](01-vision-and-scope.md) · [05](05-agentic-ai-layer.md) · [07](07-trust-and-governance.md) · [09](09-federation-and-observability.md) · [13](13-data-lake-and-space.md) · [14](14-beleidskompas-integration.md) · [17](17-source-monitor.md) · [18](18-donl-harvest.md) · [22](22-dual-audience-spatial-planning.md) · [23](23-dtas-alignment.md) · [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) |
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

**The data value chain** (datawaardeketen: inwinnen → ontslotten →
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

## 2. The mapping: vision → nLDT

| Vision element | nLDT artifact (exists today) |
|---|---|
| "Zelfde samenhangende informatie, begrijpelijk met én zonder digitale kennis" | [22](22-dual-audience-spatial-planning.md): one deterministic core, graduated narration per audience — the streefbeeld's first bullet is chapter 22's mission statement |
| **Georganiseerd vertrouwen** | The receipt trail: ValidationReport + PROV per job, trustPolicy gates, cite-or-abstain, refusal ledgers ([07](07-trust-and-governance.md)) — trust organised as data, not as goodwill |
| *Inwinnen* (incl. AI for mutation detection) | Source monitor continuity probes + human-merge patches ([17](17-source-monitor.md)); DONL/CKAN harvest ([18](18-donl-harvest.md)); AI mutation-detection itself is future work |
| *Ontsluiten*, data bij de bron | OGC API Records/Processes + DCAT catalogues; Data Space / EDC connector with ODRL offers ([13](13-data-lake-and-space.md)); what-if engines apply deltas **without mutating inputs** |
| *Analyseren* — standardised computational models, standardised outcome publication | **Recipes = the standardised rekenmodellen** (schema-validated, versioned); outcome publication = ValidationReport + PROV + run annex, replayable bit-identically |
| *Optelbaarheid* / comparability | Five-value scan normalises indicators across all neighbourhoods; cross-track overlays compare rule sets; cross-twin federation interfaces (A2A, [09](09-federation-and-observability.md)) |
| *Visualiseren*, incl. new forms for administrators/citizens | Web3D context + 3D BAG viewers ([`simulation/`](simulation/)); public lens per [22](22-dual-audience-spatial-planning.md) DA-2 |
| *Gebruiken* — laagdrempelige informatieproducten | Beleidskompas front door ([14](14-beleidskompas-integration.md)); PoC playbooks as Agent Skills ([20](20-poc-mcp-skills.md)) |
| DTFL "niet één systeem, maar afspraken; vergelijken en optellen; leveranciersonafhankelijk" | The nLDT hybrid doctrine itself: open standards (OGC, recipes, MCP) as the interface, EU LDT Toolbox as swappable implementation, federation over unification — and DTAS ([23](23-dtas-alignment.md)) as the European distribution channel |
| Publieke waarden by design | Trust gates + HITL ([07](07-trust-and-governance.md)); wallet identity with selective disclosure ([16](16-eid-wallet-identity.md)); DPIA obligations in [22](22-dual-audience-spatial-planning.md)/[23](23-dtas-alignment.md) |
| FAIR | OGC Records + DCAT-AP metadata, DONL registration, schema-validated contracts |
| Vraagsturing | PoC-first: every recipe answers a named policy question (Utrecht/Breda/Rijnland/Eindhoven), not a data push |

## 3. How the three documents now hang together

```text
 Meerjarenvisie Zicht op Nederland (GI-beraad)        ← the national frame (this chapter)
   └─ programma ZoN Digitale Tweeling (DTFL)
        ├─ nLDT Testbed 2026 / this repo              ← reference implementation
        │    (recipes · engines · governed agent layer · front doors)
        └─ DTAS vision (chapter 23)                   ← the European arm
             └─ LDT CitiVERSE EDIC · EU LDT Toolbox Marketplace
```

The streefbeeld sentence "zelfde informatie voor iedereen, begrijpelijk met
en zonder digitale kennis" spans [22](22-dual-audience-spatial-planning.md)
(audiences) and [23](23-dtas-alignment.md) (validated modules as the
sharing mechanism); the datawaardeketen weak links are what chapters
04/07/13/17/18/22 each close; the DTFL doctrine is why the toolbox wraps
standards instead of building a system.

## 4. What the vision names that nLDT should adopt (honest additions)

1. **Algoritmeregister / AI-Act transparency as an export.** The vision
   requires transparency about *which algorithms government deploys*. nLDT
   already records per-job provenance (model, version, gates, refusals) —
   but only internally. One small export (a per-seam/per-recipe record in
   algoritmeregister-ready form, derived from the seam catalogue and PROV
   bundles) turns existing internals into the externally demanded
   transparency.
2. **Optelbaarheid as an explicit test.** "Summable to a national picture"
   is a stronger claim than "comparable" — it demands agreed indicator
   definitions across areas. The five-value scan already normalises within
   a city; a cross-area run (Breda + a second city, same recipe, same
   indicator definitions) is the first real optelbaarheid test and doubles
   as the DT-4 second-city reuse proof ([23](23-dtas-alignment.md)).

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

## 6. Decisions (2026-09-28)

| # | Decision | Choice |
|---|---|---|
| 1 | Frame | The Meerjarenvisie ZoN is recorded as **the national frame**; DTAS (23) is its European arm; nLDT is a reference implementation of spoor *Doorontwikkeling NGII* / programme *Digitale Tweeling* |
| 2 | Doctrine confirmed | The DTFL sentence ("geheel van afspraken, niet één systeem") is cited as national confirmation of the wrap-don't-rebuild / federation doctrine |
| 3 | Addition ZN-1 | **Algoritmeregister-ready transparency export** from seam catalogue + PROV (small, tracked — no phase plan until an actual registration obligation applies) |
| 4 | Addition ZN-2 | **Optelbaarheid test**: cross-city run of one indicator recipe; folded into DT-4 (second-city reuse, [23](23-dtas-alignment.md)) to avoid duplicate tracks |
| 5 | Non-goals | Ondergrond modelling, financing, legislation work stay **out of repo scope** (§5) |

## 7. References

- Source: [Meerjarenvisie Zicht op Nederland](https://www.zichtopnl.nl/documenten/handlerdownloadfiles.ashx?idnv=2781424)
  — Beraad voor Geo-informatie / ministerie BZK, 2024
- European arm: [23-dtas-alignment.md](23-dtas-alignment.md) ·
  audiences: [22-dual-audience-spatial-planning.md](22-dual-audience-spatial-planning.md) ·
  trust: [07-trust-and-governance.md](07-trust-and-governance.md) ·
  chain chapters: [13](13-data-lake-and-space.md) · [17](17-source-monitor.md) · [18](18-donl-harvest.md) ·
  seam catalogue: [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md)
