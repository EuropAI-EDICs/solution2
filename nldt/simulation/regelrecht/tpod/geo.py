"""GIO-GML lezen en het DSO-punt-in-gebied-feit tegenrekenen (kans 1, eindstap).

De aanlevering (OW-uitwisselpakket) bevat per locatie een GIO-vaststelling in
GML. Bij Eindhoven volgt de koppeling locatie→GML uit de LVBB-
bestandsnaamconventie (GML-bestandsnaam = IMOW-locatie-identificatie); bij
Utrecht zijn de bestandsnamen vrij en is de koppeling alleen registratiezijdig
aanwezig — daar rapporteert de module de onmogelijkheid in plaats van te gokken.

Met het fixture-punt (RD, EPSG:28992 — zelfde CRS als de GML) wordt per
hit-locatie punt-in-polygoon gerekend met shapely en vergeleken met de
DSO-selectie (``geselecteerdeLocatieRefs``): overeenstemming is de
kruisvalidatie van laag 1; conflict is een bevinding, geen fout.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

CONTRACT = "geo-validatie/v1"

_IMOW_NAAM_RE = re.compile(r"^nl\.imow-[a-z0-9]+\.[a-z]+\.[^/]+$")
_GML_NS = "{http://www.opengis.net/gml/3.2}"


def _lokale_tagnaam(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _kind_ring(element: ElementTree.Element, rol: str) -> ElementTree.Element | None:
    """Eerste LinearRing onder <gml:{rol}> (direct of dieper)."""
    for kind in element:
        if _lokale_tagnaam(kind.tag) == rol:
            for kleinkind in kind.iter():
                if _lokale_tagnaam(kleinkind.tag) == "LinearRing":
                    return kleinkind
    return None


def _kind_ringen(element: ElementTree.Element, rol: str) -> list[ElementTree.Element]:
    """Alle LinearRings onder de <gml:{rol}>-kinderen."""
    uit: list[ElementTree.Element] = []
    for kind in element:
        if _lokale_tagnaam(kind.tag) == rol:
            for kleinkind in kind.iter():
                if _lokale_tagnaam(kleinkind.tag) == "LinearRing":
                    uit.append(kleinkind)
    return uit


def _poslist(ring: ElementTree.Element) -> list[tuple[float, float]]:
    tekst = ring.find(f"{_GML_NS}posList")
    if tekst is None or not (tekst.text or "").strip():
        return []
    waarden = tekst.text.split()
    getallen = [float(w) for w in waarden]
    return list(zip(getallen[0::2], getallen[1::2]))


def parse_gml_vorm(data: bytes) -> dict[str, Any] | None:
    """Eén GIO-GML → {"vorm": shapely-shape, "aantalPolygonen": n, "crs": …}.

    Eén GML bestand hoort bij één locatie; alle gml:Polygon-elementen samen
    vormen de locatievorm (union). Zonder parsbare polygonen: None.
    """
    try:
        import shapely
        from shapely.ops import unary_union
    except ImportError:  # pragma: no cover
        raise RuntimeError("shapely is nodig voor tpod.geo (pip install shapely)")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return None
    polygonen = []
    crs = None
    # gml:Polygon (Eindhoven-patroon) en gml:PolygonPatch in gml:Surface/
    # patches (Utrecht-patroon) hebben dezelfde exterior/interior-structuur.
    poly_elementen = [
        el
        for el in root.iter()
        if _lokale_tagnaam(el.tag) in ("Polygon", "PolygonPatch")
    ]
    for poly_el in poly_elementen:
        if crs is None:
            crs = poly_el.get("srsName")
        exterior = _kind_ring(poly_el, "exterior")
        if exterior is None:
            continue
        buiten = _poslist(exterior)
        if len(buiten) < 4:
            continue
        gaten = [
            _poslist(ring)
            for ring in _kind_ringen(poly_el, "interior")
        ]
        gaten = [g for g in gaten if len(g) >= 4]
        try:
            polygonen.append(shapely.Polygon(buiten, gaten))
        except Exception:  # onregelmatige ring: overslaan, nooit gokken
            continue
    if not polygonen:
        return None
    vorm = unary_union([p.buffer(0) for p in polygonen])
    return {"vorm": vorm, "aantalPolygonen": len(polygonen), "crs": crs}


def geo_index_uit_pakket(
    zip_path: Path, *, alleen_imow_namen: bool = True
) -> dict[str, dict[str, Any]]:
    """Zip → {locatieIdentificatie: {vorm, bestand, aantalPolygonen, crs}}.

    Alleen GML's met een IMOW-locatie-identificatie als bestandsnaam
    (LVBB-conventie, kans 1); vrije namen (Utrecht-patroon) kunnen niet
    gekoppeld worden en worden geteld in ``overgeslagen``.
    """
    uit: dict[str, dict[str, Any]] = {}
    overgeslagen = 0
    with zipfile.ZipFile(zip_path) as z:
        for naam in z.namelist():
            if not naam.endswith(".gml") or "/" not in naam:
                continue
            identificatie = naam.rsplit("/", 1)[-1][:-4]
            if alleen_imow_namen and not _IMOW_NAAM_RE.match(identificatie):
                overgeslagen += 1
                continue
            resultaat = parse_gml_vorm(z.read(naam))
            if resultaat is None:
                overgeslagen += 1
                continue
            resultaat.update({"bestand": naam, "locatieIdentificatie": identificatie})
            uit[identificatie] = resultaat
    return {"locaties": uit, "overgeslagen": overgeslagen}


def bevat_punt(vorm: Any, punt: tuple[float, float]) -> bool:
    try:
        import shapely

        return bool(vorm.covers(shapely.Point(punt)))
    except ImportError:  # pragma: no cover
        raise RuntimeError("shapely is nodig voor tpod.geo (pip install shapely)")


def sweep_bevattende_gios(zip_path: Path, punt: tuple[float, float]) -> dict[str, Any]:
    """Alle GIO's in het pakket tegen het punt: registratie-onafhankelijk.

    Los van de locatie-koppeling (die bij Utrecht registratiezijdig is) zegt
    dit wél hoeveel GIO-geometrieën het punt bevatten — de ruwe zonevraag.
    """
    bevatten: list[dict[str, str]] = []
    onderzocht = 0
    ontleedbaar = 0
    with zipfile.ZipFile(zip_path) as z:
        for naam in sorted(z.namelist()):
            if not naam.endswith(".gml") or "/" not in naam:
                continue
            onderzocht += 1
            resultaat = parse_gml_vorm(z.read(naam))
            if resultaat is None:
                continue
            ontleedbaar += 1
            if bevat_punt(resultaat["vorm"], punt):
                bevatten.append(
                    {
                        "bestand": naam,
                        "locatieIdentificatie": naam.rsplit("/", 1)[-1][:-4],
                    }
                )
    return {
        "gioOnderzocht": onderzocht,
        "gioOntleedbaar": ontleedbaar,
        "bevattenPunt": len(bevatten),
        "gmls": bevatten,
    }


def naam_afstemming(
    gebiedsaanwijzingen: list[dict[str, Any]], sweep_gmls: list[dict[str, str]]
) -> dict[str, Any]:
    """Sweep-GML-namen vs hit-gebiedsaanwijzingen, genormaliseerd vergeleken.

    Registratie-onafhankelijke bevestiging van de zonevraag: 'Klein open
    bodemenergiesysteem' ↔ 'locaties_Kleinopenbodemenergiesysteem-v1'.
    Alleen normalisatie (kleine letters, alfanumeriek, suffix -v<getal> eraf);
    geen gis-matching — wat niet exact normaliseert, blijft ongematcht.
    """
    def _slug(tekst: str) -> str:
        tekst = re.sub(r"-v\d+$", "", tekst.strip())
        tekst = re.sub(r"^locaties", "", tekst, flags=re.IGNORECASE)
        return re.sub(r"[^a-z0-9]", "", tekst.lower())

    ga_slugs = {
        _slug(g.get("naam") or ""): g.get("naam") or ""
        for g in gebiedsaanwijzingen
        if g.get("naam")
    }
    gml_slugs = {
        _slug(g.get("locatieIdentificatie") or ""): g.get("locatieIdentificatie") or ""
        for g in sweep_gmls
        if g.get("locatieIdentificatie")
    }
    gedeeld = sorted(set(ga_slugs) & set(gml_slugs))
    return {
        "gebiedsaanwijzingenInHit": len(ga_slugs),
        "sweepGmls": len(gml_slugs),
        "naamOvereenkomend": len(gedeeld),
        "overeenkomsten": [
            {"gebiedsaanwijzing": ga_slugs[s], "gml": gml_slugs[s]} for s in gedeeld
        ],
    }


def valideer_punt(
    geo_index: dict[str, dict[str, Any]],
    *,
    punt: tuple[float, float],
    geselecteerde_refs: list[str],
    hit_locaties: list[dict[str, Any]],
) -> dict[str, Any]:
    """Punt-in-polygoon per hit-locatie, vergeleken met de DSO-selectie."""
    per_locatie: list[dict[str, Any]] = []
    overeenstemming = 0
    conflicten: list[dict[str, Any]] = []
    for loc in hit_locaties:
        ident = loc["identificatie"]
        entry = geo_index["locaties"].get(ident)
        dso = loc.get("geselecteerdOpPunt")
        if entry is None:
            per_locatie.append(
                {
                    "identificatie": ident,
                    "noemer": loc.get("noemer"),
                    "dsoGeselecteerd": dso,
                    "gio": None,
                    "reden": "geen_koppelbare_gml",
                }
            )
            continue
        gio = bevat_punt(entry["vorm"], punt)
        ok = gio == dso
        per_locatie.append(
            {
                "identificatie": ident,
                "noemer": loc.get("noemer"),
                "dsoGeselecteerd": dso,
                "gio": gio,
                "overeenstemming": ok,
            }
        )
        if ok:
            overeenstemming += 1
        else:
            conflicten.append(
                {"identificatie": ident, "dsoGeselecteerd": dso, "gio": gio}
            )
    return {
        "koppeling": {
            "hitLocaties": len(hit_locaties),
            "metKoppelbareGml": sum(
                1 for p in per_locatie if p.get("gio") is not None
            ),
            "gioInPakket": len(geo_index["locaties"]),
            "overgeslagenGml": geo_index["overgeslagen"],
        },
        "validatie": {
            "punt": {"type": "Point", "coordinates": list(punt)},
            "crs": "EPSG:28992",
            "getoetst": sum(1 for p in per_locatie if p.get("gio") is not None),
            "overeenstemming": overeenstemming,
            "conflicten": sorted(conflicten, key=lambda c: c["identificatie"]),
            "perLocatie": sorted(per_locatie, key=lambda p: p["identificatie"]),
        },
        "interpretatie": "Overeenstemming tussen de DSO-puntselectie "
        "(Presenteren) en de aanlevering-GIO's bevestigt laag 1; een conflict "
        "is een bevinding voor het verslag, geen stil gecorrigeerde waarde.",
    }
