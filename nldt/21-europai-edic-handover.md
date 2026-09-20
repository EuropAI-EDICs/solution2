# 21 — EuropAI WP4: EDIC handover of nLDT results

Working basis for putting this repository’s **agents, blueprints and
methodology** into EDIC infrastructure and governance. Implements the
*EuropAI WP4 Ecosystem Orchestration Strategy* v1.0 (September 2026, project
month 3; Grant Agreement 101298736) on **this workspace**.

| | |
|---|---|
| Status | M4–M6 framing pack (2026-09-20) |
| Machine-readable map | [`recipes/edic-asset-map.json`](recipes/edic-asset-map.json) |
| Fit statements | [`edic/fit-citiverse.md`](edic/fit-citiverse.md) · [`edic/fit-impacts.md`](edic/fit-impacts.md) · [`edic/fit-commons.md`](edic/fit-commons.md) |
| Live Toolbox path | [`edic/citiverse-live-path.md`](edic/citiverse-live-path.md) |
| Route 3 operating model | [`edic/route-citiverse-first.md`](edic/route-citiverse-first.md) |
| IMPACTS framework | [`edic/impacts-framework.md`](edic/impacts-framework.md) |
| L2 consume checklist | [`edic/l2-infrastructure.md`](edic/l2-infrastructure.md) |
| Stage gates | [`edic/stage-gates.md`](edic/stage-gates.md) |
| Stewardship | [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md) · [`edic/maintenance-envelope.md`](edic/maintenance-envelope.md) |

**Leitmotif remains:** *LLMs propose · engines dispose · humans decide.*

EDICs absorb **services with acceptance conditions**, not Git folders. Every
asset in the map has a destination, a named owner and an acceptance condition
(WP4 SO5). Acceptance conditions in this pack are **proposals** until the
receiving EDIC writes them at the M13–M18 scope stage.

## 1. Why this document exists

nLDT is already aligned with LDT CitiVERSE as a *reference implementation*
([02-reference-architecture.md](02-reference-architecture.md),
[10-toolbox-integration.md](10-toolbox-integration.md)). It was **not** yet an
EuropAI asset with a post-M36 owner. WP4 §8.3: institutional adoption starts
at M4–M6, not in the last quarter.

**Locked route (WP4 §8.2, CitiVERSE-first):** three EDICs in parallel;
CitiVERSE is the first *operational* landing. Operating model:
[edic/route-citiverse-first.md](edic/route-citiverse-first.md).

1. **LDT CitiVERSE EDIC (lead)** — Solution 2: spatial recipes, governed
   agents, city capacity module. First demo because Toolbox adapters exist.
2. **IMPACTS-EDIC (paper track)** — Implementation Framework: orchestrator,
   marketplace *mechanism*, declarations, procurement language. Contact in
   M4; integrated asset after LoI.
3. **Digital Commons EDIC (stewardship track)** — `nldt/` + GovChat-NL
   front door, not as a CitiVERSE app. Pack in M4; repo handover at MS21.

Do not run Toolbox-only publication (route 1) or national App Store first
(route 2). Fallback from M12 is **per track**: CitiVERSE → VNG + Geonovum
Cookbook; IMPACTS → Interoperable Europe / EDIH; code → OS2.

No new European community under the nLDT banner. At EU level EuropAI is an
**invisible orchestrator**; the GenAI4EU CSA (when awarded) is the visible
community (WP4 §4.5).

## 2. Governance (no new bodies)

Follow WP4 §12.

| Role | Held by | What this repo supplies |
|------|---------|-------------------------|
| Forum lead | AAK | Nothing — out of this workspace |
| EDIC owners | BZK + ICTU (IMPACTS, Digital Commons); VLO + LNDS (CitiVERSE) | Fit statements, asset map, acceptance evidence |
| Infrastructure owner (NL) | ICTU (data/exchange/components); LNDS (compute / NLAIF) | L2 checklist; NLAIF only for LLM seams |
| Technical dossier | this repository | [`recipes/edic-asset-map.json`](recipes/edic-asset-map.json) |

Rhythm: monthly map health (no meeting); quarterly review with WP3 sprints;
twice-yearly stage gate continue-or-fallback ([edic/stage-gates.md](edic/stage-gates.md)).

## 3. Asset classes

See the JSON map for the full register. Summary:

| EDIC | What we hand over | Readiness today |
|------|-------------------|-----------------|
| LDT CitiVERSE | Spatial recipes, PoC agents/skills, A2A card, city onboarding module | **hybrid** (adapters exist; defaults still mock) |
| IMPACTS | Orchestrator, schemas, trust methodology, marketplace, Data Space offers, wallets | **hybrid** / schemas **live** as contracts |
| Digital Commons | Source (`nldt/`, `poc/`), GovChat-NL beleidskompas integration | **hybrid** (stewardship pack started) |
| none | Live EDC cluster, production Keycloak, national nLDT network deploy | Consume L2 / L4 — do not rebuild |

Reference recipe for the CitiVERSE live path:
`spatial-overlay-analysis` ([edic/citiverse-live-path.md](edic/citiverse-live-path.md)).

## 4. Reciprocity (WP4 §4.4)

- CitiVERSE gets applied AI services for cities; nLDT gets a maintained
  Toolbox catalogue slot.
- IMPACTS gets a multi-country framework specification; nLDT gets a
  procurement and interoperability channel.
- Digital Commons gets a maintainable repository; nLDT gets a 2030 maintainer.

If we cannot state what the other party gets that it cannot get elsewhere,
the relationship is not opened.

## 5. Verification

```bash
cd nldt
PYTHONPATH=. python -m pytest tests/test_edic_handover.py -q
PYTHONPATH=. python -m scripts.edic_live_readiness
# exit 2 until Toolbox env is live; that is expected on a laptop
```
