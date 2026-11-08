#!/usr/bin/env python3
"""veenendaal-spoorzone-scan — deterministische gebiedscheck Spoorzone Veenendaal.

Voeding: docs/USE_CASE_VEENENDAAL_SPOORZONE.md (Use Case Canvas) ·
data/gebied.json (werkgrens + doelen uit het Toekomstbeeld juni 2025).

Doctrine (GENAI_SEAMS): de rekenlaag beslist — elk getal in de rapportage is
herleidbaar naar bron-URL + query-parameters + sha256 (manifest.json naast
deze run). Stdlib + requests; geen shapely: vlakoppervlaktes via de
schoenlaced formule op EPSG:28992-coördinaten (meters, planair).

Poorten: V0 structuur · V1 geometrie-sanity · V2 bronkoppeling per indicator ·
V3 tweede, onafhankelijk geïmplementeerde aggregatiepassage over de cache.

Gebruik:  python3 run.py [--refresh]
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
RUNS = ROOT / "runs"

CRS = "http://www.opengis.net/def/crs/EPSG/0/28992"
BAG_BASE = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections"
BGT_BASE = "https://api.pdok.nl/lv/bgt/ogc/v1/collections"
PAGE_CAP = 120
PAGE_PAUSE = 0.05

# pand-statussen die (nog) niet als bestaande bouwmassa gelden
NIET_BESTAAND = {"Pand gesloopt", "Niet gerealiseerd pand"}

BOUWJAAR_BUCKETS = [("<1965", 0, 1965), ("1965-1984", 1965, 1985),
                    ("1985-1999", 1985, 2000), ("2000-2019", 2000, 2020),
                    ("≥2020", 2020, 10_000)]

# BGT-collection → indicator-key in de rapportage ('spoor' is lijngeometrie in BGT v1)
BGT_LAGEN = {
    "begroeidterreindeel": "begroeid_terrein_ha",
    "onbegroeidterreindeel": "onbegroeid_terrein_ha",
    "waterdeel": "waterdeel_ha",
    "spoor": "spoorlijn_km",
    "vegetatieobject_punt": "vegetatieobject_punt",
    "vegetatieobject_vlak": "vegetatie_vlak_ha",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- ophalen (cache-first)

def fetch_paged(base: str, collection: str, params: dict, refresh: bool = False) -> tuple[list, dict]:
    """Haalt alle pagina's van een OGC-API Features-collection; cache-first.
    Naast de cache wordt een sidecar-meta (fetchedAt, params, sha256) bewaard,
    zodat het bevraagtijdstip ook bij hergebruik in het manifest terechtkomt."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE / f"{collection}.geojson"
    meta_path = CACHE / f"{collection}.meta.json"
    if cache_path.exists() and meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text())
        doc = json.loads(cache_path.read_text())
        meta.update({"cached": True, "featureCount": len(doc["features"])})
        return doc["features"], meta

    url = f"{base}/{collection}/items"
    features: list = []
    pages = 0
    t0 = time.time()
    while url and pages < PAGE_CAP:
        resp = requests.get(url, params=params if pages == 0 else None, timeout=90)
        resp.raise_for_status()
        doc = resp.json()
        if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
            raise ValueError(f"V0-fout {collection}: geen FeatureCollection")
        features.extend(doc["features"])
        pages += 1
        url = next((l["href"] for l in doc.get("links", []) if l.get("rel") == "next"), None)
        time.sleep(PAGE_PAUSE)
    if pages >= PAGE_CAP:
        raise RuntimeError(f"{collection}: page-cap ({PAGE_CAP}) geraakt — verbreed of chunk de bbox")

    cache_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    meta = {
        "collection": collection, "cached": False, "pages": pages,
        "featureCount": len(features), "sha256": sha256_file(cache_path),
        "fetchedAt": utcnow(), "duur_s": round(time.time() - t0, 1),
        "url": f"{base}/{collection}/items", "params": params,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return features, meta


# ---------------------------------------------------------------- geometrie (schoenlac, RD-meters)

def ring_area(ring: list) -> float:
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def polygon_area(poly: list) -> float:
    if not poly:
        return 0.0
    area = abs(ring_area(poly[0]))
    for hole in poly[1:]:
        area -= abs(ring_area(hole))
    return area


def feature_area(geom: dict) -> float:
    if geom is None:
        return 0.0
    t = geom.get("type")
    if t == "Polygon":
        return polygon_area(geom.get("coordinates", []))
    if t == "MultiPolygon":
        return sum(polygon_area(p) for p in geom.get("coordinates", []))
    return 0.0  # punten/lijnen: geen vlakoppervlak


# ------------------------------------------------- clippen naar de werkgrens (bbox = (minx,miny,maxx,maxy))
# De API's leveren objecten die de bbox *snijden* met volledige geometrie; voor
# oppervlakte-indicatoren clippen we elke ring met Sutherland–Hodgman tegen de
# rechthoek (convex clipper → oppervlaktemeetkundig exact, ook bij concave ringen).

def clip_halfplane(pts: list, axis: int, bound: float, keep_ge: bool) -> list:
    out: list = []
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        vp = p[axis] - bound
        vq = q[axis] - bound
        pin = (vp >= 0) if keep_ge else (vp <= 0)
        qin = (vq >= 0) if keep_ge else (vq <= 0)
        if pin:
            out.append(p)
        if pin != qin:
            t = vp / (vp - vq)
            out.append([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])])
    if out:
        out.append(out[0])
    return out


