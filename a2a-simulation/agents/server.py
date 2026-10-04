from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

from agents.auth import ToolboxBearerMiddleware
from agents.card import build_agent_card
from agents.poc_executor import PocDeepAgentExecutor
from agents.registry import agent_spec

logger = logging.getLogger(__name__)


def create_app(agent_id: str) -> FastAPI:
    agent_card = build_agent_card(agent_id)
    task_store = InMemoryTaskStore()
    handler = DefaultRequestHandler(
        agent_executor=PocDeepAgentExecutor(agent_id),
        task_store=task_store,
        agent_card=agent_card,
    )
    app = FastAPI(title=f"A2A PoC — {agent_id}", version="1.0.0")
    app.add_middleware(ToolboxBearerMiddleware)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card=agent_card),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler=handler,
            rpc_url="/a2a/jsonrpc",
            enable_v0_3_compat=True,
        ),
        rest_routes=create_rest_routes(
            request_handler=handler,
            path_prefix="/a2a/rest",
            enable_v0_3_compat=True,
        ),
    )
    return app


async def serve(agent_id: str, host: str, port: int) -> None:
    app = create_app(agent_id)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(
        "A2A 1.x PoC agent %s on http://%s:%s — card at /.well-known/agent-card.json",
        agent_id,
        host,
        port,
    )
    await server.serve()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    agent_id = os.environ["A2A_POC_AGENT_ID"]
    spec = agent_spec(agent_id)
    host = os.environ.get("A2A_SIM_HOST", "127.0.0.1")
    port = int(os.environ.get("A2A_POC_PORT", str(spec["port"])))
    asyncio.run(serve(agent_id, host, port))


if __name__ == "__main__":
    main()
