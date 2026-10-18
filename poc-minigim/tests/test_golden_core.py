"""Gedeelde run-hulp voor golden- en vergelijk-tests (offline, stub-fetch)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import run as runmod  # noqa: E402  (test-files zetten sys.path vóór import)
from minigim import checklist as clmod
from minigim.canon import ARTIFACTS, canon

from tests import fixtures


def run_and_canon(work: Path, label: str = "golden") -> tuple[Path, Path]:
    """Draait de offline run en schrijft canonieke kopieën naar work/canon.

    Geeft (run_dir, canon_dir); de canon-dir bevat dezelfde bestandsnamen.
    """
    fake = fixtures.fake_fetch_layer_factory()
    aoi = work / "plangrens.geojson"
    aoi.write_text(json.dumps(fixtures.AOI_FC), encoding="utf-8")
    with mock.patch.object(clmod, "fetch_layer", fake):
        rc = runmod.main(["--aoi", str(aoi), "--label", label,
                          "--runs-dir", str(work / "runs")])
    assert rc == 0, "offline run faalde"
    run_dir = next((work / "runs").iterdir())
    canon_dir = work / "canon"
    canon_dir.mkdir()
    for name in ARTIFACTS:
        doc = json.loads((run_dir / name).read_text(encoding="utf-8"))
        (canon_dir / name).write_text(
            json.dumps(canon(doc), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return run_dir, canon_dir
