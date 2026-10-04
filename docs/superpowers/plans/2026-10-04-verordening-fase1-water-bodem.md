# Verordening-regeluitbreiding fase 0+1 (methodewiring + water + bodem) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the track-extension method and land the first two new verordening tracks — `water` (H2) and `bodem` (H3) — each with cite-or-abstain evidence, registered+cached GIO zones, formalizer templates, TRACKS registration, a canonical `pass` run, and conformance tests.

**Architecture:** The existing track model (SOLUTIONS_ARCHITECTURE §3.3) is extended, not changed: evidence shard + abstention ledger + registry zone aliases + agents.py template entries + TRACKS key + use-case file. A shared, data-driven conformance test module (`poc/tests/test_track_conformance.py` + `poc/corpus/track-manifest.json`) verifies every new track the same way; fase 2/3 tracks (mobiliteit, landschap, landbouw, wonen, biomassa) will be separate plans that only add manifest entries and files.

**Tech Stack:** stdlib + jsonschema (via `nldt/.venv`), shapely/geopandas for the canonical runs (unchanged pipeline), ArcGIS REST one-shot probe (network once, then offline).

**Spec:** `docs/superpowers/specs/2026-10-04-verordening-regeluitbreiding-design.md` (fase 0 + fase 1)

## Global Constraints

- Cite-or-abstain: every `quote_nl` must be a verbatim substring of the snapshot `docs/research/sources/cvdr704250-tekst-extract.txt` (whitespace-normalized comparison); no invented quotes, zones or numbers. Missing GIO ⇒ rule becomes `ambiguous`/ledger entry, never a drawn zone.
- Instrument pin: CVDR704250 geldend 13-10-2025; every shard record uses `sourceId: "S07"` and `url: https://lokaleregelgeving.overheid.nl/cvdr704250` unless a new source is genuinely needed.
- Existing tracks stay byte-identical: canonical runs `poc/runs/20260830T113234Z-wind`, `…T142439Z-zon`, `…T142446Z-bos` must not change; existing suites (poc, nldt, toolbox-sim, poc-bp2op) stay green.
- Snapshot coverage rule: for chapters 2 and 3, every artikel of the chapter must appear in the shard (`article` field) or in the ledger's `articlesConsidered` list — verified by the conformance module, which derives the artikel list from the snapshot itself.
- Test command (from `poc/`): `../nldt/.venv/bin/python -m pytest tests -q`; full repo suites per spec.
- Every task ends with a commit `feat(poc): …` / `test(poc): …`; explicit-path adds only.
- Work happens on branch `verordening-fase1` in an isolated worktree (`/Users/marc/Projecten/ldttoolbox-vf1`, venv symlinked as in the toolbox-sim run); never touch the parallel session's dirty files in the main checkout.

---

### Task 1: objectType-enum extension

**Files:**
- Modify: `poc/schemas/opportunity-map-request.schema.json` (line 52, `$defs.objectType.enum`)
- Test: `poc/tests/test_objecttype_enum.py`

**Interfaces:**
- Produces: enum `["wind_turbine","solar_field","forest_planting","biomass_installation","energy_storage","riparian_development","soil_activity","roadside_development","landscape_intervention","agricultural_expansion","housing_development"]` — later fase-2/3 tasks rely on these exact values.

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_objecttype_enum.py
import json
from pathlib import Path

import jsonschema

SCHEMA = json.loads(Path("schemas/opportunity-map-request.schema.json").read_text())
NEW = ["riparian_development", "soil_activity", "roadside_development",
       "landscape_intervention", "agricultural_expansion", "housing_development"]


def _request(object_type: str) -> dict:
    return {
        "id": "0d9f61aa-4e8a-4b8f-8a3f-6f21cb1f001",
        "objectType": object_type,
        "ambitions": ["water_safety"],
        "areaOfInterest": {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}, "crs": "EPSG:28992"},
        "policyStage": "programming",
        "effortBudget": {"maxNodes": 10},
        "requestedAt": "2026-10-04T10:00:00Z",
    }


def test_new_objecttypes_validate():
    for object_type in NEW:
        jsonschema.validate(_request(object_type), SCHEMA)


