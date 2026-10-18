# poc/tests/test_biomassa_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_landbouw_zones.py. Selectie letterlijk op biomassa-GIO's
# in poc/data/agrest-namen.json (Gebied energie uit biomassa landelijk/stedelijk).
BIOMASSA_ALIASES = [
    "gebied_energie_biomassa_landelijk",
    "gebied_energie_biomassa_stedelijk",
]
BIOMASSA_MATCH = re.compile(r"biomassa", re.IGNORECASE)


def _alias_source_ids():
    """Alias -> sourceId uit het zone-register poc/tracks/_zone-sources.json
    (sinds nspd-port fase 1 de declaratieve locatie van ZONE_SOURCES)."""
    registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    ids = {}
    for alias in BIOMASSA_ALIASES:
        entry = registry.get(alias)
        assert entry and entry.get("sourceId"), (
            f"zone-alias zonder sourceId in tracks/_zone-sources.json: {alias}")
        ids[alias] = entry["sourceId"]
    return ids


def test_biomassa_aliases_resolve_to_registered_sources():
    zone_registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    for alias in BIOMASSA_ALIASES:
        assert alias in zone_registry, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert BIOMASSA_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen biomassa-NAAM: {where}"
        )


def test_biomassa_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"biomassa-bronnen zonder cache-twins: {freshly}"
