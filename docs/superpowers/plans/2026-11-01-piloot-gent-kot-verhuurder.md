# Piloot Gent — pakket `gent-kot-verhuurder` Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derde levensgebeurtenis-pakket `gent-kot-verhuurder` (GT-KOT-01 "Ik verhuur een kot"): koteloket-melding als transactie, info-diensten rond vergunning/attest/belasting/afval, op de echte kotzone-laag — met één nieuwe generieke engine-capaciteit `gisChecks.attribuut` (benoemde zone-lookup) en een derde optie in de simulatie-dropdown.

**Architecture:** Configuratie is data: nieuw pakket onder `poc-gent/packages/`, zes verhuurder-persona's in de gedeelde fixture-ruimte, en een kleine engine-uitbreiding (gisCheck geeft bij een `attribuut` de feature-attribuutwaarde terug i.p.v. in/niet-in). Simulatie hergebruikt het adreszones-kaartpatroon met één generieke zone-lus. Runs blijven offline en deterministisch.

**Tech Stack:** Python 3 stdlib-only (poc-gent), pytest/unittest onder `nldt/.venv`, vanilla-JS simulatietemplate, data.stad.gent ODS-API voor de broncache.

**Spec:** [`docs/superpowers/specs/2026-11-01-piloot-gent-kot-verhuurder-design.md`](../specs/2026-11-01-piloot-gent-kot-verhuurder-design.md)

## Global Constraints

- Testcommando's: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q`; simulation: `cd simulation && ../nldt/.venv/bin/python -m pytest -q` en `node verify_static.mjs`.
- poc-gent blijft stdlib-only; netwerkaanraking uitsluitend in `fetch_sources.py`.
- Alle nieuwe teksten Nederlands; EN uitsluitend in `simulation/vertaal_gent.py` (volledigheidstest dwingt af).
- Bestaande twee pakketten blijven zonder aanpassingen groen (regressiesignaal); uitzonderingen staan expliciet in dit plan.
- Dataset: `kotzones-gent` (20 features, attribuut `kotzone_na`, Modellicentie Gratis Hergebruik).
- Commitstijl: `feat(poc-gent): …` / `test(poc-gent): …` / `feat(simulation): …`, Nederlands onderwerp.

---

### Task 1: `gisChecks.attribuut` — engine-capaciteit voor benoemde zones

**Files:**
- Modify: `poc-gent/adapters/gis_zones.py`, `poc-gent/core/catalog.py`, `poc-gent/fetch_sources.py` (normaliseer), `poc-gent/tests/test_gis_zones.py`, `poc-gent/tests/test_catalog.py`, `poc-gent/tests/test_fetch_sources.py`
- Test: dezelfde testbestanden

**Interfaces:**
- Produces: `gis_zones.load_ring_attributen(poc_root) -> dict[str, list[str | None]]` (per laag, per ring in dezelfde volgorde als `load_zones`); `gis_zones.attribuut_result(zones, ring_attributen, layer, lon, lat) -> str` (attribuutwaarde van de eerste treffende ring; lege waarde → `"in"`; geen treffer → `"niet-in"`); `gis_zones.apply_checks` eert `check.get("attribuut")`. `fetch_sources.normaliseer(layer, features, versie)` kopieert `LAYERS[layer].get("attribuut")` naar `properties.attribuut`. Manifestveld `gisChecks[].attribuut` (optioneel, niet-lege string).

- [ ] **Step 1: Falende tests** — in `tests/test_gis_zones.py`:

```python
def test_attribuut_lookup_geeft_zonenaam(tmp_path):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Ledeganck"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.70, 51.05], [3.72, 51.05], [3.72, 51.06], [3.70, 51.06], [3.70, 51.05]]]}},
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Haven"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.73, 51.05], [3.75, 51.05], [3.75, 51.06], [3.73, 51.06], [3.73, 51.05]]]}}]}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "gis-zones.geojson").write_text(json.dumps(fc), encoding="utf-8")
    zones = gis_zones.load_zones(tmp_path)
    attributen = gis_zones.load_ring_attributen(tmp_path)
    assert attributen["gent-kotzone"] == ["Ledeganck", "Haven"]
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.71, 51.055) == "Ledeganck"
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.74, 51.055) == "Haven"
    assert gis_zones.attribuut_result(zones, attributen, "gent-kotzone", 3.60, 51.00) == "niet-in"


def test_apply_checks_attribuut_schrijft_naam(tmp_path):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"layer": "gent-kotzone", "versie": "v", "attribuut": "Ledeganck"},
         "geometry": {"type": "Polygon", "coordinates": [[[3.70, 51.05], [3.72, 51.05], [3.72, 51.06], [3.70, 51.06], [3.70, 51.05]]]}}]}
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "gis-zones.geojson").write_text(json.dumps(fc), encoding="utf-8")
    manifest = {"gisChecks": [{"id": "kotzone", "layer": "gent-kotzone", "input": "address",
                               "output": "kotzone", "attribuut": "kotzone_na"}]}
    ctx, herkomst = {"address": "Teststraat 1, Gent"}, {}
    with patch("adapters.gis_zones.lookup_address", return_value=(3.71, 51.055)):
        gis_zones.apply_checks(manifest, ctx, herkomst, tmp_path)
    assert ctx["kotzone"] == "Ledeganck"
    assert herkomst["kotzone"]["bron"].startswith("gis:gent-kotzone (v")
```

