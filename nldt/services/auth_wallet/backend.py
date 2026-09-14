"""Pluggable presentation verifiers for the wallet token edge.

W1 ships the MockBackend (ARF-shaped envelopes, local trust anchor — never a
production configuration). W2 adds a real OpenID4VP backend (Keycloak toolbox
IM or pyeudiw) behind the same interface; ARF requirement IDs are pinned
there, not simulated here.
"""

from __future__ import annotations

from typing import Any

# Administration-defined agent assurance scale (never an eIDAS human LoA).
MOCK_PRESENTATIONS: dict[str, dict[str, Any]] = {
    "mock-user-1": {
        "subject_type": "human",
        "sub": "mock-user-1",
        "loa": "substantial",
        "org": "Provincie Test",
        "roles": ["policy-officer"],
    },
    "beleidskompas-svc": {
        "subject_type": "agent",
        "agentId": "beleidskompas-svc",
        "deployingOrg": "Provincie Test",
        "capabilities": ["beleidskompas-omgevingsanalyse", "breda-scan-query"],
        "assurance": "attested",
    },
}


class VerifierBackend:
    async def verify(self, presentation: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockBackend(VerifierBackend):
    """Deterministic mock: presentation_id selects a known subject."""

    async def verify(self, presentation: dict[str, Any]) -> dict[str, Any]:
        pid = presentation.get("presentation_id")
        if pid not in MOCK_PRESENTATIONS:
            raise ValueError(f"unknown presentation: {pid}")
        return dict(MOCK_PRESENTATIONS[pid])
