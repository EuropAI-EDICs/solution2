# toolbox-sim/tests/test_fixtures_eindhoven.py
import json

from build_fixtures import CANONICAL_RUNS, build_eindhoven_batch

RUN = CANONICAL_RUNS["eindhoven-bp2op"]


def _batch():
    return build_eindhoven_batch(RUN)


def test_counts_match_artifacts():
    batch = _batch()
    by_type = {}
    for e in batch:
        by_type.setdefault(e["type"], []).append(e)
    assert len(by_type["ldt:ConversionRow"]) == len(json.loads((RUN / "omzettabel.json").read_text()))
    assert len(by_type["ldt:BronRegel"]) == len(json.loads((RUN / "bronregels.json").read_text()))
    assert len(by_type["ldt:DoelRegel"]) == len(json.loads((RUN / "doelregels.json").read_text()))
    assert len(by_type["ldt:KennisbankRelatie"]) == len(json.loads((RUN / "kennisbank.json").read_text()))
    assert len(by_type["ldt:PipelineRun"]) == 1


def test_row_chain_and_score_on_relationship():
    batch = _batch()
    bron = {e["id"] for e in batch if e["type"] == "ldt:BronRegel"}
    doel = {e["id"] for e in batch if e["type"] == "ldt:DoelRegel"}
    kb = {e["id"] for e in batch if e["type"] == "ldt:KennisbankRelatie"}
    rows = [e for e in batch if e["type"] == "ldt:ConversionRow"]
    assert rows
    for r in rows:
        assert r["hasBronRegel"]["object"] in bron
        if "suggestsDoelRegel" in r:
            assert r["suggestsDoelRegel"]["object"] in doel
            assert isinstance(r["suggestsDoelRegel"]["ldt:score"]["value"], (int, float))
        if "basedOnKennisbank" in r:
            assert r["basedOnKennisbank"]["object"] in kb
        assert r["status"]["value"] != "gekoppeld"


def test_unique_sorted_ids():
    batch = _batch()
    ids = [e["id"] for e in batch]
    assert len(set(ids)) == len(ids) == len(sorted(ids))
