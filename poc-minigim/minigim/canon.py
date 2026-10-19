"""Canon-regel voor de M2-bewijsinstrumenten (één bron, drie gebruikers).

Ook thuis hier: fase_samenvatting, de per-fase kant van het bewijs.

Volatile run-meta (runId, generatedAt) en de artifacts-lijst vallen buiten
de vergelijking; "file"-waarden normaliseren naar bestandsnaam (het AOI-pad
van de run-invoer is per-run). Laag-bestanden worden buiten canon om
byte-gelijk vergeleken.

Gebruikers: tests/test_golden_core.py, tools/capture_golden.py,
tools/compare_runs.py.
"""

from __future__ import annotations

from pathlib import Path

VOLATILE = {"runId", "generatedAt", "artifacts"}
ARTIFACTS = ("omgevingsanalyse.json", "ils-draft.json",
             "ils-draft.features.28992.geojson", "validation.json", "run_summary.json")


def canon(doc):
    if isinstance(doc, dict):
        out = {}
        for k, v in doc.items():
            if k in VOLATILE:
                continue
            if k == "file" and isinstance(v, str):
                out[k] = Path(v).name  # aoi-invoerpad is per-run; naam is stabiel
            else:
                out[k] = canon(v)
        return out
    if isinstance(doc, list):
        return [canon(v) for v in doc]
    return doc


def fase_samenvatting(manifest: dict, records: list[dict]) -> list[dict]:
    """Per manifest-fase: taken en deliveredStatus-tellingen (deterministisch).

    Bewijs-instrument voor golden-per-fase: geen tijden, geen volgorde-afhankelijkheid
    (tellingen), join op lijstItemId.
    """
    from collections import Counter

    fase_van = {t["id"]: ph["id"]
                for ph in manifest["phases"] for t in (ph.get("tasks") or [])}
    uit = []
    for ph in manifest["phases"]:
        recs = [r for r in records if fase_van.get(r["lijstItemId"]) == ph["id"]]
        c = Counter(r["deliveredStatus"] for r in recs)
        uit.append({
            "fase": ph["id"], "taken": len(recs),
            "delivered": c.get("delivered", 0),
            "manualAction": c.get("manual-action", 0),
            "notDelivered": c.get("not-delivered", 0),
            "nvt": c.get("nvt", 0),
        })
    return uit
