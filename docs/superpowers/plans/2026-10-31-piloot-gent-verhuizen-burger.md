# Piloot Gent — pakket `gent-verhuizen-burger` Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tweede levensgebeurtenis-pakket `gent-verhuizen-burger` (GT-VERH-01 "Ik verhuis naar Gent") naast `gent-mobiliteit-ondernemer`: bewonersvergunning-transactie + afval/parkeren/LEZ-info voor burgers, gevoed door echte Gentse open data, met een nieuwe generieke `dataChecks`-engine-capaciteit en een levensgebeurtenis-dropdown in het bestaande Gent-simulatietab.

**Architecture:** Configuratie is data: nieuw pakket onder `poc-gent/packages/`, engine-uitbreidingen zijn klein en gericht (`dataChecks` naast `gisChecks`, per-pakket backoffice-contract, per-pakket KPI-drempels, generieke contextzin). De simulatie parametriseert `build_gent(package_id)` en wisselt in de template de dataset via een dropdown. Runs blijven offline en deterministisch; alle echte brondata wordt éénmalig gecached onder `fixtures/source/`.

**Tech Stack:** Python 3 stdlib-only (poc-gent), pytest/unittest onder `nldt/.venv`, vanilla-JS simulatietemplate (template.html), data.stad.gent ODS-API voor de broncache.

**Spec:** [`docs/superpowers/specs/2026-10-31-piloot-gent-verhuizen-burger-design.md`](../specs/2026-10-31-piloot-gent-verhuizen-burger-design.md)

## Global Constraints

- Testcommando poc-gent: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`; simulation: `cd simulation && ../nldt/.venv/bin/python -m pytest -q`. Losse tests ook met `python3` (stdlib-only), maar de suite draait onder de venv.
- poc-gent engine blijft stdlib-only; geen nieuwe dependencies.
- Runs zijn offline en deterministisch: netwerkaanraking uitsluitend in `fetch_sources.py` (cache-bouw); geen "nu"-afhankelijke waarden in de afvalcache.
- Alle nieuwe teksten in het pakket/pipeline zijn Nederlands; EN gebeurt uitsluitend in `simulation/vertaal_gent.py` (volledigheidstest dwingt af).
- Bestaand gedrag van `gent-mobiliteit-ondernemer` blijft ongewijzigd: bestaande testsuite moet zonder aanpassingen groen blijven (alleen expliciet benoemde uitzonderingen in dit plan).
- Commitstijl: `feat(poc-gent): …` / `test(poc-gent): …` / `feat(simulation): …`, Nederlands onderwerp.
- Nieuwe datasets (allen Modellicentie Gratis Hergebruik, data.stad.gent): `bewonerszones-gent`, `parkeertariefzones-gent`, `afvalophaalkalender-ivago-woongebied-gent-2026-2027`.
- Zone-uitkomsten van fixture-adressen worden vastgelegd tegen de échte lagen via `python3 fetch_sources.py --check` (F1.5-doctrine); als een adres niet de bedoelde combinatie oplevert, alternatief kiezen en persona's meenemen (gedocumenteerd per taak).

---

### Task 1: Nieuwe zone-lagen + kandidaat-adressen in de broncache

**Files:**
- Modify: `poc-gent/fetch_sources.py` (LAYERS, ADRESSEN)
- Modify: `poc-gent/fixtures/gis-zones.geojson`, `poc-gent/fixtures/addresses.json`, `poc-gent/fixtures/source/{bewonerszones-gent,parkeertariefzones-gent}.json`, `poc-gent/fixtures/source/source.meta.json` (gegenereerd)
- Test: `poc-gent/tests/test_gis_zones.py`

**Interfaces:**
- Produces: GIS-lagen `gent-bewonerszone` (dataset `bewonerszones-gent`) en `gent-parkeertariefzone` (dataset `parkeertariefzones-gent`) in `fixtures/gis-zones.geojson` met `properties.layer`/`properties.versie`; adressen `"Nederkouter 1, Gent"` en `"Sleepstraat 1, Gent"` in `fixtures/addresses.json`. Later taken matchen hierop via `gis_zones.zone_result(zones, "<laag>", lon, lat)`.

- [ ] **Step 1: Voeg de twee lagen toe aan LAYERS in fetch_sources.py** (na het `gent-autovrij`-blok, zelfde vorm):

```python
    "gent-bewonerszone": {
        "dataset_id": "bewonerszones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/bewonerszones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/bewonerszones-gent",
        "url_portal": f"{PORTAL}/explore/assets/bewonerszones-gent",
        "soort": "export",
        "filter": None,
    },
    "gent-parkeertariefzone": {
        "dataset_id": "parkeertariefzones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/parkeertariefzones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/parkeertariefzones-gent",
        "url_portal": f"{PORTAL}/explore/assets/parkeertariefzones-gent",
        "soort": "export",
        "filter": None,
    },
```

- [ ] **Step 2: Breid ADRESSEN uit met twee kandidaat-adressen** (fallback-combinaties voor de burger-golden set):

```python
ADRESSEN = [
    "Korenmarkt 1, Gent",                       # binnen LEZ én autovrij gebied
    "Sint-Pietersplein 1, Gent",                # binnen LEZ, buiten autovrij gebied
    "Koningin Maria Hendrikaplein 1, Gent",     # buiten beide (station Gent-Sint-Pieters)
    "Veldstraat 1, Gent",                       # centrum, binnen beide
    "Nederkouter 1, Gent",                      # burgerkandidaat: binnen singels/LEZ
    "Sleepstraat 1, Gent",                      # burgerkandidaat: buiten tariefzone centroids, binnen LEZ
]
```

- [ ] **Step 3: Bouw de cache (netwerk)**: `cd poc-gent && python3 fetch_sources.py` — herschrijft gis-zones.geojson (4 lagen), source.meta.json en de twee nieuwe ruwe bronbestanden. Verwacht: print per laag met `featuresNaFilter` > 0.
- [ ] **Step 4: Geocode de nieuwe adressen (netwerk)**: `python3 fetch_sources.py --geocode` — verwacht `6/6 adressen vernieuwd` gevolgd door het zone-rapport. Bewaar dit rapport (het pinnt de golden set in Taak 7).
- [ ] **Step 5: Schrijf de zone-pinningtest** — voeg aan `tests/test_gis_zones.py` toe (verwachtingen bijsturen op het --check-rapport uit Step 4; de structuur en laagnamen zijn het contract):

```python
def test_nieuwe_burgerlagen_bestaan_en_dekken_adressen():
    zones = gis_zones.load_zones(POC_ROOT)
    assert "gent-bewonerszone" in zones and zones["gent-bewonerszone"]
    assert "gent-parkeertariefzone" in zones and zones["gent-parkeertariefzone"]
    # gepind tegen het --check-rapport (echte lagen, F1.5-doctrine):
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Veldstraat 1, Gent")
    assert gis_zones.zone_result(zones, "gent-bewonerszone", lon, lat) == "in"
    assert gis_zones.zone_result(zones, "gent-parkeertariefzone", lon, lat) == "in"
    assert gis_zones.zone_result(zones, "gent-lez", lon, lat) == "in"
```

- [ ] **Step 6: Run de tests**: `../nldt/.venv/bin/python -m pytest tests/test_gis_zones.py -q` → PASS (plus volledige suite groen: `../nldt/.venv/bin/python -m pytest tests -q`).
- [ ] **Step 7: Commit**: `git add poc-gent/fetch_sources.py poc-gent/fixtures/gis-zones.geojson poc-gent/fixtures/addresses.json poc-gent/fixtures/source/bewonerszones-gent.json poc-gent/fixtures/source/parkeertariefzones-gent.json poc-gent/fixtures/source/source.meta.json poc-gent/tests/test_gis_zones.py && git commit -m "feat(poc-gent): echte Gentse bewonerszones en parkeertariefzones in de broncache — nieuwe lagen plus burger-kandidaatadressen"`

---

### Task 2: IVAGO-afvalkalendercache (dataChecks-databron)

**Files:**
- Modify: `poc-gent/fetch_sources.py` (nieuwe functies + `--afval`-vlag)
- Create: `poc-gent/fixtures/source/afvalkalender.json` (gegenereerd)
- Test: `poc-gent/tests/test_fetch_sources.py`

**Interfaces:**
- Produces: `fixtures/source/afvalkalender.json` met vorm `{"dataset": "ivago-ophaalkalender", "versie": "<dataset-id> (gewijzigd <date>)", "straten": {"<genormaliseerde straat>": {"afvalRest": {"dag": "dinsdag", "eerste": "2026-10-06"}, …}}}`; hulpfuncties `straatnaam_norm(adres)` en `vatten_afval(rijen)` in fetch_sources.py; `source.meta.json["bronnen"]["ivago-ophaalkalender"]`. Taak 3 leest dit formaat via `data_lookups.laad_kalender`.

- [ ] **Step 1: Controleer eerst de veldnamen van de dataset** (netwerk): `python3 -c "import json,urllib.request; r=json.load(urllib.request.urlopen('https://data.stad.gent/api/explore/v2.1/catalog/datasets/afvalophaalkalender-ivago-woongebied-gent-2026-2027/records?limit=1')); print(json.dumps(r['results'][0], ensure_ascii=False, indent=1))"`. Verwacht velden `straatnaam`, `fracties`, `datum` (kalenderjaar 2026/2027). Wijkt een naam af (bijv. `straat`), pas dan in Step 2 alleen de constante `IVAGO_VELDEN` aan.
- [ ] **Step 2: Schrijf de mislukkende test** in `tests/test_fetch_sources.py`:

```python
def test_straatnaam_norm():
    import fetch_sources as fs
    assert fs.straatnaam_norm("Veldstraat 1, Gent") == "veldstraat"
    assert fs.straatnaam_norm("Koningin Maria Hendrikaplein 12 bus 3, Gent") == "koningin maria hendrikaplein"


