# L2 — consume Europe’s digital infrastructure (do not rebuild)

WP4 §7.3, six rules, applied to this repository. Infrastructure owner (NL):
ICTU for data/exchange/components; LNDS for compute.

## Checklist

| Rule | nLDT application | Status |
|------|------------------|--------|
| Consume before you build | UCS, Marketplace, P&V, Keycloak IM are adapters. No second orchestrator or marketplace. | held |
| One compute route per country by M6 | NL = NLAIF, **only** for LLM seams S7/S8 (`NLDT_NLAIF_ROUTE`). Overlay/zone/peilen/bp2op stay local. | documented; route confirmation is LNDS |
| Exchange through SIMPL | Data Space connector is `mock` \| `edc-manifest` \| `http` ([13-data-lake-and-space.md](../13-data-lake-and-space.md)). SIMPL-Open is **not** wired. Treat current EDC manifests as a **SIMPL-shaped technical-debt bridge** until ICTU records a Simpl-Open integration pattern. | debt logged |
| Validate in a TEF or sandbox | Book CitCom.AI or an AI Act sandbox for **one** spatial pilot (Breda five-value **or** Utrecht scenario-sweep) before M24. Not done in-repo. | open (pilot owners) |
| Declarations against MIMs / Digital Rulebook | [`declarations/`](declarations/) + schema | proposed |
| Sovereignty-tier language | [sovereignty-tiers.md](sovereignty-tiers.md) | proposed |

## SIMPL / EDC pattern (current)

```
lake gold → lake-publish-offer → ODRL stub
                │
                ├─ mock            local registry
                ├─ edc-manifest    Asset + ContractDefinition JSON
                └─ http            NLDT_EDC_MANAGEMENT_URL or manifest fallback
```

Live Eclipse Dataspace Connector remains **out of band** (roadmap note). Do
not stand up an EDC cluster in this repo. When SIMPL-Open is available, map
`edc-manifest` fields onto Simpl-Open self-descriptions and delete the debt
log entry.

## NLAIF

| Workload | Route |
|----------|--------|
| Spatial intersection, H3, zone engine, peilen, bp2op | local / municipal CPU — **not** NLAIF |
| S7 scenario author (optional LLM) | NLAIF or documented national LLM host |
| S8 narrator (optional LLM) | same as S7 |
| S10 deep research | same as S7; output is a ResearchBrief only |

## CitCom.AI / sandbox

Pilot owners book the slot (WP4 intervention 10). Recommended candidate:
Breda five-value scan (public sources, no secrets, deterministic decide path)
or Utrecht scenario-sweep (stricter V3). Record booking against this file
when it exists; until then the requirement stays `open`.

## AI-on-Demand / DOME

Do not publish a competing component catalogue. Marketplace publication
targets the **EU LDT Toolbox Marketplace Agent**. Exceptions must be argued
in the IMPACTS framework backlog.
