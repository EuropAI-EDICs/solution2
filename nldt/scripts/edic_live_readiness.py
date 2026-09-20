"""CitiVERSE live-path readiness: consume Toolbox, do not rebuild it."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def _present(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def assess_live_path() -> dict[str, Any]:
    """Return connection status for the CitiVERSE reference recipe path.

    Engines stay local. UCS / Marketplace / P&V / IM are consumed.
    LLM seams are the only optional NLAIF compute route.
    """
    checks = {
        "ucs": {
            "live": _present("UCS_BASE_URL"),
            "env": "UCS_BASE_URL",
            "note": "UCS experiment endpoint; adapter falls back to local if unset",
        },
        "marketplace": {
            "live": _present("MARKETPLACE_AGENT_URL") and not _truthy("MARKETPLACE_MOCK", "true"),
            "env": "MARKETPLACE_AGENT_URL + MARKETPLACE_MOCK=false",
            "note": "Recipe publish with ValidationReport + PROV",
        },
        "play_visualise": {
            "live": _present("NLDT_PV_BASE_URL") and not _truthy("NLDT_PV_MOCK", "true"),
            "env": "NLDT_PV_BASE_URL + NLDT_PV_MOCK=false",
            "note": "Post-execution layer registration",
        },
        "identity": {
            "live": _present("KEYCLOAK_URL")
            and "localhost" not in os.environ.get("KEYCLOAK_URL", ""),
            "env": "KEYCLOAK_URL (Toolbox IM, not localhost)",
            "note": "A2A / Marketplace bearer",
        },
        "data_platform": {
            "live": (
                (_present("NLDT_DATA_PLATFORM_URL") or _present("NLDT_NGSI_LD_URL"))
                and not _truthy("NLDT_DATA_PLATFORM_MOCK", "true")
            ),
            "env": "NLDT_DATA_PLATFORM_URL or NLDT_NGSI_LD_URL + NLDT_DATA_PLATFORM_MOCK=false",
            "note": "Optional for spatial-overlay-analysis file:// inputs; required for NGSI sources",
            "optional": True,
        },
        "llm_compute": {
            "live": _present("NLDT_NLAIF_ROUTE") or _present("NLDT_LLM_BASE_URL"),
            "env": "NLDT_NLAIF_ROUTE or NLDT_LLM_BASE_URL",
            "note": "Only S7/S8 LLM seams; zone engines stay local/deterministic",
            "optional": True,
        },
    }
    required = [k for k, v in checks.items() if not v.get("optional")]
    live_required = sum(1 for k in required if checks[k]["live"])
    status = "live" if live_required == len(required) else (
        "hybrid" if live_required else "mock"
    )
    return {
        "referenceRecipe": "spatial-overlay-analysis",
        "status": status,
        "liveRequired": f"{live_required}/{len(required)}",
        "checks": checks,
        "doctrine": "Consume Toolbox IM/UCS/Marketplace/P&V; do not rebuild them.",
    }


def main() -> int:
    report = assess_live_path()
    print(json.dumps(report, indent=2))
    if report["status"] == "live":
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
