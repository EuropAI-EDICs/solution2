"""Gedeelde FakeMcpClient voor de live-sim tests (sibling-import via pytest sys.path).

Tool-resultaten als JSON-strings, vormgetrouw aan de echte servers.
"""

from __future__ import annotations

import json


class FakeMcpClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on  # (server, tool) die RuntimeError werpt

    async def call_tool(self, server: str, tool: str, args: dict) -> str:
        self.calls.append((server, tool, args))
        if self.fail_on and (server, tool) == self.fail_on:
            raise RuntimeError("broker onbereikbaar")
        if tool == "run_artifact":
            return json.dumps(
                {
                    "tool": "run_artifact",
                    "processId": "run-artifact",
                    "status": "successful",
                    "outputs": {
                        "artifact": {
                            "name": args.get("artifact"),
                            "path": f"{args.get('run_dir')}/{args.get('artifact')}",
                            "kind": "geojson" if str(args.get("artifact", "")).endswith(".geojson") else "json",
                            "bytes": 42,
                            "content": {
                                "type": "FeatureCollection",
                                "features": [
                                    {
                                        "type": "Feature",
                                        "id": "fakelayer-1",
                                        "properties": {},
                                        "geometry": {"type": "Point", "coordinates": [5.12, 52.09]},
                                    }
                                ],
                            },
                        }
                    },
                }
            )
        if tool in {
            "run_opportunity_map",
            "run_bp2op_transform",
            "run_value_scan",
            "gent_life_event_run",
            "veenendaal_gebiedscheck_run",
        }:
            return json.dumps(
                {
                    "tool": tool,
                    "processId": tool,
                    "status": "successful",
                    "outputs": {
                        "summary": {
                            "mode": args.get("mode", "execute"),
                            "runDir": f"/tmp/fake-run/{tool}",
                            "runId": "fake-run",
                            "verdict": "ok",
                        }
                    },
                }
            )
        if tool == "fetch_geo_layer":
            return json.dumps(
                {
                    "tool": "fetch_geo_layer",
                    "processId": "fetch-geo-layer",
                    "status": "successful",
                    "outputs": {
                        "summary": {
                            "sourceId": args["source_id"],
                            "title": "laag",
                            "featureCount": 44,
                        }
                    },
                }
            )
        if tool == "list_entities":
            return json.dumps(
                [
                    {
                        "id": "urn:ngsi-ld:AirQualityObserved:mock-001",
                        "type": "AirQualityObserved",
                        "mock": True,
                    }
                ]
            )
        if tool == "entities_to_geojson":
            return json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": "urn:ngsi-ld:AirQualityObserved:mock-001",
                            "properties": {
                                "type": "AirQualityObserved",
                                "source": "ngsi-ld",
                                "mock": True,
                            },
                            "geometry": {"type": "Point", "coordinates": [5.12, 52.09]},
                        }
                    ],
                }
            )
        return json.dumps(
            {"capabilities": ["opportunity-map-run"], "instrumenten": ["utrecht-domplein"]}
        )
