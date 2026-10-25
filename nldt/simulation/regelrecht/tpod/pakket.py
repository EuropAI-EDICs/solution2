"""OW-uitwisselpakket (downloaden-API) uitlezen: pons, GIO-geometrie, bestanden.

Het uitwisselpakket is de OW-aanlevering van een omgevingsdocument als zip:
OW-bestanden (IMOW-XML, waaronder de Pons-objecten die aangeven waar oude
bestemmingsplannen niet meer gelden) en GIO-geometrie in GML/GPKG. Dit is de
bron voor kans 2 (pons) en het geometrie-adres van kans 1.

De extractie is verdedigbaar generiek: IMOW-elementen worden op lokale
tagnaam herkend (namespaces verschillen per release), onbekende inhoud wordt
alleen geteld, nooit geïnterpreteerd. Output is een compact
``pakket-index`` (``<stem>.pakket-index.json``); de zip zelf blijft in de
cache (bronze in de lake).
"""
from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

CONTRACT = "pakket-index/v1"


def _lokale_tagnaam(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _tekst(element: ElementTree.Element) -> str:
    return (element.text or "").strip()


def _ref_waarden(element: ElementTree.Element) -> list[str]:
    """xlink-href-attributen of tekst van ref-achtige kindelementen."""
    waarden: list[str] = []
    for kind in element.iter():
        lokaal = _lokale_tagnaam(kind.tag)
        if lokaal.endswith("Ref"):
            href = kind.attrib.get(
                "{http://www.w3.org/1999/xlink}href"
            ) or kind.attrib.get("href")
            if href:
                waarden.append(href)
            elif _tekst(kind):
                waarden.append(_tekst(kind))
    return sorted(set(waarden))


def parse_ow_xml(data: bytes) -> dict[str, Any]:
    """Eén OW-XML-bestand: pons-objecten, overige owObject-typen, identificaties."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return {"ontleed": False}
    pons: list[dict[str, Any]] = []
    overig: list[str] = []
    for element in root.iter():
        lokaal = _lokale_tagnaam(element.tag)
        if lokaal == "Pons":
            identificatie = ""
            naam = ""
            for kind in element.iter():
                k = _lokale_tagnaam(kind.tag)
                if k == "identificatie" and not identificatie:
                    identificatie = _tekst(kind)
                elif k == "naam" and not naam:
                    naam = _tekst(kind)
            pons.append(
                {
                    "identificatie": identificatie,
                    "naam": naam,
                    "locatieRefs": _ref_waarden(element),
                }
            )
        elif lokaal in {
            "RegelVoorIedereen",
            "Instructieregel",
            "Omgevingswaarderegel",
            "Activiteit",
            "Gebiedsaanwijzing",
            "Omgevingsnorm",
            "Omgevingswaarde",
            "Kaart",
            "Divisie",
            "Regeltekst",
            "Divisietekst",
            "Gebied",
            "Lijn",
            "Punt",
            "Gebiedengroep",
            "Lijngroep",
            "Puntengroep",
            "Ambtsgebied",
            "Regelingsgebied",
            "SymbolisatieItem",
            "Hoofdlijn",
        }:
            overig.append(lokaal)
    return {"ontleed": True, "pons": pons, "owObjectTypen": overig}


def extract_pakket(zip_path: Path) -> dict[str, Any]:
    """Hele zip → compacte pakket-index (pons + GIO + bestandstypes)."""
    bestanden: Counter[str] = Counter()
    pons: list[dict[str, Any]] = []
    gio: list[dict[str, str]] = []
    ow_bestanden = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            naam = info.filename
            suffix = naam.rsplit(".", 1)[-1].lower() if "." in naam else ""
            bestanden[suffix] = bestanden.get(suffix, 0) + 1
            if suffix == "xml":
                resultaat = parse_ow_xml(z.read(info))
                if resultaat.get("ontleed"):
                    ow_bestanden += 1
                    pons.extend(resultaat.get("pons") or [])
            elif suffix in {"gml", "gpkg"}:
                gio.append(
                    {
                        "bestand": naam,
                        # GML-bestandsnaam = IMOW-locatie-identificatie
                        "locatieIdentificatie": naam.rsplit(".", 1)[0]
                        if "/" not in naam.rsplit(".", 1)[0]
                        else naam.rsplit("/", 1)[-1].rsplit(".", 1)[0],
                    }
                )
    pons.sort(key=lambda p: p.get("identificatie") or "")
    gio.sort(key=lambda g: g["bestand"])
    return {
        "contract": CONTRACT,
        "bron": {"zip": zip_path.name},
        "bestanden": dict(sorted(bestanden.items())),
        "owBestanden": ow_bestanden,
        "pons": {
            "beschikbaar": bool(pons),
            "aantal": len(pons),
            "objecten": pons,
            "opmerking": (
                "geen Pons-objecten in de aanlevering" if not pons else None
            ),
        },
        "gio": gio,
    }


def schrijf_pakket_index(zip_path: Path, out_path: Path) -> dict[str, Any]:
    index = extract_pakket(zip_path)
    out_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return index
