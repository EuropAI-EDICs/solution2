"""World Labs Marble (Renderer) spike — explore URLs only, gated by HITL.

Does not call proprietary APIs without credentials; builds operator-review URLs
from structured prompts. See docs/POC_WORLD_MODEL_UTRECHT.md.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Optional

DEFAULT_MARBLE_BASE = "https://marble.worldlabs.ai"


def build_explore_url(prompt: str, *, base_url: Optional[str] = None) -> str:
    base = (base_url or os.environ.get("MARBLE_API_BASE") or DEFAULT_MARBLE_BASE).rstrip(
        "/"
    )
    clipped = prompt.strip()[:2000]
    return f"{base}/explore?prompt={urllib.parse.quote(clipped)}"


def marble_explore_allowed(*, basis_type: str, hitl_approved: bool) -> bool:
    """Generative Renderer only for hypothetical scenarios after HITL."""
    if basis_type != "hypothetical":
        return False
    if hitl_approved:
        return True
    return os.environ.get("MARBLE_HITL_APPROVED") == "1"
