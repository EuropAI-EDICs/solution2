"""Breda five-value what-if scenario plane as a LangGraph StateGraph.

Mirrors the CLI in ``poc-breda/scenario_run.py`` but as explicit nodes:
S10 research (optional) → horizon inputs → det floor + LLM author → merge/gate
→ run → per-AI pathways → report.

Offline / unit tests use ``mode="stub"`` without importing poc-breda.
Live dispose still belongs in poc-breda deterministic engines.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class BredaScenarioState(TypedDict, total=False):
    run_id: str
    mode: Literal["stub", "live"]
    enable_deep_research: bool
    research_topic: str
    horizon_year: int
    max_scenarios: int
    lake_hints: list[dict[str, Any]]
    projections: list[dict[str, Any]]
    research_brief: dict[str, Any]
    research_rejected: list[dict[str, Any]]
    floor_specs: list[dict[str, Any]]
    llm_specs: list[dict[str, Any]]
    specs: list[dict[str, Any]]
    rejected_authoring: list[dict[str, Any]]
    baseline_scan: dict[str, Any]
    layers: dict[str, Any]
    build_whatif: bool
    out_dir: str
    report: dict[str, Any]
    llm_pathway_ids: list[str]
    whatif_html_path: str
    error: str
