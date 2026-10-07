"""LangGraph stream tracing for deep-agent runs (orchestrator + subagent subgraphs).

Consumes CompiledStateGraph.stream(..., stream_mode=[\"updates\", \"messages\"],
subgraphs=True) and writes structured lines to journal + stdout.
"""

from __future__ import annotations

from typing import Any

import journal
from hitl import PENDING, args_summary, ledger_append

# Which subagent is running tools (set on task delegate, cleared on task result).
_active_specialist: str | None = None
_seen_nodes: set[tuple[Any, ...]] = set()
_seen_message_ids: set[str] = set()


def _ns_label(namespace: tuple[Any, ...]) -> str:
    if not namespace:
        return "orchestrator"
    parts = []
    for item in namespace:
        text = str(item)
        if text.startswith("task:"):
            parts.append(text.replace("task:", "subagent:"))
        elif "SubAgent" in text or "subagent" in text.lower():
            parts.append(text)
        else:
            parts.append(text[:48])
    return " / ".join(parts) if parts else "subgraph"


def _agent_for_ns(namespace: tuple[Any, ...]) -> str:
    global _active_specialist
    if _active_specialist:
        return _active_specialist
    label = _ns_label(namespace)
    if label.startswith("subagent:"):
        return label.split(":", 1)[-1].split("/")[0].strip() or "specialist"
    return "orchestrator" if not namespace else label


def _log_graph_node(namespace: tuple[Any, ...], node: str, meta: dict[str, Any] | None) -> None:
    key = (namespace, node, (meta or {}).get("langgraph_step"))
    if key in _seen_nodes:
        return
    _seen_nodes.add(key)
    agent = _agent_for_ns(namespace)
    step = (meta or {}).get("langgraph_step")
    summary = f"LangGraph → {node}" + (f" (stap {step})" if step is not None else "")
    journal.append(
        "graph_node",
        agent,
        summary,
        graph_node=node,
        graph_step=step,
        subgraph=_ns_label(namespace),
    )
    print(f"[graph] {agent} · {node}" + (f" #{step}" if step is not None else ""))


def _message_id(msg: Any) -> str:
    mid = getattr(msg, "id", None)
    if mid:
        return str(mid)
    return f"{type(msg).__name__}:{hash(str(msg.content)[:80])}"


def _text_of(msg: Any) -> str:
    """Plain text of an AIMessage — GLM (ChatAnthropic) returns a block list
    (thinking + text blocks), not a string."""
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                parts.append(str(block["text"]))
        return "\n".join(parts)
    return str(content)


def _handle_complete_message(msg: Any, namespace: tuple[Any, ...], meta: dict[str, Any] | None) -> None:
    global _active_specialist
    cls = type(msg).__name__
    agent = _agent_for_ns(namespace)
    node = (meta or {}).get("langgraph_node") or ""

    if cls in ("AIMessage", "AIMessageChunk"):
        if node:
            _log_graph_node(namespace, node, meta)
        for call in getattr(msg, "tool_calls", None) or []:
            name = call.get("name", "?")
            args = call.get("args") or {}
            if name == "task":
                who = args.get("subagent_type", "?")
                if who == "?":
                    # streamed chunk with empty args — the complete AIMessage with
                    # the real name follows and journals the delegate properly
                    return
                _active_specialist = str(who)
                detail = (args.get("description") or "")[:240]
                journal.append(
                    "delegate",
                    "orchestrator",
                    f"→ specialist: {who}",
                    detail=detail,
                    subgraph=_ns_label(namespace),
                )
                print(f"[→] delegate {who}: {detail[:120]}")
            else:
                arg_s = ", ".join(f"{k}={v!r}"[:60] for k, v in list(args.items())[:4])
                print(f"[🔧] {agent} · {name}({arg_s})")
        content = _text_of(msg)
        if content.strip() and not getattr(msg, "tool_calls", None):
            journal.append(
                "assistant",
                agent,
                content.strip()[:500],
                graph_node=node,
                subgraph=_ns_label(namespace),
            )
            print(f"[💬] {agent}: {content.strip()[:140]}")
    elif cls == "ToolMessage":
        if node:
            _log_graph_node(namespace, node, meta)
        name = getattr(msg, "name", None) or "tool"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if name == "task":
            journal.append(
                "tool_result",
                _active_specialist or "specialist",
                f"specialist klaar ({len(content)} tekens)",
                subgraph=_ns_label(namespace),
            )
            print(f"[←] {_active_specialist or 'specialist'} report ({len(content)} chars)")
            _active_specialist = None
        else:
            print(f"[✓] {agent} · {name}")


