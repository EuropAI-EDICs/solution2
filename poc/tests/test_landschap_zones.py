# poc/tests/test_landschap_zones.py
import json
import re
from pathlib import Path

POC = Path(__file__).resolve().parents[1]

# Spiegel van test_mobiliteit_zones.py / test_bodem_zones.py (fase 1/2). De
# selectieregel uit het plan (waterlinie|landgoed|aardkundig|cultuurhistorie|
# archeolog|kasteel|havezate, case-insensitive, over poc/data/agrest-namen.json)
# levert de treffers waarop deze aliases feitelijk zijn gebaseerd; de
# selectiefeiten zijn gedocumenteerd in .superpowers/sdd/task-6-report.md:
# 1. `landgoed`, `kasteel` en `havezate` hebben nul treffers — het zijn
#    deelgebiednamen uit de art.-7.8-opsomming (bijv. Landgoed Linschoten),
#    geen IMOW-NAAM's: gap, expliciet gerapporteerd, nooit surrogaat;
# 2. de Neder-Germaanse Limes-werkingsgebieden (LS-02/LS-03) matchen geen
#    plan-woord — de selectie is feitelijk uitgebreid met de letterlijke
#    verordeningtermen `werelderfgoed` en `neder-germaanse`;
# 3. de art.-7.11a-Landschap-umbrella (LS-05) matcht eveneens geen plan-woord
#    en is feitelijk toegevoegd (verordeningterm `landschap`);
# 4. de CHS-constituenten (Historische buitenplaatszone e.d., treffer
#    `cultuurhistorie`/`archeolog` op constituent-niveau) zijn opgegaan in de
#    live geverifieerde umbrella-NAAM en hebben bewust géén eigen alias; de
#    7.10-gateway (ALH-04) en de bordenketen (ALH-06..08) zijn gemotiveerd
#    onthouden zonder alias.
LANDSCHAP_ALIASES = [
    "unesco_werelderfgoed_hollandse_waterlinies",
    "unesco_werelderfgoed_neder_germaanse_limes_kernzone",
    "unesco_werelderfgoed_neder_germaanse_limes_bufferzone",
    "gebied_cultuurhistorische_hoofdstructuur",
    "landschap",
    "gebied_aardkundige_waarden",
]
# plan-woord `cultuurhistorie` dekt de bijvoeglijke naamvalsvariant in de NAAM
# (`Gebied cultuurhistorische hoofdstructuur`) niet — de match gebruikt de
# stam `cultuurhistori` die beide dekt.
LANDSCHAP_MATCH = re.compile(
    r"waterlinie|werelderfgoed|neder-germaanse|cultuurhistori|aardkundig|landschap",
    re.IGNORECASE,
)


def _alias_source_ids():
    """Parse de landschap-alias -> sourceId-regels uit run.py::ZONE_SOURCES."""
    lines = (POC / "run.py").read_text().splitlines()
    ids = {}
    for i, line in enumerate(lines):
        m = re.match(r'\s*"(\w+)":\s*\{\s*$', line)
        if m and m.group(1) in set(LANDSCHAP_ALIASES):
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', lines[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in LANDSCHAP_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_landschap_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in LANDSCHAP_ALIASES:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in registry}
    for line in run_py.splitlines():
        m = re.match(r'\s*"(\w+)":\s*"([\w.-]+)",?\s*(?:#.*)?$', line)
        if m and m.group(1) in set(LANDSCHAP_ALIASES):
            assert m.group(2) in by_id, f"alias {m.group(1)} -> onbekende bron {m.group(2)}"
    # sterke vorm: de dict-vorm van ZONE_SOURCES moet op een bestaand registry-id
    # wijzen (zoals de fase-1/2-zoneTests) ÉN de where-NAAM van die bron moet de
    # selectieregel-matchwoorden volgen.
    for alias, sid in _alias_source_ids().items():
        assert sid in by_id, f"alias {alias} -> onbekende bron {sid}"
        where = (by_id[sid].get("queryTemplateParams") or {}).get("where", "")
        assert LANDSCHAP_MATCH.search(where), (
            f"bron {sid} van alias {alias} selecteert geen waterlinie/werelderfgoed/"
            f"cultuurhistorie/aardkundig/landschap-NAAM: {where}"
        )


def test_landschap_cache_twins_exist():
    cached = {p.name for p in (POC / "data/cache").glob("*.geojson")}
    freshly = []
    for alias, sid in _alias_source_ids().items():
        for twin in (f"{sid}.28992.geojson", f"{sid}.4326.geojson"):
            if twin not in cached:
                freshly.append(f"{alias} -> {twin}")
    assert not freshly, f"landschap-bronnen zonder cache-twins: {freshly}"
