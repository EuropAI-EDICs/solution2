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
    """Parse de landbouw-alias -> sourceId-regels uit run.py::ZONE_SOURCES.

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
        if m and m.group(1) in set(LANDBOUW_ALIASES):
            assert i + 1 < len(block), f"alias {m.group(1)} aan het einde van ZONE_SOURCES"
            m2 = re.match(r'\s*"sourceId":\s*"([\w.-]+)"', block[i + 1])
            assert m2, f"alias {m.group(1)} zonder sourceId-regel in ZONE_SOURCES"
            ids[m.group(1)] = m2.group(1)
    missing = [a for a in LANDBOUW_ALIASES if a not in ids]
    assert not missing, f"zone-alias(es) ontbreken in run.py ZONE_SOURCES: {missing}"
    return ids


def test_landbouw_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in LANDBOUW_ALIASES:
        assert f'"{alias}"' in run_py, alias
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
