# toolbox-sim/tests/test_catalogue.py
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAT = json.loads((REPO / "toolbox-sim" / "catalogue.json").read_text())

SIMULATED = {
    "EU LDT Identity Management",
    "EU LDT Data Platform",
    "EU LDT Play & Visualise",
    "EU LDT Use Cases & Scenarios",
    "EU LDT Marketplace",
}


def test_twenty_solutions():
    assert len(CAT["solutions"]) == 20
    names = [s["name"] for s in CAT["solutions"]]
    assert len(set(names)) == 20


def test_statuses_valid_and_grounded():
    for s in CAT["solutions"]:
        assert s["status"] in {"simulated", "consumed-as-data", "skipped"}
        if s["status"] == "skipped":
            assert s.get("reason"), f"{s['name']} skipped without reason"
        else:
            assert s.get("evidence"), f"{s['name']} without evidence"
        assert s["kind"] in {"tool", "algorithm-model"}


def test_simulated_set_matches_spec():
    got = {s["name"] for s in CAT["solutions"] if s["status"] == "simulated"}
    assert got == SIMULATED
    eubd = [s for s in CAT["solutions"] if s["name"] == "EU Building Database"]
    assert eubd[0]["status"] == "consumed-as-data"
