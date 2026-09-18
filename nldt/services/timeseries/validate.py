"""JSON Schema validation for time-series observations."""

from __future__ import annotations

from typing import Any

from services.common.schema import validate_instance

OBS_SCHEMA = "timeseries-observation.schema.json"
SERIES_SCHEMA = "timeseries-series.schema.json"


def validate_observation(obs: dict[str, Any]) -> None:
    validate_instance(obs, OBS_SCHEMA)


def validate_observations(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        validate_observation(row)


def validate_series_meta(meta: dict[str, Any]) -> None:
    validate_instance(meta, SERIES_SCHEMA)
