from __future__ import annotations

from typing import Any

from services.hybrid_bridge import post_execution_hooks


def register_hybrid(state: dict[str, Any]) -> dict[str, Any]:
    execution = state.get("execution")
    if not execution or state.get("error"):
        return {}
    hooks = post_execution_hooks(
        execution,
        run_id=state.get("run_id"),
        register_pv=state.get("register_pv", True),
        export_3d=state.get("export_3d", True),
    )
    return {"hybrid": hooks}
