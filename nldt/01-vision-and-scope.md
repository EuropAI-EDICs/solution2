# 01 — Vision and scope

## Vision

A **generic nLDT Digital Twin** makes it possible to model, analyse, and visualise the physical living environment in a modular way — and to steer **agentic AI** safely via open standards. Agents discover building blocks, compose execution plans, and validate results; deterministic engines decide.

This aligns with Geonovum's *Digital Twin as a Service*: reusable building blocks from different suppliers, connected through agreements and standards, in a network of local digital twins.

## Goals

1. **Interoperability** — OGC API Records (catalog), OGC API Processes (compute modules), Recipe metadata (process chains)
2. **Reusability** — AppStore → Cookbook → Cook separation (Testbed 2026 phase 2)
3. **Agent-ready** — MCP as the sole agent↔twin interface; schema-validated plans
4. **Trust** — V0–V4 validation, PROV provenance, human-in-the-loop for high-risk
5. **Hybrid implementation** — EU LDT Toolbox where available; standalone fallback where needed

## Out of scope (v1)

- Domain-specific regulation (e.g. Utrecht Environmental Ordinance) — optional future recipe
- Production deploy on the national nLDT network
- Full Web 3D Context Document implementation (Phase 4)
- Cross-organisation A2A federation (Phase 4)

## Principles

| Principle | Source | Application |
|-----------|--------|-------------|
| Modular | NLDT RA | Building blocks loosely coupled |
| Machine-first | Testbed 2025/2026 | Open APIs, no vendor lock-in |
| LLMs propose, engines dispose | GENAI_SEAMS | No LLM decisions over spatial output |
| Orchestration over integration | EDIC RA | Recipe engine + LangGraph, no point-to-point agent calls |
| Wrap, don't rebuild | MULTI_AGENT_PLAN | Toolbox services via adapters |

## Stakeholders

- **Developers** — integrate processes and recipes via OGC APIs
- **Agent builders** — MCP servers and orchestrator
- **Operators** — identity, audit, HITL
- **Testbed participants** — conformance and feedback on standards

## Success criteria (summary)

See [08-roadmap.md](08-roadmap.md). Minimum: catalog + process + recipe end-to-end; agent via MCP; one process step via EU Toolbox adapter.