(met bovenin het testbestand al aanwezige imports; voeg `from unittest.mock import patch` toe indien ontbrekend.) Daarnaast in `tests/test_catalog.py`:

```python
def test_gischeck_attribuut_leeg_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["gisChecks"][0]["attribuut"] = "  "
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="attribuut"):
        catalog.load_package(tmp_path, manifest["packageId"])
```

en in `tests/test_fetch_sources.py`:

```python
def test_normaliseer_bewaart_attribuut_voor_kotzone(monkeypatch):
    feature = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[3.72, 51.05], [3.73, 51.05], [3.73, 51.06], [3.72, 51.06], [3.72, 51.05]]]},
               "properties": {"kotzone_na": "Ledeganck"}}
    monkeypatch.setitem(fetch_sources.LAYERS, "gent-kotzone",
                        {"attribuut": "kotzone_na"})
    uit = fetch_sources.normaliseer("gent-kotzone", [feature], "v")
    assert uit[0]["properties"]["attribuut"] == "Ledeganck"
    zonder = fetch_sources.normaliseer("gent-lez", [_feature(None)], "v")
    assert "attribuut" not in zonder[0]["properties"]
```

- [ ] **Step 2: Run** → FAIL (functies bestaan niet).
- [ ] **Step 3: Implementeer** — `adapters/gis_zones.py` (na `load_layer_versies`):

```python
def load_ring_attributen(poc_root: Path) -> dict[str, list[str | None]]:
    """Attribuutwaarde per ring, in dezelfde volgorde als load_zones per laag
    ringen aanlevert (één feature kan meerdere ringen hebben: dezelfde waarde).
    Lagen zonder attribuut leveren None per ring (binaire checks negeren dit)."""
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    attributen: dict[str, list] = {}
    for feat in fc["features"]:
        laag = feat["properties"]["layer"]
        waarde = feat["properties"].get("attribuut")
        attributen.setdefault(laag, []).extend([waarde] * len(_outer_rings(feat.get("geometry"))))
    return attributen


def attribuut_result(zones: dict, ring_attributen: dict, layer: str,
                     lon: float, lat: float) -> str:
    """Benoemde zone-lookup: attribuutwaarde van de eerste treffende ring;
    lege waarde telt als 'in' (zone bestaat, naam onbekend in de bron)."""
    for idx, ring in enumerate(zones.get(layer, [])):
        if point_in_ring(lon, lat, ring):
            waarde = (ring_attributen.get(layer) or [None] * len(zones.get(layer, [])))[idx]
            return waarde if waarde else "in"
    return "niet-in"
```

In `apply_checks`: laad `ring_attributen = load_ring_attributen(poc_root)` alléén wanneer een check `attribuut` heeft, en vervang de toekenning:

```python
        if check.get("attribuut"):
            context[check["output"]] = attribuut_result(zones, ring_attributen,
                                                        check["layer"], lon, lat)
        else:
            context[check["output"]] = zone_result(zones, check["layer"], lon, lat)
```

`core/catalog.py` in de gisChecks-lus: `if "attribuut" in check and not str(check["attribuut"]).strip(): raise PackageError(f"gisCheck '{check['id']}': attribuut moet een niet-lege tekst zijn")`. `fetch_sources.normaliseer`: `attribuut`-kopie — in de uit-loop: `waarde = None; if LAYERS[layer].get("attribuut"): waarde = (feature.get("properties") or {}).get(LAYERS[layer]["attribuut"])` en voeg `"attribuut": waarde` aan properties alléén wanneer `waarde` gevuld is.
- [ ] **Step 4: Run suite** → PASS (176 + 4 nieuw). **Step 5: Commit**: `git commit -am "feat(poc-gent): gisChecks.attribuut — benoemde zone-lookup (ring→attribuutwaarde) naast de binaire in/niet-in-check"`.

