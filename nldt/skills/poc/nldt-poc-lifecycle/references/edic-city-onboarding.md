# EDIC city onboarding (CitiVERSE capacity module)

This is the **city-facing** packaging of the PoC lifecycle for LDT CitiVERSE
EDIC. It is not a new skill family. Operators follow the same four phases;
the EDIC conversation uses this page as the capacity-building annex
(WP4 §8.2: “a city-facing capacity-building module”).

Doctrine: **AI proposes · pipeline disposes · human decides.**

## Who this is for

A municipal or regional digital-twin team that already has (or can reach)
EU LDT Toolbox Identity Management. No EuropAI staff required after the
ninety-day sequence.

## Ninety-day sequence

1. **Days 1–15 — Discover.** Catalog search + source-monitor. Record
   `accessClass`. Do not ingest restricted data.
2. **Days 16–40 — Lake.** Bronze snapshot → silver convert. Gold only via
   registered processes. Restricted offers need HITL
   (`lake-publish-offer`).
3. **Days 41–70 — Scenarios.** Pick one domain skill (`breda-scan`,
   `utrecht-scenario`, `rijnland-peilen`, or overlay-only
   `spatial-overlay-analysis`). Critic V0–V4 on every run.
4. **Days 71–90 — Demo.** Static HTML under `nldt/simulation/`; no secrets
   in the page. Optional: publish the recipe to the Toolbox Marketplace
   with ValidationReport + PROV
   ([edic/citiverse-live-path.md](../../../../edic/citiverse-live-path.md)).
   Worked example (Breda on route 3):
   [edic/breda-route-map.md](../../../../edic/breda-route-map.md).

## Hard rules

- Skills are untrusted instructions. Writes only through processes.
- LLMs never write zones or maps.
- Laptop mocks are not a production twin. Run
  `python -m scripts.edic_live_readiness` before claiming Toolbox
  consumption.

## Hand-off

After phase 3, open the domain skill listed in the parent
[SKILL.md](../SKILL.md). EDIC relationship owners: VLO + LNDS; technical
dossier: ICTU.