def test_existing_objecttypes_still_validate():
    for object_type in ["wind_turbine", "solar_field", "forest_planting", "biomass_installation", "energy_storage"]:
        jsonschema.validate(_request(object_type), SCHEMA)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/marc/Projecten/ldttoolbox-vf1/poc && ../nldt/.venv/bin/python -m pytest tests/test_objecttype_enum.py -q`
Expected: FAIL — ValidationError on the six new objectTypes.

- [ ] **Step 3: Extend the enum** (line 52)

```json
    "objectType": { "enum": ["wind_turbine", "solar_field", "forest_planting", "biomass_installation", "energy_storage", "riparian_development", "soil_activity", "roadside_development", "landscape_intervention", "agricultural_expansion", "housing_development"] },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_objecttype_enum.py -q` → `2 passed`

- [ ] **Step 5: Commit**

```bash
git add poc/schemas/opportunity-map-request.schema.json poc/tests/test_objecttype_enum.py
git commit -m "feat(poc): objectType-enum uitgebreid met zes verordening-tracks"
```

---

### Task 2: agrest NAAM-probe (one-shot, committed artifact)

**Files:**
- Create: `poc/data/probe_agrest_namen.py`, `poc/data/agrest-namen.json` (generated, committed)
- Test: `poc/tests/test_agrest_namen.py`

**Interfaces:**
- Produces: `poc/data/agrest-namen.json` — `{"generatedAt": <ISO>, "service": <url>, "namen": [str, ...] sorted}`; the zone-selection evidence for Tasks 5 and 8 (and later fase-2/3 tasks).
- Consumes: `https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0` (verified live mechanics: `f=json&returnGeometry=false&outFields=NAAM&returnDistinctValues=true&resultOffset=…`, pages of 1000).

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_agrest_namen.py
import json
from pathlib import Path

ART = json.loads(Path("data/agrest-namen.json").read_text())


def test_artifact_shape():
    assert ART["service"].startswith("https://agrest.geodata-utrecht.nl")
    namen = ART["namen"]
    assert isinstance(namen, list) and namen and namen == sorted(namen)
    assert all(isinstance(n, str) and n.strip() for n in namen)
    assert len(namen) == len(set(namen))


def test_known_names_present():  # regressie op bestaande tracks
    for known in ["Gebied windenergie", "Gebied zonneveld", "Landelijk gebied"]:
        assert known in ART["namen"], known
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_agrest_namen.py -q`
Expected: FAIL — `FileNotFoundError: data/agrest-namen.json`.

- [ ] **Step 3: Implement the probe**

```python
# poc/data/probe_agrest_namen.py
"""One-shot NAAM-probe op de agrest Omgevingsverordening FeatureServer.

Zoekt alle distinct gebiedsaanwijzing-namen (GIO's) die de verordening kent;
output wordt gecommit als bewijsmateriaal voor zone-aliaskeuze (tracks water,
bodem, en later fase 2/3). Netwerk alleen bij expliciete hergeneratie.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVICE = "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0"
OUT = Path(__file__).with_name("agrest-namen.json")


def fetch_namen() -> list[str]:
    namen: set[str] = set()
    offset = 0
    while True:
        url = (
            f"{SERVICE}?f=json&returnGeometry=false&outFields=NAAM"
            f"&returnDistinctValues=true&resultOffset={offset}&resultRecordCount=1000"
            f"&where=1%3D1"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            body = json.loads(resp.read())
        features = body.get("features", [])
        if not features:
            break
        for feat in features:
            naam = (feat.get("attributes") or {}).get("NAAM")
            if naam:
                namen.add(str(naam).strip())
        if body.get("exceededLimit", False) or len(features) < 1000:
            if not body.get("exceededLimit", False):
                break
        offset += 1000
    return sorted(namen)


def main() -> int:
    namen = fetch_namen()
    OUT.write_text(
        json.dumps(
            {"generatedAt": datetime.now(timezone.utc).isoformat(), "service": SERVICE, "namen": namen},
            ensure_ascii=False, indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(namen)} distinct NAAM-waarden -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run once (network): `cd poc && ../nldt/.venv/bin/python data/probe_agrest_namen.py` → e.g. `40 distinct NAAM-waarden -> …`. If `returnDistinctValues` is rejected by the service (`error` in the first response), fall back to paging `outFields=NAAM` without distinct and dedup locally — same output contract, note the fallback in the commit message.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_agrest_namen.py -q` → `2 passed`

