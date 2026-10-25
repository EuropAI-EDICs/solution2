#!/usr/bin/env python3
"""Vergelijk DSO Presenteren (+ optioneel RP) met RegelRecht formalization reports.

Gebruik:
  export DSO_API_KEY=…          # Presenteren (PRE of prod)
  export RP_API_KEY=…           # optioneel: Ruimtelijke plannen V4
  # optioneel:
  # export DSO_PRESENTEREN_BASE=https://service.pre.omgevingswet.overheid.nl/publiek/omgevingsdocumenten/api/presenteren/v8

  nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.compare \\
    --instruments eindhoven,utrecht

  # Offline herhaal (cached raw responses):
  … compare --instruments eindhoven --offline --cache-dir nldt/simulation/regelrecht/dso_overlap/out

Keys nooit committen. Rapporten landen onder dso_overlap/out/.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

DIR = pathlib.Path(__file__).resolve().parent
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

import client  # noqa: E402
from instruments import DEFAULT_OUT, INSTRUMENTS, resolve_location  # noqa: E402
from overlap import build_overlap  # noqa: E402


def _write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _cache_paths(cache_dir: pathlib.Path, instrument_id: str, location_id: str):
    stem = f"{instrument_id}__{location_id}"
    return {
        "regeling": cache_dir / f"{stem}.regeling.json",
        "annotaties": cache_dir / f"{stem}.annotaties.json",
        "annotaties_meta": cache_dir / f"{stem}.annotaties.meta.json",
        "documentstructuur": cache_dir / f"{stem}.documentstructuur.json",
        "documentstructuur_meta": cache_dir / f"{stem}.documentstructuur.meta.json",
        "pakket": cache_dir / f"{stem}.pakket.zip",
        "pakket_meta": cache_dir / f"{stem}.pakket.meta.json",
        "rp": cache_dir / f"{stem}.rp.json",
        "rp_meta": cache_dir / f"{stem}.rp.meta.json",
        "report": cache_dir / f"{stem}.overlap.json",
    }


def _fetch_documentstructuur(meta: dict[str, Any], api_key: str, path: dict) -> None:
    payload, sha = client.fetch_documentstructuur(meta["akn_uri"], api_key=api_key)
    _write_json(path["documentstructuur"], payload)
    _write_json(
        path["documentstructuur_meta"],
        {
            "sha256": sha,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "aknUri": meta["akn_uri"],
        },
    )


def _fetch_pakket(meta: dict[str, Any], api_key: str, path: dict) -> None:
    """OW-uitwisselpakket (pons, GIO's) via de asynchrone downloaden-API.

    Duurt van enkele seconden tot minuten (status-poll); sla over als de
    cache al een niet-lege zip bevat.
    """
    if path["pakket"].is_file() and path["pakket"].stat().st_size > 1000:
        print(f"  pakket al in cache: {path['pakket']}")
        return
    raw, sha = client.fetch_uitwisselpakket(
        meta["akn_path"], api_key=api_key
    )
    path["pakket"].parent.mkdir(parents=True, exist_ok=True)
    path["pakket"].write_bytes(raw)
    _write_json(
        path["pakket_meta"],
        {
            "sha256": sha,
            "bytes": len(raw),
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "regelingId": meta["akn_path"],
        },
    )


def compare_instrument(
    instrument_id: str,
    *,
    location_id: str | None,
    out_dir: pathlib.Path,
    offline: bool,
    skip_rp: bool,
    pakket: bool = False,
) -> dict[str, Any]:
    if instrument_id not in INSTRUMENTS:
        raise SystemExit(f"onbekend instrument: {instrument_id}")
    meta = INSTRUMENTS[instrument_id]
    location = resolve_location(instrument_id, location_id)
    paths = _cache_paths(out_dir, instrument_id, location["id"])
    report_path = pathlib.Path(meta["formalization_report"])
    if not report_path.is_file():
        raise SystemExit(f"formalization-report ontbreekt: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    if offline:
        for key in ("regeling", "annotaties", "annotaties_meta"):
            if not paths[key].is_file():
                raise SystemExit(f"--offline: cache mist {paths[key]}")
        regeling = json.loads(paths["regeling"].read_text(encoding="utf-8"))
        annotaties = json.loads(paths["annotaties"].read_text(encoding="utf-8"))
        ann_meta = json.loads(paths["annotaties_meta"].read_text(encoding="utf-8"))
        ann_sha = ann_meta["sha256"]
        rp_plannen = None
        rp_sha = None
        if paths["rp"].is_file():
            rp_plannen = json.loads(paths["rp"].read_text(encoding="utf-8"))
            rp_sha = json.loads(paths["rp_meta"].read_text(encoding="utf-8"))["sha256"]
    else:
        api_key = client.require_dso_key()
        regeling = client.fetch_regeling(meta["akn_uri"], api_key=api_key)
        annotaties, ann_sha = client.fetch_regeltekstannotaties(
            meta["akn_uri"],
            location["geometry"],
            api_key=api_key,
        )
        _write_json(paths["regeling"], regeling)
        _write_json(paths["annotaties"], annotaties)
        _write_json(
            paths["annotaties_meta"],
            {
                "sha256": ann_sha,
                "fetchedAt": datetime.now(timezone.utc).isoformat(),
                "presenterenBase": client.presenteren_base(),
                "aknUri": meta["akn_uri"],
            },
        )
        _fetch_documentstructuur(meta, api_key, paths)
        if pakket:
            print("  uitwisselpakket aanvragen (kan minuten duren)…")
            _fetch_pakket(meta, api_key, paths)

        rp_plannen = None
        rp_sha = None
        rp_key = None if skip_rp else client.optional_rp_key()
        if rp_key:
            try:
                rp_plannen, rp_sha = client.fetch_rp_plannen(
                    location["geometry"],
                    api_key=rp_key,
                )
                _write_json(paths["rp"], rp_plannen)
                _write_json(
                    paths["rp_meta"],
                    {
                        "sha256": rp_sha,
                        "fetchedAt": datetime.now(timezone.utc).isoformat(),
                        "rpBase": client.rp_base(),
                    },
                )
            except client.DsoApiError as e:
                _write_json(
                    paths["rp_meta"],
                    {"error": str(e), "status": e.status},
                )

    result = build_overlap(
        instrument_id=instrument_id,
        location=location,
        regeling=regeling,
        annotaties=annotaties,
        annotaties_sha256=ann_sha,
        report=report,
        rp_plannen=rp_plannen,
        rp_sha256=rp_sha,
    )
    result["generatedAt"] = datetime.now(timezone.utc).isoformat()
    result["paths"] = {
        "formalizationReport": str(report_path),
        "overlapReport": str(paths["report"]),
    }
    _write_json(paths["report"], result)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--instruments",
        default="eindhoven,utrecht",
        help="Komma-gescheiden: eindhoven,utrecht",
    )
    p.add_argument(
        "--location",
        default=None,
        help="Optionele location_id uit fixtures/locations.json (per instrument default)",
    )
    p.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help="Cache + overlap-rapporten",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="Geen netwerk; hergebruik cached annotaties in --out-dir",
    )
    p.add_argument(
        "--skip-rp",
        action="store_true",
        help="Geen Ruimtelijke plannen-aanroep (ook als RP_API_KEY gezet is)",
    )
    p.add_argument(
        "--pakket",
        action="store_true",
        help="Ook het OW-uitwisselpakket (pons, GIO's) via de downloaden-API "
        "cachen; asynchroon, kan minuten duren",
    )
    args = p.parse_args(argv)

    ids = [x.strip() for x in args.instruments.split(",") if x.strip()]
    summaries = []
    for iid in ids:
        result = compare_instrument(
            iid,
            location_id=args.location,
            out_dir=args.out_dir,
            offline=args.offline,
            skip_rp=args.skip_rp,
            pakket=args.pakket,
        )
        ov = result["overlap"]
        summaries.append(
            {
                "instrument": iid,
                "location": result["location"]["id"],
                "dsoArticles": result["dso"]["counts"]["uniqueArticleNumbers"],
                "executable": ov["executableCount"],
                "abstain": ov["abstainCount"],
                "coverageExecutable": ov["coverageExecutable"],
                "statusCounts": ov["statusCounts"],
                "report": result["paths"]["overlapReport"],
            }
        )
        print(
            f"{iid}: DSO-artikelen={result['dso']['counts']['uniqueArticleNumbers']} "
            f"executable={ov['executableCount']} "
            f"abstain={ov['abstainCount']} "
            f"coverage={ov['coverageExecutable']} "
            f"→ {result['paths']['overlapReport']}"
        )

    index_path = args.out_dir / "overlap-index.json"
    _write_json(
        index_path,
        {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "instruments": summaries,
        },
    )
    print(f"index → {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
