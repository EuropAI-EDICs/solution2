"""Kalibratieloop van de Utrecht-PoC (herhaalbaar, ook ná 18-11-2026).

Stappen:
1. Verordening-diff (``cvdr_diff``): her-fetch van de Omgevingsverordening via
   het bestaande root-script ``fetch_omgevingsverordening.py`` en diff tegen de
   vorige output op het werkelijke script-pad
   (``nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/omgevingsverordening.geojson``).
   Afwijking t.o.v. plan: dat script schrijft géén tekst-extract naar
   ``poc/corpus/`` — het tekst-corpus (``docs/research/sources/
   cvdr704250-tekst-extract.txt``) is een statische snapshot en géén output van
   dit script; diff dus op het echte output-pad (vorige fetch vs. verse fetch).
2. Geo-versheid (``layer_freshness``): per featured track via
   ``uitdagingen.json::scenarioRuns`` → ``scenario-report.json::baselineRunId``
   → ``poc/runs/<baselineRunId>/layers.json``; goedkope ArcGIS-count
   (``$returnCountOnly=true``). Zones zonder live provinciale laag worden
   overgeslagen: ``geometrySource == "national_source"`` en de energietoets-AOI
   (``geometrySource == "none"``, géén ``serviceUrl``).
3. Zone-drift (``zone_drift``): control-herproductie per track tegen de
   baseline; tolerantie 0,1%. Bewust lokaal gedupliceerd als
   ``DRIFT_TOLERANCE`` i.p.v. geïmporteerd uit
   ``poc/pipeline/scenarios.py::CONTROL_REPRODUCTION_REL_TOLERANCE`` (zelfde
   waarde 0.001): een import zou shapely/pyproj en de hele pipeline-graaf
   meetrekken voor één float; bij wijziging daar moet deze constante worden
   bijgewerkt (cross-ref in beide docstrings).
4. Rapport: ``poc/data/calibration/<datum>-calibratierapport.{md,json}`` met
   per uitdaging bronnen × rol × lastChecked × wijzigingen × gaps en de vlag
   "her-kalibreren na PS-besluit 18-11-2026". Exit 0 zolang de zone-drift
   ≤0,1% is.

Run: ``python3 poc/data/calibrate.py [--refresh]``
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POC = REPO / "poc"
CALIB = POC / "data" / "calibration"
FETCH_SCRIPT = REPO / "fetch_omgevingsverordening.py"
# Werkelijke output van fetch_omgevingsverordening.py (zie diens OUTPUT_FILE);
# niet poc/corpus/cvdr704250-tekst-extract.txt — dat bestand bestaat daar niet.
VERORDENING_OUTPUT = (REPO / "nldt" / "data" / "lake" / "nldt-poc-lake" /
                      "silver" / "utrecht" / "geo" / "omgevingsverordening.geojson")
DRIFT_TOLERANCE = 0.001  # 0,1% — gelijk aan CONTROL_REPRODUCTION_REL_TOLERANCE
                         # in poc/pipeline/scenarios.py (bewust gedupliceerd,
                         # zie module-docstring stap 3).

AMENDEMENT = ("PS-besluit wijziging Omgevingsverordening verwacht 18-11-2026 — "
              "herkalibreren na vaststelling")


def drift_verdict(baseline_km2: float, control_km2: float) -> str:
    if not baseline_km2:
        return "drift"
    return "pass" if abs(control_km2 - baseline_km2) / baseline_km2 <= DRIFT_TOLERANCE \
        else "drift"


def cvdr_diff() -> dict:
    """Her-fetch de Omgevingsverordening en diff tegen de vorige fetch-output."""
    before = (VERORDENING_OUTPUT.read_text(encoding="utf-8")
              if VERORDENING_OUTPUT.is_file() else "")
    subprocess.run([sys.executable, str(FETCH_SCRIPT)],
                   check=True, capture_output=True)
    after = VERORDENING_OUTPUT.read_text(encoding="utf-8")
    return {"gewijzigd": before != after, "for_kenmerk": len(after)}


def arcgis_count(service_url: str, layer_id: int) -> int | None:
    """Goedkope versheid-check: feature-count van de live laag."""
    url = f"{service_url}/{layer_id}/query?f=json&where=1%3D1&returnCountOnly=true"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        return int(data.get("count"))
    except Exception:
        return None


def layer_freshness() -> list[dict]:
    rows = []
    for track, run_id in _scenario_runs().items():
        report_path = POC / "scenario-runs" / run_id / "scenario-report.json"
        layers_path = None
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            baseline = report.get("baselineRunId")  # poc/runs-id met layers.json
            if baseline:
                layers_path = POC / "runs" / baseline / "layers.json"
        if layers_path is None or not layers_path.is_file():
            continue
        manifest = json.loads(layers_path.read_text(encoding="utf-8"))
        for zid, laag in manifest.items():
            if laag.get("geometrySource") == "national_source":
                continue  # nationale bron: geen provinciale live laag
            if not laag.get("serviceUrl"):
                continue  # bijv. energietoets-AOI (geometrySource "none")
            n = arcgis_count(laag["serviceUrl"], int(laag.get("layerId") or 0))
            rows.append({"track": track, "zoneId": zid,
                         "count": n, "cached": laag.get("lastChecked")})
    return rows


def zone_drift() -> list[dict]:
    rows = []
    for track, run_id in _scenario_runs().items():
        rep = json.loads((POC / "scenario-runs" / run_id / "scenario-report.json")
                         .read_text(encoding="utf-8"))
        control = rep["control"]["finalAreaKm2"]
        base = rep["control"]["baselineFinalAreaKm2"]
        rows.append({"track": track, "verdict": drift_verdict(base, control),
                     "baselineKm2": base, "controlKm2": control})
    return rows


def _scenario_runs() -> dict[str, str]:
    uj = json.loads((POC / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))
    return {k: v for k, v in uj["scenarioRuns"].items() if v}


def render_markdown(rapport: dict) -> str:
    lines = [f"# Kalibratierapport {rapport['datum']}", "",
             f"**Amendement:** {rapport['amendement']}", ""]
    for uit in rapport["uitdagingen"]:
        lines += [f"## {uit['titel']}", ""]
        lines += ["| track | drift | lastChecked | wijzigingen |", "|---|---|---|---|"]
        for t in uit["tracks"]:
            lines.append(f"| {t['track']} | {t['drift']} | {t['lastChecked']} | "
                         f"{t['wijzigingen']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    datum = date.today().isoformat()
    diff = cvdr_diff()
    fresh = layer_freshness()
    drift = zone_drift()
    uitdagingen = json.loads(
        (POC / "scenarios" / "uitdagingen.json").read_text(encoding="utf-8"))
    rapport = {
        "datum": datum,
        "amendement": AMENDEMENT,
        "cvdr": diff,
        "lagen": fresh,
        "uitdagingen": [
            {"id": u["id"], "titel": u["titel"],
             "tracks": [{"track": d["track"],
                         "drift": d["verdict"],
                         "lastChecked": next((l["cached"] for l in fresh
                                              if l["track"] == d["track"]), "-"),
                         "wijzigingen": sum(1 for l in fresh
                                            if l["track"] == d["track"]
                                            and l["count"] is None)}
                        for d in drift if d["track"] in u["tracks"]]}
            for u in uitdagingen["uitdagingen"]],
    }
    CALIB.mkdir(parents=True, exist_ok=True)
    (CALIB / f"{datum}-calibratierapport.json").write_text(
        json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    (CALIB / f"{datum}-calibratierapport.md").write_text(
        render_markdown(rapport), encoding="utf-8")
    print(f"kalibratie {datum}: {len(drift)} tracks, cvdr gewijzigd={diff['gewijzigd']}")
    return 0 if all(d["verdict"] == "pass" for d in drift) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
