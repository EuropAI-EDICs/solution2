"""Live-probe van de BE-diensten (taak 3/5): GetCapabilities + typeNames.

Schrijft data/probe_<datum>.json; is GEEN pytest (netwerk). Discipline:
laag die niet live antwoordt blijft status=candidate in sources.json.
Run: python3 data/probe_be_sources.py
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TARGETS = {
    "geopunt-grb-wfs": "https://geo.api.vlaanderen.be/GRB/wfs?service=WFS&version=2.0.0&request=GetCapabilities",
    "geopunt-dhmv-wms": "https://geo.api.vlaanderen.be/DHMV/wms?service=WMS&request=GetCapabilities",
    "mercator-sbz-wms": "https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/ows?service=WMS&request=GetCapabilities",
    "mercator-ruimtelijk-beleid": "https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/ows?service=WFS&version=2.0.0&request=GetCapabilities",
}

INTEREST = re.compile(r"(?i)(adp|gebouw|gewestplan|rup|ruimtelijk|sbz|natura)")


def _probe(url: str) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nLDT-toolbox-poc-nspd/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
            status = r.status
    except Exception as exc:  # luid in het probe-rapport, faal-status voor de registry
        return {"url": url, "status": None, "error": f"{type(exc).__name__}: {exc}"}
    names = sorted(set(re.findall(r"<Name>([^<]{3,90})</Name>", body)))
    return {
        "url": url,
        "status": status,
        "bytes": len(body),
        "interestingNames": [n for n in names if INTEREST.search(n)][:60],
    }


def main() -> None:
    out = Path(__file__).resolve().parent / (
        "probe_" + datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".json")
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "probes": {sid: _probe(url) for sid, url in TARGETS.items()},
    }
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschreven: {out}")
    for sid, p in report["probes"].items():
        print(f"  {sid}: HTTP {p['status']}, {len(p.get('interestingNames', []))} interessante namen")


if __name__ == "__main__":
    main()
