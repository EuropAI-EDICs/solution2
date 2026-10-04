"""Background runner for the A2A live demo (LLM orchestrator or deterministic-only A2A)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SIM = Path(__file__).resolve().parent
DEEP = REPO / "deep-agents"

if str(SIM) not in sys.path:
    sys.path.insert(0, str(SIM))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_journal() -> None:
    spec = importlib.util.spec_from_file_location("journal", SIM / "journal.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["journal"] = mod
    spec.loader.exec_module(mod)


def _patch_a2a_logging() -> None:
    from agents.registry import agent_spec
    from federator import a2a_client
    from a2a_journal import log_result, log_send

    orig = a2a_client.send_message

    def wrapped(agent_id: str, text: str) -> dict[str, Any]:
        try:
            port = int(agent_spec(agent_id)["port"])
        except Exception:
            port = None
        log_send(agent_id, text, port)
        result = orig(agent_id, text)
        log_result(agent_id, result)
        return result

    a2a_client.send_message = wrapped  # type: ignore[method-assign]


def run_a2a_only(poc_id: str, message: str) -> None:
    _install_journal()
    import journal

    journal.reset(f"Deterministisch A2A (geen LLM): {poc_id} — {message[:120]}")
    _patch_a2a_logging()
    from federator import a2a_client

    result = a2a_client.send_message(poc_id, message)
    journal.append("done", poc_id, (result.get("responseText") or "")[:800])


def run_llm(question: str, thread_id: str) -> None:
    _install_journal()
    import journal

    journal.reset(question)
    if str(DEEP) not in sys.path:
        sys.path.insert(0, str(DEEP))
    os.environ.setdefault("A2A_SIM_AUTH", "static")
    os.environ.setdefault("NLDT_STATIC_TOKENS", "sim-toolbox-token")

    _patch_a2a_logging()

    from graph_trace import run_streamed  # noqa: WPS433 — deep-agents, journal patched
    from orchestrator.agent import build_agent

    agent = build_agent()
    try:
        answer = run_streamed(agent, question, thread_id=thread_id)
    except Exception as exc:
        journal.append("error", "runner", f"{type(exc).__name__}: {exc}")
        raise
    if not answer:
        entries = [
            json.loads(line)
            for line in journal.JOURNAL.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        answer = next(
            (
                e["summary"]
                for e in reversed(entries)
                if e.get("kind") == "assistant" and len(e.get("summary", "")) > 40
            ),
            "(geen eindantwoord)",
        )
    journal.append("done", "orchestrator", answer)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: demo_runner.py llm|a2a-only …", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "a2a-only":
        if len(sys.argv) < 4:
            print("usage: demo_runner.py a2a-only <poc_id> <message>", file=sys.stderr)
            return 2
        _install_journal()
        run_a2a_only(sys.argv[2], " ".join(sys.argv[3:]))
        return 0
    if cmd == "llm":
        if len(sys.argv) < 3:
            print("usage: demo_runner.py llm <question>", file=sys.stderr)
            return 2
        thread = os.environ.get("A2A_DEMO_THREAD", "a2a-demo-live")
        run_llm(" ".join(sys.argv[2:]), thread)
        return 0
    print(f"unknown cmd {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
