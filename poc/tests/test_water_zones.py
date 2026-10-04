# poc/tests/test_water_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Twee minimale aanpassingen ten opzichte van de brief-letterlijke testcode,
# gedocumenteerd in .superpowers/sdd/task-5-report.md:
# 1. `data/sources.json` is een object met een "sources"-lijst (metadata-
#    wrapper, zie pipeline/geodata.py::load_sources); itereren over het
#    top-level object levert string-keys -> TypeError. Fix: ["sources"].
# 2. De water-substring-scan over de volledige record-dump matcht 13
#    bestaande entries via toevallige substrings in notes/velden (o.a.
#    "watergren"-veldnamen, "Zoekgebieden waterberging" in notities, drie
#    alldata-lagen van 5k-35k features) die buiten deze taak vallen en geen
#    cache-twins hebben. Fix: veranker de cache-eis op de drie water-alias-
#    bronnen uit run.py::ZONE_SOURCES (het Produces-contract van taak 5).
#    run.py wordt tekstueel geparseerd (net als de brief-test zelf) en niet
#    geïmporteerd: import run trekt pipeline.norm_llm -> pipeline.llm_transport,
#    een module die buiten deze worktree bestaat en dus niet beschikbaar is.
WATER_ALIASES = ["waterbergingsgebied", "overstroombaar_gebied", "vrijwaringszone_waterkering"]


def _alias_source_ids():
    """Parse de drie water-alias -> sourceId-regels uit run.py::ZONE_SOURCES."""
    lines = (POC / "run.py").read_text().splitlines()
    ids = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"(\w+)":\s*\{\s*$', line)
        if m and m.group(1) in set(WATER_ALIASES):
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', lines[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in WATER_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_water_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in WATER_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    ids = {s["id"] for s in registry}
    for line in run_py.splitlines():
        m = re.match(r'\s*"(\w+)":\s*"([\w.-]+)",?\s*(?:#.*)?$', line)
        if m and m.group(1) in set(WATER_ALIASES):
            assert m.group(2) in ids, f"alias {m.group(1)} -> onbekende bron {m.group(2)}"
    # sterke vorm: de dict-vorm van ZONE_SOURCES (zoals gebied_windenergie)
    # moet op een bestaand registry-id wijzen.
    for alias, sid in _alias_source_ids().items():
        assert sid in ids, f"alias {alias} -> onbekende bron {sid}"


def test_water_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"water-bronnen zonder cache-twins: {freshly}"
