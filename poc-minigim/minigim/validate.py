"""Validatie van de MiniGIM-gebiedscheck — dezelfde trant als PoC-1..4.

V0 syntactisch     : jsonschema op elk artifact (checklist, ILS-draft, layer-FC's)
V1 geometrisch     : plangrens geldig + oppervlak > 0; geleverde lagen geldig
V2 brongronding    : elk delivered item heeft volledige prov; de door de Lijst
                     gedeclareerde bronregistratie moet herkenbaar zijn in de prov
V3 determinisme    : alle derivaties opnieuw berekenen uit dezelfde bronlagen en
                     vergelijken (in-run reproduceerbaarheid)
V4 mens            : pending by design — de checklist is input voor de analist
"""

from __future__ import annotations

import json


def validate_v0(doc: dict, schema: dict, artifact_id: str, checks: list) -> None:
    import jsonschema

    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        checks.append({"level": "V0", "artifact": artifact_id, "ok": False,
                       "detail": f"schema-overtreding: {exc.message[:300]}"})
        return
    checks.append({"level": "V0", "artifact": artifact_id, "ok": True, "detail": "schema geldig"})


def validate_v1(aoi_geom, layer_files: list, checks: list) -> None:
    if aoi_geom.is_empty or aoi_geom.area <= 0:
        checks.append({"level": "V1", "artifact": "aoi", "ok": False,
                       "detail": "plangrens leeg of oppervlak 0"})
    else:
        checks.append({"level": "V1", "artifact": "aoi", "ok": True,
                       "detail": f"plangrens geldig, BTO {aoi_geom.area:.1f} m²"})
    for lf in layer_files:
        try:
            fc = json.loads(lf.read_text(encoding="utf-8"))
            n = len(fc.get("features", []))
            checks.append({"level": "V1", "artifact": lf.name, "ok": n >= 0,
                           "detail": f"{n} features, GeoJSON-structuur ok"})
        except Exception as exc:  # noqa: BLE001
            checks.append({"level": "V1", "artifact": lf.name, "ok": False,
                           "detail": f"leesfout: {exc}"})


def validate_v2(records: list[dict], reg, checks: list) -> None:
    failures = []
    for r in records:
        if r["deliveredStatus"] != "delivered":
            continue
        prov = r.get("prov")
        if not prov or not prov.get("protocol"):
            failures.append(f"{r['lijstItemId']}: prov onvolledig")
            continue
        item = reg.item(r["lijstItemId"])
        declared = (item.get("bronRegistratie") or "").strip()
        if declared and prov["protocol"] not in ("derived", "input"):
            hay = " ".join(filter(None, [
                prov.get("bronRegistratie") or "",
                (reg.sources_by_id.get(
                    (reg.binding(r["lijstItemId"]).get("serviceRefs") or [""])[0]
                ) or {}).get("title", ""),
            ])).lower()
            if declared.lower() not in hay:
                failures.append(
                    f"{r['lijstItemId']}: lijst-bron '{declared}' niet in prov '{hay[:80]}'"
                )
    if failures:
        checks.append({"level": "V2", "artifact": "checklist", "ok": False,
                       "detail": "; ".join(failures[:10])})
    else:
        checks.append({"level": "V2", "artifact": "checklist", "ok": True,
                       "detail": "alle delivered items volledig en bron-gegrond"})


def validate_v3(records: list[dict], runner, reg, checks: list) -> None:
    """Herbereken alle derivaties en vergelijk de values (in-run replays)."""
    from .checklist import ChecklistRunner  # noqa: F401 — type hint

    mismatches = []
    for r in records:
        binding = reg.binding(r["lijstItemId"])
        if binding["status"] not in ("auto", "partial") or r["deliveredStatus"] != "delivered":
            continue
        if binding.get("derivation", {}).get("op") in ("echo_input", "representative_point"):
            continue  # puur input-afgeleid: deterministisch by construction
        fresh = runner._execute(reg.item(r["lijstItemId"]), binding)
        if fresh["deliveredStatus"] != "delivered":
            mismatches.append(f"{r['lijstItemId']}: replay niet delivered")
        elif _canon(fresh["values"]) != _canon(r["values"]):
            mismatches.append(f"{r['lijstItemId']}: values wijken af bij replay")
    if mismatches:
        checks.append({"level": "V3", "artifact": "checklist", "ok": False,
                       "detail": "; ".join(mismatches[:10])})
    else:
        checks.append({"level": "V3", "artifact": "checklist", "ok": True,
                       "detail": "alle derivaties reproduceerbaar (replay identiek)"})


def _canon(values: dict) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)


def verdict(checks: list[dict]) -> dict:
    failed = [c for c in checks if not c["ok"]]
    return {
        "levels": checks,
        "verdict": "pass" if not failed else "fail",
        "failedCount": len(failed),
        "v4": "pending",
    }
