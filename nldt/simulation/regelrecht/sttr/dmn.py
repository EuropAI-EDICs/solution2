"""STTR/DMN-ontleder: DMN 1.1 én 1.2, STTR v1.0- én v2.0-namespaces.

Werkt op de echte aanleveringen (RuleArts/Sogelink/Geodan-exporters) en de
officiële IPLO-voorbeeldbestanden. Prefixen worden niet aangenomen maar
afgeleid uit de xmlns-declaraties (v1.0 en v2.0 verschillen per STTR-versie);
de DMN-versie volgt uit de dmn-namespace (20151101 = 1.1, 20180521 = 1.2).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

_DMN_VERSIES = {
    "http://www.omg.org/spec/DMN/20151101/dmn.xsd": "1.1",
    "http://www.omg.org/spec/DMN/20180521/MODEL/": "1.2",
}
_STTR_SUFFIXEN = {
    "inter": "Interactieregel",
    "bedr": "Bedrijfsregel",
    "uitv": "Uitvoeringsregel",
    "content": "Content",
}
_OIN_RE = re.compile(r"toepasbare-regels\.omgevingswet\.overheid\.nl/(\d{20})")


class SttrParseFout(RuntimeError):
    pass


def _tekst(elem: ET.Element | None) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _sttr_uris(xml_tekst: str) -> dict[str, str]:
    """URI's van de vier STTR-namespace-families uit de xmlns-declaraties."""
    uris: dict[str, str] = {}
    for prefix, uri in re.findall(r'xmlns:([\w.-]+)="([^"]+)"', xml_tekst[:8000]):
        for familie, suffix in _STTR_SUFFIXEN.items():
            if uri.rstrip("/").endswith("/" + suffix):
                uris[familie] = uri
    return uris


def _type_zonder_feel(type_ref: str | None) -> str:
    t = (type_ref or "").strip()
    return t.removeprefix("feel:").removeprefix("xsd:").lower() or "string"


