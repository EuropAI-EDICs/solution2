# toolbox-sim/build_fixtures.py
"""Canonieke run-artefacten → toolbox-sim fixtures. Deterministisch, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LAKE = REPO / "nldt" / "data" / "lake" / "nldt-poc-lake"

CANONICAL_RUNS: dict[str, Path] = {
    "utrecht-wind": REPO / "poc" / "runs" / "20260830T113234Z-wind",
    "utrecht-zon": REPO / "poc" / "runs" / "20260830T142439Z-zon",
    "utrecht-bos": REPO / "poc" / "runs" / "20260830T142446Z-bos",
    "eindhoven-bp2op": REPO / "poc-bp2op" / "runs" / "20260830-124515-eindhoven",
}
UCS_PROCESSES = {  # processId → track; inputs worden genegeerd (documented replay)
    "utrecht-opportunity-map": "utrecht-wind",
    "utrecht-opportunity-map-wind": "utrecht-wind",
    "utrecht-opportunity-map-zon": "utrecht-zon",
    "utrecht-opportunity-map-bos": "utrecht-bos",
    "eindhoven-bp2op": "eindhoven-bp2op",
}


def prop(value: Any) -> dict:
    return {"type": "Property", "value": value}


def rel(objects: str | list[str]) -> dict:
    if isinstance(objects, str):
        return {"type": "Relationship", "object": objects}
    return {"type": "Relationship", "object": objects}


def zone_role(zone_id: str) -> str:
    z = zone_id.lower()
    if "final" in z:
        return "final"
    if "inclusion" in z:
        return "inclusion"
    if "exclusion" in z:
        return "exclusion"
    if any(k in z for k in ("marker", "attention", "conditional", "compensation")):
        return "marker"
    return "other"


def _load(run_dir: Path, name: str) -> Any:
    return json.loads((run_dir / name).read_text())


def build_utrecht_batch(run_dir: Path) -> list[dict]:
    zones = _load(run_dir, "zones.json")
    rules = _load(run_dir, "formalrules.json")
    cards = _load(run_dir, "normcards.json")
    summary = _load(run_dir, "run_summary.json")
    run_uri = f"urn:ldt:utrecht:run:{summary['runId']}"
    entities: list[dict] = [
        {
            "id": run_uri,
            "type": "ldt:PipelineRun",
            "runId": prop(summary["runId"]),
            "useCase": prop(summary["useCase"]),
            "verdict": prop(summary["verdict"]),
            "generatedAt": prop(summary["generatedAt"]),
            "headline": prop(summary["headline"]),
        }
    ]
    for card in cards:
        src = card.get("source", {})
        entities.append(
            {
                "id": f"urn:ldt:utrecht:normcard:{card['id']}",
                "type": "ldt:NormCard",
                "article": prop(src.get("article", "")),
                # Brief zei src["url"]/src["quote_nl"], maar canonieke artefacten
                # hebben source.uri/source.quote; de bindinge test eist http-cites.
                "quote": prop(src.get("quote", "")),
                "legalForce": prop(card.get("legalForce", "")),
                "theme": prop(card.get("theme", "")),
                "cites": rel(src.get("uri", "")),
            }
        )
    for rule in rules:
        entities.append(
            {
                "id": f"urn:ldt:utrecht:rule:{rule['id']}",
                "type": "ldt:FormalRule",
                "ruleType": prop(rule.get("ruleType", "")),
                "zoneSemantics": prop(rule.get("zoneSemantics", "")),
                "status": prop(rule.get("status", "")),
                "groundedIn": rel(f"urn:ldt:utrecht:normcard:{rule['normCardId']}"),
            }
        )
    for zone in zones:
        entities.append(
            {
                "id": f"urn:ldt:utrecht:zone:{zone['id']}",
                "type": "ldt:OpportunityZone",
                "location": {"type": "GeoProperty", "value": zone["geometry"]["payload"]},
                "areaKm2": prop(float(zone["areaKm2"])),
                "operation": prop(zone["operation"]),
                "zoneRole": prop(zone_role(zone["id"])),
                "derivedFromRule": rel([f"urn:ldt:utrecht:rule:{rid}" for rid in zone["ruleIds"]]),
                "generatedBy": rel(run_uri),
            }
        )
    entities.sort(key=lambda e: e["id"])
    return entities


def build_eindhoven_batch(run_dir: Path) -> list[dict]:
    omzettabel = _load(run_dir, "omzettabel.json")
    bronregels = _load(run_dir, "bronregels.json")
    doelregels = _load(run_dir, "doelregels.json")
    kennisbank = _load(run_dir, "kennisbank.json")
    summary = _load(run_dir, "run_summary.json")
    instrument = "http://lokaleregelgeving.overheid.nl/CVDR696400/4"
    run_uri = f"urn:ldt:eindhoven:run:{summary['runId']}"
    entities: list[dict] = [
        {
            "id": run_uri,
            "type": "ldt:PipelineRun",
            "runId": prop(summary["runId"]),
            "useCase": prop(summary["useCase"]),
            "verdict": prop(summary["verdict"]),
            # Brief zei summary["generatedAt"], maar het canonieke bp2op-artefact
            # heeft die sleutel niet (anders dan Utrecht); bindinge test vraagt
            # het niet, dus optioneel met default.
            "generatedAt": prop(summary.get("generatedAt", "")),
            "counts": prop(summary["counts"]),
        }
    ]
    for kb in kennisbank:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:kennisbank:{kb['id']}",
                "type": "ldt:KennisbankRelatie",
                "relationType": prop(kb.get("relatie", "")),
                "source": prop(kb.get("url", "")),
                "bronDocId": prop(kb.get("bronDocId", "")),
            }
        )
    for br in bronregels:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:bronregel:{br['id']}",
                "type": "ldt:BronRegel",
                "locator": prop(br.get("locator", {})),
                "permalink": prop(br.get("url", "")),
                "statusInBron": prop(br.get("statusInBron", "")),
                "partOfInstrument": rel(instrument),
            }
        )
    for dr in doelregels:
        entities.append(
            {
                "id": f"urn:ldt:eindhoven:doelregel:{dr['id']}",
                "type": "ldt:DoelRegel",
                "locator": prop(dr.get("locator", {})),
                "permalink": prop(dr.get("url", "")),
                "partOfInstrument": rel(instrument),
            }
        )
    for row in omzettabel:
        suggesties = row.get("suggesties") or []
        best = suggesties[0] if suggesties else None
        entity = {
            "id": f"urn:ldt:eindhoven:row:{row['id']}",
            "type": "ldt:ConversionRow",
            "status": prop(row["status"]),
            "needsHumanReden": prop(row.get("needsHumanReden")),
            "suggestions": prop(suggesties),
            "hasBronRegel": rel(f"urn:ldt:eindhoven:bronregel:{row['bronRegelId']}"),
            "generatedBy": rel(run_uri),
        }
        if best:
            entity["suggestsDoelRegel"] = {
                "type": "Relationship",
                "object": f"urn:ldt:eindhoven:doelregel:{best['doelRegelId']}",
                "ldt:score": prop(best["score"]),
            }
        if best and best.get("kennisbankHitId"):
            entity["basedOnKennisbank"] = rel(
                f"urn:ldt:eindhoven:kennisbank:{best['kennisbankHitId']}"
            )
        entities.append(entity)
    entities.sort(key=lambda e: e["id"])
    return entities


def write_batch(path: Path, entities: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(entities, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(body, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_eubd_batch(dsn: str, limit: int = 2000) -> list[dict]:
    """Echte PostGIS `exposure.entities`-rijen → ldt:Building-entiteiten.

    Faalt hard wanneer de database onbereikbaar is — geen verzonnen gebouwen.
    """
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("psycopg niet geïnstalleerd (requirements.txt)") from exc
    sql = (
        "SELECT id, building_id, quadkey, attributes, ST_AsGeoJSON(geometry, 6)::json "
        "FROM exposure.entities WHERE category = 0 AND iso_3166 = 'NLD' "
        "ORDER BY quadkey LIMIT %s"
    )
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        # Brief zei sources.doi, maar de autoritatieve DDL
        # (sql/00001_create_initial_structure_exposure.sql) heeft uri; daarin
        # staat de release-DOI (https://doi.org/10.5880/GFZ.2.6.2023.011).
        cur.execute("SELECT uri, name FROM exposure.sources ORDER BY id LIMIT 1")
        src = cur.fetchone() or ("", "")
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
    entities = [
        {
            "id": f"urn:ldt:eubd:building:{r[0]}",
            "type": "ldt:Building",
            "buildingId": prop(r[1] or str(r[0])),
            "quadkey": prop(r[2]),
            "attributes": prop(r[3] or {}),
            "location": {"type": "GeoProperty", "value": r[4]},
            "sourceDoi": prop(src[0]),
        }
        for r in rows
    ]
    entities.sort(key=lambda e: e["id"])
    return entities


def build_dp_temporal() -> dict:
    """NGSI-LD temporele entiteiten uit echte lake-silver-reeksen (KNMI + peilen)."""
    import duckdb

    entities: dict[str, Any] = {}

    knmi_dir = LAKE / "silver" / "timeseries" / "knmi-daily-neerslag-260"
    instances = []
    for line in (knmi_dir / "year=2024" / "observations.jsonl").read_text().splitlines():
        obs = json.loads(line)
        instances.append({"observedAt": obs["observedAt"], "value": obs["value"], "unitCode": obs["unit"]})
    entities["urn:ngsi-ld:WeatherObserved:knmi-260"] = {
        "id": "urn:ngsi-ld:WeatherObserved:knmi-260",
        "type": "WeatherObserved",
        "attribute": "rainfall",
        "provenance": "lake://nldt-poc-lake/silver/timeseries/knmi-daily-neerslag-260 (KNMI daggegevens, CC BY 4.0)",
        "instances": sorted(instances, key=lambda i: i["observedAt"]),
    }

    peilen_path = LAKE / "silver" / "rijnland" / "peilen_latest" / "peilen_latest.parquet"
    rows = duckdb.connect().execute(
        f"SELECT peilgebied_id, waterstand_m, measured_at FROM read_parquet('{peilen_path.as_posix()}') ORDER BY peilgebied_id"
    ).fetchall()
    entities["urn:ngsi-ld:WaterObserved:rijnland-peilen-latest"] = {
        "id": "urn:ngsi-ld:WaterObserved:rijnland-peilen-latest",
        "type": "WaterObserved",
        "attribute": "waterLevel",
        "provenance": "lake://nldt-poc-lake/silver/rijnland/peilen_latest/peilen_latest.parquet",
        "instances": [
            {"observedAt": measured_at.isoformat().replace("+00:00", "") + "Z",
             "value": waterstand, "unit": "mNAP", "datasetId": peilgebied_id}
            for peilgebied_id, waterstand, measured_at in rows
        ],
    }
    return entities


def copy_recipes() -> dict[str, dict]:
    """Alle nldt-recipes als gecombineerde dict (fixtures/recipes.json)."""
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted((REPO / "nldt" / "recipes").glob("*.json"))
    }


def build_participate_seed() -> dict:
    """Participate-seed: voorstellen/meetings herleidbaar naar canonieke runs."""
    return {
        "proposals": [
            {"id": "prop-1", "title": "Zonneweide Noorderpark: 15 ha", "area": "utrecht",
             "state": "open", "provenance": "canonical replay: poc/runs/20260830T142439Z-zon"},
            {"id": "prop-2", "title": "Boscompensatie Leersum: 40 ha", "area": "utrecht",
             "state": "open", "provenance": "canonical replay: poc/runs/20260830T142446Z-bos"},
            {"id": "prop-3", "title": "BP2OP-omzettingsvoorstel: 232 voorgestelde regels",
             "area": "eindhoven", "state": "closed",
             "provenance": "canonical replay: poc-bp2op/runs/20260830-124515-eindhoven"},
        ],
        "meetings": [
            {"id": "meet-1", "title": "Gebiedssessie Utrecht energy-vs-nature", "area": "utrecht"},
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", metavar="DSN", help="PostgreSQL DSN van de exposure-database")
    parser.add_argument("--eubd-limit", type=int, default=2000)
    parser.add_argument("--catalogue-extras", action="store_true",
                        help="schrijf ook dp-temporal/recipes/participate-seed (catalogus-sim)")
    args = parser.parse_args(argv)
    if args.eubd is not None and not args.eubd.strip():
        raise SystemExit(
            "--eubd: lege DSN — de EUBD-batch wordt niet stil overgeslagen; "
            "geef een echte PostgreSQL-DSN op of laat de vlag weg"
        )

    # Bestaand manifest lezen vóór herschrijven: een eubd-buildings-entry die niet
    # herbouwd wordt (geen --eubd) moet bewaard blijven zolang de fixture op schijf staat.
    manifest_path = FIXTURES / "manifest.json"
    previous_eubd: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
        entry = previous.get("batches", {}).get("eubd-buildings")
        if isinstance(entry, dict):
            previous_eubd = entry

    manifest: dict[str, Any] = {"batches": {}}
    for key, run_dir in CANONICAL_RUNS.items():
        if not run_dir.is_dir():
            raise SystemExit(f"canonieke run ontbreekt: {run_dir}")
        batch = (
            build_utrecht_batch(run_dir) if key.startswith("utrecht") else build_eindhoven_batch(run_dir)
        )
        out = FIXTURES / "ngsi-ld" / f"{key}.jsonld"
        write_batch(out, batch)
        manifest["batches"][key] = {
            "file": str(out.relative_to(FIXTURES.parent)),
            "counts": {t: sum(1 for e in batch if e["type"] == t) for t in sorted({e["type"] for e in batch})},
            "sources": {
                name: _sha(run_dir / name)
                for name in (
                    ("zones.json", "formalrules.json", "normcards.json", "run_summary.json")
                    if key.startswith("utrecht")
                    else ("omzettabel.json", "bronregels.json", "doelregels.json", "kennisbank.json", "run_summary.json")
                )
            },
        }
    eubd_out = FIXTURES / "ngsi-ld" / "eubd-buildings.jsonld"
    if args.eubd:
        batch = build_eubd_batch(args.eubd, limit=args.eubd_limit)
        write_batch(eubd_out, batch)
        manifest["batches"]["eubd-buildings"] = {
            "file": str(eubd_out.relative_to(FIXTURES.parent)),
            "counts": {"ldt:Building": len(batch)},
            "sources": {"query": "exposure.entities category=0 iso_3166=NLD ORDER BY quadkey"},
        }
    elif previous_eubd is not None and eubd_out.exists():
        # Geen --eubd deze run, maar de fixture staat nog op schijf: entry bewaren
        # in plaats van hem stilletjes uit het manifest te laten verdwijnen.
        manifest["batches"]["eubd-buildings"] = previous_eubd
    ucs = {
        pid: {
            "track": track,
            "runId": json.loads((CANONICAL_RUNS[track] / "run_summary.json").read_text())["runId"],
            "outputs": _ucs_outputs(CANONICAL_RUNS[track]),
        }
        for pid, track in UCS_PROCESSES.items()
    }
    (FIXTURES / "ucs-processes.json").write_text(
        json.dumps(ucs, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    (FIXTURES / "trino").mkdir(exist_ok=True)
    runs_table = [
        [
            json.loads((d / "run_summary.json").read_text())["runId"],
            json.loads((d / "run_summary.json").read_text())["verdict"],
        ]
        for d in CANONICAL_RUNS.values()
    ]
    (FIXTURES / "trino" / "tables.json").write_text(
        json.dumps(
            {"catalogs": {"timescaledb": {"public": {"runs": {"columns": ["run_id", "verdict"], "rows": runs_table}}}}},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    if args.catalogue_extras:
        extras = {}
        (FIXTURES / "dp-temporal.jsonld").write_text(json.dumps(build_dp_temporal(), indent=1))
        extras["dp-temporal"] = _sha(FIXTURES / "dp-temporal.jsonld")
        (FIXTURES / "recipes.json").write_text(json.dumps(copy_recipes(), indent=1))
        extras["recipes"] = _sha(FIXTURES / "recipes.json")
        (FIXTURES / "participate-seed.json").write_text(json.dumps(build_participate_seed(), indent=1))
        extras["participate-seed"] = _sha(FIXTURES / "participate-seed.json")
        manifest["extras"] = extras
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"fixtures herschreven: {len(manifest['batches'])} batches, ucs-processes, trino/tables.json")
    return 0


def _ucs_outputs(run_dir: Path) -> dict:
    summary = json.loads((run_dir / "run_summary.json").read_text())
    outputs = {"runId": summary["runId"], "verdict": summary["verdict"]}
    if "headline" in summary:
        outputs["headline"] = summary["headline"]
    if "counts" in summary:
        outputs["counts"] = summary["counts"]
    return outputs


if __name__ == "__main__":
    sys.exit(main())
