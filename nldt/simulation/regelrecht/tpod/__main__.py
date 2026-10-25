#!/usr/bin/env python3
"""Bouw tpod-indices (en optioneel punt-toetsen) op de gecachte Presenteren-antwoorden.

Gebruik:
  nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod \
    --instruments eindhoven,utrecht \
    [--cache-dir nldt/simulation/regelrecht/dso_overlap/out] [--toets]

``--toets`` executert daarna de formalized artikelen uit de DSO-hit op de
TPOD-geo-feiten (feit/afwezigheid/scenario/onthouding) en schrijft
``<instrument>__<locatie>.toets.json``. Leest ``<instrument>__<locatie>.annotaties.json``
(+ ``.meta.json``) uit de dso_overlap-cache en de RegelRecht-export; geen netwerk:
ververs de cache eerst via
``python -m nldt.simulation.regelrecht.dso_overlap.compare --instruments …``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from nldt.simulation.regelrecht.dso_overlap.instruments import (
    DEFAULT_OUT,
    INSTRUMENTS,
    resolve_location,
)
from nldt.simulation.regelrecht.tpod import CONTRACT, TOETS_CONTRACT
from nldt.simulation.regelrecht.tpod import annotaties, pakket
from nldt.simulation.regelrecht.tpod.index import build_index
from nldt.simulation.regelrecht.tpod.toets import build_toets, bouw_sweep

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "tpod-index.schema.json"
TOETS_SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parent / "punt-toets.schema.json"
)
GEO_SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parent / "geo-validatie.schema.json"
)
SWEEP_SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parent / "voorstel-sweep.schema.json"
)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _valideer(data: Any, schema_path: pathlib.Path, contract: str) -> None:
    errors = sorted(
        Draft202012Validator(_load_json(schema_path)).iter_errors(data),
        key=lambda e: list(e.absolute_path),
    )
    if errors:
        details = "; ".join(
            f"{list(e.absolute_path)}: {e.message}" for e in errors[:5]
        )
        raise SystemExit(f"artefact faalt schema {contract}: {details}")


def build_for_instrument(
    instrument_id: str,
    *,
    cache_dir: pathlib.Path,
    out_dir: pathlib.Path,
    met_toets: bool = False,
    met_geo: bool = False,
    voorstel: dict[str, Any] | None = None,
    met_sweep: bool = False,
    gegenereerd_op: str | None = None,
) -> list[pathlib.Path]:
    meta = INSTRUMENTS[instrument_id]
    locatie = resolve_location(instrument_id, None)
    stem = f"{instrument_id}__{locatie['id']}"
    gegenereerd_op = gegenereerd_op or datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    annotaties_path = cache_dir / f"{stem}.annotaties.json"
    meta_path = cache_dir / f"{stem}.annotaties.meta.json"
    if not annotaties_path.is_file() or not meta_path.is_file():
        raise SystemExit(
            f"cache mist voor {instrument_id}: {annotaties_path} / {meta_path} — "
            "ververs eerst via dso_overlap.compare (met DSO_API_KEY)"
        )
    annotaties_payload = _load_json(annotaties_path)
    annotaties_meta = _load_json(meta_path)

    inputs = [
        {"path": str(annotaties_path), "sha256": _sha256(annotaties_path),
         "role": "presenteren-annotaties"},
    ]

    report_path = pathlib.Path(meta["formalization_report"])
    report = None
    if report_path.is_file():
        report = _load_json(report_path)
        inputs.append({"path": str(report_path), "sha256": _sha256(report_path),
                       "role": "regelrecht-formalization-report"})

    artikelen_path = report_path.parent / f"{instrument_id}-articles.json"
    artikelen = None
    if artikelen_path.is_file():
        artikelen = _load_json(artikelen_path)
        inputs.append({"path": str(artikelen_path), "sha256": _sha256(artikelen_path),
                       "role": "poc-artikelen-export"})

    docstruct_path = cache_dir / f"{stem}.documentstructuur.json"
    docstruct = None
    if docstruct_path.is_file():
        docstruct = annotaties.parse_documentstructuur(_load_json(docstruct_path))
        inputs.append({"path": str(docstruct_path), "sha256": _sha256(docstruct_path),
                       "role": "presenteren-documentstructuur"})

    pakket_index_path = cache_dir / f"{stem}.pakket-index.json"
    pakket_zip_path = cache_dir / f"{stem}.pakket.zip"
    if not pakket_index_path.is_file() and pakket_zip_path.is_file() \
            and pakket_zip_path.stat().st_size > 1000:
        pakket.schrijf_pakket_index(pakket_zip_path, pakket_index_path)
    if pakket_index_path.is_file():
        pakket_index = _load_json(pakket_index_path)
        inputs.append({"path": str(pakket_index_path),
                       "sha256": _sha256(pakket_index_path),
                       "role": "ow-uitwisselpakket-index"})
    else:
        pakket_index = None

    index = build_index(
        instrument_id=instrument_id,
        instrument=meta,
        locatie=locatie,
        annotaties_payload=annotaties_payload,
        annotaties_sha256=annotaties_meta.get(
            "sha256", _sha256(annotaties_path)
        ),
        gegenereerd_op=gegenereerd_op,
        formalization_report=report,
        artikelen=artikelen,
        documentstructuur=docstruct,
        pakket_index=pakket_index,
        extra_inputen=inputs,
    )
    _valideer(index, SCHEMA_PATH, CONTRACT)

    if met_geo and pakket_zip_path.is_file() \
            and pakket_zip_path.stat().st_size > 1000:
        from nldt.simulation.regelrecht.tpod import geo

        geo_index = geo.geo_index_uit_pakket(pakket_zip_path)
        punt = tuple(locatie["geometry"]["coordinates"])
        validatie = geo.valideer_punt(
            geo_index,
            punt=punt,
            geselecteerde_refs=index["geoFeiten"]["geselecteerdeLocatieRefs"],
            hit_locaties=index["geoFeiten"]["locaties"],
        )
        validatie.update(
            {
                "contract": geo.CONTRACT,
                "instrument": {"id": instrument_id, "label": meta["label"]},
                "locatie": {"id": locatie["id"]},
                "gegenereerdOp": gegenereerd_op,
                "sweep": geo.sweep_bevattende_gios(pakket_zip_path, punt),
            }
        )
        validatie["sweep"]["naamAfstemming"] = geo.naam_afstemming(
            index["geoFeiten"]["gebiedsaanwijzingen"],
            validatie["sweep"]["gmls"],
        )
        _valideer(validatie, GEO_SCHEMA_PATH, geo.CONTRACT)
        geo_path = out_dir / f"{stem}.geo-validatie.json"
        geo_path.write_text(
            json.dumps(validatie, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        index["geoValidatie"] = {
            "rapport": geo_path.name,
            "gioInPakket": validatie["koppeling"]["gioInPakket"],
            "metKoppelbareGml": validatie["koppeling"]["metKoppelbareGml"],
            "getoetst": validatie["validatie"]["getoetst"],
            "overeenstemming": validatie["validatie"]["overeenstemming"],
            "conflicten": len(validatie["validatie"]["conflicten"]),
        }
        _valideer(index, SCHEMA_PATH, CONTRACT)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.tpod-index.json"
    out_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    uit = [out_path]

    if met_toets:
        instrument_yaml_path = pathlib.Path(meta["instrument_yaml"])
        yaml_doc = _load_yaml(instrument_yaml_path)
        toets = build_toets(
            instrument_id=instrument_id,
            instrument=meta,
            locatie=locatie,
            tpod_index=index,
            yaml_doc=yaml_doc,
            gegenereerd_op=gegenereerd_op,
            voorstel=voorstel,
        )
        _valideer(toets, TOETS_SCHEMA_PATH, TOETS_CONTRACT)
        toets_path = out_dir / f"{stem}.toets.json"
        toets_path.write_text(
            json.dumps(toets, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        uit.append(toets_path)
        if met_sweep and voorstel and (voorstel.get("variaties") or []):
            sweep = bouw_sweep(
                instrument_id=instrument_id,
                instrument=meta,
                locatie=locatie,
                tpod_index=index,
                yaml_doc=yaml_doc,
                gegenereerd_op=gegenereerd_op,
                voorstel=voorstel,
            )
            _valideer(sweep, SWEEP_SCHEMA_PATH, "voorstel-sweep/v1")
            sweep_path = out_dir / f"{stem}.voorstel-sweep.json"
            sweep_path.write_text(
                json.dumps(sweep, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            uit.append(sweep_path)
    return uit


def _load_yaml(path: pathlib.Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nldt.simulation.regelrecht.tpod",
        description=__doc__,
    )
    parser.add_argument(
        "--instruments",
        default=",".join(sorted(INSTRUMENTS)),
        help="komma-gescheiden instrument-id's (default: alle)",
    )
    parser.add_argument(
        "--cache-dir",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help="map met de gecachte Presenteren-antwoorden",
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=None,
        help="uitvoermap (default: zelfde als --cache-dir)",
    )
    parser.add_argument(
        "--toets",
        action="store_true",
        help="executert formalized artikelen op de TPOD-geo-feiten "
        "(-> <stem>.toets.json)",
    )
    parser.add_argument(
        "--geo",
        action="store_true",
        help="valideert de DSO-puntselectie punt-in-polygoon tegen de "
        "GIO-GML's uit het pakket (-> <stem>.geo-validatie.json; shapely)",
    )
    parser.add_argument(
        "--voorstel",
        type=pathlib.Path,
        default=None,
        help="voorstel-fixture (voorstel/v1: label + parameters) die "
        "scenario-velden en numerieke activiteitparameters invult; "
        "uitkomsten worden gelabeld als voorstel-gebonden",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="met --voorstel: doorloop de 'variaties' uit de fixture en "
        "bouw kantelpunt-rapport (-> <stem>.voorstel-sweep.json)",
    )
    args = parser.parse_args(argv)
    out_dir = args.out_dir or args.cache_dir
    voorstel = None
    if args.voorstel is not None:
        voorstel = _load_json(args.voorstel)
        if not isinstance(voorstel.get("parameters"), dict):
            raise SystemExit(f"voorstel mist parameters-object: {args.voorstel}")

    for instrument_id in [s.strip() for s in args.instruments.split(",") if s.strip()]:
        if instrument_id not in INSTRUMENTS:
            raise SystemExit(f"onbekend instrument: {instrument_id}")
        paden = build_for_instrument(
            instrument_id,
            cache_dir=args.cache_dir,
            out_dir=out_dir,
            met_toets=args.toets,
            met_geo=args.geo,
            voorstel=voorstel,
            met_sweep=args.sweep,
        )
        index = _load_json(paden[0])
        samenvatting = (
            f"{instrument_id}: {index['regelteksten']['aantal']} regelteksten / "
            f"{index['regelteksten']['artikelen']} artikelen; "
            f"{index['regels']['metActiviteiten']} regels met activiteit; "
            f"{index['activiteiten']['totaal']} activiteiten (tophaakKandidaten "
            f"{len(index['activiteiten']['tophaakKandidaten'])}); "
            f"{index['geoFeiten']['aantalLocatiesMetGeometrie']} locaties met "
            f"GIO-geometrie; pons beschikbaar: {index['pons']['beschikbaar']}"
        )
        if args.toets:
            toets = _load_json(paden[1])
            t = toets["tellingen"]
            samenvatting += (
                f" | toets: {t['getoetst']} getoetst, {t['scenario']} scenario, "
                f"{t['onthouding']} onthouding, {t['engineFout']} engine-fout"
            )
            if toets.get("voorstel"):
                sc = toets["voorstel"]["scorecard"]["uitkomsten"]
                samenvatting += (
                    f" (voorstel '{toets['voorstel']['label']}': "
                    f"{sc.get('waar', 0)} waar / {sc.get('onwaar', 0)} onwaar)"
                )
        if len(paden) > (2 if args.toets else 1):
            sweep = _load_json(paden[-1])
            k = len(sweep.get("kantelArtikelen") or [])
            samenvatting += (
                f" | sweep: {sweep['aantalVarianten']} varianten, "
                f"{k} kantel-artikelen"
            )
        if index.get("geoValidatie"):
            g = index["geoValidatie"]
            samenvatting += (
                f" | geo: {g['overeenstemming']}/{g['getoetst']} overeenstemming, "
                f"{g['conflicten']} conflicten"
            )
        print(samenvatting, "->", paden[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
