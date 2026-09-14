#!/usr/bin/env python3
"""Refresh lakehouse: optional CDC capture/apply → inventory → Iceberg/Parquet → dbt marts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-dbt", action="store_true")
    ap.add_argument("--force-iceberg", action="store_true", default=True)
    ap.add_argument("--cdc", action="store_true", help="Run CDC capture (outbox) + apply before inventory")
    ap.add_argument("--cdc-fixture", type=Path, help="Offline CDC: peilen.json → capture --fixture")
    ap.add_argument("--skip-cdc-capture", action="store_true")
    args = ap.parse_args()

    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)}

    if args.cdc or args.cdc_fixture:
        if not args.skip_cdc_capture:
            if args.cdc_fixture:
                cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "cdc_capture_peilen.py"),
                    "--fixture",
                    str(args.cdc_fixture),
                ]
            else:
                cmd = [sys.executable, str(ROOT / "scripts" / "cdc_capture_peilen.py")]
            print("+", " ".join(cmd), flush=True)
            subprocess.check_call(cmd, cwd=str(ROOT), env=env)
        cmd = [sys.executable, str(ROOT / "scripts" / "cdc_apply_peilen.py")]
        print("+", " ".join(cmd), flush=True)
        subprocess.check_call(cmd, cwd=str(ROOT), env=env)

    steps = [
        [sys.executable, str(ROOT / "scripts" / "build_lake_inventory.py")],
        [sys.executable, str(ROOT / "scripts" / "lake_iceberg_bootstrap.py"), "--force"],
    ]
    for cmd in steps:
        print("+", " ".join(cmd), flush=True)
        subprocess.check_call(cmd, cwd=str(ROOT), env=env)

    if not args.skip_dbt:
        dbt = ROOT / ".venv" / "bin" / "dbt"
        if not dbt.is_file():
            dbt = Path(sys.executable).parent / "dbt"
        peilen_mirror = ROOT / "data/lake/nldt-poc-lake/iceberg/mirrors/rijnland_peilen_latest.parquet"
        cmd = [str(dbt), "run", "--profiles-dir", "."]
        if not peilen_mirror.is_file():
            cmd += ["--exclude", "stg_rijnland_peilen_cdc", "mart_peil_latest"]
        print("+", " ".join(cmd), flush=True)
        subprocess.check_call(cmd, cwd=str(ROOT / "dbt_lake"), env=env)

    boot_path = ROOT / "data/lake/nldt-poc-lake/iceberg/bootstrap.json"
    boot = json.loads(boot_path.read_text()) if boot_path.is_file() else {}
    print(json.dumps({"ok": True, "iceberg": boot}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
