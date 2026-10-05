# poc/tests/test_mobiliteit_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_bodem_zones.py / test_water_zones.py (fase 1), inclusief de
# daar gedocumenteerde deviaties op de brief-letterlijke testcode:
# 1. `data/sources.json` is een object met een "sources"-lijst (metadata-wrapper,
#    zie pipeline/geodata.py::load_sources); itereren over het top-level object
#    levert string-keys -> TypeError. Fix: ["sources"].
# 2. De cache-eis is verankerd op de mobiliteit-alias-bronnen uit
#    run.py::ZONE_SOURCES i.p.v. een plan-letterlijke substring-scan over de
#    registry, zodat bestaande niet-gemobiliteerde entries (die toevallig een
#    selectiewoord in de where dragen) buiten deze taak blijven; run.py wordt
#    tekstueel geparseerd (net als de fase-1-tests zelf) en niet geïmporteerd.
# Derde verankering (de selectieregel-woorden): elke mobiliteit-bron moet een
# where-NAAM hebben die de selectieregel volgt, zodat een eventuele toekomstige
# surrogaatlaag zonder matchwoord-NAAM faalt. Selectiefeiten uit het probe-artifact
# poc/data/agrest-namen.json (122 distinct NAAM-waarden), gedocumenteerd in
# .superpowers/sdd/task-3-report.md:
# - geen enkele NAAM matcht `basisnet` (art. 4.67/4.68 zijn [Gereserveerd] in de
#   geconsolideerde tekst: geen zone, geen regel), `luchthaven` of `ontoereikend`
#   -> gap, expliciet gerapporteerd, nooit surrogaat;
# - de MO-05-werkingsgebied-NAAM is letterlijk `Luchtvaartterrein`: de selectie is
#   feitelijk uitgebreid met dat verordeningwoord (gemotiveerde afwijking op het
#   plan-woord `luchthaven`, dat nul treffers heeft);
# - treffers waarvan de regels als vergunnings-/meldingsketen gemotiveerd zijn
#   onthouden (Beperkingengebied beheer provinciale weg, Beperkingengebied vrij
#   zicht provinciale weg, Beperkingengebied vaarweg, Vaarweg in/niet in beheer)
#   en sub-zones van de umbrella-NAAM (Kernzone/Beschermingszone lokale spoorweg,
#   art. 4.46-umbrella live geverifieerd met 0,0000 km2 symdiff) hebben bewust
#   géén alias.
MOBILITEIT_ALIASES = [
    "beperkingengebied_bouwwerken_provinciale_weg",
    "geluidcontour_buiten_bebouwde_kom",
    "geluidcontour_binnen_bebouwde_kom",
    "beperkingengebied_lokale_spoorweg",
    "luchtvaartterrein",
]
MOBILITEIT_MATCH = re.compile(
    r"geluid|luchtvaartterrein|provinciale weg|spoor", re.IGNORECASE
)


def _alias_source_ids():
    """Parse de mobiliteit-alias -> sourceId-regels uit run.py::ZONE_SOURCES."""
    lines = (POC / "run.py").read_text().splitlines()
    ids = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"(\w+)":\s*\{\s*$', line)
        if m and m.group(1) in set(MOBILITEIT_ALIASES):
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', lines[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in MOBILITEIT_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_mobiliteit_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in MOBILITEIT_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    for line in run_py.splitlines():
        m = re.match(r'\s*"(\w+)":\s*"([\w.-]+)",?\s*(?:#.*)?$', line)
        if m and m.group(1) in set(MOBILITEIT_ALIASES):
            assert m.group(2) in by_id, f"alias {m.group(1)} -> onbekende bron {m.group(2)}"
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen (zoals de fase-1-zoneTests) ÉN de where-NAAM van die bron moet de
    # selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert MOBILITEIT_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen geluid/provinciale weg/"
            f"spoor/luchtvaartterrein-NAAM: {where}"
        )


def test_mobiliteit_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"mobiliteit-bronnen zonder cache-twins: {freshly}"
