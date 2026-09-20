# Fit statement — LDT CitiVERSE EDIC (one pager)

**Date:** 2026-09-20 (EuropAI M3 / framing M4–M6)  
**Relationship owners (WP4):** VLO + LNDS · **Technical dossier:** ICTU / this repo  
**Asset class:** Solution 2 — urban analysis and spatial planning  
**Track:** lead track of route 3
([route-citiverse-first.md](route-citiverse-first.md)) — first demo, not
the only EDIC conversation.  
**Fallback from M12:** VNG + Geonovum Cookbook

## What we offer that CitiVERSE did not have to build

Working, compliance-documented **spatial recipes** and a **governed agent
layer** that already speak EU LDT Toolbox interfaces (OGC Records/Processes,
Marketplace Agent, Play & Visualise, Identity Management). City evidence from
Utrecht, Breda, Rijnland and Eindhoven. Doctrine: *LLMs propose · engines
dispose · humans decide.*

## What we need

A catalogue slot and a maintenance route after M36; written acceptance
conditions at M13–M18; one live (non-mock) path on `*.ldttoolbox.app`.

## Assets in this class

Reference recipe: `spatial-overlay-analysis` (low risk, overlay + stats).

Also: hex overlay; Breda five-value scan + Q&A; Utrecht opportunity-map /
scenario author / sweep / crosstrack; Rijnland peilen; Eindhoven bp2op;
timeseries and DONL harvest (city data). MCP skills + city onboarding module
(Discover → Lake → Scenarios → Demo).

Not in this class: the implementation framework (IMPACTS), GovChat-NL source
(Digital Commons), live EDC/Keycloak clusters (consume L2).

## Proposed acceptance (until CitiVERSE writes its own)

1. Recipe + process published as Toolbox assets with ValidationReport + PROV.
2. OGC API Records / Processes as the only external interface.
3. Hybrid hook to Play & Visualise after a successful run.
4. MIM + Digital Rulebook declaration for high-risk recipes.
5. Agent Card bearer via Toolbox IM — no localhost identity in production.

## Demo for the framing meeting

```bash
cd nldt
PYTHONPATH=. python -m pytest tests/test_edic_handover.py tests/test_nldt_core.py -q
PYTHONPATH=. python -m scripts.edic_live_readiness
```

Offline overlay still runs locally. Live path:
[citiverse-live-path.md](citiverse-live-path.md).

## Reciprocity

CitiVERSE gets applied AI services for cities and a city-facing capacity
module. EuropAI gets a permanent owner for Solution 2.
