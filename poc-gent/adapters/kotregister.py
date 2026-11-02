"""Kotregister-adapter (GT-KOT-01): adres-status uit de publieke
Kotatgent-kotenzoeker. De cache is een schermbeeld van de beschikbare
advertenties (106 uit 5.130 in de database) — het volledige register is
niet open en blijft een productie-afhankelijkheid (District09/koteloket);
deze adapter is de echte-data-stand-in zolang die er niet is."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def laad_register(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "source" / "kotregister.json")
                      .read_text(encoding="utf-8"))


def norm_adres(adres: str) -> str:
    """'Rodelijvekensstraat 106' → 'rodelijvekensstraat 106': gemeente eraf,
    diakritiek gestript, kleine letters, witruimte genormaliseerd."""
    deel = adres.split(",")[0]
    nkfd = unicodedata.normalize("NFKD", deel)
    ascii_ = "".join(c for c in nkfd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def status_voor(poc_root: Path, adres: str | None) -> dict:
    """Status van een adres in het publieke kotregister: 'gemeld' wanneer het
    adres voorkomt onder de gepubliceerde advertenties, anders 'nieuw'."""
    if not adres:
        return {"status": "nieuw"}
    register = laad_register(poc_root)
    bekend = {norm_adres(kot["adres"]) for kot in register.get("koten", [])}
    return {"status": "gemeld" if norm_adres(adres) in bekend else "nieuw"}
