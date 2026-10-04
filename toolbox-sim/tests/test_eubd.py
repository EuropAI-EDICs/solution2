# toolbox-sim/tests/test_eubd.py
import json
import os
from pathlib import Path

import pytest

DSN = os.environ.get("TOOLBOX_SIM_EUBD_DSN", "")


def test_builder_fails_hard_without_db():
    from build_fixtures import build_eubd_batch

    with pytest.raises(Exception) as excinfo:  # psycopg OperationalError — nooit stille mock
        build_eubd_batch("postgresql://nobody@127.0.0.1:1/nowhere", limit=5)
    assert "mock" not in str(excinfo.value).lower()


@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_eubd_dsn_fails_hard(empty):
    from build_fixtures import main

    with pytest.raises(SystemExit) as excinfo:  # lege DSN mag de EUBD-batch niet stil skippen
        main(["--eubd", empty])
    assert excinfo.value.code != 0


def test_plain_regen_preserves_eubd_manifest_entry(tmp_path, monkeypatch):
    import build_fixtures

    fx = tmp_path / "fixtures"
    (fx / "ngsi-ld").mkdir(parents=True)
    # Kleine stand-in voor de grote EUBD-fixture; build_fixtures checkt alleen aanwezigheid.
    (fx / "ngsi-ld" / "eubd-buildings.jsonld").write_text("[]\n", encoding="utf-8")
    original_entry = {
        "counts": {"ldt:Building": 2000},
        "file": "fixtures/ngsi-ld/eubd-buildings.jsonld",
        "sources": {"query": "exposure.entities category=0 iso_3166=NLD ORDER BY quadkey"},
    }
    (fx / "manifest.json").write_text(
        json.dumps({"batches": {"eubd-buildings": original_entry}}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_fixtures, "FIXTURES", fx)

    assert build_fixtures.main([]) == 0  # gewone regen, geen --eubd

    manifest = json.loads((fx / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["batches"]["eubd-buildings"] == original_entry


@pytest.mark.skipif(not DSN, reason="TOOLBOX_SIM_EUBD_DSN niet gezet — PostGIS exposure niet beschikbaar")
def test_eubd_entities_from_real_rows():
    from build_fixtures import build_eubd_batch

    batch = build_eubd_batch(DSN, limit=50)
    assert 0 < len(batch) <= 50
    for e in batch:
        assert e["type"] == "ldt:Building"
        assert e["id"].startswith("urn:ldt:eubd:building:")
        assert e["location"]["type"] == "GeoProperty"
        assert e["location"]["value"]["type"] == "MultiPolygon"
        assert e["sourceDoi"]["value"]  # echte release-DOI uit exposure.sources
