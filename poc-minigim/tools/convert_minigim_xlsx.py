#!/usr/bin/env python3
"""Convert the MiniGIM Excel artifacts into pinned, schema-validated registry JSON.

MiniGIM (https://minigim.nl/) publishes two core artifacts:

1. Omgevingsanalyse Lijst  (checklist: thema/onderdeel/item x bron/prioriteit/risico/formaat)
2. ILS "Input Grex"        (hierarchische gebiedsindeling -> IfcExportAs + EPset_minigim)

This converter is a *build-time* tool (system python3 + openpyxl), run manually
after a new MiniGIM version is published. The generated JSON under
``poc-minigim/registry/`` is committed and is the authoritative runtime input:
the runner itself stays offline/stdlib (no openpyxl dependency).

Layout notes verified against v0.91 / v0.8 (2026-09-21):
  Lijst sheet 'Data': header row 2; section header rows carry only the thema;
  the first data row after a section header may carry the thema *comment* in
  column A; blank identifier cells are forward-filled (merged-cell semantics);
  continuation rows (only Data/formaat/2D/3D filled) merge into the previous item.
  ILS sheet 'Blad1': niveau columns A/B/D/F/H each followed by an IfcExportAs
  column; trailing rows hold EPset questions, open issues and an IGG-JKO change log.

Usage:
    python3 poc-minigim/tools/convert_minigim_xlsx.py [--sources DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import openpyxl

THEMAS = ("locatie", "topografie", "ruimtelijke ordening", "statistiek", "identiteit")

LIJST_URL = "https://minigim.nl/downloads/MiniGIM-omgevingsanalyse-lijst-v0.91.xlsx"
ILS_URL = "https://minigim.nl/downloads/MiniGIM-ILS-v0.8.xlsx"
LIJST_FILE = "MiniGIM-omgevingsanalyse-lijst-v0.91.xlsx"
ILS_FILE = "MiniGIM-ILS-v0.8.xlsx"
RETRIEVED_AT = "2026-09-21"


def _norm(v) -> str:
    """Collapse whitespace/newlines in a cell to a single trimmed string."""
    if v is None:
        return ""
    s = unicodedata.normalize("NFC", str(v))
    return re.sub(r"\s+", " ", s).strip()


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("²", "2").replace("¹", "1")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_multi(s: str, sep: str = "/") -> list[str]:
    return [p.strip() for p in s.split(sep) if p.strip()]


def _split_data(s: str) -> list[str]:
    """Split a Data cell on commas, but not inside constructs like 'x-, y-...'."""
    parts, buf = [], ""
    for i, ch in enumerate(s):
        if ch == "," and s[i + 1 : i + 2] == " " and buf.rstrip()[-1:].isalnum():
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


# --------------------------------------------------------------------------- #
# 1. Omgevingsanalyse Lijst
# --------------------------------------------------------------------------- #

def convert_lijst(xlsx: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["Data"]

    rows: list[list[str]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rows.append([_norm(v) for v in (list(row) + [""] * 13)[:13]])

    header = [h for h in rows[0] if h]
    assert header[:3] == ["thema", "onderdeel", "item"], f"unexpected header: {header}"

    sections: list[dict] = []
    items: list[dict] = []
    current_thema = None
    current_onderdeel = ""
    used_ids: set[str] = set()

    def _assign_ids(records: list[dict]) -> None:
        """Twee-pass id-toekenning: base = thema.onderdeel.item(-bron).

        Komt een triple meer dan eens voor (bijv. de twee 'bebouwing'-rijen:
        3D-BAG vs BAG), dan krijgt élke rij van dat triple de
        bronregistratie-slug als suffix — voorspelbaar en leesbaar.
        """
        triple_counts: Counter = Counter(
            (rec["thema"], rec["onderdeel"], rec["item"]) for rec in records
        )
        for rec in records:
            parts = [rec["thema"], rec["onderdeel"], rec["item"]]
            base = ".".join(_slug(p) for p in parts if p) or f"rij-{rec['sourceRow']}"
            bron = rec["bronRegistratie"]
            if triple_counts[(rec["thema"], rec["onderdeel"], rec["item"])] > 1 and bron:
                base = f"{base}-{_slug(bron)}"
            cand, n = base, 1
            while cand in used_ids:
                n += 1
                cand = f"{base}-{n}"
            used_ids.add(cand)
            rec["id"] = cand

    for rn, r in enumerate(rows[1:], start=3):
        thema_raw, onderdeel, item = r[0], r[1], r[2]
        rest = r[3:]

        if not any(r):  # fully blank row
            continue

        # section header row: a known thema without onderdeel/item; the row
        # itself may carry section-level defaults (statistiek/identiteit do)
        if thema_raw.lower() in THEMAS and not onderdeel and not item:
            current_thema = thema_raw.lower()
            current_onderdeel = ""
            defaults = {}
            if rest[2]:  # prioriteit
                defaults["prioriteit"] = rest[2]
            sections.append(
                {
                    "thema": current_thema,
                    "sourceRow": rn,
                    "comment": None,
                    "defaults": defaults,
                }
            )
            continue

        # thema *comment* smuggled into column A of a data row
        thema_comment = None
        if thema_raw and thema_raw.lower() not in THEMAS:
            thema_comment = thema_raw
        elif thema_raw.lower() in THEMAS:
            current_thema = thema_raw.lower()

        if current_thema is None:
            raise AssertionError(f"row {rn}: data before any thema header")

        if thema_comment is not None and not any([onderdeel, item, *rest]):
            # comment-only row directly under a section header
            if sections and sections[-1]["comment"] is None:
                sections[-1]["comment"] = thema_comment
            continue

        continuation = not any([thema_raw, onderdeel, item, *r[3:9]])
        if continuation:
            # merge data variants / dimension flags into the previous item
            if not items:
                raise AssertionError(f"row {rn}: continuation before any item")
            prev = items[-1]
            if r[9]:
                prev["data"].append(r[9])
            if r[10]:
                prev["bestandsformaat"].extend(_split_multi(r[10]))
            prev["bestandsformaat"] = list(dict.fromkeys(prev["bestandsformaat"]))
            if r[11]:
                prev["dim2"] = True
            if r[12]:
                prev["dim3"] = True
            prev["notes"].append(f"vervolgrij {rn} samengevoegd")
            continue

        # forward-fill onderdeel within the section (merged-cell semantics)
        if onderdeel:
            current_onderdeel = onderdeel
        effective_onderdeel = onderdeel or (current_onderdeel or None)

        sec_defaults = sections[-1]["defaults"] if sections else {}
        if thema_comment and sections and sections[-1]["comment"] is None:
            sections[-1]["comment"] = thema_comment

        prioriteit = r[5] or sec_defaults.get("prioriteit") or None

        rec = {
            "id": None,  # toegewezen in _assign_ids na de volledige scan
            "sourceRow": rn,
            "thema": current_thema,
            "onderdeel": effective_onderdeel,
            "item": item or None,
            "bronRegistratie": r[3] or None,
            "bronLeverancier": r[4] or None,
            "prioriteit": prioriteit,
            "risico": _split_multi(r[6]) if r[6] else [],
            "actie": r[7] or None,
            "datatype": r[8] or None,
            "data": _split_data(r[9]) if r[9] else [],
            "bestandsformaat": _split_multi(r[10]) if r[10] else [],
            "dim2": bool(r[11]),
            "dim3": bool(r[12]),
            "notes": [],
        }
        items.append(rec)

    _assign_ids(items)

    toelichting = []
    if "Toelichting" in wb.sheetnames:
        for row in wb["Toelichting"].iter_rows(values_only=True):
            vals = [_norm(v) for v in row if _norm(v)]
            if len(vals) >= 2:
                toelichting.append({"opmerking": vals[0], "verwerking": vals[1]})
            elif len(vals) == 1:
                toelichting.append({"opmerking": vals[0], "verwerking": None})
    wb.close()

    # record inherited priority as an explicit section default
    for sec in sections:
        rows_ = [i for i in items if i["thema"] == sec["thema"]]
        if rows_ and not sec["defaults"]:
            first = rows_[0]
            if first["prioriteit"] and all(i["prioriteit"] == first["prioriteit"] for i in rows_):
                sec["defaults"] = {"prioriteit": first["prioriteit"]}

    return {
        "registryVersion": "1.0",
        "standard": "MiniGIM",
        "artifact": "omgevingsanalyse-lijst",
        "sourceVersion": "v0.91",
        "sourceUrl": LIJST_URL,
        "sourceSha256": _sha256(xlsx),
        "retrievedAt": RETRIEVED_AT,
        "sections": sections,
        "items": items,
        "toelichting": toelichting,
    }


# --------------------------------------------------------------------------- #
# 2. ILS ("Input Grex")
# --------------------------------------------------------------------------- #

# level -> (niveau value col, IfcExportAs col), 1-based:
# A=Niveau -1 (meta), B=Niveau 0, C=IfcExportAs, D=Niveau 1, E=IfcExportAs,
# F=Niveau 2, G=IfcExportAs, H=Niveau 3, I=IfcExportAs
NIVEAU_COLS = {0: (2, 3), 1: (4, 5), 2: (6, 7), 3: (8, 9)}


def convert_ils(xlsx: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb["Blad1"]

    nodes: list[dict] = []
    parents: dict[int, str | None] = {0: None, 1: None, 2: None, 3: None}
    used_ids: set[str] = set()
    notes: list[str] = []
    epset_props: list[dict] = []
    open_issues: list[str] = []
    change_log: list[dict] = []

    def _mk_node(label: str, level: int, ifc: str | None, rn: int) -> dict:
        base = f"n{level}.{_slug(label)}"
        cand, n = base, 1
        while cand in used_ids:
            n += 1
            cand = f"{base}-{n}"
        used_ids.add(cand)
        return {
            "id": cand,
            "level": level,
            "label": label,
            "ifcExportAs": ifc if ifc and ifc != "?" else None,
            "parent": parents[level - 1] if level > 0 else None,
            "sourceRow": rn,
            "notes": [] if (ifc == "?") else [],
        }

    for rn, row in enumerate(ws.iter_rows(values_only=True), start=1):
        r = [_norm(v) for v in (list(row) + [""] * 12)[:12]]

        if rn <= 5:
            if rn == 4:
                notes.append(
                    "rij 4: kolomgroepen QUICK-SCAN (niveau 0) vs GREXKOSTEN (niveau 1-3)"
                )
            continue

        # --- change log (dated IGG-JKO rows at the tail) ----------------------
        if re.match(r"^\d{4}-\d{2}-\d{2}", r[0]):
            change_log.append(
                {"datum": r[0].split()[0], "door": r[1], "opmerking": r[2]}
            )
            continue

        # --- EPset column (K) + free-text open issues (L) ---------------------
        # Col L holds EPset answers on rows 6-8 and the reviewers' issue list
        # further down; collect both, but never let either suppress tree parsing.
        if r[10]:
            epset_props.append(
                {"name": r[10], "mapsTo": r[11] or None, "sourceRow": rn}
            )
        elif r[11]:
            open_issues.append(r[11])

        # --- meta / free-text blocks ------------------------------------------
        if r[0].startswith("Gereserveerd") or r[0] == "Wie?":
            continue
        if r[0].startswith("Wat valt") or r[1].startswith("Wat valt"):
            notes.append(f"rij {rn}: 'Wat valt:' (wat valt binnen/buiten de casus)")
            r[0] = r[1] = ""
        if r[1] in ("Binnen casus (deze ILS)", "Buiten casus (apparte IFC)"):
            notes.append(f"rij {rn}: {r[1]}")
            r[0] = r[1] = ""
        if r[5] == "Onder de grond > BRO":
            notes.append(f"rij {rn}: Onder de grond > BRO (geen ILS-niveau, BRO-referentie)")
            continue

        # --- tree columns ----------------------------------------------------
        for level in (0, 1, 2, 3):
            val_col, ifc_col = NIVEAU_COLS[level]
            label = r[val_col - 1]
            ifc = r[ifc_col - 1] or None
            if label:
                node = _mk_node(label, level, ifc, rn)
                if ifc == "?":
                    node["notes"].append("IfcExportAs in bronsheet '?': mappings nog open in de standaard")
                nodes.append(node)
                parents[level] = node["id"]
                for deeper in (level + 1, level + 2, level + 3):
                    parents[deeper] = None

    wb.close()

    return {
        "registryVersion": "1.0",
        "standard": "MiniGIM",
        "artifact": "ils",
        "name": "Informatie Leverings Specificatie",
        "purpose": "Input Grex: minimale dataset om een grondexploitatie onveranderd en inhoudelijk onderbouwd te realiseren",
        "sourceVersion": "v0.8",
        "sourceUrl": ILS_URL,
        "sourceSha256": _sha256(xlsx),
        "retrievedAt": RETRIEVED_AT,
        "levels": ["Niveau 0", "Niveau 1", "Niveau 2", "Niveau 3"],
        "nodes": nodes,
        "epset": {"id": "EPset_minigim", "properties": epset_props},
        "notes": notes,
        "openIssues": open_issues,
        "changeLog": change_log,
    }


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", default=str(Path(__file__).resolve().parents[1] / "sources"))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "registry"))
    args = ap.parse_args()

    src, out = Path(args.sources), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lijst = convert_lijst(src / LIJST_FILE)
    ils = convert_ils(src / ILS_FILE)

    (out / "minigim-lijst.json").write_text(
        json.dumps(lijst, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (out / "minigim-ils.json").write_text(
        json.dumps(ils, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    n_hoog = sum(1 for i in lijst["items"] if i["prioriteit"] == "hoog")
    print(
        f"lijst: {len(lijst['items'])} items over {len(lijst['sections'])} thema's "
        f"({n_hoog} prioriteit hoog); toelichting: {len(lijst['toelichting'])} regels"
    )
    print(f"ils:   {len(ils['nodes'])} knopen; epset {len(ils['epset']['properties'])} props; "
          f"{len(ils['openIssues'])} open issues; {len(ils['changeLog'])} changelog-regels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
