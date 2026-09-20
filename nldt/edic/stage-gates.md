# WP4 stage gates — nLDT assets

Tied to EuropAI months (project start 1 July 2026). Operating model:
[route-citiverse-first.md](route-citiverse-first.md). Review twice yearly
(WP4 §12.1). If an EDIC has not reached **intent** by M12, **that track’s**
fallback becomes its primary route. Other tracks stay on route 3.

CitiVERSE is the **lead** track (demo + live recipe). IMPACTS is **paper**
until LoI. Commons is **stewardship** until MS19/MS21. Gates below apply to
all three; the lead track has extra evidence in M4–M6.

| Gate | Window | Cluster 2 evidence this repo must show | Fallback if red |
|------|--------|------------------------------------------|-----------------|
| M4–M6 | Oct–Dec 2026 | Asset map published; three fit statements; framing demo of `spatial-overlay-analysis`; live-path runbook | Continue framing; do not claim live Toolbox |
| M7–M12 | Jan–Jun 2027 | Letter of intent CitiVERSE on “spatial recipes + governed agents”; IMPACTS intent on framework; Commons intent on repo. Internally: `edic_live_readiness` hybrid→live for reference recipe | CitiVERSE → VNG/Geonovum Cookbook; IMPACTS → Interoperable Europe/EDIH; code → OS2 |
| M13–M18 | Jul–Dec 2027 | EDIC-written acceptance criteria copied into this backlog (hard). D4.2 scoped annexes. SIMPL pattern or explicit debt. Draft Ecosystem Activation Kit uses nLDT city module | Asset whose destination went cold moves immediately, not at M30 |
| M19–M30 | 2028 H1 | One asset per EDIC in a real setting: CitiVERSE city recipe live; IMPACTS framework published; Commons stewardship live (MS21). Draft handover + [maintenance-envelope.md](maintenance-envelope.md) | Activate documented fallback as primary |
| M31–M36 | to 30 Jun 2029 | Executed handover; D4.4 package; map 100% destination+owner+acceptance | Sustainability plan names the fallback owner |

## Continue-or-fallback decision (every gate)

For each of CitiVERSE / IMPACTS / Commons:

1. Is there a named counterpart and a next meeting date?
2. Does at least one asset in that class meet the *proposed* acceptance?
3. Has the EDIC contradicted the asset class (wrong home)?

If (1) or (2) is no at M12, switch. Do not wait for M30.

## Mapping to Grant Agreement KPIs

- SO3: synergies with ≥3 EDICs; ≥3 handover or service agreements by M36
- SO5: 100% of listed assets with destination, owner, acceptance
- SO2: ≥6 infrastructure connections — tracked in
  [l2-infrastructure.md](l2-infrastructure.md) and
  `scripts/edic_live_readiness.py`
