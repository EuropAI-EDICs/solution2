"""Simulation dashboard server: run the deep agents on a chosen scenario,
prompting mode and Ollama models, and stream their steps to the dashboard.

Serves runs/ at the root plus a small API:
  GET  /                dashboard
  GET  /api/scenarios   scenario runs available for world-scene builds
  GET  /api/modes       prompting modes (label + question template)
  GET  /api/models      local Ollama models
  POST /api/run         start a simulation run (one at a time)
  GET  /api/status      running / question / exit code
  GET  /api/steps       the run journal (steps.jsonl)
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
from pocs import roster

HERE = Path(__file__).resolve().parent
from dotenv import load_dotenv  # noqa: E402

load_dotenv(HERE / ".env")  # so /api/models sees ZAI_API_KEY for the dropdown
RUNS = HERE / "runs"
SCENARIO_RUNS = HERE.parent / "poc" / "scenario-runs"
JOURNAL = RUNS / "live" / "steps.jsonl"
DASHBOARD = HERE / "dashboard.html"

MODES = [
    {
        "id": "execute",
        "label": "Uitvoeren + visual demo",
        "template": "Bouw de world scene voor scenario run {rid} en toon de visual demo.",
    },
    {
        "id": "plan",
        "label": "Alleen run plan (geen executie)",
        "template": "Geef alléén een run plan voor de utrecht-world-scene recipe voor scenario run {rid}. Voer nog niets uit.",
    },
    {
        "id": "critical",
        "label": "Kritische toets, daarna uitvoeren",
        "template": "Toets kritisch of scenario run {rid} geschikt is voor een world-scene build: risico's, missende inputs, grounding. Bouw hem daarna en toon de demo.",
    },
    {
        "id": "compare",
        "label": "Control vs scenario vergelijking",
        "template": "Vergelijk de control- en scenario-lagen van scenario run {rid}, benoem de grootste deltas met hun mutaties, en toon de demo.",
    },
    {
        "id": "geo",
        "label": "Geo-analyse + critic-validatie",
        "template": "Bouw de world scene voor scenario run {rid}, laat de geospecialist de control- en scenario-lagen analyseren (areas in km2, deltas), en laat de critic de bundle valideren. Toon de demo.",
    },
    {
        "id": "normketen",
        "label": "Normketen: intake → norm → formaliseer",
        "template": "Nieuwe aanvraag: 'Ik wil weten waar een zonnepark mag in de gemeente Utrecht, bij voorkeur buiten de Groene contour.' Doorloop de normketen: (1) laat intake de aanvraag normaliseren tot een schema-geldig OpportunityMapRequest, (2) laat normspecialist de relevante normkaarten zoeken, (3) laat formalizer voor de belangrijkste normkaart een FormalRule opstellen en valideren. Rapporteer alle drie de artefacten (request-JSON, normkaarten, formal rule).",
    },
    {
        "id": "keten",
        "label": "Volledige keten (intake → normen → regel → build → validatie)",
        "template": "Volledige keten voor scenario run {rid}. Aanvraag: 'Ik wil weten waar een zonnepark mag in de gemeente Utrecht, bij voorkeur buiten de Groene contour.' Voer ALLEEN deze 6 stappen uit, in deze volgorde, en NIETS extra: (1) intake normaliseert en SUBMIT de aanvraag (submit_request), (2) normspecialist zoekt en SUBMIT de normkaarten (submit_norm_cards), (3) formalizer formaliseert de belangrijkste kaart en SUBMIT de regel (submit_formal_rule), (4) utrecht bouwt de world scene voor {rid} — gebruik alléén deze bestaande scenario-run en verzin GEEN nieuwe run-ids of extra scenario's, (5) daarna parallel: geospecialist analyseert de lagen en critic valideert de bundle, (6) explainer legt de provenance vast en crosscheckt of de engine de gesubmiteerde regel ook echt heeft uitgevoerd. Rapporteer daarna alle artefacten met hun submission-verdicts en STOP — geen verdere stappen.",
    },
]

app = FastAPI(title="nLDT deep-agent simulatie")
_proc: dict = {"p": None, "question": None, "rc": None, "run_id": 0}


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD)


@app.get("/api/scenarios")
def scenarios() -> list[str]:
    return sorted(
        p.name for p in SCENARIO_RUNS.iterdir() if (p / "scenario-report.json").is_file()
    )


@app.get("/api/modes")
def modes() -> list[dict]:
    return MODES


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
    scenario: str
    mode: str
    model: str
    submodel: str


@app.post("/api/run")
def run(body: RunBody) -> dict:
    if _proc["p"] and _proc["p"].poll() is None:
        raise HTTPException(409, "Er draait al een simulatie — wacht tot die klaar is.")
    if not (SCENARIO_RUNS / body.scenario / "scenario-report.json").is_file():
        raise HTTPException(400, f"Onbekende scenario run: {body.scenario}")
    template = next((m["template"] for m in MODES if m["id"] == body.mode), None)
    if template is None:
        raise HTTPException(400, f"Onbekende modus: {body.mode}")
    local = models()
    for role, chosen in (("model", body.model), ("submodel", body.submodel)):
        if chosen not in local:
            raise HTTPException(
                400,
                f"{role} '{chosen}' is geen bekend model — kies er één uit de "
                "dropdown (lokaal Ollama of zai:GLM met ZAI_API_KEY).",
            )

    question = template.format(rid=body.scenario)
    env = os.environ.copy()
    env["DEEP_AGENT_MODEL"] = body.model
    env["DEEP_AGENT_SUBMODEL"] = body.submodel
    if body.mode == "keten":
        env["NLDT_REQUIRE_INTAKE"] = "1"  # hard gate: build refuses without a submitted request
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
    return {"ok": True, "question": question, "run_id": _proc["run_id"]}


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


@app.get("/{path:path}")
def files(path: str) -> FileResponse:
    target = (RUNS / path).resolve()
    if not str(target).startswith(str(RUNS.resolve())) or not target.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(target)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NLDT_SIM_PORT", "8765")))
