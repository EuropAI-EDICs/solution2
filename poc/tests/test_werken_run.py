# poc/tests/test_werken_run.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van de verharde fase-1/2/3-runtests. De werken-track is inclusion-
# dragend met één marker-dragende subklasse-verbod (art. 9.20, WE-06, na
# her-adjudicatie): de vloer vangt een stille overslaan van een inclusion of
# een terugkeer van de eerste-run-exclusie (die final naar 9.830 kelderde).
IOU_FLOOR = 0.999
REL_DELTA_CEILING = 1e-3

# Per-run stamps that a deterministic replay cannot and must not reproduce.
_VOLATILE_KEYS = ("runId", "generatedAt", "computedAt", "formalizedAt", "extractedAt")


def _latest(track: str) -> Path:
    dirs = sorted(p for p in (POC / "runs").glob(f"*-{track}") if (p / "run_summary.json").is_file())
    assert dirs, f"geen canonieke run voor {track}"
    return dirs[-1]


def _v3_numbers(summary: dict):
    """Parse (IoU, pipeline_km2, independent_km2) from the v3 summary line."""
    v3 = str(summary.get("v3", ""))
    m_iou = re.search(r"IoU ([0-9.]+)", v3)
    m_km = re.search(r"pipeline ([0-9.]+) km2 vs independent ([0-9.]+) km2", v3)
    assert m_iou and m_km, f"v3-regel mist IoU of pipeline-vs-independent: {v3!r}"
    return float(m_iou.group(1)), float(m_km.group(1)), float(m_km.group(2))


def _scrub(obj):
    """Drop run-id/tijdstempelvelden recursief zodat overgebleven dicts
    letterlijk vergelijkbaar zijn tussen replay en run-artefact."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def test_werken_run_passes_with_v3():
    run = _latest("werken")
    summary = json.loads((run / "run_summary.json").read_text())
    assert summary["verdict"] == "pass"
    v3_iou, pipeline_km2, independent_km2 = _v3_numbers(summary)
    assert v3_iou >= IOU_FLOOR, f"V3-IoU {v3_iou} onder vloer {IOU_FLOOR}"
    rel_delta = abs(pipeline_km2 - independent_km2) / pipeline_km2
    assert rel_delta <= REL_DELTA_CEILING, (
        f"independent wijkt {rel_delta:.3e} af van pipeline "
        f"({pipeline_km2} vs {independent_km2} km2)"
    )
    final_km2 = summary["headline"]["finalOpportunityKm2"]
    assert abs(pipeline_km2 - final_km2) / final_km2 <= REL_DELTA_CEILING
    # track-contract: final = inclusion-compositie (uitbreiding-bedrijventerrein
    # ∪ Stedelijk gebied); WE-06 is een marker (subklasse-gescoped verbod) —
    # een terugkeer van de exclusie keldert de final onder de helft van de
    # kleinste inclusion.
    aoi_km2 = summary["headline"]["aoiKm2"]
    assert 0 < final_km2 < 0.9 * aoi_km2, (
        f"final {final_km2} km2 valt buiten het inclusion-compositie-contract "
        f"(AOI {aoi_km2} km2)"
    )
    assert summary["headline"]["rulesTotal"] == 6
    zones = json.loads((run / "zones.json").read_text())
    inclusions = [z for z in zones if str(z.get("id", "")).startswith("ZR-inclusion_union")]
    markers = [z for z in zones if str(z.get("id", "")).startswith("ZR-conditional_mark")]
    diffs = [z for z in zones if str(z.get("id", "")).startswith("ZR-difference")]
    final = [z for z in zones if str(z.get("id", "")).startswith("ZR-final")]
    assert len(inclusions) == 1, "de twee inclusion-regels vormen één inclusion_union-zone"
    assert len(markers) == 4, f"verwacht 4 marker-zones (WE-01/02/05/06), gevonden {len(markers)}"
    assert not diffs, "er zijn geen exclusieregels in deze track (WE-06 is na her-adjudicatie een marker)"
    assert len(final) == 1
    dt = json.loads((run / "decision-table.json").read_text())
    assert len(dt.get("rows", dt if isinstance(dt, list) else [])) >= 1


def test_werken_replay_deterministic(tmp_path):
    run = _latest("werken")
    replay = tmp_path / "replay.json"
    import subprocess, sys
    # Spiegel van het replay-idioom uit test_water_run.py (zelfde caveat):
    # de asserts vergelijken de VOLLEDige normcards- en formalrules-artefacten
    # (run-id/tijdstempels gescrubd), niet alleen ids.
    code = ("import json;from pipeline.agents import NormAnalyst,NormFormalizer;"
            "cards=NormAnalyst().read('evidence-werken.json');"
            "rules=NormFormalizer().formalize(cards);"
            f"json.dump([[c.to_dict() for c in cards],[r.to_dict() for r in rules]],"
            f"open({str(replay)!r},'w'))")
    subprocess.run([sys.executable, "-c", code], cwd=POC, check=True,
                   env={"PYTHONPATH": str(POC), "PATH": "/usr/bin:/bin:/usr/local/bin"})
    cards, rules = json.loads(replay.read_text())
    run_cards = json.loads((run / "normcards.json").read_text())
    run_rules = json.loads((run / "formalrules.json").read_text())
    assert _scrub(cards) == _scrub(run_cards)
    assert _scrub(rules) == _scrub(run_rules)