---

### Task 2: Kotzone-laag in de broncache + kotadres + --check met zone-naam

**Files:**
- Modify: `poc-gent/fetch_sources.py` (LAYERS, ADRESSEN, zone_rapport), gegenereerd: `poc-gent/fixtures/gis-zones.geojson`, `poc-gent/fixtures/addresses.json`, `poc-gent/fixtures/source/kotzones-gent.json`, `poc-gent/fixtures/source/source.meta.json`
- Test: `poc-gent/tests/test_gis_zones.py`

**Interfaces:**
- Produces: laag `gent-kotzone` (dataset `kotzones-gent`, soort export, `attribuut: "kotzone_na"`) met 20 features in gis-zones.geojson mét `properties.attribuut`; adres `"Overpoortstraat 1, Gent"` in addresses.json; `zone_rapport()` drukt per adres ook `kotzone=<naam>`.

- [ ] **Step 1: LAYERS-entry** (na `gent-parkeertariefzone`):

```python
    "gent-kotzone": {
        "dataset_id": "kotzones-gent",
        "url_export": f"{PORTAL}/api/explore/v2.1/catalog/datasets/kotzones-gent/exports/geojson",
        "url_meta": f"{PORTAL}/api/explore/v2.1/catalog/datasets/kotzones-gent",
        "url_portal": f"{PORTAL}/explore/assets/kotzones-gent",
        "soort": "export",
        "filter": None,
        "attribuut": "kotzone_na",
    },
```

- [ ] **Step 2: ADRESSEN** — voeg toe: `"Overpoortstraat 1, Gent",  # kot-typisch adres (studentenwijk)`.
- [ ] **Step 3: zone_rapport** — breid uit met de zone-naam:

```python
    attributen = gis_zones.load_ring_attributen(POC_ROOT)
    for adres, (lon, lat) in adressen.items():
        resultaten = {laag: gis_zones.zone_result(zones, laag, lon, lat) for laag in sorted(zones)}
        for laag in sorted(zones):
            naam = gis_zones.attribuut_result(zones, attributen, laag, lon, lat)
            if naam not in ("in", "niet-in"):
                resultaten[laag + "=" + naam] = naam
        print(f"{adres}: {resultaten}  (lagen: {versies})")
```

- [ ] **Step 4: Cache bouwen (netwerk)**: `python3 fetch_sources.py && python3 fetch_sources.py --geocode` → 5 lagen in het rapport; bewaar de kotzone-namen per adres (pint Task 4).
- [ ] **Step 5: Pinningtest** in `tests/test_gis_zones.py` (waarden bijstellen op het --check-rapport; primair: Veldstraat en Overpoortstraat liggen in het centrum-gamma):

```python
def test_kotzone_pinning_fixture_adressen():
    zones = gis_zones.load_zones(POC_ROOT)
    attributen = gis_zones.load_ring_attributen(POC_ROOT)
    assert len(attributen["gent-kotzone"]) == len(zones["gent-kotzone"])  # ring-dekking
    for adres in ("Veldstraat 1, Gent", "Overpoortstraat 1, Gent"):
        lon, lat = gis_zones.lookup_address(POC_ROOT, adres)
        naam = gis_zones.attribuut_result(zones, attributen, "gent-kotzone", lon, lat)
        assert naam not in ("niet-in", "in", "onbekend"), adres
```

- [ ] **Step 6: Suite + Commit**: `git add poc-gent/fetch_sources.py poc-gent/fixtures/gis-zones.geojson poc-gent/fixtures/addresses.json poc-gent/fixtures/source/kotzones-gent.json poc-gent/fixtures/source/source.meta.json poc-gent/tests/test_gis_zones.py && git commit -m "feat(poc-gent): echte kotzone-laag in de broncache — 20 benoemde zones, Overpoortstraat als kotadres, --check drukt zone-namen"`.

---

### Task 3: Verhuurder-persona's en fixtures

**Files:**
- Modify: `poc-gent/fixtures/personas.json`, `poc-gent/fixtures/magda.json`, `poc-gent/fixtures/wallets.json`, `poc-gent/fixtures/identiteiten.json`

