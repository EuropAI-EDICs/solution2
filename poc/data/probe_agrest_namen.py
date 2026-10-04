# poc/data/probe_agrest_namen.py
"""One-shot NAAM-probe op de agrest Omgevingsverordening FeatureServer.

Zoekt alle distinct gebiedsaanwijzing-namen (GIO's) die de verordening kent;
output wordt gecommit als bewijsmateriaal voor zone-aliaskeuze (tracks water,
bodem, en later fase 2/3). Netwerk alleen bij expliciete hergeneratie.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVICE = "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0"
OUT = Path(__file__).with_name("agrest-namen.json")


def fetch_namen() -> list[str]:
    namen: set[str] = set()
    offset = 0
    while True:
        url = (
            f"{SERVICE}/query?f=json&returnGeometry=false&outFields=NAAM"
            f"&returnDistinctValues=true&resultOffset={offset}&resultRecordCount=1000"
            f"&where=1%3D1"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            body = json.loads(resp.read())
        features = body.get("features", [])
        if not features:
            break
        for feat in features:
            naam = (feat.get("attributes") or {}).get("NAAM")
            if naam:
                namen.add(str(naam).strip())
        if body.get("exceededLimit", False) or len(features) < 1000:
            if not body.get("exceededLimit", False):
                break
        offset += 1000
    return sorted(namen)


def main() -> int:
    namen = fetch_namen()
    OUT.write_text(
        json.dumps(
            {"generatedAt": datetime.now(timezone.utc).isoformat(), "service": SERVICE, "namen": namen},
            ensure_ascii=False, indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(namen)} distinct NAAM-waarden -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
