"""Capaciteitsgewogen afwateringsgraad uit Rijnlands openbare legger.

Trede 1 van de flow-integratie ("legger-hydrauliek", géén rekenmodel):
peilgebieden met streefpeilen bepalen de zwaartekrachtrichting tussen
aangrenzende gebieden, gemalen leggen de pomprichtingen vast (elk gemaal
verwijst naar het peilgebied dat het bemaalt), en de dwarsprofielen van
de primaire watergangen geven elke verbinding een doorvoervermogen
(Manning-doorvoerterm K = (1/n)·A·R^(2/3), zonder talud-aannames: alle
profieldelen komen uit de legger). Daarmee is ``derive_values`` een
eerlijke, afgeleide-cel-als-afgeleide-gelabelde opvulling: eerst de
mediaan van het eigen peilgebied (binnen één peilgebied is het water
vlak), daarna de dichtstbijzijnde gemeten cel stroomopwaarts in de
afwateringsketen, met verval naarmate de graafafstand toeneemt.

H3-operaties gaan via de bridge (architectuur C): alleen
``h3-polygon-to-cells`` voor de cel→peilgebied-toewijzing. Punt-in-
polygon voor waterganguiteinden en gemaalontvangers is gewone shapely-
geometrie en blijft PoC-lokaal.
"""

from __future__ import annotations

import json
import statistics
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "flow"
_DEFAULT_ROUGHNESS = 0.03  # Strickler-ruwheid bij ontbreken RUWHEIDSWAARDELAAG
_EPS_CAP = 0.01            # capaciteitsgewicht van onbekende gemaalcapaciteit


def streefpeil(props: Mapping[str, Any]) -> Optional[float]:
    """VASTPEIL, anders het gemiddelde van ZOMER- en WINTERPEIL (m NAP)."""
    if props.get("VASTPEIL") is not None:
        return float(props["VASTPEIL"])
    z, w = props.get("ZOMERPEIL"), props.get("WINTERPEIL")
    if z is not None and w is not None:
        return round((float(z) + float(w)) / 2.0, 4)
    if z is not None:
        return float(z)
    if w is not None:
        return float(w)
    return None


def conveyance(props: Mapping[str, Any]) -> float:
    """Manning-doorvoerterm K = (1/n)·A·R^(2/3) voor een trapeziumprofiel.

    A = d·b + d²·(z_links+z_rechts)/2, P = b + d·(√(1+z_l²)+√(1+z_r²)).
    K is het debiet per vierkantswortel van het verval (m³/s bij S=1);
    het werkelijke debiet volgt pas met een talud/helling, die de legger
    niet geeft — daarom heet dit consequent doorvoervermogen, geen
    debiet. Ontbrekende profieldelen leveren K=0 op (geén fantasie)."""
    b = props.get("BODEMBREEDTE")
    d = props.get("WATERDIEPTE")
    if not b or not d:
        return 0.0
    b, d = float(b), float(d)
    zl = float(props.get("TALUDHELLINGLINKS") or 0.0)
    zr = float(props.get("TALUDHELLINGRECHTS") or 0.0)
    n = float(props.get("RUWHEIDSWAARDELAAG") or _DEFAULT_ROUGHNESS)
    area = d * b + d * d * (zl + zr) / 2.0
    perim = b + d * ((1 + zl * zl) ** 0.5 + (1 + zr * zr) ** 0.5)
    if area <= 0 or perim <= 0 or n <= 0:
        return 0.0
    radius = area / perim
    return round((1.0 / n) * area * radius ** (2.0 / 3.0), 4)


def load_fixtures(fixture_dir: Path = FIXTURE_DIR) -> Dict[str, Any]:
    return {
        "peilgebieden": json.loads(
            (fixture_dir / "peilgebieden.geojson").read_text(encoding="utf-8")),
        "gemalen": json.loads(
            (fixture_dir / "gemalen.geojson").read_text(encoding="utf-8")),
        "watergangen": json.loads(
            (fixture_dir / "watergangen-primair.json").read_text(encoding="utf-8")),
    }


