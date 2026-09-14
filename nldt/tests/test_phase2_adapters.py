from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from services.adapters import data_platform, keycloak_auth, play_visualise
from services.hybrid_bridge import fetch_ngsi_as_features, post_execution_hooks


def test_data_platform_mock_entities():
    entities = data_platform.list_entities(entity_type="AirQualityObserved")
    assert len(entities) == 1
    assert entities[0]["mock"] is True


def test_entities_to_geojson():
    fc = data_platform.entities_to_geojson(
        [
            {
                "id": "urn:ngsi-ld:Test:1",
                "type": "Test",
                "location": {
                    "type": "GeoProperty",
                    "value": {"type": "Point", "coordinates": [5.0, 52.0]},
                },
            }
        ]
    )
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1


def test_fetch_ngsi_as_features():
    fc = fetch_ngsi_as_features("AirQualityObserved")
    assert fc["type"] == "FeatureCollection"


def test_play_visualise_mock_register(tmp_path, monkeypatch):
    monkeypatch.setattr(play_visualise, "EXPORT_PUBLIC_BASE", "http://localhost:8084/exports")
    monkeypatch.setattr(play_visualise, "MOCK", True)
    monkeypatch.setattr(play_visualise, "PV_BASE_URL", "")
    fc = {"type": "FeatureCollection", "features": []}
    result = play_visualise.register_geojson_layer(
        geojson=fc, name="test-layer", export_store=tmp_path
    )
    assert result["dataSource"]["mock"] is True
    assert result["dataLayer"]["mock"] is True
    assert (tmp_path / f"{result['exportId']}.geojson").exists()


def test_keycloak_client_credentials(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak.test")
    monkeypatch.setenv("KEYCLOAK_REALM", "LDT")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "nldt-agent")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "secret")
    keycloak_auth.clear_token_cache()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "tok-abc", "expires_in": 300}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        token = keycloak_auth.get_service_token()
    assert token == "tok-abc"


def test_post_execution_hooks_mock():
    execution = {
        "recipeId": "spatial-overlay-analysis",
        "outputs": {
            "intersection": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
                            ],
                        },
                        "properties": {},
                    }
                ],
            },
            "statistics": {"totalAreaM2": 1.0},
        },
        "steps": [],
    }
    hooks = post_execution_hooks(execution, run_id="hook01")
    assert "web3dContext" in hooks
    assert hooks["web3dContext"]["type"] == "Web3DContext"
    assert "visualization" in hooks


def test_ngsi_ld_source_in_fetch_features():
    from services.process_adapter.handlers import execute_local

    out = execute_local("fetch-features", {"source": "ngsi-ld://AirQualityObserved"})
    assert out["features"]["type"] == "FeatureCollection"
