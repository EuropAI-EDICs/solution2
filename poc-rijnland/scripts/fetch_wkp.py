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


ZIP_CACHE = OUT_DIR / "zips"


def fetch_zip(year: int, attempts: int = 3) -> zipfile.ZipFile:
    """Download a year's zip (cached on disk; failing years can be
    re-fetched later without redoing the rest)."""
    ZIP_CACHE.mkdir(parents=True, exist_ok=True)
    cached = ZIP_CACHE / f"{year}.zip"
    if cached.is_file() and cached.stat().st_size > 1000:
        return zipfile.ZipFile(cached)
    body = json.dumps([{"subjectId": 15, "year": year,
                        "areaLevel": AREA_LEVEL, "areaName": AREA}]).encode()
    last = None
    for attempt in range(1, attempts + 1):
        req = Request(API, data=body, method="POST",
                      headers={"Content-Type": "application/json",
                               "Accept": "application/zip"})
        try:
            with urlopen(req, timeout=300) as resp:
                data = resp.read()
            zf = zipfile.ZipFile(io.BytesIO(data))
            cached.write_bytes(data)  # prime the disk cache
            return zf
        except Exception as exc:  # transient portal timeouts
            last = exc
            print(f"[wkp] {year}: poging {attempt} mislukt "
                  f"({type(exc).__name__}: {exc})", flush=True)
            if attempt < attempts:
                import time
                time.sleep(10 * attempt)
    raise last


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


def aggregate_monthly(year_from: int, year_to: int) -> dict:
    """Monthly stats per parameter: area-wide buckets AND per-location
    medians (aligned arrays over one shared month list) — the per-location
    part feeds the animated hex map."""
    acc: dict = {}          # pkey -> ym -> {"vals": [], "locs": set()}
    per_loc: dict = {}      # pkey -> loc -> {"x":, "y":, "vals": {ym: [v]}}
    year_rows: dict = {}
    failed_years = []
    for year in range(year_from, year_to + 1):
        try:
            zf = fetch_zip(year)
        except Exception as exc:
            failed_years.append(year)
            print(f"[wkp] {year}: OVERGESLAGEN ({type(exc).__name__})", flush=True)
            continue
        mv_name = next(n for n in zf.namelist()
                       if n.startswith("WKP_Meetwaarden_"))
        want = {(g, p) for g, p in PARAMETERS}
        n_rows = 0
        with zf.open(mv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            for r in csv.DictReader(text, delimiter=";"):
                n_rows += 1
                key = (r["GrootheidCode"], r["ParameterOmschrijving"])
                if key not in want or not r["Numeriekewaarde"]:
                    continue
                ym = (r.get("Monsterophaaldatum") or "")[:7]
                if len(ym) != 7 or ym[4] != "-":
                    continue
                try:
                    val = float(str(r["Numeriekewaarde"]).replace(",", "."))
                except ValueError:
                    continue
                pkey = f"{key[0]}|{key[1]}|{r['EenheidCode']}"
                bucket = acc.setdefault(pkey, {}).setdefault(
                    ym, {"vals": [], "locs": set()})
                bucket["vals"].append(val)
                bucket["locs"].add(r["MeetobjectCode"])
                loc = per_loc.setdefault(pkey, {}).setdefault(
                    r["MeetobjectCode"],
                    {"x": None, "y": None, "vals": {}})
                if loc["x"] is None and r.get("GeometriePuntX_RD"):
                    loc["x"] = float(r["GeometriePuntX_RD"])
                    loc["y"] = float(r["GeometriePuntY_RD"])
                loc["vals"].setdefault(ym, []).append(val)
        year_rows[year] = n_rows
        print(f"[wkp] {year}: {n_rows} raw rows", flush=True)

    months_all = sorted({ym for p in acc.values() for ym in p})
    series = {}
    for pkey, months in sorted(acc.items()):
        rows = []
        for ym in sorted(months):
            b = months[ym]
            if len(b["vals"]) < 2:
                continue  # te weinig metingen voor een robuuste mediaan
            qs = statistics.quantiles(b["vals"], n=4)
            rows.append({
                "ym": ym,
                "n": len(b["vals"]),
                "nLocations": len(b["locs"]),
                "median": round(statistics.median(b["vals"]), 4),
                "p25": round(qs[0], 4),
                "p75": round(qs[2], 4),
            })
        series[pkey] = rows

    per_location = {}
    for pkey, locs in per_loc.items():
        keep = {}
        for code, loc in locs.items():
            if loc["x"] is None:
                continue
            keep[code] = {
                "x": loc["x"], "y": loc["y"],
                "values": [round(statistics.median(loc["vals"][ym]), 4)
                           if ym in loc["vals"] else None
                           for ym in months_all],
            }
        if keep:
            per_location[pkey] = keep
    if not year_rows:
        raise RuntimeError("geen enkel jaar kon worden opgehaald")
    return {"series": series, "perLocation": per_location,
            "months": months_all, "rawRowsPerYear": year_rows,
            "failedYears": failed_years}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--monthly", action="store_true",
                    help="aggregate per month over a year range instead of "
                         "per-location annual stats")
    ap.add_argument("--from-year", type=int, default=2020)
    ap.add_argument("--to-year", type=int, default=2026)
    args = ap.parse_args()
    if args.monthly:
        import datetime as _dt
        agg = aggregate_monthly(args.from_year, args.to_year)
        out = {
            "source": "Waterkwaliteitsportaal (Informatiehuis Water) download API",
            "endpoint": API,
            "subject": "Meetgegevens (Oppervlaktewaterkwaliteit)",
            "areaLevel": AREA_LEVEL,
            "areaName": AREA,
            "yearFrom": args.from_year,
            "yearTo": args.to_year,
            "rawRowsPerYear": agg["rawRowsPerYear"],
            "fetchedAt": _dt.datetime.now(_dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "series": agg["series"],
            "months": agg["months"],
            "perLocation": agg["perLocation"],
            "failedYears": agg.get("failedYears") or [],
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / (f"waterkwaliteit-monthly-"
                          f"{args.from_year}-{args.to_year}.json")
        path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"[wkp] {path}: {len(out['series'])} parameters, "
              f"{sum(len(v) for v in out['series'].values())} month buckets, "
              f"{sum(len(v) for v in out['perLocation'].values())} "
              "location-series")
        return 0
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
