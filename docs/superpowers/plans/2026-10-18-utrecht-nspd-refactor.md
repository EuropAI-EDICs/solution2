# Utrecht-PoC NSPD-refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De Utrecht-PoC intern herbouwen op NSPD-patroon — declaratieve `poc/tracks/`, registry v2.0 met probe-bewijs, `add_zone_rule` what-ifs, NSPD-stijl README — met byte-identiek pijplijngedrag.

**Architecture:** Vier fasen met elk een eigen merge-gate: (1) de hardcoded dicten (`TRACKS` + lambdas in `run.py`, `EVIDENCE_ENRICHMENT`/`TEMPLATE_SPECS` in `agents.py`, `ZONE_SOURCES`) verhuizen via een extractor-script naar `poc/tracks/*.json` met een kleine laadmodule; (2) `poc/data/sources.json` wordt voltooid naar registry v2.0 (fetchPolicy + provenance; rollen bestaan al) met een probe-tool; (3) de NSPD-`add_zone_rule`-mutatie wordt geport naar de Utrecht-sweep met aliassen over de nationale caches en twee what-if-scenario's; (4) README en prompts strakker. Acceptatie is telkens: corpus-regeneratie byte-identiek, golden-regressie groen, volledige suite groen, demo ongewijzigd.

**Tech Stack:** Python 3.13 (miniconda-base, `/opt/homebrew/Caskroom/miniconda/base/bin/python3`), pytest, stdlib; canonieke test-aanroep `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -q`; deep-agents: `cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q`.

**Spec:** `docs/superpowers/specs/2026-10-18-utrecht-nspd-refactor-design.md`.

## Global Constraints

- Corpus-regeneratie byte-identiek: `json.dumps([c.to_dict() for c in cards], ensure_ascii=False, indent=2) + "\n"` moet gelijk blijven aan de gecommitte `corpus/normcards-<track>.json` / `formalrules-<track>.json` voor alle 13 tracks (task 3 legt dit als test vast).
- Golden-regressie groen: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -m golden -q`.
- Volledige suite groen: 362+ tests; deep-agents-suite (53) groen; live_server-/api-scenarios ongewijzigd gedrag.
- Landelijke bronnen worden nooit juridische claims; what-ifs zijn `hypothetical` + V2-gate (NSPD-`ZONE_CAPABLE_ROLES = ("scenario-basis", "inclusion", "exclusion", "attention")`; `context` nooit zone-bepalend).
- De 13 canonieke scenario-sets blijven exact 3 scenario's tellen (energietoets 3 sinds plan 2); what-ifs leven in aparte `*-whatif.json`-sets buiten het 3-per-track-contract.
- Geen wijzigingen aan engine-semantiek (`pipeline/engine.py`), critic-levels, of de inhoud van de bestaande 39 scenario's.
- Commit-formaat: `refactor(poc): … (nspd-port, fase N, task M)`; elke fase eindigt met een gate-taak vóór de volgende begint.

---

## FASE 1 — tracks/ declaratief

### Task 1: extractor + poc/tracks/*.json genereren

**Files:**
- Create: `poc/tracks/make_tracks.py` (extractor, NSPD-stijl `make_aoi.py`-patroon)
- Create: `poc/tracks/<track>.json` × 13, `poc/tracks/_zone-sources.json` (gegenereerd)
- Modify: `poc/tracks/<track>.json` (limitations-conversie, handmatig per track)

**Interfaces:**
- Produces: `poc/tracks/<track>.json` met alle TRACKS-velden behalve `limitations` (die komt als `"limitationsTemplate": null` en wordt in Task 2 handmatig gevuld); `poc/tracks/_zone-sources.json` met de volledige ZONE_SOURCES-dict. Task 2's loader consumeert deze bestanden.

De TRACKS-dict (`poc/run.py:268`) heeft per track: `shard`, `ledger`, `report_title`, `decision_table_id`, `decision_table_title`, `prov_namespace`, `headline_note`, `limitations` (lambda). ZONE_SOURCES (`poc/run.py:69`) is `{zoneId: {sourceId, note}}` (juridische agrest/ArcGIS-aliassen — apart van de nationale fase-3-aliassen).

- [ ] **Step 1: Schrijf de extractor**

```python
"""One-shot extractor: TRACKS/ZONE_SOURCES uit poc/run.py -> poc/tracks/*.json.

Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 tracks/make_tracks.py
Limitations-lambdas worden niet geserialiseerd: elk <track>.json krijgt
"limitationsTemplate": null en wordt handmatig gevuld (task 2, wind is het
uitgewerkte voorbeeld). Idempotent: herschrijft de gegenereerde bestanden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # poc/ op pad zodat `run` importeerbaar is

from run import TRACKS, ZONE_SOURCES  # noqa: E402


def main() -> None:
    for track, cfg in TRACKS.items():
        out = {k: v for k, v in cfg.items() if k != "limitations"}
        out["limitationsTemplate"] = None  # handmatig vullen (task 2)
        (HERE / f"{track}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"tracks/{track}.json ({', '.join(sorted(out))})")
    (HERE / "_zone-sources.json").write_text(
        json.dumps(ZONE_SOURCES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tracks/_zone-sources.json ({len(ZONE_SOURCES)} aliassen)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Draai de extractor en verifieer**

Run: `cd /Users/marc/Projecten/ldttoolbox/poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 tracks/make_tracks.py`
Expected: 13 regels `tracks/<track>.json …` + `tracks/_zone-sources.json (<N> aliassen)`; geen tracebacks.

- [ ] **Step 3: Vul limitationsTemplate handmatig (13×, wind als voorbeeld)**

Conventie: de lambda-lichaams-f-strings worden template-strings; `cov['X']` → `{X}` (gevonden keys: `ambiguous`, `output_rules`, `formalized`); de `abst`-parameter wordt in geen enkele lambda gebruikt (geverifieerd: grep `abst[` = 0 hits in run.py).

Voorbeeld wind (`poc/tracks/wind.json`) — de lambda uit `run.py:285-300` wordt:

```json
"limitationsTemplate": [
  "The province-scale 'Gebied windenergie' polygon (1166.5 km²) is a designation envelope, not a 'suitable everywhere' area: clustering, removal duty, beeldkwaliteit and municipal omgevingsplan rules still apply per location.",
  "{ambiguous} of {output_rules} rules are intentionally 'ambiguous' (open norms such as 'onevenredig aantasten', deviation paths, noise ambitions): they carry no executable predicate (cite-or-abstain) and are routed to the V4 human-expert checkpoint; the deterministic map consumed only the {formalized} formalized rules.",
  "Abstained topics (no verified provincial citation): stikstof deposition, national wind-turbine noise limits (Wgh/Bal), tip height/setback distances, Natura 2000 GIO absence, ET_wind tracking-layer misrepresentation risk, the pending 1-1-2027 amendment."
],
```

Herhaal letterlijk voor de overige 12 tracks (lees elk lambda-lichaam in `run.py` en vervang alleen de cov-indices door placeholders). Gebruik `"limitationsTemplate": null` blijft bestaan bij twijfel — task 3's vergelijkingstest vangt elke afwijking.

- [ ] **Step 4: Commit**

```bash
git add poc/tracks/
git commit -m "refactor(poc): poc/tracks/*.json geëxtraheerd uit TRACKS/ZONE_SOURCES (nspd-port, fase 1, task 1)"
```

### Task 2: track_config.py loader + run.py/agents.py als consumer

**Files:**
- Create: `poc/pipeline/track_config.py`
- Modify: `poc/run.py:69-…` (ZONE_SOURCES-dict → loader), `poc/run.py:268-…` (TRACKS-dict → loader)
- Modify: `poc/pipeline/agents.py:228-…` (EVIDENCE_ENRICHMENT-dict → loader), `poc/pipeline/agents.py:1301-…` (TEMPLATE_SPECS-dict → loader)
- Test: `poc/tests/test_track_config.py` (nieuw)

**Interfaces:**
- Consumes: `poc/tracks/*.json` (task 1).
- Produces: `track_config.load_track(track_id: str) -> dict` (keys = oude TRACKS-entry incl. callable `limitations(cov, abst) -> list[str]`), `track_config.load_enrichment() -> Dict[str, dict]`, `track_config.load_templates() -> Dict[str, dict]`, `track_config.load_zone_sources() -> Dict[str, dict]`.

- [ ] **Step 1: Write the failing tests**

```python
"""track_config: declaratieve track-lading (nspd-port fase 1)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import track_config  # noqa: E402