- [ ] **Step 5: Commit**

```bash
git add poc/data/probe_agrest_namen.py poc/data/agrest-namen.json poc/tests/test_agrest_namen.py
git commit -m "feat(poc): agrest NAAM-probe + gecommit artifact (zone-selectiebewijs)"
```

---

### Task 3: track-manifest + gedeelde conformatietest-module

**Files:**
- Create: `poc/corpus/track-manifest.json`, `poc/tests/test_track_conformance.py`
- Test: the module itself (unit test with inline mini-fixture)

**Interfaces:**
- Produces:
  - `track-manifest.json`: `{"tracks": {<track-id>: {"shard": "corpus/evidence-<id>.json", "ledger": "corpus/normcards-rejected-<id>.json", "objectType": <enum>, "chapters": ["2"], "formalizableArticles": [<str>…], "useCase": "use-cases/<id>.json"}}}` — Tasks 4/5/6/7/8/9 add entries; fase 2/3 plans extend it further.
  - `test_track_conformance.py` exports helpers used by its own parametrized tests: `load_manifest()`, `snapshot_text()` (whitespace-normalized), `chapter_articles(chapter)` (regex `^Artikel {ch}\.\d` over the snapshot, deduped).

- [ ] **Step 1: Write the module + its unit test (born-green — the parametrized track tests activate when manifest entries appear)**

```python
# poc/tests/test_track_conformance.py
"""Data-driven conformatie voor nieuwe verordening-tracks.

Per manifest-track: shard-schema, letterlijkheid (citaat-containment tegen de
snapshot), bronresolutie en artikeldekking (shard ∪ ledger.articlesConsidered
== alle snapshot-artikelen van de hoofdstukken). De dekking wordt afgeleid
uit de snapshot zelf, niet handgetypt.
"""
import json
import re
from pathlib import Path

import pytest

POC = Path(__file__).resolve().parents[1]
SNAPSHOT = (POC.parent / "docs/research/sources/cvdr704250-tekst-extract.txt").read_text(encoding="utf-8")

SHARD_FIELDS = {"id", "sourceId", "instrument", "article", "quote_nl", "theme", "url", "verified", "notes"}


def snapshot_norm() -> str:
    return re.sub(r"\s+", " ", SNAPSHOT)


def chapter_articles(chapter: str) -> set[str]:
    return set(re.findall(rf"^Artikel {chapter}\.\d+[a-z]?", SNAPSHOT, flags=re.M))


def load_manifest() -> dict:
    return json.loads((POC / "corpus/track-manifest.json").read_text())["tracks"]


def test_chapter_articles_known_counts():  # snapshot-sanity van de afleider zelf
    assert "2.15" in {a.split()[-1] for a in chapter_articles("2")}
    assert "3.2" in {a.split()[-1] for a in chapter_articles("3")}
    assert len(chapter_articles("2")) > 30 and len(chapter_articles("3")) > 20


@pytest.mark.parametrize("track_id", ["water", "bodem"])
def test_track_conformance(track_id):
    tracks = load_manifest()
    if track_id not in tracks:
        pytest.skip(f"{track_id} nog niet in manifest (taak volgt)")
    entry = tracks[track_id]
    shard = json.loads((POC / entry["shard"]).read_text())
    ledger = json.loads((POC / entry["ledger"]).read_text())
    sources = json.loads((POC / "corpus/sources.json").read_text())
    source_ids = {s["id"] for s in sources}
    norm = snapshot_norm()

    covered: set[str] = set()
    for rec in shard:
        assert SHARD_FIELDS <= set(rec), rec.get("id")
        assert rec["verified"] is True
        assert rec["sourceId"] in source_ids
        assert rec["url"].startswith("https://")
        quote = re.sub(r"\s+", " ", rec["quote_nl"]).strip()
        assert quote in norm, f"citaat niet letterlijk in snapshot: {rec['id']} ({rec['article']})"
        m = re.match(r"Artikel (\d+\.\d+[a-z]?)", rec["article"])
        assert m, f"article-veld zonder artikelnummer: {rec['article']}"
        covered.add(m.group(1))
    considered = {a.split()[-1] for a in ledger.get("articlesConsidered", [])}
    expected = {a.split()[-1] for a in chapter_articles(entry["chapters"][0])}
    missing = expected - covered - considered
    assert not missing, f"artikelen zonder thuis in {track_id}: {sorted(missing)}"
    assert set(entry["formalizableArticles"]) <= covered, "manifest belooft formaliseerbaar wat niet geciteerd is"
```

