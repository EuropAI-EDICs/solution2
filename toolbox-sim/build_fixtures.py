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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eubd", metavar="DSN", help="PostgreSQL DSN van de exposure-database")
    parser.add_argument("--eubd-limit", type=int, default=2000)
    args = parser.parse_args(argv)

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
    if args.eubd:
        batch = build_eubd_batch(args.eubd, limit=args.eubd_limit)
        out = FIXTURES / "ngsi-ld" / "eubd-buildings.jsonld"
        write_batch(out, batch)
        manifest["batches"]["eubd-buildings"] = {
            "file": str(out.relative_to(FIXTURES.parent)),
            "counts": {"ldt:Building": len(batch)},
            "sources": {"query": "exposure.entities category=0 iso_3166=NLD ORDER BY quadkey"},
        }
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
    (FIXTURES / "manifest.json").write_text(
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
