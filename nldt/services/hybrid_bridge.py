from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from services.adapters import data_platform, play_visualise
from services.context3d.export_import import export_from_execution

NLDT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = NLDT_ROOT / "data" / "exports"


def post_execution_hooks(
    execution: dict[str, Any],
    *,
    run_id: str | None = None,
    register_pv: bool = True,
    export_3d: bool = True,
    lake_upload: bool | None = None,
) -> dict[str, Any]:
    """Fase 2 hybrid hooks after recipe execution (+ optional gold lake upload)."""
    result: dict[str, Any] = {"runId": run_id}

    if export_3d and "intersection" in execution.get("outputs", {}):
        try:
            ctx = export_from_execution(execution, run_id=run_id)
            result["web3dContext"] = ctx
        except Exception as exc:
            result["web3dContextError"] = str(exc)

    if register_pv and play_visualise.available():
        intersection = execution.get("outputs", {}).get("intersection")
        if intersection:
            try:
                reg = play_visualise.register_geojson_layer(
                    geojson=intersection,
                    name=f"nldt-{execution.get('recipeId', 'result')}",
                    export_store=EXPORT_DIR,
                )
                result["visualization"] = reg
            except Exception as exc:
                result["visualizationError"] = str(exc)

    do_lake = lake_upload if lake_upload is not None else (
        os.environ.get("NLDT_LAKE_POST_RUN", "").lower() in {"1", "true", "yes"}
    )
    if do_lake:
        try:
            from services.lake.publish import upload_execution_gold

            result["lake"] = upload_execution_gold(execution, run_id=run_id)
        except Exception as exc:
            result["lakeError"] = str(exc)

    return result


def fetch_ngsi_as_features(entity_type: str, scope: str | None = None) -> dict[str, Any]:
    entities = data_platform.list_entities(entity_type=entity_type, scope=scope)
    return data_platform.entities_to_geojson(entities)
