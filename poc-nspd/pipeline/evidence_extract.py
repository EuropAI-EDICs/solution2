"""Evidence-extractor: kandidaatcitaten uit corpus-tekst (deterministisch).

Curation-flow: extract_candidates() → curator verifieert en promote tot
evidence-*.json (cite-or-abstain: alleen gecontroleerde citaten verder).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

# Kopvormen in het corpus: inline "Artikel 18.17 Windenergie" én de
# gefragmenteerde CVDR-export ("Artikel" op eigen regel, witregels, dan het
# nummer, dan de kop — bijv. Artikel 18.17/18.18 in Afdeling 18.4 Energie).
# Maximaal 3 witte regels tussen "Artikel" en het nummer, zodat geen
# lidaanduidingen ("1", "2") uit lopende tekst als artikelnummer opvatten.
_ARTIKEL_RE = re.compile(
    r"^[ \t]*Artikel[ \t]*(?:\n[ \t]*){0,3}([0-9]+(?:\.[0-9]+)*)\b", re.M)
_EVID_PREFIX = {"wind": "EVW", "zon": "EVZ", "energietoets": "EVE"}


def _artikelgrenzen(tekst: str) -> list[tuple[str, int, int]]:
    koppen = list(_ARTIKEL_RE.finditer(tekst))
    grenzen = []
    for i, m in enumerate(koppen):
        start = m.start()
        einde = koppen[i + 1].start() if i + 1 < len(koppen) else len(tekst)
        grenzen.append((f"Artikel {m.group(1)}", start, einde))
    return grenzen


def extract_candidates(
    *,
    tekst: str,
    track: str,
    trefwoorden: tuple[str, ...],
    jurisdictie: str,
    source_url: str,
    bron_label: str = "",
) -> list[dict]:
    ev_prefix = _EVID_PREFIX[track]
    kandidaten: list[dict] = []
    for kop, start, einde in _artikelgrenzen(tekst):
        blok = tekst[start:einde]
        laag = blok.lower()
        if any(tw.lower() in laag for tw in trefwoorden):
            quote = " ".join(blok.split())[:600]
            record = {
                "id": f"{ev_prefix}-{len(kandidaten) + 1:02d}",
                "jurisdictie": jurisdictie,
                "track": track,
                "locator": kop,
                "quote": quote,
                "sourceUrl": source_url,
                "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "verified": False,  # curator-promotie zet deze op true
            }
            if bron_label:
                record["bron"] = bron_label
            kandidaten.append(record)
    return kandidaten


def merge_brondocumenten(meta_path: Path) -> list[tuple[str, str, str]]:
    """Geeft [(instrumentId, titel, tekst)] voor alle .txt in corpus/be."""
    import json as _json
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))
    uit = []
    for ins in meta["instrumenten"]:
        txt = meta_path.parent / ins["bestand"].replace(".pdf", ".txt")
        if txt.is_file():
            uit.append((ins["id"], ins["titel"], txt.read_text(encoding="utf-8", errors="replace")))
    return uit
