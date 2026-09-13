"""Indicatoren van de Breda vijf-waardenscan — puur en deterministisch.

Elke waarde van *AI in the City 2026* krijgt per buurt een score 0–100
(hoger = meer van die waarde / meer potentieel), samengesteld uit
genormaliseerde deelindicatoren. Normalisatie: percentielscore over alle
buurten mét geldige input (cite-or-abstain: ontbrekende input wordt
genoteerd, nooit geimputeerd).

Richting per waarde (bewust eenduidig "hoger = meer waarde"):

- democratic  — voorzieningen dichtbij + wijkdeals aanwezig;
- spatial     — groene ruggegraat (overlap, groenafstand, bomen);
- economic    — onbenut dakpotentieel + bedrijvigheid;
- social      — waar klimaatadaptatie (hitte) de meeste sociale meerwaarde
                kan opleveren: verharding × 65+-aandeel;
- autonomous  — geen buurtlaag: het soevereiniteitsmanifest (architectuur).
"""

from __future__ import annotations

import math

SENTINEL = -90000  # CBS: -99995 geheim, -99997/onbekend, -99998 niet van toepassing

INPUT_SIMPLIFY_M = 2.0  # CBS-WFS-geometrie is ongesimplificeerd; 2 m DP (PoC-1-praktijk)

# --------------------------------------------------------------------------- #
# CBS-velden per deelindicator (naamgeving conform PDOK WFS 2024, recon 13-9-2026)
# --------------------------------------------------------------------------- #

ACCESS_FIELDS = [
    ("huisartsenpraktijkGemiddeldeAfstandInKm", "huisarts"),
    ("groteSupermarktGemiddeldeAfstandInKm", "supermarkt"),
    ("basisonderwijsGemiddeldeAfstandInKm", "basisschool"),
    ("kinderdagverblijfGemiddeldeAfstandInKm", "kinderdagverblijf"),
    ("bibliotheekGemiddeldeAfstandInKm", "bibliotheek"),
    ("treinstationGemiddeldeAfstandInKm", "treinstation"),
]
ACCESS_MIN_PRESENT = 4  # van de 6 — anders te onvolledig voor een score

BEDRIJVEN_FIELDS = [
    "aantalBedrijvenLandbouwBosbouwVisserij",
    "aantalBedrijvenNijverheidEnergie",
    "aantalBedrijvenHandelEnHoreca",
    "aantalBedrijvenVervoerInformatieCommunicatie",
    "aantalBedrijvenFinancieelOnroerendGoed",
    "aantalBedrijvenZakelijkeDienstverlening",
    "aantalBedrijvenOverheidOnderwijsEnZorg",
    "aantalBedrijvenCultuurRecreatieOverige",
]


