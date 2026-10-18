import json
from datetime import date
from pathlib import Path
HERE = Path("poc/data")
pad = HERE / f"probe-sources-{date.today().isoformat()}.json"
reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
reg["probeEvidence"] = [f"poc/data/{pad.name}"] + [
    p for p in reg.get("probeEvidence", []) if "probe-sources-" not in p]
geprobeerd = {b["id"] for b in json.loads(pad.read_text(encoding="utf-8"))["bronnen"]}
for it in reg["sources"]:
    if it["id"] in geprobeerd:
        it["provenance"]["evidence"] = f"poc/data/{pad.name}"
(HERE / "sources.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("probe gelinkt:", len(geprobeerd), "bronnen")
