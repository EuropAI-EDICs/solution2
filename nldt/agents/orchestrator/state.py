from __future__ import annotations

from typing import Any, TypedDict


class OrchestratorState(TypedDict, total=False):
    run_id: str
    natural_language_request: str
    recipe_id: str
    resolved_inputs: dict[str, Any]
    catalog_hits: list[dict[str, Any]]
    lake_hits: list[dict[str, Any]]
    data_plane: str
    agent_plan: dict[str, Any]
    execution: dict[str, Any]
    validation_report: dict[str, Any]
    hybrid: dict[str, Any]
    explanation: dict[str, Any]
    error: str
    auto_approve_hitl: bool
    register_pv: bool
    export_3d: bool
