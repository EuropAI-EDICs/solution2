# Digital Commons — maintenance cost envelope (1 page)

Proposal for T4.3 / MS21. Not a budget commitment.

## What is a production service vs mock

| Surface | Production intent | Stays mock / local | Indicative effort after M36 |
|---------|-------------------|--------------------|-----------------------------|
| Cookbook + process adapter + catalog | yes — OGC interfaces | — | 0.3 FTE |
| Critic V0–V4 + HITL + PROV | yes — trust gate | — | included above |
| PoC engines (Utrecht/Breda/Rijnland/Eindhoven) | yes as *engines behind* recipes | city-specific corpora | 0.4 FTE shared |
| Toolbox adapters (UCS, P&V, IM, Marketplace) | consume Toolbox; thin adapters | laptop mocks | 0.1 FTE |
| Data lake + EDC/SIMPL connector | silver/gold + offer publish | live EDC cluster | 0.2 FTE |
| GovChat-NL beleidskompas front door | platform pattern | Limburg-hosted UI | 0.2 FTE (integration only) |
| LLM seams S7/S8/S10 | optional | default stub | 0 (NLAIF billed elsewhere) |
| A2A agent card | yes if CitiVERSE federates | localhost URL | included in adapters |

**Envelope:** ≈ **1.2 FTE** to keep the common plus engines replayable,
excluding city-specific data work and excluding EuroHPC compute.

## What we will not maintain as a common

- A second marketplace or IAM
- Production Eclipse Dataspace Connector
- National nLDT network operations
- Closed LLM subscriptions

## Licence

nLDT code: **EUPL-1.2** ([LICENSE](../LICENSE)). GovChat-NL is a *dependency
with a different licence* (Open WebUI Licence) — see
[14-beleidskompas-integration.md](../14-beleidskompas-integration.md) §9.
Do not relicense GovChat-NL as EUPL.
