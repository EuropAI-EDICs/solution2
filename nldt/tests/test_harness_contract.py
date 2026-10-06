from __future__ import annotations

import importlib.util
from pathlib import Path

from services.mcp_servers import data_server, poc_server

DEEP_AGENTS = Path(__file__).resolve().parents[2] / "deep-agents"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, DEEP_AGENTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_deep_agents_targets_only_nldt_mcp_servers() -> None:
    cfg = _load("mcp_client").build_client_config("http://x")
    assert set(cfg) == {"nldt-catalog", "nldt-process", "nldt-data", "nldt-poc"}


def test_state_changing_poc_operations_exist_on_poc_server() -> None:
    for fn in ("run_opportunity_map", "propose_scenarios", "run_scenario_sweep", "build_world_scene"):
        assert hasattr(poc_server, fn), fn


def test_read_only_operations_registered() -> None:
    assert hasattr(poc_server, "get_provenance")
    assert hasattr(poc_server, "crosscheck_formal_rule")
    assert hasattr(data_server, "inspect_geo_layer")
