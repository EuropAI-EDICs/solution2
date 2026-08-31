# Cross-track conflict report — XR-20260831T094204Z

| track | baseline run | final km² | reproduction rel Δ |
|---|---|---:|---:|
| wind | 20260830T113234Z-wind | 859.463 | 0.000000 |
| zon | 20260830T142439Z-zon | 1,167.936 | 0.000000 |
| bos | 20260830T142446Z-bos | 23.924 | 0.000000 |

## Pairwise conflicts (open on the same ground)

| pair | conflict km² | share of each track's zone |
|---|---:|---|
| wind × zon | 845.445 | wind 98.37% · zon 72.39% |
| wind × bos | 22.657 | wind 2.64% · bos 94.70% |
| zon × bos | 22.665 | zon 1.94% · bos 94.74% |

## Shared zone: `groene_contour` (23.925 km²)

> Groene contour: the bos track's zoekgebied nieuwe natuur (art. 6.4 lid 1) and simultaneously a compensation marker for zon (art. 6.5a lid 3: new nature within 25 years of panel placement) and wind (art. 6.5 lid 2 onder d: >=1:1 compensation ratio) — the verordening's own energy-vs-nature conflict zone.

| track | overlap km² | share of zone | share of track zone |
|---|---:|---:|---:|
| wind | 22.655 | 94.69% | 2.64% |
| zon | 22.665 | 94.74% | 1.94% |
| bos | 23.921 | 99.98% | 99.98% |

> Deterministic cross-track overlay (docs/GENAI_SEAMS.md phase C base): each track's unmutated control re-executed from its baseline run; no legal claim is added, dropped or mutated (V2 not_applicable by design).
> A conflict area is ground on which two tracks' opportunity zones are both open under the current verordening — the programming stage must arbitrate; this overlay quantifies, never decides.
