"""Synthetische lagen voor offline tests — geen netwerk, volledig deterministisch."""

from __future__ import annotations

import json

AOI_POLY = [[100000.0, 400000.0], [100500.0, 400000.0], [100500.0, 400500.0], [100000.0, 400500.0], [100000.0, 400000.0]]

AOI_FC = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
    "features": [{
        "type": "Feature",
        "properties": {"naam": "testplangrens"},
        "geometry": {"type": "Polygon", "coordinates": [AOI_POLY]},
    }],
}


def _poly(x, y, w=50.0, h=50.0):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]]}


def _point(x, y):
    return {"type": "Point", "coordinates": [x, y]}


def _line(x0, y0, x1, y1):
    return {"type": "LineString", "coordinates": [[x0, y0], [x1, y1]]}


def _fc(features):
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
        "features": features,
    }


def layers() -> dict[str, dict]:
    """key = '<serviceId>::<collection|typeName>' → synthetic FeatureCollection."""
    L = {}
    # BGT
    L["pdok-bgt-ogc-api::wegdeel"] = _fc([
        {"type": "Feature", "properties": {"functie": "rijbaan lokale weg"}, "geometry": _poly(100050, 400050, 200, 40)},
        {"type": "Feature", "properties": {"functie": "voetpad"}, "geometry": _poly(100300, 400300, 30, 100)},
        {"type": "Feature", "properties": {"functie": "rijbaan regionale weg", "eind_registratie": "2020-01-01T00:00:00Z"},
         "geometry": _poly(100400, 400400, 60, 60)},  # historisch → weggefilterd
    ])
    L["pdok-bgt-ogc-api::waterdeel"] = _fc([
        {"type": "Feature", "properties": {}, "geometry": _poly(100000, 400000, 80, 80)},
    ])
    L["pdok-bgt-ogc-api::begroeidterreindeel"] = _fc([
        {"type": "Feature", "properties": {"fysiek_voorkomen": "groenvoorziening"}, "geometry": _poly(100100, 400100, 100, 100)},
    ])
    L["pdok-bgt-ogc-api::onbegroeidterreindeel"] = _fc([
        # live-BGT-vorm: functie leeg, fysiek_voorkomen dragt de classificatie
        {"type": "Feature", "properties": {"functie": None, "fysiek_voorkomen": "gesloten verharding"}, "geometry": _poly(100200, 400050, 100, 50)},
        {"type": "Feature", "properties": {"functie": None, "fysiek_voorkomen": "onverhard"}, "geometry": _poly(100350, 400150, 40, 40)},
        {"type": "Feature", "properties": {"functie": "verhard", "fysiek_voorkomen": None}, "geometry": _poly(100420, 400200, 30, 30)},
    ])
    L["pdok-bgt-ogc-api::overbruggingsdeel"] = _fc([
        {"type": "Feature", "properties": {}, "geometry": _poly(100010, 400010, 20, 20)},
    ])
    # BAG
    L["pdok-bag-wfs::bag:pand"] = _fc([
        {"type": "Feature", "properties": {"identificatie": "P1", "bouwjaar": 1972, "status": "Pand in gebruik"}, "geometry": _poly(100050, 400050, 30, 30)},
        {"type": "Feature", "properties": {"identificatie": "P2", "bouwjaar": 2005, "status": "Pand in gebruik"}, "geometry": _poly(100100, 400050, 30, 30)},
    ])
    L["pdok-bag-wfs::bag:verblijfsobject"] = _fc([
        {"type": "Feature", "properties": {"identificatie": "V1", "oppervlakte": 120, "gebruiksdoel": "woonfunctie",
                                           "openbare_ruimte": "Dorpsstraat", "huisnummer": 1, "postcode": "1234 AB"},
         "geometry": _point(100060, 400060)},
        {"type": "Feature", "properties": {"identificatie": "V2", "oppervlakte": 80, "gebruiksdoel": "kantoorfunctie",
                                           "openbare_ruimte": "Dorpsstraat", "huisnummer": 2, "postcode": "1234 AB"},
         "geometry": _point(100110, 400060)},
        {"type": "Feature", "properties": {"identificatie": "V3", "oppervlakte": 60, "gebruiksdoel": "woonfunctie",
                                           "openbare_ruimte": "Verweg", "huisnummer": 99},
         "geometry": _point(99000, 39000)},  # buiten plangrens
    ])
    # Kadaster
    L["pdok-brk-kadastrale-kaart::perceel"] = _fc([
        {"type": "Feature", "properties": {"kadastraleGemeente": "Test", "sectie": "A", "perceelnummer": 100},
         "geometry": _poly(100000, 400000, 250, 250)},
    ])
    # CBS (wijk-/buurtstatistiek rond de plangrens)
    L["pdok-cbs-wijkenbuurten-2024::wijkenbuurten:buurten"] = _fc([
        {"type": "Feature", "properties": {"buurtnaam": "Testbuurt", "aantalInwoners": 400, "gemiddeldeWoningwaarde": 350},
         "geometry": _poly(99950, 399950, 600, 600)},
    ])
    # Natura 2000: dichtstbijzijnde gebied ±2,5 km ten noorden van de plangrens
    L["pdok-natura2000::natura2000"] = _fc([
        {"type": "Feature", "properties": {"naam": "Test N2000"}, "geometry": _poly(100000, 403000, 400, 400)},
    ])
    # NWB
    L["pdok-nwb-wegen::wegvakken"] = _fc([
        {"type": "Feature", "properties": {"wegnaam": "Provincialeweg"}, "geometry": _line(100000, 400100, 100500, 400100)},
    ])
    # RCE
    L["pdok-rce-cultuurhistorie::rce_inspire_points"] = _fc([
        {"type": "Feature", "properties": {"ci_citation": "https://monumentenregister.cultureelerfgoed.nl/monumenten/1"},
         "geometry": _point(100020, 400020)},
    ])
    # Breda-lagen (arcgis)
    L["breda-milieuzones::"] = _fc([{"type": "Feature", "properties": {"IDENTIFICATIE": "1"}, "geometry": _poly(99900, 399900, 100, 100)}])
    L["breda-geluidcontouren::"] = _fc([{"type": "Feature", "properties": {"LOW_VAL": 50}, "geometry": _poly(100040, 400040, 100, 100)}])
    L["breda-cultuurhistorie::"] = _fc([{"type": "Feature", "properties": {"WAARDE": "hoog"}, "geometry": _poly(100080, 400080, 60, 60)}])
    L["breda-archeologie::"] = _fc([{"type": "Feature", "properties": {"identificatie": "A1"}, "geometry": _poly(100120, 400120, 70, 70)}])
    return L


def fake_fetch_layer_factory(store: dict[str, dict] | None = None):
    """Bouwt een fetch_layer-stub met dezelfde signatuur als minigim.fetch.fetch_layer."""
    store = store if store is not None else layers()

    def fake_fetch_layer(source, bbox=None, refresh=False, cbs_filter=None):
        sid = source["id"]
        coll = ""
        if source["protocol"] == "ogc-api-features":
            coll = (source.get("collections") or [""])[0]
        elif source["protocol"] == "wfs2":
            coll = (source.get("typeNames") or [source.get("typeName") or ""])[0]
        key = f"{sid}::{coll}"
        if key not in store:
            raise RuntimeError(f"geen synthetic layer voor {key}")
        fc = json.loads(json.dumps(store[key]))  # deep copy
        manifest = {
            "protocol": source["protocol"], "urls": [f"https://example.test/{key}"],
            "pages": 1, "fetchedAt": "2026-09-21T00:00:00Z",
            "sha256": ["0" * 64], "featureCount": len(fc["features"]), "sourceId": sid,
        }
        return fc, manifest

    return fake_fetch_layer
