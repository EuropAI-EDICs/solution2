from __future__ import annotations

import argparse
import asyncio
import json
import sys

from agents.registry import agent_spec, load_catalog
from federator.a2a_client import fetch_agent_card_proto, send_message
from federator.discovery import list_agents_live
from google.protobuf.json_format import MessageToDict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="A2A 1.x federation client (discover Agent Cards, message/send)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog", help="Static PoC catalog (recipes, ports)")

    p_list = sub.add_parser("list-agents", help="GET /.well-known/agent-card.json per PoC")
    p_list.add_argument("--offline", action="store_true")

    p_card = sub.add_parser("agent-card", help="Fetch one Agent Card (A2A 1.0)")
    p_card.add_argument("agent_id")

    p_send = sub.add_parser("send", help="Send Message (JSON-RPC binding)")
    p_send.add_argument("agent_id")
    p_send.add_argument("message", nargs="?", default="Run the default governed recipe.")

    args = parser.parse_args(argv)

    if args.cmd == "catalog":
        print(json.dumps(load_catalog(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "list-agents":
        if args.offline:
            print(json.dumps(load_catalog()["agents"], indent=2, ensure_ascii=False))
            return 0
        print(json.dumps(list_agents_live(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "agent-card":
        agent_spec(args.agent_id)
        card = fetch_agent_card_proto(args.agent_id)
        print(json.dumps(MessageToDict(card, preserving_proto_field_name=True), indent=2))
        return 0

    if args.cmd == "send":
        agent_spec(args.agent_id)
        result = send_message(args.agent_id, args.message)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