def clean(value):
    """CBS-sentinel / leeg / non-numeriek -> None (nooit imputeren)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        if value < SENTINEL:
            return None
        return value
    return None


def percentile_scores(values):
    """Percentielscore 0–100 per index; hoger = hogere rangorde van de waarde.

    ``values``: lijst parallel aan objecten, met ``None`` voor ontbrekend.
    Ontbrekende waarden krijgen score ``None`` en doen niet mee in de
    verdeling.
    """
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return [None if v is None else 50.0 for v in values]
    ordered = sorted(present)

    def rank_score(v):
        # aantal strikt kleinere waarden / (n-1) — mediaan=50 bij oneven n
        lo, hi = 0, len(ordered)
        while lo < hi:
            mid = (lo + hi) // 2
            if ordered[mid] < v:
                lo = mid + 1
            else:
                hi = mid
        first = lo
        last = len(ordered) - 1 - _reverse_rank(ordered, v)
        return 100.0 * ((first + last) / 2) / (len(ordered) - 1)

    return [None if v is None else round(rank_score(v), 1) for v in values]


def _reverse_rank(ordered, v):
    n = 0
    for x in reversed(ordered):
        if x > v:
            n += 1
        else:
            break
    return n


def inverse(scores):
    """Spiegel een percentielscore (van 'hoger=is erger' naar 'hoger=is beter')."""
    return [None if s is None else round(100.0 - s, 1) for s in scores]


def mean_available(parts):
    """Gemiddelde van de niet-None parts; None als er niks is, plus welke ontbreken."""
    present = [p for p in parts if p is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1), [i for i, p in enumerate(parts) if p is None]


# --------------------------------------------------------------------------- #
# Ruimtelijke hulpjes (shapely, alles RD)
# --------------------------------------------------------------------------- #


def _to_geometries(fc):
    from shapely.geometry import shape as _shape

    return [_shape(f["geometry"]) for f in fc["features"] if f.get("geometry") is not None]


def _union(fc):
    from shapely.ops import unary_union

    geoms = _to_geometries(fc)
    if not geoms:
        return None
    return unary_union(geoms)


def _points_in(fc_points, polygons):
    """Aantal punten per polygoon (index-parallel), via STRtree."""
    pts = _to_geometries(fc_points)
    if not pts:
        return [0] * len(polygons)
    from shapely.strtree import STRtree

    tree = STRtree(pts)
    counts = []
    for poly in polygons:
        idx = tree.query(poly, predicate="intersects")
        counts.append(int(len(idx)))
    return counts


def _overlap_share(polygons, cover):
    """Oppervlakteaandeel van elk polygoon dat binnen ``cover`` ligt (0..1)."""
    if cover is None:
        return [None] * len(polygons)
    shares = []
    for poly in polygons:
        area = poly.area
        if area <= 0:
            shares.append(None)
            continue
        inter = poly.intersection(cover).area
        shares.append(min(1.0, inter / area))
    return shares


def _max_overlap_attribute(polygons, other_fc, attr_picker):
    """Per polygoon het attribuut van de ``other``-feature met grootste overlap.

    ``attr_picker(feature_dict) -> value``. Bepaalt bijvoorbeeld per buurt de
    P_verhard van het verhardingsvlak dat er het meeste in ligt (verharding is
    een wijkvlak; buurten nesten daarin).
    """
    others = [
        (_shape_of(f), attr_picker(f))
        for f in other_fc["features"]
        if f.get("geometry") is not None
    ]
    result = []
    for poly in polygons:
        best_val, best_area = None, 0.0
        for geom, val in others:
            if geom is None:
                continue
            inter_area = poly.intersection(geom).area
            if inter_area > best_area:
                best_area, best_val = inter_area, val
        result.append(best_val)
    return result


def _shape_of(feature):
    from shapely.geometry import shape as _shape

    try:
        return _shape(feature["geometry"])
    except Exception:
        return None


def _overlapping_attrs(polygons, other_fc, attr_picker):
    """Alle unieke attribuutwaarden van features die de polygoon raken (kansenkaart)."""
    others = [
        (_shape_of(f), attr_picker(f))
        for f in other_fc["features"]
        if f.get("geometry") is not None
    ]
    result = []
    for poly in polygons:
        vals = []
        for geom, val in others:
            if geom is not None and val is not None and poly.intersects(geom):
                if val not in vals:
                    vals.append(val)
        result.append(vals or None)
    return result


# --------------------------------------------------------------------------- #
# De scan zelf
# --------------------------------------------------------------------------- #


def _mask_water(values, is_water):
    """Zet waarden van water-buurten op None: CBS levert daar geen statistiek,
    dus ook geometrisch berekende deelindicatoren doen niet mee (geen stille
    score zonder bevolkingscontext)."""
    return [None if w else v for v, w in zip(values, is_water)]


def compute_scan(layers: dict) -> dict:
    """Bouw de volledige vijf-waardenscan uit de opgehaalde lagen.

    ``layers``: keys ``buurten`` (verplicht) en optioneel ``wijkdeals``,
    ``hoofdgroenstructuur``, ``verharding``, ``kansenkaart``, ``bomen``
    (elk GeoJSON FeatureCollection RD of None bij degradatie).
    """
    buurten_fc = layers.get("buurten")
    if not buurten_fc or not buurten_fc.get("features"):
        raise ValueError("compute_scan: geen CBS-buurtvlakken (cbs-buurten-2024)")

    feats = buurten_fc["features"]
    polys = [
        g.simplify(INPUT_SIMPLIFY_M, preserve_topology=True)
        for g in _to_geometries(buurten_fc)
    ]
    props = [f.get("properties") or {} for f in feats]
    is_water = [p.get("water") == "JA" for p in props]

    # -- democratisch: afstanden ------------------------------------------- #
    access_vals, access_missing = [], []
    for p in props:
        per_field = {label: clean(p.get(field)) for field, label in ACCESS_FIELDS}
        present = [v for v in per_field.values() if v is not None]
        access_vals.append(
            round(sum(present) / len(present), 3)
            if len(present) >= ACCESS_MIN_PRESENT
            else None
        )
        access_missing.append(
            [k for k, v in per_field.items() if v is None]
        )
    access_score = inverse(percentile_scores(access_vals))  # kortbij = hoog

    deals_fc = layers.get("wijkdeals")
    if deals_fc is not None and deals_fc.get("features"):
        deal_counts = _mask_water(
            _points_in(
                {"features": [
                    {"geometry": f["geometry"]} for f in deals_fc["features"]
                ]},
                polys,
            ),
            is_water,
        )
        deals_score = percentile_scores(deal_counts)
    else:
        deal_counts, deals_score = [None] * len(polys), [None] * len(polys)

    # -- ruimtelijk: groene ruggegraat -------------------------------------- #
    groen_fc = layers.get("hoofdgroenstructuur")
    groen_union = _union(groen_fc) if groen_fc and groen_fc.get("features") else None
    groen_share = _mask_water(_overlap_share(polys, groen_union), is_water)
    groen_share_score = percentile_scores(groen_share)

    groen_afstand = [clean(p.get("afstandTotOpenbaarGroenTotaal")) for p in props]
    groen_afstand_score = inverse(percentile_scores(groen_afstand))

    inwoners = [clean(p.get("aantalInwoners")) for p in props]
    bomen_fc = layers.get("bomen")
    if bomen_fc is not None and bomen_fc.get("features"):
        boom_counts = _mask_water(_points_in(bomen_fc, polys), is_water)
        bomen_per_100 = [
            round(100.0 * c / inw, 2)
            if inw is not None and inw >= 100
            else None
            for c, inw in zip(boom_counts, inwoners)
        ]
        bomen_score = percentile_scores(bomen_per_100)
    else:
        boom_counts, bomen_per_100, bomen_score = (
            [None] * len(polys),
            [None] * len(polys),
            [None] * len(polys),
        )

    kansen_fc = layers.get("kansenkaart")
    if kansen_fc is not None and kansen_fc.get("features"):
        kansen = _overlapping_attrs(polys, kansen_fc, _kansen_omschrijving)
    else:
        kansen = [None] * len(polys)

    # -- economisch: onbenut dak + bedrijvigheid ---------------------------- #
    zon = [clean(p.get("percentageWoningenMetZonnestroom")) for p in props]
    eengezins = [clean(p.get("percentageEengezinswoning")) for p in props]
    onbenut = [
        round((1 - z / 100.0) * (e / 100.0), 4)
        if z is not None and e is not None
        else None
        for z, e in zip(zon, eengezins)
    ]
    onbenut_score = percentile_scores(onbenut)

    opp_ha = [clean(p.get("oppervlakteLandInHa")) for p in props]
    bedrijven_per_km2 = []
    for p, ha in zip(props, opp_ha):
        tot = sum(
            (clean(p.get(f)) or 0) for f in BEDRIJVEN_FIELDS
        )
        if ha is not None and ha > 0 and tot > 0:
            bedrijven_per_km2.append(round(tot / (ha / 100.0), 1))
        else:
            bedrijven_per_km2.append(None)
    bedrijvigheid_score = percentile_scores(bedrijven_per_km2)

    # -- sociaal: hitte-aandacht (verharding × 65+) -------------------------- #
    verh_fc = layers.get("verharding")
    if verh_fc is not None and verh_fc.get("features"):
        verharding = _mask_water(
            _max_overlap_attribute(polys, verh_fc, _p_verhard), is_water
        )
    else:
        verharding = [None] * len(polys)
    verharding_score = percentile_scores(verharding)
    ouderen = [clean(p.get("percentagePersonen65JaarEnOuder")) for p in props]
    ouderen_score = percentile_scores(ouderen)

    # -- samenvoegen per buurt ---------------------------------------------- #
    buurten_out = []
    for i, p in enumerate(props):
        dem_parts = [access_score[i], deals_score[i]]
        soc_parts = [verharding_score[i], ouderen_score[i]]
        spatial_parts = [groen_share_score[i], groen_afstand_score[i], bomen_score[i]]
        econ_parts = [onbenut_score[i], bedrijvigheid_score[i]]

        dem = mean_available(dem_parts)
        soc = mean_available(soc_parts)
        spa = mean_available(spatial_parts)
        eco = mean_available(econ_parts)

        missing = {
            "democratic": access_missing[i]
            + ([] if deals_score[i] is not None else ["wijkdeals-laag"]),
            "spatial": [
                name
                for name, val in (
                    ("hoofdgroenstructuur-dekking", groen_share_score[i]),
                    ("afstand-openbaar-groen", groen_afstand_score[i]),
                    ("bomen", bomen_score[i]),
                )
                if val is None
            ],
            "economic": [
                name
                for name, val in (
                    ("zonnestroom/dakpotentieel", onbenut_score[i]),
                    ("bedrijvigheid", bedrijvigheid_score[i]),
                )
                if val is None
            ],
            "social": [
                name
                for name, val in (
                    ("verharding", verharding_score[i]),
                    ("ouderen-aandeel", ouderen_score[i]),
                )
                if val is None
            ],
        }

        buurten_out.append(
            {
                "buurtcode": p.get("buurtcode"),
                "buurtnaam": p.get("buurtnaam"),
                "wijkcode": p.get("wijkcode"),
                "water": p.get("water"),
                "aantalInwoners": inwoners[i],
                "scores": {
                    "democratic": _score_block(
                        dem, access=access_vals[i], deals=deal_counts[i]
                    ),
                    "spatial": _score_block(
                        spa,
                        groendekking_share=groen_share[i],
                        groen_afstand_km=groen_afstand[i],
                        bomen=boom_counts[i],
                        bomen_per_100_inw=bomen_per_100[i],
                    ),
                    "economic": _score_block(
                        eco,
                        zonnestroom_pct=zon[i],
                        eengezins_pct=eengezins[i],
                        onbenut_dakpotentieel=onbenut[i],
                        bedrijven_per_km2=bedrijven_per_km2[i],
                    ),
                    "social": _score_block(
                        soc,
                        verharding_pct=verharding[i],
                        ouderen_pct=ouderen[i],
                    ),
                },
                "kansenkaart": kansen[i],
                "missing": missing,
            }
        )

    return {
        "buurten": buurten_out,
        "rollup": _rollup(buurten_out),
    }


def _score_block(mean_result, **inputs):
    score = mean_result[0] if isinstance(mean_result, tuple) else mean_result
    block = {"score": score, "inputs": {k: v for k, v in inputs.items()}}
    return block


def _kansen_omschrijving(feature):
    p = feature.get("properties") or {}
    val = p.get("OMSCHRIJV") or p.get("WIJK")
    return val if val else None


def _p_verhard(feature):
    p = feature.get("properties") or {}
    return clean(p.get("P_verhard"))


def _rollup(buurten_out):
    result = {}
    for value in ("democratic", "spatial", "economic", "social"):
        scored = [
            [b["buurtnaam"], b["scores"][value]["score"]]
            for b in buurten_out
            if b.get("water") == "NEE" and b["scores"][value]["score"] is not None
        ]
        if not scored:
            result[value] = {"top": [], "bottom": [], "n": 0}
            continue
        scored.sort(key=lambda t: (-t[1], t[0]))
        result[value] = {
            "top": scored[:5],
            "bottom": list(reversed(scored[-5:])),
            "n": len(scored),
        }
    return result
