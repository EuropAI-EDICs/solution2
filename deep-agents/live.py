"""Live runner: streams an orchestrated agent run into the run journal.

Uses LangGraph stream_mode updates+messages with subgraphs so orchestrator and
specialist graphs (model/tools nodes) are visible. Dashboard:
http://127.0.0.1:8765/
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import journal  # noqa: E402
from agent import build_agent  # noqa: E402
from graph_trace import run_streamed  # noqa: E402
from laya_router import augment_user_message  # noqa: E402
from models import check_ollama, orchestrator_model_name, subagent_model_name  # noqa: E402

DEFAULT_QUESTION = (
    "Bouw de world scene voor scenario run 20260831T074521Z-wind-scen "
    "en toon de visual demo."
)


def main() -> None:
    raw = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    journal.reset(raw)
    question = augment_user_message(raw)
    try:
        check_ollama([orchestrator_model_name(), subagent_model_name()])
    except SystemExit as exc:
        journal.append("error", "runner", str(exc))
        raise
    print(f"live run | {orchestrator_model_name()} + {subagent_model_name()}")
    print(f"vraag: {question}\n")

    agent = build_agent()
    try:
        answer = run_streamed(agent, question)
    except Exception as exc:
        journal.append("error", "runner", f"{type(exc).__name__}: {exc}")
        print(f"\n[✗] {type(exc).__name__}: {exc}")
        raise

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
