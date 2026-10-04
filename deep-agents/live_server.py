"""Simulation dashboard server: run the deep agents per POC demo.

Serves runs/ at the root plus a small API:
  GET  /                dashboard
  GET  /api/pocs        POC catalog (dropdown)
  GET  /api/scenarios   scenario runs (Utrecht / Crosstrack)
  GET  /api/modes       prompting modes for ?poc=
  GET  /api/models      local Ollama models
  POST /api/run         start a simulation run (one at a time)
  GET  /api/status      running / question / exit code
  GET  /api/steps       the run journal (steps.jsonl)
  GET  /simulation/…    static nldt/simulation HTML demos (reference panels)
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
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import journal
from poc_demos import format_question, get_poc, list_pocs, modes_for_poc
from pocs import roster
from scenario_catalog import list_scenario_runs

HERE = Path(__file__).resolve().parent
from dotenv import load_dotenv  # noqa: E402

load_dotenv(HERE / ".env")  # so /api/models sees ZAI_API_KEY for the dropdown
RUNS = HERE / "runs"
SCENARIO_RUNS = HERE.parent / "poc" / "scenario-runs"
SIMULATION_DIR = HERE.parent / "nldt" / "simulation"
JOURNAL = RUNS / "live" / "steps.jsonl"
DASHBOARD = HERE / "dashboard.html"

app = FastAPI(title="nLDT deep-agent simulatie")
_proc: dict = {"p": None, "question": None, "rc": None, "run_id": 0}


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD)


@app.get("/api/pocs")
def pocs() -> list[dict]:
    return list_pocs()


@app.get("/api/scenarios")
def scenarios(poc: str | None = None) -> list[dict]:
    if poc:
        try:
            if not get_poc(poc)["requiresScenario"]:
                return []
        except KeyError:
            return []
    return list_scenario_runs(SCENARIO_RUNS)


@app.get("/api/modes")
def modes(poc: str = "utrecht") -> list[dict]:
    try:
        return [{"id": m["id"], "label": m["label"]} for m in modes_for_poc(poc)]
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/agents")
def agents() -> list[dict]:
    return roster()


@app.get("/api/models")
def models() -> list[str]:
    """Local Ollama models, plus Z.ai GLM entries when ZAI_API_KEY is set."""
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=5) as resp:
            names = [m["name"] for m in json.load(resp).get("models", [])]
    except Exception:
        names = []
    skip = ("embed", "bge-", "llava", "vision", "-vl", "cloud")
    usable = [n for n in names if not any(s in n for s in skip)]
    if os.environ.get("ZAI_API_KEY"):
        # GLM via Z.ai (like the ZCode assistant) — Anthropic-compatible endpoint
        usable = [f"zai:{m}" for m in ("glm-5.3-flash", "glm-5.3")] + usable
    return usable or names


class RunBody(BaseModel):
    poc: str = "utrecht"
    scenario: str = ""
    mode: str
    model: str
    submodel: str
    use_laya: bool = True


@app.post("/api/run")
def run(body: RunBody) -> dict:
    if _proc["p"] and _proc["p"].poll() is None:
        raise HTTPException(409, "Er draait al een simulatie — wacht tot die klaar is.")
    try:
        poc_spec = get_poc(body.poc)
    except KeyError as exc:
        raise HTTPException(400, str(exc)) from exc
    scenario = body.scenario.strip()
    if poc_spec["requiresScenario"]:
        if not scenario:
            raise HTTPException(400, f"POC '{body.poc}' vereist een scenario run.")
        if not (SCENARIO_RUNS / scenario / "scenario-report.json").is_file():
            raise HTTPException(400, f"Onbekende scenario run: {scenario}")
    try:
        question = format_question(body.poc, body.mode, scenario or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    local = models()
    for role, chosen in (("model", body.model), ("submodel", body.submodel)):
        if chosen not in local:
            raise HTTPException(
                400,
                f"{role} '{chosen}' is geen bekend model — kies er één uit de "
                "dropdown (lokaal Ollama of zai:GLM met ZAI_API_KEY).",
            )

    env = os.environ.copy()
    env["DEEP_AGENT_MODEL"] = body.model
    env["DEEP_AGENT_SUBMODEL"] = body.submodel
    env["NLDT_DEMO_POC"] = body.poc
    if body.mode == "keten" and body.poc == "utrecht":
        env["NLDT_REQUIRE_INTAKE"] = "1"  # hard gate: build refuses without a submitted request
    env["DEEP_AGENT_LAYA"] = "1" if body.use_laya else "0"
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    log = (RUNS / "live" / "run.log").open("w")
    _proc.update(
        p=subprocess.Popen(
            [sys.executable, "live.py", question],
            cwd=HERE,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        ),
        question=question,
        rc=None,
        run_id=_proc["run_id"] + 1,
    )
    return {"ok": True, "question": question, "run_id": _proc["run_id"], "poc": body.poc}


@app.post("/api/stop")
def stop() -> dict:
    if _proc["p"] and _proc["p"].poll() is None:
        _proc["p"].terminate()
        journal.append("error", "runner", "simulatie gestopt door gebruiker")
        return {"ok": True, "stopped": True}
    return {"ok": True, "stopped": False}


@app.get("/api/status")
def status() -> dict:
    running = bool(_proc["p"] and _proc["p"].poll() is None)
    if _proc["p"] and not running and _proc["rc"] is None:
        _proc["rc"] = _proc["p"].returncode
    return {
        "running": running,
        "question": _proc["question"],
        "rc": _proc["rc"],
        "run_id": _proc["run_id"],
        "ever_ran": _proc["p"] is not None,
    }


@app.get("/api/steps")
def steps() -> PlainTextResponse:
    if not JOURNAL.is_file():
        return PlainTextResponse("")
    return PlainTextResponse(JOURNAL.read_text(encoding="utf-8"))


@app.get("/simulation/{path:path}")
def simulation_assets(path: str) -> FileResponse:
    target = (SIMULATION_DIR / path).resolve()
    if not str(target).startswith(str(SIMULATION_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(target)


@app.get("/{path:path}")
def files(path: str) -> FileResponse:
    target = (RUNS / path).resolve()
    if not str(target).startswith(str(RUNS.resolve())) or not target.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(target)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NLDT_SIM_PORT", "8765")))
