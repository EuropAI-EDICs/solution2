# Piloot Gent F3 — documenten → H4-inzending → ontvangstbewijs → vervolgsamenvatting (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bouw F3 van `poc-gent/`: na H3 volgen de documentencontrole (FR-12), de H4-poort (expliciete bevestiging vóór inzending, FR-15), idempotente inzending in de backoffice-mock mét ontvangstbewijs (FR-16) en de vervolgsamenvatting (FR-18), plus een statusraadplegingsmodus (FR-19). Daarnaast: de echte databronnen die nu beschikbaar zijn ontsluiten (VKBO live keyless; GIPOD live-of-mock; BeSt Address als geregistreerd productiepad), de uitgestelde review-items (Magda-ontbreekt-persona, catalogus-aanscherpingen, event-masking) en de simulatietab meenemen in fase 3.

**Architecture:** Voortbouwend op F1/F1.5/F2 (config-is-data; LLM stelt voor / engine beslist / mens bevestigt). Nieuw: `core/documents.py` (documentencontrole), `adapters/backoffice_mock.py` + `core/submit.py` (idempotente inzending + ontvangstbewijs + statusmapping INT-03/06), H4-gate, schema v1.2 (`transaction.submission`), event-masking van intake/H1-payloads (SEC-05), en broncache-uitbreiding in `fetch_sources.py` (VKBO echt, GIPOD echt-of-mock).

**Tech Stack:** Python 3.11+ stdlib-only voor `core/` en `adapters/`; jsonschema alleen voor run-validatie onder `../nldt/.venv`; pytest.

**Spec:** design §5 (stappen 8–9 + S8/S9, H4, escalatie H5), §6 (backoffice/Gentinfo-adapters), §11 (fasering F3 = FR-12/14/15/16/18/19/20). Bronverkenning 2026-10-30: VKBO OGC Features keyless (`geo.api.vlaanderen.be/VKBO/ogc/features/v1`, bbox-query, properties `Commerciele_naam`, `AR_straat` e.a.); GIPOD API `gipod.api.vlaanderen.be` (detail-auth; publiek via LDES — probe, fallback mock); BeSt Address = officiële self-host REST ("Best in a Box", opendata.bosa.be/download/best/bestinabox) — productiepad-registratie, Nominatim blijft de werkende echte geocoder.

## Global Constraints

- Alle code draait met `python3` (3.11+) zonder netwerk; geen echte persoonsgegevens — echte open-registerdata (VKBO) mag als broncache; persona's blijven synthetisch.
- `core/`, `adapters/`, `run.py`, `eval.py` stdlib-only; `jsonschema` alléén in `core/runs.py::validate` en tests/eval onder `../nldt/.venv/bin/python`.
- Tests: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` (na F3: `97 passed` voor de poc-gent-suite; de simulation-embedtests lopen apart).
- Deterministische replay: geen muurklok in canonieke run-inhoud; ontvangstbewijzen zijn deterministisch afgeleid (hash-gebaseerd), niet `random`.
- Docstrings/teksten Nederlands; productie-identifiers Engels; testnamen mogen Nederlands.
- Commit per taak, conventional commits scope `poc-gent` (sim-tab: scope `simulation`), Nederlandse samenvatting.
- Statuswaarden blijven: `gereed | gereed-met-waarschuwing | blokkade | geweigerd | escalatie`; nieuw: inzendingstatus `geaccepteerd | in-wachtrij | afgewezen | technisch-mislukt` (FR-16) + `niet-ingediend` bij H4-weigering of blokkade.
- Event-log blijft waardevrij: intake-situatieschets en H1-contextwaarden komen níet langer als ruwe tekst in events (hash + feitnamen; run-artefact blijft volledig).

---

### Task 1: Bronnenlaag-uitbreiding — VKBO (echt), GIPOD (echt-of-mock), BeSt Address (registratie)

**Files:**
- Modify: `poc-gent/fetch_sources.py`
- Create: `poc-gent/fixtures/source/gipod-gent.json` (door fetch of door mock-fallback)
- Test: `poc-gent/tests/test_bronnen.py`

**Interfaces:**
- Produces (voor latere fasen en de broncatalogus):
  - `fetch_sources.haal_vkbo(poc_root, bbox="3.700,51.030,3.760,51.080", limit=200) -> dict` — echte VKBO-features via OGC API Features (keyless); normaliseert naar `[{"naam", "straat", "huisnr", "postcode", "inschrijving"}]` (keys `Commerciele_naam`/`Afgekorte_naam`, `AR_straat`, `AR_huisnr`/`AR_busnr`, `AR_postcode`, `Datum_inschrijving`); cache onder `fixtures/source/vkbo-gent.json` mét meta-entry.
  - `fetch_sources.haal_gipod(poc_root) -> dict` — probeert de publieke LDES/OGC-Features-ingang van GIPOD (swagger `https://gipod.api.vlaanderen.be/swagger/v1/swagger.json`: zoek paden met `mobilityhindrance` zonder auth-policy); bij falen (netwerk/404/auth) valt hij terug op `fixtures/source/gipod-gent.json` als meegeleverde **testdata-mock** en registreert `"mode": "mock"` in de meta.
  - `fetch_sources.BEST_ADDRESS_PAD` — constante met de productiepad-documentatie (Best in a Box user-guide URL + docker) die in `source.meta.json` wordt geregistreerd bij een fetch-run.
  - `--bronnen` CLI-vlag: voert VKBO+GIPOD+registratie uit (naast de bestaande zone-fetch).

