# nldt/tests/test_full_catalogue_adapters.py
"""Full-catalogus adaptertests: draaien tegen een gestarte toolbox-sim (--full).

Start: ``cd toolbox-sim && ../nldt/.venv/bin/python -m app.server --full`` en draai
daarna met ``NLDT_FULL_SIM=1`` (zonder die env skippen de live-tests netjes).
De offline UCSAdapter merge/strip-tests onderaan draaien altijd (httpx.MockTransport,
geen sim nodig).
"""
import httpx
import json
import os
from pathlib import Path

import pytest

SIM_ENV = Path(__file__).resolve().parents[2] / "toolbox-sim" / ".env.sim"
OFFERS_DIR = Path(__file__).resolve().parents[1] / "data" / "dataspace" / "offers"

# B1: het volledige env-blok (zowel .env.sim als de EDC-setdefaults) mag alléén
# draaien bij een echte full-sim run. Zonder NLDT_FULL_SIM blijft deze module
# inert — anders snapshotten data_platform e.a. bij latere import in dezelfde
# pytest-run de live-env (MOCK=false, URLs) en faalt de suite zonder draaiende sim.
if os.environ.get("NLDT_FULL_SIM"):
    if SIM_ENV.exists():
        for line in SIM_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

    os.environ.setdefault("NLDT_EDC_MANAGEMENT_URL", "http://127.0.0.1:9197")
    os.environ.setdefault("NLDT_EDC_MANAGEMENT_TOKEN", "sim-toolbox-token")

from services.adapters import dataspace_connector  # noqa: E402
from services.process_adapter.router import UCSAdapter  # noqa: E402

MODEL_IDS = [
    "neighbourhood-energy-demand", "building-environmental-footprint", "renovation-strategies",
    "urban-planning-vulnerability", "urban-mobility", "pollution-propagation", "police-routing",
]


def _first_offer_uid() -> str:
    """Eerste uid uit nldt/data/dataspace/offers — exact de bron die de sim --full laadt."""
    offer_files = sorted(OFFERS_DIR.glob("*.json"))
    assert offer_files, "geen offers in nldt/data/dataspace/offers"
    return json.loads(offer_files[0].read_text(encoding="utf-8"))["uid"]


@pytest.mark.skipif(not os.environ.get("NLDT_FULL_SIM"), reason="start de sim met --full en NLDT_FULL_SIM=1")
def test_edc_negotiate_and_transfer_live():
    offer_uid = _first_offer_uid()
    result = dataspace_connector.negotiate_and_transfer(offer_uid)
    assert result["backend"] == "http"
    assert result["negotiationState"] == "CONFIRMED"
    assert result["transferState"] == "COMPLETED"
    assert result["offerUid"] == offer_uid
    assert "destination" in result


@pytest.mark.skipif(not os.environ.get("NLDT_FULL_SIM"), reason="start de sim met --full en NLDT_FULL_SIM=1")
@pytest.mark.parametrize("process_id", MODEL_IDS)
def test_model_processes_via_ucs_adapter(process_id):
    inputs = {"intensity_kwh_per_m2_year": 10.0} if "energy" in process_id else {}
    if "footprint" in process_id:
        inputs = {"carbon_kg_per_m2": 200.0}
    adapter = UCSAdapter()
    outputs = adapter.execute(process_id, inputs)
    assert outputs["model"] == process_id
    assert outputs["deterministic"] is True


# --- B2: offline UCSAdapter-dekking (geen sim, geen NLDT_FULL_SIM nodig) --------


def _mock_ucs_http(monkeypatch, response_json) -> dict:
    """Pin UCSAdapter's HTTP-call op httpx.MockTransport; retourneert de captures."""
    monkeypatch.setenv("UCS_BASE_URL", "http://ucs.test")
    monkeypatch.setenv("UCS_TOKEN", "test-token")
    captured: dict = {}
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=response_json)

    def client_factory(*args, **kwargs):
        kwargs.setdefault("transport", httpx.MockTransport(handler))
        return real_client(*args, **kwargs)

    # router.py doet ``with httpx.Client(timeout=120.0) as client`` — injecteer
    # de MockTransport op het laagste werkende punt (de Client-constructor).
    monkeypatch.setattr("services.process_adapter.router.httpx.Client", client_factory)
    return captured


def test_ucs_adapter_model_envelope_merge(monkeypatch):
    """Model-run-envelope: outputs gemerged met model/deterministic/provenance."""
    envelope = {
        "model": "urban-mobility",
        "deterministic": True,
        "outputs": {"od_matrix_trips_day": {"trips": 42}},
        "provenance": {"run": "sim-1"},
    }
    captured = _mock_ucs_http(monkeypatch, envelope)
    result = UCSAdapter().execute("urban-mobility", {})
    assert result["model"] == "urban-mobility"
    assert result["deterministic"] is True
    assert result["od_matrix_trips_day"] == {"trips": 42}
    assert result["provenance"] == {"run": "sim-1"}
    assert captured["url"] == "http://ucs.test/api/v1/experiments/trigger-process"
    assert captured["payload"] == {"processId": "urban-mobility", "inputs": {}}
    assert captured["auth"] == "Bearer test-token"


def test_ucs_adapter_replay_strip(monkeypatch):
    """Replay-antwoord: alléén outputs, zonder 'model'-key (strip-tak ongewijzigd)."""
    replay = {
        "outputs": {"verdict": "pass", "runId": "X"},
        "provenance": "sim-replay://canonical/X",
    }
    _mock_ucs_http(monkeypatch, replay)
    result = UCSAdapter().execute("urban-mobility", {})
    assert result == {"verdict": "pass", "runId": "X"}
    assert "model" not in result
