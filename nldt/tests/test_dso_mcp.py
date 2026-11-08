from __future__ import annotations

import json

from services.mcp_servers import dso_server, dso_tools
from services.process_adapter.dso_handlers import DSO_PROCESS_DEFINITIONS


def test_tools_spiegelen_processen():
    assert set(dso_tools.DSO_TOOLS) == {
        "dso_kb_overview", "dso_kb_annotations", "dso_kb_document_structure",
        "dso_kb_tpod", "dso_kb_toets", "dso_kb_overlap", "dso_kb_gios",
        "dso_kb_point_in_gio", "dso_kb_refresh",
    }
    for tool, spec in dso_tools.DSO_TOOLS.items():
        assert spec["process_id"] in DSO_PROCESS_DEFINITIONS, tool
        assert spec["description"]


def test_façade_payload_shape(monkeypatch):
    monkeypatch.setenv("NLDT_OFFLINE", "1")

    def nep_lokaal(process_id, inputs):
        return {"jobId": "j-1", "status": "successful",
                "outputs": {"result": {"instrument": "testgm"}},
                "prov": {"bron": "test"}}

    monkeypatch.setattr(dso_server, "_execute_local", nep_lokaal)
    import asyncio

    uit = json.loads(asyncio.run(dso_server.dso_kb_annotations(instrument="testgm")))
    assert uit["tool"] == "dso_kb_annotations"
    assert uit["processId"] == "dso-kb-annotations"
    assert uit["jobId"] == "j-1"
    assert uit["outputs"]["result"]["instrument"] == "testgm"


def test_poort_8094_in_main_standaard():
    bron = __import__("pathlib").Path(dso_server.__file__).read_text(encoding="utf-8")
    assert "run_mcp_http(mcp, 8094)" in bron
