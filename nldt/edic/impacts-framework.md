# IMPACTS-EDIC — Implementation Framework specification (compact)

Reusable multi-country service description of nLDT. Detail remains in
[02](../02-reference-architecture.md), [04](../04-recipes-and-processes.md),
[07](../07-trust-and-governance.md), [12](../12-governed-agent-layer.md).
This page is the IMPACTS-facing extract (WP4 §8.2).

## Object

A governed way for public administrations to **discover, plan, execute and
validate** spatial and policy computations without vendor lock-in, and without
letting a language model write legal geometry.

## External interface (only)

| Capability | Contract | nLDT realisation |
|------------|----------|------------------|
| Discover | OGC API Records | `services/catalog_adapter` |
| Define | Recipe JSON Schema | `schemas/recipe.schema.json` + Cookbook |
| Execute | OGC API Processes | `services/process_adapter` |
| Plan | AgentPlan schema | LangGraph orchestrator |
| Trust | ValidationReport V0–V4 | Critic node + HITL |
| Provenance | W3C PROV | `prov.json` per run |
| Identity | OIDC / Toolbox IM | Keycloak adapter + wallets |
| Exchange | Data Space offer + ODRL | `lake-publish-offer` |

Agents never call UCS internals. They call Records / Processes / Recipe.

## Doctrine (non-negotiable)

*LLMs propose · engines dispose · humans decide.*

- High `riskLevel` or `needs_human` → HITL before a result leaves the
  orchestrator as a trusted artefact.
- Cite-or-abstain for legal claims; reject ledgers instead of silent guesses.
- Marketplace publication carries ValidationReport + PROV
  ([`../services/marketplace_publish.py`](../services/marketplace_publish.py)).

## Declarations

High-risk recipes ship a MIM + Digital Rulebook declaration under
[`declarations/`](declarations/). Schema:
[`../schemas/compliance-declaration.schema.json`](../schemas/compliance-declaration.schema.json).

Procurement descriptions use sovereignty tiers
([sovereignty-tiers.md](sovereignty-tiers.md)).

## Flow A — requirements

Validated interoperability requirements from the four Dutch pilots:
[requirements-backlog.md](requirements-backlog.md). Quarterly consolidation
into IMPACTS / Interoperable Europe processes (WP4 SO4).

## What IMPACTS should not absorb

Spatial Solution 2 city recipes (CitiVERSE). Source-code stewardship
(Digital Commons). National App Store governance (VNG / Geonovum / BZK L4).