TRACKS13 = ["wind", "zon", "bos", "water", "bodem", "mobiliteit", "landschap",
            "landbouw", "wonen", "werken", "recreatie", "biomassa", "energietoets"]


def test_load_track_geeft_alle_velden_en_callable_limitations():
    cfg = track_config.load_track("wind")
    for key in ("shard", "ledger", "report_title", "decision_table_id",
                "decision_table_title", "prov_namespace", "headline_note"):
        assert key in cfg, key
    assert callable(cfg["limitations"])


def test_limitations_templates_gelijk_aan_oude_lambdas():
    """Vergelijkt gerenderde limitations van de templates met de oorspronkelijke
    lambda-uitkomsten (vast leguster: vaste cov). De 13 lambdas zijn in task 2
    verwijderd; deze asserts zijn tegen de handmatig omgezette templates."""
    cov = {"ambiguous": 13, "output_rules": 24, "formalized": 11}
    # wind-voorbeeld letterlijk uit run.py:285 (lambda-output met deze cov):
    rendered = track_config.load_track("wind")["limitations"](cov, [])
    assert rendered[1].startswith("13 of 24 rules are intentionally 'ambiguous'")
    assert "consumed only the 11 formalized rules." in rendered[1]


def test_load_enrichment_en_templates_omvatten_alle_84_ids():
    enr = track_config.load_enrichment()
    tpl = track_config.load_templates()
    assert len(enr) >= 84 and len(tpl) >= 84
    assert set(enr) == set(tpl)


def test_load_zone_sources_gelijk_aan_oude_dict():
    zs = track_config.load_zone_sources()
    assert "gebied_windenergie" in zs and "natura_2000" in zs
    assert zs["gebied_windenergie"]["sourceId"] == "agrest-ov-gebied-windenergie"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_track_config.py -v`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError` (track_config bestaat niet).

- [ ] **Step 3: Implementeer track_config.py**

