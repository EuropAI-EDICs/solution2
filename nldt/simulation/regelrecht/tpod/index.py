"""TpOD-index: de IMOW-annotatielaag van een instrument als één herhaalbaar artefact.

Bouwt uit een gecacht Presenteren-antwoord (en optioneel de PoC-artefacten
formalization-report en artikelen-export) een ``tpod-index``:

- **wId-anchoring** (kans 3): per artikelnummer de regelteksten (incl. lid)
  waarop de DSO-hit ze verankert — de officiële opvolger van het
  artikelnummer-regex-join in ``dso_overlap/overlap.py``;
- **artikelprofielen**: per artikel de regels, leden, activiteitsgroepen,
  locatieRefs en gebiedsaanwijzingen, plus de RegelRecht-formaliseringsstatus
  (formalized uit het report; ``null`` = niet in report);
- **activiteitstructuur** (kans 4): tophaak, boomdiepte en groepen — het
  officiële equivalent van de thema-clusters in de Eindhoven-PoC;
- **geo-feiten** (kans 1): de locaties die het bevraagde punt bevatten
  (punt-in-gebied volgens de DSO) met hun GIO-geometrie-referentie;
- **pons** (kans 2): expliciet ``beschikbaar: false`` zolang ze niet aangeleverd
  zijn; met het OW-uitwisselpakket (downloaden-API) wél echt;
- **documentstructuur** (kans 3, optioneel): de hele-instrument wId-boom uit
  het Presenteren-documentstructuur-endpoint — anchoring los van het punt.

Deterministisch en offline: alles volgt uit de ingegeven payloads.
"""
from __future__ import annotations

from typing import Any

from . import annotaties

CONTRACT = "tpod-index/v1"


