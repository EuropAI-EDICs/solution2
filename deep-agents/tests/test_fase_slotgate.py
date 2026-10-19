"""Slotgate-tests (M3): het manifest stuurt de wiring — agenten buiten hun
fase hebben geen tools. Offline, LLM-vrij (pytest, standaardsuite)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import fase_slotgate as fs


class FakeTool:
    def __init__(self, name: str):
        self.name = name


def _names(tools) -> set[str]:
    return {getattr(t, "name", getattr(t, "__name__", "")) for t in tools}


def test_manifest_bestaat_en_dekt_vijf_fasen():
    manifest = fs.load_manifest("minigim")
    assert manifest is not None
    assert [p["id"] for p in manifest["phases"]] == [
        "F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
        "F3-doorrekening", "F4-synthese"]


def test_resolve_agent_phases_rol_splits_en_aliassen():
    manifest = fs.load_manifest("minigim")
    out = fs.resolve_agent_phases(manifest)
    assert out["minigim"] == ["F1-omgevingsanalyse", "F3-doorrekening"]
    assert out["intake"] == ["F0-intake"]
    assert out["geospecialist"] == ["F2-gebiedsindeling"]
    assert out["critic"] == ["F4-synthese"] and out["explainer"] == ["F4-synthese"]


def test_onbekende_rol_faalt_luid():
    manifest = {"poc": "x", "methodiek": "m", "phases": [
        {"id": "F1-x", "title": "X", "agent": {"role": "tovenaar"},
         "tasks": [{"id": "t", "binding": "auto",
                    "tool": {"class": "retrieval", "ref": "r"}}]}]}
    with pytest.raises(ValueError):
        fs.resolve_agent_phases(manifest)


def test_apply_slotgate_stript_tool_buiten_de_fase():
    """De kern van het bewijs: een tool die niet in de fase-pool van de agent
    zit wordt gestript — de wiring kan niet stilletjes afdwalen van het manifest."""
    manifest = fs.load_manifest("minigim")
    specs = [
        {"name": "intake", "description": "d", "system_prompt": "p", "model": None,
         "tools": [FakeTool("request_template"), FakeTool("run_minigim_live")]},
        {"name": "utrecht", "description": "d", "system_prompt": "p", "model": None,
         "tools": [FakeTool("run_minigim_live"), FakeTool("run_world_scene")]},
    ]
    out = {s["name"]: s for s in fs.apply_slotgate(specs, manifest, poc_agent_names={"minigim"})}
    intake = _names(out["intake"]["tools"])
    assert "run_minigim_live" not in intake          # buiten intakes fase → gestript
    assert "request_template" in intake              # fase-tool blijft
    utrecht = _names(out["utrecht"]["tools"])        # niet in het manifest → onaangetast
    assert "run_minigim_live" in utrecht and "run_world_scene" in utrecht


def test_catalog_discovery_blijft_binnen_poc_agenten():
    manifest = fs.load_manifest("minigim")
    specs = [{"name": "minigim", "description": "d", "system_prompt": "p", "model": None,
              "tools": [FakeTool("list_recipes"), FakeTool("run_minigim_live"),
                        FakeTool("submit_request")]}]
    out = {s["name"]: s for s in fs.apply_slotgate(specs, manifest, poc_agent_names={"minigim"})}
    minigim = _names(out["minigim"]["tools"])
    assert {"list_recipes", "run_minigim_live"} <= minigim   # catalog + fase-tool
    assert "submit_request" not in minigim                    # F0-gate is niet voor minigim


def test_journal_fases_en_gate(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"verdict": "pass", "label": "pilot"}), encoding="utf-8")
    fs.journal_fases_en_gate("minigim", tmp_path)
    fases = [e[3]["fase"] for e in events if e[0] == "fase"]
    assert fases == ["F0-intake", "F1-omgevingsanalyse", "F2-gebiedsindeling",
                     "F3-doorrekening", "F4-synthese"]
    gates = [e for e in events if e[0] == "gate"]
    assert len(gates) == 1 and gates[0][3]["verdict"] == "pass"


def test_journal_zonder_manifest_is_stil(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    monkeypatch.setitem(fs.MANIFEST_PATHS, "minigim", Path("/niet/bestaand.json"))
    fs.journal_fases_en_gate("minigim", tmp_path)
    assert events == []


def test_journal_zonder_run_summary_is_stil(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(fs.journal, "append",
                        lambda kind, agent, summary, **kw: events.append((kind, agent, summary, kw)))
    fs.journal_fases_en_gate("minigim", tmp_path)  # geen run_summary.json
    assert events == []


# ---- wiring (taak 2): poc_subagents past de slotgate toe ----

from pocs import poc_subagents  # noqa: E402


def test_poc_subagents_minigim_heeft_fase_en_catalog_tools():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    minigim = _names(specs["minigim"]["tools"])
    assert {"list_recipes", "get_recipe", "run_minigim_live"} <= minigim
    assert "submit_request" not in minigim and "validate_world_scene" not in minigim


def test_poc_subagents_agent_buiten_zijn_fase_heeft_geen_tools():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    assert "run_minigim_live" not in _names(specs["intake"]["tools"])
    assert "run_minigim_live" not in _names(specs["geospecialist"]["tools"])
    assert _names(specs["critic"]["tools"]) == {"validate_world_scene"}
    assert _names(specs["explainer"]["tools"]) == {"get_provenance", "crosscheck_formal_rule"}


def test_poc_subagents_agenten_buiten_manifest_ongewijzigd():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=None)}
    assert "run_world_scene" in _names(specs["utrecht"]["tools"])
    assert "run_breda_scan" in _names(specs["breda"]["tools"])
    assert _names(specs["normspecialist"]["tools"]) == {"search_norms", "submit_norm_cards"}


def test_poc_subagents_mcp_catalog_komt_door_de_slotgate():
    specs = {s["name"]: s for s in poc_subagents(mcp_tools=[
        FakeTool("search_records"), FakeTool("get_record"), FakeTool("run_opportunity_map")])}
    minigim = _names(specs["minigim"]["tools"])
    assert {"search_records", "get_record", "run_minigim_live"} <= minigim
    assert "list_recipes" not in minigim
