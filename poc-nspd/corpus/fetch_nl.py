"""Haal CVDR709135 (Omgevingsverordening Zeeland) op naar corpus/nl/.

Geen pytest (netwerk). Run: python3 corpus/fetch_nl.py
"""
from __future__ import annotations

import hashlib
import html as html_mod
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent / "nl" / "CVDR709135"
URL = "https://lokaleregelgeving.overheid.nl/CVDR709135"


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "nLDT-toolbox-poc-nspd/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    (BASE / "index.html").write_bytes(raw)
    tekst = re.sub(r"<[^>]+>", "\n", raw.decode("utf-8", errors="replace"))
    tekst = html_mod.unescape(tekst)
    tekst = re.sub(r"\n{2,}", "\n", tekst)
    (BASE / "tekst.txt").write_text(tekst, encoding="utf-8")
    m = re.search(r"(?i)geldend\s+vanaf\s+([0-9]{2}-[0-9]{2}-[0-9]{4})", tekst)
    meta = {
        "cvdrId": "CVDR709135",
        "titel": "Omgevingsverordening Zeeland",
        "consolidatieDatum": m.group(1) if m else "ONBEKEND-ZOEK-HANDMATIG",
        "sha256Html": hashlib.sha256(raw).hexdigest(),
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceUrl": URL,
    }
    (BASE / "META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"consolidatie: {meta['consolidatieDatum']} → {BASE}")


if __name__ == "__main__":
    main()