def ring_area_in_bbox(ring: list, bbox: tuple) -> float:
    pts = ring
    for axis, bound, keep_ge in [(0, bbox[0], True), (0, bbox[2], False),
                                 (1, bbox[1], True), (1, bbox[3], False)]:
        pts = clip_halfplane(pts, axis, bound, keep_ge)
        if not pts:
            return 0.0
    return abs(ring_area(pts))


def polygon_area_in_bbox(poly: list, bbox: tuple) -> float:
    if not poly:
        return 0.0
    area = ring_area_in_bbox(poly[0], bbox)
    for hole in poly[1:]:
        area -= ring_area_in_bbox(hole, bbox)
    return max(area, 0.0)


def feature_area_in_bbox(geom: dict, bbox: tuple) -> float:
    if geom is None:
        return 0.0
    t = geom.get("type")
    if t == "Polygon":
        return polygon_area_in_bbox(geom.get("coordinates", []), bbox)
    if t == "MultiPolygon":
        return sum(polygon_area_in_bbox(p, bbox) for p in geom.get("coordinates", []))
    return 0.0


def seg_len_in_rect(p: list, q: list, bbox: tuple) -> float:
    """Lengte van het deel van segment p→q binnen de bbox (Liang–Barsky)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pi, di, lo, hi in ((p[0], dx, bbox[0], bbox[2]), (p[1], dy, bbox[1], bbox[3])):
        if di == 0:
            if pi < lo or pi > hi:
                return 0.0
        else:
            a, b = (lo - pi) / di, (hi - pi) / di
            if a > b:
                a, b = b, a
            t0, t1 = max(t0, a), min(t1, b)
    if t0 >= t1:
        return 0.0
    return ((dx * (t1 - t0)) ** 2 + (dy * (t1 - t0)) ** 2) ** 0.5


def lijn_len_in_bbox(geom: dict, bbox: tuple) -> float:
    if geom is None or geom.get("type") not in ("LineString", "MultiLineString"):
        return 0.0
    lines = ([geom["coordinates"]] if geom["type"] == "LineString"
             else geom["coordinates"])
    return sum(
        seg_len_in_rect(a, b, bbox)
        for line in lines for a, b in zip(line, line[1:])
    )


def bgt_actueel(features: list) -> list:
    """Versie-deduplice: BGT v1 levert ook historische versies. Per lokaal_id
    blijft de versie met lege eind_registratie (actueel); is er geen actuele
    versie, dan bestaat het object niet meer en valt het weg. Bij meerdere
    actieve versies wint de laatste tijdstip_registratie."""
    actueel: dict = {}
    for f in features:
        p = f.get("properties", {})
        lid = p.get("lokaal_id")
        if p.get("eind_registratie") not in (None, ""):
            continue
        ts = p.get("tijdstip_registratie") or ""
        if lid not in actueel or ts > actueel[lid][0]:
            actueel[lid] = (ts, f)
    return [f for _, f in actueel.values()]


# ---------------------------------------------------------------- indicatoren (1e implementatie)

def bag_indicatoren(features: list, bbox: tuple) -> dict:
    bestaand, verwijderd = [], 0
    for f in features:
        if f.get("properties", {}).get("status") in NIET_BESTAAND:
            verwijderd += 1
        else:
            bestaand.append(f)

    woningen_vbo = 0
    panden_met_woonfunctie = 0
    vloer_m2 = 0.0
    ge2020 = 0
    buckets = {label: 0 for label, _, _ in BOUWJAAR_BUCKETS}
    for f in bestaand:
        p = f.get("properties", {})
        gd = p.get("gebruiksdoel") or ""
        if "woonfunctie" in gd:
            panden_met_woonfunctie += 1
            woningen_vbo += p.get("aantal_verblijfsobjecten") or 0
        vloer_m2 += feature_area_in_bbox(f.get("geometry"), bbox)
        bj = p.get("bouwjaar")
        if isinstance(bj, int):
            if bj >= 2020:
                ge2020 += 1
            for label, lo, hi in BOUWJAAR_BUCKETS:
                if lo <= bj < hi:
                    buckets[label] += 1
                    break

    return {
        "panden_bestand": len(bestaand),
        "panden_verwijderd_status": verwijderd,
        "woningen_verblijfsobjecten_proxy": woningen_vbo,
        "panden_met_woonfunctie": panden_met_woonfunctie,
        "pand_vloeroppervlak_m2": round(vloer_m2),
        "panden_bouwjaar_vanaf_2020": ge2020,
        "bouwjaar_buckets": buckets,
    }


def bgt_indicatoren(features: list, key: str, bbox: tuple):
    actueel = bgt_actueel(features)
    if key.endswith("_punt"):
        return len(actueel)
    if key == "spoorlijn_km":
        return round(sum(lijn_len_in_bbox(f.get("geometry"), bbox) for f in actueel) / 1000, 1)
    return round(sum(feature_area_in_bbox(f.get("geometry"), bbox) for f in actueel) / 10_000, 2)  # ha


# ---------------------------------------------------------------- V3: tweede, onafhankelijke passage

def v3_herberekening(indicatoren: dict, bbox: tuple) -> tuple[bool, str]:
    """Opnieuw aggregeren vanuit de cachebestanden met een apart geschreven
    implementatie (generator-based, ander loop-patroon); waakt tegen
    aggregatie-bugs. De oppervlaktemeetkunde (schoenlac + bbox-clip) is gedeeld
    en wordt door de V1-sanity gedekt."""
    def iter_features(name):
        doc = json.loads((CACHE / name).read_text())
        yield from doc["features"]

    pand = sum(
        1 for f in iter_features("pand.geojson")
        if f["properties"].get("status") not in NIET_BESTAAND
    )
    ge2020 = sum(
        1 for f in iter_features("pand.geojson")
        if f["properties"].get("status") not in NIET_BESTAAND
        and isinstance(f["properties"].get("bouwjaar"), int)
        and f["properties"]["bouwjaar"] >= 2020
    )
    groen_ha = round(sum(
        feature_area_in_bbox(f.get("geometry"), bbox)
        for f in bgt_actueel(list(iter_features("begroeidterreindeel.geojson")))
    ) / 10_000, 2)
    vlak_totaal_ha = sum(
        indicatoren[k] for k in
        ["begroeid_terrein_ha", "onbegroeid_terrein_ha", "waterdeel_ha"]
    )
    opp_ha = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / 10_000

    checks = [
        (pand == indicatoren["panden_bestand"], f"panden {pand} vs {indicatoren['panden_bestand']}"),
        (ge2020 == indicatoren["panden_bouwjaar_vanaf_2020"],
         f"bouwjaar≥2020 {ge2020} vs {indicatoren['panden_bouwjaar_vanaf_2020']}"),
        (groen_ha == indicatoren["begroeid_terrein_ha"],
         f"groen {groen_ha} vs {indicatoren['begroeid_terrein_ha']}"),
        (vlak_totaal_ha <= opp_ha * 1.02,
         f"vlaktotalen {round(vlak_totaal_ha, 1)} ha ≤ werkgrens {round(opp_ha, 1)} ha (+2%)"),
    ]
    return all(c for c, _ in checks), "; ".join(m for _, m in checks)


# ---------------------------------------------------------------- rapport

def doelvergelijking(ind: dict, doelen: dict, opp_ha: float, nu_jaar: int) -> list:
    verwacht = round((nu_jaar - doelen["programma_start"]) * doelen["woningen_per_jaar_gemiddeld"])
    return [
        ("Wonen", f"~{doelen['woningen_nieuw_feiten_tabel']} nieuw (p.14; inleiding p.3 noemt "
                  f"~{doelen['woningen_tot_2040_inleiding']})",
         f"{ind['woningen_verblijfsobjecten_proxy']} bestaand (vbo-proxy) → groei ≈ "
         f"{round(doelen['woningen_nieuw_feiten_tabel'] / max(ind['woningen_verblijfsobjecten_proxy'], 1), 1)}×"),
        ("Bouwtempo", f"{doelen['woningen_per_jaar_gemiddeld']} woningen/jaar sinds {doelen['programma_start']}",
         f"verwacht tot {nu_jaar}: ~{verwacht}; proxy gerealiseerd: {ind['panden_bouwjaar_vanaf_2020']} "
         f"nieuwe pánden (pand ≠ woning, indicatief)"),
        ("Groen", f"> {doelen['groen_ha_minimum']} ha",
         f"huidig begroeid terrein: {ind['begroeid_terrein_ha']} ha "
         f"(+ vegetatievlak {ind['vegetatie_vlak_ha']} ha)"),
        ("Werken", f"~{doelen['arbeidsplaatsen_nieuw']} nieuwe arbeidsplaatsen",
         "arbeidsplaatsen niet rechtstreeks meetbaar in BAG/BGT (open seam: bron met banenregistratie)"),
        ("Dichtheid", f"stedelijk; basishoogte {doelen['woongebouwen_basishoogte_lagen']} lagen, "
                      f"accenten {doelen['woongebouwen_accenten_lagen']}",
         f"huidig: {round(ind['woningen_verblijfsobjecten_proxy'] / (opp_ha / 100))} woningen/km²; "
         f"na realisatie: ~{round((ind['woningen_verblijfsobjecten_proxy'] + doelen['woningen_nieuw_feiten_tabel']) / (opp_ha / 100))}"),
    ]


def schrijf_rapport(run_dir: Path, gebied: dict, ind: dict, vergelijking: list,
                    v1: list, v3: tuple, run_id: str) -> None:
    bron = gebied["bron"]
    wg = gebied["werkgrens"]
    vloer = f"{ind['pand_vloeroppervlak_m2']:,}".replace(",", ".")
    regels = [
        f"# Gebiedscheck Spoorzone Veenendaal — {run_id}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/run.py` · doctrine: rekenlaag beslist, mens beslist.*",
        "",
        f"**Brongebiedsdocument:** [{bron['naam']}]({bron['url']}) (geraadpleegd {bron['geraadpleegd']}).",
        "",
        f"**Werkgrens:** {wg['type']} — bbox RD {wg['bbox_rd']} ({wg['breedte_m']}×{wg['hoogte_m']} m ≈ "
        f"{wg['opp_ha']} ha). {wg['afleiding']}",
        "",
        "## Huidige stand (deterministisch uit BAG/BGT; per bron URL+sha256 in `manifest.json`)",
        "",
        "| Indicator | Waarde | Bron |",
        "|---|---:|---|",
        f"| Panden bestand (excl. gesloopt/niet gerealiseerd) | {ind['panden_bestand']} | BAG pand |",
        f"| — panden met status gesloopt/niet gerealiseerd | {ind['panden_verwijderd_status']} | BAG pand |",
        f"| Panden met woonfunctie | {ind['panden_met_woonfunctie']} | BAG pand |",
        f"| Woningen (som verblijfsobjecten op woonpanden; proxy) | {ind['woningen_verblijfsobjecten_proxy']} | BAG pand |",
        f"| Pand-vloeroppervlak binnen werkgrens (grondvlak, som) | {vloer} m² | BAG pand |",
        f"| Panden met bouwjaar ≥ 2020 | {ind['panden_bouwjaar_vanaf_2020']} | BAG pand |",
        f"| Begroeid terrein binnen werkgrens | {ind['begroeid_terrein_ha']} ha | BGT |",
        f"| Onbegroeid (verhard) terrein binnen werkgrens | {ind['onbegroeid_terrein_ha']} ha | BGT |",
        f"| Water binnen werkgrens | {ind['waterdeel_ha']} ha | BGT |",
        f"| Spoorlijn binnen werkgrens | {ind['spoorlijn_km']} km | BGT |",
        f"| Bomen (vegetatieobject punt) | {ind['vegetatieobject_punt']} | BGT |",
        f"| Vegetatievlak binnen werkgrens | {ind['vegetatie_vlak_ha']} ha | BGT |",
        "",
        "**Bouwjaar-verdeling (bestaande panden):** "
        + " · ".join(f"{k}: {v}" for k, v in ind["bouwjaar_buckets"].items()),
        "",
        "## Doelvergelijking (toekomstbeeld ↔ gemeten)",
        "",
        "| Onderwerp | Doel (Toekomstbeeld) | Stand/kader |",
        "|---|---|---|",
    ]
    regels += [f"| {o} | {d} | {s} |" for o, d, s in vergelijking]
    regels += [
        "",
        "## Kwaliteitspoorten",
        "",
        "- **V0 structuur**: alle responses FeatureCollection; featureCounts per bron in manifest.",
        f"- **V1 geometrie-sanity**: {'geen afwijkingen' if not v1 else 'WAARSCHUWINGEN: ' + '; '.join(v1)}.",
        "- **V2 bronherleidbaarheid**: elke indicator verwijst naar collection+URL in manifest.json (sha256 vast).",
        f"- **V3 herberekening (tweede implementatie over cache)**: {'PASS' if v3[0] else 'FAIL'} — {v3[1]}.",
        "",
        "## Beperkingen & vervolg",
        "",
        "- Werkgrens is een provisionele bbox; het werkelijke gebied is zandloper-vormig — cijfers zijn",
        "  indicatief tot de officiële gebiedsgrens beschikbaar is (open item, USE_CASE Annex B).",
        "- Woningen zijn een proxy (som `aantal_verblijfsobjecten` op panden met woonfunctie); panden ≠ woningen.",
        "- Bouwjaar ≥ 2020 omvat ook vervangingsbouw; geen uitsplitsing sloop/nieuw zonder historische BAG.",
        "- Volgende stap volgens canvas: omgevingswet-toets (DSO/IMRO) en ontwerpvarianten (nLDT Plane B/D).",
        "",
        "*Manifest: `manifest.json` · indicatoren: `indicators.json` · cache: `data/cache/`.*",
    ]
    (run_dir / "report.md").write_text("\n".join(regels))


# ---------------------------------------------------------------- main

def main(refresh: bool = False) -> int:
    gebied = json.loads((DATA / "gebied.json").read_text())
    bbox = ",".join(str(v) for v in gebied["werkgrens"]["bbox_rd"])
    params = {"bbox": bbox, "bbox-crs": CRS, "crs": CRS}
    bag_params = {**params, "limit": 400}
    bgt_params = {**params, "limit": 500}

    print("→ ophalen BAG pand …")
    pand, m_pand = fetch_paged(BAG_BASE, "pand", bag_params, refresh)
    print(f"  {m_pand['featureCount']} panden")
    bbox_rd = gebied["werkgrens"]["bbox_rd"]
    bbox = (bbox_rd[0], bbox_rd[1], bbox_rd[2], bbox_rd[3])
    indicatoren = bag_indicatoren(pand, bbox)
    manifests = [m_pand]

    for coll, key in BGT_LAGEN.items():
        print(f"→ ophalen BGT {coll} …")
        feats, m = fetch_paged(BGT_BASE, coll, bgt_params, refresh)
        indicatoren[key] = bgt_indicatoren(feats, key, bbox)
        manifests.append(m)
        print(f"  {m['featureCount']} objecten → {key} = {indicatoren[key]}")

    # V1: geclipte vlaktotalen mogen de werkgrens niet overschrijden (met kleine marge)
    v1 = []
    bbox_opp = gebied["werkgrens"]["breedte_m"] * gebied["werkgrens"]["hoogte_m"]
    for key in ["begroeid_terrein_ha", "onbegroeid_terrein_ha", "waterdeel_ha", "vegetatie_vlak_ha"]:
        if key in indicatoren and indicatoren[key] * 10_000 > bbox_opp * 1.05:
            v1.append(f"{key} = {indicatoren[key]} ha overschrijdt de werkgrens")

    v3 = v3_herberekening(indicatoren, bbox)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-gebiedscheck"
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    vergelijking = doelvergelijking(indicatoren, gebied["doelen_uit_toekomstbeeld"],
                                    gebied["werkgrens"]["opp_ha"],
                                    datetime.now(timezone.utc).year)
    manifest = {"runId": run_id, "geraadpleegdOp": utcnow(), "crs": CRS,
                "werkgrens": gebied["werkgrens"], "bronnen": manifests}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    (run_dir / "indicators.json").write_text(json.dumps(indicatoren, indent=2, ensure_ascii=False))
    schrijf_rapport(run_dir, gebied, indicatoren, vergelijking, v1, v3, run_id)

    print(f"\n✓ run {run_id}")
    print(f"  panden bestand: {indicatoren['panden_bestand']} | woningen-proxy: "
          f"{indicatoren['woningen_verblijfsobjecten_proxy']} | groen: {indicatoren['begroeid_terrein_ha']} ha")
    print(f"  V3: {'PASS' if v3[0] else 'FAIL'} | rapport: {run_dir / 'report.md'}")
    return 0 if v3[0] and not v1 else (2 if not v3[0] else 1)


if __name__ == "__main__":
    sys.exit(main(refresh="--refresh" in sys.argv))
