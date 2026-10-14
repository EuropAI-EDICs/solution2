"""Genereer AOI-use-cases per jurisdictie (bbox-deel). Run: python3 use-cases/make_aoi.py

objectType en ambitions worden per track overgenomen uit de bestaande
poc/use-cases/<track>.json (dus altijd schema-conform); alle AOI's worden in
RD (EPSG:28992) geschreven, het werkkader van de zone-engine. Naast
objectType/ambitions worden ook de overige schema-verplichte velden
(policyStage, effortBudget, requestedAt, requestedBy, parameters) 1-op-1
overgenomen — alleen ``id`` (deterministisch per track+jurisdictie) en
``areaOfInterest`` (jurisdictie-ring) worden hier aangemaakt.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pyproj import Transformer  # noqa: E402

from bbox import NSPD_BBOX_WGS84  # noqa: E402

HIER = Path(__file__).resolve().parent
POC_USECASES = Path(__file__).resolve().parents[2] / "poc" / "use-cases"
# jurisdictie-splitsing: NL-kant west van de grens, BE-kant oostelijk (ruwe lengte-snede
# op 3.73°E — haven Gent/Zelzate ligt oostelijk, Terneuzen/Vlissingen westelijk)
SPLIT_LON = 3.73

TRACKS = ("wind", "zon", "energietoets", "bos", "water", "bodem", "mobiliteit",
          "landschap", "landbouw", "wonen", "werken", "recreatie", "biomassa")


def _ring(bbox):
    x0, y0, x1, y1 = bbox
    t = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    return [[list(t.transform(x, y)) for x, y in
             ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]]


def main() -> None:
    x0, y0, x1, y1 = NSPD_BBOX_WGS84
    delen = {
        "nl": (x0, y0, SPLIT_LON, y1),
        "be": (SPLIT_LON, y0, x1, y1),
    }
    for land, bbox in delen.items():
        for track in TRACKS:
            bron = json.loads((POC_USECASES / f"{track}.json").read_text(encoding="utf-8"))
            parameters = dict(bron.get("parameters") or {})
            # AOI-provenance is hier niet de Utrecht-provinciegrens-dienst maar de
            # deterministische NSPD-werkbbox-deel; overschrijf de 1-op-1
            # overgenomen aoi-*-velden (review-fix taak 9).
            for k in ("aoiSourceId", "aoiServiceUrl", "aoiLayerId",
                      "aoiLastChecked", "aoiNote"):
                parameters.pop(k, None)
            parameters["aoiSourceId"] = "poc-nspd-bbox"
            parameters["aoiNote"] = (
                "NSPD-werkbbox-deel (jurisdictie), bbox.py NSPD_BBOX_WGS84, "
                "deterministisch gegenereerd"
            )
            req = {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"poc-nspd-{track}-{land}")),
                "objectType": bron["objectType"],
                "ambitions": bron["ambitions"],
                "areaOfInterest": {"geometry": {"type": "Polygon", "coordinates": _ring(bbox)},
                                   "crs": "EPSG:28992"},
                "policyStage": bron["policyStage"],
                "effortBudget": bron["effortBudget"],
                "requestedAt": bron["requestedAt"],
                "requestedBy": bron.get("requestedBy", "poc-nspd"),
                "parameters": parameters,
            }
            (HIER / f"{track}-{land}.json").write_text(
                json.dumps(req, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{track}-{land}.json geschreven (objectType={bron['objectType']})")


if __name__ == "__main__":
    main()
