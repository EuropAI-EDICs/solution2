from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from services.common import urbanstrategy_client as us


FIXDIR = Path(__file__).resolve().parents[1] / "fixtures" / "urbanstrategy"
RECEPTORS = FIXDIR / "receptors-demo.geojson"


def test_load_fixture_normalizes_laeq():
    fc = us.load_fixture(f"fixture://{RECEPTORS.name}")
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 5
    ids = [f["properties"]["id"] for f in fc["features"]]
    assert ids == sorted(ids)
    assert all("lAeq" in f["properties"] for f in fc["features"])
    by_id = {f["properties"]["id"]: f["properties"]["lAeq"] for f in fc["features"]}
    assert by_id["r-kern-ok"] == 38.2
    assert by_id["r-kern-hi"] == 42.5


def test_normalize_store_rows():
    payload = {
        "NOISE_RECEPTORS": [
            {"id": "a", "lon": 5.1, "lat": 52.1, "L_AEQ": 41.0, "I_LDEN": 43.0},
            {"id": "b", "lon": 5.2, "lat": 52.2, "L_AEQ": 39.0},
        ]
    }
    fc = us.normalize_receptors(payload, collection="NOISE_RECEPTORS")
    assert len(fc["features"]) == 2
    assert fc["features"][0]["properties"]["id"] == "a"
    assert fc["features"][0]["geometry"]["coordinates"] == [5.1, 52.1]


def test_login_and_get_bin_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "tok-abc"})
        if "/data/bin/" in request.url.path:
            assert request.url.params.get("token") == "tok-abc"
            return httpx.Response(
                200,
                json={
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"id": "x", "L_AEQ": 40.0},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [5.11, 52.09],
                            },
                        }
                    ],
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        token = us.login("https://us.example", "a@b.c", "secret", client=client)
        assert token == "tok-abc"
        raw = us.get_bin("https://us.example", token, "US_DEMO", client=client)
        fc = us.normalize_receptors(raw)
        assert len(fc["features"]) == 1


def test_fetch_refuses_live_without_flag(monkeypatch):
    monkeypatch.delenv("US_LIVE", raising=False)
    with pytest.raises(us.UrbanStrategyError, match="US_LIVE"):
        us.fetch_noise_receptors(base_url="https://us.example", bin_id="X")


def test_fetch_live_with_mock(monkeypatch):
    monkeypatch.setenv("US_LIVE", "1")
    monkeypatch.setenv("US_TOKEN", "tok-env")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("token") == "tok-env"
        body = json.loads(RECEPTORS.read_text(encoding="utf-8"))
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fc = us.fetch_noise_receptors(
            base_url="https://us.example",
            bin_id="US_DEMO",
            client=client,
        )
    assert len(fc["features"]) == 5