- [ ] **Step 1: Schrijf de falende test** (`poc-gent/tests/test_bronnen.py`):

```python
"""Bronnenlaag F3: VKBO-normalisatie, GIPOD-mockfallback en meta-volledigheid."""

import json
from pathlib import Path

import fetch_sources

POC_ROOT = Path(__file__).resolve().parents[1]


def test_vkbo_normalisatie_werkt_op_waren():
    features = [{"type": "Feature", "properties": {
        "Commerciele_naam": "BVBA Testbouw", "Afgekorte_naam": "Testbouw",
        "AR_straat": "Korenmarkt", "AR_huisnr": "1", "AR_postcode": "9000",
        "Datum_inschrijving": "2015-03-02"}}]
    rijen = fetch_sources.normaliseer_vkbo(features)
    assert rijen == [{"naam": "BVBA Testbouw", "straat": "Korenmarkt",
                      "huisnr": "1", "postcode": "9000", "inschrijving": "2015-03-02"}]


def test_gipod_mockfallback_levert_testdata_en_mode():
    pad = POC_ROOT / "fixtures" / "source" / "gipod-gent.json"
    data = json.loads(pad.read_text(encoding="utf-8"))
    assert data["mode"] == "mock"
    assert data["innames"], "mock-innames mogen niet leeg zijn"
    for inn in data["innames"]:
        assert {"id", "straat", "type", "van", "tot"} <= set(inn)


def test_gipod_mock_wordt_nooit_herschreven(tmp_path, monkeypatch):
    (tmp_path / "source").mkdir()
    import shutil
    mock = POC_ROOT / "fixtures" / "source" / "gipod-gent.json"
    doel = tmp_path / "source" / "gipod-gent.json"
    shutil.copy(mock, doel)
    foraf = doel.read_text(encoding="utf-8")
    monkeypatch.setattr(fetch_sources, "SOURCE_DIR", tmp_path / "source")
    monkeypatch.setattr(fetch_sources, "GIPOD_SWAGGER", "https://onbereikbaar.voor.test/swagger.json")
    uitslag = fetch_sources.haal_gipod(POC_ROOT)
    assert uitslag["mode"] == "mock"
    assert doel.read_text(encoding="utf-8") == foraf


def test_best_address_productiepad_geregistreerd():
    assert "bestinabox" in fetch_sources.BEST_ADDRESS_PAD.lower()
```

- [ ] **Step 2: Draai en verifieer falen**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_bronnen.py -q`
Expected: FAIL — `AttributeError`/`ImportError` op `normaliseer_vkbo` e.a.

- [ ] **Step 3: Implementeer**

In `poc-gent/fetch_sources.py`: voeg bovenin (na `ADRESSEN`) toe:

```python
BEST_ADDRESS_PAD = ("productiepad officiële geocoding: BeSt Address Web API — "
                    "https://opendata.bosa.be/download/best/bestinabox/best-webapi-user-guide.pdf "
                    "(self-host via docker bosa/opendata-best-webapi); PoC gebruikt OSM Nominatim ( echt, ODbL)")
VKBO_URL = "https://geo.api.vlaanderen.be/VKBO/ogc/features/v1/collections/Vkbo/items"
GIPOD_SWAGGER = "https://gipod.api.vlaanderen.be/swagger/v1/swagger.json"
```

en (nieuwe functies; hergebruik `_fetch_json`, `SOURCE_DIR`, `_now`):

```python
def normaliseer_vkbo(features: list[dict]) -> list[dict]:
    rijen = []
    for f in features:
        p = f.get("properties") or {}
        busnr = (p.get("AR_busnr") or "").strip()
        rijen.append({
            "naam": (p.get("Commerciele_naam") or "").strip()
                    or (p.get("Afgekorte_naam") or "").strip() or "onbekend",
            "straat": (p.get("AR_straat") or "").strip(),
            "huisnr": ((p.get("AR_huisnr") or "").strip()
                       + (f" bus {busnr}" if busnr else "")),
            "postcode": (p.get("AR_postcode") or "").strip(),
            "inschrijving": (p.get("Datum_inschrijving") or "")[:10],
        })
    return rijen