def test_vatten_afval_deterministisch():
    import fetch_sources as fs
    rijen = [{"fracties": "PMD", "datum": "2026-10-06"},
             {"fracties": "PMD", "datum": "2026-10-13"},
             {"fracties": "Restafval", "datum": "2026-10-07"},
             {"fracties": "Glas, papier", "datum": "2026-10-08"}]
    uit = fs.vatten_afval(rijen)
    assert uit["afvalPmd"] == {"dag": "dinsdag", "eerste": "2026-10-06"}
    assert uit["afvalRest"]["dag"] == "woensdag"
    assert uit["afvalGlas"]["eerste"] == "2026-10-08" and uit["afvalPapier"]["eerste"] == "2026-10-08"
    assert "afvalGft" not in uit or uit["afvalGft"]  # GFT optioneel aanwezig
```

- [ ] **Step 3: Run**: `../nldt/.venv/bin/python -m pytest tests/test_fetch_sources.py -q` → FAIL (`straatnaam_norm` bestaat niet).
- [ ] **Step 4: Implementeer in fetch_sources.py** (bij de andere normaliseer-hulpfuncties; imports `re`, `unicodedata` bovenaan aanvullen):

```python
IVAGO_DATASET = "afvalophaalkalender-ivago-woongebied-gent-2026-2027"
IVAGO_VELDEN = {"straat": "straatnaam", "fractie": "fracties", "datum": "datum"}
IVAGO_FRACTIES = {"afvalRest": ("restafval",), "afvalPmd": ("pmd",), "afvalGlas": ("glas",),
                  "afvalPapier": ("papier",), "afvalGft": ("gft",)}
DAG_NAMEN = ("maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag")


def straatnaam_norm(adres: str) -> str:
    """'Veldstraat 1, Gent' → 'veldstraat': huisnummer/bus en gemeente eraf,
    diakritiek gestript, kleine letters (cache-sleutel voor de afvalkalender)."""
    deel = adres.split(",")[0]
    zonder_nummer = re.sub(r"\s+\d+.*$", "", deel)
    nkfd = unicodedata.normalize("NFKD", zonder_nummer)
    ascii_ = "".join(c for c in nkfd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def _norm_datum(raw: str) -> str | None:
    raw = raw.strip()
    for patroon in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, patroon).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def vatten_afval(rijen: list[dict]) -> dict:
    """Per fractie: weekdag('n) + eerste datum. Deterministisch: alleen uit de
    rijen zelf — geen 'nu'-berekening (replay-stabiliteit)."""
    uit: dict[str, dict] = {}
    for rij in rijen:
        datum = _norm_datum(str(rij.get(IVAGO_VELDEN["datum"], "")))
        if not datum:
            continue
        fracties = str(rij.get(IVAGO_VELDEN["fractie"], "")).lower()
        weekdag = DAG_NAMEN[datetime.strptime(datum, "%Y-%m-%d").weekday()]
        for slot, sleutels in IVAGO_FRACTIES.items():
            if any(s in fracties for s in sleutels):
                info = uit.setdefault(slot, {"eerste": datum, "dagen": []})
                info["eerste"] = min(info["eerste"], datum)
                if weekdag not in info["dagen"]:
                    info["dagen"].append(weekdag)
    return {slot: {"dag": "/".join(sorted(info["dagen"], key=DAG_NAMEN.index)),
                   "eerste": info["eerste"]}
            for slot, info in uit.items()}


