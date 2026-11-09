#!/usr/bin/env python3
"""Corpus-staging: plant de instrument-YAML's in de regelrecht-corpus-padconventie.

Fase 1 van het migratietraject (docs/MAPPING_DSO_NAAR_REGELRECHT.md): de
volledige Omgevingsverordening Utrecht (CVDR704250) en het Omgevingsplan
Eindhoven (CVDR696400) zijn de eerste lokale instrumenten die
corpus-klaar zijn. Dit script plant de al tegen schema v0.8.11 gevalideerde
exporten (full_export/out) in de padconventie van
NederlandseDigitaleDienst/regelrecht-corpus — live geverifieerd 8-11-2026:

    regulation/nl/<laag>/<slug>/<valid_from>.yaml   (+ status.yaml per regeling)

Het corpus kent de lagen `wet`, `amvb`, `beleidsregel` en
`waterschaps_verordening`; `gemeentelijke_verordening` en
`provinciale_verordening` bestaan daar nog niet (geen enkel lokaal OV/OP in
het corpus, docs/POC_REGELRECHT_INTEGRATION.md). De status blijft `poc_export`
— géén `harvested` veinzen; indienen loopt via een PR onder de MC-6-discipline
(voorstel, mens op de knop).

Gebruik:
  nldt/.venv/bin/python -m nldt.simulation.regelrecht.corpus_export [--stamp <ISO>]

Offline en deterministisch: leest alléén full_export/out + het vastgepinde
schema; geen netwerk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
from datetime import datetime, timezone
from typing import Any

import yaml
from jsonschema import Draft202012Validator

DIR = pathlib.Path(__file__).resolve().parent
if str(DIR) not in sys.path:
    sys.path.insert(0, str(DIR))

from dso_overlap.instruments import INSTRUMENTS  # noqa: E402

SCHEMA_PATH = DIR / "schema" / "regelrecht-v0.8.11.schema.json"
DEFAULT_OUT = DIR / "corpus_export"

_README = """# Corpus-staging — eerste lokale instrumenten voor regelrecht-corpus

Deze map plant de twee PoC-instrumenten in de padconventie van
[NederlandseDigitaleDienst/regelrecht-corpus](https://github.com/NederlandseDigitaleDienst/regelrecht-corpus)
(`regulation/nl/<laag>/<slug>/<valid_from>.yaml` + `status.yaml`, vorm
geverifieerd tegen het HHNK-precedent CVDR686061_1). Beide bestanden zijn
byte-identieke kopieën van de tegen schema v0.8.11 gevalideerde
full-export (pin: `nldt/simulation/regelrecht/schema/pin.json`).

## Stand van het landelijke corpus (8-11-2026, live gecheckt)

`regulation/nl/` bevat alleen `wet`, `amvb`, `beleidsregel` en
`waterschaps_verordening` — géén enkele gemeentelijke of provinciale
verordening en geen enkel omgevingsplan. Deze staging levert de eerste
kandidaten voor `gemeentelijke_verordening` en `provinciale_verordening`.

## Bewuste keuzes (vóór indienen te beslissen)

- **Omgevingsplan onder `gemeentelijke_verordening`**: schema v0.8.11 kent
  géén `OMGEVINGSPLAN`-laag; dit is de dichtstbijzijnde laag mét
  `gemeente_code`. Moet samen met de laag-uitbreiding in RFC 1/2
  (docs/POC_REGELRECHT_INTEGRATION.md, upstream-issues) worden neergelegd.
- **`cvdr_id`**: schrijft het veld gewoon mee ( valideert, maar het
  upstream law-model leest het sinds v0.7.1 niet meer ) — zelfde issue.
- **`status: poc_export`** in `status.yaml`: eerlijk over de herkomst
  (PoC-export, geen harvest uit BWB); upstream PR's gebruiken `harvested`.

## Indienen (MC-6: voorstel, nooit autonoom)

1. Fork het corpus, branch `poc/lokale-ov-op`.
2. Kopieer `regulation/` uit deze map naar de fork.
3. Open een PR met verwijzing naar
   [POC_REGELRECHT_INTEGRATION.md](../../../docs/POC_REGELRECHT_INTEGRATION.md)
   en [MAPPING_DSO_NAAR_REGELRECHT.md](../../../docs/MAPPING_DSO_NAAR_REGELRECHT.md);
   de PR-review is de mens-op-de-knop.

Herbouwen: `nldt/.venv/bin/python -m nldt.simulation.regelrecht.corpus_export`.
"""


def _stage_instrument(
    instrument_id: str,
    *,
    out_dir: pathlib.Path,
    validator: Draft202012Validator,
    stamp: str,
) -> dict[str, Any]:
    meta = INSTRUMENTS[instrument_id]
    yaml_path: pathlib.Path = meta["instrument_yaml"]
    report_path: pathlib.Path = meta["formalization_report"]

    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    fouten = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if fouten:
        raise SystemExit(
            f"{yaml_path.name} faalt tegen vastgepind schema: "
            + "; ".join(f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
                        for e in fouten[:3])
        )

    laag = str(doc["regulatory_layer"]).lower()
    slug = str(doc["$id"])
    valid_from = str(doc["valid_from"])
    doel = out_dir / "regulation" / "nl" / laag / slug / f"{valid_from}.yaml"
    doel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(yaml_path, doel)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    formalized = sum(
        1 for r in report.get("articles", []) if r.get("status") == "formalized"
    )
    status = {
        "law_id": doc.get("cvdr_id"),
        "law_name": doc["name"],
        "slug": slug,
        "status": "poc_export",
        "bron": "LDT-toolbox full_export (cite-or-abstain)",
        "bron_bestand": str(yaml_path),
        "bron_sha256": hashlib.sha256(yaml_path.read_bytes()).hexdigest(),
        "gegenereerd": stamp,
        "harvest_date": valid_from,
        "article_count": len(doc["articles"]),
        "formalized_count": formalized,
        "warning_count": 0,
        "warnings": [],
    }
    (doel.parent / "status.yaml").write_text(
        yaml.safe_dump(status, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return {
        "instrument": instrument_id,
        "pad": str(doel.relative_to(out_dir)),
        "artikelen": len(doc["articles"]),
        "formalized": formalized,
        "laag": laag,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m nldt.simulation.regelrecht.corpus_export",
        description=__doc__,
    )
    p.add_argument("--stamp", default=None, help="ISO-tijdstempel (default: nu)")
    p.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help=f"stagingsmap (default: {DEFAULT_OUT})",
    )
    args = p.parse_args(argv)
    stamp = args.stamp or datetime.now(timezone.utc).isoformat(timespec="seconds")

    validator = Draft202012Validator(
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    )
    # Alleen instruments met een volle RegelRecht-export (de PoC's); RTR-only
    # koppelingen (zoals veenendaal) hebben geen formalization-report.
    geschikt = [
        iid for iid, meta in sorted(INSTRUMENTS.items())
        if "instrument_yaml" in meta and "formalization_report" in meta
    ]
    regels = [
        _stage_instrument(iid, out_dir=args.out_dir, validator=validator, stamp=stamp)
        for iid in geschikt
    ]
    for iid in sorted(set(INSTRUMENTS) - set(geschikt)):
        print(f"{iid}: overgeslagen — geen full_export (RTR-only koppeling)")
    (args.out_dir / "README.md").write_text(_README, encoding="utf-8")

    for r in regels:
        print(
            f"{r['instrument']}: {r['pad']} — {r['artikelen']} artikelen "
            f"({r['formalized']} formalized, laag {r['laag']})"
        )
    print(f"README → {args.out_dir / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
