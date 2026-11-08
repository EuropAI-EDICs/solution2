"""RegelRecht → STTR: executions serialiseren als STTR 3.0/DMN 1.2-beslistabel.

De omgekeerde brug (docs/POC_STTR_IMTR_KANSEN.md, kans 2 — autorauteitsroute):
precies de vier operatoren die de import op de engine projecteert, worden hier
geserialiseerd naar de officiële vorm — v2.0-namespaces, ``bedr:sttr versie="3"``,
``uitv:uitvoeringsregels`` als vragen, ANY-hit booleaanse tabellen, en
``annotationEntry``/``knowledgeSource`` met het artikelanker. Twee garanties:

- **XSD**: het resultaat valideert tegen de vastgepinnde ``DMN_v12.xsd`` —
  hetzelfde schema dat de officiële IPLO-voorbeelden keurt.
- **Roundtrip**: export → eigen parser → eigen projectie moet per
  invoercombinatie dezélfde engine-uitkomst geven (zie de tests).

Eerlijke grens: dit is het mechanisme voor toekomstige, échte toepasbare regels;
de huidige Eindhovense artikel-executies zijn RFOV/conversie-feiten en horen
niet zomaar de RTR in (zie de notitie).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr

from nldt.simulation.regelrecht.sttr.dmn import parse_sttr
from nldt.simulation.regelrecht.sttr.executie import projecteer_decision

DMN12_NS = "http://www.omg.org/spec/DMN/20180521/MODEL/"
STTR_V2 = "http://toepasbare-regels.omgevingswet.overheid.nl/v2.0"
XSD_DIR = (
    Path(__file__).resolve().parents[4]
    / "docs" / "research" / "sttr-imtr" / "xsd-sttr-3.0" / "XSD 3.0 2025-05-01"
)

_FEEL_TYPE = {"boolean": "boolean", "number": "number", "string": "string"}


class ExportFout(RuntimeError):
    """Executie buiten het exporteerbare Domein — nooit gissen."""


def _num(waarde: float) -> str:
    return f"{waarde:g}"


def _vraag_tekst(invoer: dict[str, Any]) -> str:
    tekst = (invoer.get("description") or invoer.get("name") or "").strip()
    return " ".join(tekst.split())[:240] or str(invoer.get("name"))


def _cel_voor(conditie: dict[str, Any], invoer_namen: set[str]) -> tuple[str, str]:
    """Eén engine-conditie → (invoernaam, FEEL-celtekst)."""
    subject = conditie.get("subject", "")
    if not isinstance(subject, str) or not subject.startswith("$"):
        raise ExportFout(f"conditie zonder $-subject: {conditie!r}")
    naam = subject[1:]
    if naam not in invoer_namen:
        raise ExportFout(f"subject {naam!r} is niet als input gedeclareerd")
    waarde = conditie.get("value")
    op = conditie.get("operation")
    if op == "EQUALS":
        if isinstance(waarde, bool):
            return naam, "true" if waarde else "false"
        if isinstance(waarde, (int, float)):
            return naam, _num(float(waarde))
        return naam, f'"{waarde}"'
    if op == "LESS_THAN_OR_EQUAL":
        if not isinstance(waarde, (int, float)):
            raise ExportFout(f"<= met niet-numerieke waarde: {waarde!r}")
        return naam, f"<= {_num(float(waarde))}"
    raise ExportFout(f"operatie {op!r} is niet exporteerbaar")


def _condities(node: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        raise ExportFout(f"geen conditieknooppunt: {node!r}")
    if node.get("operation") == "AND":
        return node.get("conditions") or []
    return [node]


def _rijen_uit_value(
    value: Any, invoer_namen: set[str]
) -> list[tuple[dict[str, str], bool]]:
    """Action-waarde → rijen [(celtekst per invoernaam, uitgang)] voor een
    ANY-hit booleaanse tabel; vangnetrij (alles '-') sluit af."""
    if not isinstance(value, dict) or "operation" not in value:
        raise ExportFout(f"action-waarde is geen operatie: {value!r}")
    op = value["operation"]

    def _check_bool(w: Any, wat: str) -> bool:
        if not isinstance(w, bool):
            raise ExportFout(f"{wat} is niet booleaans — ANY boolean-tabel vereist bool")
        return w

    rijen: list[tuple[dict[str, str], bool]] = []
    if op == "IF":
        for case in value.get("cases") or []:
            cellen: dict[str, str] = {}
            for conditie in _condities(case.get("when") or {}):
                naam, tekst = _cel_voor(conditie, invoer_namen)
                if naam in cellen:
                    raise ExportFout(f"invoer {naam!r} dubbelt in één rij")
                cellen[naam] = tekst
            rijen.append((cellen, _check_bool(case.get("then"), "then")))
        rijen.append(({}, _check_bool(value.get("default"), "default")))
        return rijen
    if op == "AND":
        cellen = {}
        for conditie in _condities(value):
            naam, tekst = _cel_voor(conditie, invoer_namen)
            if naam in cellen:
                raise ExportFout(f"invoer {naam!r} dubbelt in één rij")
            cellen[naam] = tekst
        return [(cellen, True), ({}, False)]
    if op in ("EQUALS", "LESS_THAN_OR_EQUAL"):
        naam, tekst = _cel_voor(value, invoer_namen)
        return [({naam: tekst}, True), ({}, False)]
    raise ExportFout(f"operatie {op!r} is niet exporteerbaar")


def export_document(
    artikelen: list[dict[str, Any]],
    *,
    oin: str,
    naam: str,
    versie: str = "3",
    regelgroep: str = "RegelRecht-export",
) -> str:
    """Artikelen met ``machine_readable``-executie → STTR 3.0/DMN 1.2-document.

    Elk artikel: ``{"naam": "art. 1.8", "anker": "CVDR696400/4 art. 1.8",
    "execution": {…}}`` (regelrecht-vorm: input/output/actions).
    """
    if not (isinstance(oin, str) and len(oin) == 20 and oin.isdigit()):
        raise ExportFout(f"OIN moet 20 cijfers zijn: {oin!r}")
    if not artikelen:
        raise ExportFout("geen artikelen om te exporteren")

    invoer: dict[str, dict[str, Any]] = {}
    for art in artikelen:
        ex = art.get("execution") or {}
        if not (ex.get("input") and ex.get("output") and ex.get("actions")):
            raise ExportFout(f"artikel {art.get('naam')!r} heeft geen volledige execution")
        for iv in ex["input"]:
            if iv["name"] in invoer:
                continue
            soort = _FEEL_TYPE.get(str(iv.get("type")))
            if soort is None:
                raise ExportFout(f"invoertype {iv.get('type')!r} niet exporteerbaar")
            invoer[iv["name"]] = {"type": soort, "vraag": _vraag_tekst(iv)}
        for uit in ex["output"]:
            if not isinstance(uit.get("type"), str) or _FEEL_TYPE.get(uit["type"]) is None:
                raise ExportFout(f"uitgangtype {uit.get('type')!r} niet exporteerbaar")

    regels: list[str] = []
    regels.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    regels.append(
        f'<dmn:definitions xmlns:dmn={quoteattr(DMN12_NS)}\n'
        f'                 xmlns:inter={quoteattr(STTR_V2 + "/Interactieregel")}\n'
        f'                 xmlns:bedr={quoteattr(STTR_V2 + "/Bedrijfsregel")}\n'
        f'                 xmlns:uitv={quoteattr(STTR_V2 + "/Uitvoeringsregel")}\n'
        f'                 xmlns:content={quoteattr(STTR_V2 + "/Content")}\n'
        f'                 xmlns={quoteattr("http://toepasbare-regels.omgevingswet.overheid.nl/" + oin)}\n'
        f'                 namespace={quoteattr("http://toepasbare-regels.omgevingswet.overheid.nl/" + oin)}\n'
        f'                 name={quoteattr(naam)}>'
    )
    regels.append("  <dmn:extensionElements>")
    regels.append(f'    <bedr:sttr versie={quoteattr(str(versie))}/>')
    regels.append("    <inter:regelgroepen>")
    regels.append('      <inter:regelgroep id="groep1">')
    regels.append(f"        <inter:naam>{escape(regelgroep)}</inter:naam>")
    regels.append("        <inter:prioriteit>1</inter:prioriteit>")
    regels.append("      </inter:regelgroep>")
    regels.append("    </inter:regelgroepen>")
    regels.append("    <uitv:uitvoeringsregels>")
    for i, (naam_iv, iv) in enumerate(invoer.items(), start=1):
        regels.append(f'      <uitv:uitvoeringsregel id="uitv_{i}">')
        regels.append('        <uitv:regelgroepRef href="#groep1"/>')
        regels.append(f"        <inter:prioriteit>{10 * i}</inter:prioriteit>")
        regels.append("        <uitv:vraag>")
        regels.append(f"          <uitv:gegevensType>{escape(iv['type'])}</uitv:gegevensType>")
        regels.append(f"          <uitv:vraagTekst>{escape(iv['vraag'])}</uitv:vraagTekst>")
        regels.append("        </uitv:vraag>")
        regels.append("      </uitv:uitvoeringsregel>")
    regels.append("    </uitv:uitvoeringsregels>")
    regels.append("  </dmn:extensionElements>")

    for i, naam_iv in enumerate(invoer, start=1):
        regels.append(f'  <dmn:inputData id="input_{i}" name={quoteattr(naam_iv)}>')
        regels.append("    <dmn:extensionElements>")
        regels.append(f'      <uitv:uitvoeringsregelRef href="#uitv_{i}"/>')
        regels.append("    </dmn:extensionElements>")
        regels.append(
            f'    <dmn:variable id="var_{i}" name={quoteattr(naam_iv)} '
            f'typeRef={quoteattr(invoer[naam_iv]["type"])}/>'
        )
        regels.append("  </dmn:inputData>")

    for d, art in enumerate(artikelen, start=1):
        ex = art["execution"]
        uit_naam = ex["output"][0]["name"]
        eigen_invoer = [iv["name"] for iv in ex["input"]]
        rijen = _rijen_uit_value(ex["actions"][0]["value"], set(invoer))
        anker = art.get("anker") or art.get("naam") or ""
        regels.append(f'  <dmn:decision id="dec_{d}" name={quoteattr(uit_naam)}>')
        regels.append(
            f'    <dmn:variable id="dvar_{d}" name={quoteattr(uit_naam)} '
            f'typeRef={quoteattr(_FEEL_TYPE[ex["output"][0]["type"]])}/>'
        )
        for naam_iv in eigen_invoer:
            i = list(invoer).index(naam_iv) + 1
            regels.append(
                f'    <dmn:informationRequirement><dmn:requiredInput href="#input_{i}"/>'
                f"</dmn:informationRequirement>"
            )
        regels.append(
            f'    <dmn:decisionTable hitPolicy="ANY" id="tbl_{d}" '
            f'outputLabel={quoteattr(uit_naam)} '
            f'typeRef={quoteattr(_FEEL_TYPE[ex["output"][0]["type"]])}>'
        )
        for j, naam_iv in enumerate(eigen_invoer, start=1):
            regels.append(
                f'      <dmn:input id="in_{d}_{j}" label={quoteattr(invoer[naam_iv]["vraag"])}>'
            )
            regels.append(
                f'        <dmn:inputExpression typeRef={quoteattr(invoer[naam_iv]["type"])}>'
                f"<dmn:text>{escape(naam_iv)}</dmn:text></dmn:inputExpression>"
            )
            regels.append("      </dmn:input>")
        regels.append(f'      <dmn:output id="out_{d}" label={quoteattr(uit_naam)}/>')
        for r, (cellen, uitgang) in enumerate(rijen, start=1):
            regels.append(f'      <dmn:rule id="r_{d}_{r}">')
            for j, naam_iv in enumerate(eigen_invoer, start=1):
                tekst = cellen.get(naam_iv, "-")
                regels.append(
                    f'        <dmn:inputEntry id="c_{d}_{r}_{j}">'
                    f"<dmn:text>{escape(tekst)}</dmn:text></dmn:inputEntry>"
                )
            regels.append(
                f'        <dmn:outputEntry id="o_{d}_{r}">'
                f"<dmn:text>{'true' if uitgang else 'false'}</dmn:text></dmn:outputEntry>"
            )
            regels.append(
                f"        <dmn:annotationEntry><dmn:text>{escape(anker)}</dmn:text>"
                f"</dmn:annotationEntry>"
            )
            regels.append("      </dmn:rule>")
        regels.append("    </dmn:decisionTable>")
        regels.append("  </dmn:decision>")
        if anker:
            regels.append(f'  <dmn:knowledgeSource id="ks_{d}" name={quoteattr(anker)}>')
            regels.append(
                f'    <dmn:authorityRequirement><dmn:requiredDecision href="#dec_{d}"/>'
                f"</dmn:authorityRequirement>"
            )
            regels.append("  </dmn:knowledgeSource>")

    regels.append("</dmn:definitions>")
    return "\n".join(regels) + "\n"


def valideer_tegen_xsd(
    xml_tekst: str, *, xsd_pad: Path = XSD_DIR / "DMN_v12.xsd"
) -> list[str]:
    """Valideer tegen de vastgepinnde XSD (lxml); return foutregels (leeg = geldig)."""
    from lxml import etree

    schema = etree.XMLSchema(etree.parse(str(xsd_pad)))
    doc = etree.fromstring(xml_tekst.encode("utf-8"))
    if schema.validate(doc):
        return []
    return [str(e) for e in schema.error_log]


def roundtrip_verschil(
    execution: dict[str, Any], xml_tekst: str, combinaties: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Vergelijk engine-uitkomsten origineel vs. teruggelezen export per combinatie.

    Return alleen de verschillen (leeg = roundtrip exact). Geen interpretatie:
    elke afwijking is een verschilrij.
    """
    from nldt.simulation.regelrecht import reference_engine

    parsed = parse_sttr(xml_tekst)
    doel = execution["output"][0]["name"]
    kandidaten = [d for d in parsed.get("decisions") or [] if d.get("naam") == doel]
    if not kandidaten:
        raise ExportFout(f"beslissing {doel!r} niet teruggevonden in de export")
    projectie = projecteer_decision(kandidaten[0])
    if not projectie.get("projecteerbaar"):
        raise ExportFout(f"teruggelezen export projecteert niet: {projectie.get('reden')}")

    # De export zet de vraag-tekst als kolomlabel (Eindhovens idioom); de
    # teruggelezen projectie noemt de invoer naar dat label. Vertaal de
    # combinatie-sleutels één-op-één langs de kolomvolgorde.
    namen_origineel = [iv["name"] for iv in execution["input"]]
    namen_terug = [iv["name"] for iv in projectie["execution"]["input"]]
    if len(namen_origineel) != len(namen_terug):
        raise ExportFout(
            f"aantal invoerkolommen wijkt af na roundtrip: "
            f"{len(namen_origineel)} ≠ {len(namen_terug)}"
        )
    vertaling = dict(zip(namen_origineel, namen_terug))

    verschillen: list[dict[str, Any]] = []
    for combinatie in combinaties:
        onbekend = [k for k in combinatie if k not in vertaling]
        if onbekend:
            raise ExportFout(
                f"combinatie-sleutel(s) {onbekend!r} zijn geen invoer van de executie"
            )
        origineel = reference_engine.evaluate(execution, dict(combinatie))["outputs"][doel]
        terug_invoer = {vertaling[k]: v for k, v in combinatie.items()}
        terug = reference_engine.evaluate(projectie["execution"], terug_invoer)["outputs"][doel]
        if origineel != terug:
            verschillen.append(
                {"invoer": combinatie, "origineel": origineel, "teruggelezen": terug}
            )
    return verschillen
