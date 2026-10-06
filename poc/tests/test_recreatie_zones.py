# poc/tests/test_recreatie_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_werken_zones.py (begrensde parse is standaard). Twee nieuwe
# aliassen (Gebied bovenlokaal dagrecreatieterrein, Recreatiezone); de
# H9-broer tracks (wonen fase 3, werken fase 5) dekken de overige artikelen
# (ARC-01..08); geen hergebruik nodig — beide zones zijn nieuw.
RECREATIE_ALIASES = [
    "gebied_bovenlokaal_dagrecreatieterrein",
    "recreatiezone",
]
RECREATIE_MATCH = re.compile(r"dagrecreatieterrein|recreatiezone", re.IGNORECASE)


def _alias_source_ids():
    """Parse de recreatie-alias -> sourceId-regels uit run.py::ZONE_SOURCES.

    De scan is begrensd tot het ZONE_SOURCES-dict: de onbegrensde variant
    pakt ook regels buiten het dict en botst zodra een aliasnaam óók een
    TRACKS-sleutel is."""
    lines = (POC / "run.py").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("ZONE_SOURCES"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    block = lines[start:end]
    ids = {}
    for i, line in enumerate(block):
        m = re.match(r'\s*"(\w+)":\s*\{\s*$', line)
        if m and m.group(1) in set(RECREATIE_ALIASES):
            assert i + 1 < len(block), f"alias {m.group(1)} aan het einde van ZONE_SOURCES"
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', block[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in RECREATIE_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_recreatie_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in RECREATIE_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen ÉN de where-NAAM van die bron moet de selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert RECREATIE_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen recreatie-NAAM: {where}"
        )


def test_recreatie_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"recreatie-bronnen zonder cache-twins: {freshly}"
