#!/usr/bin/env python3
"""Broncache-bouwstap (F1.5): haalt de échte Gentse zone-lagen éénmalig op
en legt ze vast onder fixtures/source/ mét source.meta.json (DATA-02 in het
klein). Runs blijven offline: core/ leest uitsluitend de gecachte files.

Bronnen (Modellicentie Gratis Hergebruik, Stad Gent open data):
  - lage-emissie-zone-gent      → laag `gent-lez`
  - sectoren-circulatieplan-gent → laag `gent-autovrij` (filter: autovrijgebied gevuld)
Adressen: optioneel `--geocode` via OSM Nominatim (ODbL, attributie in meta);
productie-pad is de officiële BeSt Address API (zie source.meta.json).

CLI:  python3 fetch_sources.py [--geocode] [--check] [--bronnen] [--kaart]
  --geocode : vernieuw fixtures/addresses.json via Nominatim (netwerk, 1 req/sec)
  --check   : print zone-uitkomsten per fixture-adres (offline) ter herleiding
              van de golden set
  --bronnen : breid de broncache uit: VKBO (echt, keyless OGC Features) en
              GIPOD (publieke LDES, bij falen mock-testdata) — netwerk
  --kaart   : bouw fixtures/source/kaart.json: VKBO-bedrijfsadressen,
              OSRM-routes mét alternatief, Gentse gemeentegrens en
              innames-punten — netwerk
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
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
    "gent-bewonerszone": {
        "dataset_id": "bewonerszones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/bewonerszones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/bewonerszones-gent",
        "url_portal": f"{PORTAL}/explore/assets/bewonerszones-gent",
        "soort": "export",
        "filter": None,
    },
    "gent-parkeertariefzone": {
        "dataset_id": "parkeertariefzones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/parkeertariefzones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/parkeertariefzones-gent",
        "url_portal": f"{PORTAL}/explore/assets/parkeertariefzones-gent",
        "soort": "export",
        "filter": None,
    },
    "gent-kotzone": {
        "dataset_id": "kotzones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/kotzones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/kotzones-gent",
        "url_portal": f"{PORTAL}/explore/assets/kotzones-gent",
        "soort": "export",
        "filter": None,
        "attribuut": "kotzone_na",
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
    "Nederkouter 1, Gent",                      # burgerkandidaat: binnen singels/LEZ
    "Sleepstraat 1, Gent",                      # burgerkandidaat: vergelijkingspunt buiten centrum-tariefzone
    "Ottergemsesteenweg-Zuid 1, Gent",          # burgergolden: buiten bewoners-/tariefzone en LEZ (Gentbrugge)
    "Overpoortstraat 1, Gent",                  # kotgolden: studentenwijk, eigen kotzone
]

BEST_ADDRESS_PAD = ("productiepad officiële geocoding: BeSt Address Web API — "
                    "https://opendata.bosa.be/download/best/bestinabox/best-webapi-user-guide.pdf "
                    "(self-host via docker bosa/opendata-best-webapi); PoC gebruikt OSM Nominatim ( echt, ODbL)")
# Stadsgarde voor Nominatim-treffers (met addressdetails): de straatnaam moet
# exact kloppen én de gemeente 'Gent' zijn of de postcode tot de stad Gent
# behoren. De display_name is onbetrouwbaar: '…, Hijfte, Lochristi, Gent,
# Oost-Vlaanderen, … 9080, …' bevat het woord Gent als arrondissement, en
# huisnummers zonder eigen object matchen los op andere straten
# ('Oude Veldstraat' bij Veldstraat).
GENT_POSTCODES = {"9000", "9030", "9031", "9032", "9040", "9041", "9051", "9052"}


def _in_gent(resultaat: dict, straatnaam: str) -> bool:
    adres = resultaat.get("address") or {}
    return (adres.get("road") == straatnaam
            and (adres.get("city") == "Gent" or adres.get("postcode") in GENT_POSTCODES))
VKBO_URL = "https://geo.api.vlaanderen.be/VKBO/ogc/features/v1/collections/Vkbo/items"
GIPOD_SWAGGER = "https://gipod.api.vlaanderen.be/swagger/v1/swagger.json"
NOMINATIM = "https://nominatim.openstreetmap.org"
OSRM_URL = ("https://router.project-osrm.org/route/v1/driving/{van};{naar}"
            "?alternatives=true&overview=simplified&geometries=geojson")

# Persona's mét geregistreerd voertuig (magda:kenteken): voor hen plot de
# simulatie de route bedrijfsadres → werkadres; maria (burger zonder
# voertuigrecord) krijgt geen kaart.
KENTEEKEN_PERSONAS = ("sanne", "ahmed", "fatima", "jeroen", "ellen", "dirk", "wim",
                      "nadia", "ilse", "hanne")

# Burgerpakket GT-VERH-01: de simulatie plot per persona de nieuwe woning
# tegen de regeling-zones (bewoners/tarief/LEZ) — geen routes of innames.
BURGER_PERSONAS = ("lisa", "tomas", "farah", "noor", "emma", "yana", "robrecht")

# Kotpakket GT-KOT-01: per verhuurder het kotadres tegen de kotzone-laag.
KOT_PERSONAS = ("wouter", "saartje", "gregory", "lea", "milan", "karel")


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
    """Filter op de officiële afbakening en voorzie de interne layer-tag;
    bij een attribuut-config (benoemde zones, bijv. kotzones) bewaart de
    normalisatie de attribuutwaarde per feature voor de gisCheck-lookup."""
    if layer == "gent-autovrij":
        features = [f for f in features if (f.get("properties") or {}).get("autovrijgebied")]
    attribuutveld = LAYERS.get(layer, {}).get("attribuut")
    uit = []
    for feature in features:
        properties = {"layer": layer, "versie": versie}
        if attribuutveld:
            waarde = (feature.get("properties") or {}).get(attribuutveld)
            if waarde:
                properties["attribuut"] = waarde
        uit.append({
            "type": "Feature",
            "properties": properties,
            "geometry": feature.get("geometry"),
        })
    return uit


# Afvalkalender (IVAGO, open data Stad Gent): fracties per straat en datum.
# Deterministisch gevatted: weekdag + eerste datum úit de rijen zelf — geen
# 'nu'-berekening (replay-stabiliteit), geen grofvuil-slot in het burgerpakket.
IVAGO_DATASET = "afvalophaalkalender-ivago-woongebied-gent-2026-2027"
IVAGO_VELDEN = {"straat": "straatnaam", "fractie": "fracties", "datum": "datum"}
IVAGO_FRACTIES = {"afvalRest": ("rest",), "afvalPmd": ("pmd",), "afvalGlas": ("glas",),
                  "afvalPapier": ("papier",), "afvalGft": ("gft",)}
DAG_NAMEN = ("maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag")


def straatnaam_norm(adres: str) -> str:
    """'Veldstraat 1, Gent' → 'veldstraat': huisnummer/bus en gemeente eraf,
    diakritiek gestript, kleine letters (cache-sleutel voor de afvalkalender)."""
    deel = adres.split(",")[0]
    zonder_nummer = re.sub(r"\s+\d+.*$", "", deel)
    nkfd = unicodedata.normalize("NFKD", zonder_nummer)
    ascii_ = "".join(c for c in nkfd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def _norm_datum(raw: str) -> str | None:
    for patroon in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw.strip(), patroon).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _rij_geldig_voor_nummer(rij: dict, huisnummer: int | None) -> bool:
    """De dataset kent per ronde nummerbereiken (even/oneven zijdes). Een rij
    geldt voor dit nummer als het bereik van de eigen zijde het nummer dekt;
    alleen rijen zónder enkel bereik gelden voor de hele straat (een bereik
    alléén aan de andere zijde sluit dit nummer uit)."""
    if huisnummer is None:
        return True
    soort = "even" if huisnummer % 2 == 0 else "on"
    van, tot = rij.get(f"{soort}_van"), rij.get(f"{soort}_tot")
    if van is not None and tot is not None:
        try:
            return int(van) <= huisnummer <= int(tot)
        except (TypeError, ValueError):
            return True  # onleesbaar bereik: niet beperkend
    return all(rij.get(veld) is None for veld in
               ("even_van", "even_tot", "on_van", "on_tot"))


def vatten_afval(rijen: list[dict], huisnummer: int | None = None) -> dict:
    """Per fractie: modus-weekdag (de meest voorkomende ophaaldag — de kalender
    publiceert verspreide datums o.a. door feestdagverschuivingen), alle
    dagen, aantal en eerste datum. Deterministisch: alleen uit de rijen zelf,
    geen 'nu'-berekening (replay-stabiliteit)."""
    uit: dict[str, dict] = {}
    for rij in rijen:
        if not _rij_geldig_voor_nummer(rij, huisnummer):
            continue
        datum = _norm_datum(str(rij.get(IVAGO_VELDEN["datum"], "")))
        if not datum:
            continue
        fracties = str(rij.get(IVAGO_VELDEN["fractie"], "")).lower()
        weekdag = DAG_NAMEN[datetime.strptime(datum, "%Y-%m-%d").weekday()]
        for slot, sleutels in IVAGO_FRACTIES.items():
            if any(sleutel in fracties for sleutel in sleutels):
                info = uit.setdefault(slot, {"eerste": datum, "dagen": [], "telling": {}})
                info["eerste"] = min(info["eerste"], datum)
                if weekdag not in info["dagen"]:
                    info["dagen"].append(weekdag)
                info["telling"][weekdag] = info["telling"].get(weekdag, 0) + 1
    return {slot: {"dag": min(info["telling"], key=lambda d: (-info["telling"][d], DAG_NAMEN.index(d))),
                   "dagen": sorted(info["dagen"], key=DAG_NAMEN.index),
                   "aantal": sum(info["telling"].values()), "eerste": info["eerste"]}
            for slot, info in uit.items()}


def haal_afvalkalender(poc_root: Path) -> dict:
    """Complete IVAGO-kalender ophalen (gepagineerd: de API capt op 100 rijen
    per request) en per straat vatten — geen fixture-adresfilter meer, zodat
    elke Gentse straat in het woongebied uit de cache antwoordt. Ruwe rijen
    blijven een fetch-artefact; gecommit wordt alleen de vatting."""
    kal_meta = _fetch_json(f"{PORTAL}/api/explore/v2.1/catalog/datasets/{IVAGO_DATASET}")
    gewijzigd = ((kal_meta.get("metas") or {}).get("default") or {}).get("modified")
    # De records-API capt hard op 100 rijen per request; de export-endpoint
    # levert de volledige dataset (171k rijen, ~40 s) in één keer.
    rijen = _fetch_json(
        f"{PORTAL}/api/explore/v2.1/catalog/datasets/{IVAGO_DATASET}/exports/json?limit=-1"
    )
    per_straat: dict[str, list[dict]] = {}
    for rij in rijen:
        naam = str(rij.get(IVAGO_VELDEN["straat"], "")).strip()
        if naam:
            per_straat.setdefault(naam, []).append(rij)
    document = {"dataset": "ivago-ophaalkalender",
                "versie": f"{IVAGO_DATASET} (gewijzigd {str(gewijzigd)[:10]})",
                "straten": {straatnaam_norm(f"{naam} 1, Gent"): vatten_afval(rijen_straat)
                            for naam, rijen_straat in per_straat.items()}}
    (SOURCE_DIR / "afvalkalender.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"versie": document["versie"], "straten": len(document["straten"]),
            "aantalRijen": len(rijen)}


def normaliseer_vkbo(features: list[dict]) -> list[dict]:
    rijen = []
    for f in features:
        p = f.get("properties") or {}
        busnr = (p.get("AR_busnr") or "").strip()
        rijen.append({
            "naam": (p.get("Commerciele_naam") or "").strip()
                    or (p.get("Afgekorte_naam") or "").strip() or "onbekend",
            "straat": (p.get("AR_straat") or "").strip(),
            "huisnr": ((p.get("AR_huisnr") or "").strip()
                       + (f" bus {busnr}" if busnr else "")),
            "postcode": (p.get("AR_postcode") or "").strip(),
            "inschrijving": (p.get("Datum_inschrijving") or "")[:10],
        })
    return rijen


def haal_vkbo(poc_root: Path, bbox: str = "3.700,51.030,3.760,51.080", limit: int = 200) -> dict:
    data = _fetch_json(f"{VKBO_URL}?bbox={bbox}&limit={limit}")
    rijen = normaliseer_vkbo(data.get("features", []))
    (SOURCE_DIR / "vkbo-gent.json").write_text(json.dumps(rijen, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"bron": VKBO_URL, "aantal": len(rijen), "licentie": "VKBO (Vlaanderen) — open data"}


def haal_gipod(poc_root: Path) -> dict:
    """Publieke GIPOD-LDES proberen; de echt-cache (gipod-gent-echt.json) is
    een fetch-artefact en wordt níet gecommit. De gecommitte mock-fixture
    (gipod-gent.json) is de stabiele offline testbasis en wordt nooit
    herschreven of herlabeld."""
    echt_pad = SOURCE_DIR / "gipod-gent-echt.json"
    try:
        swagger = _fetch_json(GIPOD_SWAGGER)
        kandidaten = []
        for pad, operaties in swagger.get("paths", {}).items():
            if "mobilityhindrance" not in pad.lower().replace("-", ""):
                continue
            get = operaties.get("get") or {}
            if "Auth policies" in (get.get("description") or ""):
                continue  # auth-policy-endpoint is geen publieke ingang
            kandidaten.append(pad)
        if not kandidaten:
            raise RuntimeError("geen publiek (auth-vrij) mobilityhindrance-pad in swagger")
        proef = None
        gebruikte_url = None
        fouten = []
        for kandidaat in kandidaten[:3]:
            url = f"https://gipod.api.vlaanderen.be{kandidaat}" if kandidaat.startswith("/") else kandidaat
            try:
                proef = _fetch_json(url)
                gebruikte_url = url
                break
            except Exception as poging:
                fouten.append(f"{kandidaat}: {poging}")
        if proef is None:
            raise RuntimeError("publieke LDES-ingangen onbereikbaar: " + "; ".join(fouten))
        echt_pad.write_text(json.dumps({"mode": "echt", "bron": gebruikte_url, "ruw": proef},
                                       ensure_ascii=False), encoding="utf-8")
        return {"mode": "echt", "bron": gebruikte_url}
    except Exception as fout:  # netwerk/auth/404 — fallback op meegeleverde testdata
        mock_pad = SOURCE_DIR / "gipod-gent.json"
        if not mock_pad.is_file():
            raise RuntimeError(f"GIPOD onbereikbaar en geen mock aanwezig: {fout}")
        return {"mode": "mock", "fout": str(fout), "mock": mock_pad.name}


def bedrijf_toewijzing(vkbo_rijen: list[dict], persona_ids: tuple[str, ...]) -> dict:
    """Deterministische toewijzing persona → KBO/VKBO-bedrijfsadres (het adres
    waar het kenteken geregistreerd staat in de replay): gesorteerde rijen met
    vaste offset per persona — stabiel zolang de broncache niet ververst."""
    rijen = sorted((rij for rij in vkbo_rijen
                    if rij.get("straat") and rij.get("huisnr") and rij.get("postcode")),
                   key=lambda rij: (rij["naam"], rij["straat"], rij["huisnr"]))
    if not rijen:
        raise ValueError("vkbo-cache bevat geen bruikbare bedrijfsadressen")
    uit = {}
    for offset, pid in enumerate(persona_ids):
        rij = rijen[offset % len(rijen)]
        uit[pid] = {"naam": rij["naam"],
                    "adres": f"{rij['straat']} {rij['huisnr']}, {rij['postcode']} Gent"}
    return uit


def dun_punten(punten: list, max_punten: int = 80) -> list:
    """Polylijn gelijkmatig verdunnen voor een compacte embed; eerste en
    laatste punt blijven altijd staan."""
    if len(punten) <= max_punten:
        return [list(p) for p in punten]
    stap = (len(punten) - 1) / (max_punten - 1)
    return [list(punten[round(i * stap)]) for i in range(max_punten)]


def _nominatim_zoek(straat: str) -> list[dict]:
    from urllib.parse import urlencode

    query = urlencode({"format": "json", "limit": 5, "street": straat,
                       "city": "Gent", "country": "Belgium", "addressdetails": "1",
                       "viewbox": "3.630,50.990,3.830,51.160", "bounded": "1"})
    resultaten = _fetch_json(f"{NOMINATIM}/search?{query}")
    time.sleep(1.1)
    return resultaten


def _gent_coord(straat_en_huisnr: str) -> list[float] | None:
    """Coördinaat in de stad Gent voor een adres: eerst huisniveau, bij geen
    treffers het straatcentroid — telkens mét de exacte straatnaam- en
    stadsgarde (onbestaande huisnummers, bijv. Veldstraat 1, vallen terug op
    de straat zelf)."""
    straatnaam = straat_en_huisnr.rsplit(" ", 1)[0]  # huisnummer (of '1A') eraf
    for poging in (straat_en_huisnr, straatnaam):
        treffers = [r for r in _nominatim_zoek(poging) if _in_gent(r, straatnaam)]
        treffers = [r for r in treffers if r.get("addresstype") in ("house", "building")] or treffers
        if treffers:
            return [float(treffers[0]["lon"]), float(treffers[0]["lat"])]
    return None


def _geocode(straat_en_huisnr: str, cache_sleutel: str | None = None) -> list[float] | None:
    """Coördinaat voor een Gent-adres: eerst de gecommitte adrescache, daarna
    Nominatim met stadsgarde (1 req/s)."""
    sleutel = cache_sleutel or f"{straat_en_huisnr}, Gent"
    cache_pad = POC_ROOT / "fixtures" / "addresses.json"
    cache = json.loads(cache_pad.read_text(encoding="utf-8")) if cache_pad.is_file() else {}
    if sleutel in cache:
        return cache[sleutel]
    return _gent_coord(straat_en_huisnr)


def _haal_grens() -> dict | None:
    """Gentse gemeentegrens als GeoJSON-polygoon (Nominatim/OSM)."""
    from urllib.parse import urlencode

    query = urlencode({"q": "Gent, Oost-Vlaanderen, Belgium", "format": "json",
                       "polygon_geojson": "1", "limit": "1"})
    resultaten = _fetch_json(f"{NOMINATIM}/search?{query}")
    time.sleep(1.1)
    return (resultaten[0].get("geojson") or None) if resultaten else None


def _haal_route(van: list[float], naar: list[float]) -> dict | None:
    """Route mét alternatief via de OSRM-demo-server (OpenStreetMap, ODbL):
    primair (snelste) en alternatief, punten gedaan voor de embed."""
    data = _fetch_json(OSRM_URL.format(van=f"{van[0]},{van[1]}", naar=f"{naar[0]},{naar[1]}"))
    routes = data.get("routes") or []
    if not routes:
        return None

    def _vorm(route: dict) -> dict:
        return {"punten": dun_punten(route["geometry"]["coordinates"]),
                "afstand_m": round(route["distance"]),
                "duur_s": round(route["duration"])}

    return {"primaire": _vorm(routes[0]),
            "alternatief": _vorm(routes[1]) if len(routes) > 1 else None}


def haal_kaart(poc_root: Path, kenteken_personas: tuple = KENTEEKEN_PERSONAS) -> dict:
    """Netwerkstap (F-kaart): bedrijfsadressen uit de VKBO-cache (KBO-open
    register, deterministische toewijzing), geocoding (adrescache → Nominatim),
    routes mét alternatief (OSRM/OSM), de Gentse gemeentegrens en
    innames-punten uit de GIPOD-cache — naar fixtures/source/kaart.json."""
    source = poc_root / "fixtures" / "source"
    vkbo = json.loads((source / "vkbo-gent.json").read_text(encoding="utf-8"))
    gipod = json.loads((source / "gipod-gent.json").read_text(encoding="utf-8"))
    personas = {p["id"]: p for p in json.loads(
        (poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))["personas"]}

    bedrijven = bedrijf_toewijzing(vkbo, kenteken_personas)
    routes: dict = {}
    for pid in kenteken_personas:
        bedrijf = bedrijven[pid]
        straat_huisnr = bedrijf["adres"].split(",")[0]
        start = _geocode(straat_huisnr, cache_sleutel=bedrijf["adres"])
        persona = personas[pid]
        doel_adres = persona.get("corrections", {}).get("address") or persona["intentSlots"]["address"]
        doel = _geocode(doel_adres)
        if start is None or doel is None:
            print(f"WAARSCHUWING: geen coördinaten voor {pid} ({bedrijf['adres']} → {doel_adres})",
                  file=sys.stderr)
            continue
        bedrijf["coord"] = start
        routes[pid] = {"doel": doel_adres, "doelCoord": doel, **_haal_route(start, doel)}

    innames = []
    for inname in gipod.get("innames", []):
        coord = _geocode(f"{inname['straat']} 1", cache_sleutel=f"{inname['straat']} 1, Gent")
        if coord:
            innames.append({**inname, "coord": coord,
                            "bron": f"gipod-{gipod.get('mode', 'mock')} (punt via adrescache/Nominatim)"})

    kaart = {
        "grens": _haal_grens(),
        "bedrijven": bedrijven,
        "routes": routes,
        "innames": innames,
        "meta": {
            "bronnen": {
                "osrm": {"url": OSRM_URL.split("?")[0], "dienst": "OSRM demo-server op OpenStreetMap",
                         "licentie": "ODbL — © OpenStreetMap-contributors", "fetchDatum": _now()},
                "nominatim": {"url": f"{NOMINATIM}/search", "licentie": "ODbL — © OpenStreetMap-contributors",
                              "fetchDatum": _now()},
                "vkbo": {"bron": VKBO_URL, "licentie": "open registerdata KBO/VKBO (Digital Vlaanderen)",
                         "selectie": "deterministisch — zie bedrijf_toewijzing"},
                "gipod": {"mode": gipod.get("mode"), "licentie": "Modellicentie Gratis Hergebruik",
                          "geometrie": "mock: straat-punt via adrescache"},
            },
            "productiepaden": {
                "geocoding": BEST_ADDRESS_PAD,
                "innames": "GIPOD LDES mobility-hindrances (WKT Lambert72 → WGS84)",
            },
            "fetchedAt": _now(),
        },
    }
    (source / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    return kaart


def haal_kaart_persoonsadressen(poc_root: Path, personas: tuple, doel_naam: str) -> dict:
    """Persoonsadres-kaart (GT-VERH-01/GT-KOT-01): gemeentegrens + per persona
    het doeladres (na eventuele H1-correctie) als startpunt. De regeling-zones
    leest de build rechtstreeks uit gis-zones.geojson — geen routes of innames."""
    kaart_pad = SOURCE_DIR / "kaart.json"
    grens = json.loads(kaart_pad.read_text(encoding="utf-8")).get("grens") \
        if kaart_pad.is_file() else _haal_grens()
    adressen = json.loads((poc_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    persona_fixtures = {p["id"]: p for p in json.loads(
        (poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))["personas"]}
    uit = {"grens": grens, "personas": {}, "meta": {"fetchedAt": _now()}}
    for pid in personas:
        doel = persona_fixtures[pid].get("corrections", {}).get("address") \
            or persona_fixtures[pid]["intentSlots"]["address"]
        if doel in adressen:
            uit["personas"][pid] = {"adres": doel, "coord": adressen[doel]}
    (SOURCE_DIR / doel_naam).write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return uit


def haal_kaart_burger(poc_root: Path, burger_personas: tuple = BURGER_PERSONAS) -> dict:
    return haal_kaart_persoonsadressen(poc_root, burger_personas, "kaart-burger.json")


def haal_kaart_kot(poc_root: Path, kot_personas: tuple = KOT_PERSONAS) -> dict:
    return haal_kaart_persoonsadressen(poc_root, kot_personas, "kaart-kot.json")


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
        "kbo": "KBO/CBE bulk-CSV (FOD Economie, gratis download) — zwaarder dan de via VKBO FeatureService ontsloten vestigingsdata; pas nodig voor dossiers buiten de Gentse bbox (latere fase)",
    }
    _merge_adressen_meta(meta_document)
    (SOURCE_DIR / "source.meta.json").write_text(
        json.dumps(meta_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta_document


def _merge_adressen_meta(meta_document: dict) -> None:
    """Houd eerdere geocode-informatie (fetchedAt per adres) én bron-entries
    uit andere cache-stappen (bijv. ivago-ophaalkalender, kaart, kaart-burger)
    bij een her-fetch: elke CLI-run herbouwt alleen zijn eigen onderdelen."""
    pad = SOURCE_DIR / "source.meta.json"
    if pad.is_file():
        oud = json.loads(pad.read_text(encoding="utf-8"))
        if "geocodedAt" in oud:
            meta_document["geocodedAt"] = oud["geocodedAt"]
        for sleutel, info in (oud.get("bronnen") or {}).items():
            if sleutel not in meta_document["bronnen"]:
                meta_document["bronnen"][sleutel] = info
        if "beschikbaarNogNietGecached" in oud and "beschikbaarNogNietGecached" not in meta_document:
            meta_document["beschikbaarNogNietGecached"] = oud["beschikbaarNogNietGecached"]


def geocoden() -> None:
    """Vernieuw fixtures/addresses.json via Nominatim (1 request/seconde).

    Gestructureerde zoekopdracht (street/city/country), begrensd op het Gentse
    stadsgebied (viewbox+bounded, inclusief deelgemeenten als Gentbrugge — de
    burger-adressen liggen buiten de singels) mét stadsgarde via
    addressdetails: alleen treffers waarvan de gemeente 'Gent' is of de
    postcode tot de stad Gent behoort tellen mee, dus gelijknamige straten in
    omliggende gemeenten (Veldstraat bij Lochristi/Destelbergen, Sleepstraat
    bij Gavere, Veldstraat bij Eeklo) vallen af.
    """
    from urllib.parse import urlencode

    adressen: dict[str, list[float]] = {}
    tijdstippen: dict[str, str] = {}
    for adres in ADRESSEN:
        straat_en_nummer = adres.replace(", Gent", "")
        coord = _gent_coord(straat_en_nummer)
        if coord is None:
            print(f"WAARSCHUWING: geen Gent-treffer voor {adres}", file=sys.stderr)
            continue
        adressen[adres] = coord
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
    attributen = gis_zones.load_ring_attributen(POC_ROOT)
    adressen = json.loads((POC_ROOT / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    for adres, (lon, lat) in adressen.items():
        resultaten = {laag: gis_zones.zone_result(zones, laag, lon, lat) for laag in sorted(zones)}
        for laag in sorted(zones):
            naam = gis_zones.attribuut_result(zones, attributen, laag, lon, lat)
            if naam not in ("in", "niet-in"):
                resultaten[f"{laag}={naam}"] = naam
        print(f"{adres}: {resultaten}  (lagen: {versies})")


def main() -> int:
    ap = argparse.ArgumentParser(description="poc-gent broncache-bouw (F1.5)")
    ap.add_argument("--geocode", action="store_true", help="vernieuw adrescoördinaten via Nominatim")
    ap.add_argument("--check", action="store_true", help="print zone-uitkomsten per fixture-adres (offline)")
    ap.add_argument("--bronnen", action="store_true",
                    help="breid uit met VKBO (echt) en GIPOD (echt-of-mock) — netwerk")
    ap.add_argument("--afval", action="store_true",
                    help="bouw de IVAGO-afvalkalender-cache per fixture-straat — netwerk")
    ap.add_argument("--kaart", action="store_true",
                    help="bouw de kaart-cache (VKBO-bedrijfsadressen, OSRM-routes mét alternatief, "
                         "Gent-grens, innames-punten) — netwerk")
    ap.add_argument("--kaart-burger", action="store_true",
                    help="bouw de burgerkaart-cache (Gent-grens + nieuwe woning per burger-persona, "
                         "offline uit de adrescache) — netwerk alléén bij ontbrekende grens")
    ap.add_argument("--kaart-kot", action="store_true",
                    help="bouw de kotkaart-cache (Gent-grens + kotadres per verhuurder-persona, "
                         "offline uit de adrescache) — netwerk alléén bij ontbrekende grens")
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
    if args.afval:
        afval = haal_afvalkalender(POC_ROOT)
        meta_document["bronnen"]["ivago-ophaalkalender"] = {
            "cache": "fixtures/source/afvalkalender.json", **afval,
            "titel": "Afvalophaalkalender IVAGO woongebied Gent 2026-2027",
            "licentie": "Modellicentie Gratis Hergebruik",
            "url": f"{PORTAL}/explore/assets/{IVAGO_DATASET}",
        }
        print(f"afval: {afval['straten']} straten ({afval['aantalRijen']} rijen; {afval['versie']})")
    if args.kaart:
        kaart = haal_kaart(POC_ROOT)
        meta_document["bronnen"]["kaart"] = {
            "cache": "fixtures/source/kaart.json",
            "fetchedAt": kaart["meta"]["fetchedAt"],
            "onderdelen": sorted(kaart["meta"]["bronnen"]),
        }
        print(f"kaart: {len(kaart['routes'])}/{len(KENTEEKEN_PERSONAS)} routes | "
              f"{len(kaart['innames'])} innames | grens: {'ja' if kaart['grens'] else 'nee'}")
    if args.kaart_burger:
        kaart_burger = haal_kaart_burger(POC_ROOT)
        meta_document["bronnen"]["kaart-burger"] = {
            "cache": "fixtures/source/kaart-burger.json",
            "fetchedAt": kaart_burger["meta"]["fetchedAt"],
            "personas": sorted(kaart_burger["personas"]),
        }
        print(f"kaart-burger: {len(kaart_burger['personas'])}/{len(BURGER_PERSONAS)} woningen "
              f"| grens: {'ja' if kaart_burger['grens'] else 'nee'}")
    if args.kaart_kot:
        kaart_kot = haal_kaart_kot(POC_ROOT)
        meta_document["bronnen"]["kaart-kot"] = {
            "cache": "fixtures/source/kaart-kot.json",
            "fetchedAt": kaart_kot["meta"]["fetchedAt"],
            "personas": sorted(kaart_kot["personas"]),
        }
        print(f"kaart-kot: {len(kaart_kot['personas'])}/{len(KOT_PERSONAS)} kotadressen "
              f"| grens: {'ja' if kaart_kot['grens'] else 'nee'}")
    (SOURCE_DIR / "source.meta.json").write_text(
        json.dumps(meta_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for laag, info in meta_document["bronnen"].items():
        if laag in ("adressen", "bestAddress", "vkbo", "gipod", "kaart", "kaart-burger",
                    "kaart-kot", "ivago-ophaalkalender"):
            continue
        print(f"{laag}: {info['titel']} | {info['licentie']} | versie {info['versie']} "
              f"| {info['featuresNaFilter']}/{info['featuresRuwwerk']} features")
    if args.geocode:
        geocoden()
        zone_rapport()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
