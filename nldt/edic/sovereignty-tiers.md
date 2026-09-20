# Cloud and AI Development Act — sovereignty-tier mapping

WP4 rule 6: speak the procurement language administrations will be required
to use. Tiers below are the working vocabulary for EuropAI (proposal status
2026 — re-verify before D4.2). They are **not** a legal assessment.

| Tier | Meaning (working) | nLDT component | Default in this repo |
|------|-------------------|----------------|----------------------|
| T0 | Unclassified / public internet | Public open-data reads (PDOK, DONL) | live |
| T1 | EU-available, extra-EU control possible | Optional LLM seams S7/S8 if a non-NLAIF host is used | gap unless `NLDT_NLAIF_ROUTE` |
| T2 | EU-controlled, restricted extra-EU access | EU LDT Toolbox (UCS, Marketplace, P&V, IM) on `*.ldttoolbox.app`; lake on EU-hosted MinIO | hybrid (mock on laptop) |
| T3 | Public-sector / sovereign compute | Deterministic engines (overlay, zone, peilen, bp2op); local orchestrator critic | live (runs without cloud) |

## Mapping rules

1. **Orchestrator + critic + zone engines = T3-capable.** They run on
   municipal or national infra with no vendor LLM in the decide path.
2. **Toolbox adapters = T2 consumption.** Identity, marketplace and
   visualisation are not rebuilt (WP4 consume-before-build).
3. **Lake = T2 if the object store is EU-hosted; T3 if filesystem on-prem.**
   `accessClass=restricted` still requires HITL regardless of tier.
4. **LLM seams (S7/S8) = T1 unless routed to NLAIF** (`NLDT_NLAIF_ROUTE`).
   Fine-tuning of foundation models is a WP3/LNDS compute-route question,
   not an nLDT engine question.
5. Mock adapters have **no production tier**. `scripts/edic_live_readiness.py`
   must report `live` before a framing demo claims T2 Toolbox consumption.

See declarations: `sovereignty.tier` on each high-risk recipe under
[`declarations/`](declarations/).
