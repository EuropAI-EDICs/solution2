#!/usr/bin/env python3
"""Extraheert het Conceptueel Informatiemodel VTH Fysieke Leefomgeving (CIm VTH FLo)
uit de AVG-geanonimiseerde publicatie-PDF naar machine-leesbaar JSON.

Patroon volgt het RegelRecht-schema-pin (nldt/simulation/regelrecht/schema/):
het resultaat wordt vastgepind onder nldt/references/cim-vth-flo/<versie>/
en getest in nldt/tests/test_cim_vth_flo.py.

Gebruik (vanuit de repo-root):

    python3 nldt/scripts/extract_cim_vth_flo.py [--pdf PAD] [--out DIR]

Standaard-PDF: docs/EvT Conceptueel Informatiemodel Fysieke Leefomgeving VTH
0.9.1 07-2025 AVG.pdf. Standaard-uitvoermap: nldt/references/cim-vth-flo/0.9.1/.

Vereist pdftotext (poppler). Het script is deterministisch: geen tijdstempels
in model.json, zodat regeneratie een byte-stabiel bestand oplevert.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = (
    REPO_ROOT
    / "docs"
    / "EvT Conceptueel Informatiemodel Fysieke Leefomgeving VTH 0.9.1 07-2025 AVG.pdf"
)
DEFAULT_OUT = REPO_ROOT / "nldt" / "references" / "cim-vth-flo" / "0.9.1"

VERSIE = "0.9.1"

# Voettekst-/kopregels die pdftotext tussen de inhoud door laat invallen.
_FOOTER_RE = re.compile(
    r"^\s*(?:Pagina \d+ van \d+"
    r"|PROGRAMMA DIGITAAL VTH-STELSEL MILIEU \| CIM VTH FLO VERSIE 0\.9\.1( CONCEPT)?)\s*$"
)

# Bekende labels uit de key-value blokken in h4/h5/h6 (MIM-kenmerken).
LABELS = [
    "Naam",
    "Mnemonic",
    "Herkomst",
    "Gerelateerd objecttype",
    "Definitie",
    "Herkomst definitie",
    "Datum opname",
    "Unieke aanduiding",
    "Data locatie",
    "Mogelijk geen waarde",
    "Indicatie abstract object",
    "Indicatie kardinaliteit",
    "Indicatie authentiek",
    "Indicatie materiële historie",
    "Indicatie formele historie",
    "Indicatie in onderzoek",
    "Aanduiding strijdigheid/nietigheid",
    "Lengte",
    "Formaat",
    "Patroon",
    "Indicatie afleidbaar",
    "Waarde afleidbaar",
    "Regels",
    "Toelichting",
]
_LABEL_RE = re.compile(r"^(" + "|".join(re.escape(l) for l in LABELS) + r")\s{2,}(.*)$")
_LABEL_ONLY_RE = re.compile(
    r"^(" + "|".join(re.escape(l) for l in LABELS) + r")\s*$"
)

# Blokkoppen binnen een h5/h6-sectie.
_BLOCK_HEADER_RE = re.compile(
    r"^(Attribuutsoort details|Relatiesoort details|Referentie element) (.+)$"
)
# Subsectie-/hoofdstukkoppen die een blok of sectie afsluiten (alleen op kolom 0).
_SECTION_RE = re.compile(r"^\d+(?:\.\d+)*\s+\S")

# Vertaling label -> JSON-sleutel (camelCase, dicht bij MIM-terminologie).
LABEL_KEYS = {
    "Naam": "naam",
    "Mnemonic": "mnemonic",
    "Herkomst": "herkomst",
    "Gerelateerd objecttype": "gerelateerdObjecttype",
    "Definitie": "definitie",
    "Herkomst definitie": "herkomstDefinitie",
    "Datum opname": "datumOpname",
    "Unieke aanduiding": "uniekeAanduiding",
    "Data locatie": "dataLocatie",
    "Mogelijk geen waarde": "mogelijkGeenWaarde",
    "Indicatie abstract object": "indicatieAbstractObject",
    "Indicatie kardinaliteit": "kardinaliteit",
    "Indicatie authentiek": "indicatieAuthentiek",
    "Indicatie materiële historie": "indicateMaterieleHistorie",
    "Indicatie formele historie": "indicatieFormeleHistorie",
    "Indicatie in onderzoek": "indicatieInOnderzoek",
    "Aanduiding strijdigheid/nietigheid": "aanduidingStrijdigheidNietigheid",
    "Lengte": "lengte",
    "Formaat": "formaat",
    "Patroon": "patroon",
    "Indicatie afleidbaar": "indicatieAfleidbaar",
    "Waarde afleidbaar": "waardeAfleidbaar",
    "Regels": "regels",
    "Toelichting": "toelichting",
}
# Labels met lege waarde die we niet opnemen.
_DROP_EMPTY = {
    "mnemonic",
    "dataLocatie",
    "lengte",
    "patroon",
    "regels",
    "aanduidingStrijdigheidNietigheid",
    "indicatieInOnderzoek",
    "indicatieAfleidbaar",
    "herkomstDefinitie",
    "datumOpname",
}
_DROP_EMPTY.update(
    [
        "indicateMaterieleHistorie",
        "indicatieFormeleHistorie",
        "mogelijkGeenWaarde",
        "indicatieAbstractObject",
        "waardeAfleidbaar",
    ]
)


def _ja_nee(value: str):
    v = value.strip().lower()
    if v == "ja":
        return True
    if v == "nee":
        return False
    return value.strip() if value.strip() else None


def extract_text(pdf: Path) -> str:
    """pdftotext -layout over de PDF; voetregels eruit."""
    proc = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln for ln in proc.stdout.splitlines() if not _FOOTER_RE.match(ln)]
    return "\n".join(lines)


def body_start(lines: list[str]) -> int:
    """Index van de eerste inhoudsregel na het voorwerk (inhoudsopgave)."""
    for i, ln in enumerate(lines):
        if re.match(r"^Inhoud\s*$", ln):
            for j in range(i + 1, len(lines)):
                if re.match(r"^1\s+Inleiding\s*$", lines[j]):
                    return j
    raise ValueError("Kon begin van de tekst (na inhoudsopgave) niet vinden")


def find_sections(lines: list[str], chapter: str) -> "OrderedDict[str, list[str]]":
    """Secties van een hoofdstuk: nummer -> regels (exclusief kopregel).

    Alleen kopregels op kolom 0 zonder puntrechtse ('....') uit de inhoudsopgave.
    """
    pattern = re.compile(rf"^{chapter}(\d+(?:\.\d+)*)\s+(\S.*?)\s*$")
    sections: OrderedDict[str, dict] = OrderedDict()
    start = body_start(lines)
    current = None
    for i in range(start, len(lines)):
        m = pattern.match(lines[i])
        if not m or "..." in lines[i]:
            continue
        num, title = m.group(1), m.group(2)
        if current is not None:
            sections[current]["end"] = i
        # "5.8.1 Gegevensgroeptype Adres": nummer 8.1 valt onder 5.8; de
        # sectietabel houdt ze apart via het volledige nummer als sleutel.
        sections[num] = {"title": title, "start": i + 1, "end": len(lines)}
        current = num
    return OrderedDict(
        (num, lines[sec["start"] : sec["end"]]) for num, sec in sections.items()
    ), OrderedDict((num, sec["title"]) for num, sec in sections.items())


def parse_blocks(lines: list[str]) -> list[dict]:
    """Parseert een reeks 'Attribuutsoort/Relatiesoort/Referentie element
    details'-blokken met key-value-regels + Toelichting-paragrafen.
    """
    blocks = []
    current = None
    last_label = None
    in_toelichting = False

    def flush():
        nonlocal current, last_label, in_toelichting
        if current is not None:
            blocks.append(current)
        current = None
        last_label = None
        in_toelichting = False

    for raw in lines:
        if not raw.strip():
            continue
        header = _BLOCK_HEADER_RE.match(raw)
        if header:
            flush()
            current = {"_type": header.group(1), "_ref": header.group(2).strip()}
            in_toelichting = False
            continue
        if current is None:
            continue
        # Kolom-0 regels die geen label zijn sluiten het blok af
        # (bijv. 'Overzicht ...' of een nieuwe sectiekop).
        m = _LABEL_RE.match(raw)
        only = _LABEL_ONLY_RE.match(raw)
        if m:
            label, value = m.group(1), m.group(2).strip()
            current[label] = value
            last_label = label
            in_toelichting = label == "Toelichting"
            continue
        if only:
            label = only.group(1)
            # 'Aanduiding' + 'strijdigheid/nietigheid' is één label over
            # twee regels; overige kale labels krijgen een lege waarde.
            if label == "Aanduiding" and not current.get(label):
                current[label] = ""
                last_label = label
                in_toelichting = False
            else:
                current[label] = ""
                last_label = label
            continue
        if _SECTION_RE.match(raw):
            flush()
            continue
        indent = len(raw) - len(raw.lstrip())
        if in_toelichting and indent >= 4:
            current["Toelichting"] = (current.get("Toelichting", "") + " " + raw.strip()).strip()
        elif last_label and indent >= 30:
            base = current.get(last_label, "")
            glue = "\n" if raw.lstrip().startswith(("- ", "•")) else " "
            current[last_label] = (base + glue + raw.strip()).strip()
        # overige regels (bijv. tabelresten) negeren
    flush()
    return blocks


def block_to_dict(block: dict, kind: str) -> dict:
    out = {}
    for label, value in block.items():
        if label.startswith("_"):
            continue
        key = LABEL_KEYS[label]
        value = (value or "").strip()
        if not value and key in _DROP_EMPTY:
            continue
        if key in ("mogelijkGeenWaarde", "waardeAfleidbaar"):
            value = _ja_nee(value)
        elif key == "indicatieAbstractObject":
            value = _ja_nee(value)
        elif key == "lengte" and value.isdigit():
            value = int(value)
        out[key] = value
    # naam uit blokkop halen als het label 'Naam' ontbreekt
    out.setdefault("naam", block.get("_ref"))
    return out


def parse_ch4_specialisaties(lines: list[str], bekende_namen: set[str]) -> list[dict]:
    """Leest 'X is specialisatie van Y'-rijen uit de h4-overzichtstabel.

    Generalisaties staan alleen in de h4-tabellen (en de view-figuren), niet
    als detailblokken in h5. Eerste tabelkolom (inspringing < 30) samenvoegen;
    de superbegrip-naam kan over regels afgebroken zijn ('GEO-' + 'OBJECT').
    """
    zone = False
    def_col = None
    eerste_kolom = []
    for raw in lines:
        s = raw.strip()
        if s == "Overzicht relaties":
            zone = True
            continue
        if zone and (s == "Toelichting" or s.startswith("Overzicht")):
            break
        if not zone or not s:
            continue
        if def_col is None and "Relatienaam met kardinaliteiten" in s:
            def_col = raw.find("Definitie")
            continue
        if def_col is None:
            def_col = 44  # fallback
        eerste_kolom.append(raw[:def_col].strip())
    tekst = re.sub(r"([A-Z])-\s+([A-Z])", r"\1-\2", " ".join(eerste_kolom))
    resultaat = []
    for m in re.finditer(r"([A-Z][A-Z0-9 -]*?) is specialisatie van ([A-Z][A-Z0-9-]*(?: [A-Z0-9-]+)*)", tekst):
        sub = m.group(1).strip()
        # langste prefix van doel-dat een bestaand objecttype is
        doel = None
        kandidaten = m.group(2).split(" ")
        for n in range(len(kandidaten), 0, -1):
            kandidaat = " ".join(kandidaten[:n])
            if kandidaat in bekende_namen:
                doel = kandidaat
                break
        if doel and sub in bekende_namen:
            resultaat.append({"objecttype": sub, "generaliseert": doel})
        else:
            raise ValueError(f"Specialisatierij niet herleidbaar: {sub!r} -> {m.group(2)!r}")
    return resultaat


def parse_ch4_objecttype(lines: list[str]) -> dict:
    """Key-value kop + Toelichting-paragraaf van een h4-objecttypesectie."""
    obj = {}
    last_label = None
    i = 0
    toelichting_started = False
    seen_overzicht = False  # na 'Overzicht ...' volgen tabellen: geen labels meer
    toelichting = []
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            i += 1
            continue
        m = _LABEL_RE.match(raw)
        only = _LABEL_ONLY_RE.match(raw)
        if m and m.group(1) == "Toelichting":
            # Toelichting kan met waarde op één regel of als kale kop vóór
            # inspringende paragrafen; staat ná de overzichtstabellen.
            toelichting_started = True
            if m.group(2).strip():
                toelichting.append(m.group(2).strip())
        elif only and only.group(1) == "Toelichting":
            toelichting_started = True
        elif m and not toelichting_started and not seen_overzicht:
            obj[m.group(1)] = m.group(2).strip()
            last_label = m.group(1)
        elif (
            only
            and not toelichting_started
            and not seen_overzicht
            and only.group(1) == "Aanduiding"
            and i + 1 < len(lines)
            and lines[i + 1].strip() == "strijdigheid/nietigheid"
        ):
            obj["Aanduiding strijdigheid/nietigheid"] = ""
            last_label = "Aanduiding strijdigheid/nietigheid"
            i += 1
        elif only and not toelichting_started and not seen_overzicht:
            obj[only.group(1)] = ""
            last_label = only.group(1)
        elif raw.lstrip().startswith("Overzicht"):
            seen_overzicht = True
        elif toelichting_started and len(raw) - len(raw.lstrip()) >= 4:
            toelichting.append(raw.strip())
        elif (
            last_label
            and not toelichting_started
            and not seen_overzicht
            and len(raw) - len(raw.lstrip()) >= 30
        ):
            base = obj.get(last_label, "")
            glue = "\n" if raw.lstrip().startswith(("- ", "•")) else " "
            obj[last_label] = (base + glue + raw.strip()).strip()
        i += 1
    out = {}
    for label, value in obj.items():
        key = LABEL_KEYS[label]
        value = (value or "").strip()
        if not value and key in _DROP_EMPTY:
            continue
        if key == "indicatieAbstractObject":
            value = _ja_nee(value)
        out[key] = value
    if toelichting:
        out["toelichting"] = " ".join(toelichting)
    return out


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"PDF niet gevonden: {args.pdf}", file=sys.stderr)
        return 2

    text = extract_text(args.pdf)
    lines = text.splitlines()

    ch4, ch4_titles = find_sections(lines, r"4\.")
    ch5, ch5_titles = find_sections(lines, r"5\.")
    ch6, ch6_titles = find_sections(lines, r"6\.")
    ch3, ch3_titles = find_sections(lines, r"3\.")

    warnings = []

    # --- objecttypen (h4: 4.1 .. 4.33; 4.34 = relatieklassen) ---
    objecttypen = []
    relatieklasse_ch4 = None
    for num in ch4:
        title = ch4_titles[num]
        body = ch4[num]
        if num == "34":
            continue  # 'Relatieklassen' kop-sectie
        if "." in num:  # 34.1 Relatieklasse Mutatie specifiek voorschrift
            relatieklasse_ch4 = parse_ch4_objecttype(body)
            relatieklasse_ch4["hoofdstuk"] = f"4.{num}"
            continue
        obj = parse_ch4_objecttype(body)
        obj["hoofdstuk"] = f"4.{num}"
        obj["detailHoofdstuk"] = None
        obj["attribuutsoorten"] = []
        obj["relatiesoorten"] = []
        if not obj.get("definitie"):
            warnings.append(f"4.{num} {title}: geen definitie gevonden")
        objecttypen.append(obj)

    by_name = {o["naam"]: o for o in objecttypen}

    # generalisaties uit de h4-overzichtstabellen (bestaan alleen daar,
    # niet als detailblokken in h5)
    generalisaties = []
    for num in ch4:
        if num == "34" or "." in num:
            continue
        generalisaties.extend(parse_ch4_specialisaties(ch4[num], set(by_name)))
    generalisaties.sort(key=lambda g: (g["objecttype"], g["generaliseert"]))

    # --- views (h3: 3.1 .. 3.6) ---
    views = []
    for num in ch3:
        title = ch3_titles[num]
        if not title.endswith("-view"):
            continue
        views.append(
            {
                "naam": title,
                "hoofdstuk": f"3.{num}",
                # kern-objecttypen staan alleen in figuren (Figuur 4 e.v. en
                # Figuur 17), niet als tekst.
                "kernObjecttypen": None,
                "kernObjecttypenBron": "figuren in h3 en Bijlage 1 (niet tekst-extrimeerbaar)",
            }
        )

    # --- detailblokken (h5) ---
    gegevensgroeptypen = []
    relatieklasse = None
    for num in ch5:
        title = ch5_titles[num]
        body = ch5[num]
        if num.startswith("8.1"):
            ggp = {
                "naam": "Adres",
                "hoofdstuk": f"5.{num}",
                "bijObjecttype": "BETROKKENE",
                "attribuutsoorten": [],
                "relatiesoorten": [],
            }
            for block in parse_blocks(body):
                kind = block["_type"]
                if kind == "Attribuutsoort details":
                    ggp["attribuutsoorten"].append(block_to_dict(block, kind))
                elif kind == "Relatiesoort details":
                    ggp["relatiesoorten"].append(block_to_dict(block, kind))
            gegevensgroeptypen.append(ggp)
            continue
        if num.startswith("32"):
            relatieklasse = {
                "naam": "Mutatie specifiek voorschrift",
                "hoofdstuk": f"5.{num}",
                "attribuutsoorten": [],
                "relatiesoorten": [],
            }
            for block in parse_blocks(body):
                kind = block["_type"]
                if kind == "Attribuutsoort details":
                    relatieklasse["attribuutsoorten"].append(block_to_dict(block, kind))
                elif kind == "Relatiesoort details":
                    relatieklasse["relatiesoorten"].append(block_to_dict(block, kind))
            continue
        obj = by_name.get(title)
        if obj is None:
            warnings.append(f"5.{num} {title}: geen bijbehorend objecttype in h4")
            continue
        obj["detailHoofdstuk"] = f"5.{num}"
        for block in parse_blocks(body):
            kind = block["_type"]
            if kind == "Attribuutsoort details":
                obj["attribuutsoorten"].append(block_to_dict(block, kind))
            elif kind == "Relatiesoort details":
                obj["relatiesoorten"].append(block_to_dict(block, kind))

    for obj in objecttypen:
        if obj["detailHoofdstuk"] is None:
            warnings.append(
                f"{obj['naam']}: geen detailhoofdstuk (h5) — attribuut-/relatiedetails ontbreken in het document"
            )

    # relatieklasse samenvoegen (h4-kopblok + h5-details)
    if relatieklasse is not None and relatieklasse_ch4 is not None:
        merged = {**relatieklasse_ch4}
        merged.pop("hoofdstuk", None)
        relatieklasse = {**merged, **relatieklasse}

    # --- referentielijsten (h6) ---
    referentielijsten = []
    for num in ch6:
        title = ch6_titles[num]
        if not title.startswith("Referentielijst "):
            continue
        naam = title[len("Referentielijst ") :]
        body = ch6[num]
        if num.startswith("5."):  # 6.5.x: elementdetails per lijst
            for rl in referentielijsten:
                if rl["naam"] == naam:
                    for block in parse_blocks(body):
                        if block["_type"] == "Referentie element":
                            rl["elementen"].append(block_to_dict(block, "Referentie element"))
            continue
        rl = parse_ch4_objecttype(body)  # zelfde key-value opbouw
        rl = {
            "naam": rl.pop("naam", naam),
            "hoofdstuk": f"6.{num}",
            "definitie": rl.get("definitie", ""),
            "herkomst": rl.get("herkomst"),
            "toelichting": rl.get("toelichting"),
            "elementen": [],
            # De waarden zelf worden buiten dit model beheerd (ld. de
            # toelichting bij de lijsten); het model specificeert alleen
            # de referentie-elementen.
            "waarden": None,
        }
        referentielijsten.append(rl)

    model = {
        "model": {
            "naam": "Conceptueel Informatiemodel VTH Fysieke Leefomgeving",
            "afkorting": "CIm VTH FLo",
            "versie": VERSIE,
            "status": "concept",
            "datum": "2025-07-14",
            "bronhouder": "Programma Digitaal VTH-stelsel Milieu",
            "project": "Eenheid van Taal (EvT)",
            "metamodel": "MIM (Metamodel Informatiemodellering)",
            "metamodelUrl": "https://docs.geostandaarden.nl/mim/mim/",
            "publicatieVariant": "AVG-geanonimiseerd (redacties uitsluitend in documenthistorie en bronnenlijst)",
            "bronbestand": str(args.pdf.relative_to(REPO_ROOT)),
            "bronSha256": sha256_of(args.pdf),
            "gegenereerdDoor": "nldt/scripts/extract_cim_vth_flo.py",
            "opmerkingen": [
                "Conceptversie 0.9.1; de 1.0-vaststelling volgt via de governance van het programma.",
                "Referentielijsten (waardenlijsten) worden buiten dit model beheerd; het model "
                "specificeert alleen de referentie-elementen.",
                "Kern-objecttypen per view staan in figuren en zijn daarom niet als tekst opgenomen.",
                "Relatiesoorten zijn de detailblokken uit h5 (uitgaand, vanuit het objecttype "
                "gezien); inkomende relaties zijn via de bronzijde opgenomen.",
                "Generalisaties ('is specialisatie van') staan alleen in de h4-overzichtstabellen "
                "en de view-figuren; alleen de tabelrijen zijn geëxtraheerd. Aanvullende "
                "specialisaties uit figuren (bijv. NIET-NATUURLIJK PERSOON naar BETROKKENE via "
                "de Betrokkene-view) ontbreken daarom.",
                "KLACHT en SIGNAAL hebben in het document (versie 0.9.1) geen detailhoofdstuk in "
                "hoofdstuk 5; hun attribuut-/relatiedetails ontbreken daardoor.",
            ],
        },
        "views": views,
        "objecttypen": objecttypen,
        "generalisaties": generalisaties,
        "gegevensgroeptypen": gegevensgroeptypen,
        "relatieklasse": relatieklasse,
        "referentielijsten": referentielijsten,
    }

    args.out.mkdir(parents=True, exist_ok=True)
    model_path = args.out / "model.json"
    with open(model_path, "w", encoding="utf-8") as fh:
        json.dump(model, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    pin = {
        "versie": VERSIE,
        "bronbestand": str(args.pdf.relative_to(REPO_ROOT)),
        "bronSha256": model["model"]["bronSha256"],
        "modelSha256": sha256_of(model_path),
        "vastgepindOp": "2026-11-10",
        "opmerking": "Conceptversie — bij 1.0-vaststelling een nieuwe versiemap genereren met dit script.",
    }
    with open(args.out / "pin.json", "w", encoding="utf-8") as fh:
        json.dump(pin, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # Samenvatting + validatie-uitkomsten op stdout
    n_attr = sum(len(o["attribuutsoorten"]) for o in objecttypen)
    n_rel = sum(len(o["relatiesoorten"]) for o in objecttypen)
    print(f"objecttypen:        {len(objecttypen)}")
    print(f"attribuutsoorten:   {n_attr}")
    print(f"relatiesoorten:     {n_rel}")
    print(f"generalisaties:     {len(generalisaties)}")
    print(f"gegevensgroeptypen: {len(gegevensgroeptypen)}")
    print(f"referentielijsten:  {len(referentielijsten)} "
          f"({', '.join(rl['naam'] for rl in referentielijsten)})")
    print(f"views:              {len(views)}")
    print(f"objecttypen zonder h5-detail: "
          f"{[o['naam'] for o in objecttypen if o['detailHoofdstuk'] is None]}")
    if relatieklasse:
        print(f"relatieklasse:      {relatieklasse['naam']} "
              f"({len(relatieklasse['attribuutsoorten'])} attribuutsoorten)")
    for w in warnings:
        print(f"WAARSCHUWING: {w}", file=sys.stderr)
    print(f"geschreven: {model_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
