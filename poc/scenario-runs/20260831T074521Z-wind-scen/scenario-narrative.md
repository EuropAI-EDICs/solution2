# Scenario narrative — SR-20260830T113234Z-wind-20260831T074521Z

The unmutated control re-executes the baseline at 859.463 km2, reproducing the recorded 859.463 km2 (relative delta 0.000000). Against that control:

- art. 6.3 lid 2 exception granted province-wide (SC-W-NNN-EXCEPTION, flips the documented choice on NC-W-14) moves the opportunity zone to 1,181.982 km2 — +322.519 km2 (+37.53%) versus the control, spatial agreement 0.727136.
- Stiltegebieden treated as hard exclusion (SC-W-STILTE-HARD, flips the documented choice on NC-W-12) moves the opportunity zone to 716.241 km2 — -143.221 km2 (-16.66%) versus the control, spatial agreement 0.833359.
- Aandachtsgebied stiltegebied enforced as 500 m exclusion (SC-W-AANDACHT-500, varies the cited rule behind NC-W-10) (buffer_distance 1500 m -> 500 m, attention marker -> hard exclusion) moves the opportunity zone to 644.506 km2 — -214.956 km2 (-25.01%) versus the control, spatial agreement 0.749895.
- Aandachtsgebied stiltegebied enforced as 1500 m exclusion (SC-W-AANDACHT-1500, flips the documented choice on NC-W-10) moves the opportunity zone to 525.500 km2 — -333.963 km2 (-38.86%) versus the control, spatial agreement 0.611428.
- Aandachtsgebied stiltegebied enforced as 3000 m exclusion (SC-W-AANDACHT-3000, varies the cited rule behind NC-W-10) (buffer_distance 1500 m -> 3000 m, attention marker -> hard exclusion) moves the opportunity zone to 333.712 km2 — -525.751 km2 (-61.17%) versus the control, spatial agreement 0.388279.
- 500 m setback around Natura 2000 / ganzenrustgebieden (SC-W-NATURA-SETBACK, is explicitly not legally grounded) moves the opportunity zone to 812.541 km2 — -46.922 km2 (-5.46%) versus the control, spatial agreement 0.945405.

Every figure above comes from the scenario report rows; the deltas are measured against the re-executed control, not the baseline summary. Scenario choice remains a human decision (V4 pending by design).