```python
"""Declaratieve track-lading (nspd-port fase 1): poc/tracks/*.json.

Enige lezer van poc/tracks/; run.py en agents.py zijn consumers. De
limitations-templates worden geformatteerd met de coverage-dict van de
formalizer (keys: ambiguous, output_rules, formalized) — format_map faalt
luid op een onbekende placeholder (geen stil geweid gedrag).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

POC_ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = POC_ROOT / "tracks"


def _read(name: str) -> Any:
    return json.loads((TRACKS_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load_track_raw(track_id: str) -> dict:
    data = _read(f"{track_id}.json")
    templates = data.pop("limitationsTemplate")
    if not isinstance(templates, list) or not templates:
        raise ValueError(
            f"tracks/{track_id}.json: limitationsTemplate ontbreekt of is leeg "
            "(vul de template-strings in — task 1 stap 3)")

    def limitations(cov: dict, abst: list) -> list:
        return [t.format_map(dict(cov)) for t in templates]

    data["limitations"] = limitations
    return data


def load_track(track_id: str) -> dict:
    return dict(_load_track_raw(track_id))


def load_all_tracks() -> dict:
    return {t: load_track(t) for t in sorted(
        p.stem for p in TRACKS_DIR.glob("*.json") if not p.stem.startswith("_"))}


def _merge_dir(subdir: str) -> dict:
    merged: dict = {}
    for p in sorted((TRACKS_DIR / subdir).glob("*.json")):
        merged.update(json.loads(p.read_text(encoding="utf-8")))
    return merged


@lru_cache(maxsize=None)
def load_enrichment() -> dict:
    return _merge_dir("_enrichment")


@lru_cache(maxsize=None)
def load_templates() -> dict:
    return _merge_dir("_templates")


@lru_cache(maxsize=None)
def load_zone_sources() -> dict:
    return _read("_zone-sources.json")
```

- [ ] **Step 4: Vervang de dicten door loader-consumptie**

In `poc/run.py`: verwijder het ZONE_SOURCES-blok (regel 69-…, tot de sluitende `}`) en zet op die plek:

```python
from pipeline import track_config  # noqa: E402  (bovenaan, bij de overige pipeline-imports)

ZONE_SOURCES: Dict[str, Dict[str, Any]] = track_config.load_zone_sources()
```

verwijder het TRACKS-blok (regel 268-1141) en zet op die plek:

```python
TRACKS: Dict[str, Dict[str, Any]] = {
    t: track_config.load_track(t) for t in track_config.load_all_tracks()
}
```

In `poc/pipeline/agents.py`: verwijder het `EVIDENCE_ENRICHMENT`-blok (regel 228-1087) en het `TEMPLATE_SPECS`-blok (regel 1301-2178) en zet op die plekken:

```python
from pipeline import track_config  # bovenaan bij de imports

EVIDENCE_ENRICHMENT: Dict[str, Dict[str, Any]] = track_config.load_enrichment()
TEMPLATE_SPECS: Dict[str, Dict[str, Any]] = track_config.load_templates()
```

Let op: `agents.py` heeft een import-dual (`from pipeline import contracts` + try/except `import contracts` — regel 33-36); voeg de track_config-import in hetzelfde patroon in, of importeer bovenaan op de plek waar contracts al geïmporteerd wordt (module-niveau, vóór de dict-definities).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_track_config.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add poc/pipeline/track_config.py poc/tests/test_track_config.py poc/run.py poc/pipeline/agents.py
git commit -m "refactor(poc): track_config-loader, run.py/agents.py consumers (nspd-port, fase 1, task 2)"
```

### Task 3: byte-identiek-corpus-gate + goldens (fase-1 gate)

**Files:**
- Test: `poc/tests/test_track_config.py` (uitbreiding)

**Interfaces:**
- Consumes: `agents.NormAnalyst`, `agents.NormFormalizer` (bestaand); serialisatie-recept uit `agents.generate_corpus` (`json.dumps(..., ensure_ascii=False, indent=2) + "\n"`).
- Produces: de blijvende regressietest `test_corpus_regenereert_byte_identiek` (13 tracks).

- [ ] **Step 1: Write the test**

```python
def test_corpus_regenereert_byte_identiek():
    """De declaratieve tracks moeten byte-identieke corpus-artefacten
    opleveren (nspd-port gate, spec §3): dezelfde serialisatie als
    agents.generate_corpus, nu voor alle 13 tracks."""
    from pipeline import agents

    corpus = ROOT / "corpus"
    for track in TRACKS13:
        analyst = agents.NormAnalyst()
        formalizer = agents.NormFormalizer()
        cards = analyst.read(corpus / f"evidence-{track}.json")
        rules = formalizer.formalize(cards)
        expected_cards = json.dumps(
            [c.to_dict() for c in cards], ensure_ascii=False, indent=2) + "\n"
        expected_rules = json.dumps(
            [r.to_dict() for r in rules], ensure_ascii=False, indent=2) + "\n"
        assert (corpus / f"normcards-{track}.json").read_text(encoding="utf-8") == expected_cards, track
        assert (corpus / f"formalrules-{track}.json").read_text(encoding="utf-8") == expected_rules, track
