"""Live runner: streams an orchestrated agent run into the run journal.

Every observable step (delegations, tool calls, tool results, answers) is
appended to runs/live/steps.jsonl and echoed to stdout; the dashboard at
http://127.0.0.1:8765/ shows them live. Use directly (python live.py "vraag")
or via the simulation dashboard (live_server.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import journal  # noqa: E402  (env must be loaded first)
from agent import build_agent  # noqa: E402
from models import check_ollama, orchestrator_model_name, subagent_model_name  # noqa: E402

DEFAULT_QUESTION = (
    "Bouw de world scene voor scenario run 20260831T074521Z-wind-scen "
    "en toon de visual demo."
)


def _handle_message(msg) -> None:
    cls = type(msg).__name__
    if cls == "AIMessage":
        for call in msg.tool_calls or []:
            if call["name"] == "task":
                who = call["args"].get("subagent_type", "?")
                detail = (call["args"].get("description") or "")[:200]
                journal.append("delegate", "orchestrator", f"→ specialist: {who}", detail=detail)
                print(f"[→] delegate {who}: {detail}")
            else:
                args = ", ".join(f"{k}={v}" for k, v in list(call.get("args", {}).items())[:3])
                journal.append("tool_call", "orchestrator", f"{call['name']}({args})")
                print(f"[🔧] {call['name']}({args})")
        content = msg.content if isinstance(msg.content, str) else ""
        if content.strip() and not msg.tool_calls:
            journal.append("assistant", "orchestrator", content.strip()[:400])
            print(f"[💬] {content.strip()[:160]}")
    elif cls == "ToolMessage":
        if msg.name == "task":
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            journal.append(
                "tool_result", "specialist", f"specialist-rapport ({len(content)} tekens)"
            )
            print(f"[←] specialist report ({len(content)} chars)")


def main() -> None:
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    journal.reset(question)
    try:
        check_ollama([orchestrator_model_name(), subagent_model_name()])
    except SystemExit as exc:
        journal.append("error", "runner", str(exc))
        raise
    print(f"live run | {orchestrator_model_name()} + {subagent_model_name()}")
    print(f"vraag: {question}\n")

    agent = build_agent()
    seen = 0
    answer = ""
    try:
        for state in agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            config={"configurable": {"thread_id": "nldt-live"}, "recursion_limit": 60},
            stream_mode="values",
        ):
            messages = state.get("messages", [])
            for msg in messages[seen:]:
                _handle_message(msg)
            seen = len(messages)
            if messages:
                last = messages[-1]
                if type(last).__name__ == "AIMessage" and not getattr(last, "tool_calls", None):
                    content = last.content if isinstance(last.content, str) else ""
                    if content.strip():
                        answer = content
    except Exception as exc:  # surfaced in the dashboard, never a silent hang
        journal.append("error", "runner", f"{type(exc).__name__}: {exc}")
        print(f"\n[✗] {type(exc).__name__}: {exc}")
        raise

    journal.append("done", "orchestrator", answer or "(geen antwoord)")
    print("\n--- klaar ---")
    print(answer)


if __name__ == "__main__":
    main()