def haal_vkbo(poc_root: Path, bbox: str = "3.700,51.030,3.760,51.080", limit: int = 200) -> dict:
    data = _fetch_json(f"{VKBO_URL}?bbox={bbox}&limit={limit}")
    rijen = normaliseer_vkbo(data.get("features", []))
    (SOURCE_DIR / "vkbo-gent.json").write_text(json.dumps(rijen, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"bron": VKBO_URL, "aantal": len(rijen), "licentie": "VKBO (Vlaanderen) — open data"}


def haal_gipod(poc_root: Path) -> dict:
    """Publieke GIPOD-LDES proberen; de echt-cache (gipod-gent-echt.json) is
    een fetch-artefact en wordt níet gecommit. De gecommitte mock-fixture
    (gipod-gent.json) is de stabiele offline testbasis en wordt nooit
    herschreven of herlabeld."""
    echt_pad = SOURCE_DIR / "gipod-gent-echt.json"
    try:
        swagger = _fetch_json(GIPOD_SWAGGER)
        kandidaten = []
        for pad, operaties in swagger.get("paths", {}).items():
            if "mobilityhindrance" not in pad.lower().replace("-", ""):
                continue
            get = operaties.get("get") or {}
            if "Auth policies" in (get.get("description") or ""):
                continue
            kandidaten.append(pad)
        if not kandidaten:
            raise RuntimeError("geen publiek (auth-vrij) mobilityhindrance-pad in swagger")
        proef = None
        gebruikte_url = None
        fouten = []
        for kandidaat in kandidaten[:3]:
            url = f"https://gipod.api.vlaanderen.be{kandidaat}" if kandidaat.startswith("/") else kandidaat
            try:
                proef = _fetch_json(url)
                gebruikte_url = url
                break
            except Exception as poging:
                fouten.append(f"{kandidaat}: {poging}")
        if proef is None:
            raise RuntimeError("publieke LDES-ingangen onbereikbaar: " + "; ".join(fouten))
        echt_pad.write_text(json.dumps({"mode": "echt", "bron": gebruikte_url, "ruw": proef},
                                       ensure_ascii=False), encoding="utf-8")
        return {"mode": "echt", "bron": gebruikte_url}
    except Exception as fout:
        mock_pad = SOURCE_DIR / "gipod-gent.json"
        if not mock_pad.is_file():
            raise RuntimeError(f"GIPOD onbereikbaar en geen mock aanwezig: {fout}")
        return {"mode": "mock", "fout": str(fout), "mock": mock_pad.name}
```

Maak de mock-testdata `poc-gent/fixtures/source/gipod-gent.json`:

```json
{
  "mode": "mock",
  "bron": "GIPOD (Athumi/Digitaal Vlaanderen) — publieke LDES bereikbaar; dit is de stabiele offline testdata-mock (echt-cache: gipod-gent-echt.json na --bronnen)",
  "innames": [
    {"id": "GP-2026-0001", "straat": "Korenmarkt", "type": "grondwerk", "van": "2026-11-02", "tot": "2026-11-06"},
    {"id": "GP-2026-0002", "straat": "Veldstraat", "type": "evenement", "van": "2026-12-12", "tot": "2026-12-13"}
  ]
}
```

Breid `main()` uit met `ap.add_argument("--bronnen", action="store_true")`; in `main()`: na `build_cache()` altijd `meta_document["bronnen"]["bestAddress"] = {"productiepad": BEST_ADDRESS_PAD, "pocGeocoder": "OSM Nominatim (ODbL)"}` schrijven (hergebruik het bestaande meta-lees/-schrijfpad); bij `--bronnen`: `haal_vkbo(POC_ROOT)` en `haal_gipod(POC_ROOT)` uitvoeren en print hun samenvatting.

- [ ] **Step 4: Draai alle tests + smoke**

Run: `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → `77 passed` (74 + 3).
Smoke (netwerk): `python3 fetch_sources.py --bronnen` → print VKBO-aantal (>0) en GIPOD-mode (`mock` bij auth-fal).

- [ ] **Step 5: Commit**

Run eerst `python3 fetch_sources.py --bronnen` zodat `fixtures/source/vkbo-gent.json` gevuld is, en commit de cache mee (committed-cache-doctrine, zoals de F1.5-zonecaches):

```bash
git add poc-gent/fetch_sources.py poc-gent/fixtures/source/gipod-gent.json poc-gent/fixtures/source/vkbo-gent.json poc-gent/tests/test_bronnen.py
git commit -m "feat(poc-gent): bronnenlaag F3 — VKBO echt (OGC Features), GIPOD echt-of-mock, BeSt Address productiepad"
```

---

### Task 2: Catalogus v0.3.0 — documenteneisen, vereistAuth- en broncontroles

**Files:**
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json` (version 0.3.0)
- Modify: `poc-gent/core/catalog.py`
- Test: `poc-gent/tests/test_catalog.py`

**Interfaces:**
- Produces: `services[<id>].documenten: [{"id": str, "titel": str, "verplicht": bool}]` (inzendingen: niet-lege lijst; info: leeg); catalogus wijst af: inzending zonder `documenten`-sleutel, `vereistAuth` ontbreekt of is geen bool, `type == "inzending"` zonder `vereistAuth: true`, en dubbele `source`-waarden in `authenticSources`.
- Manifest: `ontheffing-lez` en `ontheffing-autovrij` krijgen `"documenten": [{"id": "kentekenbewijs", "titel": "Kentekenbewijs van het voertuig", "verplicht": true}]` (lez) resp. hetzelfde bewijs plus `{"id": "machtiging", "titel": "Machtiging indien u namens iemand handelt", "verplicht": false}` (autovrij).

- [ ] **Step 1: Falende tests** (toevoegen aan `test_catalog.py`):

```python
def test_documenteneisen_verplicht_voor_inzendingen(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["documenten"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="documenten"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_vereistauth_verplicht_en_true_voor_inzendingen(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["vereistAuth"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="vereistAuth"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_dubbele_bron_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append({"slot": "timing", "source": "magda:kenteken", "purpose": "tweede doel"})
    manifest["contextSchema"]["slots"]["timing"]["authenticSource"] = "magda:kenteken"
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="bron"):
        catalog.load_package(tmp_path, manifest["packageId"])
```

- [ ] **Step 2: Draai falen** → `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_catalog.py -q` → 3 nieuwe tests FAIL (DID NOT RAISE).

- [ ] **Step 3: Implementeer** — manifest: version `0.3.0` + de twee `documenten`-lijsten zoals hierboven. In `catalog._validate`, binnen de bestaande services-lus uitbreiden:

```python
        if "vereistAuth" not in service or not isinstance(service.get("vereistAuth"), bool):
            raise PackageError(f"dienst '{service_id}': vereistAuth moet een bool zijn")
        if service.get("type") == "inzending" and service.get("vereistAuth") is not True:
            raise PackageError(f"dienst '{service_id}': inzending vereist vereistAuth true")
        if service.get("type") == "inzending" and not service.get("documenten"):
            raise PackageError(f"dienst '{service_id}': inzending zonder documenten-eisen")
```

en ná de bestaande per-bron-lus in `authenticSources`:

```python
    bronnen_zonder_dubbel = {b.get("source") for b in bronnen}
    if len(bronnen_zonder_dubbel) != len(bronnen):
        raise PackageError("authenticSources bevat meerdere entries voor dezelfde bron (één doelbinding per bron)")
```

- [ ] **Step 4: Alle tests** → `83 passed` (80 + 3).

- [ ] **Step 5: Commit** → `git add … && git commit -m "feat(poc-gent): pakketconfig v0.3.0 — documenteneisen + vereistAuth- en broncontroles"`

---

### Task 3: Documentenmodule

**Files:**
- Create: `poc-gent/core/documents.py`
- Create: `poc-gent/fixtures/documenten.json`
- Test: `poc-gent/tests/test_documents.py`

**Interfaces:**
- Fixture `{"personas": {<pid>: [{"id": "kentekenbewijs", "bestand": "kenteken.pdf", "type": "pdf", "grootteKB": 240, "scanSchoon": true}, …]}}` — alle bestaande persona's leveren een geldig `kentekenbewijs`; de nieuwe persona `ilse` (taak 7) levert niets (D0-geval). Het te-grote/tiff-geval is unit-only (`test_documents`); `hanne` (taak 7) levert geldige documenten en weigert alléén H4.
- Produces: `documents.controleer(manifest: dict, service_id: str, aangeleverd: list[dict]) -> dict` met exact `{"volledig": bool, "bevindingen": [{"id", "ernst": "blokkade"|"waarschuwing", "melding"}]}`. Regels: verplicht `id` zonder aanlever → blokkade `D0-<id>`; `type` niet in `("pdf", "jpg", "png")` → blokkade `D1-<id>`; `grootteKB > 10240` → blokkade `D2-<id>`; `scanSchoon is False` → waarschuwing `D3-<id>` ("virusscan niet schoon — bestand in quarantaine"). OCR is uitsluitend assisterend: komt in F3 niet voor (FR-12-notitie in de docstring).

- [ ] **Step 1: Falende test** (`poc-gent/tests/test_documents.py`):

```python
"""Documentenmodule: compleetheid, type, grootte en scan (FR-12; OCR assisterend — buiten F3)."""

from pathlib import Path

from core import catalog, documents

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_verplicht_bewijs_ontbreekt_is_blokkade():
    uitslag = documents.controleer(MANIFEST, "ontheffing-lez", [])
    assert uitslag["volledig"] is False
    assert uitslag["bevindingen"][0]["id"] == "D0-kentekenbewijs"


def test_geldig_bewijs_is_volledig():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.pdf", "type": "pdf", "grootteKB": 240, "scanSchoon": True}])
    assert uitslag == {"volledig": True, "bevindingen": []}


def test_te_groot_bestand_is_blokkade():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.tiff", "type": "tiff", "grootteKB": 20480, "scanSchoon": True}])
    ids = {b["id"] for b in uitslag["bevindingen"]}
    assert ids == {"D1-kentekenbewijs", "D2-kentekenbewijs"}


def test_scan_niet_schoon_is_waarschuwing():
    uitslag = documents.controleer(
        MANIFEST, "ontheffing-lez",
        [{"id": "kentekenbewijs", "bestand": "k.pdf", "type": "pdf", "grootteKB": 240, "scanSchoon": False}])
    assert uitslag["volledig"] is False
    assert uitslag["bevindingen"][0]["ernst"] == "waarschuwing"
```

- [ ] **Step 2: Falen** → `ImportError: core.documents`.

- [ ] **Step 3: Fixture + implementatie** — fixture zoals het interface voorschrijft (sanne/ahmed/maria/fatima/jeroen/ellen/dirk: geldig kentekenbewijs; `ilse`: `[]`; `hanne`: het te grote tiff-bestand). `core/documents.py`:

```python
"""Documentenmodule (F3): compleetheid, type, grootte en virusscan-uitslag van
aangeleverde bewijzen (FR-12). OCR is assisterend en komt in F3 niet voor;
beslissingen blijven bij de mens (H4)."""

from __future__ import annotations

TOEGESTANE_TYPES = ("pdf", "jpg", "png")
MAX_KB = 10240


def controleer(manifest: dict, service_id: str, aangeleverd: list[dict]) -> dict:
    eisen = manifest["services"][service_id].get("documenten", [])
    per_id = {d["id"]: d for d in aangeleverd}
    bevindingen: list[dict] = []
    for eis in eisen:
        doc = per_id.get(eis["id"])
        if doc is None:
            if eis.get("verplicht"):
                bevindingen.append({"id": f"D0-{eis['id']}", "ernst": "blokkade",
                                    "melding": f"Ontbrekend document: {eis['titel']}."})
            continue
        if doc.get("type") not in TOEGESTANE_TYPES:
            bevindingen.append({"id": f"D1-{eis['id']}", "ernst": "blokkade",
                                "melding": f"Bestandstype niet toegestaan ({doc.get('type')}): gebruik pdf, jpg of png."})
        if (doc.get("grootteKB") or 0) > MAX_KB:
            bevindingen.append({"id": f"D2-{eis['id']}", "ernst": "blokkade",
                                "melding": f"Bestand te groot ({doc.get('grootteKB')} kB; max {MAX_KB} kB)."})
        if doc.get("scanSchoon") is False:
            bevindingen.append({"id": f"D3-{eis['id']}", "ernst": "waarschuwing",
                                "melding": "Virusscan niet schoon — bestand staat in quarantaine; lever opnieuw aan."})
    volledig = not any(b["ernst"] == "blokkade" for b in bevindingen)
    return {"volledig": volledig, "bevindingen": bevindingen}
```

- [ ] **Step 4: Alle tests** → `87 passed` (83 + 4). **Step 5: Commit** → `feat(poc-gent): documentenmodule met compleetheids- en veiligheidscontroles`

---

### Task 4: Backoffice-mock + idempotente submit-engine

**Files:**
- Create: `poc-gent/adapters/backoffice_mock.py`
- Create: `poc-gent/core/submit.py`
- Test: `poc-gent/tests/test_submit.py`

**Interfaces:**
- `backoffice_mock.dien_in(contract: str, lading: dict, idempotentie_sleutel: str) -> dict` — exact `{"referentie": str, "status": "geaccepteerd"|"in-wachtrij"}`; referentie is deterministisch: `"GENT-" + idempotentie_sleutel[:12].upper()`; dezelfde sleutel retourneert hetzelfde resultaat (dictionary-cache per proces); onbekend contract → `KeyError`. Contracten: `"district09-vergunningen"` (geregistreerd in `fixtures/source/source.meta.json` bij Task 1's meta — registratie mag ook hier in de docstring blijven; meta-updates in taak 9).
- `submit.bereid_voor(package_id: str, persona_id: str, service_id: str, draft: dict) -> dict` — stelt `{"service": service_id, "lading": canonical draft, "idempotentie_sleutel": sha256hex(package_id|persona_id|service_id|json(canonical draft))[:16]}` samen.
- `submit.dien_in(package_id: str, persona_id: str, formulieren: list[dict]) -> list[dict]` — per transactie: `bereid_voor` + `backoffice_mock.dien_in`; retourneert `[{"service", "referentie", "status"}]` (FR-16).

- [ ] **Step 1: Falende test** (`poc-gent/tests/test_submit.py`):

```python
"""Backoffice-mock + submit: idempotent, deterministisch ontvangstbewijs (FR-16, INT-03/06, NFR-04)."""

import pytest

from adapters import backoffice_mock
from core import submit


def test_referentie_is_deterministisch_en_idempotent():
    eerste = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    tweede = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    assert eerste == tweede
    assert eerste["referentie"] == "GENT-" + "abc123"[:12].upper()
    assert eerste["status"] in ("geaccepteerd", "in-wachtrij")


def test_andere_sleutel_andere_referentie():
    a = backoffice_mock.dien_in("district09-vergunningen", {"x": 1}, "abc123")
    b = backoffice_mock.dien_in("district09-vergunningen", {"x": 2}, "def456")
    assert a["referentie"] != b["referentie"]


def test_onbekend_contract_faalt():
    with pytest.raises(KeyError):
        backoffice_mock.dien_in("bestaat-niet", {}, "x")


def test_submit_een_transactie():
    formulieren = [{"service": "ontheffing-lez", "velden": [{"veld": "k", "waarde": "1-ABC-123"}], "ontbrekend": []}]
    resultaat = submit.dien_in("gent-mobiliteit-ondernemer", "sanne", formulieren)
    assert len(resultaat) == 1
    assert resultaat[0]["service"] == "ontheffing-lez"
    assert resultaat[0]["referentie"].startswith("GENT-")
    opnieuw = submit.dien_in("gent-mobiliteit-ondernemer", "sanne", formulieren)
    assert opnieuw == resultaat
```

- [ ] **Step 2: Falen** → `ImportError`. **Step 3: Implementatie**:

`poc-gent/adapters/backoffice_mock.py`:

```python
"""District09-backoffice-mock (F3): inzending mét idempotent ontvangstbewijs.
Productie vervangt dit door de versioned API-contracten van District09 (INT-03);
statusmapping technisch→burgerlijk gebeurt in de pipeline (INT-06)."""

from __future__ import annotations

_CONTRACTEN = {"district09-vergunningen"}
_CACHE: dict[str, dict] = {}


def dien_in(contract: str, lading: dict, idempotentie_sleutel: str) -> dict:
    if contract not in _CONTRACTEN:
        raise KeyError(f"onbekend backoffice-contract: {contract}")
    if idempotentie_sleutel in _CACHE:
        return _CACHE[idempotentie_sleutel]
    resultaat = {"referentie": "GENT-" + idempotentie_sleutel[:12].upper(), "status": "geaccepteerd"}
    _CACHE[idempotentie_sleutel] = resultaat
    return resultaat
```

`poc-gent/core/submit.py`:

```python
"""Submit-engine (F3): bereidt een inzending voor met idempotentiesleutel over
de canonieke conceptlading en dient die in bij het backoffice-contract."""

from __future__ import annotations

import hashlib
import json

from adapters import backoffice_mock

BACKOFFICE_CONTRACT = "district09-vergunningen"


def bereid_voor(package_id: str, persona_id: str, service_id: str, draft: dict) -> dict:
    lading = json.dumps(draft, ensure_ascii=False, sort_keys=True)
    sleutel = hashlib.sha256(f"{package_id}|{persona_id}|{service_id}|{lading}".encode("utf-8")).hexdigest()[:16]
    return {"service": service_id, "lading": draft, "idempotentie_sleutel": sleutel}


def dien_in(package_id: str, persona_id: str, formulieren: list[dict]) -> list[dict]:
    resultaten = []
    for formulier in formulieren:
        voorbereid = bereid_voor(package_id, persona_id, formulier["service"], formulier)
        ontvangst = backoffice_mock.dien_in(BACKOFFICE_CONTRACT, voorbereid["lading"],
                                            voorbereid["idempotentie_sleutel"])
        resultaten.append({"service": formulier["service"], "referentie": ontvangst["referentie"],
                           "status": ontvangst["status"]})
    return resultaten
```

- [ ] **Step 4: Alle tests** → `91 passed` (87 + 4). **Step 5: Commit** → `feat(poc-gent): backoffice-mock en idempotente submit-engine met ontvangstbewijs`

---

### Task 5: Run-schema v1.2 — submission, documenten, h4

**Files:**
- Modify: `poc-gent/schemas/gent-run.schema.json`
- Test: `poc-gent/tests/test_runs.py`

**Interfaces:**
- `schemaVersion` const `"1.2"`; `transaction` krijgt vereist `submission`:
  `{"h4": {"verdict": "gegeven"|"geweigerd"|"n.v.t.", "bevestigdOp": str}, "documenten": {"status": "volledig"|"onvolledig"|"n.v.t.", "bevindingen": [ {id, ernst, melding} ]}, "ontvangst": {"transacties": [{"service", "referentie", "status": "geaccepteerd"|"in-wachtrij"|"afgewezen"|"technisch-mislukt"|"niet-ingediend"}]}, "vervolgsamenvatting": {"gereed": [str], "open": [str]}}`
  — bij H4-weigering/blokkade/escalatie: `ontvangst.transacties` bevat per transactie `status: "niet-ingediend"` zonder referentie-veld? Nee: schema-eenvoud — `"referentie": {"type": ["string", "null"]}`; `vervolgsamenvatting.open` benoemt dan de te ondernemen actie.

- [ ] **Step 1:** Breid het schema uit (const 1.2; `$defs.submissionH4`, `submissionDocumenten`, `ontvangstTransactie`, `vervolgsamenvatting` met `additionalProperties: false`; required-uitbreiding `transaction` + `"submission"`).
- [ ] **Step 2:** Werk `_minimale_run()` bij: `"schemaVersion": "1.2"` en een geldig `submission`-blok (`h4: n.v.t.`, `documenten: n.v.t.` met lege bevindingen, lege ontvangst, lege vervolgsamenvatting-lijsten). Nieuwe test `test_schema_verwerpt_zonder_submission` (verwijder het blok → ValidationError).
- [ ] **Step 3:** `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests/test_runs.py -q` → `8 passed` (7 + 1); daarna faalt de suite uitsluitend op de validerende pipeline-tests (verwachte tussenfase, zoals bij F2-T7).
- [ ] **Step 4: Commit** → `feat(poc-gent): run-schema v1.2 met submission-blok (H4, documenten, ontvangst, vervolgsamenvatting)`

---

### Task 6: Pipeline fase-3 + event-masking

**Files:**
- Modify: `poc-gent/core/pipeline.py`
- Test: `poc-gent/tests/test_pipeline.py`

**Interfaces:**
- Na H3 (en alleen bij `status` ∈ {`gereed`, `gereed-met-waarschuwing`}): documentencontrole over `fixtures/documenten.json[personas][pid]` per transactie; blokkades → status `blokkade` (documenten-bevindingen in `submission.documenten`), anders H4-poort: stap `h4-inzending` (actor `mens`, consent `gevraagd`→verdict) + events `gate_request`/`gate_verdict` gate `H4` met payload `{"transacties": [service…], "samenvatting": "concept + bewijzen"}`; persona-veld `inzendingBevestigen` (`"gegeven"` standaard; hanne: `"geweigerd"`). Weigering → status `geweigerd` (H4), ontvangst per transactie `niet-ingediend`. Bevestiging → `submit.dien_in` per transactie, ontvangstbewijzen, stap `ontvangstbewijs` (actor `partij`), vervolgsamenvatting (`gereed`: referenties; `open`: waarschuwings- en D3-meldingen + "status volgen via Gentinfo"), events `inzending` per transactie (service + referentie — referenties zijn geen persoonsgegevens) en `vervolgsamenvatting`.
- Bij status `blokkade`/`geweigerd`/`escalatie`: `submission` met `h4.verdict "n.v.t."` (of `geweigerd`), `documenten.status "n.v.t."`, ontvangst `niet-ingediend`, `vervolgsamenvatting.open` met de reden-tekst.
- **Event-masking (SEC-05, uit review-backlog)**: `intake_genomen`-payload wordt `{"situatieschetsHash": sha256(situatieschets)[:16], "slots_uit_intentie": [...]}`; H1 `gate_request`-payload wordt `{"gate": "H1", "feitnamen": [...]}`. Run-artefact ongewijzigd (bevat de volledige schets/feiten). Nieuwe test verifieert dat géén adresstring of schets-tekst in de events voorkomt.

- [ ] **Step 1: Falende tests** (toevoegen; pas bestaande aan waar masking de events-vorm raakt — `test_bron_raadpleging…` blijft geldig):

```python
def test_sanne_rondt_inzending_af_met_ontvangstbewijs():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    runs.validate(run, POC_ROOT)
    ontvangst = run["transaction"]["submission"]["ontvangst"]["transacties"]
    assert len(ontvangst) == 2
    assert all(t["status"] == "geaccepteerd" and t["referentie"].startswith("GENT-") for t in ontvangst)
    assert run["transaction"]["submission"]["h4"]["verdict"] == "gegeven"
    assert any(e["kind"] == "inzending" for e in log)
    assert run["transaction"]["submission"]["vervolgsamenvatting"]["gereed"]


def test_hanne_weigert_h4_en_stopt_voor_inzending():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "hanne")
    runs.validate(run, POC_ROOT)
    ontvangst = run["transaction"]["submission"]["ontvangst"]["transacties"]
    assert all(t["status"] == "niet-ingediend" and t["referentie"] is None for t in ontvangst)
    assert run["transaction"]["status"] == "geweigerd"


def test_ilse mist_verplicht_document():
    run, _log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "ilse")
    runs.validate(run, POC_ROOT)
    docs = run["transaction"]["submission"]["documenten"]
    assert docs["status"] == "onvolledig"
    assert docs["bevindingen"][0]["id"].startswith("D0-")
    assert run["transaction"]["status"] == "blokkade"


def test_events_bevatten_geen_ruwe_schets_of_adres():
    run, log = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    tekst = json.dumps(log)
    assert "Korenmarkt 1, Gent" not in tekst
    assert "loodgieter" not in tekst  # woord uit sanne's schets
```

- [ ] **Step 2: Falen** → `KeyError: 'submission'` e.a. **Step 3: Implementeer** fase-3 volgens het interface boven (spiegel de F2-fase-2-structuur; documenten vóór H4; `submit.dien_in` alleen na verdict `gegeven`; vervolgsamenvatting opbouwen uit ontvangst + open bevindingen). **Step 4: Alle tests** → `97 passed` (92 + 5; de 2 eerder falende validerende pipeline-tests zijn nu weer groen). **Step 5: Commit** → `feat(poc-gent): pipeline fase-3 — documenten, H4, inzending met ontvangstbewijs, vervolgsamenvatting, event-masking`

---

### Task 7: Personas/golden — ilse (document ontbreekt), hanne (H4-weigering), g9–g11

**Files:**
- Modify: `poc-gent/fixtures/personas.json`, `poc-gent/fixtures/magda.json`, `poc-gent/fixtures/identiteiten.json`, `poc-gent/fixtures/documenten.json`
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl`, `poc-gent/tests/test_catalog.py` (golden-count 8 → 11)
- Test: `poc-gent/tests/test_pipeline.py` (gedekt door taak 6; counttest in catalog)

**Interfaces:** nieuwe persona's: `ilse` (ondernemer, Korenmarkt — Magda-record aanwezig Euro 6, maar géén kentekenbewijs → D0-blokkade; edge `document-ontbreekt`) en `hanne` (ondernemer, Korenmarkt, documenten geldig, `inzendingBevestigen: "geweigerd"`; edge `weigert-inzending`). Golden: g9 ilse → status `blokkade`; g10 hanne → `geweigerd` met ontvangst `niet-ingediend`; g11 sanne → `gereed` mét ontvangst `geaccepteerd`. Alle bestaande golden-regels ongewijzigd (sanne e.a. krijgen via `documenten.json` en default `inzendingBevestigen: "gegeven"` automatisch inzending).

- Stappen: fixtures uitbreiden (identiteiten + magda voor ilse/hanne; documenten per taak 3 + hanne's te grote variant vervalt — hanne levert geldige documenten en weigert alleen H4; de te-grote testcase staat al in `test_documents` als unit); golden +3; catalogus-counttest 8 → 11; suite `97 passed`; eval smoke `11/11`. Commit: `feat(poc-gent): personas ilse en hanne + golden g9-g11 voor document- en H4-randpaden`.

---

### Task 8: CLI + README + statusraadpleging (FR-19)

**Files:**
- Modify: `poc-gent/run.py`, `poc-gent/README.md`
- Test: smokes (geen nieuwe pytest-tests; CLI-vorm is al gedekt door pipeline-tests)

**Interfaces:**
- `run.py` print na status: ontvangstbewijzen (`  ontvangst: <service> → <referentie> (<status>)`) en de vervolgsamenvatting (`  nog te doen:` regels), en bij weigering de stopmelding. Nieuwe vlag `--status --persona <id>`: herhaalt de replay en print per transactie `ingediend als <referentie> · <status>` of `niet ingediend (<reden>)` — FR-19-mockvorm (geen aparte backoffice-query; documentatie vermeldt productiepad polling INT-06).
- README: Fase 1+2+3-beschrijving, `--status`-voorbeeld, broncatalogus-verwijzing (VKBO/GIPOD/BeSt).
- Smokes: `python3 run.py --persona sanne | head -12` (ontvangst + vervolgsamenvatting), `python3 run.py --status --persona hanne | head -4` (niet ingediend), `python3 eval.py` → `11/11`.
- Suite blijft `97 passed`. Commit: `feat(poc-gent): ontvangstbewijs en vervolgsamenvatting in CLI; --status raadpleging; README F3`.

---

### Task 9: Simulatietab fase 3

**Files:**
- Modify: `simulation/build_simulation.py` (`build_gent`: `submission`-blok meenemen), `simulation/template.html` (view5: ontvangstkaart + vervolgsamenvatting + documentbevindingen; sim5-stappen uit de run-stappen incl. nieuwe stappen — generiek al het geval), `simulation/verify_static.mjs` (drive ilse/hanne), `simulation/test_build_gent.py`
- Test: `simulation/test_build_gent.py` uitbreiding (+2: ontvangstbewijzen aanwezig voor sanne/geen voor hanne; events bevatten geen adresstring).

Stappen: `build_gent()` neemt `t["submission"]` over in de persona-dict; template voegt achter het statuskaartje een ontvangst/vervolg-blok toe (alleen als `submission.ontvangst.transacties` niet-leeg of `vervolgsamenvatting.open` niet-leeg); verifier rijdt `gentPersona("ilse")` en `gentPersona("hanne")`; build + `node verify_static.mjs` exit 0; suite `99 passed` (95 poc-gent + 4→6 test_build_gent… let op: poc-gent-suite telt niet test_build_gent; zelfcheck noemt beide). Commit (scope `simulation`): `feat(simulation): Gent-tab fase 3 — ontvangstbewijs, vervolgsamenvatting en documentbevindingen`.

---

## Zelfcheck na afronding (executeur)

1. `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → `94 passed`.
2. `python3 eval.py` → `golden: 11/11 geslaagd`, `determinisme: OK`, exit 0.
3. `python3 run.py --persona sanne | head -12` → ontvangstbewijzen + vervolgsamenvatting; `--persona ilse` → D0-blokkade; `--persona hanne` → geweigerd/niet-ingediend.
4. `python3 run.py --status --persona sanne | head -4` → referenties.
5. `cd ../simulation && ../nldt/.venv/bin/python build_simulation.py` → gent-regel met 9 persona's; `node verify_static.mjs` → OK (exit 0).
