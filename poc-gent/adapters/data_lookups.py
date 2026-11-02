"""Dataset-lookups (F1-burger): niet-ruimtelijke open data als bron naast de
GIS-zonechecks. Productie vervangt de cache door de interne diensten van Stad
Gent; de adapter-interface blijft gelijk (DATA-01: herkomst per uitkomst)."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def laad_kalender(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "source" / "afvalkalender.json")
                      .read_text(encoding="utf-8"))


def laad_feesten(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "source" / "feestenkalender.json")
                      .read_text(encoding="utf-8"))


def _straat_van_adres(adres: str) -> str:
    deel = adres.split(",")[0]
    zonder_nummer = re.sub(r"\s+\d+.*$", "", deel)
    nkfd = unicodedata.normalize("NFKD", zonder_nummer)
    ascii_ = "".join(c for c in nkfd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def apply_checks(manifest: dict, context: dict, herkomst: dict, poc_root: Path,
                 suffix: str = "") -> None:
    """Voer alle dataChecks uit op hun input-slot. Onbekende straat volgt het
    per-check beleid: fallback (outputs 'onbekend', neutrale info-tekst) of
    escalate (outputs 'onbekend-straat' → geen regel vuurt → Gentinfo).
    Mutatie van context/herkomst is bewust: de caller geeft kopieën mee
    (context.build / gates.confirm_h1)."""
    kalenders = {"ivago-ophaalkalender": laad_kalender, "gentse-feesten": laad_feesten}
    for check in manifest.get("dataChecks", []):
        adres = context.get(check["input"])
        if adres is None:
            continue
        kalender = kalenders[check["dataset"]](poc_root)
        straat = _straat_van_adres(adres)
        if check["dataset"] == "gentse-feesten":
            # straten-map: locatiestraten van de Gentse Feesten (curated)
            for out in check["outputs"]:
                context[out] = "in" if straat in kalender.get("straten", {}) else "niet-in"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:gentse-feesten ({kalender['versie']})"}
            continue
        gevonden = kalender.get("straten", {}).get(straat)
        for out in check["outputs"]:
            if gevonden and out in gevonden:
                context[out] = gevonden[out]["dag"]
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} ({kalender['versie']}{suffix})"}
            elif gevonden is not None:
                # Straat bekend in de kalender, maar deze fractie wordt er
                # niet (via deze route) ingezameld — bijv. glas via containers.
                context[out] = "onbekend"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} (geen {out}-inzameling bekend voor deze straat{suffix})"}
            elif check.get("unknownPolicy", "escalate") == "fallback":
                context[out] = "onbekend"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} (straat niet in cache{suffix})"}
            else:
                context[out] = "onbekend-straat"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} (straat niet in cache{suffix})"}
