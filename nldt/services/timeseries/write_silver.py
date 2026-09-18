"""Write normalized observations to the lake silver zone (JSONL for FS-dev)."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from services.lake import get_lake_client
from services.timeseries.validate import validate_observations, validate_series_meta


def silver_observations_key(series_id: str, year: int) -> str:
    safe = series_id.replace("/", "-")
    return f"silver/timeseries/{safe}/year={year}/observations.jsonl"


def series_meta_key(series_id: str) -> str:
    safe = series_id.replace("/", "-")
    return f"silver/timeseries/{safe}/series.json"


def _year_of(observed_at: str) -> int:
    return int(str(observed_at)[:4])


def write_series_bundle(
    observations: list[dict[str, Any]],
    series_meta: dict[str, Any],
    *,
    lake: Any | None = None,
) -> dict[str, Any]:
    """Validate and write observations (JSONL by year) + series.json metadata."""
    if not observations:
        raise ValueError("no observations to write")
    validate_observations(observations)
    validate_series_meta(series_meta)

    client = lake or get_lake_client()
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for obs in observations:
        by_year[_year_of(obs["observedAt"])].append(obs)

    observation_uris: list[str] = []
    lake_keys: list[str] = []
    for year, rows in sorted(by_year.items()):
        key = silver_observations_key(str(series_meta["seriesId"]), year)
        payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"
        uri = client.put_bytes(key, payload.encode("utf-8"), content_type="application/x-ndjson")
        observation_uris.append(uri)
        lake_keys.append(key)

    meta_key = series_meta_key(str(series_meta["seriesId"]))
    series_meta = dict(series_meta)
    series_meta["lakeKey"] = meta_key
    series_meta["lakeUri"] = client.uri_for(meta_key)
    series_meta["observationLakeKeys"] = lake_keys
    meta_uri = client.put_bytes(
        meta_key,
        json.dumps(series_meta, indent=2, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )
    return {
        "seriesId": series_meta["seriesId"],
        "seriesLakeUri": meta_uri,
        "seriesLakeKey": meta_key,
        "observationUris": observation_uris,
        "observationCount": len(observations),
        "years": sorted(by_year.keys()),
    }
