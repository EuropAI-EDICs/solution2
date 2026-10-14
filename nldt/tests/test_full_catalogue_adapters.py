# nldt/tests/test_full_catalogue_adapters.py
"""Full-catalogus adaptertests: draaien tegen een gestarte toolbox-sim (--full).

Start: ``cd toolbox-sim && ../nldt/.venv/bin/python -m app.server --full`` en draai
daarna met ``NLDT_FULL_SIM=1`` (zonder die env skippen deze tests netjes).
"""
import json
import os
from pathlib import Path

import pytest

SIM_ENV = Path(__file__).resolve().parents[2] / "toolbox-sim" / ".env.sim"
OFFERS_DIR = Path(__file__).resolve().parents[1] / "data" / "dataspace" / "offers"

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