`poc/corpus/track-manifest.json` (initial — entries land per track-task):

```json
{
  "description": "Manifest van verordening-tracks voor de conformatietests (fase 1: water+bodem; fase 2/3 breidt uit).",
  "tracks": {}
}
```

- [ ] **Step 2: Run to verify**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_track_conformance.py -q`
Expected: `2 skipped, 1 passed` (snapshot-sanity green; water/bodem skip until Tasks 4/7).

- [ ] **Step 3: Commit**

```bash
git add poc/corpus/track-manifest.json poc/tests/test_track_conformance.py
git commit -m "test(poc): track-manifest + data-driven conformatiemodule (citaat-/dekkingsgate)"
```

---

### Task 4: water-recon (evidence-shard + leger + manifestentry)

**Files:**
- Create: `poc/corpus/evidence-water.json`, `poc/corpus/normcards-rejected-water.json`
- Modify: `poc/corpus/track-manifest.json` (add `water` entry)
- Test: Task 3's `test_track_conformance["water"]` (activates)

**Interfaces:**
- Produces: evidence records `{id: "WA-01"…, sourceId: "S07", instrument: "Omgevingsverordening provincie Utrecht (CVDR704250, geldend 13-10-2025) - artikeltekst", article: "Artikel 2.15", quote_nl: <letterlijk>, theme: "water:<…>", url: "https://lokaleregelgeving.overheid.nl/cvdr704250", verified: true, notes: <motivatie>}`; ledger follows the zon-ledger shape (`description, generatedBy, generatedAt, policy, rejectedEvidence, abstentions` + **new field `articlesConsidered`**: artikelen die bewust geen NormCard worden, met reden in `abstentions`).

- [ ] **Step 1: Recon — letterlijk extraheren uit de snapshot** (geen netwerk; snapshot is SoT):

Per beoogd artikel de brontekst ophalen en `quote_nl` kopiëren:
`F=../docs/research/sources/cvdr704250-tekst-extract.txt; L=$(grep -n "^Artikel 2.15 " $F | tail -1 | cut -d: -f1); sed -n "${L},$((L+12))p" $F` (herhaal per artikel; `tail -1` pakt de body-instantie, niet de inhoudsopgave).

Verwachte verdeling (leidraad — de letterlijke tekst beslist):
- **Formaliseerbaar (shard)**: 2.14 vrijwaringszone regionale waterkering, 2.15 waterbergingsgebied, 2.16 overstroombaar gebied (instructieregels met gebiedsaanwijzing). Minimaal deze drie records `WA-01..WA-03`.
- **articlesConsidered + abstentions**: 2.1–2.13 (omgevingswaarden/monitoring: `topic: "omgevingswaarden waterkering/wateroverlast (monitoring-normen)"`, `reason: "omgevingswaarde-artikelen leggen normen voor waterschapsmonitoring vast, geen gebiedsaanwijzing met instructieregel-zone; formalisering zou een zone verzinnen"`), 2.17–2.24 (waterschaarste-rangorde, peilbesluit-/legger-inhoud: procedureel), 2.25–2.39+ (zwemlocaties, woonschepen/partyschepen, voorwerpen in water: vergunnings-/beoordelingsregels; `wouldHaveBeen: "conditional"` waar toepasselijk). De volledige H2-artikellenlijst komt uit `chapter_articles("2")` — elk artikel óf in shard óf in `articlesConsidered`.

- [ ] **Step 2: Manifestentry toevoegen**

```json
"water": {
  "shard": "corpus/evidence-water.json",
  "ledger": "corpus/normcards-rejected-water.json",
  "objectType": "riparian_development",
  "chapters": ["2"],
  "formalizableArticles": ["2.14", "2.15", "2.16"],
  "useCase": "use-cases/water.json"
}
```

- [ ] **Step 3: Run the conformance gate**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_track_conformance.py -q`
Expected: `1 passed, 1 skipped` — de water-parametrisatie groen (citaat-letterlijkheid + volledige H2-dekking afgedwongen); bodem skipt nog.

