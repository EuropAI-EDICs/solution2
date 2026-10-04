from __future__ import annotations

import os

from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    HTTPAuthSecurityScheme,
    SecurityRequirement,
    SecurityScheme,
    StringList,
)

from agents.auth import SCHEME_ID
from agents.registry import agent_spec

PROTOCOL_VERSION = "1.0.0"


def _host_port(spec: dict) -> tuple[str, int]:
    host = os.environ.get("A2A_SIM_HOST", "127.0.0.1")
    port = int(os.environ.get("A2A_POC_PORT", spec["port"]))
    return host, port


def build_agent_card(agent_id: str) -> AgentCard:
    spec = agent_spec(agent_id)
    host, port = _host_port(spec)
    base = f"http://{host}:{port}"
    jsonrpc = f"{base}/a2a/jsonrpc"
    rest = f"{base}/a2a/rest"

    skills: list[AgentSkill] = []
    for recipe_id in spec["recipes"]:
        skills.append(
            AgentSkill(
                id=recipe_id,
                name=recipe_id.replace("-", " ").title(),
                description=f"nLDT governed recipe `{recipe_id}` (PoC {agent_id})",
                tags=["nldt", "poc", agent_id, "eu-ldt-toolbox"],
                examples=[f"Run recipe {recipe_id} for a demo AOI"],
            )
        )

    card = AgentCard(
        name=spec["name"],
        description=spec.get("question", f"PoC agent {agent_id}"),
        version="1.0.0",
        documentation_url="https://a2a-protocol.org/latest/",
        provider=AgentProvider(
            organization=spec.get("organization", agent_id),
            url="https://ldttoolbox.app",
        ),
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text", "application/json"],
        skills=skills,
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version=PROTOCOL_VERSION,
                url=jsonrpc,
            ),
            AgentInterface(
                protocol_binding="HTTP+JSON",
                protocol_version=PROTOCOL_VERSION,
                url=rest,
            ),
        ],
    )
    card.security_schemes[SCHEME_ID].CopyFrom(
        SecurityScheme(
            http_auth_security_scheme=HTTPAuthSecurityScheme(
                scheme="bearer",
                bearer_format="JWT",
                description=(
                    "EU LDT Identity Management (Keycloak realm LDT). "
                    "Simulation: NLDT_STATIC_TOKENS=sim-toolbox-token with A2A_SIM_AUTH=static."
                ),
            )
        )
    )
    requirement = SecurityRequirement()
    requirement.schemes[SCHEME_ID].CopyFrom(StringList())
    card.security_requirements.append(requirement)
    return card
