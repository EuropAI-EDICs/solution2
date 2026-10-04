from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from a2a.helpers.proto_helpers import new_data_part, new_text_part
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types.a2a_pb2 import Task, TaskState, TaskStatus

from agents.registry import agent_spec

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "tasks"


class PocDeepAgentExecutor(AgentExecutor):
    """Deterministic A2A rekenblok (architectuur §2): simulate fixtures of nldt orchestrator."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._running: set[str] = set()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        self._running.discard(task_id)
        if not task_id or not context.context_id:
            return
        updater = TaskUpdater(event_queue, task_id, context.context_id)
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_message = context.message
        task_id = context.task_id
        context_id = context.context_id
        if not user_message or not task_id or not context_id:
            return

        self._running.add(task_id)
        spec = agent_spec(self.agent_id)
        query = context.get_user_input()
        mode = _sim_mode()

        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[user_message],
            )
        )

        updater = TaskUpdater(event_queue, task_id, context_id)
        working = updater.new_agent_message(
            parts=[new_text_part(f"Deterministisch rekenblok `{self.agent_id}` ({mode})…")]
        )
        await updater.start_work(message=working)

        try:
            payload, summary = await _build_payload(query, spec, task_id, mode)
        except Exception as exc:
            self._running.discard(task_id)
            fail = updater.new_agent_message(parts=[new_text_part(str(exc))])
            await updater.failed(message=fail)
            return

        if task_id not in self._running:
            return

        await updater.add_artifact(
            parts=[new_text_part(summary)],
            name="summary",
            last_chunk=False,
        )
        await updater.add_artifact(
            parts=[new_data_part(payload, media_type="application/json")],
            name="nldt-execution",
            last_chunk=True,
        )
        await updater.complete(message=updater.new_agent_message(parts=[new_text_part(summary)]))
        self._running.discard(task_id)


async def _build_payload(
    query: str, spec: dict[str, Any], task_id: str, mode: str
) -> tuple[dict[str, Any], str]:
    recipe_id = _pick_recipe(query, spec)

    if mode in ("live", "nldt"):
        payload = await _nldt_orchestrator(query, spec, task_id)
        summary = payload.get("explanation") or json.dumps(payload.get("upstream", {}))[:500]
        return payload, summary

    if mode == "deep":
        raise RuntimeError(
            "A2A_SIM_MODE=deep on PoC servers is disabled — LLM belongs in orchestrator/ "
            "(see architectuur-llm-gedreven-deepagents-met-deterministische-rekentools.md §10)."
        )

    await asyncio.sleep(0.25)
    payload = _simulated_payload(query, spec, task_id)
    summary = payload.get("explanation") or f"Simulated `{recipe_id}`."
    return payload, summary


def _sim_mode() -> str:
    return os.environ.get("A2A_SIM_MODE", "simulate").strip().lower()


def _fixture_path(agent_id: str) -> Path:
    path = FIXTURES / f"{agent_id}-completed.json"
    return path if path.is_file() else FIXTURES / "_default-completed.json"


def _pick_recipe(query: str, spec: dict[str, Any]) -> str:
    ql = query.lower()
    for recipe_id in spec["recipes"]:
        if recipe_id.replace("-", " ") in ql or recipe_id in ql:
            return recipe_id
    return spec["defaultRecipeId"]


def _simulated_payload(query: str, spec: dict[str, Any], task_id: str) -> dict[str, Any]:
    recipe_id = _pick_recipe(query, spec)
    fixture = json.loads(_fixture_path(spec["id"]).read_text(encoding="utf-8"))
    result = dict(fixture.get("result", {}))
    result["recipeId"] = recipe_id
    result["agentPocId"] = spec["id"]
    result["messageEcho"] = query[:500]
    result["mode"] = "simulate"
    result["architectureLayer"] = "deterministic-a2a"
    result["provenance"] = {
        "computation": f"fixture:{_fixture_path(spec['id']).name}",
        "recipeId": recipe_id,
        "enginePath": spec.get("enginePath"),
        "executedAt": datetime.now(timezone.utc).isoformat(),
        "taskId": task_id,
    }
    return result


async def _nldt_orchestrator(query: str, spec: dict[str, Any], task_id: str) -> dict[str, Any]:
    import httpx

    upstream = os.environ.get("NLDT_A2A_URL", "http://127.0.0.1:8085").rstrip("/")
    token = (os.environ.get("NLDT_STATIC_TOKENS") or "sim-toolbox-token").split(",")[0].strip()
    recipe_id = _pick_recipe(query, spec)
    auto_hitl = os.environ.get("NLDT_A2A_AUTO_HITL", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    legacy_body = {
        "skillId": "execute-recipe",
        "message": query,
        "recipeId": recipe_id,
        "inputs": {},
        "autoApproveHitl": auto_hitl,
    }
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{upstream}/tasks",
                json=legacy_body,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        return {
            "mode": "nldt",
            "error": f"nLDT unreachable at {upstream}/tasks: {exc}. Start ./scripts/start_nldt_stack.sh",
            "taskId": task_id,
        }
    if resp.status_code >= 400:
        return {"mode": "nldt", "error": resp.text, "taskId": task_id}
    data = resp.json()
    return {
        "mode": "nldt",
        "architectureLayer": "deterministic-a2a",
        "nldtLegacyA2A": True,
        "recipeId": recipe_id,
        "agentPocId": spec["id"],
        "provenance": {
            "computation": "nldt/services/a2a",
            "recipeId": recipe_id,
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "taskId": task_id,
        },
        "upstream": data,
    }
