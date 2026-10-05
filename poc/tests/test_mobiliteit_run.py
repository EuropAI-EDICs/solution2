# poc/tests/test_mobiliteit_run.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_water_run.py (verharde fase-1-vorm). De mobiliteit-track is
# een all-marker track (vijf conditional-instructieregels, geen enkele
# onvoorwaardelijke weigering van roadside development in H4): de final zone
# is AOI-seeded, dus IoU/rel-delta liggen structureel dicht bij 1/0 — de vloer
# blijft waarde als regressiehek omdat een stille overslaan van een marker of
# een onbedoelde exclusie (bijv. MO-05 als track-brede exclusie over
# 1014 km2) de final-area en daarmee pipeline-vs-independent meteen scheef
# trekt.
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


def test_mobiliteit_run_passes_with_v3():
    run = _latest("mobiliteit")
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
    # all-marker contract: final = AOI (geen H4-regel weigert roadside
    # development onvoorwaardelijk) en precies vijf conditional markers.
    assert abs(final_km2 - summary["headline"]["aoiKm2"]) / summary["headline"]["aoiKm2"] <= REL_DELTA_CEILING, (
        f"final {final_km2} km2 wijkt af van AOI {summary['headline']['aoiKm2']} km2 — "
        "mobiliteit is een all-marker track, geen enkele regel mag oppervlak aftrekken"
    )
    zones = json.loads((run / "zones.json").read_text())
    # wrap_contract_zones mapt elke interne operatie via _OP_MAP naar een
    # contract-operatie (conditional_mark -> union, final -> union zonder
    # difference-regels), dus het onderscheid zit in het id-prefix.
    markers = [z for z in zones if str(z.get("id", "")).startswith("ZR-conditional_mark")]
    final = [z for z in zones if str(z.get("id", "")).startswith("ZR-final")]
    assert len(markers) == 5, f"verwacht 5 marker-zones (MO-01..MO-05), gevonden {len(markers)}"
    assert len(final) == 1
    assert summary["headline"]["rulesTotal"] == 5
    dt = json.loads((run / "decision-table.json").read_text())
    assert len(dt.get("rows", dt if isinstance(dt, list) else [])) >= 1
    # elke marker draagt zijn regel en een niet-lege geometrie (spiegel van de
    # fase-1-runtests: lege geometrie = stille overslaan)
    for z in markers:
        assert z.get("ruleIds"), f"marker {z.get('id')} zonder ruleIds"
        assert (z.get("areaKm2") or 0) > 0, f"marker {z.get('id')} leeg"


def test_mobiliteit_replay_deterministic(tmp_path):
    run = _latest("mobiliteit")
    replay = tmp_path / "replay.json"
    import subprocess, sys
    # Spiegel van het replay-idioom uit test_water_run.py (zelfde caveat:
    # NormAnalyst/NormFormalizer hebben géén (track)-constructor; de asserts
    # vergelijken de VOLLEDige normcards- en formalrules-artefacten
    # (run-id/tijdstempels gescrubd), niet alleen ids.
    code = ("import json;from pipeline.agents import NormAnalyst,NormFormalizer;"
            "cards=NormAnalyst().read('evidence-mobiliteit.json');"
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
