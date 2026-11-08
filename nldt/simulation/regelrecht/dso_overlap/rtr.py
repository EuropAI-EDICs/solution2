#!/usr/bin/env python3
"""RTR-client (Registratie Toepasbare Regels): derde kennisbank-bron.

Bevraagt de DSO-API *Uitvoeren gegevens toepasbare regels* v2 (x-api-key,
zelfde key-portaal als Presenteren) per OIN en downloadt de complete
STTR-bestanden (DMN-xml). Identificatie van het bevoegd gezag loopt via de
gm-code in ``functioneleStructuurRef`` — de metadata kent geen namen
(docs/POC_STTR_IMTR_KANSEN.md, kans 3 en de correctie-notitie daar).

Gebruik:
  export DSO_API_KEY=…   # of .env in de repo-root (gitignored)
  nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.rtr \\
    --instruments eindhoven [--bestanden] [--force]

Cache (gitignored, dso_overlap/out): ``<instrument>.rtr.json`` (metadata +
provenance + per bestand sha256) en ``<instrument>.rtr.<id>.dmn``.
``--bestanden`` slaat bestaande .dmn's over tenzij ``--force``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

DIR = pathlib.Path(__file__).resolve().parent
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

import client  # noqa: E402  (DsoApiError + .env-lading)
from instruments import DEFAULT_OUT, INSTRUMENTS  # noqa: E402

DEFAULT_RTR_BASE = (
    "https://service.pre.omgevingswet.overheid.nl"
    "/publiek/toepasbare-regels/api/toepasbareregelsuitvoerengegevens/v2"
)
PAGE_SIZE = 500
CONTRACT = "rtr/v1"


def rtr_base() -> str:
    return (
        os.environ.get("RTR_API_BASE", "").strip() or DEFAULT_RTR_BASE
    ).rstrip("/")


def _open_json(url: str, api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise client.DsoApiError(
            e.code, e.read().decode("utf-8", errors="replace"), url
        ) from e


def fetch_toepasbare_regels(oin: str, *, api_key: str) -> list[dict[str, Any]]:
    """Alle toepasbareRegels-entries voor één OIN (server-side ?oin=-filter, paging)."""
    entries: list[dict[str, Any]] = []
    page = 1
    while True:
        d = _open_json(
            f"{rtr_base()}/toepasbareRegels?oin={oin}"
            f"&pageSize={PAGE_SIZE}&page={page}",
            api_key,
        )
        entries.extend(d.get("_embedded", {}).get("toepasbareRegels", []))
        total = (d.get("page") or {}).get("totalPages") or 1
        if page >= total:
            return entries
        page += 1
        time.sleep(0.1)


def fetch_sttr_bestand(identifier: int | str, *, api_key: str) -> tuple[bytes, str]:
    """Compleet STTR-bestand (DMN-xml) van één entry; return (bytes, sha256)."""
    url = f"{rtr_base()}/toepasbareRegels/{identifier}/sttrBestand"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise client.DsoApiError(
            e.code, e.read().decode("utf-8", errors="replace"), url
        ) from e
    return raw, hashlib.sha256(raw).hexdigest()


def refresh_instrument(
    instrument_id: str,
    *,
    out_dir: pathlib.Path,
    met_bestanden: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Ververs de RTR-cache voor één instrument; return het rtr.json-dict."""
    meta = INSTRUMENTS[instrument_id]
    oin = meta.get("oin")
    if not oin:
        raise SystemExit(
            f"instrument {instrument_id} heeft geen OIN in instruments.py — "
            "lokaliseer het bevoegd gezag via de gm-code in functioneleStructuurRef "
            "(zie docs/POC_STTR_IMTR_KANSEN.md, kans 3)"
        )
    api_key = client.require_dso_key()
    entries = fetch_toepasbare_regels(oin, api_key=api_key)
    geldig = [e for e in entries if not e.get("einddatum")]

    bestanden: dict[str, dict[str, Any]] = {}
    if met_bestanden:
        for e in geldig:
            pad = out_dir / f"{instrument_id}.rtr.{e['identifier']}.dmn"
            if pad.is_file() and pad.stat().st_size > 0 and not force:
                bestanden[str(e["identifier"])] = {
                    "bestand": pad.name,
                    "bytes": pad.stat().st_size,
                    "sha256": hashlib.sha256(pad.read_bytes()).hexdigest(),
                    "cache": "bestaand",
                }
                continue
            raw, sha = fetch_sttr_bestand(e["identifier"], api_key=api_key)
            out_dir.mkdir(parents=True, exist_ok=True)
            pad.write_bytes(raw)
            bestanden[str(e["identifier"])] = {
                "bestand": pad.name,
                "bytes": len(raw),
                "sha256": sha,
                "cache": "opgehaald",
            }
            time.sleep(0.1)

    uit = {
        "contract": CONTRACT,
        "instrument": instrument_id,
        "label": meta.get("label"),
        "oin": oin,
        "base": rtr_base(),
        "gegenereerdOp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "entries": len(entries),
            "geldig": len(geldig),
            "metEinddatum": len(entries) - len(geldig),
            "bestanden": len(bestanden),
        },
        "entries": entries,
        "bestanden": bestanden,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{instrument_id}.rtr.json").write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return uit


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m nldt.simulation.regelrecht.dso_overlap.rtr",
        description=__doc__,
    )
    p.add_argument(
        "--instruments",
        default=",".join(
            sorted(i for i, m in INSTRUMENTS.items() if m.get("oin"))
        ),
        help="komma-gescheiden instrument-id's (default: alle met bekende OIN)",
    )
    p.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help="cache-map (default dso_overlap/out)",
    )
    p.add_argument(
        "--bestanden",
        action="store_true",
        help="download ook alle geldige STTR-bestanden (.dmn)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="met --bestanden: haal ook reeds gecachte bestanden opnieuw op",
    )
    args = p.parse_args(argv)

    for iid in [s.strip() for s in args.instruments.split(",") if s.strip()]:
        if iid not in INSTRUMENTS:
            raise SystemExit(f"onbekend instrument: {iid}")
        uit = refresh_instrument(
            iid, out_dir=args.out_dir, met_bestanden=args.bestanden, force=args.force
        )
        c = uit["counts"]
        print(
            f"{iid}: OIN {uit['oin']} — {c['geldig']} geldig / {c['entries']} entries"
            + (f", {c['bestanden']} bestanden gecacht" if args.bestanden else "")
            + f" → {args.out_dir}/{iid}.rtr.json"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
