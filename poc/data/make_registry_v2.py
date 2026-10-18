"""One-shot migratie: sources.json v1.0 -> v2.0 (fetchPolicy + provenance).

fetchPolicy: "cache" als de bron een dual-CRS-cache heeft (cachePath in een
van de 13 canonieke layers.json-manifesten, of een bestand onder
data/cache/national/), anders "service". provenance.pinned = lastChecked van
de bron (of de probe-datum 2026-08-30 voor de agrest/ArcGIS-set); evidence =
de probe-ref uit de bestaande probeEvidence-lijst; note/notes verhuizen naar
provenance.note (de sleutel blijft bewaard voor backwards-compat — consumers
lezen hem niet, geverifieerd per grep, maar weglaten is onnodig risico).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE.parent

reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
manifest_caches: set[str] = set()
for run in sorted((POC / "runs").glob("*/layers.json")):
    for laag in json.loads(run.read_text(encoding="utf-8")).values():
        cp = laag.get("cachePath")
        if cp:
            manifest_caches.add(Path(cp).name)
national = {p.name for p in (POC / "data" / "cache" / "national").rglob("*.json")}
probe_refs = reg.get("probeEvidence", [])
default_probe = probe_refs[0] if probe_refs else "poc/data/probe_raw_20260830.json"

for it in reg["sources"]:
    caches = {f"{it['id']}.28992.geojson", f"{it['id']}.4326.geojson", f"{it['id']}.json"}
    hit = bool(caches & manifest_caches) or any(it["id"] in n for n in national)
    it["fetchPolicy"] = "cache" if hit else "service"
    note = it.pop("note", None)
    extra = it.pop("notes", None)
    note = note or extra  # beide sleutels komen voor; geen van beide mag verliezen
    pinned = str(it.get("lastChecked") or "2026-08-30")[:10]
    it["provenance"] = {"pinned": pinned,
                        "evidence": default_probe,
                        **({"note": note} if note else {})}
    it.setdefault("role", "context")

reg["registryVersion"] = "2.0"
(HERE / "sources.json").write_text(
    json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("registry v2.0:", len(reg["sources"]), "entries;",
      sum(1 for i in reg["sources"] if i["fetchPolicy"] == "cache"), "cache /",
      sum(1 for i in reg["sources"] if i["fetchPolicy"] == "service"), "service")
