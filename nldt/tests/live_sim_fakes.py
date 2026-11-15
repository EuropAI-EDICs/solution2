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