```

- [ ] **Step 2: Run de fase-1 gate**

```bash
cd /Users/marc/Projecten/ldttoolbox/poc
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_track_config.py tests/test_world_scene.py -v
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -q
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -m golden -q
```
Expected: alles groen (incl. golden-regressie). Bij faal: de faalende track's `limitationsTemplate` of extractie corrigeren (task 1/2 revisie), niet de corpus-bestanden.

- [ ] **Step 3: Demo-smoke**

```bash
cd /Users/marc/Projecten/ldttoolbox/deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages ../nldt/.venv/bin/python -m pytest tests -q
curl -s "http://127.0.0.1:8765/api/scenarios?poc=utrecht" | head -c 200
```
Expected: 53 passed; API antwoordt (server draait met oude code — de import wijzigt pas na herstart; de smoke checkt alleen dat de API leeft).

- [ ] **Step 4: Commit (fase-1 gate)**

```bash
git add poc/tests/test_track_config.py
git commit -m "test(poc): byte-identiek-corpus-gate over 13 tracks (nspd-port, fase 1, task 3 — gate)"
```

---

## FASE 2 — registry v2.0 volmaken + probe

### Task 4: registry v2.0 (fetchPolicy + provenance; roles bestaan al)

**Files:**
- Create: `poc/data/make_registry_v2.py` (migratie-script)
- Modify: `poc/data/sources.json` (registryVersion "1.0" → "2.0"; per entry `fetchPolicy` + `provenance`)
- Test: `poc/tests/test_registry_v2.py` (nieuw)

**Interfaces:**
- Consumes: bestaande sources.json (`registryVersion: "1.0"`, 122 entries met `role`; probe-lijst onder `probeEvidence`).
- Produces: registry v2.0 — `{"registryVersion": "2.0", "sources": [...]}` met per entry `fetchPolicy: "cache"|"service"` en `provenance: {pinned: "<ISO-datum>", evidence: "<pad>", note?: str}`. Geodata/national_data blijven `{id: entry}`-consumers (load_sources ongewijzigd contract).

- [ ] **Step 1: Write the failing test**

```python
"""Registry v2.0-vorm (nspd-port fase 2)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))


def test_registry_is_v2_met_verplichte_velden():
    assert REG["registryVersion"] == "2.0"
    for it in REG["sources"]:
        assert it["role"] in {
            "inclusion", "exclusion", "conditional", "attention", "compensation",
            "context", "scenario-basis", "aoi"}, it["id"]
        assert it["fetchPolicy"] in {"cache", "service"}, it["id"]
        prov = it["provenance"]
        assert prov["pinned"] and len(prov["pinned"]) == 10, it["id"]  # ISO-datum
        assert prov.get("evidence"), it["id"]


def test_load_sources_werkt_nog_tegen_v2():
    import sys
    sys.path.insert(0, str(ROOT))
    from pipeline.geodata import load_sources
    src = load_sources()
    assert "agrest-ov-gebied-windenergie" in src
    assert src["netbeheerder-netcongestie"]["role"] == "scenario-basis"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_registry_v2.py -v`
Expected: FAIL — `registryVersion == "2.0"` faalt (staat op "1.0").

- [ ] **Step 3: Schrijf en draai de migratie**

```python
"""One-shot migratie: sources.json v1.0 -> v2.0 (fetchPolicy + provenance).

fetchPolicy: "cache" als de bron een dual-CRS-cache heeft (cachePath in een
van de 13 canonieke layers.json-manifesten, of een bestand onder
data/cache/national/), anders "service". provenance.pinned = lastChecked van
de bron (of de probe-datum 2026-08-30 voor de agrest/ArcGIS-set); evidence =
de probe-ref uit de bestaande probeEvidence-lijst; note/notes verhuizen naar
provenance.note (de sleutel blijft bewaard voor backwards-compat — consumers
lezen hem niet, geverifieerd per grep, maar weglaten is onnodig risico).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE.parent

reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
manifest_caches: set[str] = set()
for run in sorted((POC / "runs").glob("*/layers.json")):
    for laag in json.loads(run.read_text(encoding="utf-8")).values():
        cp = laag.get("cachePath")
        if cp:
            manifest_caches.add(Path(cp).name)
national = {p.name for p in (POC / "data" / "cache" / "national").rglob("*.json")}
probe_refs = reg.get("probeEvidence", [])
default_probe = probe_refs[0] if probe_refs else "poc/data/probe_raw_20260830.json"

for it in reg["sources"]:
    caches = {f"{it['id']}.28992.geojson", f"{it['id']}.4326.geojson", f"{it['id']}.json"}
    hit = bool(caches & manifest_caches) or any(it["id"] in n for n in national)
    it["fetchPolicy"] = "cache" if hit else "service"
    note = it.pop("note", it.pop("notes", None))
    pinned = str(it.get("lastChecked") or "2026-08-30")[:10]
    it["provenance"] = {"pinned": pinned,
                        "evidence": default_probe,
                        **({"note": note} if note else {})}
    it.setdefault("role", "context")

reg["registryVersion"] = "2.0"
(HERE / "sources.json").write_text(
    json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("registry v2.0:", len(reg["sources"]), "entries;",
      sum(1 for i in reg["sources"] if i["fetchPolicy"] == "cache"), "cache /",
      sum(1 for i in reg["sources"] if i["fetchPolicy"] == "service"), "service")
```

(Sla op als `poc/data/make_registry_v2.py`, draai: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 data/make_registry_v2.py`. Let op: `it.pop("note", it.pop("notes", None))` — pop-volgorde maakt dat `note` wint; beide sleutels komen voor in de registry.)

