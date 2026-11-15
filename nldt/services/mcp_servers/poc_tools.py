"""PoC MCP tool definitions (shared by poc_server and tests)."""

from __future__ import annotations

from typing import Any

POC_TOOLS: dict[str, dict[str, Any]] = {
    "run_opportunity_map": {
        "process_id": "opportunity-map-run",
        "description": "Utrecht opportunity-map (Plane A)",
    },
    "propose_scenarios": {
        "process_id": "scenario-author-propose",
        "description": "Scenario author proposals S7 (Utrecht Plane B)",
    },
    "run_scenario_sweep": {
        "process_id": "scenario-sweep",
        "description": "Utrecht scenario sweep (Plane B)",
    },
    "build_world_scene": {
        "process_id": "world-scene-build",
        "description": "Build world-scene-specs.json for scenario-copilot (Renderer contract)",
    },
    "ask_scan": {
        "process_id": "breda-scan-query",
        "description": "Breda scan Q&A S4 (cite-or-abstain)",
    },
    "run_value_scan": {
        "process_id": "breda-scan-run",
        "description": "Breda five-value scan run",
    },
    "run_crosstrack": {
        "process_id": "crosstrack-overlay",
        "description": "Utrecht crosstrack overlay (Plane C)",
    },
    "run_peil_conflict": {
        "process_id": "rijnland-peil-conflict",
        "description": "Rijnland peil conflict analysis",
    },
    "run_peil_conflict_live": {
        "process_id": "rijnland-peil-conflict",
        "description": "Rijnland peil conflict using CDC lake snapshot path (live recipe)",
    },
    "run_peil_whatif": {
        "process_id": "rijnland-peil-whatif",
        "description": "Rijnland peilen what-if via CDC lake + multi-scenario Leaflet map (demo pack map-only)",
    },
    "run_bp2op_transform": {
        "process_id": "bp2op-transform",
        "description": "Eindhoven bp2op transform (bestemmingsplan → omgevingsplan)",
    },
    "run_minigim_gebiedscheck": {
        "process_id": "minigim-gebiedscheck-run",
        "description": "MiniGIM gebiedscheck: 74-item Lijst + ILS draft (PoC-5, keyless open data)",
    },
    "fetch_geo_layer": {
        "process_id": "fetch-geo-layer",
        "description": "Haal één PoC-geolaag op (ArcGIS/agrest, cache-first); compacte samenvatting",
    },
    "run_artifact": {
        "process_id": "run-artifact",
        "description": "Lees één outputbestand uit een pipeline-run-dir (inline, max 5 MB)",
    },
    "gent_life_event_run": {
        "process_id": "gent-life-event-run",
        "description": "Gent levensgebeurtenis-replay (fase 1+2+3): nieuwste run of echte CLI",
    },
}