def parse_sttr(xml_tekst: str) -> dict[str, Any]:
    """Ontleed één STTR-bestand tot een JSON-serialiseerbare structuur."""
    try:
        root = ET.fromstring(xml_tekst)
    except ET.ParseError as e:
        raise SttrParseFout(f"geen geldige xml: {e}") from e

    tag = root.tag
    dmn_uri = tag[1 : tag.index("}")] if tag.startswith("{") else ""
    dmn_versie = _DMN_VERSIES.get(dmn_uri)
    if dmn_versie is None:
        raise SttrParseFout(f"onbekende dmn-namespace: {dmn_uri!r}")

    def D(local: str) -> str:
        return f"{{{dmn_uri}}}{local}"

    nss = _sttr_uris(xml_tekst)

    def V(familie: str, local: str) -> str | None:
        uri = nss.get(familie)
        return f"{{{uri}}}{local}" if uri else None

    oin = None
    m = _OIN_RE.search(root.get("namespace") or "")
    if m:
        oin = m.group(1)

    sttr_versie = None
    bedr_tag = V("bedr", "sttr")
    if bedr_tag:
        for el in root.iter(bedr_tag):
            sttr_versie = el.get("versie")
            break

    # — interactieregels: regelgroepen —
    regelgroepen: list[dict[str, Any]] = []
    inter_groep = V("inter", "regelgroep")
    if inter_groep:
        for g in root.iter(inter_groep):
            naam_tag = V("inter", "naam")
            prio_tag = V("inter", "prioriteit")
            regelgroepen.append(
                {
                    "id": g.get("id"),
                    "naam": _tekst(g.find(naam_tag)) if naam_tag else "",
                    "prioriteit": _tekst(g.find(prio_tag)) if prio_tag else "",
                }
            )

    # — uitvoeringsregels: de vragen —
    uitvoeringsregels: list[dict[str, Any]] = []
    uitvr_tag = V("uitv", "uitvoeringsregel")
    if uitvr_tag:
        for u in root.iter(uitvr_tag):
            rec: dict[str, Any] = {"id": u.get("id")}
            for kind in ("vraag", "vasteWaarde", "geoVerwijzing"):
                tagref = V("uitv", kind)
                if tagref is None:
                    continue
                el = u.find(tagref)
                if el is None:
                    continue
                if kind == "vraag":
                    gd = V("uitv", "gegevensType")
                    vt = V("uitv", "vraagTekst")
                    opties = []
                    if V("uitv", "optie"):
                        for o in el.iter(V("uitv", "optie")):
                            ot = V("uitv", "optieText")
                            opties.append(
                                {
                                    "sequenceId": _tekst(o.find(V("uitv", "sequenceId")))
                                    if V("uitv", "sequenceId")
                                    else "",
                                    "optieText": _tekst(o.find(ot)) if ot else "",
                                }
                            )
                    rec["vraag"] = {
                        "gegevensType": _type_zonder_feel(
                            _tekst(el.find(gd)) if gd else ""
                        ),
                        "vraagTekst": _tekst(el.find(vt)) if vt else "",
                        "opties": opties,
                    }
                elif kind == "vasteWaarde":
                    wv = V("uitv", "waardeVraag")
                    rec["vasteWaarde"] = {
                        "waardeVraag": _tekst(el.find(wv)) if wv else "",
                    }
                    for waarde in ("booleanWaarde", "stringWaarde", "numberWaarde", "dateWaarde"):
                        wt = V("uitv", waarde)
                        if wt is not None and el.find(wt) is not None:
                            rec["vasteWaarde"][waarde] = _tekst(el.find(wt))
                else:  # geoVerwijzing
                    loc = el.find(V("uitv", "locatie")) if V("uitv", "locatie") else None
                    vt = V("uitv", "vraagTekst")
                    rec["geoVerwijzing"] = {
                        "locatieIdentificatie": (loc.get("identificatie") if loc is not None else None),
                        "vraagTekst": _tekst(el.find(vt)) if vt else "",
                    }
            uitvoeringsregels.append(rec)

    # — inputData: koppel vragen aan dmn-variabelen —
    vraag_per_ref: dict[str, dict[str, Any]] = {u["id"]: u for u in uitvoeringsregels}
    invoer_gegevens: list[dict[str, Any]] = []
    for data in root.iter(D("inputData")):
        variabele = data.find(D("variable"))
        rec = {
            "id": data.get("id"),
            "naam": data.get("name"),
            "type": _type_zonder_feel(variabele.get("typeRef") if variabele is not None else None),
        }
        ref_tag = V("uitv", "uitvoeringsregelRef")
        if ref_tag:
            for ref in data.iter(ref_tag):
                href = (ref.get("href") or "").lstrip("#")
                vraag = vraag_per_ref.get(href)
                if vraag and "vraag" in vraag:
                    rec["vraag"] = vraag["vraag"]
                elif vraag and "geoVerwijzing" in vraag:
                    rec["geoVerwijzing"] = vraag["geoVerwijzing"]
        invoer_gegevens.append(rec)

    # — decisions met beslistabellen —
    decisions: list[dict[str, Any]] = []
    for dec in root.iter(D("decision")):
        rec: dict[str, Any] = {
            "id": dec.get("id"),
            "naam": dec.get("name"),
            "vereistInvoer": [],
            "vereistDecisions": [],
        }
        var = dec.find(D("variable"))
        if var is not None:
            rec["type"] = _type_zonder_feel(var.get("typeRef"))
        bedr_ref = V("bedr", "functioneleStructuurRef")
        if bedr_ref:
            for el in dec.iter(bedr_ref):
                rec["functioneleStructuurRef"] = el.get("href")
                break
        for req in dec.iter(D("informationRequirement")):
            for inp in req.iter(D("requiredInput")):
                rec["vereistInvoer"].append((inp.get("href") or "").lstrip("#"))
            for rd in req.iter(D("requiredDecision")):
                rec["vereistDecisions"].append((rd.get("href") or "").lstrip("#"))

        tabel = dec.find(D("decisionTable"))
        if tabel is None:
            rec["tabel"] = None
            decisions.append(rec)
            continue

        invoer: list[dict[str, Any]] = []
        for inp in tabel.iter(D("input")):
            expr = inp.find(D("inputExpression"))
            invoer.append(
                {
                    "label": inp.get("label") or "",
                    "naam": _tekst(expr.find(D("text"))) if expr is not None else "",
                    "type": _type_zonder_feel(expr.get("typeRef") if expr is not None else None),
                }
            )
        uit: list[dict[str, Any]] = []
        for out in tabel.iter(D("output")):
            waarden = _tekst(out.find(D("outputValues")) .find(D("text"))
                             if out.find(D("outputValues")) is not None else None)
            uit.append({"label": out.get("label") or "", "outputValues": waarden})

        rijen: list[dict[str, Any]] = []
        for regel in tabel.iter(D("rule")):
            cellen = [
                _tekst(ie.find(D("text")))
                for ie in regel.iter(D("inputEntry"))
            ]
            uitgangen = [
                _tekst(oe.find(D("text")))
                for oe in regel.iter(D("outputEntry"))
            ]
            annotatie = ""
            for an in regel.iter(D("annotationEntry")):
                annotatie = _tekst(an.find(D("text")))
            rijen.append(
                {"id": regel.get("id"), "cellen": cellen, "uitgangen": uitgangen,
                 "annotatie": annotatie}
            )

        rec["tabel"] = {
            "hitPolicy": tabel.get("hitPolicy") or "UNIQUE",
            "outputLabel": tabel.get("outputLabel") or "",
            "type": _type_zonder_feel(tabel.get("typeRef")),
            "invoer": invoer,
            "uitgangen": uit,
            "rijen": rijen,
        }
        decisions.append(rec)

    kennisbronnen = [ks.get("name") for ks in root.iter(D("knowledgeSource"))]

    return {
        "naam": root.get("name"),
        "oin": oin,
        "dmnVersie": dmn_versie,
        "sttrNamespace": "v2.0" if any("/v2.0/" in u for u in nss.values()) else ("v1.0" if nss else None),
        "sttrVersie": sttr_versie,
        "exporter": root.get("exporter") or None,
        "regelgroepen": regelgroepen,
        "uitvoeringsregels": uitvoeringsregels,
        "inputData": invoer_gegevens,
        "decisions": decisions,
        "kennisbronnen": kennisbronnen,
    }