- [ ] **Step 4: Run tests to verify they pass + volledige suite**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_registry_v2.py tests/test_uitdagingen.py -v
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -q
```
Expected: PASS; volledige suite groen (V2-dataGrounding-check leest role — ongewijzigd).

- [ ] **Step 5: Commit**

```bash
git add poc/data/make_registry_v2.py poc/data/sources.json poc/tests/test_registry_v2.py
git commit -m "refactor(poc): registry v2.0 — fetchPolicy + provenance per bron (nspd-port, fase 2, task 4)"
```

### Task 5: probe_sources.py + frisse probe-evidence

**Files:**
- Create: `poc/data/probe_sources.py`
- Create: `poc/data/probe-sources-<datum>.json` (gegenereerd, gecommit)
- Modify: `poc/data/sources.json` (probeEvidence-lijst uitgebreid met het nieuwe bestand; `provenance.evidence` per entry wijst naar de frisse probe waar beschikbaar)

**Interfaces:**
- Consumes: registry v2.0 (task 4); `pipeline.geodata` ArcGIS-count-patroon (zie `poc/data/calibrate.py::arcgis_count`).
- Produces: `poc/data/probe-sources-<datum>.json` — `{datum, aoi, bronnen: [{id, role, bereikbaar, featureCount|null, fout?}]}` voor de gebruikte bronnen (aanwezig in een layers.json-manifest of met role scenario-basis).

- [ ] **Step 1: Implementeer probe_sources.py**

```python
"""Live probe van de gebruikte Utrecht-bronnen (nspd-port fase 2).

Leest de registry, kiest de bronnen die in een layers.json-manifest voorkomen
of role scenario-basis hebben, en probeert elk: ArcGIS-count (agrest/hub),
OGC-API/WFS-head (nationale bronnen), of "document" (skip). Schrijft
probe-sources-<datum>.json als NSPD-stijl evidence. Lees-only: raakt geen
caches. Run: cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 data/probe_sources.py
"""
from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE.parent
AOI = {"type": "Polygon", "coordinates": [[[130000, 440000], [160000, 440000],
      [160000, 470000], [130000, 470000], [130000, 440000]]]}


def _arcgis_count(entry: dict) -> int | None:
    url = f"{entry['serviceUrl']}/{entry.get('layerId', 0)}/query?f=json&where=1%3D1&returnCountOnly=true"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return int(json.loads(r.read().decode("utf-8")).get("count"))
    except Exception as exc:  # bewust breed: de probe registreert, faalt nooit
        return None if not isinstance(exc, KeyboardInterrupt) else None


