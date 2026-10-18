# poc/tests/test_wonen_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_landbouw_zones.py (begrensde parse is standaard). De
# selectieregel uit het fase-3-plan (wonen: wonen|woning| recreatie|stedelijk|
# kernrand, feitelijk aangevuld met de verordeningtermen) is hier gebaseerd op
# de selectiefeiten die in .superpowers/sdd/task-5-report.md en het task-6-
# rapport zijn gedocumenteerd:
# - vier nieuwe aliassen (Kernrandzone, Gebied recreatiewoning, Gebied
#   uitbreiding woningbouw onder voorwaarden mogelijk, Stedelijk gebied);
# - HERGEBRUIK (fase-1-dedupregel: zelfde service+laag) van de bestaande
#   aliassen landelijk_gebied (WN-01/02/05/06), stiltegebied en
#   aandachtsgebied_stiltegebied (WN-11/WN-12, deels al wind-track W-10) —
#   die staan al in ZONE_SOURCES en worden hier niet opnieuw geëist;
# - gaps: bebouwingsenclaves/-linten (9.7) hebben geen GIO/NAAM (AWN-03);
#   werken/recreatie-zones (reductielocaties, kantoor-knooppunten,
#   detailhandel, bedrijventerrein-uitbreiding, recreatiezone,
#   dagrecreatieterrein) zijn bewust niet geregistreerd in deze track
#   (AWN-04/07, fase-4-heroverweging).
WONEN_ALIASES = [
    "kernrandzone",
    "gebied_recreatiewoning",
    "gebied_uitbreiding_woningbouw",
    "stedelijk_gebied",
]
WONEN_MATCH = re.compile(
    r"woning|recreatiewoning|stedelijk|kernrand", re.IGNORECASE
)


def _alias_source_ids():
    """Alias -> sourceId uit het zone-register poc/tracks/_zone-sources.json
    (sinds nspd-port fase 1 de declaratieve locatie van ZONE_SOURCES)."""
    registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    ids = {}
    for alias in WONEN_ALIASES:
        entry = registry.get(alias)
        assert entry and entry.get("sourceId"), (
            f"zone-alias zonder sourceId in tracks/_zone-sources.json: {alias}")
        ids[alias] = entry["sourceId"]
    return ids


def test_wonen_aliases_resolve_to_registered_sources():
    zone_registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    for alias in WONEN_ALIASES:
        assert alias in zone_registry, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen ÉN de where-NAAM van die bron moet de selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert WONEN_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen wonen-NAAM: {where}"
        )


def test_wonen_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"wonen-bronnen zonder cache-twins: {freshly}"


def test_wonen_hergebruik_bestande_aliassen():
    """WN-01/02/05/06 (Landelijk gebied) en WN-11/12 (Stiltegebied /
    Aandachtsgebied) hergebruiken de fase-1-aliases bij dezelfde service+laag
    (fase-1-dedupregel): die moeten ongewijzigd in ZONE_SOURCES blijven."""
    zone_registry = json.loads((POC / "tracks" / "_zone-sources.json").read_text())
    for reused in ["landelijk_gebied", "stiltegebied", "aandachtsgebied_stiltegebied"]:
        assert reused in zone_registry, reused