**Interfaces:**
- Produces: persona's `wouter, saartje, gregory, lea, milan, karel` (allen `applicantType: burger`; `address` per --check-rapport: wouter/saartje/gregory/lea/karel → `"Overpoortstraat 1, Gent"`, milan → start `"Ottergemsesteenweg-Zuid 1, Gent"` correctie naar `"Overpoortstraat 1, Gent"`); slots `omzetten` (alleen gregory `ja`, rest `nee`) en `typeKot` (`kamer` behalve lea `residentie`); `gent:kotregister`-record voor allen (`saartje`: `{"status": "gemeld"}`, rest `{"status": "nieuw"}`).

- [ ] **Step 1: personas.json** — zes entries (spiegel bestaande velden):

```json
    { "id": "wouter", "label": {"nl": "Wouter — verhuurt een kamer in zijn woning aan de Overpoort"},
      "edge": null,
      "situatieschets": "Ik wil vanaf volgend academiejaar een kamer in mijn huis aan de Overpoortstraat aan een student verhuren.",
      "intentSlots": {"applicantType": "burger", "address": "Overpoortstraat 1, Gent", "omzetten": "nee", "typeKot": "kamer"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "saartje", "label": {"nl": "Saartje — haar kotadres staat al als gemeld kot genoteerd"},
      "edge": "al-gemeld",
      "situatieschets": "Ik verhuur al een kot aan de Overpoortstraat en wil mijn melding actualiseren.",
      "intentSlots": {"applicantType": "burger", "address": "Overpoortstraat 1, Gent", "omzetten": "nee", "typeKot": "kamer"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "gregory", "label": {"nl": "Gregory — zet zijn woning om naar twee koten"},
      "edge": "omzetting-zonder-vergunning",
      "situatieschets": "Ik wil mijn woning aan de Overpoortstraat omzetten naar twee aparte koten en die dan verhuren.",
      "intentSlots": {"applicantType": "burger", "address": "Overpoortstraat 1, Gent", "omzetten": "ja", "typeKot": "studio"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "lea", "label": {"nl": "Lea — meldt een studentenresidentie"},
      "edge": "residentie",
      "situatieschets": "Ik beheer een studentenresidentie aan de Overpoortstraat en wil de kamers melden.",
      "intentSlots": {"applicantType": "burger", "address": "Overpoortstraat 1, Gent", "omzetten": "nee", "typeKot": "residentie"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "milan", "label": {"nl": "Milan — corrigeert het kotadres tijdens de contextcheck"},
      "edge": "correctie-tijdens-h1",
      "situatieschets": "Ik ga een kot verhuren — ik noemde eerst het verkeerde adres in Gentbrugge, het wordt de Overpoortstraat.",
      "intentSlots": {"applicantType": "burger", "address": "Ottergemsesteenweg-Zuid 1, Gent", "omzetten": "nee", "typeKot": "kamer"},
      "antwoorden": {}, "corrections": {"address": "Overpoortstraat 1, Gent"},
      "gebruikGegevens": "gegeven", "inzendingBevestigen": "gegeven" },
    { "id": "karel", "label": {"nl": "Karel — weigert de inzending bij H4"},
      "edge": "weigert-inzending",
      "situatieschets": "Ik wil een studio aan de Overpoortstraat als kot melden, maar twijfel nog over de belasting.",
      "intentSlots": {"applicantType": "burger", "address": "Overpoortstraat 1, Gent", "omzetten": "nee", "typeKot": "studio"},
      "antwoorden": {}, "corrections": {}, "gebruikGegevens": "gegeven", "inzendingBevestigen": "geweigerd" }
```

- [ ] **Step 2: magda.json** — zes entries, allen `{"gent:kotregister": {"status": "nieuw"}}` behalve `"saartje": {"gent:kotregister": {"status": "gemeld"}}` (geen kentekens nodig).
- [ ] **Step 3: wallets + identiteiten** — zes pid-attestaties (loa substantial) + machtiging leeg; identiteiten `type: burger` met unieke pseudoniemen `rrn-••••402` e.d. en namen: Wouter De Craene (402), Saartje Verhaege (715), Gregory Peirens (268), Lea Hoste (833), Milan Segers (594), Karel Boone (077).
- [ ] **Step 4: Rooktest + Commit**: `python3 run.py --package gent-mobiliteit-ondernemer --persona wouter` → `uitkomst: escalatie` (persona verstoort oude pakketten niet); suite groen; commit `feat(poc-gent): zes verhuurder-persona's met kotregister-, wallet- en identiteitsfixtures`.

---

### Task 4: Pakket `gent-kot-verhuurder` + golden set

**Files:**
- Create: `poc-gent/packages/gent-kot-verhuurder/manifest.json`, `decision-tables.json`, `golden/scenarios.jsonl`
- Modify: `poc-gent/adapters/backoffice_mock.py` (contract `district09-koteloket`)
- Test: rooktests per persona, `eval.py --package gent-kot-verhuurder`

