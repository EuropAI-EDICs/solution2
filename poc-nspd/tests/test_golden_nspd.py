"""Golden-regressie voor de NSPD-fase-1-tracks (plan 2026-10-14-poc-nspd, taak 13).

Vier golden-tracks: ``wind-nl``, ``wind-be``, ``zon-nl``, ``zon-be`` (de demo-
tracks wind/zon beiderzijds van de grens; energietoets is test-score-only en
hoort bewust niet bij de goldens). Elke test draait de volledige pipeline
(``run.py``) naar een tmp-map en vergelijkt een bewust BEPERKTE veldset tegen
de frozen golden onder ``pipeline/goldens-nspd/<track>.json``:

- ``verdict``      <- run_summary.json: pipeline-eindoordeel van de Critic;
- ``output_rules`` <- formalrules.json: ``len(rules)`` — inclusief de +1
  orchestrator-constructie FR-AOI-01;
- ``formalized``   <- formalrules.json: aantal ``status=="formalized"`` — telt
  FR-AOI-01 bewust mee (+1 orchestrator-constructie FR-AOI-01, taak-9-zone-
  semantiek: de run voegt de AOI-basisrule toe zodra geen inclusion-regel van
  de shard executabel is; die telling is daardoor deterministisch);
- ``rejected``     <- formalrules.json: aantal ``status=="rejected"``;
- ``v2bStatus``    <- run_summary.json ``v2b.status``; hieronder apart ook hard
  op ``"pass"`` geëist (V2b jurisdictie-gate mag nooit driftigen).

Buiten de vergelijking (bewust, task-9-bevindingen): ``formalizedAt`` van
FR-AOI-01 is een dag-stamp die per dag drijft, en verder álle vluchtige
summary-velden (runId, generatedAt, durationS, artifact-sha256's, timings,
prov-tijdstempels). Zone-geometrie wordt hier niet IoU-vergelijken — de
reproduceerbaarheid van het eindoppervlak wordt bewezen door de aparte
controle-run (tweemaal wind-nl, verschil ≤ 0,1 %, zie rapport taak 13).

Netwerk: ``run.py`` is cache-first (``geodata.fetch_layer`` levert een geldige
cache vóór elke registry-consultatie en raakt alleen bij ``--refresh`` of een
afwijkende query-fingerprint het netwerk). De her-uitvoering hier geeft
``--refresh`` niet mee, dus een tweede run is netwerkvrij; een aparte
``--offline``-vlag is daarom bewust níét toegevoegd aan run.py.

Freeze-procedure (eerste keer, of na een bewuste, gereviewde gedragswijziging):

    NSPD_GOLDEN_FREEZE=1 .venv/bin/python -m pytest -m golden

Zonder die env-var faalt een ontbrekende golden hard (TDD: eerst de test
ROOD, dan de freeze-run, dan groen bij de tweede run).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.golden

TRACKS = ("wind-nl", "wind-be", "zon-nl", "zon-be", "bos-nl", "water-nl",
           "bodem-nl", "mobiliteit-nl")
FREEZE_ENV = "NSPD_GOLDEN_FREEZE"
GOLDEN_DIR = ROOT / "pipeline" / "goldens-nspd"

# de beperkte veldset (controller-besluit taak 13): alleen drift-gevoelige
# gedragsvelden, geen vluchtige metadata — zie module-docstring
GOLDEN_VELDEN = ("verdict", "output_rules", "formalized", "rejected", "v2bStatus")


def _golden_samenvatting(run_dir: Path) -> dict:
    """Normaliseer een run naar de beperkte golden-veldset."""
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    rules = json.loads((run_dir / "formalrules.json").read_text(encoding="utf-8"))
    return {
        "verdict": summary.get("verdict"),
        "output_rules": len(rules),
        "formalized": sum(1 for r in rules if r.get("status") == "formalized"),
        "rejected": sum(1 for r in rules if r.get("status") == "rejected"),
        "v2bStatus": (summary.get("v2b") or {}).get("status"),
    }


def _run(track: str, tmp: Path) -> Path:
    """Draai de pipeline cache-first voor één track; geef de run-map terug."""
    uit = tmp / track
    subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "--use-case", track, "--out", str(uit)],
        check=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    return uit


@pytest.mark.parametrize("track", TRACKS)
def test_golden_track(track, tmp_path):
    run_dir = _run(track, tmp_path)
    samenvatting = _golden_samenvatting(run_dir)
    golden = GOLDEN_DIR / f"{track}.json"
    if not golden.is_file():  # eerste keer: freeze (alleen met expliciete env-var)
        if os.environ.get(FREEZE_ENV) != "1":
            pytest.fail(
                f"golden ontbrekt: {golden} — freeze bewust met "
                f"{FREEZE_ENV}=1 .venv/bin/python -m pytest -m golden"
            )
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(samenvatting, indent=1, sort_keys=True) + "\n",
                          encoding="utf-8")
        return
    vast = json.loads(golden.read_text(encoding="utf-8"))
    gedrift = {veld: (samenvatting.get(veld), vast.get(veld))
               for veld in GOLDEN_VELDEN
               if samenvatting.get(veld) != vast.get(veld)}
    assert not gedrift, f"{track}: golden gedrift: {gedrift}"
    # V2b jurisdictie-gate: geen claim over de grens — altijd pass
    assert samenvatting["v2bStatus"] == "pass", f"{track}: v2b niet pass"


def test_controle_run_reproduceerbaarheid(tmp_path):
    """Spec-controle-run: wind-nl tweemaal → identieke uitkomst (≤0,1%, hier 0%).

    De golden-veldset hierboven vergelijkt bewust géén zone-geometrie (task-9-
    bevindingen: vluchtige velden uitgesloten). Deze test bewijst de reproduceer-
    baarheid van het eindoppervlak zelf: twee cache-first runs van dezelfde
    track moeten exact dezelfde ``headline.finalOpportunityKm2`` opleveren.
    """
    uitkomsten = []
    for i in (1, 2):
        run_dir = _run("wind-nl", tmp_path / f"c{i}")
        summary = json.loads(
            (run_dir / "run_summary.json").read_text(encoding="utf-8")
        )
        uitkomsten.append(summary["headline"]["finalOpportunityKm2"])
    assert uitkomsten[0] == uitkomsten[1], uitkomsten
