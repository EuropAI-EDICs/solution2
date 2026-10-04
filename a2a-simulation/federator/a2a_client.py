from __future__ import annotations

import os
import uuid
from typing import Any

import httpx
from google.protobuf.json_format import MessageToDict

from a2a.client import ClientConfig, create_client
from a2a.client.card_resolver import A2ACardResolver
from a2a.helpers.proto_helpers import get_message_text
from a2a.types.a2a_pb2 import Message, Part, Role, SendMessageRequest

from agents.auth import auth_mode, static_tokens
from agents.registry import agent_spec


def _httpx_auth_headers() -> dict[str, str]:
    if auth_mode() != "static":
        return {}
    token = static_tokens()[0] if static_tokens() else ""
    return {"Authorization": f"Bearer {token}"} if token else {}


def agent_base_url(port: int) -> str:
    host = os.environ.get("A2A_SIM_HOST", "127.0.0.1")
    return f"http://{host}:{port}"


def fetch_agent_card_proto(agent_id: str):
    spec = agent_spec(agent_id)
    url = agent_base_url(int(spec["port"]))

    async def _fetch():
        headers = _httpx_auth_headers()
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as httpx_client:
            resolver = A2ACardResolver(httpx_client, url)
            return await resolver.get_agent_card()

    import asyncio

    return asyncio.run(_fetch())


async def send_message_async(agent_id: str, text: str) -> dict[str, Any]:
    spec = agent_spec(agent_id)
    url = agent_base_url(int(spec["port"]))
    headers = _httpx_auth_headers()
    async with httpx.AsyncClient(timeout=120.0, headers=headers) as httpx_client:
        config = ClientConfig(
            streaming=True,
            supported_protocol_bindings=["JSONRPC", "HTTP+JSON"],
            httpx_client=httpx_client,
        )
        resolver = A2ACardResolver(httpx_client, url)
        card = await resolver.get_agent_card()
        client = await create_client(card, client_config=config)

        message = Message(
            role=Role.ROLE_USER,
            message_id=str(uuid.uuid4()),
            parts=[Part(text=text)],
        )
        request = SendMessageRequest(message=message)
        stream = client.send_message(request)

        events: list[Any] = []
        final_text: list[str] = []
        async for event in stream:
            events.append(event)
            art = getattr(event, "artifact", None)
            if art is not None and art.parts:
                for part in art.parts:
                    if part.text:
                        final_text.append(part.text)
            au = getattr(event, "artifact_update", None)
            if au is not None and au.artifact.parts:
                for part in au.artifact.parts:
                    if part.text:
                        final_text.append(part.text)
            su = getattr(event, "status_update", None)
            if su is not None and su.status.message.parts:
                final_text.append(get_message_text(su.status.message))

        return {
            "agentId": agent_id,
            "url": url,
            "responseText": "\n".join(dict.fromkeys(final_text)).strip() or "(no text in stream)",
            "eventCount": len(events),
            "events": [MessageToDict(e, preserving_proto_field_name=True) for e in events[:20]],
        }


def send_message(agent_id: str, text: str) -> dict[str, Any]:
    import asyncio

    return asyncio.run(send_message_async(agent_id, text))
