#!/usr/bin/env python3
"""Vergelijk of update de vastgepinde RegelRecht-schema-pin (NDD)."""
from __future__ import annotations
import argparse, hashlib, json, sys, urllib.request
from pathlib import Path

DIR = Path(__file__).resolve().parent / "schema"
PIN_PATH = DIR / "pin.json"
DEFAULT_VERSION = "v0.8.11"

def _url(version: str) -> str:
    return (
        "https://raw.githubusercontent.com/NederlandseDigitaleDienst/regelrecht/"
        f"main/schema/{version}/schema.json"
    )

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=DEFAULT_VERSION)
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--allow-drift", action="store_true")
    args = ap.parse_args(argv)
    url = _url(args.version)
    with urllib.request.urlopen(url, timeout=60) as resp:
        remote = resp.read()
    remote_sha = hashlib.sha256(remote).hexdigest()
    local_path = DIR / f"regelrecht-{args.version}.schema.json"
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8")) if PIN_PATH.exists() else {}
    if args.update:
        local_path.write_bytes(remote)
        pin = {
            "version": args.version,
            "sourceUrl": url,
            "sha256": remote_sha,
            "pinnedAt": __import__("datetime").date.today().isoformat(),
        }
        PIN_PATH.write_text(json.dumps(pin, indent=2) + "\n", encoding="utf-8")
        print(f"updated pin {args.version} sha256={remote_sha}")
        return 0
    local_sha = hashlib.sha256(local_path.read_bytes()).hexdigest()
    if local_sha != pin.get("sha256") or remote_sha != pin.get("sha256"):
        print(f"DRIFT local={local_sha} pin={pin.get('sha256')} remote={remote_sha}", file=sys.stderr)
        return 0 if args.allow_drift else 1
    print("ok", pin["version"], pin["sha256"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
