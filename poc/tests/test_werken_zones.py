# poc/tests/test_werken_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_landbouw_zones.py (begrensde parse is standaard). De
# selectiefeiten zijn gedocumenteerd in .superpowers/sdd/task-2-report.md en
# het task-3-rapport:
# - zes nieuwe aliassen (uitbreiding bedrijventerrein, twee kantoor-knooppunten,
#   reductielocaties, gebiedstransformatie/herstructurering, detailhandel buiten
#   bestaand winkelgebied);
# - HERGEBRUIK (fase-1-dedupregel) van landelijk_gebied (WE-01/WE-02) en
#   stedelijk_gebied (WE-04) — fase-3-aliassen, hier niet opnieuw geëist;
# - LET OP: de NAAM 'Gebiedstransformatie of  herstructurering' bevat een
#   verordening-eigen dubbele spatie (getrouw in de where overgenomen);
# - de detailhandel-aanduiding dekt 1550.208 km2 (provincie minus bestaande
#   winkelgebieden): juridisch correct voor art. 9.20.
WERKEN_ALIASES = [
    "gebied_uitbreiding_bedrijventerrein",
    "kantoor_knooppunt_utrecht_centraal",
    "kantoor_knooppunt_leidsche_rijn_centrum",
    "reductielocaties",
    "gebiedstransformatie_herstructurering",
    "gebied_detailhandel_buiten_bestaand_winkelgebied",
]
WERKEN_MATCH = re.compile(
    r"bedrijventerrein|kantoor|reductielocaties|gebiedstransformatie|detailhandel",
    re.IGNORECASE,
)


def _alias_source_ids():
    """Parse de werken-alias -> sourceId-regels uit run.py::ZONE_SOURCES.

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
        if m and m.group(1) in set(WERKEN_ALIASES):
            assert i + 1 < len(block), f"alias {m.group(1)} aan het einde van ZONE_SOURCES"
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', block[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in WERKEN_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_werken_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in WERKEN_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen ÉN de where-NAAM van die bron moet de selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert WERKEN_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen werken-NAAM: {where}"
        )


def test_werken_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"werken-bronnen zonder cache-twins: {freshly}"


def test_werken_hergebruik_bestande_aliassen():
    """WE-01/WE-02 (Landelijk gebied) en WE-04 (Stedelijk gebied) hergebruiken
    de fase-3-wonen-aliases bij dezelfde service+laag (fase-1-dedupregel)."""
    run_py = (POC / "run.py").read_text()
    for reused in ["landelijk_gebied", "stedelijk_gebied"]:
        assert f'"{reused}": {{' in run_py, reused


def test_werken_dubbele_spatie_naam_verbatim():
    """De verordening-NAAM 'Gebiedstransformatie of  herstructurering' heeft een
    dubbele spatie — de where moet die letterlijk bevatten (anders 0 treffers)."""
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    src = next(s for s in registry if s["id"] == "agrest-ov-gebiedstransformatie-of-herstructurering")
    where = src["queryTemplateParams"]["where"]
    assert "Gebiedstransformatie of  herstructurering" in where, where
