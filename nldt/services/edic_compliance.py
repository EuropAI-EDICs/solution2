"""Helpers for IMPACTS-EDIC MIM / Digital Rulebook declarations."""

from __future__ import annotations

from typing import Any

from services.common.schema import load_recipe

HIGH_RISK_RECIPES = (
    "utrecht-opportunity-map",
    "utrecht-scenario-author",
    "utrecht-scenario-sweep",
    "multi-track-crosstrack",
    "eindhoven-bp2op",
    "rijnland-peil-whatif",
    "rijnland-peil-conflict-live",
    "donl-harvest-publish",
    "lake-publish-offer",
    "source-monitor-run",
)


def declaration_for_recipe(recipe_id: str, *, declared_at: str = "2026-09-20") -> dict[str, Any]:
    recipe = load_recipe(recipe_id)
    hitl = recipe.get("riskLevel") == "high"
    spatial = recipe_id not in {
        "donl-harvest-publish",
        "lake-publish-offer",
        "source-monitor-run",
    }
    return {
        "id": f"DECL-{recipe_id}",
        "assetId": f"recipe:{recipe_id}",
        "assetKind": "recipe",
        "version": recipe.get("version", "1.0.0"),
        "declaredAt": declared_at,
        "doctrine": "LLMs propose · engines dispose · humans decide",
        "mims": [
            {
                "id": "MIM2",
                "title": "Data models",
                "status": "aligned",
                "evidence": "JSON Schema contracts under nldt/schemas; recipe inputs/outputs typed",
            },
            {
                "id": "MIM5",
                "title": "Fair AI",
                "status": "aligned",
                "evidence": "Critic V0–V4, cite-or-abstain, reject ledgers; LLMs never write zones",
            },
            {
                "id": "MIM7",
                "title": "Places",
                "status": "aligned" if spatial else "not_applicable",
                "evidence": (
                    "OGC Features/Processes and GeoJSON CRS checks (V1)"
                    if spatial
                    else "No geometry; Data Space / continuity asset"
                ),
            },
        ],
        "digitalRulebook": {
            "interoperability": "External interface is OGC API Records/Processes + Recipe, not vendor APIs.",
            "transparency": "Every run emits ValidationReport + PROV; marketplace payload carries both.",
            "contestability": "HITL on riskLevel high / needs_human; NormCard quote+article where legal.",
        },
        "sovereignty": {
            "tier": "T3" if spatial else "T2",
            "compute": "local-engine",
            "note": "Deterministic engines run locally; optional NLAIF only for S7/S8 LLM seams.",
        },
        "hitl": {
            "required": hitl,
            "trigger": "recipe.riskLevel == high or ValidationReport.verdict == needs_human",
        },
        "status": "proposed",
    }
