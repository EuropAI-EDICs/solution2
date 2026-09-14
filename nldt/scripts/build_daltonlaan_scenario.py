#!/usr/bin/env python3
"""Build simulation/building-scenario.json for Daltonlaan 100 (3D BAG + verbouwing).

Bestemmingsplan: cite-or-abstain corpus in simulation/corpus/ (POC-patroon).
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from pyproj import Transformer
from shapely.geometry import Polygon, shape

PAND_ID = "0344100000039220"
ADDRESS = "Daltonlaan 100, 3584BJ Utrecht"
CENTER_RD = (139375.636, 455479.709)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "simulation" / "building-scenario.json"
CORPUS = ROOT / "simulation" / "corpus"

to_wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)


def fetch_footprint_rd() -> tuple[list[list[float]], Polygon]:
    half = 50
    x, y = CENTER_RD
    bbox = f"{x - half},{y - half},{x + half},{y + half}"
    wfs = (
        "https://service.pdok.nl/lv/bag/wfs/v2_0?service=WFS&version=2.0.0"
        f"&request=GetFeature&typeName=bag:pand&bbox={bbox},EPSG:28992"
        "&outputFormat=application/json&count=50"
    )
    features = httpx.get(wfs, timeout=60).json()["features"]
    feat = next(f for f in features if f["properties"]["identificatie"] == PAND_ID)
    ring_rd = feat["geometry"]["coordinates"][0]
    return ring_rd, shape(feat["geometry"])


def fetch_3dbag_attrs(bbox: str) -> dict:
    bag_id = f"NL.IMBAG.Pand.{PAND_ID}"
    url = f"https://api.3dbag.nl/collections/pand/items?bbox={bbox}&limit=50"
    with httpx.Client(timeout=120) as client:
        data = client.get(url).json()
    for feature in data.get("features", []):
        if bag_id in feature.get("CityObjects", {}):
            return feature["CityObjects"][bag_id]["attributes"]
    raise RuntimeError(f"3D BAG pand {bag_id} niet gevonden in bbox {bbox}")


def ring_wgs(ring_rd: list[list[float]]) -> list[list[float]]:
    wgs = [[round(lo, 7), round(la, 7)] for lo, la in (to_wgs.transform(x, y) for x, y in ring_rd)]
    if wgs[0] != wgs[-1]:
        wgs.append(wgs[0])
    return wgs


def uitbouw_polygon(poly_wgs: Polygon) -> list[list[float]]:
    minx, miny, maxx, maxy = poly_wgs.bounds
    coords = list(poly_wgs.exterior.coords)
    south_edges: list[tuple[float, tuple[float, float], tuple[float, float], tuple[float, float]]] = []
    for i in range(len(coords) - 1):
        p1, p2 = coords[i], coords[i + 1]
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        length = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        if mid[1] < (miny + maxy) / 2 and length > 0.00003:
            south_edges.append((length, mid, p1, p2))
    south_edges.sort(reverse=True)
    _, _, p1, p2 = south_edges[0]
    depth_deg = 4.0 / 111_000
    edge_len = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    ux, uy = (p2[0] - p1[0]) / edge_len, (p2[1] - p1[1]) / edge_len
    hw = (12 / 111_000) / 2
    c1 = (mx - ux * hw, my - uy * hw)
    c2 = (mx + ux * hw, my + uy * hw)
    c3 = (c2[0], c2[1] - depth_deg)
    c4 = (c1[0], c1[1] - depth_deg)
    ring = [c1, c2, c3, c4, c1]
    return [[round(lo, 7), round(la, 7)] for lo, la in ring]


def load_corpus() -> tuple[list, dict]:
    normcards = json.loads((CORPUS / "normcards-building.json").read_text(encoding="utf-8"))
    decision_table = json.loads((CORPUS / "decision-table-building.json").read_text(encoding="utf-8"))
    return normcards, decision_table


def evaluate_scenario(attrs: dict, normcards: list, decision_table: dict) -> dict:
    h = float(attrs.get("b3_h_dak_max") or 0)
    max_h = 22.0  # aanduiding verbeelding (NC-BP-02 geoBinding caveat)
    bijgebouw_max_m2 = 100.0
    bijgebouw_max_h = 3.0
    proposed_bijgebouw_m2 = 24.0

    return {
        "dakopbouw": {
            "toegestaan": False,
            "normCardIds": ["NC-BP-02", "NC-BP-06"],
            "maxExtraM": 0,
            "tekst": f"Bouwhoogte ({h:.1f} m) op plafond aanduiding verbeelding ({max_h:.0f} m) — art. 15.2.1c",
        },
        "uitbouwAchter": {
            "toegestaan": False,
            "normCardIds": ["NC-BP-03"],
            "maxDiepteM": 0,
            "maxOppervlakM2": 0,
            "tekst": "Uitbouw vergroot BVO boven bestaand niveau — art. 15.2.1b (geen BVO-aanduiding op bouwvlak)",
        },
        "bijgebouw": {
            "toegestaan": proposed_bijgebouw_m2 <= bijgebouw_max_m2,
            "normCardIds": ["NC-BP-04"],
            "maxOppervlakM2": bijgebouw_max_m2,
            "maxHoogteM": bijgebouw_max_h,
            "tekst": f"Ondergeschikt gebouw buiten bouwvlak tot {bijgebouw_max_m2:.0f} m² / {bijgebouw_max_h:.0f} m — art. 15.2.1e",
        },
        "verdieping": {
            "toegestaan": False,
            "normCardIds": ["NC-BP-02"],
            "tekst": "Geen extra verdieping — bouwhoogte-plafond bereikt (art. 15.2.1c)",
        },
        "_meta": {
            "normCardCount": len(normcards),
            "decisionTableId": decision_table["id"],
        },
    }


def bestemmingsplan_block(decision_table: dict) -> dict:
    return {
        "plan": "Bestemmingsplan Rijnsweerd, Maarschalkerweerd",
        "planIdn": "NL.IMRO.0344.BPRIJNSMAARSCH-0401",
        "status": "vastgesteld, deels onherroepelijk in werking per 26-09-2013",
        "functie": "Kantoor - 1",
        "artikel": "art. 15.1 t/m 15.2",
        "maxBouwhoogteM": 22.0,
        "maxBouwhoogteBron": "aanduiding 'maximale bouwhoogte (m)' op verbeelding",
        "maxBvoRegel": "bestaand BVO (geen aparte BVO-aanduiding op bouwvlak)",
        "uri": "https://www.ruimtelijkeplannen.nl/web-roo/?planidn=NL.IMRO.0344.BPRIJNSMAARSCH-0401",
        "decisionTableId": decision_table["id"],
        "nota": "Geciteerde normen uit corpus; geen juridisch advies",
    }


def bijgebouw_polygon(poly_wgs: Polygon) -> list[list[float]]:
    minx, miny, maxx, maxy = poly_wgs.bounds
    depth_deg = 4.0 / 111_000
    bx = minx + (maxx - minx) * 0.15
    by = miny - depth_deg - 8 / 111_000
    bw, bh = 6 / 111_000, 4 / 111_000
    ring = [(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh), (bx, by)]
    return [[round(lo, 7), round(la, 7)] for lo, la in ring]


def main() -> int:
    ring_rd, poly_rd = fetch_footprint_rd()
    half = 50
    x, y = CENTER_RD
    bbox = f"{x - half},{y - half},{x + half},{y + half}"
    attrs = fetch_3dbag_attrs(bbox)
    footprint = ring_wgs(ring_rd)
    poly_wgs = Polygon([(lo, la) for lo, la in footprint[:-1]])
    center = poly_wgs.centroid

    normcards, decision_table = load_corpus()
    scenario_eval = evaluate_scenario(attrs, normcards, decision_table)
    scenario_eval.pop("_meta", None)

    scenario = {
        "bagId": f"NL.IMBAG.Pand.{PAND_ID}",
        "label": "Daltonlaan 100 — 3D BAG pand",
        "address": ADDRESS,
        "center_wgs84": {"lon": round(center.x, 8), "lat": round(center.y, 8)},
        "center_rd": [round(poly_rd.centroid.x, 1), round(poly_rd.centroid.y, 1)],
        "footprint_wgs84": footprint,
        "uitbouw_wgs84": uitbouw_polygon(poly_wgs),
        "bijgebouw_wgs84": bijgebouw_polygon(poly_wgs),
        "properties": {
            "b3_h_maaiveld": attrs.get("b3_h_maaiveld"),
            "b3_h_dak_max": attrs.get("b3_h_dak_max"),
            "b3_h_nok": attrs.get("b3_h_nok"),
            "b3_volume_lod22": attrs.get("b3_volume_lod22"),
            "b3_opp_grond": attrs.get("b3_opp_grond"),
            "b3_dak_type": attrs.get("b3_dak_type"),
            "b3_bouwlagen": attrs.get("b3_bouwlagen"),
            "oorspronkelijkbouwjaar": 1996,
        },
        "bestemmingsplan": bestemmingsplan_block(decision_table),
        "normcards": normcards,
        "decisionTable": decision_table,
        "volumes": {
            "uitbouw": {"heightM": 4.0, "color": "#3fb950", "alpha": 0.45},
            "bijgebouw": {"heightM": 3.0, "color": "#a371f7", "alpha": 0.75},
        },
        "scenario": scenario_eval,
        "tiles_lod22": "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json",
    }
    OUT.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    print(f"Geschreven: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
