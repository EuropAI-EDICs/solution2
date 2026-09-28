# RA conformity — nLDT against the LDT CitiVERSE EDIC Reference Architecture

Machine-readable outcome of mapping nLDT onto the EDIC Reference
Architecture (RA): what the testbed **is** in RA vocabulary, what it
realises, and where the honest gaps are. Feeds
[21-europai-edic-handover.md](../21-europai-edic-handover.md) (the handover
speaks the EDIC's own capability language) and
[23-dtas-alignment.md](../23-dtas-alignment.md) DT-0 (module passports can
cite RA capabilities).

| | |
|---|---|
| Artefacts | [`ra-capability-map.json`](ra-capability-map.json) (curated mapping) · [`ra-capability-snapshot.json`](ra-capability-snapshot.json) (extracted RA) · [`../scripts/extract_edic_ra.py`](../scripts/extract_edic_ra.py) (extractor) |
| RA source | [Geonovum/ldt-citiverse-edic-ra](https://github.com/Geonovum/ldt-citiverse-edic-ra) @ `0e8519a` · [ArchiMate report](https://geonovum.github.io/ldt-citiverse-edic-ra/archimate/) (model `id-ldt-fixed-arch-003`) |
| Method | Extraction from the ReSpec sources, **pinned to a commit** — the RA repo publishes no `.archimate`/Open Exchange file. Statuses (`strong / partial / absent`) only claim what an artifact evidences. |
| Caveat | RA repo states: *temporary repository, first draft, no licence noted*. The snapshot records provenance; EDIC content is not republished. Coded subcapabilities (`DS.*`…`UX.*`) and MIMs 0–8 live only in the ArchiMate model, not (yet) in the ReSpec text, and are therefore outside this mapping until they land in text. |

---

## 1. The RA in one paragraph

The RA structures an LDT as a composition of **capabilities** along a value
stream (Digital Foundation/Integration → Generate Knowledge → Decide →
Intervene, enabled by Technical and Community Enablement), realised by five
**business services** (Context Awareness; Co-Creation and Participation;
Digital Twin Visualisation; Data Exchange and Collaboration; Capability
Development) on five **application services** (Data; Processing;
Visualisation; Participation; Integration), exposed through **open
interfaces** — OGC API Features/Processes/Records/Tiles and NGSI-LD as
design-time contracts, OIDC/OID4VC for trust, OpenTelemetry for
observability, Dataspace/IDS protocols for sharing, DCAT-AP/PROV-O as
semantic assets. Maturity is expressed in six cumulative **conformance
profiles**: Descriptive → Diagnostic → Predictive → Prospective →
Prescriptive → Autonomous, each with required capabilities and building
blocks. Participation in the ecosystem requires a common foundation
(standards-based APIs, metadata publication, IAM, open interfaces,
guardrails, federated discovery).

## 2. Conformance claim

**Foundation requirements: 4 of 6 strong, 2 partial.** The RA's default
public interfaces are OGC API Records and Processes — which *are* nLDT's
external interface, by original design. The two partials: architectural
guardrails (not yet published as a checkable list; nLDT's V0–V4 covers
outcomes) and federated discovery (live Marketplace registration = DT-1).

**Profile claim: Prospective LDT (strong), with deliberate boundaries.**

| Profile | Claim | Why |
|---|---|---|
| Descriptive | partial | Catalog/lake/viewers exist; no live sensor integration or event detection |
| Diagnostic | partial | Rule knowledge graph + decision tables explain *why*; no generic KG services |
| Predictive | partial | Time-series + CDC replay; no forecasting/ML |
| **Prospective** | **strong** | Scenario Management, What-if Analysis and Model Composition implemented with provenance and controls (Utrecht sweep, Breda variants, Rijnland what-if, cross-track composition) |
| Prescriptive | absent (deliberate) | No recommendation/optimisation — the doctrine keeps the recommendation with the human |
| Autonomous | partial | trustPolicy + HITL match the profile's Policy Enforcement / Human Oversight building blocks; no adaptive learning, no actuation |

This is a useful claim to make externally: the RA itself says not every
twin must be Autonomous — *"Urban Planning Scenarios → Prospective"* is the
RA's own example row — which is exactly the testbed's lane.

## 3. Mapping summary (full detail in the JSON)

| nLDT | RA business/application service | RA standards |
|---|---|---|
| `catalog_adapter` | Data Services (metadata, cataloguing) · Data Exchange (discovery) | OGC API Records, DCAT-AP |
| `process_adapter` + cookbook | Processing Services (processing, simulation, scenario analysis) | OGC API Processes |
| scenario engines (Utrecht/Breda/Rijnland/crosstrack) | **Prospective** capabilities · Computational Models, Scenario Engines | — |
| validation + PROV + run annex | Data Services (provenance management) | PROV-O |
| `context3d` + 3D viewers | Digital Twin Visualisation · Visualisation Services | Web 3D Context schema |
| timeseries + CDC lake | Time Travel groundwork | Parquet |
| source monitor + DONL harvest | Data Services (metadata/quality) | DCAT-AP |
| data space connector | Data Exchange (Data Space participation) | Dataspace Protocol, IDS Catalog (partial) |
| Keycloak + eID/agent wallets | Integration Services (identity federation) | OIDC (strong), OID4VC/VC (partial) |
| MCP + A2A + orchestrator | Integration Services (federation, API mgmt) · Autonomous building blocks | — |
| beleidskompas + S11 | Co-Creation and Participation · Participation Services | — |
| P&V adapter + hybrid bridge | EU LDT Toolbox tool wiring | — |

## 4. Gaps (named by the RA, absent in nLDT)

1. **Live sensing / event detection** (Descriptive) — sources arrive as
   files, not feeds.
2. **Forecasting / ML** (Predictive) — the LLM seams propose; they do not
   forecast.
3. **Recommendation / optimisation** (Prescriptive) — absent *by doctrine*;
   record it as a boundary, not a deficiency.
4. **Adaptive learning / actuation** (Autonomous) — agents act on data and
   models, never on the physical environment.
5. **XR/immersive** (Visualisation) — Cesium viewers only.
6. **Knowledge Graph Services** (Diagnostic) — PoC-1 rule KG exists; no
   SPARQL/KG service product.

## 5. Maintenance (drift)

```bash
# refresh the RA extraction and review drift against the pinned snapshot
.venv/bin/python scripts/extract_edic_ra.py --commit latest --check
# after review, pin the new state
.venv/bin/python scripts/extract_edic_ra.py --commit latest
```

The script fails loudly if the RA structure changes beyond recognition
(profiles/services/standards no longer parse). After a refresh, update the
statuses in [`ra-capability-map.json`](ra-capability-map.json) — never
before: the map claims only what the pinned snapshot supports.
