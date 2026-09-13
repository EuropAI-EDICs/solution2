"""Synthetische RD-fixtures voor de offline tests van de Breda-vijf-waardenscan.

12×10 grid van 1×1 km-cellen (EPSG:28992) rond x=115000, y=400000: 108 buurten
(> de V1-volumecheck) waarvan de onderste 2 rijen water-buurten zijn. Statistiek-
velden volgen de CBS-sentinelconventie (-99997 = onbekend) zodat het
missing-beleid op de proef wordt gesteld.
"""

from __future__ import annotations

import math

X0, Y0 = 115000.0, 400000.0
CELL = 1000.0
COLS, ROWS = 12, 10


def _square(x, y, size=CELL):
    return {
        "type": "Polygon",
        "coordinates": [[[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]]],
    }


def _props(i, j, water):
    code = f"BU0758{(j * COLS + i):04d}"
    if water:
        stats = {
            "aantalInwoners": -99997,
            "percentagePersonen65JaarEnOuder": -99997,
            "afstandTotOpenbaarGroenTotaal": -99997,
            "groteSupermarktGemiddeldeAfstandInKm": -99997,
            "huisartsenpraktijkGemiddeldeAfstandInKm": -99997,
            "basisonderwijsGemiddeldeAfstandInKm": -99997,
            "kinderdagverblijfGemiddeldeAfstandInKm": -99997,
            "bibliotheekGemiddeldeAfstandInKm": -99997,
            "treinstationGemiddeldeAfstandInKm": -99997,
            "percentageWoningenMetZonnestroom": -99997,
            "percentageEengezinswoning": -99997,
            "oppervlakteLandInHa": 0,
        }
    else:
        # deterministische 'realistische' variatie per cel
        d = lambda base, amp: round(base + amp * math.sin(i * 2.1 + j * 1.3), 3)
        stats = {
            "aantalInwoners": int(800 + 400 * ((i * 7 + j * 3) % 12)),
            "percentagePersonen65JaarEnOuder": d(17, 6),
            "afstandTotOpenbaarGroenTotaal": d(0.9, 0.6),
            "huisartsenpraktijkGemiddeldeAfstandInKm": d(1.1, 0.7),
            "groteSupermarktGemiddeldeAfstandInKm": d(1.0, 0.8),
            "basisonderwijsGemiddeldeAfstandInKm": d(0.8, 0.5),
            "kinderdagverblijfGemiddeldeAfstandInKm": d(1.2, 0.6),
            "bibliotheekGemiddeldeAfstandInKm": d(2.0, 1.2),
            "treinstationGemiddeldeAfstandInKm": d(2.5, 1.5),
            "percentageWoningenMetZonnestroom": d(14, 9),
            "percentageEengezinswoning": d(55, 25),
            "oppervlakteLandInHa": 100,
        }
    bedrijven = {} if water else {
        "aantalBedrijvenHandelEnHoreca": 40 + (i * 3 + j) % 25,
        "aantalBedrijvenZakelijkeDienstverlening": 30 + (i + j * 2) % 20,
    }
    return {
        "buurtcode": code,
        "buurtnaam": f"Cel {i}-{j}",
        "wijkcode": f"WK0758{j:02d}",
        "gemeentecode": "GM0758",
        "gemeentenaam": "Breda",
        "water": "JA" if water else "NEE",
        **stats,
        **bedrijven,
    }


def buurten_fc() -> dict:
    feats = []
    for j in range(ROWS):
        for i in range(COLS):
            water = j >= ROWS - 2
            feats.append(
                {"type": "Feature", "properties": _props(i, j, water),
                 "geometry": _square(X0 + i * CELL, Y0 + j * CELL)}
            )
    return {"type": "FeatureCollection", "crs": {"type": "name",
            "properties": {"name": "EPSG:28992"}}, "features": feats}


def wijkdeals_fc() -> dict:
    # 6 kleine deals in drie cellen linksboven
    feats = []
    for k in range(6):
        x = X0 + (k % 3) * CELL + 100 + 30 * k
        y = Y0 + (k // 3) * CELL + 100
        feats.append({"type": "Feature",
                      "properties": {"identificatie": f"deal-{k}"},
                      "geometry": _square(x, y, 40)})
    return {"type": "FeatureCollection", "features": feats}


def hoofdgroenstructuur_fc() -> dict:
    # één baan over de linkerhelft van het grid (6 kolommen breed)
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": 1},
         "geometry": {
             "type": "Polygon",
             "coordinates": [[[X0, Y0], [X0 + 6 * CELL, Y0], [X0 + 6 * CELL, Y0 + ROWS * CELL],
                              [X0, Y0 + ROWS * CELL], [X0, Y0]]],
         }},
    ]}


def verharding_fc() -> dict:
    # twee vlakken: bovenste helft 75% verhard, onderste 35%
    half = ROWS * CELL / 2
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"P_verhard": 75, "id": 1},
         "geometry": {
             "type": "Polygon",
             "coordinates": [[[X0, Y0 + half], [X0 + COLS * CELL, Y0 + half],
                              [X0 + COLS * CELL, Y0 + ROWS * CELL],
                              [X0, Y0 + ROWS * CELL], [X0, Y0 + half]]],
         }},
        {"type": "Feature", "properties": {"P_verhard": 35, "id": 2},
         "geometry": {
             "type": "Polygon",
             "coordinates": [[[X0, Y0], [X0 + COLS * CELL, Y0],
                              [X0 + COLS * CELL, Y0 + half], [X0, Y0 + half], [X0, Y0]]],
         }},
    ]}


def kansenkaart_fc() -> dict:
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"OMSCHRIJV": "Groene klimaatas",
                                           "WIJK": "WK075800"},
         "geometry": _square(X0 + 2 * CELL, Y0 + 2 * CELL, 2 * CELL)},
        {"type": "Feature", "properties": {"OMSCHRIJV": "Waterberging",
                                           "WIJK": "WK075801"},
         "geometry": _square(X0 + 8 * CELL, Y0 + 3 * CELL, 1.5 * CELL)},
    ]}


def bomen_fc() -> dict:
    feats = []
    n = 0
    for j in range(ROWS - 2):
        for i in range(COLS):
            for t in range(4 + (i + j) % 3):  # 4–6 bomen per landcel
                feats.append({
                    "type": "Feature", "properties": {"id": n},
                    "geometry": {"type": "Point",
                                 "coordinates": [X0 + i * CELL + 100 + 90 * t,
                                                 Y0 + j * CELL + 200]},
                })
                n += 1
    return {"type": "FeatureCollection", "features": feats}


def layers_dict(include_bomen=True) -> dict:
    return {
        "buurten": buurten_fc(),
        "gemeentegrens": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {}, "geometry": {
                "type": "Polygon",
                "coordinates": [[[X0, Y0], [X0 + COLS * CELL, Y0],
                                 [X0 + COLS * CELL, Y0 + ROWS * CELL],
                                 [X0, Y0 + ROWS * CELL], [X0, Y0]]],
            }},
        ]},
        "wijkdeals": wijkdeals_fc(),
        "hoofdgroenstructuur": hoofdgroenstructuur_fc(),
        "verharding": verharding_fc(),
        "kansenkaart": kansenkaart_fc(),
        **({"bomen": bomen_fc()} if include_bomen else {}),
    }
