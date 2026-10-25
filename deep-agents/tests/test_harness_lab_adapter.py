"""Harness-lab adapter-tests (offline): variant-toepassing, grant-patch en
de fake-modus-probe end-to-end. De llm-modus-probe volgt het S1/S7-patroon:
expliciet met `pytest -m llm`, geskipt zonder LDT_DEEP_AGENTS_ENDPOINT.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import fase_slotgate as fs
import harness_lab_adapter as adapter

HERE = Path(__file__).resolve().parents[1]


class FakeTool:
    def __init__(self, name: str):
        self.name = name


def _names(tools) -> set[str]:
    return {getattr(t, "name", getattr(t, "__name__", "")) for t in tools}


@pytest.fixture(scope="module")
def specs():
    import pocs

    return pocs.poc_subagents(mcp_tools=None)


def _schrijf_variant(tmp_path: Path, variant: dict, prompt_tekst: str | None = None) -> Path:
    if prompt_tekst is not None:
        (tmp_path / "files").mkdir(exist_ok=True)
        (tmp_path / "files" / "variant-prompt.md").write_text(prompt_tekst, encoding="utf-8")
    pad = tmp_path / "variant.json"
    pad.write_text(json.dumps(variant), encoding="utf-8")
    return pad


# ---- apply_variant ---------------------------------------------------------

def test_apply_variant_is_puur_en_wisselt_prompt(tmp_path, specs):
    variant = {"id": "v-minigim", "title": "V", "components": [
        {"type": "prompt", "target": "poc/minigim", "path": "files/variant-prompt.md"},
        {"type": "modelPin", "target": "subagent",
         "env": {"DEEP_AGENT_SUBMODEL": "test:1b"}},
    ]}
    pad = _schrijf_variant(tmp_path, variant, "MINIGIM-VARIANT-PROMPT")
    kopie = json.dumps([{k: v for k, v in s.items() if k != "model"} for s in specs],
                       default=str)

    gepatcht, ctx = adapter.apply_variant(specs, variant, variant_path=pad)

    assert ctx["prompts"]["minigim"] == "MINIGIM-VARIANT-PROMPT"
    assert ctx["model_env"] == {"DEEP_AGENT_SUBMODEL": "test:1b"}
    minigim = next(s for s in gepatcht if s["name"] == "minigim")
    assert minigim["system_prompt"] == "MINIGIM-VARIANT-PROMPT"
    # zuiverheid: de invoerlijst is ongewijzigd
    origineel = next(s for s in specs if s["name"] == "minigim")
    assert origineel["system_prompt"] != "MINIGIM-VARIANT-PROMPT"
    assert json.dumps([{k: v for k, v in s.items() if k != "model"} for s in specs],
                      default=str) == kopie


def test_apply_variant_orchestrator_en_onbekende_target(tmp_path, specs):
    variant = {"id": "v-orch", "title": "V", "components": [
        {"type": "prompt", "target": "recipe_driver", "path": "files/variant-prompt.md"},
    ]}
    pad = _schrijf_variant(tmp_path, variant, "ORCH-VARIANT")
    _, ctx = adapter.apply_variant(specs, variant, variant_path=pad)
    assert ctx["orchestrator_prompt"] == "ORCH-VARIANT"

    slecht = {"id": "v-slecht", "title": "V", "components": [
        {"type": "prompt", "target": "poc/bestaat-niet", "path": "files/variant-prompt.md"}]}
    with pytest.raises(adapter.hl.HarnessLabError, match="onbekende prompt-target"):
        adapter.apply_variant(specs, slecht, variant_path=pad)


def test_apply_grants_deny_en_allow(specs):
    manifest = fs.load_manifest("minigim")
    # deny op de echte wiring: strip de fase-tool van critic
    gefilterd = adapter.apply_grants(
        specs, manifest, {"minigim"}, {}, {"critic": ["validate_world_scene"]})
    assert "validate_world_scene" not in _names(
        next(s["tools"] for s in gefilterd if s["name"] == "critic"))

    # allow haalt een gestripte tool terug, maar alleen binnen de
    # pre-slotgate toolset van die agent (synthetische wiring)
    synth = [{"name": "intake", "description": "d", "system_prompt": "p",
              "model": None,
              "tools": [FakeTool("request_template"), FakeTool("run_minigim_live")]}]
    terug = adapter.apply_grants(
        synth, manifest, {"minigim"}, {"intake": ["run_minigim_live"]}, {})
    assert "run_minigim_live" in _names(terug[0]["tools"])
    weg = adapter.apply_grants(
        synth, manifest, {"minigim"}, {}, {"intake": ["run_minigim_live"]})
    assert "run_minigim_live" not in _names(weg[0]["tools"])

    zonder = adapter.apply_grants(specs, manifest, {"minigim"}, {}, {})
    assert zonder is specs  # geen patch → geen kopij


def test_variant_env_weigert_vreemde_vars():
    slecht = {"id": "v", "title": "V", "components": [
        {"type": "modelPin", "target": "subagent", "env": {"HOME": "/tmp"}}]}
    with pytest.raises(adapter.hl.HarnessLabError, match="DEEP_AGENT"):
        adapter.variant_env(slecht)


# ---- run_probe (fake-modus, volledig offline) ------------------------------

TASKSET = {
    "id": "lab-test",
    "adapter": "deepagents",
    "tasks": [
        {"id": "s1", "kind": "static", "expect": [
            {"check": "slotgateAllows",
             "value": {"agent": "critic", "tools": ["validate_world_scene"]}},
            {"check": "slotgateForbids",
             "value": {"agent": "critic", "tools": ["run_minigim_live"]}, "hard": True},
        ]},
        {"id": "r1", "kind": "route", "delegateTo": "minigim",
         "question": "Doe een gebiedscheck.", "fakeAnswer": "gebiedscheck afgerond",
         "expect": [
             {"check": "delegatesTo", "value": "minigim", "hard": True},
             {"check": "answerContains", "value": ["gebiedscheck"]},
         ]},
        {"id": "a1", "kind": "standalone", "poc": "minigim",
         "question": "Welke recepten zijn er?", "fakeAnswer": "recepten opgesomd",
         "expect": [{"check": "answerContains", "value": ["recepten"]}]},
    ],
}


def _schrijf_taskset(tmp_path: Path, taskset: dict) -> Path:
    pad = tmp_path / "taskset.json"
    pad.write_text(json.dumps(taskset), encoding="utf-8")
    return pad


def _basis_variant(tmp_path: Path) -> tuple[dict, Path]:
    """Identiteits-variant: poc/minigim-prompt wijst op het live bestand."""
    variant = {"id": "baseline", "title": "huidige harness", "components": [
        {"type": "prompt", "target": "poc/minigim",
         "path": str(HERE / "prompts" / "poc" / "minigim.md")},
    ]}
    pad = tmp_path / "baseline.json"
    pad.write_text(json.dumps(variant), encoding="utf-8")
    return variant, pad


def test_run_probe_fake_end_to_end_en_deterministisch(tmp_path, specs):
    from fundament import harnesslab as hl

    variant, variant_pad = _basis_variant(tmp_path)
    taskset_pad = _schrijf_taskset(tmp_path, TASKSET)
    taskset = hl.load_taskset(taskset_pad)

    ev1 = adapter.run_probe(variant=variant, variant_path=variant_pad,
                            taskset=taskset, taskset_path=taskset_pad,
                            mode="fake", out_dir=tmp_path / "probe-1")
    ev2 = adapter.run_probe(variant=variant, variant_path=variant_pad,
                            taskset=taskset, taskset_path=taskset_pad,
                            mode="fake", out_dir=tmp_path / "probe-2")

    assert ev1["verdict"] == "pass" and ev2["verdict"] == "pass"
    assert ev1["score"]["total"] == 3
    # canon-determinisme: volatile probe-meta buiten vergelijking
    assert json.dumps(hl.canon_evidence(ev1), sort_keys=True) == \
        json.dumps(hl.canon_evidence(ev2), sort_keys=True)
    # isolatie: evidence staat in de probe-map
    assert (tmp_path / "probe-1" / hl.EVIDENCE_FILENAME).exists()


def test_run_probe_fake_kaakt_gezakte_check(tmp_path, specs):
    from fundament import harnesslab as hl

    taskset = json.loads(json.dumps(TASKSET))
    taskset["id"] = "lab-lek"
    taskset["tasks"][0]["expect"][1] = {
        "check": "slotgateForbids",
        "value": {"agent": "critic", "tools": ["validate_world_scene"]}}
    variant, variant_pad = _basis_variant(tmp_path)
    taskset_pad = _schrijf_taskset(tmp_path, taskset)

    ev = adapter.run_probe(variant=variant, variant_path=variant_pad,
                           taskset=hl.load_taskset(taskset_pad),
                           taskset_path=taskset_pad,
                           mode="fake", out_dir=tmp_path / "probe")
    assert ev["verdict"] == "fail"
    gezakt = [c for r in ev["results"] for c in r["checks"] if not c["pass"]]
    assert gezakt and gezakt[0]["detail"].startswith("gelekt")


def test_run_probe_route_zonder_delegateto_is_luid(tmp_path, specs):
    from fundament import harnesslab as hl

    taskset = {"id": "lab-slecht", "adapter": "deepagents", "tasks": [
        {"id": "r1", "kind": "route", "question": "x", "fakeAnswer": "y",
         "expect": [{"check": "answerContains", "value": ["y"]}]},
    ]}
    variant, variant_pad = _basis_variant(tmp_path)
    taskset_pad = _schrijf_taskset(tmp_path, taskset)
    with pytest.raises(adapter.hl.HarnessLabError, match="delegateTo"):
        adapter.run_probe(variant=variant, variant_path=variant_pad,
                          taskset=hl.load_taskset(taskset_pad),
                          taskset_path=taskset_pad,
                          mode="fake", out_dir=tmp_path / "probe")


# ---- llm-modus (expliciet, patroon S1/S7) ----------------------------------

ENDPOINT_ENV = "LDT_DEEP_AGENTS_ENDPOINT"


@pytest.mark.llm
@pytest.mark.skipif(not os.environ.get(ENDPOINT_ENV),
                    reason=f"{ENDPOINT_ENV} niet gezet — llm-modus vergt een echt model")
def test_run_probe_llm_route(tmp_path, specs):
    from fundament import harnesslab as hl

    taskset = {"id": "lab-llm", "adapter": "deepagents", "tasks": [
        {"id": "r1", "kind": "route",
         "question": "Which recipes exist for the Rijnland POC? Answer in one sentence.",
         "expect": [{"check": "delegatesTo", "value": "rijnland"},
                    {"check": "answerContains", "value": ["rijnland"]}]},
    ]}
    variant, variant_pad = _basis_variant(tmp_path)
    taskset_pad = _schrijf_taskset(tmp_path, taskset)
    ev = adapter.run_probe(variant=variant, variant_path=variant_pad,
                           taskset=hl.load_taskset(taskset_pad),
                           taskset_path=taskset_pad,
                           mode="llm", out_dir=tmp_path / "probe")
    assert ev["verdict"] == "pass"