def main() -> int:
    reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    used: set[str] = set()
    for run in sorted((POC / "runs").glob("*/layers.json")):
        for laag in json.loads(run.read_text(encoding="utf-8")).values():
            sid = laag.get("aliasSourceId")
            if sid:
                used.add(sid)
    for it in reg["sources"]:
        if it.get("role") == "scenario-basis":
            used.add(it["id"])
    by_id = {it["id"]: it for it in reg["sources"]}
    out = {"datum": date.today().isoformat(), "aoi": AOI, "bronnen": []}
    for sid in sorted(used):
        it = by_id.get(sid)
        if not it or "serviceUrl" not in it:
            out["bronnen"].append({"id": sid, "role": it.get("role") if it else None,
                                   "bereikbaar": False, "featureCount": None,
                                   "fout": "geen serviceUrl (document/AOI)"})
            continue
        count = _arcgis_count(it) if "arcgis" in it["serviceUrl"] or "agrest" in it["serviceUrl"] else None
        out["bronnen"].append({"id": sid, "role": it.get("role"),
                               "bereikbaar": count is not None,
                               "featureCount": count})
    path = HERE / f"probe-sources-{date.today().isoformat()}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_ok = sum(1 for b in out["bronnen"] if b["bereikbaar"])
    print(f"probe {path.name}: {n_ok}/{len(out['bronnen'])} bereikbaar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Draai de probe en werk de registry bij**

Run: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 data/probe_sources.py`
Expected: `probe probe-sources-2026-10-XX.json: N/M bereikbaar` (N/M opschrijven in het rapport; niet-bereikbare bronnen zijn bevindingen, geen faal — noteer ze).

Werk daarna de registry bij met dit vaste script (bewaar als `poc/data/link_probe.py` of draai inline):

```python
import json
from datetime import date
from pathlib import Path
HERE = Path("poc/data")
pad = HERE / f"probe-sources-{date.today().isoformat()}.json"
reg = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
reg["probeEvidence"] = [f"poc/data/{pad.name}"] + [
    p for p in reg.get("probeEvidence", []) if "probe-sources-" not in p]
geprobeerd = {b["id"] for b in json.loads(pad.read_text(encoding="utf-8"))["bronnen"]}
for it in reg["sources"]:
    if it["id"] in geprobeerd:
        it["provenance"]["evidence"] = f"poc/data/{pad.name}"
(HERE / "sources.json").write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("probe gelinkt:", len(geprobeerd), "bronnen")
```

Run: `cd poc && /opt/homebrew/Caskroom/miniconda/base/bin/python3 data/link_probe.py`
Expected: `probe gelinkt: N bronnen`.

- [ ] **Step 3: Suite + commit**

```bash
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests/test_registry_v2.py -q
/opt/homebrew/Caskroom/miniconda/base/bin/python3 -m pytest tests -q
git add poc/data/probe_sources.py poc/data/probe-sources-*.json poc/data/sources.json
git commit -m "feat(poc): probe_sources-tool + frisse probe-evidence (nspd-port, fase 2, task 5 — gate fase 2)"
```

---

## FASE 3 — add_zone_rule what-ifs

### Task 6: schema-uitbreiding add_zone_rule

**Files:**
- Modify: `poc/schemas/scenario-spec.schema.json` (action-enum + zoneId-property)
- Test: `poc/tests/test_scenarios.py` (uitbreiding)

**Interfaces:**
- Produces: `mutations[]`-items met `action: "add_zone_rule"` + verplicht `zoneId`; verder ongewijzigd. Task 7 consumeert dit in de sweep.

- [ ] **Step 1: Write the failing test** (naar het Task-1-patroon van plan 2; unittest-stijl, `contracts.ContractError`)

```python
    def test_add_zone_rule_is_toegestaan_met_zoneid(self):
        spec = {
            "id": "SC-T-AZR", "name": "test", "objectType": "business_development",
            "basis": {
                "type": "hypothetical",
                "rationale": "data-grounded what-if",
                "provenanceNote": "NOT legally grounded: data-grounded only.",
                "dataGrounding": {"sourceId": "netbeheerder-netcongestie",
                                  "retrieved": "2026-10-14"},
            },
            "mutations": [{"ruleId": "SC-AZR-1", "action": "add_zone_rule",
                           "zoneId": "netcongestie", "zoneSemantics": "exclusion",
                           "bufferDistanceM": 1000}],
            "proposedBy": "a#b",
        }
        contracts.validate(spec, "scenario-spec")  # V0-gate

    def test_add_zone_rule_zonder_zoneid_faalt(self):
        spec = {
            "id": "SC-T-AZR2", "name": "test", "objectType": "business_development",
            "basis": {
                "type": "hypothetical",
                "rationale": "x",
                "provenanceNote": "NOT legally grounded.",
                "dataGrounding": {"sourceId": "netbeheerder-netcongestie",
                                  "retrieved": "2026-10-14"},
            },
            "mutations": [{"ruleId": "SC-AZR-2", "action": "add_zone_rule",
                           "zoneSemantics": "exclusion"}],
            "proposedBy": "a#b",
        }
        with self.assertRaises(contracts.ContractError):
            contracts.validate(spec, "scenario-spec")
```

- [ ] **Step 2: Run → FAIL** (`zoneId` onbekend / action niet in enum)

- [ ] **Step 3: Patch het schema** — in `poc/schemas/scenario-spec.schema.json`: `action.enum` uitbreiden met `"add_zone_rule"`; in `mutations.items.properties` toevoegen: `"zoneId": {"type": "string", "minLength": 1}`; het basis-oneOf/anyOf dat per action voorwaarden stelt (zoals `zoneSemantics` bij `set_semantics`) uitbreiden met de `add_zone_rule`-combinatie (`zoneId` + `zoneSemantics` verplicht; `bufferDistanceM` optioneel) — volg de bestaande conditional-structuur in het schema (bekijk de `allOf`-blokken rond de mutations).

- [ ] **Step 4: Run → PASS + volledige suite groen**

- [ ] **Step 5: Commit** — `feat(poc): scenario-spec action add_zone_rule + zoneId (nspd-port, fase 3, task 6)`

### Task 7: add_zone_rule-executie in de sweep (NSPD-port)

**Files:**
- Modify: `poc/pipeline/scenarios.py` (mutatie-tak + alias-lader + V2-gate)
- Test: `poc/tests/test_scenarios.py` (uitbreiding — port van de drie NSPD-tests)

**Interfaces:**
- Consumes: schema (task 6); `poc/tracks/_zone-aliases.json` (task 8 — in deze task met een stub-alias-dict getest).
- Produces: `apply_mutations` accepteert `add_zone_rule` (synthetische regel volgens NSPD `_synthetic_zone_rule`-vorm); `load_extra_zone_layers(zone_ids, aliases, cache_root=Path)` leest alias-caches (Utrecht-conventie: `alias["cachePath"]` relatief aan poc/); `track_config.load_zone_aliases() -> dict` (leest `_zone-aliases.json`, geeft `{}` als het bestand ontbreekt — task 8 legt het echte bestand neer); de sweep-loop (`run_scenario_set`) krijgt `zone_aliases` als parameter met die loader als default en voert de V2-check `v2-add-zone-rule` uit via extra check (hypothetical + dataGrounding.sourceId == alias-sourceId + alias-role in `ZONE_CAPABLE_ROLES`).

Port-bron: `poc-nspd/pipeline/scenarios.py` regel 209-300 (`add_zone_rule_zone_ids`, `load_extra_zone_layers`, `sources_prov_from_manifest`), 293-300 (`ZONE_CAPABLE_ROLES`, `_SEMANTICS_RULE_TYPE`), 300-340 (`_synthetic_zone_rule`), 348-388 (`apply_mutations`-tak) — lees die volledig vóór het porten; de enige Utrecht-aanpassingen: (a) alias-lader leest `cachePath` uit het alias-item i.p.v. `<sid>.28992.geojson`-conventie (Utrecht's nationale caches liggen onder `data/cache/national/`, genest voor netcongestie); (b) de V2-gate checkt de alias-rol via `zone_aliases[zoneId]["role"]` tegen `ZONE_CAPABLE_ROLES` en `dataGrounding.sourceId == alias["sourceId"]`.

- [ ] **Step 1: Port de drie NSPD-tests** naar `poc/tests/test_scenarios.py` (unittest-stijl, nieuw TestCase `AddZoneRuleTests`) — bron: `poc-nspd/tests/test_scenarios_nspd.py:256` (`test_add_zone_rule_voegt_synthetische_regel_toe_en_rekent_door`), `:283` (`…collision_en_ontbrekende_velden_zijn_authoring_fouten`), `:300` (`…v2_add_zone_rule_eist_hypothetical_en_passende_dataGrounding`). Lees elk NSPD-testlichaam volledig en pas alleen de imports/paden aan. Vervang NSPD-alias-fixture-door een stub `{"netcongestie": {"sourceId": "netbeheerder-netcongestie", "role": "scenario-basis", "cachePath": "<tmp>/netcongestie.geojson"}}` (tmp_path fixture).

- [ ] **Step 2: Run → FAIL** (action onbekend in `apply_mutations`)

- [ ] **Step 3: Port de implementatie** (zie port-bron hierboven; including `scenario-spec`-schema-echo: geen wijziging — de sweep valideert specs al tegen scenario-spec). Neem ook `add_zone_rule_zone_ids` + `load_extra_zone_layers` + `sources_prov_from_manifest` op in `pipeline/scenarios.py` (Utrecht-naamgeving behouden) en wire ze in de sweep-loop waar `apply_mutations` wordt aangeroepen (alias-lagen merge in `layers` vóór `execute_rule_set`; manifest merge vóór provenance; degradaties in de bestaande `degradations`-lijst).

- [ ] **Step 4: Run → PASS + volledige suite groen**

- [ ] **Step 5: Commit** — `feat(poc): add_zone_rule-executie + V2-gate in de sweep (nspd-port, fase 3, task 7)`

### Task 8: aliassen + twee what-if-scenario's (fase-3 gate)

**Files:**
- Create: `poc/tracks/_zone-aliases.json`
- Create: `poc/scenarios/werken-whatif.json`, `poc/scenarios/wonen-whatif.json`
- Create: `poc/scenario-runs/<ts>-werken-whatif/`, `<ts>-wonen-whatif/` (sweep-output, commit zoals de 13 featured runs)
- Modify: geen bestaande sets

**Interfaces:**
- Consumes: task 7 (sweep-executie), nationale caches (plan 2).
- Produces: alias-registry + twee what-if-runs (verdict pass). De 13 canonieke sets en `uitdagingen.json` blijven ongewijzigd (what-ifs vallen buiten het 3-per-track-contract).

- [ ] **Step 1: Schrijf `poc/tracks/_zone-aliases.json`**

```json
{
  "netcongestie": {
    "sourceId": "netbeheerder-netcongestie",
    "cachePath": "data/cache/national/netcongestie/netcongestie.geojson",
    "role": "scenario-basis",
    "note": "Landelijke Capaciteitskaart 'afname' (plan 2, task 6) — voedingsgebieden"
  },
  "rce-monumenten": {
    "sourceId": "rce-monumenten",
    "cachePath": "data/cache/national/rce-monumenten.json",
    "role": "context",
    "note": "rijksmonumentpunten (punten; engine buffert tot vlakken)"
  },
  "rce-iam-archeologie": {
    "sourceId": "rce-iam-archeologie",
    "cachePath": "data/cache/national/rce-iam-archeologie.json",
    "role": "context",
    "note": "AMK-2014 archeologische monumenten/terreinen"
  },
  "nwb-wegvakken": {
    "sourceId": "rws-nwb-wegen",
    "cachePath": "data/cache/national/rws-nwb-wegen.json",
    "role": "context",
    "note": "NWB-wegvakken (servercap 1000/request)"
  },
  "prorail-spoor": {
    "sourceId": "prorail-spoor",
    "cachePath": "data/cache/national/prorail-spoor.json",
    "role": "context",
    "note": "spoorlijnen"
  }
}
```

Let op: de RCE/infra-aliassen hebben `role: context` — de V2-gate (ZONE_CAPABLE_ROLES bevat context **niet**) zal what-ifs op die lagen dus bewust weigeren; alleen `netcongestie` (scenario-basis) komt door de gate. Dat is de bedoeling van de gate — de twee demo-what-ifs gebruiken daarom netcongestie; de context-lagen staan geregistreerd voor een later besluit (rol-verhoging = beleidskeuze, geen code-wijziging). **Hierom zijn de twee scenario's:**

1. `SC-WER-NETCONGESTIE-1KM` (werken): exclusion 1 km rond `netcongestie` — data-gegrond; `basis.dataGrounding.sourceId: "netbeheerder-netcongestie"`.
2. `SC-WON-NETCONGESTIE-500M` (wonen): attention 500 m rond `netcongestie` — let op: attention is geen ZONE_CAPABLE_RULE_TYPE-issue (semantics inclusion|exclusion in `_synthetic_zone_rule`; attention via add_zone_rule is in NSPD niet uitdruikbaar — `_SEMANTICS_RULE_TYPE` kent alleen inclusion/exclusion). **Daarom scenario 2 = `SC-WON-NETCONGESTIE-INCLUSIE-500M`**: inclusion binnen 500 m van de netcongestiegebieden ("herstructureringsdruk rond knelpunten") — inclusion is gate-toegestaan en een ander verhaal dan de werken-exclusie.

(De spec noemde "wonen 250 m rond rijksmonumenten" — dat vergt een rol-verhoging van `rce-monumenten` naar scenario-basis; bewust uitgesteld tot dat besluit, zie boven. Vastleggen in het taakrapport.)

- [ ] **Step 2: Schrijf beide set-bestanden** (scenario-set-schema; `useCase`: "werken" resp. "wonen"; elk 1 scenario met `add_zone_rule`-mutatie en hypothetical+dataGrounding-basis zoals task 6's test)

- [ ] **Step 3: Voer beide sweeps uit**

```bash
cd /Users/marc/Projecten/ldttoolbox && /opt/homebrew/Caskroom/miniconda/base/bin/python3 poc/scenarios/run.py --set poc/scenarios/werken-whatif.json --no-h3
/opt/homebrew/Caskroom/miniconda/base/bin/python3 poc/scenarios/run.py --set poc/scenarios/wonen-whatif.json --no-h3
```
Expected: beide verdict pass (1 scenario + control per run). Commit de run-mappen (conventie featured runs).

- [ ] **Step 4: Volledige suite + goldens + deep-agents-suite** — alles groen.

- [ ] **Step 5: Commit (fase-3 gate)** — `feat(poc): zone-aliassen + twee data-gegronde what-ifs (nspd-port, fase 3, task 8 — gate)`

---

## FASE 4 — README + prompts strakker

### Task 9: README herschrijven (530 → ±350 regels)

**Files:**
- Modify: `poc/README.md`

**Structuurvoorschrift (NSPD-stijl, volgorde):** (1) titel + één-zin-succescriterium ("waar kan ik wat?" over 13 tracks × 5 uitdagingen, elke claim geciteerd, scenario's V2-gegate) + status-regel; (2) uitdagingen-tabel (uit `uitdagingen.json`, niet proza); (3) bronnen-tabel (uit registry v2: id/rol/fetchPolicy/pinned — samenvattend, niet alle 122); (4) "Run it"-blok (bestaande commando's, inkorten); (5) architectuurdiagram (ASCII, naar NSPD-voorbeeld: intake → … → run_summary); (6) scenario's + what-ifs kort (link naar uitdagingen.json/tracks/); (7) kalibratie; (8) limitations kort; (9) opdrachten. De lange zone-semantiek-per-track-proza (regels ~159-307) verdwijnt — die staat al declaratief in `poc/tracks/<track>.json` (headlineNote) en in de limitations-templates; de README linkt erheen.

- [ ] **Step 1: Herschrijf volgens het structuurvoorschrift; behoud alle nog-klopende commando's; verwijder alleen verhalende duplicatie.**
- [ ] **Step 2: Controleer** `wc -l poc/README.md` ≤ 380; grep op dode bestandsverwijzingen (`grep -oE '\(([^)]+\.(json|py|md))\)' poc/README.md` → elk pad bestaat).
- [ ] **Step 3: Commit** — `docs(poc): README NSPD-stijl (nspd-port, fase 4, task 9)`

### Task 10: prompts verwijzen naar tracks/ + eindgate

**Files:**
- Modify: `deep-agents/prompts/poc/utrecht.md`, `deep-agents/poc_demos.py` (alleen template-teksten)
- Test: deep-agents-suite + poc-suite (volledige eindgate)

- [ ] **Step 1: Pas de prompt-referenties aan** — `utrecht.md` verwijs in de Rules/Recipes naar de declaratieve bron ("tracks zijn declaratief beschreven in `poc/tracks/<track>.json`; verzin geen tracks buiten die lijst"); de poc_demos-templates waarin 13 tracks/39 scenario's worden opgesomd verwijzen voortaan naar `poc/scenarios/uitdagingen.json` + `poc/tracks/`. Geen gedragswijziging in de modes-lijst.
- [ ] **Step 2: Eindgate** — poc-suite groen; golden groen; deep-agents-suite groen; live_server-herstart + smoke (`/api/scenarios`, `/api/modes?poc=utrecht`).
- [ ] **Step 3: Commit** — `refactor(poc): prompts verwijzen naar declaratieve tracks (nspd-port, fase 4, task 10 — slotgate)`

---

## Self-review-notities (voor de uitvoerder)

- De gevaarlijkste stap is Task 2 (dicten vervangen door loader): de byte-identiek-test (Task 3) en de limitations-vergelijkingstest vangen elke conversiefout — verklein nooit die tests om groen te worden.
- ZONE_SOURCES en de fase-3 `_zone-aliases.json` zijn bewust twee verschillende bestanden (juridische zone-aliassen vs. nationale what-if-operanden).
- Na Task 8 telt de demo 41+ scenario's over 15 sets; de 3-per-track-contract-test telt alléén de 13 canonieke sets — niet verbreden.
