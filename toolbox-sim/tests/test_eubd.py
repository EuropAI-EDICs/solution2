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
