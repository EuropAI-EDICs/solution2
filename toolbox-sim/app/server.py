# toolbox-sim/app/server.py
"""Start alle sim-diensten: 9191–9195 (+9196 met --eubd)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import uvicorn

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PORTS = {"identity": 9191, "broker": 9192, "pv": 9193, "ucs": 9194, "marketplace": 9195, "eubd": 9196}


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


async def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", action="store_true", help="start ook de EUBD-feed op 9196")
    args = parser.parse_args(argv)

    from app.data_platform import create_broker_app
    from app.identity import create_app as identity_app
    from app.marketplace import create_app as marketplace_app
    from app.play_visualise import create_app as pv_app
    from app.ucs import create_app as ucs_app

    entities_by_tenant, provenance = _load_batches()
    ucs_processes = json.loads((FIXTURES / "ucs-processes.json").read_text())
    apps = {
        "identity": identity_app(),
        "broker": create_broker_app(
            entities_by_tenant=entities_by_tenant,
            provenance_by_tenant=provenance,
            include_proxy=True,
            include_trino=True,
        ),
        "pv": pv_app(),
        "ucs": ucs_app(ucs_processes),
        "marketplace": marketplace_app(),
    }
    if args.eubd:
        apps["eubd"] = create_broker_app(
            entities_by_tenant={"eubd": _eubd_batch()},
            provenance_by_tenant={"eubd": "toolbox-sim/data-platform; fixture=eubd-buildings; source=exposure.entities"},
        )
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
