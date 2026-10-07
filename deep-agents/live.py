"""Live runner: streams an orchestrated agent run into the run journal.

Uses LangGraph stream_mode updates+messages with subgraphs so orchestrator and
specialist graphs (model/tools nodes) are visible. Dashboard:
http://127.0.0.1:8765/
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import journal  # noqa: E402
from agent import LOCAL_TOOLS, build_agent  # noqa: E402
from graph_trace import run_streamed  # noqa: E402
from hitl import (  # noqa: E402
    PENDING,
    PENDING_EXIT_CODE,
    ledger_append,
    verdict_to_decisions,
)
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.types import Command  # noqa: E402
from laya_router import augment_user_message  # noqa: E402
from models import check_ollama, orchestrator_model_name, subagent_model_name  # noqa: E402

HERE = Path(__file__).resolve().parent
THREAD_ID = "nldt-live"  # zelfde thread voor run én (auto-)resume; Task 6 hergebruikt deze
AUTO_COMMENT = "auto: dev-flag --auto-approve-hitl"

DEFAULT_QUESTION = (
    "Bouw de world scene voor scenario run 20260831T074521Z-wind-scen "
    "en toon de visual demo."
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live runner: streamt een agent-run naar de journal.")
    parser.add_argument("question", nargs="*", help="de vraag; zonder vraag wordt de standaardvraag gebruikt")
    parser.add_argument(
        "--auto-approve-hitl",
        action="store_true",
        help="dev-flag: hervat een HITL-interrupt in-process met een machinaal verdict",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args(sys.argv[1:])
    raw = " ".join(args.question) or DEFAULT_QUESTION
    journal.reset(raw)
    question = augment_user_message(raw)
    try:
        check_ollama([orchestrator_model_name(), subagent_model_name()])
    except SystemExit as exc:
        journal.append("error", "runner", str(exc))
        raise
    print(f"live run | {orchestrator_model_name()} + {subagent_model_name()}")
    print(f"vraag: {question}\n")

    cp_conn = sqlite3.connect(str(HERE / "runs" / "live" / "checkpoints.sqlite"), check_same_thread=False)
    saver = SqliteSaver(cp_conn)
    agent = build_agent(list(LOCAL_TOOLS), checkpointer=saver)
    try:
        answer = run_streamed(agent, question, thread_id=THREAD_ID)
    except Exception as exc:
        journal.append("error", "runner", f"{type(exc).__name__}: {exc}")
        print(f"\n[✗] {type(exc).__name__}: {exc}")
        raise

    if answer == PENDING:
        if not args.auto_approve_hitl:
            journal.append("hitl_pending", "orchestrator", "wacht op menselijk verdict")
            sys.exit(PENDING_EXIT_CODE)
        # dev-flag: hervat in-process met een expliciet machinaal verdict
        state = agent.get_state({"configurable": {"thread_id": THREAD_ID}})
        intr = next(t.interrupts[0] for t in state.tasks if t.interrupts)
        ledger_append({
            "kind": "verdict", "interruptId": intr.id, "threadId": THREAD_ID,
            "approved": True, "comment": AUTO_COMMENT,
            "operator": "dev-flag", "auto": True,
        })
        for _ in agent.stream(
            Command(resume=verdict_to_decisions(True, AUTO_COMMENT)),
            config={"configurable": {"thread_id": THREAD_ID}},
            stream_mode=["updates", "messages"], subgraphs=True,
        ):
            pass  # stream is lazy — itereren, anders voert de resume niets uit
        answer = ""  # sentinel mag niet in de journal belanden; bestaande fallback bepaalt het antwoord

    if not answer:
        import json as _json

        entries = [
            _json.loads(l)
            for l in journal.JOURNAL.read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        answer = next(
            (e["summary"] for e in reversed(entries)
             if e["kind"] == "assistant" and len(e.get("summary", "")) > 60),
            "(geen antwoord)",
        )
    journal.append("done", "orchestrator", answer)
    print("\n--- klaar ---")
    print(answer)


if __name__ == "__main__":
    main()
