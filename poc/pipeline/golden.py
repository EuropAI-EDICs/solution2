"""Golden-regressie: normalisatie en diff van canonieke PoC-runs (eval-harness).

Pure module — geen netwerk, geen schrijfacties. De 13 canonieke runs onder
poc/runs/ zijn de frozen goldens (GS-1/GS-3-kern); de mapping is bewust
expliciet. Diff-semantiek (spec 2026-10-06): verdicts + perRule exact,
zone-geometrie IoU-gelimiteerd, zones.gml structureel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

POC_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = POC_ROOT / "runs"

CANONICAL_RUNS: dict[str, str] = {
    "wind": "20260830T113234Z-wind",
    "zon": "20260830T142439Z-zon",
    "bos": "20260830T142446Z-bos",
    "water": "20261004T185116Z-water",
    "bodem": "20261004T185509Z-bodem",
    "mobiliteit": "20261005T072839Z-mobiliteit",
    "landschap": "20261005T070621Z-landschap",
    "landbouw": "20261005T094244Z-landbouw",
    "wonen": "20261005T100258Z-wonen",
    "werken": "20261006T121921Z-werken",
    "recreatie": "20261006T114934Z-recreatie",
    "biomassa": "20261006T120133Z-biomassa",
    "energietoets": "20261006T171730Z-energietoets",
}

VOLATILE_SUMMARY_KEYS = ("runId", "requestId", "generatedAt", "durationS")


def golden_dir(track: str) -> Path:
    return RUNS_ROOT / CANONICAL_RUNS[track]


def normalize_run_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in summary.items() if k not in VOLATILE_SUMMARY_KEYS}


def load_verdicts(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": summary.get("verdict"),
        "verdicts": summary.get("verdicts"),
        "perRule": [(r.get("ruleId"), r.get("verdict")) for r in summary.get("perRule", [])],
    }


def gml_zone_ids(path: Path) -> list[str]:
    """Zone-feature-ids (`zones.<n>`) uit zones.gml, gesorteerd en ontdubbeld."""
    text = path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'gml:id="(zones\.\d+)"', text)))


def _features(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("features", [])
    return [z for z in data if isinstance(z, dict)]


def zones_iou(new_geojson: Path, gold_geojson: Path, tolerance: float = 0.9999) -> dict[str, Any]:
    from shapely.geometry import shape
    from shapely.ops import unary_union

    new = _features(new_geojson)
    gold = _features(gold_geojson)
    count_equal = len(new) == len(gold)
    union_new = unary_union([shape(z["geometry"]) for z in new if z.get("geometry")]) if new else None
    union_gold = unary_union([shape(z["geometry"]) for z in gold if z.get("geometry")]) if gold else None
    if union_new is None or union_gold is None or union_new.area == 0 or union_gold.area == 0:
        iou = 1.0 if (union_new is None and union_gold is None) else 0.0
    else:
        iou = union_new.intersection(union_gold).area / union_new.union(union_gold).area
    return {
        "featureCountEqual": count_equal,
        "iou": round(iou, 6),
        "pass": count_equal and iou >= tolerance,
    }


def diff_runs(new_dir: Path, gold_dir: Path, iou_tolerance: float = 0.9999) -> dict[str, Any]:
    new_summary = json.loads((new_dir / "run_summary.json").read_text(encoding="utf-8"))
    gold_summary = json.loads((gold_dir / "run_summary.json").read_text(encoding="utf-8"))
    verdicts_new, verdicts_gold = load_verdicts(new_summary), load_verdicts(gold_summary)
    verdicts_equal = verdicts_new == verdicts_gold

    if (new_dir / "zones.geojson").is_file() and (gold_dir / "zones.geojson").is_file():
        geo = zones_iou(new_dir / "zones.geojson", gold_dir / "zones.geojson", iou_tolerance)
    else:
        geo = {"featureCountEqual": True, "iou": None, "pass": True}

    gml_new = gml_zone_ids(new_dir / "zones.gml") if (new_dir / "zones.gml").is_file() else []
    gml_gold = gml_zone_ids(gold_dir / "zones.gml") if (gold_dir / "zones.gml").is_file() else []
    gml_equal = gml_new == gml_gold

    passed = verdicts_equal and geo["pass"] and gml_equal
    return {
        "pass": passed,
        "verdictsEqual": verdicts_equal,
        "geo": geo,
        "gmlEqual": gml_equal,
        "gmlZoneCount": len(gml_gold),
        "details": {} if passed else {
            "verdicts": None if verdicts_equal else {"new": verdicts_new, "golden": verdicts_gold},
            "gmlOnlyInNew": sorted(set(gml_new) - set(gml_gold))[:10],
            "gmlOnlyInGolden": sorted(set(gml_gold) - set(gml_new))[:10],
        },
    }
