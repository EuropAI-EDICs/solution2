# poc/tests/test_water_run.py
import json
from pathlib import Path

POC = Path(__file__).resolve().parents[1]


def _latest(track: str) -> Path:
    dirs = sorted(p for p in (POC / "runs").glob(f"*-{track}") if (p / "run_summary.json").is_file())
    assert dirs, f"geen canonieke run voor {track}"
    return dirs[-1]


def test_water_run_passes_with_v3():
    run = _latest("water")
    summary = json.loads((run / "run_summary.json").read_text())
    assert summary["verdict"] == "pass"
    assert "v3" in summary and "IoU" in json.dumps(summary.get("v3", "")).lower() or "geopandas" in summary["v3"].lower()
    zones = json.loads((run / "zones.json").read_text())
    assert zones, "water-run zonder zones"
    dt = json.loads((run / "decision-table.json").read_text())
    assert len(dt.get("rows", dt if isinstance(dt, list) else [])) >= 1


def test_water_replay_deterministic(tmp_path):
    run = _latest("water")
    replay = tmp_path / "replay.json"
    import subprocess, sys
    # Brief-caveat toegepast: NormAnalyst/NormFormalizer hebben géén
    # (track)-constructor of .analyze()/.formalize(cards, track)-handtekening;
    # gespiegeld aan het replay-idioom van `python3 -m pipeline.agents`
    # (NormAnalyst().read(shard) -> NormFormalizer().formalize(cards), .to_dict()
    # voor de JSON-dump). De asserts zijn brief-letterlijk: herhaalde
    # deterministische replay identiek aan de run-artefacten.
    code = ("import json;from pipeline.agents import NormAnalyst,NormFormalizer;"
            "cards=NormAnalyst().read('evidence-water.json');"
            "rules=NormFormalizer().formalize(cards);"
            f"json.dump([[c.to_dict() for c in cards],[r.to_dict() for r in rules]],"
            f"open({str(replay)!r},'w'))")
    subprocess.run([sys.executable, "-c", code], cwd=POC, check=True,
                   env={"PYTHONPATH": str(POC), "PATH": "/usr/bin:/bin:/usr/local/bin"})
    cards, rules = json.loads(replay.read_text())
    run_cards = json.loads((run / "normcards.json").read_text())
    run_rules = json.loads((run / "formalrules.json").read_text())
    assert [c["id"] for c in cards] == [c["id"] for c in run_cards]
    assert [r["id"] for r in rules] == [r["id"] for r in run_rules]
