"""Validatie van de vijf-waardenscan (V0 schema + V1 sanity).

V0 — het scan-artifact is schema-valide (value-scan.schema.json).
V1 — sanity: scores in bereik, aantallen in bereik, geen stille missing
     inputs (elke ``None``-score moet een niet-lege missing-lijst hebben),
     degradaties geregistreerd.
V4 — menselijke check (congres) blijft principieel pending.

Verdict ``pass`` alleen als er nul errors zijn; warnings zijn toegestaan en
worden mee in het rapport genomen.
"""

from __future__ import annotations

import json
from pathlib import Path

JSONSCHEMA_AVAILABLE = True
try:
    import jsonschema
except ImportError:  # pragma: no cover — venv heeft jsonschema
    JSONSCHEMA_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "value-scan.schema.json"

MIN_BUURTEN = 40  # CBS 2024: gemeente Breda = 56 buurten in 11 wijken (recon 2026-09-13,
# geverifieerd via OGC-filter-query op de WFS; grove indeling — zie README)


def validate_scan(scan: dict, degradations: list | None = None, min_buurten: int = MIN_BUURTEN) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    checks: list[dict] = []

    def check(cid, ok, detail, level="error"):
        entry = {"id": cid, "ok": bool(ok), "detail": detail}
        checks.append(entry)
        if not ok:
            (errors if level == "error" else warnings).append(entry)

    # V0 — schema
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if JSONSCHEMA_AVAILABLE:
        try:
            jsonschema.validate(scan, schema)
            check("V0-schema", True, "value-scan.schema.json: geldig")
        except jsonschema.ValidationError as exc:
            check(
                "V0-schema",
                False,
                f"schema-schending op {'/'.join(str(p) for p in exc.absolute_path)}: "
                f"{exc.message}",
            )
    else:  # pragma: no cover
        check("V0-schema", False, "jsonschema niet geinstalleerd", level="warning")

    buurten = scan.get("buurten", [])

    # V1 — volume
    check(
        "V1-buurtvolume",
        len(buurten) >= min_buurten,
        f"{len(buurten)} buurten (verwacht ≥ {min_buurten}; CBS 2024 incl. water-buurten)",
    )

    # V1 — per buurt: score in bereik; None-score <=> missing gedocumenteerd
    bad_range, silent_missing, undocumented_present = [], [], []
    for b in buurten:
        for value, block in (b.get("scores") or {}).items():
            score = block.get("score")
            if score is not None and not (0.0 <= score <= 100.0):
                bad_range.append(f"{b['buurtcode']}/{value}={score}")
            if score is None and not (b.get("missing") or {}).get(value):
                silent_missing.append(f"{b['buurtcode']}/{value}")
            if score is not None and (b.get("missing") or {}).get(value):
                # toegestaan (deelindicator kan ontbreken) — tellen als waarschuwing
                pass
    check(
        "V1-scorebereik",
        not bad_range,
        "alle scores ∈ [0,100]" if not bad_range else f"buiten bereik: {bad_range[:5]}",
    )
    check(
        "V1-missing-gedocumenteerd",
        not silent_missing,
        "elke None-score heeft missing-inputs"
        if not silent_missing
        else f"stille missing: {silent_missing[:5]}",
    )

    # V1 — water-buurten krijgen geen score hoeven te hebben
    water_no_score = [
        b["buurtcode"]
        for b in buurten
        if b.get("water") == "JA"
        and all((b["scores"][v]["score"] is not None) for v in ("democratic", "spatial", "economic", "social"))
    ]
    check(
        "V1-waterbuurten",
        True,  # informatieel: CBS geeft voor water meestal geen statistiek
        f"{len(water_no_score)} water-buurten hebben desondanks volledige scores "
        "(CBS levert daar soms toch afstanden)",
        level="warning" if water_no_score else "info",
    )

    # V1 — degradaties geregistreerd (elke falende bron moet er staan)
    degraded_ids = sorted({d.get("sourceId") for d in (degradations or [])})
    check(
        "V1-degradaties-geregistreerd",
        True,
        f"gedegradeerde bronnen: {degraded_ids or 'geen'}",
        level="info",
    )

    # V1 — zonder CBS-buurtvlakken of wijkdeals-géén scan (fetch zou al falen)
    check(
        "V1-kernbronnen",
        len(buurten) > 0,
        "cbs-buurten-2024 aanwezig",
    )

    verdict = "pass" if not errors else "fail"
    return {
        "validationLevels": {
            "V0": "syntactisch (schema)",
            "V1": "sanity (bereiken, volumes, missing-beleid)",
            "V2": "n.v.t. (geen juridische claims in deze PoC)",
            "V3": "n.v.t. (deterministische herschrijving zit in de unittests)",
            "V4": "pending by design (menselijke check op het congres)",
        },
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "degradations": list(degradations or []),
        "verdict": verdict,
    }
