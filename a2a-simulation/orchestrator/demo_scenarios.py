"""Demo: LLM door meerdere scenario's met deterministische A2A-rekenblokken.

Zie architectuur-llm-gedreven-deepagents-met-deterministische-rekentools.md §10.2.

Usage (mesh moet draaien, of laat --start-mesh toe):
  export PYTHONPATH=../deep-agents:.
  export A2A_SIM_AUTH=static NLDT_STATIC_TOKENS=sim-toolbox-token
  python -m orchestrator.demo_scenarios
  python -m orchestrator.demo_scenarios --start-mesh
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def _print_trace(result: dict) -> None:
    print("\n--- tool / task trace ---")
    for msg in result.get("messages", []):
        for call in getattr(msg, "tool_calls", None) or []:
            name = call.get("name", "?")
            args = call.get("args", {})
            print(f"  • {name}({json.dumps(args, ensure_ascii=False)[:200]})")
        if getattr(msg, "type", "") == "tool":
            content = str(getattr(msg, "content", ""))[:300]
            if any(k in content for k in ("conflictCells", "responseText", '"mode": "nldt"')):
                print(f"    → artifact snippet: {content[:280]}…")


def _start_mesh(poc_ids: list[str], mode: str) -> list[subprocess.Popen]:
    py = os.environ.get(
        "NLDT_PYTHON",
        str(REPO / "nldt" / ".venv" / "bin" / "python"),
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}:{REPO / 'nldt'}"
    env["A2A_SIM_MODE"] = mode
    if mode == "nldt":
        env.setdefault("NLDT_A2A_URL", "http://127.0.0.1:8085")
        env.setdefault("NLDT_AUTH_MODE", "static")
        env.setdefault("NLDT_A2A_AUTO_HITL", "1")
        env.setdefault("NLDT_OFFLINE", "1")
    env.setdefault("A2A_SIM_AUTH", "static")
    env.setdefault("NLDT_STATIC_TOKENS", "sim-toolbox-token")
    procs: list[subprocess.Popen] = []
    for poc_id in poc_ids:
        env["A2A_POC_AGENT_ID"] = poc_id
        procs.append(
            subprocess.Popen(
                [py, "-m", "agents.app"],
                cwd=str(ROOT),  # noqa: PTH109 — PoC package `agents` lives here
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
    time.sleep(2)
    return procs


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-scenario LLM + A2A demo")
    parser.add_argument(
        "--start-mesh",
        action="store_true",
        help="Start rijnland + utrecht PoC servers locally",
    )
    parser.add_argument(
        "--mode",
        choices=("simulate", "nldt"),
        default=os.environ.get("A2A_SIM_MODE", "simulate"),
        help="PoC rekenblok: simulate fixtures of nldt orchestrator proxy",
    )
    args = parser.parse_args()
    os.environ["A2A_SIM_MODE"] = args.mode
    if args.mode == "nldt":
        os.environ.setdefault("NLDT_A2A_URL", "http://127.0.0.1:8085")
        os.environ.setdefault("NLDT_A2A_AUTO_HITL", "1")
        os.environ.setdefault("NLDT_OFFLINE", "1")
        os.environ.setdefault("NLDT_AUTH_MODE", "static")
    procs: list[subprocess.Popen] = []
    if args.start_mesh:
        print("Starting deterministic mesh (rijnland, utrecht)…")
        procs = _start_mesh(["rijnland", "utrecht"], args.mode)

    sys.path.insert(0, str(REPO / "deep-agents"))
    os.environ.setdefault("DEEP_AGENT_MODEL", "gemma4:12b-mlx")
    os.environ.setdefault("DEEP_AGENT_SUBMODEL", "gemma4:12b-mlx")
    os.environ.setdefault("A2A_SIM_AUTH", "static")
    os.environ.setdefault("NLDT_STATIC_TOKENS", "sim-toolbox-token")

    from orchestrator.agent import build_agent

    question = (
        "Doorloop **twee** scenario's en gebruik overal het architectuurpatroon:\n"
        "1) task → scenario_analist: run plan voor `rijnland-peil-conflict`\n"
        "2) delegate_to_poc_agent → rijnland met die recipe\n"
        "3) task → scenario_analist: run plan voor `utrecht-opportunity-map` (track wind)\n"
        "4) delegate_to_poc_agent → utrecht\n"
        "5) task → interpretatie: vergelijk de **getallen uit de A2A-artifacts** (geen schattingen)\n"
        "Antwoord in het Nederlands, compact."
    )
    print("\n=== Orchestrator (LLM) ===\n")
    agent = build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": "demo-multi-scenario"}},
    )
    _print_trace(result)
    print("\n=== Eindantwoord ===\n")
    print(result["messages"][-1].content)

    for p in procs:
        p.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