def _ingest_messages(messages: list[Any], namespace: tuple[Any, ...]) -> None:
    for msg in messages:
        mid = _message_id(msg)
        if mid in _seen_message_ids:
            continue
        # Skip streaming chunks without tool calls or final text
        if type(msg).__name__ == "AIMessageChunk":
            if getattr(msg, "tool_calls", None):
                _handle_complete_message(msg, namespace, None)
                _seen_message_ids.add(mid)
            continue
        _seen_message_ids.add(mid)
        _handle_complete_message(msg, namespace, None)


def run_streamed(
    agent: Any,
    question: str,
    *,
    thread_id: str = "nldt-live",
    recursion_limit: int = 60,
) -> str:
    """Stream a run; journal + stdout; returns final assistant answer if any."""
    global _active_specialist, _seen_nodes, _seen_message_ids
    _active_specialist = None
    _seen_nodes.clear()
    _seen_message_ids.clear()

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}
    answer = ""
    gezien_interrupt = False

    for chunk in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
        stream_mode=["updates", "messages"],
        subgraphs=True,
    ):
        if not isinstance(chunk, tuple) or len(chunk) != 3:
            continue
        namespace, mode, payload = chunk

        if mode == "updates" and isinstance(payload, dict):
            for node, delta in payload.items():
                if node.endswith(".before_agent") or node.endswith(".after_agent"):
                    continue
                if isinstance(delta, dict) and delta.get("messages"):
                    _ingest_messages(list(delta["messages"]), namespace)
                elif delta is not None:
                    _log_graph_node(namespace, node.split(".")[-1], None)

        elif mode == "messages" and isinstance(payload, tuple) and len(payload) == 2:
            msg, meta = payload
            mid = _message_id(msg)
            if mid in _seen_message_ids:
                continue
            if type(msg).__name__ == "AIMessageChunk" and not getattr(msg, "tool_calls", None):
                continue
            _seen_message_ids.add(mid)
            _handle_complete_message(msg, namespace, meta if isinstance(meta, dict) else None)
            if type(msg).__name__ in ("AIMessage", "AIMessageChunk"):
                content = _text_of(msg)
                if content.strip() and not getattr(msg, "tool_calls", None):
                    answer = content.strip()

        if mode == "updates":
            items = payload if isinstance(payload, tuple) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                for intr in item.get("__interrupt__", ()):
                    gezien_interrupt = True
                    value = getattr(intr, "value", {}) or {}
                    for act in value.get("action_requests", []):
                        thread_id_cfg = config.get("configurable", {}).get("thread_id", "")
                        samenvatting = f"{act.get('name')}: {args_summary(act.get('args', {}))}"
                        journal.append(
                            kind="hitl_request",
                            agent="orchestrator",
                            summary=samenvatting,
                            kind_event="hitl_request",
                            interruptId=getattr(intr, "id", ""),
                            tool=act.get("name", ""),
                            threadId=thread_id_cfg,
                        )
                        ledger_append({
                            "kind": "request",
                            "interruptId": getattr(intr, "id", ""),
                            "threadId": thread_id_cfg,
                            "tool": act.get("name", ""),
                            "argsSummary": args_summary(act.get("args", {})),
                        })

    return PENDING if gezien_interrupt else answer
