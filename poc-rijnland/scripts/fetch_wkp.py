#!/usr/bin/env python3
"""Fetch actual water-quality measurements from the Waterkwaliteitsportaal.

One-time (per year) data pull for PoC-3 fase 2b: POSTs to the national
portal's download API (the same request its downloadmodule UI makes),
aggregates the raw measurement rows to per-location annual statistics for
a curated set of parameters, and writes a compact fixture with provenance.

Usage:
    nldt/.venv/bin/python poc-rijnland/scripts/fetch_wkp.py --year 2025
"""

from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import statistics
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://wkp.rws.nl/api/v1/data-downloads/download"
AREA = "Hoogheemraadschap van Rijnland"
AREA_LEVEL = "waterbeheerder"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "wkp"

#: curated (GrootheidCode, ParameterOmschrijving) pairs kept in the fixture
PARAMETERS = [
    ("CONCTTE", "zuurstof"),
    ("VERZDGGD", "zuurstof"),
    ("CONCTTE", "chloride"),
    ("CONCTTE", "chlorofyl-a"),
    ("CONCTTE", "elektrische geleidbaarheid"),
    ("CONCTTE", "ammonium"),
    ("CONCTTE", "nitraat"),
    ("CONCTTE", "nitriet"),
    ("CONCTTE", "orthofosfaat"),
    ("CONCTTE", "totaal fosfor"),
    ("CONCTTE", "totaal stikstof"),
    ("CONCTTE", "zwevende stof"),
    ("pH", ""),
    ("T", ""),
    ("ZICHT", ""),
    ("GELDHD", ""),
]


def fetch_zip(year: int) -> zipfile.ZipFile:
    body = json.dumps([{"subjectId": 15, "year": year,
                        "areaLevel": AREA_LEVEL, "areaName": AREA}]).encode()
    req = Request(API, data=body, method="POST",
                  headers={"Content-Type": "application/json",
                           "Accept": "application/zip"})
    with urlopen(req, timeout=300) as resp:
        return zipfile.ZipFile(io.BytesIO(resp.read()))


def aggregate(year: int) -> dict:
    zf = fetch_zip(year)
    mv_name = next(n for n in zf.namelist() if n.startswith("WKP_Meetwaarden_"))
    mo_name = next(n for n in zf.namelist() if n.startswith("WKP_Meetobjecten_"))
    objects = {}
    with zf.open(mo_name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        for r in csv.DictReader(text, delimiter=";"):
            objects[r["MeetobjectCode"]] = {
                "omschrijving": r.get("Omschrijving") or "",
                "x": float(r["GeometriePuntX_RD"]),
                "y": float(r["GeometriePuntY_RD"]),
                "krwType": r.get("KRWwatertypeOmschrijving") or None,
            }
    want = {(g, p) for g, p in PARAMETERS}
    acc: dict = {}
    n_raw = 0
    with zf.open(mv_name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        for r in csv.DictReader(text, delimiter=";"):
            n_raw += 1
            key = (r["GrootheidCode"], r["ParameterOmschrijving"])
            if key not in want or not r["Numeriekewaarde"]:
                continue
            loc = r["MeetobjectCode"]
            try:
                val = float(str(r["Numeriekewaarde"]).replace(",", "."))
            except ValueError:
                continue
            slot = acc.setdefault(loc, {"x": None, "y": None, "params": {}})
            if slot["x"] is None and r.get("GeometriePuntX_RD"):
                slot["x"] = float(r["GeometriePuntX_RD"])
                slot["y"] = float(r["GeometriePuntY_RD"])
            unit = r["EenheidCode"]
            series = slot["params"].setdefault(f"{key[0]}|{key[1]}|{unit}",
                                               {"n": 0, "vals": []})
            series["n"] += 1
            series["vals"].append(val)
    locations = {}
    for loc, slot in acc.items():
        meta = objects.get(loc, {})
        x = slot["x"] if slot["x"] is not None else meta.get("x")
        y = slot["y"] if slot["y"] is not None else meta.get("y")
        if x is None or y is None:
            continue
        locations[loc] = {
            "omschrijving": meta.get("omschrijving", ""),
            "krwType": meta.get("krwType"),
            "x": x, "y": y,
            "params": {
                k: {"n": v["n"],
                    "median": round(statistics.median(v["vals"]), 4),
                    "min": round(min(v["vals"]), 4),
                    "max": round(max(v["vals"]), 4)}
                for k, v in sorted(slot["params"].items())
            },
        }
    return {"rawRows": n_raw, "locations": locations}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--year", type=int, default=2025)
    args = ap.parse_args()
    data = aggregate(args.year)
    out = {
        "source": "Waterkwaliteitsportaal (Informatiehuis Water) download API",
        "endpoint": API,
        "subject": "Meetgegevens (Oppervlaktewaterkwaliteit)",
        "areaLevel": AREA_LEVEL,
        "areaName": AREA,
        "year": args.year,
        "rawRows": data["rawRows"],
        "locationCount": len(data["locations"]),
        "parameters": sorted({p for loc in data["locations"].values()
                              for p in loc["params"]}),
        "fetchedAt": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "locations": data["locations"],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"waterkwaliteit-{args.year}.json"
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[wkp] {path}: {out['locationCount']} locations, "
          f"{out['rawRows']} raw rows, {len(out['parameters'])} parameter-keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