**Interfaces:**
- Produces: pakket-id `gent-kot-verhuurder`, `lifeEventCode: GT-KOT-01`; services `kot-melden` + `info-omgevingsvergunning`/`info-conformiteitsattest`/`info-kotbelasting`/`info-afvalkalender`; slots `applicantType/address/omzetten/typeKot` + authentiek `bestaandeMelding` (`gent:kotregister`); gisCheck `kotzone` (attribuut); dataCheck `afvalkalender` (fallback, hergebruik); `submission.contract: district09-koteloket`; `kpiDrempels` gelijk aan default.

- [ ] **Step 1: backoffice_mock**: `_CONTRACTEN` += `"district09-koteloket"`.
- [ ] **Step 2: manifest.json**:

```json
{
  "packageId": "gent-kot-verhuurder",
  "version": "0.1.0",
  "status": "concept",
  "lifeEventCode": "GT-KOT-01",
  "title": "GT-KOT-01 — Kot verhuren: melden via het koteloket",
  "texts": {
    "intro": "Ik help je regelen wat je nodig hebt om een kot te verhuren: de melding via het koteloket, de regels rond omzetten, het conformiteitsattest en de kotbelasting.",
    "scope": "Deze assistent gaat over gemeentelijke regelingen voor verhuurders van studentenkamers in Gent.",
    "aiToelichting": "Ik ben een AI-assistent van Stad Gent. Ik stel voor en leg uit; jij beslist en bevestigt.",
    "weigering": "Als ik het niet zeker weet, zeg ik dat eerlijk en verbind ik je door met een medewerker.",
    "escalatie": "Twijfel of een bijzondere situatie? Dan neemt een medewerker van Gentinfo het van me over.",
    "contextZin": "U bent {applicantType} en wilt een kot verhuren aan: {address}. Woning omzetten: {omzetten}."
  },
  "contextSchema": {
    "slots": {
      "applicantType": {"type": "enum", "values": ["burger", "ondernemer", "organisatie"], "required": true, "authenticSource": null, "vraag": "Bent u particulier, ondernemer of organisatie?"},
      "address": {"type": "string", "required": true, "authenticSource": null, "vraag": "Op welk adres ligt het kot?"},
      "omzetten": {"type": "enum", "values": ["ja", "nee"], "required": true, "authenticSource": null, "vraag": "Zet u een bestaande woning om naar kot(s)?"},
      "typeKot": {"type": "enum", "values": ["kamer", "studio", "residentie"], "required": true, "authenticSource": null, "vraag": "Wat voor studentenhuisvesting verhuurt u?"},
      "bestaandeMelding": {"type": "enum", "values": ["gemeld", "nieuw"], "required": false, "authenticSource": "gent:kotregister", "vraag": null}
    }
  },
  "gisChecks": [
    {"id": "kotzone", "layer": "gent-kotzone", "input": "address", "output": "kotzone", "attribuut": "kotzone_na"},
    {"id": "kotzoneAanwezig", "layer": "gent-kotzone", "input": "address", "output": "kotzoneIn"}
  ],
  "dataChecks": [
    {"id": "afvalkalender", "dataset": "ivago-ophaalkalender", "input": "address",
     "outputs": ["afvalRest", "afvalPmd", "afvalGlas", "afvalPapier"], "unknownPolicy": "fallback"}
  ],
  "authenticSources": [
    {"slot": "bestaandeMelding", "source": "gent:kotregister", "purpose": "vaststellen of dit adres al als gemeld kot genoteerd staat"}
  ],
  "submission": {"contract": "district09-koteloket"},
  "kpiDrempels": {"kpi01_min": 90.0, "kpi01_doel": 95.0, "kpi02_min": 100.0, "kpi03_min": 100.0, "kpi04_min": 90.0},
  "decisionTables": "decision-tables.json",
  "services": {
    "kot-melden": {
      "type": "inzending", "vereistAuth": true, "minLoA": "substantial",
      "titel": "Kot melden via het koteloket",
      "uitleg": "Meldingsplicht: wie een kot verhuurt, meldt het pand en de kamers via het koteloket (Kotatgent). Het koteloket controleert de melding vóór publicatie op de kotenzoeker.",
      "documenten": [],
      "formulier": [
        {"veld": "kotadres", "bron": "slot:address"},
        {"veld": "kotzone", "bron": "slot:kotzone"},
        {"veld": "type-studentenhuisvesting", "bron": "slot:typeKot"},
        {"veld": "woning-omzetten", "bron": "slot:omzetten"},
        {"veld": "koteloket-status", "bron": "gent:kotregister.status"}
      ],
      "validaties": [
        {"id": "V1-al-gemeld", "wanneer": {"koteloket-status": "gemeld"}, "ernst": "waarschuwing",
         "melding": "Dit adres staat al als gemeld kot genoteerd: beheer uw melding via het koteloket."},
        {"id": "V2-omzetten-zonder-vergunning", "wanneer": {"woning-omzetten": "ja"}, "ernst": "waarschuwing",
         "melding": "Een omzettingsvergunning is nodig vóór u het kot verhuurt; vraag die eerst aan (zie de informatie over de omgevingsvergunning)."},
        {"id": "V3-residentie", "wanneer": {"type-studentenhuisvesting": "residentie"}, "ernst": "waarschuwing",
         "melding": "Grote studentenresidenties krijgen een voorbehandeling via kot@stad.gent vóór de online melding."}
      ]
    },
    "info-omgevingsvergunning": {"type": "info", "vereistAuth": false,
      "titel": "Omgevingsvergunning bij omzetten naar kot",
      "uitleg": "Een woning omzetten of (ver)bouwen naar kot(s) vereist een omgevingsvergunning, met de Gentse stedenbouwkundige voorschriften en de Vlaamse Codex Wonen.",
      "formulier": [], "validaties": []},
    "info-conformiteitsattest": {"type": "info", "vereistAuth": false,
      "titel": "Conformiteitsattest voor uw kot",
      "uitleg": "Na controle op de Vlaamse woningkwaliteitsnormen krijgt uw kot een conformiteitsattest; dat wordt op de kotenzoeker getoond.",
      "formulier": [], "validaties": []},
    "info-kotbelasting": {"type": "info", "vereistAuth": false,
      "titel": "Kotbelasting vanaf 2027",
      "uitleg": "Vanaf 2027 geldt een belasting op studentenkoten in Gent; verhuurders mogen die niet zomaar doorschuiven naar de student.",
      "formulier": [], "validaties": []},
    "info-afvalkalender": {"type": "info", "vereistAuth": false,
      "titel": "Afvalophaling op uw kotadres (IVAGO)",
      "uitleg": "Ophaaldagen per fractie voor uw kotadres, uit de IVAGO-ophaalkalender (open data). Staat uw straat er niet bij, raadpleeg dan gent.be/recycle of de Recycle!-app.",
      "formulier": [], "validaties": []}
  },
  "golden": "golden/scenarios.jsonl"
}
```

