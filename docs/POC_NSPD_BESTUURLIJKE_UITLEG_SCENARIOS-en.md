# Executive brief — what the AI pipeline does with scenarios and what-if (NSPD)

| | |
|---|---|
| **For** | Executive board and management (provinces of Zeeland and East Flanders, municipalities and port in the North Sea Port District) |
| **Date** | 17 October 2026 · draft for discussion |
| **Sources** | Dutch original: [POC_NSPD_BESTUURLIJKE_UITLEG_SCENARIOS.md](POC_NSPD_BESTUURLIJKE_UITLEG_SCENARIOS.md) · earlier briefs: [POC_BESTUURLIJKE_SAMENVATTING.md](POC_BESTUURLIJKE_SAMENVATTING.md) (Utrecht/Eindhoven), [poc-nspd/README.md](../poc-nspd/README.md) (technical documentation), [spec](superpowers/specs/2026-10-14-poc-nspd-design.md) |

---

## The core in one paragraph

The NSPD pilot answers, for thirteen policy themes (wind energy, solar, forest,
water, housing, business, …), the same question on **both sides of the border**:
*where is this allowed, and on the basis of which article?* The computer reads
the Zeeland Omgevingsverordening and the Flemish plans (GRUP Zeehavengebied
Gent, the gewestplan) article by article, extracts the corresponding map layers,
and converts them into a single zone map in which every polygon traces back to
a literal citation. Scenarios and what-if sit on top of this as the **policy
calculator**: they show in advance what changes if a chosen rule is applied
differently — before the first permit application, not after. This remains a
deliberate design: **no citation, no rule; no human, no decision.** The AI
computes and proposes; it never signs off and never decides.

## What the pipeline does with scenarios

A scenario is **not a new AI invention but a governable modification of an
already-established rule**. Only three interventions are possible, and each is
a shift of a previously formalised rule:

1. **Drop a rule** — for instance: "what if the wind-energy concentration-area
   policy (article 18.17, annex XIV) were abandoned?" The effect is immediate:
   the development space for wind in the district grows from 12.2 km² to
   852 km².
2. **Adjust a distance** — for instance: "what if the Natura 2000 exclusion
   started 500 metres earlier?" The wind space shrinks by 15%. Everyone
   understands that those 500 metres appear nowhere in the ordinance; the
   system itself says so in the report.
3. **Apply the strictest reading** — for example, executing the 100-metre
   assessment zone around nature areas not as a point of attention but as a
   hard exclusion: 26 km² less space for landscape interventions.

Three safeguards make this trustworthy for governance. First, **the calculator
repeats itself**: with every scenario run, the unchanged situation is silently
recomputed and compared — a deviation of even one thousandth fails the report.
Second, **everything claimed must appear in the report**: the narrative is
automatically checked against every number and article number it mentions —
a text asserting something the computation does not support is rejected.
Third, **the border is not a line but a comparison**: every scenario runs
separately for the Dutch and the Flemish side, so the district is explored as
one area under two legal systems — precisely the cross-border challenge of
North Sea Port.

## What the pipeline does with what-if

What-if is the step before the scenario: the **systematic generation of the
policy variants worth calculating**. The base variants come from the curator
(the human who established the rules); a language model may add proposals, but
they pass through exactly the same gates: non-existent article numbers,
duplicate variants and fabricated sources are refused and land in an open
register of rejected proposals. For every successful variant, the report
states: how much space is gained or lost (in km²), how much of the area stays
the same, on what footing the variant rests (policy variant, interpretation
variant or exploration), plus a link to the full cross-border report. In the
map viewer this is directly visible: grey polygons are the current situation,
green is what a variant adds, red what it costs — click a layer and the report
opens.

## Examples from the pilot

| Policy question (what-if) | Effect on development space |
|---|---|
| Abandon the wind concentration-area policy (NL) | + 840 km² |
| Solar everywhere except Natura 2000 (NL) | + 829 km² |
| Tourist accommodation no longer limited to seaside resorts (NL) | + 985 km² |
| Natura 2000 exclusion brought forward by 500 m (NL, wind) | − 15% |
| 100 m nature-assessment zone as a hard exclusion (NL) | − 26 km² |
| Regional dike exclusion widened by 250 m (NL, water) | − 30 km² |
| Turbine-row zone widened by 500 m (BE side) | + 15.4 km² |

Where a theme has **no map rules** — its norms are of the type "emission
requirement", "notification duty" or "monitoring obligation" — the system
refuses to draw a polygon and the report itself carries the content; this is
explicitly flagged ("area-wide") and the report is one click away in the map
library.

## Caveats and next step

As in the Utrecht and Eindhoven pilots: **the pipeline proposes, the executive
disposes.** A scenario outcome is a computation over established rules and
maps, not advice; the human assessment is a mandatory, permanently open
decision line in the system itself. The next step for the district is to
select a limited number of policy questions from the lever list above, to be
tested by the legal experts on both sides — the system makes that assessment
preparable, not redundant.
