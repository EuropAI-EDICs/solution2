# Contributing to nLDT

nLDT is the Dutch Local Digital Twin reference implementation. Code in
`nldt/` is intended for **Digital Commons EDIC** stewardship (EuropAI T4.3).
Spatial recipes are handed to **LDT CitiVERSE**; the framework to
**IMPACTS-EDIC**. See [21-europai-edic-handover.md](21-europai-edic-handover.md).

## Doctrine

*LLMs propose · engines dispose · humans decide.*

Do not add a path where a language model writes zones, formal rules, or maps.
Do not rebuild EU LDT Toolbox capabilities (UCS, Marketplace, Play & Visualise,
Identity Management). Consume them.

## Licence

Contributions to `nldt/` are accepted under **EUPL-1.2** ([LICENSE](LICENSE)).
Do not copy GovChat-NL / Open WebUI code into this tree.

## Before a pull request

1. `cd nldt && PYTHONPATH=. python -m pytest tests/test_edic_handover.py tests/test_nldt_core.py tests/test_phase4.py -q`
2. New recipes must validate against `schemas/recipe.schema.json` **and** appear
   in `recipes/edic-asset-map.json` with `edic`, `owner`, `acceptance`,
   `fallback`, `readiness`.
3. `riskLevel: high` recipes need a declaration under
   `edic/declarations/<recipeId>.json`.
4. Do not commit secrets, Toolbox client secrets, or live `.env` files.

## Code owners

Named owners live in [CODEOWNERS](CODEOWNERS) and the asset map (`owner`,
`relationshipOwners`). EDIC relationship owners are BZK/ICTU (IMPACTS,
Commons) and VLO/LNDS (CitiVERSE) — they are not GitHub teams.

## Security

Report vulnerabilities per [SECURITY.md](SECURITY.md). Do not file public
issues for undisclosed flaws.
