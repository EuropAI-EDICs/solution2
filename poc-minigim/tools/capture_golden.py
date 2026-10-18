#!/usr/bin/env python3
"""Vangt de offline (fixture) run van PoC-5 als golden-artefacten.

Vóór de M2-refactor draaien en committen — test_golden.py bewijst dat de
refactor byte-identieke (canonische) artefacten oplevert. Volatile velden
(runId, generatedAt) en de artifacts-lijst worden gecanoniseerd, evenals het
aoi-invoerpad (aoi.file: alleen de bestandsnaam is stabiel); report.html
en prov.json worden bewust uitgesloten (per-run tijden resp. aoi-pad).

Gebruik: ../nldt/.venv/bin/python tools/capture_golden.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run as runmod  # noqa: E402
from minigim import checklist as clmod  # noqa: E402

from tests import fixtures  # noqa: E402

GOLDEN = ROOT / "tests" / "golden"
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


def run_offline(runs_root: Path) -> Path:
    fake = fixtures.fake_fetch_layer_factory()
    aoi = runs_root / "plangrens.geojson"
    aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
    with mock.patch.object(clmod, "fetch_layer", fake):
        rc = runmod.main(["--aoi", str(aoi), "--label", "golden",
                          "--runs-dir", str(runs_root / "runs")])
    assert rc == 0, "offline run faalde — golden kan niet gevangen worden"
    return next((runs_root / "runs").iterdir())


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        run_dir = run_offline(Path(td))
        GOLDEN.mkdir(parents=True, exist_ok=True)
        for old in GOLDEN.iterdir():
            old.unlink()
        for name in ARTIFACTS:
            doc = json.loads((run_dir / name).read_text(encoding="utf-8"))
            (GOLDEN / name).write_text(
                json.dumps(canon(doc), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
        for lf in sorted((run_dir / "layers").glob("*.geojson")):
            (GOLDEN / f"layers__{lf.name}").write_text(lf.read_text(encoding="utf-8"),
                                                       encoding="utf-8")
    n_layers = len(list(GOLDEN.glob("layers__*")))
    print(f"golden: {len(ARTIFACTS)} artefacten + {n_layers} lagen → {GOLDEN}")


if __name__ == "__main__":
    main()