- [ ] **Step 3: decision-tables.json**:

```json
{
  "id": "R-kot-verhuurder",
  "version": "2026.11",
  "rules": [
    {"id": "RK1", "when": {"applicantType": "burger", "kotzoneIn": "in"}, "then": {"transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"]}, "legalBasis": "Gent kotreglement — meldingsplicht koteloket (stad.gent)", "uitleg": "U gaat een kot verhuren: meld het pand en de kamers via het koteloket — de melding wordt gecontroleerd vóór publicatie."},
    {"id": "RK2", "when": {"applicantType": "burger", "omzetten": "ja"}, "then": {"transactions": [], "info": ["info-omgevingsvergunning"]}, "legalBasis": "Vlaamse Codex Wonen / Gentse stedenbouwkundige voorschriften (stad.gent)", "uitleg": "U zet een woning om naar kot(s): daarvoor is een omgevingsvergunning nodig vóór de verhuur."},
    {"id": "RK3", "when": {"applicantType": "burger", "kotzoneIn": "niet-in"}, "then": {"transactions": [], "info": ["info-conformiteitsattest", "info-kotbelasting"]}, "legalBasis": "Gent kotreglement — kotzones (open data Stad Gent)", "uitleg": "Uw adres valt buiten de kotzone-indeling: het koteloket beoordeelt de melding handmatig — u krijgt alleen de algemene informatie."}
  ],
  "unknownPolicy": "escalate"
}
```

- [ ] **Step 4: golden/scenarios.jsonl** (info-volgorde = regelvolgorde; Overpoortstraat in LEZ → info-lez bestaat niet hier, dus geen):

