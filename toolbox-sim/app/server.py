# toolbox-sim/app/server.py
"""Start alle sim-diensten: 9191–9195 (+9196 met --eubd, +9197–9204 met --full)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import uvicorn

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REPO = Path(__file__).resolve().parents[2]
PORTS = {
    "identity": 9191, "broker": 9192, "pv": 9193, "ucs": 9194, "marketplace": 9195, "eubd": 9196,
    "dataspace": 9197, "algorithms": 9198, "participate": 9199,
    "fl": 9200, "ain": 9201, "dm": 9202, "ie": 9203, "cip": 9204,
}


def _load_batches(exclude_eubd: bool = True) -> tuple[dict[str, list[dict]], dict[str, str]]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    entities: list[dict] = []
    names: list[str] = []
    for name in sorted(manifest["batches"]):
        if exclude_eubd and name.startswith("eubd"):
            continue
        entities.extend(json.loads((FIXTURES / "ngsi-ld" / f"{name}.jsonld").read_text()))
        names.append(name)
    provenance = {"ldt": f"toolbox-sim/data-platform; fixtures={','.join(names)}"}
    return {"ldt": entities}, provenance


def _eubd_batch() -> list[dict]:
    path = FIXTURES / "ngsi-ld" / "eubd-buildings.jsonld"
    if not path.exists():
        raise SystemExit("--eubd gevraagd maar fixtures/ngsi-ld/eubd-buildings.jsonld ontbreekt; draai build_fixtures.py --eubd <DSN>")
    return json.loads(path.read_text())


def _read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def build_apps(full: bool, eubd: bool) -> dict[str, "FastAPI"]:
    from app.algorithms import create_app as algorithms_app
    from app.algorithms import load_ground
    from app.cip import create_app as cip_app
    from app.ai_notebook import create_app as ain_app
    from app.data_modeller import create_app as dm_app
    from app.data_platform import create_broker_app
    from app.dataspace_ready import create_app as dataspace_app
    from app.federated_learning import create_app as fl_app
    from app.identity import create_app as identity_app
    from app.integrated_environment import create_app as ie_app
    from app.marketplace import create_app as marketplace_app
    from app.participate import create_app as participate_app
    from app.play_visualise import create_app as pv_app
    from app.ucs import create_app as ucs_app

    entities_by_tenant, provenance = _load_batches()
    ucs_processes = json.loads((FIXTURES / "ucs-processes.json").read_text())
    temporal = _read_json(FIXTURES / "dp-temporal.jsonld")
    recipes = _read_json(FIXTURES / "recipes.json") or {}
    participate_seed = _read_json(FIXTURES / "participate-seed.json") or {"proposals": [], "meetings": []}
    ground = load_ground(FIXTURES)

    offers: list[dict] = []
    offers_dir = REPO / "nldt" / "data" / "dataspace" / "offers"
    if offers_dir.exists():
        for path in sorted(offers_dir.glob("*.json")):
            offers.append(json.loads(path.read_text()))

    lake_root = REPO / "nldt" / "data" / "lake" / "nldt-poc-lake"
    inventory_path = REPO / "nldt" / "data" / "lake-inventory.json"

    def _schemas() -> dict:
        out = {}
        for path in sorted((REPO / "nldt" / "schemas").glob("*.json")):
            try:
                out[path.stem] = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
        return out

    solutions_ie = [{"name": name, "port": PORTS[name], "status": "simulated"} for name in
                    ("identity", "broker", "pv", "ucs", "marketplace", "dataspace",
                     "algorithms", "participate", "fl", "ain", "dm", "cip")]

    apps: dict[str, "FastAPI"] = {
        "identity": identity_app(),
        "broker": create_broker_app(
            entities_by_tenant=entities_by_tenant,
            provenance_by_tenant=provenance,
            include_proxy=True,
            include_trino=True,
            temporal=temporal,
        ),
        "pv": pv_app(),
        "ucs": ucs_app(ucs_processes, recipes=recipes, ground=ground),
        "marketplace": marketplace_app(),
    }
    if eubd:
        apps["eubd"] = create_broker_app(
            entities_by_tenant={"eubd": _eubd_batch()},
            provenance_by_tenant={"eubd": "toolbox-sim/data-platform; fixture=eubd-buildings; source=exposure.entities"},
        )
    if full:
        apps["dataspace"] = dataspace_app(offers, lake_root=lake_root)
        apps["algorithms"] = algorithms_app(ground)
        apps["participate"] = participate_app(participate_seed)
        apps["fl"] = fl_app(ground.peilen)
        apps["ain"] = ain_app(lake_root=lake_root)
        apps["dm"] = dm_app(_schemas())
        apps["ie"] = ie_app(solutions_ie, inventory_path=inventory_path)
        apps["cip"] = cip_app()
    return apps


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", action="store_true", help="start ook de EUBD-feed op 9196")
    parser.add_argument("--full", action="store_true", help="start ook de catalogus-apps op 9197–9204")
    args = parser.parse_args(argv)

    apps = build_apps(full=args.full, eubd=args.eubd)
    servers = [
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORTS[name], log_level="warning"))
        for name, app in apps.items()
    ]
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