- [ ] **Step 4: Commit**

```bash
git add poc/corpus/evidence-water.json poc/corpus/normcards-rejected-water.json poc/corpus/track-manifest.json
git commit -m "feat(poc): water-recon — evidence-shard H2 met cite-or-abstain-dekking"
```

---

### Task 5: water-zones (registry + aliases + cache)

**Files:**
- Modify: `poc/data/sources.json` (nieuwe entries), `poc/run.py` (`ZONE_SOURCES`-blok)
- Test: `poc/tests/test_water_zones.py`

**Interfaces:**
- Consumes: `poc/data/agrest-namen.json` (Task 2) — selectieregel: kies namen die `waterbergingsgebied`, `overstroombaar`, `vrijwaringszone` of `regionale waterkering` matchen (case-insensitive); registreer de bijbehorende FeatureServer-laag niet opnieuw als de bestaande registry (incl. `ow_bwp_overstroombaar`) dezelfde service al dekt.
- Produces: zone-aliases `waterbergingsgebied`, `overstroombaar_gebied`, `vrijwaringszone_waterkering` (keys) → registry-bron-id's; cache-twins onder `poc/data/cache/<source-id>.{28992,4326}.geojson`.

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_water_zones.py
import json
from pathlib import Path

POC = Path(__file__).resolve().parents[1]


def test_water_aliases_resolve_to_registered_sources():
    run_py = (POC / "run.py").read_text()
    for alias in ["waterbergingsgebied", "overstroombaar_gebied", "vrijwaringszone_waterkering"]:
        assert f'"{alias}"' in run_py, alias
    registry = json.loads((POC / "data/sources.json").read_text())
    ids = {s["id"] for s in registry}
    import re
    for line in run_py.splitlines():
        m = re.match(r'\s*"(\w+)":\s*"([\w.-]+)",?\s*(?:#.*)?$', line)
        if m and m.group(1) in {"waterbergingsgebied", "overstroombaar_gebied", "vrijwaringszone_waterkering"}:
            assert m.group(2) in ids, f"alias {m.group(1)} -> onbekende bron {m.group(2)}"


def test_water_cache_twins_exist():
    registry = json.loads((POC / "data/sources.json").read_text())
    water_ids = [s["id"] for s in registry if "water" in json.dumps(s).lower() or "overstroom" in json.dumps(s).lower() or "kering" in json.dumps(s).lower()]
    cached = {p.stem.replace(".28992", "").replace(".4326", "") for p in (POC / "data/cache").glob("*.geojson")}
    freshly = [i for i in water_ids if i not in cached]
    assert not freshly, f"water-bronnen zonder cache-twins: {freshly}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_water_zones.py -q` → FAIL (aliases bestaan nog niet).

- [ ] **Step 3: Registreer + fetch + alias**

1. Kies uit `data/agrest-namen.json` de water-gebiedsnamen (selectieregel hierboven). Voor elke gekozen naam: voeg één registry-entry toe naar het patroon van de bestaande OV-entries (id bijv. `ov_waterbergingsgebied`, url = de agrest FeatureServer met `where NAAM='<naam>'`-queryvorm zoals `Gebied windenergie` die gebruikt, rol `inclusion`/`exclusion` conform semantiek: vrijwaringszone/waterberging/overstroombaar = `exclusion`/`conditional` voor riparian_development).
2. Haal elke laag éénmalig op met het bestaande fetch-mechanisme (`python3 -m pipeline.geodata` resp. het cache-first pad zoals bij bestaande lagen) zodat `data/cache/<id>.28992.geojson` + `.4326.geojson` ontstaan.
3. Voeg in `run.py::ZONE_SOURCES` de drie alias-regels toe (zelfde vorm als `gebied_windenergie`).