```
{"scenarioId": "kot-01-wouter-melding", "persona": "wouter", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"], "status": "gereed"}}
{"scenarioId": "kot-02-saartje-al-gemeld", "persona": "saartje", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"], "status": "gereed-met-waarschuwing"}}
{"scenarioId": "kot-03-gregory-omzetten", "persona": "gregory", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting", "info-omgevingsvergunning"], "status": "gereed-met-waarschuwing"}}
{"scenarioId": "kot-04-lea-residentie", "persona": "lea", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"], "status": "gereed-met-waarschuwing"}}
{"scenarioId": "kot-05-milan-adrescorrectie", "persona": "milan", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"], "status": "gereed"}}
{"scenarioId": "kot-06-karel-h4-weigering", "persona": "karel", "expect": {"outcome": "paden", "transactions": ["kot-melden"], "info": ["info-afvalkalender", "info-conformiteitsattest", "info-kotbelasting"], "status": "geweigerd"}}
```

- [ ] **Step 5: Rooktests + eval**: `python3 run.py --package gent-kot-verhuurder --persona wouter` (enz.) → routing/statussen zoals de golden; `../nldt/.venv/bin/python eval.py --package gent-kot-verhuurder` → 6/6 GO; regressie: beide bestaande evals GO + suite groen. Bij afwijkende info-volgorde golden aanpassen aan de werkelijke regelaggregatie.
- [ ] **Step 6: Commit**: `feat(poc-gent): levensgebeurtenis-pakket gent-kot-verhuurder — koteloket-melding als transactie, kotzone-attribuut in het formulier, golden set 6/6 en go/no-go GO`.

---

### Task 5: Injectiesuite voor het kotpakket

**Files:**
- Modify: `poc-gent/fixtures/injecties.json`, `poc-gent/tests/test_injectie.py`

**Interfaces:**
- Produces: `pakketten["gent-kot-verhuurder"]` met personas direct/documentnaam/tool=wouter, indirect=milan, exfiltratie=karel; vrijeSlots `["address"]`; overigeSlots `["omzetten"]`; schone waarden address=Overpoortstraat, omzetten=nee, kot-schets.

- [ ] **Step 1: fixture**:

```json
    "gent-kot-verhuurder": {
      "personas": {"direct": "wouter", "indirect": "milan", "documentnaam": "wouter",
                   "tool-misbruik": "wouter", "exfiltratie": "karel"},
      "vrijeSlots": ["address"],
      "overigeSlots": ["omzetten"],
      "schoneWaarden": {
        "address": "Overpoortstraat 1, Gent",
        "omzetten": "nee",
        "situatieschets": "Ik wil een kamer in mijn huis aan een student verhuren."
      }
    }
```

- [ ] **Step 2: tests** in `test_injectie.py`: `len(aanvallen(POC_ROOT, "gent-kot-verhuurder")) == 24` met personas `{wouter, milan, karel}`; `voer_uit(POC_ROOT, "gent-kot-verhuurder")` zonder schendingen.
- [ ] **Step 3: Run**: `eval.py --injectie --package gent-kot-verhuurder` → 24/24; de twee bestaande suites ongewijzigd (34/34, 24/24). **Step 4: Commit**: `feat(poc-gent): injectieconfig voor het kotpakket — 24/24 weerstand`.

---

### Task 6: Simulatie — derde dropdown-optie met kotzone-kaart

**Files:**
- Modify: `poc-gent/fetch_sources.py` (`--kaart-kot` via gegeneraliseerde persoonsadressen-cache), `simulation/build_simulation.py`, `simulation/template.html`, `simulation/vertaal_gent.py`, `simulation/test_build_gent_burger.py` (of nieuw `test_build_gent_kot.py`), `simulation/test_vertaal_gent.py`, `simulation/verify_static.mjs`
- Create: `poc-gent/fixtures/source/kaart-kot.json` (gegenereerd)

**Interfaces:**
- Produces: `haal_kaart_persoonsadressen(poc_root, personas, doel_pad)` (hergebruikt door `--kaart-burger` én `--kaart-kot`); `build_gent("gent-kot-verhuurder")` met per persona `kaart.mode == "kot"` (één zone-laag `gent-kotzone` + zone-naam in `kaart.zones["gent-kotzone"]` als naam en `kaart.zoneNaam`); data `data["gentKot"]`; template-GP derde optie `["gentKot","GT-KOT-01 · kot verhuren","GT-KOT-01 · renting out a kot"]`; kaartStap behandelt mode `burger` én `kot` via één generieke zone-lus met kleurmap.