def _containing_finder(polys: List[Tuple[str, Any]]):
    """Bepaalend peilgebied per punt: shapely STRtree; bij overlap of
    missers de dichtstbijzijnde (vindplaatsen van de legger liggen soms
    net buiten hun eigen gebied)."""
    from shapely.geometry import Point
    from shapely.strtree import STRtree

    tree = STRtree([g for _, g in polys])

    def find(x: float, y: float) -> Optional[str]:
        pt = Point(x, y)
        for i in tree.query(pt):
            if polys[int(i)][1].contains(pt):
                return polys[int(i)][0]
        return polys[int(tree.nearest(pt))][0]

    return find


def build_flow_graph(
    *,
    peilgebieden_fc: Mapping[str, Any],
    gemalen_fc: Mapping[str, Any],
    watergangen: Mapping[str, Any],
    resolution: int = 8,
    call: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Cel→peilgebied + gerichte, capaciteitsgewogen afwateringsgraven.

    Kanten: ``gravity`` (hoger → lager streefpeil, capaciteit = som van
    het doorvoervermogen van de verbindende primaire watergangen) en
    ``gemaal`` (bemaald peilgebied → ontvangend peilgebied, capaciteit =
    MAXIMALECAPACITEIT/60 m³/s; pomprichting geldt ongeacht peil)."""
    if call is None:
        return None
    from shapely.geometry import shape
    from shapely.validation import make_valid

    nodes: Dict[str, Dict[str, Any]] = {}
    polys: List[Tuple[str, Any]] = []
    cell_pg: Dict[str, str] = {}
    for f in sorted(peilgebieden_fc.get("features") or [],
                    key=lambda f: (f.get("properties") or {}).get("CODE") or ""):
        p = f.get("properties") or {}
        code = p.get("CODE")
        geom = shape(f["geometry"])
        if not geom.is_valid:
            geom = make_valid(geom)
        nodes[code] = {"name": p.get("NAAM") or code,
                       "peil": streefpeil(p),
                       "soort": p.get("SOORTAFWATERING"),
                       "nCells": 0}
        polys.append((code, geom))
        cov = call("h3-polygon-to-cells",
                   {"polygon": {"type": "FeatureCollection",
                                "features": [f]},
                    "resolution": resolution})["coverage"]
        for row in cov.get("cells") or []:
            if row["cell"] not in cell_pg:  # overlap: eerste (gesorteerde) code
                cell_pg[row["cell"]] = code
                nodes[code]["nCells"] += 1

    find = _containing_finder(polys)

    # watergangen verbinden peilgebieden fysiek; hun profiel bepaalt
    # het doorvoervermogen van de verbinding
    conn: Dict[Tuple[str, str], float] = {}
    for row in watergangen.get("rows") or []:
        (sx, sy), (_mx, _my), (ex, ey) = row["p"]
        a, b = find(sx, sy), find(ex, ey)
        if not a or not b or a == b:
            continue
        key = (a, b) if a < b else (b, a)
        conn[key] = round(conn.get(key, 0.0) + conveyance(row["a"]), 4)

    edges: List[Dict[str, Any]] = []
    for (a, b), k in sorted(conn.items()):
        pa, pb = nodes[a]["peil"], nodes[b]["peil"]
        if pa is None or pb is None or pa == pb:
            continue  # richting onbepaalbaar: geen aannames
        hi, lo = (a, b) if pa > pb else (b, a)
        edges.append({"from": hi, "to": lo, "kind": "gravity",
                      "capacity": k})

    for f in sorted(gemalen_fc.get("features") or [],
                    key=lambda f: (f.get("properties") or {}).get("CODE") or ""):
        p = f.get("properties") or {}
        drained = p.get("CODEPEILGEBIEDPRAKTIJK")
        if drained not in nodes:
            continue
        gx, gy = (f.get("geometry") or {}).get("coordinates") or [None, None]
        if gx is None:
            continue
        receiving = find(gx, gy)
        if receiving in (None, drained):
            continue  # ontvanger niet te bepalen: geen fantasierichting
        cap = p.get("MAXIMALECAPACITEIT")
        edges.append({"from": drained, "to": receiving, "kind": "gemaal",
                      "capacity": round(float(cap) / 60.0, 4)
                      if cap else None})

    edges.sort(key=lambda e: (e["from"], e["to"], e["kind"]))
    upstream: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        upstream.setdefault(e["to"], []).append(
            {"from": e["from"], "capacity": e["capacity"] or _EPS_CAP,
             "kind": e["kind"]})
    return {"nodes": nodes, "cellPg": cell_pg, "edges": edges,
            "upstream": upstream, "resolution": resolution}


def derive_values(
    graph: Mapping[str, Any],
    values: Mapping[str, Sequence[Optional[float]]],
    *,
    max_depth: int = 3,
    decay: float = 0.5,
) -> Dict[str, Any]:
    """Per cel per stap een afgeleide waarde, of None.

    Regel (eerlijk gelabeld): gemeten cellen blijven gemeten; een lege
    cel erft eerst de mediaan van gemeten cellen in het eigen
    peilgebied (vlak water), anders de best-scorende meting
    stroomopwaarts — score = flessenhals-capaciteit × decay^diepte.
    Return: ``{"derived": {cell: [v|null per stap]},
    "notes": {cell: bronomschrijving}}``."""
    cell_pg = graph["cellPg"]
    nodes = graph["nodes"]
    upstream = graph["upstream"]
    n_steps = max((len(s) for s in values.values()), default=0)

    def pg_medians(t: int) -> Dict[str, Tuple[float, int]]:
        per_pg: Dict[str, List[float]] = {}
        for cell, series in values.items():
            pg = cell_pg.get(cell)
            if pg is None or t >= len(series) or series[t] is None:
                continue
            per_pg.setdefault(pg, []).append(float(series[t]))
        return {pg: (statistics.median(v), len(v))
                for pg, v in per_pg.items()}

    def upstream_median(start: str, medians) -> Optional[Tuple[float, str, int]]:
        best: Optional[Tuple[float, str, int]] = None
        seen = {start}
        frontier = deque([(start, 1.0)])  # (peilgebied, flessenhals-capaciteit)
        depth = 0
        while frontier and depth < max_depth:
            nxt = deque()
            for pg, cap in frontier:
                for edge in upstream.get(pg) or []:
                    src = edge["from"]
                    if src in seen:
                        continue
                    seen.add(src)
                    bottleneck = min(cap, edge["capacity"])
                    if src in medians:
                        score = bottleneck * (decay ** (depth + 1))
                        cand = (score, src)
                        if best is None or (cand[0], cand[1]) > (best[0], best[1]):
                            best = (score, src, depth + 1)
                    nxt.append((src, bottleneck))
            frontier = nxt
            depth += 1
        return best

    derived: Dict[str, List[Optional[float]]] = {}
    notes: Dict[str, str] = {}
    step_meds = [pg_medians(t) for t in range(n_steps)]
    for cell, series in values.items():
        pg = cell_pg.get(cell)
        row: List[Optional[float]] = []
        for t in range(n_steps):
            if t < len(series) and series[t] is not None:
                row.append(None)  # gemeten blijft gemeten
                continue
            if pg is None:
                row.append(None)
                continue
            med = step_meds[t].get(pg)
            if med:
                row.append(round(med[0], 4))
                notes.setdefault(
                    cell, f"mediaan peilgebied {nodes[pg]['name']} "
                          f"(n={med[1]})")
                continue
            up = upstream_median(pg, step_meds[t])
            if up:
                _score, src, depth = up
                src_med = step_meds[t][src]
                row.append(round(src_med[0], 4))
                notes.setdefault(
                    cell, f"stroomopwaarts peilgebied {nodes[src]['name']} "
                          f"(diepte {depth})")
            else:
                row.append(None)
        if any(v is not None for v in row):
            derived[cell] = row
    return {"derived": derived, "notes": notes}
