"""Tel de Eindhovense RegelRecht-executies (full export) tegen STTR/DMN-vormen.

Reproduceerbaar: nldt/.venv/bin/python docs/research/sttr-imtr/scan_executies.py
Bronnen (gegenereerd door nldt/simulation/regelrecht/full_export/build_all.py):
  - nldt/simulation/regelrecht/full_export/out/eindhoven-cvdr696400.yaml
  - nldt/simulation/regelrecht/full_export/out/eindhoven-formalization-report.json

Classificatie is vorm-gebaseerd (geen verzonnen mapping): elke template van
eindhoven_templates.py (limiet / verbod / equivalentie) krijgt zijn DMN-tegenhanger
(ddecisionTable-vorm), en alles wat geen machine_readable execution heeft telt niet.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "nldt/simulation/regelrecht/full_export/out"
YAML_PATH = OUT / "eindhoven-cvdr696400.yaml"
REPORT_PATH = OUT / "eindhoven-formalization-report.json"
DEST = Path(__file__).resolve().parent / "eindhoven-567-dmn-scan.json"


def operaties(value) -> Counter:
    """Tel operatoren in een action-waarde (recursief)."""
    teller: Counter = Counter()
    if isinstance(value, dict):
        op = value.get("operation")
        if op:
            teller[op] += 1
        for sub in value.get("conditions", []) or []:
            teller.update(operaties(sub))
        for case in value.get("cases", []) or []:
            teller.update(operaties(case.get("when")))
    return teller


def vorm(action) -> str:
    """Vind de template-vorm van één action-waarde."""
    waarde = action.get("value")
    if not isinstance(waarde, dict):
        return "onbekend"
    if waarde.get("operation") == "IF":
        return "equivalentie (IF/cases)"
    if waarde.get("operation") == "AND":
        tekst = json.dumps(waarde)
        if "LESS_THAN_OR_EQUAL" in tekst:
            return "limiet (AND: <= + werkingsgebied)"
        return "verbod (AND: booleans)"
    if waarde.get("operation") == "LESS_THAN_OR_EQUAL":
        return "limiet (<= zonder werkingsgebied)"
    return waarde.get("operation", "onbekend")


def main() -> None:
    report = json.loads(REPORT_PATH.read_text())
    doc = yaml.safe_load(YAML_PATH.read_text())

    status = Counter(a.get("status") for a in report.get("articles", []))
    reden = Counter()
    for a in report.get("articles", []):
        if a.get("status") != "formalized":
            continue
        reden[re.sub(r"[-\d.,]+ (m²?|%)*.*", "", a.get("reason", "")).strip()] += 1

    vormen: Counter = Counter()
    inputtypes: Counter = Counter()
    params: Counter = Counter()
    met_werkingsgebied = 0
    numerieke_vergelijkingen = 0
    booleaanse_gelijkheden = 0
    exec_n = 0

    for art in doc.get("articles", []):
        mr = art.get("machine_readable") or {}
        ex = mr.get("execution")
        if not ex:
            continue
        exec_n += 1
        for act in ex.get("actions", []):
            vormen[vorm(act)] += 1
            teller = operaties(act.get("value"))
            numerieke_vergelijkingen += teller.get("LESS_THAN_OR_EQUAL", 0)
            booleaanse_gelijkheden += teller.get("EQUALS", 0)
        for i in ex.get("input", []):
            inputtypes[i.get("type")] += 1
            if i.get("name") == "in_werkingsgebied":
                met_werkingsgebied += 1
            else:
                params[i.get("name")] += 1

    resultaat = {
        "bron": {
            "report": str(REPORT_PATH.relative_to(REPO)),
            "export": str(YAML_PATH.relative_to(REPO)),
            "reportSha256": report.get("sourceSha256"),
            "gegenereerdOp": report.get("generatedAt"),
        },
        "aantallen": {
            "artikelenTotaal": sum(status.values()),
            **{k: v for k, v in status.items()},
            "executiesInExport": exec_n,
            "metWerkingsgebiedInput": met_werkingsgebied,
            "numeriekeVergelijkingen": numerieke_vergelijkingen,
            "booleaanseGelijkheden": booleaanse_gelijkheden,
        },
        "templateVormen": dict(vormen),
        "redenUitReport": dict(reden),
        "inputTypes": dict(inputtypes),
        "activiteitParameters": dict(params.most_common()),
    }
    DEST.write_text(json.dumps(resultaat, ensure_ascii=False, indent=1))
    print(json.dumps(resultaat, ensure_ascii=False, indent=1))
    print("\n→", DEST.relative_to(REPO))


if __name__ == "__main__":
    main()
