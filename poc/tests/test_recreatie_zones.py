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
    """Alias -> sourceId uit het zone-register poc/tracks/_zone-sources.json
    (sinds nspd-port fase 1 de declaratieve locatie van ZONE_SOURCES)."""
    registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    ids = {}
    for alias in RECREATIE_ALIASES:
        entry = registry.get(alias)
        assert entry and entry.get("sourceId"), (
            f"zone-alias zonder sourceId in tracks/_zone-sources.json: {alias}")
        ids[alias] = entry["sourceId"]
    return ids


def test_recreatie_aliases_resolve_to_registered_sources():
    zone_registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    for alias in RECREATIE_ALIASES:
        assert alias in zone_registry, alias
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
