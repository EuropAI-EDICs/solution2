"""Canon-regel voor de M2-bewijsinstrumenten (één bron, drie gebruikers).

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
