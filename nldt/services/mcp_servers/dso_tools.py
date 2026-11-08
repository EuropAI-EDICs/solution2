"""DSO-KB MCP tool-definitions (gedeeld door dso_server en tests)."""

from __future__ import annotations

from typing import Any

DSO_TOOLS: dict[str, dict[str, Any]] = {
    "dso_kb_overview": {
        "process_id": "dso-kb-overview",
        "description": "DSO-kennisbank: instrumenten × locaties, freshness (sha256), dekking",
    },
    "dso_kb_annotations": {
        "process_id": "dso-kb-annotations",
        "description": "DSO-annotaties per artikel (wId-gegroepeerd), filterbaar + detail",
    },
    "dso_kb_document_structure": {
        "process_id": "dso-kb-document-structure",
        "description": "Documentstructuur als vlakke componentreeks (wIdPrefix-filter)",
    },
    "dso_kb_tpod": {
        "process_id": "dso-kb-tpod",
        "description": "TPOD-index: wId-anchoring, geoFeiten, activiteiten, pons",
    },
    "dso_kb_toets": {
        "process_id": "dso-kb-toets",
        "description": "RegelRecht-punttoets: feit/afwezigheid/scenario/onthouding per artikel",
    },
    "dso_kb_overlap": {
        "process_id": "dso-kb-overlap",
        "description": "DSO↔RegelRecht-dekking + per-artikel statusrijen (filter/pagina)",
    },
    "dso_kb_gios": {
        "process_id": "dso-kb-gios",
        "description": "GIO-inventaris uit het officiële uitwisselpakket",
    },
    "dso_kb_point_in_gio": {
        "process_id": "dso-kb-point-in-gio",
        "description": "Deterministisch punt-in-polygoon (EPSG:28992) tegen officiële GIO's",
    },
    "dso_kb_refresh": {
        "process_id": "dso-kb-refresh",
        "description": "Live PRE-refresh + canonieke drift-uitslag (enige tool met side-effect; keys server-side)",
    },
}
