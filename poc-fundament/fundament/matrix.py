"""Agent–fase–tool matrix: het manifest als leesbare tabel (md)."""

from __future__ import annotations

_BINDINGS = ("auto", "partial", "manual", "out-of-scope")


def _counts(tasks: list[dict]) -> str:
    parts = [f"{sum(1 for t in tasks if t['binding'] == b)} {b}"
             for b in _BINDINGS if any(t["binding"] == b for t in tasks)]
    return ", ".join(parts) if parts else "—"


def _classes(tasks: list[dict]) -> str:
    classes = []
    for t in tasks:
        c = (t.get("tool") or {}).get("class")
        if c and c not in classes:
            classes.append(c)
    return ", ".join(classes) if classes else "—"


def render_matrix(manifest: dict) -> str:
    lines = [
        "| fase | agent | tools | taken | bindingen | gate |",
        "|---|---|---|---|---|---|",
    ]
    for ph in manifest["phases"]:
        tasks = ph.get("tasks") or []
        gate = ph.get("gate") or {}
        gate_txt = ", ".join(gate.get("validate") or [])
        if gate.get("hitl"):
            gate_txt = (gate_txt + " " if gate_txt else "") + f"HITL: {gate['hitl']}"
        agent = ph["agent"]
        agent_txt = agent["role"] + (" (LLM)" if agent.get("llm") else "")
        lines.append(
            f"| {ph['id']} — {ph['title']} | {agent_txt} | {_classes(tasks)} "
            f"| {len(tasks)} | {_counts(tasks)} | {gate_txt or '—'} |"
        )
    return "\n".join(lines) + "\n"


def render_run_matrix(manifest: dict, records: list[dict]) -> str:
    by_id = {r["lijstItemId"]: r for r in records}
    lines = [
        "| fase | taak | binding | tool | status |",
        "|---|---|---|---|---|",
    ]
    for ph in manifest["phases"]:
        for t in ph.get("tasks") or []:
            tool = t.get("tool") or {}
            tool_txt = f"{tool.get('class', '—')}:{tool.get('ref', '—')}" if tool else \
                (t.get("manualPointer") or "—")
            status = by_id.get(t["id"], {}).get("deliveredStatus", "—")
            lines.append(f"| {ph['id']} | {t['id']} | {t['binding']} | {tool_txt} | {status} |")
    return "\n".join(lines) + "\n"