- [ ] **Step 1: fetch**: hernoem `haal_kaart_burger` intern naar `haal_kaart_persoonsadressen(poc_root, personas, doel)` en laat `--kaart-burger`/`--kaart-kot` die aanroepen met `BURGER_PERSONAS`/`KOT_PERSONAS = ("wouter","saartje","gregory","lea","milan","karel")`; bronnen-meta zoals bestaand. Bouw: `python3 fetch_sources.py --kaart-burger --kaart-kot` (grens uit kaart.json, offline).
- [ ] **Step 2: build_simulation**: `GENT_PACKAGE_PERSONAS["gent-kot-verhuurder"]` + kaartentry `("kaart-kot.json", _kaart_blok_kot)`; `_kaart_blok_kot` spiegel van `_kaart_blok_burger` maar met `burger_zones = {"gent-kotzone": ringen}`, `mode: "kot"`, plus `"zoneNaam": zone_uit-naam via attribuut_result` en `bron: "kotzones: Stad Gent open data (Modellicentie Gratis Hergebruik) · gemeentegrens: OSM/Nominatim (ODbL)"`; `main()`: `data["gentKot"] = build_gent("gent-kot-verhuurder")`.
- [ ] **Step 3: template**: GP derde optie; `kaartStap` burger-tak veralgemeniseerd: `if (k.mode === "burger" || k.mode === "kot")` en de drie vaste zone-paden vervangen door een lus over `Object.entries(z.zones)` met kleurmap `{"gent-parkeertariefzone":["#a78bfa1f","#a78bfa99"], "gent-bewonerszone":["#34d39922","#34d39999"], "gent-lez":["#f59e0b1f","#f59e0b99"], "gent-kotzone":["#38bdf822","#38bdf899"]}` (volgorde: lez→bewoners→tarief→kot via vaste key-array zodat burgerweergave identiek blijft); kop/legenda: mode `kot` krijgt eigen regels (kotzone + nieuwe woning/kot); `renderGentStatic`: burger-tak ook voor `kot` (zone-labels generiek: LBL-uitbreiding `gent-kotzone: ["kotzone","kot zone"]`, en bij `k.zoneNaam` een extra kopregel `kotzone: <naam>`); dropdown-teksten in de optie-array.
- [ ] **Step 4: vertaal_gent**: zes persona-labels + zes schetsen, diensttitels (5), RK1–RK3-uitleg, V1–V3-meldingen, vragen ("Op welk adres ligt het kot?", "Zet u een bestaande woning om naar kot(s)?", "Wat voor studentenhuisvesting verhuurt u?"), doelbinding "vaststellen of dit adres al als gemeld kot genoteerd staat", stap-titel data-lookup bestaat al, kot-kaartbronregel.
- [ ] **Step 5: tests**: nieuw `simulation/test_build_gent_kot.py` (zes statussen: wouter gereed, saartje/gregory/lea gereed-met-waarschuwing, milan gereed, karel geweigerd; `lifeEventCode == "GT-KOT-01"`; per persona `mode == "kot"`, `svg.zones["gent-kotzone"]` gevuld, `zoneNaam` gevuld, `svg.routes is None`); `test_vertaal_gent.py`: derde build met `onbekend() == []`; `test_build_gent_burger.py` ongewijzigd groen; `verify_static.mjs`: na de burger-switch een kot-switch (`ds.gentPackage("gentKot")`, kaart = grens + kotzone + kot → 5 tags, `zoneNaam`-weergave via kaart5info string check "kotzone:"), terug naar `gent` (6 tags).
- [ ] **Step 6: Build + verify**: `../nldt/.venv/bin/python build_simulation.py && node verify_static.mjs` → OK; `../nldt/.venv/bin/python -m pytest -q` groen. **Step 7: Commit**: `feat(simulation): derde levensgebeurtenis in de Gent-dropdown — kot verhuren met kotzone-kaart en zone-naam, volledig NL/EN`.

---

### Task 7: README's en eindcontrole

**Files:**
- Modify: `poc-gent/README.md`, `simulation/README.md`

- [ ] **Step 1: poc-gent/README** — pakket GT-KOT-01 toevoegen aan de multi-package-sectie (diensten, kotzones-dataset + attribuut-capaciteit, `--kaart-kot`, eval/injectie-commando's).
- [ ] **Step 2: simulation/README** — derde dropdown-optie in de tab-5-sectie.
- [ ] **Step 3: Eindcontrole**: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` (alles groen) en voor elk der drie pakketten `eval.py [--package …]` → GO; beide injectiesuites 34/24/24; `python3 fetch_sources.py --check` (5 lagen incl. kotzone-namen); `cd ../simulation && ../nldt/.venv/bin/python -m pytest -q && node verify_static.mjs && ../nldt/.venv/bin/python build_simulation.py`.
- [ ] **Step 4: Commit**: `docs: README's voor het kotpakket gent-kot-verhuurder en de derde dropdown-optie`.
