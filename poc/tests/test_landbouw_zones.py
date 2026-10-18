# poc/tests/test_landbouw_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_landschap_zones.py (begrensde parse is standaard sinds de
# fase-2-reviewbacklog-hygiëne). Selectieregel uit het fase-3-plan:
# agrarisch|landbouw|glastuinbouw|bodembewerking (case-insensitive) over
# poc/data/agrest-namen.json. Selectiefeiten, gedocumenteerd in
# .superpowers/sdd/task-2-report.md en task-3-rapport:
# - zes treffers zijn feitelijk gebonden aan LB-01..LB-06;
# - art. 8.4 geitenhouderij is een provincie-breed verbod ZONDER
#   gebiedsaanwijzing en heeft daarom bewust géén alias (ALB-01);
# - `Gebied glastuinbouw niet toegestaan` dekt vrijwel de hele provincie
#   (1 feature, 1557.796 km2): juridisch correct voor art. 8.6.
LANDBOUW_ALIASES = [
    "gebied_agrarische_bedrijven",
    "landbouwontwikkelingsgebied",
    "landbouwstabiliseringsgebied",
    "concentratiegebied_glastuinbouw",
    "gebied_glastuinbouw_niet_toegestaan",
    "gebied_beperken_bodembewerking",
]
LANDBOUW_MATCH = re.compile(
    r"agrarisch|landbouw|glastuinbouw|bodembewerking", re.IGNORECASE
)


def _alias_source_ids():
    """Alias -> sourceId uit het zone-register poc/tracks/_zone-sources.json
    (sinds nspd-port fase 1 de declaratieve locatie van ZONE_SOURCES)."""
    registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    ids = {}
    for alias in LANDBOUW_ALIASES:
        entry = registry.get(alias)
        assert entry and entry.get("sourceId"), (
            f"zone-alias zonder sourceId in tracks/_zone-sources.json: {alias}")
        ids[alias] = entry["sourceId"]
    return ids


def test_landbouw_aliases_resolve_to_registered_sources():
    zone_registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    for alias in LANDBOUW_ALIASES:
        assert alias in zone_registry, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen ÉN de where-NAAM van die bron moet de selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert LANDBOUW_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen agrarisch/landbouw/"
            f"glastuinbouw/bodembewerking-NAAM: {where}"
        )


def test_landbouw_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"landbouw-bronnen zonder cache-twins: {freshly}"
