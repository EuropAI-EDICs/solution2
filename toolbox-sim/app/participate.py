# toolbox-sim/app/participate.py
"""EU LDT Participate-sim: Decidim-vorm (proposals/meetings) + Jitsi-vorm (rooms)."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.guards import add_provenance, require_bearer


class ProposalIn(BaseModel):
    title: str
    area: str = "utrecht"


class RoomIn(BaseModel):
    title: str


def create_app(seed: dict) -> FastAPI:
    app = FastAPI(title="toolbox-sim participate", docs_url=None, openapi_url=None)
    add_provenance(app, "participate")
    proposals: dict[str, dict] = {p["id"]: dict(p) for p in seed.get("proposals", [])}
    meetings = [dict(m) for m in seed.get("meetings", [])]
    seq = {"n": 0}

    @app.get("/health")
    def health() -> dict:
        return {"status": "UP"}

    @app.get("/api/proposals")
    def list_proposals(_: dict = Depends(require_bearer)):
        return {"data": [dict(p) for p in proposals.values()]}

    @app.post("/api/proposals", status_code=201)
    def create_proposal(payload: ProposalIn, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        prop = {"id": f"prop-{len(proposals) + seq['n']}", "title": payload.title,
                "area": payload.area, "state": "open",
                "provenance": "toolbox-sim/participate; seed=fixtures/participate-seed.json"}
        proposals[prop["id"]] = prop
        return prop

    @app.get("/api/meetings")
    def list_meetings(_: dict = Depends(require_bearer)):
        return {"data": meetings}

    @app.post("/rooms")
    def create_room(payload: RoomIn, _: dict = Depends(require_bearer)):
        seq["n"] += 1
        slug = payload.title.lower().replace(" ", "-")[:24] or f"room-{seq['n']}"
        return {"roomUrl": f"http://localhost:9199/rooms/{slug}-{seq['n']}", "title": payload.title}

    return app
