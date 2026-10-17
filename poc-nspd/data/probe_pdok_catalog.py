"""Live-probe van de PDOK-catalogus (api.pdok.nl) binnen de NSPD-bbox.

Doel: nagaan welke PDOK OGC API Features-diensten daadwerkelijk features
leveren binnen het North Sea Port District (bbox.py) en voor welke tracks ze
bruikbaar zijn. Schrijft data/probe_pdok_catalog_<datum>.json en bewaart de
ruwe catalogus (api.pdok.nl/index.json) als-ontvangen onder
data/bronze/pdok-catalog/<retrievedAt>/index.json (lake-bronze, via lake_sync).

Is GEEN pytest (netwerk). Discipline (zie probe_be_sources.py): een dienst die
niet live antwoordt of geen features in de bbox heeft, wordt niet gepind.
Run: .venv/bin/python data/probe_pdok_catalog.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bbox import NSPD_BBOX_WGS84  # noqa: E402

INDEX_URL = "https://api.pdok.nl/index.json"
UA = "nLDT-toolbox-poc-nspd/1.0 (PDOK-catalogusprobe, cache-first, 1 request in flight)"
DELAY_S = 0.15
MAX_COLLECTIONS_PER_API = 8

# api-pad (na https://api.pdok.nl/) → tracks + rolhint. De tracks zijn de 13
# NSPD-tracks (run.py:TRACKS); 'context' = nooit zone-bepalend.
KANDIDATEN: dict[str, dict] = {
    "rvo/windsnelheden/ogc/v1": {"tracks": ["wind"], "rol": "scenario-basis",
        "waarom": "windsnelheid op 100 m — opbrengstpotentieel windturbines"},
    "kadaster/omgevingswet-geometrieen/ogc/v2": {"tracks": ["*"], "rol": "legal-geometrie",
        "waarom": "geometrieën van omgevingsdocumenten (DSO) — operand-geometrie OVZ Zeeland"},
    "hwh/waterschappen-keringen-imwa/ogc/v1": {"tracks": ["water", "wonen", "wind"], "rol": "exclusion",
        "waarom": "waterkeringen Scheldestromen (IMWA) — FR-WAT-03-operand naast OVZ-dijktrajecten"},
    "hwh/waterschappen-zoneringen-imwa/ogc/v1": {"tracks": ["water"], "rol": "attention",
        "waarom": "waterstaatskundige zoneringen (kern-/beschermingszone waterstaatswerk)"},
    "hwh/waterschappen-oppervlaktewateren-imwa/ogc/v1": {"tracks": ["water", "landschap"], "rol": "context",
        "waarom": "oppervlaktewateren waterschap (IMWA)"},
    "hwh/waterschappen-kunstwerken-imwa/ogc/v2": {"tracks": ["water", "mobiliteit"], "rol": "context",
        "waarom": "gemalen/sluizen/stuwen (IMWA)"},
    "hwh/waterschappen-waterbeheergebieden-imwa/ogc/v1": {"tracks": ["water"], "rol": "context",
        "waarom": "beheergebied waterschap Scheldestromen"},
    "rws/nationaal-wegenbestand-vaarwegen/ogc/v1": {"tracks": ["mobiliteit", "water"], "rol": "attention",
        "waarom": "NWB-vaarwegen (Kanaal Gent-Terneuzen, Westerschelde)"},
    "rws/nationaal-wegenbestand-wegen/ogc/v1": {"tracks": ["mobiliteit"], "rol": "context",
        "waarom": "NWB-wegvakken — omvangrijk, waarschijnlijk service-only"},
    "rws/weggegevens/ogc/v1": {"tracks": ["mobiliteit"], "rol": "context",
        "waarom": "WEGGEG rijkswegkenmerken"},
    "prorail/spoorwegen/ogc/v1": {"tracks": ["mobiliteit", "werken"], "rol": "context",
        "waarom": "spoorwegen ProRail (havenspoor Sloe/Terneuzen)"},
    "rvo/gewaspercelen/ogc/v1": {"tracks": ["landbouw", "biomassa"], "rol": "inclusion",
        "waarom": "BRP-gewaspercelen — omvangrijk; landbouwgrond + gewascategorie"},
    "rvo/fysisch-geografische-regios/ogc/v1": {"tracks": ["landschap", "bodem"], "rol": "attention",
        "waarom": "fysisch-geografische regio's (zeekleigebied/duinen)"},
    "rvo/indicatieve-aandachtsgebieden-funderingsproblematiek/ogc/v1": {"tracks": ["bodem", "wonen"], "rol": "attention",
        "waarom": "funderingsrisico-aandachtsgebieden"},
    "rvo/potentiekaart-reststromen/ogc/v1": {"tracks": ["biomassa", "energietoets"], "rol": "scenario-basis",
        "waarom": "reststromen-potentieel (biomassa)"},
    "rvo/potentiekaart-restwarmte/ogc/v1": {"tracks": ["energietoets", "werken"], "rol": "scenario-basis",
        "waarom": "restwarmte-bronnen industrie (havengebied)"},
    "rvo/potentiekaart-omgevingswarmte/ogc/v1": {"tracks": ["energietoets"], "rol": "scenario-basis",
        "waarom": "omgevingswarmte-potentieel (aquathermie e.d.)"},
    "rvo/potentieel-warmte-koude-opslagsystemen/ogc/v1": {"tracks": ["bodem", "energietoets"], "rol": "scenario-basis",
        "waarom": "WKO-potentieel open/gesloten systemen (GJ/ha.jaar)"},
    "rws/overstromingen-gevarengebied/ogc/v1": {"tracks": ["water", "wonen", "werken"], "rol": "attention",
        "waarom": "ROR-overstromingsgevarengebieden"},
    "rws/overstromingen-risicogebied/ogc/v2": {"tracks": ["water", "wonen"], "rol": "attention",
        "waarom": "ROR-overstromingsrisicogebieden"},
    "rce/beschermde-gebieden-cultuurhistorie/ogc/v1": {"tracks": ["landschap", "wonen", "recreatie"], "rol": "attention",
        "waarom": "beschermde stads-/dorpsgezichten, werelderfgoed (RCE)"},
    "rvo/wetlands/ogc/v1": {"tracks": ["bos", "landschap", "wind"], "rol": "exclusion",
        "waarom": "Ramsar-wetlands (Westerschelde & Saeftinghe)"},
    "rvo/nationaal-beschermde-gebieden-cdda/ogc/v1": {"tracks": ["bos", "landschap", "wind"], "rol": "exclusion",
        "waarom": "nationaal beschermde gebieden (CDDA)"},
    "rvo/nationale-parken/ogc/v1": {"tracks": ["recreatie", "bos"], "rol": "attention",
        "waarom": "nationale parken"},
    "rvo/natuurmeting-op-kaart-2014/ogc/v1": {"tracks": ["bos"], "rol": "context",
        "waarom": "natuurmeting op kaart (EHS-realisatie)"},
    "ienw/hoofdwegen-omgevingslawaai-geharmoniseerd/ogc/v1": {"tracks": ["wonen", "mobiliteit"], "rol": "attention",
        "waarom": "hoofdwegen Richtlijn Omgevingslawaai"},
    "ienw/hoofdspoorwegen-omgevingslawaai-geharmoniseerd/ogc/v1": {"tracks": ["wonen", "mobiliteit"], "rol": "attention",
        "waarom": "hoofdspoorwegen Richtlijn Omgevingslawaai"},
    "ienw/agglomeraties-omgevingslawaai-geharmoniseerd/ogc/v1": {"tracks": ["wonen"], "rol": "context",
        "waarom": "agglomeraties omgevingslawaai"},
    "cbs/wijken-en-buurten-2025/ogc/v1": {"tracks": ["wonen", "werken"], "rol": "scenario-basis",
        "waarom": "kerncijfers wijken/buurten 2025"},
    "cbs/bevolkingskernen-2021/ogc/v1": {"tracks": ["wonen"], "rol": "context",
        "waarom": "bevolkingskernen 2021"},
    "cbs/bestand-bodemgebruik-2017/ogc/v1": {"tracks": ["bodem", "landschap", "landbouw"], "rol": "context",
        "waarom": "BBG2017 bodemgebruik"},
    "kadaster/brk-bestuurlijke-gebieden/ogc/v1": {"tracks": ["*"], "rol": "context",
        "waarom": "gemeente-/provinciegrenzen (rapportage per gemeente)"},
    "rws/productie-en-industrie-productiefaciliteiten/ogc/v1": {"tracks": ["werken", "energietoets"], "rol": "scenario-basis",
        "waarom": "REV-productiefaciliteiten — havenbedrijven/energie-infra-gap (README §Beperkingen)"},
    "rws/productie-en-industrie-productie-installaties/ogc/v1": {"tracks": ["werken", "energietoets"], "rol": "scenario-basis",
        "waarom": "REV-productie-installaties"},
    "rws/richtlijn-stedelijk-afvalwater/ogc/v1": {"tracks": ["water"], "rol": "context",
        "waarom": "RWZI's / agglomeraties RSA"},
    "rws/kwetsbaar-gebied/ogc/v1": {"tracks": ["water"], "rol": "attention",
        "waarom": "kwetsbaar gebied RSA"},
    "rvo/habitatrichtlijn-verspreiding-typen/ogc/v1": {"tracks": ["bos", "wind"], "rol": "attention",
        "waarom": "habitattypen-verspreiding (10 km-grid)"},
    "rvo/vogelrichtlijn-verspreidingsgebied-soorten/ogc/v1": {"tracks": ["wind"], "rol": "attention",
        "waarom": "vogelrichtlijn-verspreidingsgebieden (aanvaringsrisico wind)"},
    "rvo/krm-beschermde-gebieden/ogc/v1": {"tracks": ["water", "bos"], "rol": "attention",
        "waarom": "KRM beschermde gebieden"},
    "rws/hydrografie-netwerk/ogc/v1": {"tracks": ["water"], "rol": "context",
        "waarom": "hydrografisch netwerk (INSPIRE)"},
    "kadaster/brt-top10nl/ogc/v1": {"tracks": ["*"], "rol": "context",
        "waarom": "TOP10NL — basis; service-only (omvang)"},
    "kadaster/bgt/ogc/v1": {"tracks": ["*"], "rol": "context",
        "waarom": "BGT — basis; service-only (omvang)"},
    "kadaster/bag/ogc/v2": {"tracks": ["wonen", "werken"], "rol": "context",
        "waarom": "BAG panden/verblijfsobjecten; service-only (omvang)"},
    "kadaster/brk-kadastrale-kaart/ogc/v1": {"tracks": ["*"], "rol": "context",
        "waarom": "kadastrale percelen; service-only (omvang)"},
    "kadaster/3d-basisvoorziening/ogc/v1": {"tracks": ["*"], "rol": "context",
        "waarom": "3D basisvoorziening (naast 3D BAG)"},
    "kadaster/brk-publiekrechtelijke-beperkingen-wkpb/ogc/v1": {"tracks": ["wonen", "werken"], "rol": "context",
        "waarom": "Wkpb-beperkingen op percelen"},
}


def _get(session: requests.Session, url: str, params: dict | None = None, timeout: float = 60.0) -> dict:
    time.sleep(DELAY_S)
    try:
        r = session.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return {"status": None, "error": f"{type(exc).__name__}: {exc}", "url": url}
    out: dict = {"status": r.status_code, "url": r.url, "bytes": len(r.content)}
    if r.status_code == 200:
        try:
            out["body"] = r.json()
        except ValueError as exc:
            out["error"] = f"geen JSON: {exc}"
    else:
        out["error"] = r.text[:200].replace("\n", " ")
    return out


def _probe_api(session: requests.Session, root: str, bbox: str) -> dict:
    root = root.rstrip("/")
    res: dict = {"root": root}
    coll = _get(session, f"{root}/collections", {"f": "json"})
    res["collectionsStatus"] = coll.get("status")
    if coll.get("error") or not coll.get("body"):
        res["error"] = coll.get("error")
        return res
    cols = coll["body"].get("collections") or []
    res["collectionCount"] = len(cols)
    res["collections"] = {}
    for c in cols[:MAX_COLLECTIONS_PER_API]:
        cid = c.get("id")
        if not cid:
            continue
        items = _get(session, f"{root}/collections/{cid}/items", {"f": "json", "bbox": bbox, "limit": 1})
        entry: dict = {"title": c.get("title"), "itemsStatus": items.get("status")}
        body = items.get("body")
        if items.get("error") or not isinstance(body, dict):
            entry["error"] = items.get("error")
        else:
            feats = body.get("features") or []
            entry["numberReturned"] = body.get("numberReturned", len(feats))
            if "numberMatched" in body:
                entry["numberMatched"] = body["numberMatched"]
            entry["hasNext"] = any(l.get("rel") == "next" for l in body.get("links") or [])
            if feats:
                f0 = feats[0]
                g = f0.get("geometry") or {}
                entry["geometrie"] = g.get("type") or "GEEN-GEOMETRIE"
                entry["props"] = list((f0.get("properties") or {}).keys())[:12]
            else:
                entry["geometrie"] = None
        res["collections"][cid] = entry
    if len(cols) > MAX_COLLECTIONS_PER_API:
        res["collectionsNietGeprobeerd"] = [c.get("id") for c in cols[MAX_COLLECTIONS_PER_API:]]
    return res


def main() -> None:
    here = Path(__file__).resolve().parent
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    session = requests.Session()
    session.headers["User-Agent"] = UA

    # 1. catalogus als-ontvangen (bronze)
    r = session.get(INDEX_URL, timeout=60)
    r.raise_for_status()
    bronze = here / "bronze" / "pdok-catalog" / stamp / "index.json"
    bronze.parent.mkdir(parents=True, exist_ok=True)
    bronze.write_bytes(r.content)
    index = r.json()
    apis = index.get("apis") or []
    by_path = {}
    for a in apis:
        for l in a.get("links") or []:
            if l.get("rel") == "root":
                by_path[l["href"].replace("https://api.pdok.nl/", "").strip("/")] = a

    # 2. kandidaten proberen
    x0, y0, x1, y1 = NSPD_BBOX_WGS84
    bbox = f"{x0},{y0},{x1},{y1}"
    report = {
        "probedAt": now.isoformat(timespec="seconds"),
        "bboxWGS84": list(NSPD_BBOX_WGS84),
        "catalogus": {"url": INDEX_URL, "apiCount": len(apis), "bronze": str(bronze.relative_to(here.parent))},
        "kandidaten": {},
    }
    for pad, meta in KANDIDATEN.items():
        api = by_path.get(pad.strip("/"))
        entry = dict(meta)
        entry["inCatalogus"] = api is not None
        entry["titel"] = api.get("title") if api else None
        entry["keywords"] = (api.get("keywords") or [])[:10] if api else []
        entry.update(_probe_api(session, f"https://api.pdok.nl/{pad}", bbox))
        report["kandidaten"][pad] = entry
        n_hit = sum(1 for c in (entry.get("collections") or {}).values() if (c.get("numberReturned") or 0) > 0)
        print(f"  {pad}: collections HTTP {entry.get('collectionsStatus')}, "
              f"{entry.get('collectionCount', 0)} collecties, {n_hit} met features in bbox")

    out = here / f"probe_pdok_catalog_{now.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschreven: {out}")


if __name__ == "__main__":
    main()
