#!/usr/bin/env python3
"""Broncache-bouwstap (F1.5): haalt de échte Gentse zone-lagen éénmalig op
en legt ze vast onder fixtures/source/ mét source.meta.json (DATA-02 in het
klein). Runs blijven offline: core/ leest uitsluitend de gecachte files.

Bronnen (Modellicentie Gratis Hergebruik, Stad Gent open data):
  - lage-emissie-zone-gent      → laag `gent-lez`
  - sectoren-circulatieplan-gent → laag `gent-autovrij` (filter: autovrijgebied gevuld)
Adressen: optioneel `--geocode` via OSM Nominatim (ODbL, attributie in meta);
productie-pad is de officiële BeSt Address API (zie source.meta.json).

CLI:  python3 fetch_sources.py [--geocode] [--check] [--bronnen]
  --geocode : vernieuw fixtures/addresses.json via Nominatim (netwerk, 1 req/sec)
  --check   : print zone-uitkomsten per fixture-adres (offline) ter herleiding
              van de golden set
  --bronnen : breid de broncache uit: VKBO (echt, keyless OGC Features) en
              GIPOD (publieke LDES, bij falen mock-testdata) — netwerk
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

POC_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = POC_ROOT / "fixtures" / "source"
PORTAL = "https://data.stad.gent"
UA = "ldttoolbox-poc-gent/0.1 (broncache-bouw; contact via repo)"

LAYERS = {
    "gent-lez": {
        "dataset_id": "lage-emissie-zone-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/lage-emissie-zone-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/lage-emissie-zone-gent",
        "url_portal": f"{PORTAL}/explore/assets/lage-emissie-zone-gent",
        "soort": "export",
        "filter": None,
    },
    "gent-autovrij": {
        "dataset_id": "sectoren-circulatieplan-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/sectoren-circulatieplan-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/sectoren-circulatieplan-gent",
        "url_portal": f"{PORTAL}/explore/assets/sectoren-circulatieplan-gent",
        "soort": "records",
        "filter": "autovrijgebied is gevuld (Autovrij gebied 1–5); voetgangersstraten vallen buiten de laag",
    },
}

# Fixture-adressen voor de personas (cache-committed; herleid via --geocode).
# Keuze: in OSM huisniveau vindbaar binnen Gent én samen de drie zone-cases
# dekkend (beide zones / alleen LEZ / buiten beide) volgens de échte lagen.
ADRESSEN = [
    "Korenmarkt 1, Gent",                       # binnen LEZ én autovrij gebied
    "Sint-Pietersplein 1, Gent",                # binnen LEZ, buiten autovrij gebied
    "Koningin Maria Hendrikaplein 1, Gent",     # buiten beide (station Gent-Sint-Pieters)
    "Veldstraat 1, Gent",                       # centrum, binnen beide
]

BEST_ADDRESS_PAD = ("productiepad officiële geocoding: BeSt Address Web API — "
                    "https://opendata.bosa.be/download/best/bestinabox/best-webapi-user-guide.pdf "
                    "(self-host via docker bosa/opendata-best-webapi); PoC gebruikt OSM Nominatim ( echt, ODbL)")
VKBO_URL = "https://geo.api.vlaanderen.be/VKBO/ogc/features/v1/collections/Vkbo/items"
GIPOD_SWAGGER = "https://gipod.api.vlaanderen.be/swagger/v1/swagger.json"


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dataset_meta(layer: str) -> dict:
    meta = _fetch_json(LAYERS[layer]["url_meta"])
    default = (meta.get("metas") or {}).get("default") or {}
    return {
        "titel": default.get("title"),
        "licentie": ((meta.get("metas") or {}).get("information") or {}).get("licence") or default.get("license"),
        "gewijzigd": default.get("modified"),
    }


def laad_ruwe_laag(layer: str) -> list[dict]:
    """Haal de ruwe features op: export-GeoJSON (lez) of records-API (autovrij,
    want daar staan de veldnamen expliciet in)."""
    if LAYERS[layer]["soort"] == "export":
        return _fetch_json(LAYERS[layer]["url_export"]).get("features", [])
    records = _fetch_json(LAYERS[layer]["url_export"].replace("/exports/geojson", "/records?limit=-1"))
    features = []
    for record in records.get("results", []):
        feature = record.get("geometry") or {}
        if feature.get("type") == "Feature":
            properties = {k: v for k, v in record.items() if k not in ("geometry", "geo_point_2d")}
            feature = dict(feature, properties=properties)
            features.append(feature)
    return features


def normaliseer(layer: str, features: list[dict], versie: str) -> list[dict]:
    """Filter op de officiële afbakening en voorzie de interne layer-tag."""
    if layer == "gent-autovrij":
        features = [f for f in features if (f.get("properties") or {}).get("autovrijgebied")]
    uit = []
    for feature in features:
        uit.append({
            "type": "Feature",
            "properties": {"layer": layer, "versie": versie},
            "geometry": feature.get("geometry"),
        })
    return uit


def normaliseer_vkbo(features: list[dict]) -> list[dict]:
    rijen = []
    for f in features:
        p = f.get("properties") or {}
        rijen.append({
            "naam": p.get("Commerciele_naam") or p.get("Afgekorte_naam") or "onbekend",
            "straat": p.get("AR_straat") or "",
            "huisnr": (p.get("AR_huisnr") or "") + ((" bus " + p["AR_busnr"]) if p.get("AR_busnr") else ""),
            "postcode": p.get("AR_postcode") or "",
            "inschrijving": (p.get("Datum_inschrijving") or "")[:10],
        })
    return rijen


def haal_vkbo(poc_root: Path, bbox: str = "3.700,51.030,3.760,51.080", limit: int = 200) -> dict:
    data = _fetch_json(f"{VKBO_URL}?bbox={bbox}&limit={limit}")
    rijen = normaliseer_vkbo(data.get("features", []))
    (SOURCE_DIR / "vkbo-gent.json").write_text(json.dumps(rijen, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"bron": VKBO_URL, "aantal": len(rijen), "licentie": "VKBO (Vlaanderen) — open data"}


def haal_gipod(poc_root: Path) -> dict:
    try:
        swagger = _fetch_json(GIPOD_SWAGGER)
        paden = [p for p in swagger.get("paths", {}) if "mobilityhindrance" in p.lower()]
        if not paden:
            raise RuntimeError("geen publiek mobilityhindrance-pad in swagger")
        ldes = paden[0]
        proef = _fetch_json(f"https://gipod.api.vlaanderen.be{ldes}" if ldes.startswith("/") else ldes)
        (SOURCE_DIR / "gipod-gent.json").write_text(
            json.dumps({"mode": "echt", "bron": ldes, "ruw": proef}, ensure_ascii=False), encoding="utf-8")
        return {"mode": "echt", "bron": ldes}
    except Exception as fout:  # netwerk/auth/404 — fallback op meegeleverde testdata
        pad = SOURCE_DIR / "gipod-gent.json"
        if not pad.is_file():
            raise RuntimeError(f"GIPOD onbereikbaar en geen mock aanwezig: {fout}")
        data = json.loads(pad.read_text(encoding="utf-8"))
        data["mode"] = "mock"
        pad.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"mode": "mock", "fout": str(fout)}


def build_cache() -> dict:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    meta_document: dict = {"gegenereerdOp": _now(), "bronnen": {}}
    zone_features: list[dict] = []
    for layer, config in LAYERS.items():
        informatie = dataset_meta(layer)
        ruw = laad_ruwe_laag(layer)
        (SOURCE_DIR / f"{config['dataset_id']}.json").write_text(
            json.dumps(ruw, ensure_ascii=False), encoding="utf-8")
        versie = f"stad-gent-open-data {str(informatie['gewijzigd'])[:10]}"
        features = normaliseer(layer, ruw, versie)
        zone_features.extend(features)
        meta_document["bronnen"][layer] = {
            **config, **informatie, "versie": versie,
            "featuresRuwwerk": len(ruw), "featuresNaFilter": len(features),
        }
    (POC_ROOT / "fixtures" / "gis-zones.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False),
        encoding="utf-8")
    meta_document["bronnen"]["adressen"] = {
        "dienst": "OSM Nominatim (cache-bouw; productie-pad: BeSt Address API, FOD BOSA)",
        "licentie": "Data (c) OpenStreetMap contributors, ODbL 1.0 — https://osm.org/copyright",
        "url": "https://nominatim.openstreetmap.org/search",
    }
    meta_document["beschikbaarNogNietGecached"] = {
        "kbo": "KBO/CBE open data (FOD Economie, gratis CSV) + VKBO geo — voor realistische ondernemersdossiers (F2)",
        "gipod": "GIPOD open data (Athumi/Digitaal Vlaanderen) — innames/werken/evenementen openbaar domein (F2)",
    }
    _merge_adressen_meta(meta_document)
    (SOURCE_DIR / "source.meta.json").write_text(
        json.dumps(meta_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta_document


def _merge_adressen_meta(meta_document: dict) -> None:
    """Houd eerdere geocode-informatie (fetchedAt per adres) bij een her-fetch."""
    pad = SOURCE_DIR / "source.meta.json"
    if pad.is_file():
        oud = json.loads(pad.read_text(encoding="utf-8"))
        if "geocodedAt" in oud:
            meta_document["geocodedAt"] = oud["geocodedAt"]


def geocoden() -> None:
    """Vernieuw fixtures/addresses.json via Nominatim (1 request/seconde).

    Gestructureerde zoekopdracht (street/city/country), begrensd op het Gentse
    stadsgebied (viewbox+bounded): vrije-tekst-zoeking trof eerder gelijknamige
    straten in omliggende gemeenten (Sleepstraat bij Gavere, Veldstraat bij Eeklo).
    """
    from urllib.parse import urlencode

    adressen: dict[str, list[float]] = {}
    tijdstippen: dict[str, str] = {}
    for adres in ADRESSEN:
        straat_en_nummer = adres.replace(", Gent", "")
        query = urlencode({"format": "json", "limit": 5, "street": straat_en_nummer,
                           "city": "Gent", "country": "Belgium",
                           "viewbox": "3.680,51.020,3.760,51.080", "bounded": "1"})
        resultaten = _fetch_json(f"https://nominatim.openstreetmap.org/search?{query}")
        treffers = [r for r in resultaten if r.get("addresstype") in ("house", "building")]
        treffers = treffers or [r for r in resultaten if "Gent, Oost-Vlaanderen" in r.get("display_name", "")]
        if not treffers:
            print(f"WAARSCHUWING: geen Gent-treffer voor {adres}", file=sys.stderr)
            continue
        adressen[adres] = [float(treffers[0]["lon"]), float(treffers[0]["lat"])]
        tijdstippen[adres] = _now()
        time.sleep(1.1)
    (POC_ROOT / "fixtures" / "addresses.json").write_text(
        json.dumps(adressen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pad = SOURCE_DIR / "source.meta.json"
    meta_document = json.loads(pad.read_text(encoding="utf-8"))
    meta_document["geocodedAt"] = tijdstippen
    pad.write_text(json.dumps(meta_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"geocode: {len(adressen)}/{len(ADRESSEN)} adressen vernieuwd")


def zone_rapport() -> None:
    """Offline herleidingshulp: zone-uitkomst per fixture-adres tegen de cache."""
    if str(POC_ROOT) not in sys.path:
        sys.path.insert(0, str(POC_ROOT))
    from adapters import gis_zones

    zones = gis_zones.load_zones(POC_ROOT)
    versies = gis_zones.load_layer_versies(POC_ROOT)
    adressen = json.loads((POC_ROOT / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    for adres, (lon, lat) in adressen.items():
        resultaten = {laag: gis_zones.zone_result(zones, laag, lon, lat) for laag in sorted(zones)}
        print(f"{adres}: {resultaten}  (lagen: {versies})")


def main() -> int:
    ap = argparse.ArgumentParser(description="poc-gent broncache-bouw (F1.5)")
    ap.add_argument("--geocode", action="store_true", help="vernieuw adrescoördinaten via Nominatim")
    ap.add_argument("--check", action="store_true", help="print zone-uitkomsten per fixture-adres (offline)")
    ap.add_argument("--bronnen", action="store_true",
                    help="breid uit met VKBO (echt) en GIPOD (echt-of-mock) — netwerk")
    args = ap.parse_args()
    if args.check:
        zone_rapport()
        return 0
    meta_document = build_cache()
    meta_document["bronnen"]["bestAddress"] = {
        "productiepad": BEST_ADDRESS_PAD,
        "pocGeocoder": "OSM Nominatim (ODbL)",
    }
    if args.bronnen:
        vkbo = haal_vkbo(POC_ROOT)
        gipod = haal_gipod(POC_ROOT)
        meta_document["bronnen"]["vkbo"] = vkbo
        meta_document["bronnen"]["gipod"] = gipod
        print(f"vkbo: {vkbo['aantal']} ondernemingen | {vkbo['bron']} | {vkbo['licentie']}")
        print(f"gipod: mode {gipod['mode']}" + (f" | {gipod['bron']}" if gipod.get("bron") else ""))
    (SOURCE_DIR / "source.meta.json").write_text(
        json.dumps(meta_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for laag, info in meta_document["bronnen"].items():
        if laag in ("adressen", "bestAddress", "vkbo", "gipod"):
            continue
        print(f"{laag}: {info['titel']} | {info['licentie']} | versie {info['versie']} "
              f"| {info['featuresNaFilter']}/{info['featuresRuwwerk']} features")
    if args.geocode:
        geocoden()
        zone_rapport()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