- [ ] **Step 4: Run test + commit**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_water_zones.py -q` → `2 passed`

```bash
git add poc/data/sources.json poc/data/cache poc/run.py poc/tests/test_water_zones.py
git commit -m "feat(poc): water-zones — registry, cache-twins en ZONE_SOURCES-aliases"
```

---

### Task 6: water formalisering + TRACKS + use-case + canonieke run

**Files:**
- Modify: `poc/pipeline/agents.py` (TEMPLATE-tabel: `WA-01..WA-03`-entries), `poc/run.py` (`TRACKS["water"]`)
- Create: `poc/use-cases/water.json` (AoI letterlijk gekopieerd uit `use-cases/wind.json`), `poc/runs/<ts>-water/` (canonieke run, ge commit zoals de bestaande canonieke runs — artefacten zonder zware tussenbestanden)
- Test: `poc/tests/test_water_run.py`

**Interfaces:**
- Consumes: shard `WA-01..WA-03` (Task 4), aliases (Task 5).
- Produces: `TRACKS["water"]` (complete entry hieronder); template-velden exact zoals `W-05`: `claim, confidence, contextTags, geoBinding{zoneIds, geometrySource, gioJoinId?, caveat}`.

- [ ] **Step 1: Write the failing test**

```python
# poc/tests/test_water_run.py
import json
from pathlib import Path

POC = Path(__file__).resolve().parents[1]


def _latest(track: str) -> Path:
    dirs = sorted(p for p in (POC / "runs").glob(f"*-{track}") if (p / "run_summary.json").is_file())
    assert dirs, f"geen canonieke run voor {track}"
    return dirs[-1]


def test_water_run_passes_with_v3():
    run = _latest("water")
    summary = json.loads((run / "run_summary.json").read_text())
    assert summary["verdict"] == "pass"
    assert "v3" in summary and "IoU" in json.dumps(summary.get("v3", "")).lower() or "geopandas" in summary["v3"].lower()
    zones = json.loads((run / "zones.json").read_text())
    assert zones, "water-run zonder zones"
    dt = json.loads((run / "decision-table.json").read_text())
    assert len(dt.get("rows", dt if isinstance(dt, list) else [])) >= 1


def test_water_replay_deterministic(tmp_path):
    run = _latest("water")
    replay = tmp_path / "replay.json"
    import subprocess, sys
    code = ("import json,sys;from pipeline.agents import NormAnalyst,NormFormalizer;"
            "cards=NormAnalyst('water').analyze();rules=NormFormalizer(cards,'water').formalize();"
            f"json.dump([cards,rules],open({str(replay)!r},'w'))")
    subprocess.run([sys.executable, "-c", code], cwd=POC, check=True,
                   env={"PYTHONPATH": str(POC), "PATH": "/usr/bin:/bin:/usr/local/bin"})
    cards, rules = json.loads(replay.read_text())
    run_cards = json.loads((run / "normcards.json").read_text())
    run_rules = json.loads((run / "formalrules.json").read_text())
    assert [c["id"] for c in cards] == [c["id"] for c in run_cards]
    assert [r["id"] for r in rules] == [r["id"] for r in run_rules]
```

(Als `NormAnalyst/NormFormalizer` andere constructorhandtekeningen hebben: spiegel de replay-aanroep zoals `python3 -m pipeline.agents` die doet — de assert blijft: herhaalde deterministische replay identiek aan de run-artefacten.)

- [ ] **Step 2: Templates + TRACKS + use-case + run**

1. `agents.py` TEMPLATE-tabel, per kaart naar het W-05-patroon (tekst letterlijk uit de shard citeren in `claim`; `geoBinding.zoneIds` = aliaskeys uit Task 5; `geometrySource: "provincial_gio"` met `gioJoinId` uitsluitend als die écht uit de laag/tekt bekend is — anders `caveat: CAVEAT_GIO_ACCESS`).
2. `run.py::TRACKS["water"]`:

```python
    "water": {
        "shard": "corpus/evidence-water.json",
        "ledger": "corpus/normcards-rejected-water.json",
        "report_title": "Where is riparian development bounded by the watersysteem rules in province Utrecht?",
        "decision_table_id": "DT-water-utrecht-poc1",
        "decision_table_title": "Watersysteem rule bounds for riparian development "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:water:",
        "headline_note": (
            "Semantics: instructieregels art. 2.14 (vrijwaringszone regionale waterkering), 2.15 "
            "(waterbergingsgebied) and 2.16 (overstroombaar gebied) bound development in and around "
            "the watersysteem; zones are the provincial designations clipped to the province "
            "boundary. Omgevingswaarden (monitoring norms) are deliberately abstained. "
            "Programming-stage screening artifact; per-location permission assessment remains required."
        ),
        "limitations": lambda cov, abst: [
            "Waterkering-omgevingswaarden (art. 2.2-2.11) are monitoring norms for water boards, "
            "not zone rules: abstained under cite-or-abstain.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms, "
                "procedural rules): routed to the V4 human-expert checkpoint."
            ),
            "Peilbesluit/legger/waterschaarste articles are procedural for water boards: abstained.",
        ],
    },
