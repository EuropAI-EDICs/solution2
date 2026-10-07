"""Hervat een op de mens wachtende run na een dashboard-verdict.

Gebruik: python resume.py <interruptId> (--approved|--rejected) --comment "…" [--operator naam]
Exit: 0 = verwerkt · 3 = interrupt bestaat niet (al verbruikt) · 4 = ongeldig verdict.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import journal
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from agent import LOCAL_TOOLS, build_agent  # cirkelvrij: agent importeert hitl, niet resume
from hitl import args_summary, ledger_append, verdict_to_decisions

HERE = Path(__file__).resolve().parent
THREAD_ID = "nldt-live"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("interrupt_id")
    groep = p.add_mutually_exclusive_group(required=True)
    groep.add_argument("--approved", action="store_true")
    groep.add_argument("--rejected", action="store_true")
    p.add_argument("--comment", required=True)
    p.add_argument("--operator", default="operator")
    args = p.parse_args()

    # Cheap-fail vóór checkpointer/model: één check, geldt voor approve én reject.
    if not args.comment.strip():
        print("Het verdict vereist een niet-lege opmerking (leerstaat).", file=sys.stderr)
        return 4

    conn = sqlite3.connect(str(HERE / "runs" / "live" / "checkpoints.sqlite"), check_same_thread=False)
    saver = SqliteSaver(conn)
    agent = build_agent(list(LOCAL_TOOLS), checkpointer=saver)  # zelfde patroon als live.py (T5-fix)
    config = {"configurable": {"thread_id": THREAD_ID}}
    state = agent.get_state(config)
    intr = None
    for t in state.tasks:
        for i in t.interrupts:
            if i.id == args.interrupt_id:
                intr = i
    if intr is None:
        print(f"Interrupt {args.interrupt_id} bestaat niet (al verbruikt?)", file=sys.stderr)
        return 3

    tool = (intr.value.get("action_requests") or [{}])[0].get("name", "")
    ledger_append({
        "kind": "verdict", "interruptId": intr.id, "threadId": THREAD_ID,
        "tool": tool, "approved": bool(args.approved), "comment": args.comment.strip(),
        "operator": args.operator, "auto": False,
    })
    journal.append(
        "hitl_verdict", "operator",
        f"{'goedgekeurd' if args.approved else 'afgewezen'}: {tool} — {args_summary({'comment': args.comment.strip()})}",
        kind_event="hitl_verdict", interruptId=intr.id, operator=args.operator,
    )
    for _ in agent.stream(Command(resume=verdict_to_decisions(bool(args.approved), args.comment.strip())),
                          config=config, stream_mode=["updates", "messages"], subgraphs=True):
        pass  # stream is lazy — itereren, anders voert de resume niets uit
    return 0


if __name__ == "__main__":
    sys.exit(main())
