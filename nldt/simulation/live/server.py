"""Live fetch-keten server (spec 2026-11-15).

Mount de bestaande MCP-servers, serves de WGS84-cache-twins als lagen en
(Transient in deze task) de startpagina. Start:

    cd nldt && .venv/bin/python simulation/live/server.py
    open http://127.0.0.1:8095
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

LIVE_ROOT = Path(__file__).resolve().parent
NLDT_ROOT = LIVE_ROOT.parents[1]
for _p in (str(NLDT_ROOT), str(LIVE_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# poc-/dso-tools executeren in-process via de job-store (één proces voor de demo)
os.environ.setdefault("NLDT_OFFLINE", "1")

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

from services.mcp_servers.catalog_server import mcp as catalog_mcp  # noqa: E402
from services.mcp_servers.data_server import mcp as data_mcp  # noqa: E402
from services.mcp_servers.dso_server import mcp as dso_mcp  # noqa: E402
from services.mcp_servers.http_transport import build_mcp_http_app  # noqa: E402
from services.mcp_servers.poc_server import mcp as poc_mcp  # noqa: E402

import json

from fastapi.responses import StreamingResponse  # noqa: E402

from agent import ScriptedAgent, SessionStore  # noqa: E402
from mcp_client import McpLoopbackClient  # noqa: E402

import chains  # noqa: E402

POC_CACHE = NLDT_ROOT.parent / "poc" / "data" / "cache"
MOUNTS = [
    ("/mcp/data", data_mcp),
    ("/mcp/dso", dso_mcp),
    ("/mcp/catalog", catalog_mcp),
    ("/mcp/poc", poc_mcp),
]


@asynccontextmanager
async def _lifespan(_app):
    # Gemounte ASGI-apps krijgen geen lifespan-events: de parent start de
    # session-managers (zelfde patroon als http_transport.run_mcp_http).
    managers = [srv.session_manager.run() for _, srv in MOUNTS]
    for mgr in managers:
        await mgr.__aenter__()
    try:
        yield
    finally:
        # LIFO: contextmanagers moeten in omgekeerde volgorde sluiten (de
        # task-group-scope van de laatste manager is nu de actieve scope).
        for mgr in reversed(managers):
            await mgr.__aexit__(None, None, None)


def create_app(tool_client_factory=None):
    app = FastAPI(title="nldt-live-fetch-sim", version="1.0.0", lifespan=_lifespan)
    for prefix, srv in MOUNTS:
        app.mount(prefix, build_mcp_http_app(srv))

    store = SessionStore()

    def _default_tool_client_factory():
        base = os.environ.get("NLDT_LIVE_SIM_BASE") or (
            f"http://127.0.0.1:{os.environ.get('NLDT_LIVE_SIM_PORT', '8095')}"
        )
        return McpLoopbackClient(base)

    @app.get("/api/chains")
    def list_chains():
        return [
            {"id": c["id"], "label": c["label"], "stepCount": len(c["stappen"])}
            for c in chains.CHAINS.values()
        ]

    @app.post("/api/session")
    async def start_session(chain: str = "utrecht"):
        if chain not in chains.CHAINS:
            raise HTTPException(status_code=400, detail=f"onbekende chain: {chain}")
        factory = tool_client_factory or _default_tool_client_factory

        def agent_factory():
            gekozen = factory()
            # compat: een geïnjecteerde factory mag een ScriptedAgent (oud
            # test-contract) of een client (productie-contract) teruggeven
            client = gekozen.client if isinstance(gekozen, ScriptedAgent) else gekozen
            return ScriptedAgent(client, stappen=chains.CHAINS[chain]["stappen"])

        try:
            sid = store.start(agent_factory)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"sessionId": sid, "chain": chain}

    @app.get("/api/session/{sid}/events")
    async def events(sid: str):
        async def gen():
            try:
                async for ev, data in store.stream(sid):
                    yield f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            except KeyError:
                yield "event: error\ndata: " + json.dumps(
                    {"stap": None, "label": "sessie", "melding": "onbekende sessie"},
                    ensure_ascii=False,
                ) + "\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/layers/{source_id}")
    def layer(source_id: str):
        pad = POC_CACHE / f"{source_id}.4326.geojson"
        if not pad.is_file():
            raise HTTPException(status_code=404, detail=f"geen 4326-twin voor {source_id}")
        return FileResponse(pad, media_type="application/geo+json")

    @app.get("/")
    def index():
        return FileResponse(LIVE_ROOT / "index.html")

    return app


def main() -> None:
    import uvicorn

    port = int(os.environ.get("NLDT_LIVE_SIM_PORT", "8095"))
    host = os.environ.get("NLDT_LIVE_SIM_HOST", "127.0.0.1")
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
