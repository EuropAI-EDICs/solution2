"""Live A2A-simulation dashboard: mesh health, federated runs, LLM orchestrator trace.

  GET  /                 dashboard
  GET  /info.html        static architecture blurb
  GET  /api/catalog      PoC catalog
  GET  /api/mesh         live Agent Cards
  GET  /api/presets      demo scenarios
  GET  /api/models       Ollama models (optional)
  POST /api/run          start LLM or A2A-only run
  GET  /api/status       runner state
  GET  /api/steps        steps.jsonl
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SIM = Path(__file__).resolve().parent
DASHBOARD = SIM / "dashboard.html"
JOURNAL = SIM / "runs" / "live" / "steps.jsonl"

sys.path.insert(0, str(ROOT))

PRESETS = [
    {
        "id": "dual-llm",
        "label": "LLM: Rijnland + Utrecht (architectuur)",
        "kind": "llm",
        "meshPocs": ["rijnland", "utrecht"],
        "question": (
            "Doorloop **twee** scenario's en gebruik overal het architectuurpatroon:\n"
            "1) task → scenario_analist: run plan voor `rijnland-peil-conflict`\n"
            "2) delegate_to_poc_agent → rijnland met die recipe\n"
            "3) task → scenario_analist: run plan voor `utrecht-opportunity-map` (track wind)\n"
            "4) delegate_to_poc_agent → utrecht\n"
            "5) task → interpretatie: vergelijk de **getallen uit de A2A-artifacts** (geen schattingen)\n"
            "Antwoord in het Nederlands, compact."
        ),
    },
    {
        "id": "rijnland-llm",
        "label": "LLM: plan + A2A Rijnland peil-conflict",
        "kind": "llm",
        "meshPocs": ["rijnland"],
        "question": (
            "Plan via scenario_analist de recipe `rijnland-peil-conflict`, "
            "delegate naar rijnland via A2A, en laat interpretatie de artifact-getallen uitleggen. Nederlands, kort."
        ),
    },
    {
        "id": "rijnland-a2a",
        "label": "Alleen A2A: Rijnland (geen LLM)",
        "kind": "a2a-only",
        "meshPocs": ["rijnland"],
        "pocId": "rijnland",
        "message": "Run recipe rijnland-peil-conflict with full artifact JSON.",
    },
    {
        "id": "utrecht-a2a",
        "label": "Alleen A2A: Utrecht opportunity (geen LLM)",
        "kind": "a2a-only",
        "meshPocs": ["utrecht"],
        "pocId": "utrecht",
        "message": "Run utrecht-opportunity-map for track wind; return metrics JSON.",
    },
]

app = FastAPI(title="A2A-simulation live demo")
_proc: dict = {"p": None, "label": None, "rc": None, "run_id": 0}
_mesh: list[subprocess.Popen] = []


def _runner_python() -> str:
    venv = REPO / "deep-agents" / ".venv" / "bin" / "python"
    return str(venv if venv.is_file() else sys.executable)


def _mesh_env(mode: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}:{REPO / 'nldt'}"
    env["A2A_SIM_MODE"] = mode
    env.setdefault("A2A_SIM_AUTH", "static")
    env.setdefault("NLDT_STATIC_TOKENS", "sim-toolbox-token")
    if mode == "nldt":
        env.setdefault("NLDT_A2A_URL", "http://127.0.0.1:8085")
        env.setdefault("NLDT_A2A_AUTO_HITL", "1")
        env.setdefault("NLDT_OFFLINE", "1")
        env.setdefault("NLDT_AUTH_MODE", "static")
    return env


def _start_mesh(poc_ids: list[str], mode: str) -> None:
    _stop_mesh()
    py = os.environ.get("NLDT_PYTHON", _runner_python())
    env = _mesh_env(mode)
    for poc_id in poc_ids:
        env["A2A_POC_AGENT_ID"] = poc_id
        _mesh.append(
            subprocess.Popen(
                [py, "-m", "agents.app"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
    import time

    time.sleep(2)


def _stop_mesh() -> None:
    for p in _mesh:
        if p.poll() is None:
            p.terminate()
    _mesh.clear()


class RunBody(BaseModel):
    preset_id: str
    mesh_mode: str = "simulate"
    start_mesh: bool = True
    model: str = ""
    submodel: str = ""


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD)


@app.get("/info.html")
def info_page() -> FileResponse:
    return FileResponse(SIM / "index.html")


@app.get("/api/catalog")
def catalog() -> dict:
    from agents.registry import load_catalog

    return load_catalog()


@app.get("/api/mesh")
def mesh() -> list:
    from federator.discovery import list_agents_live

    return list_agents_live()


@app.get("/api/presets")
def presets() -> list:
    return PRESETS


@app.get("/api/models")
def models() -> list[str]:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.load(resp).get("models", [])]
    except Exception:
        names = []
    skip = ("embed", "bge-", "llava", "vision", "-vl", "cloud")
    usable = [n for n in names if not any(s in n for s in skip)]
    return usable or names


@app.post("/api/run")
def run(body: RunBody) -> dict:
    if _proc["p"] and _proc["p"].poll() is None:
        raise HTTPException(409, "Er draait al een run — wacht tot die klaar is.")
    preset = next((p for p in PRESETS if p["id"] == body.preset_id), None)
    if preset is None:
        raise HTTPException(400, f"Onbekend preset: {body.preset_id}")

    if body.start_mesh:
        _start_mesh(preset.get("meshPocs") or [], body.mesh_mode)
    os.environ["A2A_SIM_MODE"] = body.mesh_mode

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SIM}:{ROOT}:{REPO / 'deep-agents'}:{REPO / 'nldt'}"
    env.setdefault("A2A_SIM_AUTH", "static")
    env.setdefault("NLDT_STATIC_TOKENS", "sim-toolbox-token")
    if body.model:
        env["DEEP_AGENT_MODEL"] = body.model
    if body.submodel:
        env["DEEP_AGENT_SUBMODEL"] = body.submodel
    env["A2A_DEMO_THREAD"] = f"a2a-demo-{_proc['run_id'] + 1}"

    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("", encoding="utf-8")
    log = (SIM / "runs" / "live" / "run.log").open("w")
    py = _runner_python()
    runner = SIM / "demo_runner.py"

    if preset["kind"] == "a2a-only":
        cmd = [py, str(runner), "a2a-only", preset["pocId"], preset["message"]]
    else:
        cmd = [py, str(runner), "llm", preset["question"]]

    _proc.update(
        p=subprocess.Popen(cmd, cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT),
        label=preset["label"],
        rc=None,
        run_id=_proc["run_id"] + 1,
    )
    return {"ok": True, "run_id": _proc["run_id"], "label": preset["label"]}


@app.post("/api/stop")
def stop() -> dict:
    if _proc["p"] and _proc["p"].poll() is None:
        _proc["p"].terminate()
    _stop_mesh()
    return {"ok": True}


@app.get("/api/status")
def status() -> dict:
    running = bool(_proc["p"] and _proc["p"].poll() is None)
    if _proc["p"] and not running and _proc["rc"] is None:
        _proc["rc"] = _proc["p"].returncode
    return {
        "running": running,
        "label": _proc["label"],
        "rc": _proc["rc"],
        "run_id": _proc["run_id"],
        "ever_ran": _proc["p"] is not None,
        "mesh_procs": len(_mesh),
    }


@app.get("/api/steps")
def steps() -> PlainTextResponse:
    if not JOURNAL.is_file():
        return PlainTextResponse("")
    return PlainTextResponse(JOURNAL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("A2A_DEMO_PORT", "9190"))
    uvicorn.run(app, host="127.0.0.1", port=port)
