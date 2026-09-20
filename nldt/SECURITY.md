# Security disclosure

## Report

Email the nLDT maintainers at ICTU (EuropAI NL technical owner) with:

- affected component (`nldt/services/…`, recipe id, adapter)
- reproduction without exploit payload
- whether Toolbox IM / wallets / lake `restricted` data are involved

Do not open a public issue for undisclosed vulnerabilities.

## Scope

In scope: Cookbook, process adapter, catalog, orchestrator, wallets, lake
publish, Marketplace publish, A2A agent card.

Out of scope: EU LDT Toolbox upstream (report to the Toolbox operator);
GovChat-NL upstream (their licence and disclosure process).

## Process

1. Acknowledge within 5 working days.
2. Patch or document compensating control.
3. Credit reporters unless they ask otherwise.
4. High-risk recipe changes require a ValidationReport path and HITL trigger
   to remain intact.

Identity: never commit `KEYCLOAK_CLIENT_SECRET`, `MARKETPLACE_TOKEN`, or
wallet private material. Agent registry (`data/agent-clients.json`) stays
secret-free.
