#!/usr/bin/env python3
"""Bouw de STTR-import-index over de RTR-cache (of de officiële voorbeelden).

Gebruik:
  # eerst verversen: python -m nldt.simulation.regelrecht.dso_overlap.rtr \
  #                     --instruments eindhoven --bestanden
  nldt/.venv/bin/python -m nldt.simulation.regelrecht.sttr --instruments eindhoven

  # de zes officiële IPLO-voorbeelden (STTR 3.0.0, DMN 1.2) in plaats van de RTR:
  nldt/.venv/bin/python -m nldt.simulation.regelrecht.sttr --van-voorbeelden

Geen netwerk: leest ``<instrument>.rtr.json`` + ``<instrument>.rtr.<id>.dmn``
uit de dso_overlap-cache en schrijft ``<instrument>.sttr.json`` (contract
``sttr-index/v1``): per bestand de beslistabellen en — waar deterministisch
mogelijk — de engine-projectie met scenario-uitkomsten (docs/POC_STTR_IMTR_KANSEN.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from datetime import datetime, timezone
from typing import Any

from jsonschema import Draft202012Validator

from nldt.simulation.regelrecht.dso_overlap.instruments import DEFAULT_OUT, INSTRUMENTS
from nldt.simulation.regelrecht.sttr import CONTRACT
from nldt.simulation.regelrecht.sttr.dmn import SttrParseFout, parse_sttr
from nldt.simulation.regelrecht.sttr.executie import projecteer_decision, scenario_run

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "sttr-index.schema.json"
VOORBEELDEN_DIR = (
    pathlib.Path(__file__).resolve().parents[4]
    / "docs" / "research" / "sttr-imtr" / "dmn-voorbeelden-sttr-3.0.0"
)
_ACT_RE = re.compile(r"nl\.imow-[a-z0-9]+\.activiteit\.([A-Za-z0-9]+)")


def _activiteit_uit_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    m = _ACT_RE.search(ref)
    return m.group(1) if m else None


def _samenvatting_bestand(
    *, naam: str | None, dmn_tekst_sha: str, parsed: dict[str, Any],
    identifier: int | str | None, begindatum: str | None, einddatum: str | None,
    functionele_structuur_ref: str | None,
) -> dict[str, Any]:
    decisions_uit: list[dict[str, Any]] = []
    redenen: dict[str, int] = {}
    scenario_uitgevoerd = 0
    refs = [functionele_structuur_ref] + [
        d.get("functioneleStructuurRef") for d in parsed.get("decisions") or []
    ]
    for d in parsed.get("decisions") or []:
        projectie = projecteer_decision(d)
        scenario = scenario_run(projectie)
        if scenario.get("status") == "uitgevoerd":
            scenario_uitgevoerd += 1
        if not projectie.get("projecteerbaar"):
            reden = projectie.get("reden") or "onbekend"
            redenen[reden] = redenen.get(reden, 0) + 1
        rec = {
            "naam": projectie.get("naam"),
            "hitPolicy": projectie.get("hitPolicy"),
            "aantalRijen": projectie.get("aantalRijen", 0),
            "projecteerbaar": projectie.get("projecteerbaar", False),
            "reden": projectie.get("reden"),
        }
        if projectie.get("projecteerbaar"):
            rec["defaultRij"] = projectie.get("defaultRij", False)
            rec["uitgang"] = projectie.get("uitgang")
            rec["inputs"] = projectie.get("inputs")
            rec["scenario"] = scenario
        decisions_uit.append(rec)

    return {
        "identifier": identifier,
        "naam": parsed.get("naam") or naam,
        "activiteit": _activiteit_uit_ref(functionele_structuur_ref),
        "begindatum": begindatum,
        "einddatum": einddatum,
        "dmnVersie": parsed.get("dmnVersie"),
        "sttrNamespace": parsed.get("sttrNamespace"),
        "sttrVersie": parsed.get("sttrVersie"),
        "exporter": parsed.get("exporter"),
        "sha256": dmn_tekst_sha,
        "functioneleStructuurRef": functionele_structuur_ref,
        "kennisbronnen": len(parsed.get("kennisbronnen") or []),
        "geoVerwijzingen": sum(
            1 for u in parsed.get("uitvoeringsregels") or [] if "geoVerwijzing" in u
        ),
        "redenen": redenen,
        "scenarioUitgevoerd": scenario_uitgevoerd,
        "decisions": decisions_uit,
    }


def _totaal(bestanden: list[dict[str, Any]], *, instrument: str) -> dict[str, Any]:
    dmn_versies: dict[str, int] = {}
    exporters: dict[str, int] = {}
    redenen: dict[str, int] = {}
    for b in bestanden:
        dmn_versies[b["dmnVersie"]] = dmn_versies.get(b["dmnVersie"], 0) + 1
        exp = b.get("exporter") or "(geen)"
        exporters[exp] = exporters.get(exp, 0) + 1
        for reden, n in (b.get("redenen") or {}).items():
            redenen[reden] = redenen.get(reden, 0) + n
    alle_decisions = [d for b in bestanden for d in b["decisions"]]
    return {
        "bestanden": len(bestanden),
        "decisions": len(alle_decisions),
        "projecteerbaar": sum(1 for d in alle_decisions if d["projecteerbaar"]),
        "nietProjecteerbaar": sum(1 for d in alle_decisions if not d["projecteerbaar"]),
        "dmnVersies": dmn_versies,
        "exporters": exporters,
        "redenen": redenen,
        "geoVerwijzingen": sum(b.get("geoVerwijzingen", 0) for b in bestanden),
        "kennisbronnen": sum(b.get("kennisbronnen", 0) for b in bestanden),
        "scenarioUitgevoerd": sum(b.get("scenarioUitgevoerd", 0) for b in bestanden),
    }


def bouw_uit_rtr(instrument_id: str, *, cache_dir: pathlib.Path) -> dict[str, Any]:
    rtr_pad = cache_dir / f"{instrument_id}.rtr.json"
    if not rtr_pad.is_file():
        raise SystemExit(
            f"RTR-cache mist {rtr_pad} — ververs eerst: "
            f"python -m nldt.simulation.regelrecht.dso_overlap.rtr --instruments {instrument_id} --bestanden"
        )
    rtr = json.loads(rtr_pad.read_text(encoding="utf-8"))
    bestanden: list[dict[str, Any]] = []
    for entry in rtr.get("entries") or []:
        if entry.get("einddatum"):
            continue
        dmn_pad = cache_dir / f"{instrument_id}.rtr.{entry['identifier']}.dmn"
        if not dmn_pad.is_file():
            continue
        tekst = dmn_pad.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = parse_sttr(tekst)
        except SttrParseFout as e:
            bestanden.append(
                {
                    "identifier": entry["identifier"],
                    "naam": dmn_pad.name,
                    "activiteit": _activiteit_uit_ref(entry.get("functioneleStructuurRef")),
                    "begindatum": entry.get("begindatum"),
                    "einddatum": entry.get("einddatum"),
                    "dmnVersie": "onbekend",
                    "sttrNamespace": None,
                    "sttrVersie": None,
                    "exporter": None,
                    "sha256": hashlib.sha256(tekst.encode()).hexdigest(),
                    "functioneleStructuurRef": entry.get("functioneleStructuurRef"),
                    "kennisbronnen": 0,
                    "geoVerwijzingen": 0,
                    "redenen": {f"parse-fout: {e}": 1},
                    "scenarioUitgevoerd": 0,
                    "decisions": [
                        {
                            "naam": None,
                            "hitPolicy": None,
                            "aantalRijen": 0,
                            "projecteerbaar": False,
                            "reden": f"parse-fout: {e}",
                        }
                    ],
                }
            )
            continue
        bestanden.append(
            _samenvatting_bestand(
                naam=dmn_pad.name,
                dmn_tekst_sha=hashlib.sha256(tekst.encode()).hexdigest(),
                parsed=parsed,
                identifier=entry["identifier"],
                begindatum=entry.get("begindatum"),
                einddatum=entry.get("einddatum"),
                functionele_structuur_ref=entry.get("functioneleStructuurRef"),
            )
        )
    return {
        "contract": CONTRACT,
        "instrument": instrument_id,
        "label": rtr.get("label"),
        "oin": rtr.get("oin"),
        "gegenereerdOp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bronnen": {
            "rtrCache": str(rtr_pad),
            "rtrCacheSha256": hashlib.sha256(rtr_pad.read_bytes()).hexdigest(),
        },
        "totals": _totaal(bestanden, instrument=instrument_id),
        "bestanden": bestanden,
    }


def bouw_uit_voorbeelden(*, bron_dir: pathlib.Path = VOORBEELDEN_DIR) -> dict[str, Any]:
    bestanden: list[dict[str, Any]] = []
    for dmn_pad in sorted(bron_dir.rglob("*.dmn")):
        tekst = dmn_pad.read_text(encoding="utf-8", errors="replace")
        parsed = parse_sttr(tekst)
        bestanden.append(
            _samenvatting_bestand(
                naam=dmn_pad.name,
                dmn_tekst_sha=hashlib.sha256(tekst.encode()).hexdigest(),
                parsed=parsed,
                identifier=dmn_pad.stem,
                begindatum=None,
                einddatum=None,
                functionele_structuur_ref=None,
            )
        )
    return {
        "contract": CONTRACT,
        "instrument": "voorbeelden",
        "label": "Officiële IPLO-voorbeeldbestanden STTR 3.0.0",
        "oin": None,
        "gegenereerdOp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bronnen": {"rtrCache": None, "rtrCacheSha256": None},
        "totals": _totaal(bestanden, instrument="voorbeelden"),
        "bestanden": bestanden,
    }


def _valideer(data: Any) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    fouten = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda e: list(e.absolute_path),
    )
    if fouten:
        details = "; ".join(
            f"{list(e.absolute_path)}: {e.message}" for e in fouten[:5]
        )
        raise SystemExit(f"artefact faalt schema {CONTRACT}: {details}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m nldt.simulation.regelrecht.sttr",
        description=__doc__,
    )
    p.add_argument("--instruments", default="eindhoven", help="komma-gescheiden")
    p.add_argument(
        "--cache-dir",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help="map met de RTR-cache (dso_overlap/out)",
    )
    p.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=None,
        help="uitvoermap (default: zelfde als --cache-dir)",
    )
    p.add_argument(
        "--van-voorbeelden",
        action="store_true",
        help="ontleed de officiële IPLO-voorbeeldbestanden i.p.v. de RTR-cache",
    )
    args = p.parse_args(argv)
    out_dir = args.out_dir or args.cache_dir

    if args.van_voorbeelden:
        index = bouw_uit_voorbeelden()
        _valideer(index)
        pad = out_dir / "voorbeelden.sttr.json"
        pad.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", "utf-8")
        t = index["totals"]
        print(
            f"voorbeelden: {t['bestanden']} bestanden, {t['decisions']} decisions, "
            f"{t['projecteerbaar']} projecteerbaar → {pad}"
        )
        return 0

    for iid in [s.strip() for s in args.instruments.split(",") if s.strip()]:
        if iid not in INSTRUMENTS:
            raise SystemExit(f"onbekend instrument: {iid}")
        index = bouw_uit_rtr(iid, cache_dir=args.cache_dir)
        _valideer(index)
        pad = out_dir / f"{iid}.sttr.json"
        pad.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", "utf-8")
        t = index["totals"]
        print(
            f"{iid}: {t['bestanden']} bestanden ({t['dmnVersies']}), "
            f"{t['decisions']} decisions, {t['projecteerbaar']} projecteerbaar, "
            f"{t['scenarioUitgevoerd']} scenario-uitgevoerd → {pad}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