def build_index(
    *,
    instrument_id: str,
    instrument: dict[str, Any],
    locatie: dict[str, Any] | None,
    annotaties_payload: dict[str, Any],
    annotaties_sha256: str,
    gegenereerd_op: str,
    formalization_report: dict[str, Any] | None = None,
    artikelen: dict[str, Any] | None = None,
    documentstructuur: dict[str, Any] | None = None,
    pakket_index: dict[str, Any] | None = None,
    extra_inputen: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    regelteksten = annotaties.parse_regelteksten(annotaties_payload)
    regels = annotaties.parse_regels(annotaties_payload)
    structuur = annotaties.activiteit_structuur(annotaties_payload)
    feiten = annotaties.geo_feiten(annotaties_payload)
    pons = annotaties.pons_annotaties(annotaties_payload)
    gio_by_loc: dict[str, str] = {}
    if pakket_index is not None:
        # uit het OW-uitwisselpakket (downloaden-API): overtreft de punt-cache
        pons = pakket_index.get("pons") or pons
        gio_by_loc = {
            g["locatieIdentificatie"]: g["bestand"]
            for g in pakket_index.get("gio") or []
            if g.get("locatieIdentificatie")
        }
        for loc in feiten["locaties"]:
            loc["gmlBestand"] = gio_by_loc.get(loc["identificatie"])
        feiten["gioInPakket"] = len(gio_by_loc)

    tekst_by_id = {rt["identificatie"]: rt for rt in regelteksten}
    groep_by_id = {
        a.get("identificatie"): (a.get("groep") or {}).get("waarde")
        for a in (annotaties_payload.get("activiteiten") or [])
    }
    ga_naam_by_ref = {
        g["identificatie"]: g["naam"] for g in feiten["gebiedsaanwijzingen"]
    }
    ambtsgebied = feiten["ambtsgebiedRef"]

    # --- artikelprofielen: regels gegroepeerd op artikelnummer (wId-anchoring)
    per_artikel: dict[str, dict[str, Any]] = {}
    regels_zonder_tekst = 0
    for regel in regels:
        if not regel["tekstInPayload"]:
            regels_zonder_tekst += 1
        num = regel["artikel"]
        if num is None:
            continue
        profiel = per_artikel.setdefault(
            num,
            {
                "artikel": num,
                "hoofdstuk": regeltekst_hoofdstuk(tekst_by_id, regel),
                "leden": [],
                "aantalRegels": 0,
                "activiteitGroepen": set(),
                "locatieRefs": set(),
                "gebiedsaanwijzingen": set(),
            },
        )
        profiel["aantalRegels"] += 1
        if regel["lid"] is not None and regel["lid"] not in profiel["leden"]:
            profiel["leden"].append(regel["lid"])
        for ref in regel["activiteitRefs"]:
            groep = groep_by_id.get(ref)
            if groep:
                profiel["activiteitGroepen"].add(groep)
        for ref in regel["locatieRefs"]:
            if ref != ambtsgebied:  # ambtsgebied = "heel Eindhoven", geen signaal
                profiel["locatieRefs"].add(ref)
        for ref in regel["gebiedsaanwijzingRefs"]:
            naam = ga_naam_by_ref.get(ref, ref)
            profiel["gebiedsaanwijzingen"].add(naam)

    status_by_num: dict[str, dict[str, Any]] = {}
    if formalization_report:
        status_by_num = {
            a["number"]: a for a in formalization_report.get("articles") or []
        }

    artikel_profielen: list[dict[str, Any]] = []
    for num in sorted(per_artikel, key=artikel_sleutel):
        profiel = per_artikel[num]
        status = status_by_num.get(num)
        artikel_profielen.append(
            {
                "artikel": profiel["artikel"],
                "hoofdstuk": profiel["hoofdstuk"],
                "leden": sorted(profiel["leden"], key=artikel_sleutel),
                "aantalRegels": profiel["aantalRegels"],
                "activiteitGroepen": sorted(profiel["activiteitGroepen"]),
                "locatieRefs": sorted(profiel["locatieRefs"]),
                "gebiedsaanwijzingen": sorted(profiel["gebiedsaanwijzingen"]),
                "formalized": (status.get("status") == "formalized")
                if status
                else None,
                "rrStatus": status.get("status") if status else None,
            }
        )

    # --- aggregaten
    met_lid = sum(1 for rt in regelteksten if rt["lid"] is not None)
    hit_artikelen = {p["artikel"] for p in artikel_profielen}
    poc_artikelen: set[str] = set()
    if artikelen:
        poc_artikelen = {
            a["number"] for a in artikelen.get("articles") or [] if a.get("number")
        }
    formalized_in_hit = {p["artikel"] for p in artikel_profielen if p["formalized"]}

    index: dict[str, Any] = {
        "contract": CONTRACT,
        "instrument": {
            "id": instrument_id,
            "label": instrument["label"],
            "aknUri": instrument["akn_uri"],
            "aknPath": instrument["akn_path"],
            "cvdr": instrument["cvdr"],
            "bevoegdGezag": instrument["bevoegd_gezag"],
        },
        "locatie": {
            "id": (locatie or {}).get("id"),
            "notes": (locatie or {}).get("notes"),
        },
        "gegenereerdOp": gegenereerd_op,
        "bron": {
            "annotatiesSha256": annotaties_sha256,
            "presentatieScope": "annotaties die op de bevraagde geometrie van "
            "toepassing zijn — de hele instrument-populatie zit hier niet in",
        },
        "regelteksten": {
            "aantal": len(regelteksten),
            "artikelen": len(hit_artikelen),
            "metLid": met_lid,
            "zonderLid": len(regelteksten) - met_lid,
            "zonderArtikel": sum(1 for rt in regelteksten if rt["artikel"] is None),
        },
        "regels": {
            "aantal": len(regels),
            "regelVoorIedereen": sum(
                1 for r in regels if r["soort"] == "regelVoorIedereen"
            ),
            "instructieregel": sum(
                1 for r in regels if r["soort"] == "instructieregel"
            ),
            "metActiviteiten": sum(1 for r in regels if r["activiteitRefs"]),
            "zonderTekstInPayload": regels_zonder_tekst,
        },
        "artikelProfielen": artikel_profielen,
        "hitCoverage": {
            "pocArtikelen": len(poc_artikelen) if artikelen else None,
            "pocArtikelenInHit": len(poc_artikelen & hit_artikelen)
            if artikelen
            else None,
            "formalizedInHit": len(formalized_in_hit),
            "toelichting": "Punt-hit: overlap tussen de PoC-artikelenpopulatie "
            "(volledige instrument-export) en wat de DSO op dit punt annoteert.",
        },
        "activiteiten": structuur,
        "geoFeiten": feiten,
        "pons": pons,
        "inputs": extra_inputen or [],
    }
    if documentstructuur is not None:
        index["documentstructuur"] = documentstructuur
    return index


def regeltekst_hoofdstuk(
    tekst_by_id: dict[str, dict[str, Any]], regel: dict[str, Any]
) -> str | None:
    rt = tekst_by_id.get(regel["regeltekstRef"])
    return rt.get("hoofdstuk") if rt else None


def artikel_sleutel(num: str) -> tuple[int, ...]:
    """Sorteert artikelnummers numeriek ('10.2' na '9.9')."""
    delen: list[int] = []
    for stuk in str(num).split("."):
        try:
            delen.append(int(stuk))
        except ValueError:
            delen.append(-1)
    return tuple(delen)