```

3. `use-cases/water.json`: kopieer `use-cases/wind.json`, zet `id: "UC-water-utrecht-poc1"`, `objectType: "riparian_development"`, `ambitions: ["water_safety"]`, `requestedAt: "2026-10-04T10:00:00Z"` — **`areaOfInterest` letterlijk ongewijzigd laten** (provinciegrens).
4. Run: `cd poc && ../nldt/.venv/bin/python run.py --use-case water` → verdict `pass` vereist; commit de run-map zoals de bestaande canonieke runs (alle JSON-artefacten + rapport, geen `__pycache__`).

- [ ] **Step 3: Run tests + regressie**

Run: `cd poc && ../nldt/.venv/bin/python -m pytest tests -q` → alles groen (incl. bestaande suites-onderdelen).
Run: `git status --short poc/runs/20260830T113234Z-wind` → leeg (bestaande canonieke runs onaangeroerd).

- [ ] **Step 4: Commit**

```bash
git add poc/pipeline/agents.py poc/run.py poc/use-cases/water.json poc/runs/*-water poc/tests/test_water_run.py
git commit -m "feat(poc): water-track live — templates, TRACKS, use-case, canonieke pass-run"
```

---

### Task 7: bodem-recon

**Files:**
- Create: `poc/corpus/evidence-bodem.json`, `poc/corpus/normcards-rejected-bodem.json`
- Modify: `poc/corpus/track-manifest.json` (add `bodem`)
- Test: Task 3's `test_track_conformance["bodem"]`

**Interfaces:** identiek aan Task 4, nu hoofdstuk 3.

- [ ] **Step 1: Recon** — extractie per artikel zoals Task 4 (`grep -n "^Artikel 3.2 " …`). Verwachte verdeling:
- **Formaliseerbaar**: 3.2-kern grondwaterbeschermingszone(s) (instructieregels met gebiedsaanwijzing; record `BO-01…`), plus evt. 3.4 grondverzet/rommelterrein waar zonegebonden (`BO-02`), 3.5 gesloten stortplaats waar zonegebonden (`BO-03`) — de letterlijke tekst beslist; zonder zonedraagvlak → `articlesConsidered`.
- **articlesConsidered + abstentions**: 3.1 grondwaterbeheer (vergunning-/beoordelingskader: procedureel), 3.3 grondwaterverontreiniging (sanerings-/zorgplichtregels), niet-zonegebonden delen van 3.4/3.5.
- [ ] **Step 2: Manifestentry** — `"bodem": {"shard": "corpus/evidence-bodem.json", "ledger": "corpus/normcards-rejected-bodem.json", "objectType": "soil_activity", "chapters": ["3"], "formalizableArticles": [<de feitelijke lijst>], "useCase": "use-cases/bodem.json"}`
- [ ] **Step 3: Gate** — `cd poc && ../nldt/.venv/bin/python -m pytest tests/test_track_conformance.py -q` → `2 passed` (water én bodem actief).
- [ ] **Step 4: Commit** — `feat(poc): bodem-recon — evidence-shard H3 met cite-or-abstain-dekking`

---

### Task 8: bodem-zones

**Files:**
- Modify: `poc/data/sources.json`, `poc/run.py` (`ZONE_SOURCES`)
- Test: `poc/tests/test_bodem_zones.py`

**Interfaces:** als Task 5; aliaskeys `grondwater_beschermingszone`, `gesloten_stortplaats` (en `grondverzet_gebied` uitsluitend als de probe er een gebiedsaanwijzing voor vindt); selectieregel op `agrest-namen.json`: namen die `grondwater`, `stortplaats` of `rommelterrein` matchen; bestaande registry-entry `ow_bwp_grondwater` hergebruiken waar die dezelfde service dekt (niet dubbel registreren).

- [ ] **Step 1: failing test** — kopieer `test_water_zones.py`, hernoem naar `test_bodem_zones.py`, vervang de drie aliaskeys door de bodemkeys, de water-matchwoorden door `grondwater|stortplaats|rommelterrein` en de bestandsnamen. Run → FAIL.
- [ ] **Step 2: registreer + fetch + alias** — als Task 5 stap 3 (rollen: grondwaterbeschermingszone `conditional`/`exclusion` voor soil_activity conform de letterlijke regel).
- [ ] **Step 3: test groen** → `2 passed`; **Step 4: Commit** — `feat(poc): bodem-zones — registry, cache-twins en ZONE_SOURCES-aliases`

---

### Task 9: bodem formalisering + TRACKS + use-case + canonieke run

**Files:**
- Modify: `poc/pipeline/agents.py` (`BO-*`-templates), `poc/run.py` (`TRACKS["bodem"]`)
- Create: `poc/use-cases/bodem.json` (AoI letterlijk uit wind.json; `objectType: "soil_activity"`, `ambitions: ["water_safety"]`, `id: "UC-bodem-utrecht-poc1"`), `poc/runs/<ts>-bodem/`
- Test: `poc/tests/test_bodem_run.py` (kopie van `test_water_run.py` met `track="bodem"` en bestandsnaam aangepast)

**TRACKS["bodem"]** (volledig):

```python
    "bodem": {
        "shard": "corpus/evidence-bodem.json",
        "ledger": "corpus/normcards-rejected-bodem.json",
        "report_title": "Where is soil activity bounded by groundwater and soil rules in province Utrecht?",
        "decision_table_id": "DT-bodem-utrecht-poc1",
        "decision_table_title": "Ondergrond-en-bodem rule bounds for soil activity "
                                "Decision table (programming stage)",
        "prov_namespace": "ldttoolbox:poc:bodem:",
        "headline_note": (
            "Semantics: the grondwaterbeschermingszone instructieregels (art. 3.2 core) bound "
            "soil-affecting activities (infiltration, grondverzet) inside the designated protection "
            "zones; gesloten stortplaats and rommelterrein articles apply only where the letteral "
            "text carries a gebiedsaanwijzing. Groundwater permitting frames (art. 3.1) are "
            "procedural and deliberately abstained. Programming-stage screening artifact."
        ),
        "limitations": lambda cov, abst: [
            "Grondwaterbeheer (art. 3.1) and verontreiniging (art. 3.3) are permitting/assessment "
            "frames: abstained under cite-or-abstain.",
            (
                f"{cov['ambiguous']} of {cov['output_rules']} rules are intentionally 'ambiguous' (open norms): "
                "routed to the V4 human-expert checkpoint."
            ),
        ],
    },
```

Stappen zoals Task 6 (failing test → templates/TRACKS/use-case → `run.py --use-case bodem` → verdict `pass` → suite + canonieke-regressie → commit `feat(poc): bodem-track live — templates, TRACKS, use-case, canonieke pass-run`).

---

### Task 10: fase-1-afsluiting — volledige regressie + documentatie

**Files:**
- Modify: `poc/README.md` (tracklijst + één regel per nieuwe track), `docs/SOLUTIONS_ARCHITECTURE.md` (§2 usetabel + §4 rooster: water/bodem-regels)

- [ ] **Step 1: Volledige regressie** — `cd poc && ../nldt/.venv/bin/python -m pytest tests -q` (alles groen); `cd ../nldt && .venv/bin/python -m pytest tests -q` (336 verwacht); `cd ../toolbox-sim && ../nldt/.venv/bin/python -m pytest tests -q` (65+1 skip verwacht).
- [ ] **Step 2: Docs** — poc/README tracktabel: `water (riparian_development)` en `bodem (soil_activity)` met elk hun canonieke run-id; SOLUTIONS_ARCHITECTURE §2-usetabel krijgt de twee tracks erbij (zelfde vorm als wind/zon/bos-regels, met de daadwerkelijke km²-uitkomsten uit de run_summary's — letterlijk overnemen, niet afronden).
- [ ] **Step 3: Commit** — `docs(poc): fase 1 verordening-uitbreiding — water+bodem in README en architectuurdoc`
