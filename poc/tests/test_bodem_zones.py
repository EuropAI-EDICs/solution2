# poc/tests/test_bodem_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_water_zones.py (taak 5), inclusief de twee daar gedocumenteerde
# deviaties op de brief-letterlijke testcode (zie .superpowers/sdd/task-5-report.md):
# 1. `data/sources.json` is een object met een "sources"-lijst (metadata-wrapper,
#    zie pipeline/geodata.py::load_sources); itereren over het top-level object
#    levert string-keys -> TypeError. Fix: ["sources"].
# 2. De cache-eis is verankerd op de bodem-alias-bronnen uit run.py::ZONE_SOURCES
#    i.p.v. de plan-letterlijke substring-scan: een scan op de matchwoorden
#    grondwater|stortplaats|rommelterrein raakt in de huidige registry ook de
#    bestaande arcgis-owbwp-grondwaterbeschermingszone-entry (AGOL-mirror, geen
#    cache-twins) — buiten deze taak, en tegen de harde git-regel "alléén de
#    nieuwe twins committen". run.py wordt tekstueel geparseerd (net als de
#    brief-test zelf) en niet geïmporteerd.
# Toegevoegde derde verankering (de matchwoorden uit de brief): elke bodem-bron
# moet een where-NAAM hebben die de selectieregel volgt, zodat een eventuele
# toekomstige surrogaatlaag zonder grondwater/stortplaats/rommelterrein-NAAM
# faalt. `grondverzet_gebied` is bewust géén alias: het probe-artifact
# (corpus/evidence-bodem.json) bevat geen Vergraving-/Storings-/Grondverzetgebied-
# aanwijzing (afdeling 3.4 grondverzet/rommelterrein is als rejected gemotiveerd).
BODEM_ALIASES = ["grondwater_beschermingszone", "gesloten_stortplaats"]
BODEM_MATCH = re.compile(r"grondwater|stortplaats|rommelterrein", re.IGNORECASE)


def _alias_source_ids():
    """Parse de bodem-alias -> sourceId-regels uit run.py::ZONE_SOURCES."""
    lines = (POC / "run.py").read_text().splitlines()
    ids = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"(\w+)":\s*\{\s*$', line)
        if m and m.group(1) in set(BODEM_ALIASES):
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', lines[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in BODEM_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_bodem_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in BODEM_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    for line in run_py.splitlines():
        m = re.match(r'\s*"(\w+)":\s*"([\w.-]+)",?\s*(?:#.*)?$', line)
        if m and m.group(1) in set(BODEM_ALIASES):
            assert m.group(2) in by_id, f"alias {m.group(1)} -> onbekende bron {m.group(2)}"
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen (zoals test_water_zones.py) én de where-NAAM van die bron moet de
    # selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert BODEM_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen grondwater/stortplaats/"
            f"rommelterrein-NAAM: {where}"
        )


def test_bodem_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"bodem-bronnen zonder cache-twins: {freshly}"