def haal_afvalkalender(poc_root: Path) -> dict:
    """Per straat uit addresses.json de IVAGO-rijen ophalen (where-query, klein
    en deterministisch) en vatten naar fixtures/source/afvalkalender.json."""
    adressen = json.loads((poc_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    kal_meta = _fetch_json(f"{PORTAL}/api/explore/v2.1/catalog/datasets/{IVAGO_DATASET}")
    gewijzigd = ((kal_meta.get("metas") or {}).get("default") or {}).get("modified")
    straten: dict[str, dict] = {}
    velden = IVAGO_VELDEN
    for adres in adressen:
        straat = straatnaam_norm(adres)
        if straat in straten:
            continue
        url = (f"{PORTAL}/api/explore/v2.1/catalog/datasets/{IVAGO_DATASET}/records"
               f"?limit=-1&where={velden['straat']}%3D%22{adres.split(',')[0].rsplit(' ', 1)[0]}%22")
        rijen = _fetch_json(url).get("results", [])
        if rijen:
            straten[straat] = vatten_afval(rijen)
        time.sleep(0.2)
    document = {"dataset": "ivago-ophaalkalender",
                "versie": f"{IVAGO_DATASET} (gewijzigd {str(gewijzigd)[:10]})",
                "straten": straten}
    (SOURCE_DIR / "afvalkalender.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"versie": document["versie"], "straten": len(straten), "aantalAdressen": len(adressen)}
```

Fix-instructie uit eerdere versie is vervallen: de code hierboven is de definitieve versie (één `ascii_ = "".join(...)`-regel, geen ongebruikte `meta`-variabele).

- [ ] **Step 5: Koppel de CLI**: in `main()` na `args = ap.parse_args()` een vlag `--afval` toevoegen (zelfde patroon als `--bronnen`):

```python
    ap.add_argument("--afval", action="store_true",
                    help="bouw de IVAGO-afvalkalender-cache per fixture-straat — netwerk")
```

en in `main()` vóór het wegschrijven van source.meta.json:

```python
    if args.afval:
        afval = haal_afvalkalender(POC_ROOT)
        meta_document["bronnen"]["ivago-ophaalkalender"] = {
            "cache": "fixtures/source/afvalkalender.json", **afval,
            "titel": "Afvalophaalkalender IVAGO woongebied Gent 2026-2027",
            "licentie": "Modellicentie Gratis Hergebruik",
            "url": f"{PORTAL}/explore/assets/{IVAGO_DATASET}",
        }
        print(f"afval: {afval['straten']} straten ({afval['versie']})")
```

- [ ] **Step 6: Run de test uit Step 2** → PASS. Bouw daarna de cache (netwerk): `python3 fetch_sources.py --afval` → verwacht `afval: N straten …` met N ≥ 4.
- [ ] **Step 7: Controleer de cache**: `python3 -c "import json; d=json.load(open('fixtures/source/afvalkalender.json')); print(d['versie']); print({k: sorted(v) for k,v in d['straten'].items()})"` — elke fixture-straat (of expliciet afwezig) en per straat fractie-sleutels.
- [ ] **Step 8: Commit**: `git add poc-gent/fetch_sources.py poc-gent/fixtures/source/afvalkalender.json poc-gent/fixtures/source/source.meta.json poc-gent/tests/test_fetch_sources.py && git commit -m "feat(poc-gent): IVAGO-afvalkalender als gecachte dataChecks-bron — deterministisch per fixture-straat gevat"`

---

### Task 3: `dataChecks`-engine (adapter + catalog + context + gates + pipeline)

**Files:**
- Create: `poc-gent/adapters/data_lookups.py`
- Modify: `poc-gent/core/catalog.py` (validatie + dataset-register), `poc-gent/core/context.py` (build, summary), `poc-gent/core/gates.py` (confirm_h1), `poc-gent/core/pipeline.py` (data_check-event + stap)
- Test: `poc-gent/tests/test_data_lookups.py`, `poc-gent/tests/test_catalog.py`, `poc-gent/tests/test_context.py`

**Interfaces:**
- Produces: `data_lookups.apply_checks(manifest, context, herkomst, poc_root, suffix="") -> None` (mutatie, zelfde contract als `gis_zones.apply_checks`); `data_lookups.laad_kalender(poc_root) -> dict`. Manifestveld `dataChecks`: `[{"id", "dataset", "input", "outputs": [slotnamen], "unknownPolicy": "escalate"|"fallback"}]` (default escalate). `texts.contextZin` (optioneel sjabloon met `{slot}`-plaatshouders; default reproduces de huidige zin). Context-slots uit dataChecks zijn matchbaar in beslistabel-`when`.

- [ ] **Step 1: Schrijf de mislukkende adaptertests** — nieuw bestand `tests/test_data_lookups.py`:

```python
"""dataChecks (F1-burger): dataset-lookups naast GIS-zonechecks, met
fallback/escalate-beleid en herkomstlabels (DATA-01)."""
import json
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(POC_ROOT))

from adapters import data_lookups  # noqa: E402


def _cache(tmp_path, straten=None):
    (tmp_path / "fixtures" / "source").mkdir(parents=True)
    document = {"dataset": "ivago-ophaalkalender", "versie": "test (2026-2027)",
                "straten": straten if straten is not None else
                {"veldstraat": {"afvalRest": {"dag": "woensdag", "eerste": "2026-10-07"},
                                 "afvalPmd": {"dag": "dinsdag", "eerste": "2026-10-06"}}}}
    (tmp_path / "fixtures" / "source" / "afvalkalender.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8")


CHECK = {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
         "outputs": ["afvalRest", "afvalPmd"], "unknownPolicy": "fallback"}


def test_bekende_straat_vult_outputs_met_herkomst(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {"address": "Veldstraat 1, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert ctx["afvalPmd"] == "dinsdag"
    assert herkomst["afvalPmd"] == {"label": "afgeleid", "bron": "dataset:ivago-ophaalkalender (test (2026-2027))"}


def test_onbekende_straat_fallback(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {"address": "Onbekendelaan 9, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert ctx["afvalRest"] == "onbekend"
    assert "straat niet in cache" in herkomst["afvalRest"]["bron"]


def test_onbekende_straat_escalate_waarde(tmp_path):
    _cache(tmp_path)
    check = {**CHECK, "unknownPolicy": "escalate"}
    ctx, herkomst = {"address": "Onbekendelaan 9, Gent"}, {}
    data_lookups.apply_checks({"dataChecks": [check]}, ctx, herkomst, tmp_path)
    assert ctx["afvalPmd"] == "onbekend-straat"


def test_zonder_input_slot_geen_uitvoer(tmp_path):
    _cache(tmp_path)
    ctx, herkomst = {}, {}
    data_lookups.apply_checks({"dataChecks": [CHECK]}, ctx, herkomst, tmp_path)
    assert "afvalRest" not in ctx
```

- [ ] **Step 2: Run** → FAIL (module bestaat niet).
- [ ] **Step 3: Implementeer `adapters/data_lookups.py`**:

```python
"""Dataset-lookups (F1-burger): niet-ruimtelijke open data als bron naast de
GIS-zonechecks. Productie vervangt de cache door de interne diensten van Stad
Gent; de adapter-interface blijft gelijk (DATA-01: herkomst per uitkomst)."""

from __future__ import annotations

import json
from pathlib import Path


def laad_kalender(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "source" / "afvalkalender.json")
                      .read_text(encoding="utf-8"))


def _straat_van_adres(adres: str, poc_root: Path) -> str | None:
    import re
    import unicodedata

    deel = adres.split(",")[0]
    zonder_nummer = re.sub(r"\s+\d+.*$", "", deel)
    nkfd = unicodedata.normalize("NFKD", zonder_nummer)
    ascii_ = "".join(c for c in nkfd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def apply_checks(manifest: dict, context: dict, herkomst: dict, poc_root: Path,
                 suffix: str = "") -> None:
    """Voer alle dataChecks uit op hun input-slot. Onbekende straat volgt het
    per-check beleid: fallback (outputs 'onbekend', neutrale info-tekst) of
    escalate (outputs 'onbekend-straat' → geen regel vuurt → Gentinfo)."""
    kalenders = {"ivago-ophaalkalender": laad_kalender}
    for check in manifest.get("dataChecks", []):
        adres = context.get(check["input"])
        if adres is None:
            continue
        laad = kalenders[check["dataset"]]
        kalender = laad(poc_root)
        straat = _straat_van_adres(adres, poc_root)
        gevonden = kalender.get("straten", {}).get(straat)
        for out in check["outputs"]:
            if gevonden and out in gevonden:
                context[out] = gevonden[out]["dag"]
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} ({kalender['versie']}{suffix})"}
            elif check.get("unknownPolicy", "escalate") == "fallback":
                context[out] = "onbekend"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} (straat niet in cache{suffix})"}
            else:
                context[out] = "onbekend-straat"
                herkomst[out] = {"label": "afgeleid",
                                 "bron": f"dataset:{check['dataset']} (straat niet in cache{suffix})"}
```

- [ ] **Step 4: Run de adaptertests** → PASS.
- [ ] **Step 5: Catalog-validatie** — voeg in `core/catalog.py::_validate` na het gisChecks-blok toe:

```python
    for check in manifest.get("dataChecks", []):
        for field_name in ("id", "dataset", "input", "outputs"):
            if field_name not in check or not check[field_name]:
                raise PackageError(f"dataCheck mist veld '{field_name}': {check}")
        if check["input"] not in slots:
            raise PackageError(f"dataCheck '{check['id']}': onbekende input-slot '{check['input']}'")
        if check.get("unknownPolicy", "escalate") not in ("escalate", "fallback"):
            raise PackageError(f"dataCheck '{check['id']}': ongeldig unknownPolicy (escalate|fallback)")
        for out in check["outputs"]:
            if out in slots or out in outputs or out in data_outputs:
                raise PackageError(f"dataCheck '{check['id']}': output-botsing op '{out}'")
            data_outputs.add(out)
```

met `data_outputs: set = set()` direct boven het gisChecks-blok, en in de when-sleutelcontrole van regels `key not in slots and key not in outputs` uitbreiden naar `key not in slots and key not in outputs and key not in data_outputs`. Voeg daarnaast in `load_package` een registercontrole toe (na `_validate(manifest, tables)`):

```python
    register_pad = poc_root / "fixtures" / "source" / "source.meta.json"
    if manifest.get("dataChecks"):
        bronnen = json.loads(register_pad.read_text(encoding="utf-8")).get("bronnen", {})
        for check in manifest["dataChecks"]:
            if check["dataset"] not in bronnen:
                raise PackageError(f"dataCheck '{check['id']}': dataset '{check['dataset']}' "
                                   "staat niet in de broncatalogus (fixtures/source/source.meta.json)")
```

- [ ] **Step 6: Catalog-tests** — voeg aan `tests/test_catalog.py` toe (spiegel bestaande kapotte-variant patronen; het hulpbouwschrijfpad daar schrijft manifest+tabellen naar `tmp_path`):

```python
def test_datachecks_valideren(tmp_path, schrijf_pakket):
    basis = schrijf_pakket(tmp_path)
    bronnen = {"bronnen": {"ivago-ophaalkalender": {"versie": "x"}}}
    (tmp_path / "fixtures" / "source").mkdir(parents=True)
    (tmp_path / "fixtures" / "source" / "source.meta.json").write_text(json.dumps(bronnen), encoding="utf-8")

    goed = {**basis, "dataChecks": [{"id": "afvalkalender", "dataset": "ivago-ophaalkalender",
                                     "input": "address", "outputs": ["afvalRest"], "unknownPolicy": "fallback"}]}
    schrijf_pakket(tmp_path, goed)
    catalog.load_package(tmp_path, goed["packageId"])  # laadt zonder fout

    for slecht in (
        {"dataChecks": [{"id": "x", "dataset": "ivago-ophaalkalender", "input": "address", "outputs": []}]},
        {"dataChecks": [{"id": "x", "dataset": "ivago-ophaalkalender", "input": "stad", "outputs": ["a"]}]},
        {"dataChecks": [{"id": "x", "dataset": "ivago-ophaalkalender", "input": "address", "outputs": ["applicantType"]}]},
        {"dataChecks": [{"id": "x", "dataset": "ivago-ophaalkalender", "input": "address", "outputs": ["a"], "unknownPolicy": "boe"}]},
        {"dataChecks": [{"id": "x", "dataset": "onbekende-dataset", "input": "address", "outputs": ["a"]}]},
    ):
        with pytest.raises(catalog.PackageError):
            schrijf_pakket(tmp_path, {**basis, **slecht})
            catalog.load_package(tmp_path, basis["packageId"])
```

(Pas het hulpje `schrijf_pakket` aan de bestaande teststructuur aan: daar staat al een builder voor geldige pakketten — hergebruik die; het registerbestand hoeft er alléén wanneer `dataChecks` gezet is.)

- [ ] **Step 7: context.build + gates.confirm_h1 + summary** — in `core/context.py`: import `data_lookups`, voer na het GIS-blok `data_lookups.apply_checks(manifest, context, herkomst, poc_root)` uit; breid `summary` uit met een dataChecks-lus over `check["outputs"]` (zelfde regels-vorm als gisChecks) en maak de zin configureerbaar:

```python
DEFAULT_ZIN = "U bent {applicantType} en wilt: {activity}. Adres: {address}."


class _Onbekend(dict):
    def __missing__(self, key):
        return "onbekend"


def summary(manifest: dict, context: dict, herkomst: dict) -> dict:
    regels = []
    for slot in manifest["contextSchema"]["slots"]:
        if slot in context:
            regels.append({"feit": slot, "waarde": context[slot], **herkomst[slot]})
    for check in manifest.get("gisChecks", []):
        out = check["output"]
        if out in context:
            regels.append({"feit": out, "waarde": context[out], **herkomst[out]})
    for check in manifest.get("dataChecks", []):
        for out in check["outputs"]:
            if out in context:
                regels.append({"feit": out, "waarde": context[out], **herkomst[out]})
    zin = manifest.get("texts", {}).get("contextZin") or DEFAULT_ZIN
    tekst = zin.format_map(_Onbekend(context))
    return {"tekst": tekst, "regels": regels}
```

In `core/gates.py::confirm_h1` na de GIS-herhaling: `data_lookups.apply_checks(manifest, context, herkomst, poc_root, suffix=", na correctie")` (import bij de andere adapters).

- [ ] **Step 8: pipeline** — na het `gis_check`-event-blok in `run_replay`:

```python
    for check in pkg.manifest.get("dataChecks", []):
        events_mod.emit(events, "data_check",
                        {"id": check["id"], "dataset": check["dataset"],
                         "resultaten": {out: ctx.get(out) for out in check["outputs"]}})
```

en ná de `gis-zonecheck`-stap in `steps` (alleen wanneer het pakket dataChecks heeft, zodat het ondernemerspakket byte-identiek blijft):

```python
    if pkg.manifest.get("dataChecks"):
        steps.append({"stepId": "data-lookup", "title": "We halen de afvalkalender van je straat op",
                      "actor": "agent", "genAiTestPoint": "—",
                      "dataUsed": [f"{out}={ctx.get(out)}"
                                   for c in pkg.manifest["dataChecks"] for out in c["outputs"]],
                      "consent": "n.v.t.", "handover": None, "kpiEvents": [],
                      "prov": {"sources": ["dataset:ivago-ophaalkalender (open data Stad Gent/IVAGO)"]}})
```

LET OP: `steps` wordt in `run_replay` als letterale lijst gebouwd met de vaste volgorde intake → context-vragen → gis → h1 → routing; voeg de data-lookup-stap in die literal in tussen de gis-stap en de h1-stap met de conditie eromheen (`*( [ ... ] ) if pkg.manifest.get("dataChecks") else []` uitgepakkt in een `steps = [...]; if dataChecks: steps.insert(3, {...})`-vorm — kies de insert-vorm, index 3).

- [ ] **Step 9: context-tests** — voeg aan `tests/test_context.py` toe: `summary` met een manifest mét `texts.contextZin` "U bent {applicantType} en verhuist naar: {address}." geeft die zin; zonder contextZin geeft het oudere standaardpatroon exact `U bent burger en wilt: onbekend. Adres: X.` voor een context zonder `activity`; regels bevatten dataCheck-outputs.
- [ ] **Step 10: Volledige suite**: `../nldt/.venv/bin/python -m pytest tests -q` → alles PASS (ondernemerspakket ongewijzigd: geen dataChecks → zelfde stappen/events).
- [ ] **Step 11: Commit**: `git add -A poc-gent/adapters/data_lookups.py poc-gent/core/catalog.py poc-gent/core/context.py poc-gent/core/gates.py poc-gent/core/pipeline.py poc-gent/tests/ && git commit -m "feat(poc-gent): generieke dataChecks naast gisChecks — dataset-lookups mét herkomst, unknownPolicy en contextZin-sjabloon"`

---

### Task 4: Backoffice-contract per pakket

**Files:**
- Modify: `poc-gent/adapters/backoffice_mock.py`, `poc-gent/core/submit.py`, `poc-gent/core/pipeline.py`, `poc-gent/core/catalog.py`
- Test: `poc-gent/tests/test_submit.py`

**Interfaces:**
- Produces: `submit.contract_van(manifest) -> str` (default `"district09-vergunningen"`); `submit.dien_in(manifest, package_id, persona_id, formulieren)` (nieuwe eerste parameter). Manifestveld `submission: {"contract": "<id>"}`. Backoffice-mock kent `district09-parkeervergunningen`.

- [ ] **Step 1: Mislukkende test** in `tests/test_submit.py`:

```python
def test_contract_uit_manifest():
    manifest = {"submission": {"contract": "district09-parkeervergunningen"}}
    resultaat = submit.dien_in(manifest, "gent-verhuizen-burger", "lisa",
                               [{"service": "bewonerskaart", "velden": []}])
    assert resultaat[0]["referentie"].startswith("GENT-")
    assert resultaat[0]["status"] == "geaccepteerd"


def test_contract_default_blijft_vergunningen():
    assert submit.contract_van({}) == "district09-vergunningen"
    assert submit.contract_van({"submission": {"contract": "district09-parkeervergunningen"}}) == "district09-parkeervergunningen"
```

- [ ] **Step 2: Run** → FAIL (signature).
- [ ] **Step 3: Implementeer** — `backoffice_mock.py`: `_CONTRACTEN = {"district09-vergunningen", "district09-parkeervergunningen"}`. `submit.py`:

```python
BACKOFFICE_CONTRACT = "district09-vergunningen"


def contract_van(manifest: dict) -> str:
    return manifest.get("submission", {}).get("contract") or BACKOFFICE_CONTRACT


def dien_in(manifest: dict, package_id: str, persona_id: str, formulieren: list[dict]) -> list[dict]:
    contract = contract_van(manifest)
    resultaten = []
    for formulier in formulieren:
        voorbereid = bereid_voor(package_id, persona_id, formulier["service"], formulier)
        ontvangst = backoffice_mock.dien_in(contract, voorbereid["lading"],
                                            voorbereid["idempotentie_sleutel"])
        resultaten.append({"service": formulier["service"], "referentie": ontvangst["referentie"],
                           "status": ontvangst["status"]})
    return resultaten
```

`pipeline.py`: aanroep wordt `submit.dien_in(pkg.manifest, package_id, persona_id, formulieren)`; de ontvangstbewijs-stap krijgt `"prov": {"sources": [f"{submit.contract_van(pkg.manifest)} (mock v1, INT-03)"]}`. `catalog.py::_validate`: `if "submission" in manifest and not str(manifest["submission"].get("contract", "")).strip(): raise PackageError("manifest.submission: niet-lege 'contract' vereist")`.
- [ ] **Step 4: Run suite** → PASS (geen enkele test assert de oude prov-string; gecontroleerd).
- [ ] **Step 5: Commit**: `git commit -am "feat(poc-gent): backoffice-contract per pakket — submission.contract in het manifest, parkeervergunningen-contract in de mock"` (alleen poc-gent-bestanden stagen).

---

### Task 5: Catalog: lege documentenlijst + KPI-drempels per pakket

**Files:**
- Modify: `poc-gent/core/catalog.py`, `poc-gent/core/kpis.py`
- Test: `poc-gent/tests/test_catalog.py`, `poc-gent/tests/test_kpis.py`

**Interfaces:**
- Produces: inzendingsdiensten mogen `"documenten": []` hebben (sleutel verplicht); `kpis.drempels(manifest) -> dict` (override via `manifest["kpiDrempels"]`, keys beperkt tot de bekende).

- [ ] **Step 1: Mislukkende tests**: in `test_catalog.py` een variant met `"documenten": []` op een inzendingsdienst laadt; een variant zonder `documenten`-sleutel faalt met PackageError. In `test_kpis.py`:

```python
def test_drempels_per_pakket():
    manifest = {"kpiDrempels": {"kpi01_min": 80.0}}
    d = kpis.drempels(manifest)
    assert d["kpi01_min"] == 80.0 and d["kpi02_min"] == 100.0
    assert kpis.drempels({}) == kpis.DREMPELS
```

- [ ] **Step 2: Implementeer** — catalog: `if service.get("type") == "inzending" and "documenten" not in service: raise PackageError(f"dienst '{service_id}': inzending zonder documenten-eisen (gebruik [] als authentieke bronnen volstaan)")`. kpis:

```python
def drempels(manifest: dict) -> dict:
    """Per pakket configureerbaar (manifest.kpiDrempels); default = de
    mobiliteitsbaseline. Onbekende keys blijven ongebruikt (fail-safe)."""
    return {**DREMPELS, **(manifest or {}).get("kpiDrempels", {})}
```

en in `rapport()` bovenaan `d = drempels(manifest)` en alle `DREMPELS[…]`-referenties in de kpis_block/drempelregels vervangen door `d[…]`.
- [ ] **Step 3: Run suite** → PASS. **Step 4: Commit**: `git commit -am "feat(poc-gent): lege documentenlijst toegestaan voor inzendingen en KPI-drempels per pakket"`.

---

### Task 6: Burger-persona's en fixtures

**Files:**
- Modify: `poc-gent/fixtures/personas.json`, `poc-gent/fixtures/magda.json`, `poc-gent/fixtures/wallets.json`, `poc-gent/fixtures/identiteiten.json`

**Interfaces:**
- Produces: persona's `lisa, tomas, farah, noor, emma, yana, robrecht` (allen `applicantType: burger`, `parkeergelegenheid` in intentSlots behalve waar anders vermeld; `address` per het --check-rapport: lisa/farah/noor/emma/robrecht → `"Veldstraat 1, Gent"`, tomas → adres met uitkomst niet-in/niet-in/niet-in (primair `"Koningin Maria Hendrikaplein 1, Gent"`, anders `"Sleepstraat 1, Gent"`/`"Nederkouter 1, Gent"` per rapport), yana → start `"Sint-Pietersplein 1, Gent"` met `corrections.address = "Veldstraat 1, Gent"`). Magda-records incl. nieuwe tool `gent:parkeervergunningen` (elke persona die prefill bereikt heeft een record: `{"status": "geen"}`, farah `{"status": "aanwezig"}`; emma heeft bewust géén `magda:kenteken`).

- [ ] **Step 1: personas.json** — zeven entries toevoegen (spiegel de bestaande velden; edge-labels voor yana/robrecht):

```json
    { "id": "lisa", "label": {"nl": "Lisa — verhuist naar een appartement aan de Veldstraat"},
      "edge": null,
      "situatieschets": "Ik verhuis volgende maand naar een appartement aan de Veldstraat en wil weten wat ik rond parkeren en afval moet regelen.",
      "intentSlots": {"applicantType": "burger", "address": "Veldstraat 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "tomas", "label": {"nl": "Tomas — verhuist naar het station, geen parkeerregeling"},
      "edge": null,
      "situatieschets": "Ik verhuis naar een flat bij het station van Gent en heb geen auto, maar wil wel weten wanneer mijn afval wordt opgehaald.",
      "intentSlots": {"applicantType": "burger", "address": "Koningin Maria Hendrikaplein 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "farah", "label": {"nl": "Farah — er staat al een bewonersvergunning op haar adres"},
      "edge": "tweede-vergunning",
      "situatieschets": "Ik verhuis in met mijn partner aan de Veldstraat; hij heeft daar al een bewonersvergunning voor zijn auto.",
      "intentSlots": {"applicantType": "burger", "address": "Veldstraat 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "noor", "label": {"nl": "Noor — heeft een eigen garage bij haar nieuwe woning"},
      "edge": "eigen-parkeergelegenheid",
      "situatieschets": "Ik verhuis naar een huis aan de Veldstraat met eigen garage, en overweeg toch een bewonersvergunning voor een tweede auto.",
      "intentSlots": {"applicantType": "burger", "address": "Veldstraat 1, Gent", "parkeergelegenheid": "ja"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "emma", "label": {"nl": "Emma — geen voertuig op haar naam (verwacht blokkade)"},
      "edge": "geen-voertuig",
      "situatieschets": "Ik verhuis naar de Veldstraat en wil een bewonersvergunning aanvragen, al staat er nog geen auto op mijn naam.",
      "intentSlots": {"applicantType": "burger", "address": "Veldstraat 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "yana", "label": {"nl": "Yana — corrigeert het adres tijdens de contextcheck"},
      "edge": "correctie-tijdens-h1",
      "situatieschets": "Ik verhuis binnen Gent — ik noemde eerst een adres bij het station, maar het wordt de Veldstraat.",
      "intentSlots": {"applicantType": "burger", "address": "Sint-Pietersplein 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {"address": "Veldstraat 1, Gent"},
      "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "robrecht", "label": {"nl": "Robrecht — weigert de inzending bij H4"},
      "edge": "weigert-inzending",
      "situatieschets": "Ik verhuis naar een loft aan de Veldstraat en wil een bewonersvergunning aanvragen, maar ik twijfel nog.",
      "intentSlots": {"applicantType": "burger", "address": "Veldstraat 1, Gent", "parkeergelegenheid": "nee"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "geweigerd" }
```

- [ ] **Step 2: magda.json** — per persona (tomas krijgt ook records; consistentie voor hergebruik):

```json
    "lisa":      {"magda:kenteken": {"kenteken": "11-LIS-001", "euroklasse": "Euro 6", "brandstof": "benzine"}, "gent:parkeervergunningen": {"status": "geen"}},
    "tomas":     {"magda:kenteken": {"kenteken": "12-TOM-002", "euroklasse": "Euro 6", "brandstof": "diesel"}, "gent:parkeervergunningen": {"status": "geen"}},
    "farah":     {"magda:kenteken": {"kenteken": "13-FAR-003", "euroklasse": "Euro 6", "brandstof": "benzine"}, "gent:parkeervergunningen": {"status": "aanwezig"}},
    "noor":      {"magda:kenteken": {"kenteken": "14-NOO-004", "euroklasse": "Euro 5", "brandstof": "diesel"}, "gent:parkeervergunningen": {"status": "geen"}},
    "emma":      {"gent:parkeervergunningen": {"status": "geen"}},
    "yana":      {"magda:kenteken": {"kenteken": "16-YAN-006", "euroklasse": "Euro 6", "brandstof": "benzine"}, "gent:parkeervergunningen": {"status": "geen"}},
    "robrecht":  {"magda:kenteken": {"kenteken": "17-ROB-007", "euroklasse": "Euro 6", "brandstof": "diesel"}, "gent:parkeervergunningen": {"status": "geen"}}
```

- [ ] **Step 3: wallets.json + identiteiten.json** — voor alle zeven: pid-attestatie `{"type": "pid", "issuer": "itsme-belgie-mock", "claims": {"sub": "rrn-••••<3cijfer>", "loa": "substantial", "naam": "<Naam>"}}` + machtiging met lege mandaten; identiteiten `{"pseudoniem": …, "naam": …, "type": "burger", "mandaten": []}`. Namen: Lisa Vermeulen (481→kies uniekereeks 203), Tomas Wouters (314), Farah Bakkali (657), Noor Desmet (128), Emma Janssens (970), Yana Petrenko (241), Robrecht Maervoet (586) — pseudoniemen `rrn-••••203` e.d.
- [ ] **Step 4:documenten.json blijft ongewijzigd** (bewonerskaart vraagt geen documenten; ontbrekende fixture-entry betekent n.v.t.).
- [ ] **Step 5: Snelle rooktest**: `python3 run.py --package gent-mobiliteit-ondernemer --persona lisa` → verwacht `uitkomst: escalatie` (burger valt buiten de ondernemerstabellen — bewijst dat de persona's het oude pakket niet verstoren) en suite groen.
- [ ] **Step 6: Commit**: `git commit -am "feat(poc-gent): zeven burger-persona's met magda-, wallet- en identiteitsfixtures — waaronder 2e-vergunning, garage, geen-voertuig, adrescorrectie en H4-weigering"`.

---

### Task 7: Pakket `gent-verhuizen-burger` + golden set

**Files:**
- Create: `poc-gent/packages/gent-verhuizen-burger/manifest.json`, `poc-gent/packages/gent-verhuizen-burger/decision-tables.json`, `poc-gent/packages/gent-verhuizen-burger/golden/scenarios.jsonl`
- Test: `poc-gent/tests/test_gis_zones.py` (zone-pinning burger-golden), `poc-gent/eval.py` (golden+KPI+exit)

**Interfaces:**
- Produces: pakket-id `gent-verhuizen-burger`, `lifeEventCode: GT-VERH-01`, services `bewonerskaart` (inzending) + `info-afvalkalender`/`info-parkeren-tarief`/`info-lez-burger` (info), slots `applicantType/address/parkeergelegenheid` + authentieke `vehicle` (magda:kenteken) en `bestaandeVergunningen` (gent:parkeervergunningen), gisChecks `zoneBewoners/zoneTarief/zoneLez`, dataCheck `afvalkalender` (fallback), `submission.contract: district09-parkeervergunningen`, `kpiDrempels` gelijk aan de default.

- [ ] **Step 1: manifest.json**:

```json
{
  "packageId": "gent-verhuizen-burger",
  "version": "0.1.0",
  "status": "concept",
  "lifeEventCode": "GT-VERH-01",
  "title": "GT-VERH-01 — Verhuizen naar Gent: parkeren, afval en LEZ voor burgers",
  "texts": {
    "intro": "Ik help je regelen wat je nodig hebt wanneer je naar Gent verhuist: parkeren bij je nieuwe adres, afvalophaling en de lage-emissiezone.",
    "scope": "Deze assistent gaat over gemeentelijke regelingen voor burgers bij een verhuizing binnen of naar Gent.",
    "aiToelichting": "Ik ben een AI-assistent van Stad Gent. Ik stel voor en leg uit; jij beslist en bevestigt.",
    "weigering": "Als ik het niet zeker weet, zeg ik dat eerlijk en verbind ik je door met een medewerker.",
    "escalatie": "Twijfel of een bijzondere situatie? Dan neemt een medewerker van Gentinfo het van me over.",
    "contextZin": "U bent {applicantType} en verhuist naar: {address}. Eigen parkeergelegenheid: {parkeergelegenheid}."
  },
  "contextSchema": {
    "slots": {
      "applicantType": {"type": "enum", "values": ["burger", "ondernemer", "organisatie"], "required": true, "authenticSource": null, "vraag": "Bent u particulier, ondernemer of organisatie?"},
      "address": {"type": "string", "required": true, "authenticSource": null, "vraag": "Naar welk adres verhuist u?"},
      "parkeergelegenheid": {"type": "enum", "values": ["ja", "nee"], "required": true, "authenticSource": null, "vraag": "Heeft u eigen parkeergelegenheid (garage of oprit) bij uw nieuwe adres?"},
      "vehicle": {"type": "kenteken", "required": false, "authenticSource": "magda:kenteken", "vraag": null},
      "bestaandeVergunningen": {"type": "enum", "values": ["aanwezig", "geen"], "required": false, "authenticSource": "gent:parkeervergunningen", "vraag": null}
    }
  },
  "gisChecks": [
    {"id": "bewonerszone", "layer": "gent-bewonerszone", "input": "address", "output": "zoneBewoners"},
    {"id": "tariefzone", "layer": "gent-parkeertariefzone", "input": "address", "output": "zoneTarief"},
    {"id": "lez", "layer": "gent-lez", "input": "address", "output": "zoneLez"}
  ],
  "dataChecks": [
    {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
     "outputs": ["afvalRest", "afvalPmd", "afvalGlas", "afvalPapier"], "unknownPolicy": "fallback"}
  ],
  "authenticSources": [
    {"slot": "vehicle", "source": "magda:kenteken", "purpose": "vaststellen van het kenteken voor de bewonersvergunning"},
    {"slot": "bestaandeVergunningen", "source": "gent:parkeervergunningen", "purpose": "vaststellen of er al een bewonersvergunning op het adres geldt"}
  ],
  "submission": {"contract": "district09-parkeervergunningen"},
  "kpiDrempels": {"kpi01_min": 90.0, "kpi01_doel": 95.0, "kpi02_min": 100.0, "kpi03_min": 100.0, "kpi04_min": 90.0},
  "decisionTables": "decision-tables.json",
  "services": {
    "bewonerskaart": {
      "type": "inzending", "vereistAuth": true, "minLoA": "substantial",
      "titel": "Bewonersvergunning parkeren (1e of 2e)",
      "uitleg": "Jaarlijkse vergunning om als bewoner van een bewonerszone in uw eigen zone te parkeren; de eerste per gezin/adres is gratis, de tweede kost €300 per jaar (tarief 2026). Aan elke vergunning is exact één kenteken gekoppeld.",
      "documenten": [],
      "formulier": [
        {"veld": "kenteken", "bron": "magda:kenteken.kenteken"},
        {"veld": "vergunning-op-adres", "bron": "gent:parkeervergunningen.status"},
        {"veld": "adres-domicilie", "bron": "slot:address"},
        {"veld": "eigen-parkeergelegenheid", "bron": "slot:parkeergelegenheid"},
        {"veld": "aanvrager", "bron": "slot:applicantType"}
      ],
      "validaties": [
        {"id": "V1-tweede-vergunning", "wanneer": {"vergunning-op-adres": "aanwezig"}, "ernst": "waarschuwing",
         "melding": "Er staat al een bewonersvergunning op dit adres: dit wordt de tweede vergunning (€300/jaar, tarief 2026)."},
        {"id": "V2-eigen-parkeergelegenheid", "wanneer": {"eigen-parkeergelegenheid": "ja"}, "ernst": "waarschuwing",
         "melding": "U heeft eigen parkeergelegenheid: u komt hooguit in aanmerking voor een tijdelijke vergunning. De beoordeling gebeurt door de dienst Parkeren."}
      ]
    },
    "info-afvalkalender": {"type": "info", "vereistAuth": false,
      "titel": "Afvalophaling op uw nieuwe adres (IVAGO)",
      "uitleg": "Ophaaldagen per fractie voor uw straat, uit de IVAGO-ophaalkalender (open data). Staat uw straat er niet bij, raadpleeg dan gent.be/recycle of de Recycle!-app.",
      "formulier": [], "validaties": []},
    "info-parkeren-tarief": {"type": "info", "vereistAuth": false,
      "titel": "Parkeren tegen tarief in uw buurt",
      "uitleg": "Uw adres ligt in een parkeertariefzone maar buiten een bewonerszone: u heeft geen recht op een bewonersvergunning. Betalen kan aan de parkeerautomaat of via de app; zie stad.gent/parkeren.",
      "formulier": [], "validaties": []},
    "info-lez-burger": {"type": "info", "vereistAuth": false,
      "titel": "Lage-emissiezone: dagenpas bij ouder voertuig",
      "uitleg": "Uw nieuwe adres ligt in de lage-emissiezone. Met een oudere diesel of benzineauto heeft u een dagenpas (of een geldige ontheffing) nodig; controleer uw euroklasse op stad.gent/lez.",
      "formulier": [], "validaties": []}
  },
  "golden": "golden/scenarios.jsonl"
}
```

- [ ] **Step 2: decision-tables.json**:

```json
{
  "id": "R-verhuizen-burger",
  "version": "2026.10",
  "rules": [
    {"id": "RB1", "when": {"applicantType": "burger", "zoneBewoners": "in"}, "then": {"transactions": ["bewonerskaart"], "info": ["info-afvalkalender"]}, "legalBasis": "Gent parkeerreglement — bewonersvergunningen (stad.gent, tarief 2026)", "uitleg": "Uw nieuwe adres ligt in een bewonerszone: u komt in aanmerking voor een bewonersvergunning (eerste gratis per gezin, tweede €300/jaar), gekoppeld aan één kenteken."},
    {"id": "RB2", "when": {"applicantType": "burger", "zoneBewoners": "niet-in", "zoneTarief": "in"}, "then": {"transactions": [], "info": ["info-parkeren-tarief", "info-afvalkalender"]}, "legalBasis": "Gent parkeerreglement — parkeertariefzones (open data)", "uitleg": "Uw adres ligt buiten een bewonerszone maar binnen een parkeertariefzone: parkeren gebeurt tegen het geldende tarief; een bewonersvergunning is hier niet mogelijk."},
    {"id": "RB3", "when": {"applicantType": "burger", "zoneBewoners": "niet-in", "zoneTarief": "niet-in"}, "then": {"transactions": [], "info": ["info-afvalkalender"]}, "legalBasis": "—", "uitleg": "Uw adres ligt buiten bewoners- en tariefzone: er geldt geen bijzondere parkeerregeling voor uw adres."},
    {"id": "RB4", "when": {"applicantType": "burger", "zoneLez": "in"}, "then": {"transactions": [], "info": ["info-lez-burger"]}, "legalBasis": "Gent LEZ-reglement — dagenpassen (stad.gent/lez)", "uitleg": "Uw nieuwe adres ligt in de lage-emissiezone: met een oudere wagen heeft u een dagenpas nodig."}
  ],
  "unknownPolicy": "escalate"
}
```

- [ ] **Step 3: Rooktest per persona**: `python3 run.py --package gent-verhuizen-burger --persona lisa` (enz. voor alle zeven). Verwachte routing: lisa/farah/noor/emma/robrecht/yana(na correctie) → `transactie: bewonerskaart` + `informatie: info-afvalkalender, info-lez-burger`; tomas → alleen info (afval, evt. tarief/lez per --check-rapport). STATUS-pinnen: lisa `gereed`, farah/noor `gereed-met-waarschuwing`, emma `blokkade` (V0 ontbrekend kenteken), yana `gereed`, robrecht `geweigerd`, tomas `gereed`.
- [ ] **Step 4: golden/scenarios.jsonl** (info-volgorde = regelvolgorde RB1→RB4; bijstellen op het --check-rapport als tomas' adres toch in tarief/lez ligt):

```
{"scenarioId": "verh-01-lisa-bewonerszone", "persona": "lisa", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "gereed"}}
{"scenarioId": "verh-02-tomas-geen-regeling", "persona": "tomas", "expect": {"outcome": "paden", "transactions": [], "info": ["info-afvalkalender"], "status": "gereed"}}
{"scenarioId": "verh-03-farah-tweede-vergunning", "persona": "farah", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "gereed-met-waarschuwing"}}
{"scenarioId": "verh-04-noor-garage", "persona": "noor", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "gereed-met-waarschuwing"}}
{"scenarioId": "verh-05-emma-geen-voertuig", "persona": "emma", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "blokkade"}}
{"scenarioId": "verh-06-yana-adrescorrectie", "persona": "yana", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "gereed"}}
{"scenarioId": "verh-07-robrecht-h4-weigering", "persona": "robrecht", "expect": {"outcome": "paden", "transactions": ["bewonerskaart"], "info": ["info-afvalkalender", "info-lez-burger"], "status": "geweigerd"}}
```

Indien het --check-rapport voor tomas' adres afwijkende zone-uitkomsten geeft: kies per combinatietabel hierboven een ander adres uit `{Koningin Maria Hendrikaplein 1, Sleepstraat 1, Nederkouter 1}` (persona + golden samen aanpassen; Sint-Pietersplein 1 dekt yana's startpunt en hoort bij LEZ-in).
- [ ] **Step 5: eval**: `../nldt/.venv/bin/python eval.py --package gent-verhuizen-burger` → 7/7 golden OK, determinisme OK, KPI's GO, exit-test 7/7 identiek, `go/no-go: GO`.
- [ ] **Step 6: Regressie**: `../nldt/.venv/bin/python eval.py` (ondernemerspakket) → nog steeds 13/13 + GO; volledige suite groen.
- [ ] **Step 7: Zone-pinningtest** in `tests/test_gis_zones.py` — pin tomas' golden-adres tegen de echte lagen (uitkomst zoals het --check-rapport uit Taak 1 laat zien; primair buiten alle drie):

```python
def test_burgergolden_tomas_adres_pinning():
    zones = gis_zones.load_zones(POC_ROOT)
    lon, lat = gis_zones.lookup_address(POC_ROOT, "Koningin Maria Hendrikaplein 1, Gent")
    for laag in ("gent-bewonerszone", "gent-parkeertariefzone", "gent-lez"):
        assert gis_zones.zone_result(zones, laag, lon, lat) == "niet-in", laag
```

(wijkt het --check-rapport af, dan adres én persona én golden-regel samen aanpassen en de test met dat adres herschrijven — het pin-testpatroon blijft gelijk).
- [ ] **Step 8: Commit**: `git add poc-gent/packages/gent-verhuizen-burger poc-gent/tests/test_gis_zones.py && git commit -m "feat(poc-gent): levensgebeurtenis-pakket gent-verhuizen-burger — bewonerskaart-transactie en afval/parkeren/LEZ-info op echte Gentse data, golden set 7/7"`.

---

### Task 8: Injectiesuite per pakket

**Files:**
- Modify: `poc-gent/fixtures/injecties.json`, `poc-gent/core/injectie.py`
- Test: `poc-gent/tests/test_injectie.py`

**Interfaces:**
- Produces: `injecties.json["pakketten"]["gent-verhuizen-burger"] = {"personas": {…}, "vrijeSlots": ["address"], "overigeSlots": ["parkeergelegenheid"], "schoneWaarden": {…}}`; `injectie.aanvallen(poc_root, package_id)` en `voer_uit(poc_root, package_id)` zijn pakketbewust (default = huidig gedrag voor het ondernemerspakket, 34 aanvallen; burger = 24).

- [ ] **Step 1: fixture-sectie** toevoegen aan `injecties.json`:

```json
  "pakketten": {
    "gent-verhuizen-burger": {
      "personas": {"direct": "lisa", "indirect": "yana", "documentnaam": "lisa",
                   "tool-misbruik": "lisa", "exfiltratie": "tomas"},
      "vrijeSlots": ["address"],
      "overigeSlots": ["parkeergelegenheid"],
      "schoneWaarden": {
        "address": "Veldstraat 1, Gent",
        "parkeergelegenheid": "nee",
        "situatieschets": "Ik verhuis volgende maand naar een appartement in het centrum van Gent."
      }
    }
  }
```

- [ ] **Step 2: implementatie** — `injectie.py`: `_pakket_config(poc_root, package_id) -> dict` zoals hierboven ontworpen (defaults exact de huidige hardcodes: personas sanne/jeroen/sanne/sanne/ahmed, vrije_slots `(address, activity, timing)`, overige `(activity,)`, schone waarden de globale); `aanvallen(poc_root, package_id="gent-mobiliteit-ondernemer")` gebruikt de config (direct: ×vrije_slots; tool-misbruik/exfiltratie: ×overige_slots) en zet op elke aanval `"controle": "adres"` als `slot=="address"` en `"routing-gelijk"` voor de andere vrije/overige slots en situatieschets/documentnaam; `controleer` vervangt de hardcoded slotlijsten door `aanval["controle"]`; `voer_uit(poc_root, package_id=…)` geeft package_id door.
- [ ] **Step 3: tests** — in `test_injectie.py`: `len(aanvallen(POC_ROOT, "gent-verhuizen-burger")) == 24` (5 direct×1 + 4 + 4 + 5 + 6); default nog 34; één burger-address-aanval leidt tot escalatie.
- [ ] **Step 4: Run beide suites**: `../nldt/.venv/bin/python eval.py --injectie` → 34/34; `../nldt/.venv/bin/python eval.py --injectie --package gent-verhuizen-burger` → 24/24, 0 open bevindingen.
- [ ] **Step 5: Commit**: `git commit -am "feat(poc-gent): injectiesuite per levensgebeurtenis-pakket — burgeraanvallen tegen de echte burger-slots"`.

---

### Task 9: Simulatie — levensgebeurtenis-dropdown in het Gent-tab

**Files:**
- Modify: `poc-gent/fetch_sources.py` (`--kaart-burger`), `simulation/build_simulation.py`, `simulation/template.html`, `simulation/vertaal_gent.py`, `simulation/test_build_gent.py`, `simulation/test_vertaal_gent.py`
- Create: `poc-gent/fixtures/source/kaart-burger.json` (gegenereerd), `simulation/simulation.html` (gegenereerd)

**Interfaces:**
- Produces: `build_gent(package_id="gent-mobiliteit-ondernemer") -> dict` (persona-filter via `GENT_PACKAGE_PERSONAS`); `build_gent("gent-verhuizen-burger")` levert hetzelfde blok-formaat met per persona `kaart.mode == "burger"`; template: dropdown `gentPackage(key)` wisselt `G` tussen `DATA.gent` en `DATA.gentBurger`.

- [ ] **Step 1: kaart-burger-cache** — in `fetch_sources.py`:

```python
BURGER_PERSONAS = ("lisa", "tomas", "farah", "noor", "emma", "yana", "robrecht")


def haal_kaart_burger(poc_root: Path, burger_personas: tuple = BURGER_PERSONAS) -> dict:
    """Burgerkaart (GT-VERH-01): gemeentegrens + per persona het doeladres als
    startpunt. Zones komen uit gis-zones.geojson (build leest ze daar)."""
    kaart_pad = SOURCE_DIR / "kaart.json"
    grens = json.loads(kaart_pad.read_text(encoding="utf-8")).get("grens") if kaart_pad.is_file() else _haal_grens()
    adressen = json.loads((poc_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    personas = {p["id"]: p for p in json.loads(
        (poc_root / "fixtures" / "personas.json").read_text(encoding="utf-8"))["personas"]}
    uit = {"grens": grens, "personas": {}, "meta": {"fetchedAt": _now()}}
    for pid in burger_personas:
        doel = personas[pid].get("corrections", {}).get("address") or personas[pid]["intentSlots"]["address"]
        if doel in adressen:
            uit["personas"][pid] = {"adres": doel, "coord": adressen[doel]}
    (SOURCE_DIR / "kaart-burger.json").write_text(
        json.dumps(uit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return uit
```

plus argparse `--kaart-burger` en in `main()`: `if args.kaart_burger: kb = haal_kaart_burger(POC_ROOT); meta_document["bronnen"]["kaart-burger"] = {"cache": "fixtures/source/kaart-burger.json", "fetchedAt": kb["meta"]["fetchedAt"]}`. Bouw: `python3 fetch_sources.py --kaart-burger` (offline mits kaart.json/grens aanwezig; anders Nominatim).
- [ ] **Step 2: build_simulation.py** — `GENT_PACKAGE_PERSONAS`-mapping (11 oud + 7 nieuw); `build_gent(package_id="gent-mobiliteit-ondernemer")` filtert persona's en kiest kaartbron + kaartblok-functie:

```python
GENT_PACKAGE_PERSONAS = {
    "gent-mobiliteit-ondernemer": ("sanne", "ahmed", "maria", "fatima", "jeroen",
                                   "ellen", "dirk", "wim", "nadia", "ilse", "hanne"),
    "gent-verhuizen-burger": ("lisa", "tomas", "farah", "noor", "emma", "yana", "robrecht"),
}

GENT_KAART = {
    "gent-mobiliteit-ondernemer": ("kaart.json", "_kaart_blok"),
    "gent-verhuizen-burger": ("kaart-burger.json", "_kaart_blok_burger"),
}
```

met in `build_gent`: `package_id`-parameter, `for pid, persona in personas.items(): if pid not in GENT_PACKAGE_PERSONAS[package_id]: continue`, kaartpad/-blok via `GENT_KAART[package_id]`. Nieuwe `_kaart_blok_burger(kaart, zones, pid)`:

```python
def _kaart_blok_burger(kaart, zones, pid):
    """Burgerkaart: regeling-zones (bewoners, tarief, LEZ) rond de nieuwe
    woning — geen routes/innames (dat is ondernemersmobiliteit)."""
    entry = (kaart.get("personas") or {}).get(pid)
    if not entry:
        return None
    coord = entry["coord"]
    burger_zones = {laag: ringen for laag, ringen in zones.items()
                    if laag in ("gent-bewonerszone", "gent-parkeertariefzone", "gent-lez")}
    project = _maak_projectie(_kaart_bbox(kaart.get("grens"), [coord]))
    gis = _gis_zones_module()
    zone_uit = {laag: ("in" if any(gis.point_in_ring(coord[0], coord[1], r) for r in ringen) else "niet-in")
                for laag, ringen in burger_zones.items()}
    start = project(coord)
    return {"mode": "burger",
            "start": {"label": "nieuwe woning", "adres": entry["adres"], "coord": coord},
            "doel": entry["adres"], "zones": zone_uit, "gewenst": None,
            "routes": [], "innames": [], "omzeil": [],
            "svg": {"grens": _pad_ringen(_grens_ringen(kaart.get("grens")), project) if kaart.get("grens") else None,
                    "zones": {laag: _pad_ringen(ringen, project) for laag, ringen in burger_zones.items()},
                    "start": [start[0], start[1]], "routes": None, "innames": []},
            "bron": "zones & kalender: Stad Gent open data (Modellicentie Gratis Hergebruik) · gemeentegrens: OSM/Nominatim (ODbL)"}
```

in `main()`: `data = {…, "gent": build_gent(), "gentBurger": build_gent("gent-verhuizen-burger")}`.
- [ ] **Step 3: template.html** — (a) `const G = DATA.gent;` → `let G = DATA.gent; let GPKG = "gent";`; (b) dropdown in `renderGentMeta()` vóór de persona-knoppen:

```js
const GP = [["gent","GT-MOB-01 · voertuigtoegang ondernemer","GT-MOB-01 · vehicle access entrepreneur"],
            ["gentBurger","GT-VERH-01 · verhuizen (burger)","GT-VERH-01 · moving house (citizen)"]];
```

gerenderd als `<select class="gpkg" onchange="gentPackage(this.value)">` met `option` per entry (tekst via `TT`); (c) `function gentPackage(k){ if(sim5) sim5.pause(); GPKG=k; G=DATA[k]; curGent=G.personas[0].id; renderGentMeta(); renderGentStatic(); sim5=makeSim5(); sim5.prog(); }` en `gentPackage` in `globalThis.__ds`; (d) in `kaartStap(st)` als eerste tak na `const k = p.kaart, z = k.svg;`:

```js
  if (k.mode === "burger") {
    let s = "";
    if (z.grens) s += `<path d="${z.grens}" fill="none" stroke="#8b93a7" stroke-width="1.2" opacity=".45"/>`;
    s += `<path d="${z.zones["gent-parkeertariefzone"]}" fill="#a78bfa1f" stroke="#a78bfa99" stroke-width="1.2"/>`;
    s += `<path d="${z.zones["gent-bewonerszone"]}" fill="#34d39922" stroke="#34d39999" stroke-width="1.2"/>`;
    s += `<path d="${z.zones["gent-lez"]}" fill="#f59e0b1f" stroke="#f59e0b99" stroke-width="1.2"/>`;
    const startNieuw = kaartLaatsteStap < -1;
    s += `<circle class="${startNieuw?"kpop":""}" cx="${z.start[0]}" cy="${z.start[1]}" r="7" fill="#34d399" stroke="#0e2a1c"><title>${esc(k.start.adres)}</title></circle>`;
    s += `<text x="${z.start[0]+10}" y="${z.start[1]+4}" font-size="12" fill="#34d399">${esc(k.start.label)}</text>`;
    $("kaart5").innerHTML = s; kaartLaatsteStap = st; return;
  }
```

(e) in `renderGentStatic()` burger-tak voor kaart5meta/info/bron: `if (k.mode === "burger") { $("kaart5meta").textContent = ""; $("kaart5info").innerHTML = `<div>${TT("nieuwe woning:","new home:")} <b>${esc(k.start.adres)}</b></div>` + ["gent-bewonerszone","gent-parkeertariefzone","gent-lez"].filter(l=>k.zones[l]).map(l=>`<div class="gdu">${TT({"gent-bewonerszone":"bewonerszone","gent-parkeertariefzone":"parkeertariefzone","gent-lez":"lage-emissiezone"}[l], {"gent-bewonerszone":"residents' zone","gent-parkeertariefzone":"paid-parking zone","gent-lez":"low-emission zone"}[l])}: <b>${TTV(k.zones[l],{in:"in","niet-in":"outside"})}</b></div>`).join(""); $("kaart5bron").innerHTML = TT(esc(k.bron), esc(k.bronEn)); } else { …bestaande code… }`; (f) kaartkop/legenda: de `gkaartkop`-titel en legenda-regels per modus togglen (twee varianten met `tekst-nl`/`tekst-en`, `display` via `GPKG==="gentBurger"`); burger-legenda: `<span style="color:#34d399">▨</span> bewonerszone · <span style="color:#a78bfa">▨</span> parkeertariefzone · <span style="color:#f59e0b">▨</span> lage-emissiezone · <span style="color:#34d399">●</span> nieuwe woning · 🔍 scroll = inzoomen · sleep = verschuiven · dubbelklik = herstellen` (+ EN-variant); (g) CSS-hook `.gpkg` in het `#view5`-blok (klein, mono, donker — spiegel `.ttab`).
- [ ] **Step 4: vertaal_gent.py** — DICT-aanvullingen: 7 persona-labels, 7 situatieschetsen, 4 diensttitels ("Bewonersvergunning parkeren (1e of 2e)" → "Residents' parking permit (1st or 2nd)", "Afvalophaling op uw nieuwe adres (IVAGO)" → "Waste collection at your new address (IVAGO)", "Parkeren tegen tarief in uw buurt" → "Paid parking in your area", "Lage-emissiezone: dagenpas bij ouder voertuig" → "Low-emission zone: day pass for older vehicles"), uitleg RB1–RB4, V1/V2-meldingen, nieuwe intakevragen ("Naar welk adres verhuist u?", "Heeft u eigen parkeergelegenheid (garage of oprit) bij uw nieuwe adres?"), doelbindingen ("vaststellen van het kenteken voor de bewonersvergunning", "vaststellen of er al een bewonersvergunning op het adres geldt"), stap-titel "We halen de afvalkalender van je straat op" → "We fetch the collection calendar for your street", burger-kaartbronregel, en het PATROON `r"Ontbrekend gegeven: (.+) — vraag het aan bij de bronhouder\."` → `f"Missing data: {vt(g[0])} — request it from the data holder."`.
- [ ] **Step 5: tests** — nieuw `simulation/test_build_gent_burger.py` (statusses-dict: lisa gereed, tomas gereed, farah/noor gereed-met-waarschuwing, emma blokkade, yana gereed, robrecht geweigerd; `lifeEventCode == "GT-VERH-01"`; per persona `kaart.mode == "burger"` met drie zone-paden + start; events-ketting ok; `serviceTitels` bevat `bewonerskaart`). `test_vertaal_gent.py`: `build_gent("gent-verhuizen-burger")` toevoegen met `len(personas) == 7` en `onbekend() == []` (vt-state resetten: `vertaal_gent._onbekend.clear()` vóór de assert, spiegel de bestaande test). `test_build_gent.py`: statusset blijft exact de 11 oude persona's (door de filter).
- [ ] **Step 6: Build + verify**: `cd simulation && ../nldt/.venv/bin/python build_simulation.py` → schrijft simulation.html mét `gentBurger`; `../nldt/.venv/bin/python -m pytest -q` groen (simulation). Open `simulation.html` (tab 5): dropdown wisselt pakket, persona's, kaart en NL/EN.
- [ ] **Step 7: Commit**: `git add poc-gent/fetch_sources.py poc-gent/fixtures/source/kaart-burger.json poc-gent/fixtures/source/source.meta.json simulation/build_simulation.py simulation/template.html simulation/vertaal_gent.py simulation/test_build_gent.py simulation/test_build_gent_burger.py simulation/test_vertaal_gent.py simulation/simulation.html && git commit -m "feat(simulation): levensgebeurtenis-dropdown in het Gent-tab — burgerpakket GT-VERH-01 mét regeling-zones-kaart, volledig NL/EN"`.

---

### Task 10: README's en eindcontrole

**Files:**
- Modify: `poc-gent/README.md`, `simulation/README.md`

- [ ] **Step 1: poc-gent/README.md** — nieuwe sectie "Levensgebeurtenis-pakketken (multi-package)" onder de intro: het burgerpakket GT-VERH-01 (diensten, regels, datasets bewonerszones/parkeertariefzones/IVAGO mét licenties), `run.py --package gent-verhuizen-burger --persona lisa`, `eval.py --package …`, `eval.py --injectie --package …`, dataChecks-uitleg (unknownPolicy), `fetch_sources.py --afval --kaart-burger`, en de Gedeelde-fixtures-opmerking.
- [ ] **Step 2: simulation/README.md** — dropdown per levensgebeurtenis in het Gent-tab, burgerkaartmodus.
- [ ] **Step 3: Eindcontrole** (alles in één adem): `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q && ../nldt/.venv/bin/python eval.py && ../nldt/.venv/bin/python eval.py --package gent-verhuizen-burger && ../nldt/.venv/bin/python eval.py --injectie && ../nldt/.venv/bin/python eval.py --injectie --package gent-verhuizen-burger && python3 fetch_sources.py --check && cd ../simulation && ../nldt/.venv/bin/python -m pytest -q && ../nldt/.venv/bin/python build_simulation.py` — alles groen/GO.
- [ ] **Step 4: Commit**: `git commit -am "docs: README's voor het burgerpakket gent-verhuizen-burger en de levensgebeurtenis-dropdown"`.
