#!/usr/bin/env python3
"""Build marketplace/data/catalog.json from edic-asset-map + recipe JSON files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "marketplace" / "data" / "catalog.json"
RECIPES_OUT = ROOT / "marketplace" / "data" / "recipes"


def display_owner(asset: dict) -> str:
    """Marketplace-facing owner (not internal delivery org)."""
    asset_class = str(asset.get("assetClass") or "")
    edic = str(asset.get("edic") or "")
    if asset_class.startswith("hcs") or edic == "impacts":
        return "EuropAI"
    return "LDT EDIC"


def theme_for(recipe_id: str) -> str:
    rid = recipe_id
    if rid.startswith("thk-"):
        return "key"
    if rid.startswith(("uam-", "grn-", "cir-", "min-")) and not rid.startswith("minigim"):
        return "city"
    if any(x in rid for x in ("utrecht", "opportunity", "scenario", "crosstrack", "world-scene", "multi-track")):
        return "utrecht"
    if "breda" in rid:
        return "breda"
    if "rijnland" in rid or "peil" in rid:
        return "rijnland"
    if "eindhoven" in rid or "bp2op" in rid:
        return "eindhoven"
    if any(x in rid for x in ("donl", "lake", "timeseries", "source-monitor")):
        return "lake"
    if any(x in rid for x in ("spatial", "hex", "beleidskompas", "minigim")):
        return "gis"
    return "other"


def main() -> int:
    import shutil

    assets = json.loads((ROOT / "recipes" / "edic-asset-map.json").read_text(encoding="utf-8"))["assets"]
    RECIPES_OUT.mkdir(parents=True, exist_ok=True)
    recipes: list[dict] = []
    for a in assets:
        if a.get("kind") != "recipe":
            continue
        name = Path(a.get("path", "")).name
        local = ROOT / "recipes" / name
        rec: dict = {}
        if local.is_file():
            rec = json.loads(local.read_text(encoding="utf-8"))
            shutil.copy2(local, RECIPES_OUT / name)
        rid = rec.get("id") or str(a["id"]).removeprefix("recipe:")
        procs = rec.get("requiredProcesses") or [
            s.get("processId")
            for s in (rec.get("steps") or [])
            if isinstance(s, dict) and s.get("processId")
        ]
        seen: set[str] = set()
        uniq: list[str] = []
        for p in procs:
            if p and p not in seen:
                seen.add(p)
                uniq.append(p)
        recipes.append(
            {
                "id": rid,
                "assetId": a["id"],
                "title": rec.get("title") or a.get("title"),
                "description": rec.get("description") or "",
                "riskLevel": rec.get("riskLevel") or a.get("riskLevel") or "",
                "requiredProcesses": uniq,
                "edic": a.get("edic"),
                "assetClass": a.get("assetClass"),
                "owner": display_owner(a),
                "readiness": a.get("readiness"),
                "acceptance": a.get("acceptance"),
                "path": f"./data/recipes/{name}",
                "tags": rec.get("tags") or [],
                "theme": theme_for(rid),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0",
        "source": "edic-asset-map+recipes",
        "count": len(recipes),
        "recipes": recipes,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(recipes)} recipes -> {OUT.relative_to(ROOT)}")
    print(dict(Counter(r["theme"] for r in recipes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
