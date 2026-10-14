# poc-nspd fase 2 Implementatieplan — overige 10 tracks + eindreview-adviezen

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De overige 10 tracks (bos, water, bodem, mobiliteit, landschap, landbouw, wonen, werken, recreatie, biomassa) op de fase-1-machinerie van `poc-nspd/` — curatie NL+BE, runs, goldens, xborder-demo's — plus de technische/kwaliteitsadviezen uit de fase-1-eindreview als voorbereiding.

**Architecture:** Hergebruik de fase-1-machinerie ongewijzigd: TRACKS-tabel in run.py uitbreiden naar 13 tracks, per track evidence/normcards/formalrules-shards in `corpus/`, V2b met document_registry, FR-AOI-01-constructie bij zone-loze inclusions, goldens via `NSPD_GOLDEN_FREEZE=1`. Geen nieuwe bronnen pinnen zonder probe-bewijs; BE-corpus blijft S02–S05, NL blijft S01 (CVDR709135).

**Tech Stack:** ongewijzigd (Python 3.13 stdlib-first, pyproj, jsonschema, jinja2, pytest; Leia-submodule ongewijzigd).

**Spec:** `docs/superpowers/specs/2026-10-14-poc-nspd-design.md` §8 fase 2 (items 10–11; crosstrack-overlay blijft expliciet buiten scope). Fase-1-plan: `docs/superpowers/plans/2026-10-14-poc-nspd.md`. Eindreview-rapport: `.superpowers/sdd/progress.md` (sectie poc-nspd) + task-13-report/eindreview-notities.

## Global Constraints

- `poc/` en de overige repo-onderdelen blijven onaangeroerd; alle wijzigingen onder `poc-nspd/` (pathspec `-- poc-nspd` bij elke commit; uitzondering: `.gitignore` alleen indien gewijzigd).
- Werken in de fase-2-worktree `/Users/marc/Projecten/ldttoolbox-fase2` (checkout van `main`, met symlinks `poc-nspd/.venv` en `poc-nspd/data/cache` naar de hoofdcheckout) — de hoofdcheckout is in gebruik door een parallelle sessie. Commits landen direct op `main`. Bestaande branches niet aanraken.
- Cite-or-abstain: elke normcard uitsluitend met letterlijk verifieerbaar citaat (whitespace-genormaliseerd substring van de .txt-laag van het eigen docId); kaartformaat = strikte PoC-1-source-vorm, referentie `poc-nspd/corpus/normcards-nl-wind.json`.
- V2b met `document_registry=corpus/sources.json`, strict=True, in elke run; V2B-BRON faalt-closed.
- Luid falen; cache-first; geen netwerk in de standaard-suite; LLM uit.
- Zone-aliases alléén `natura2000-nl`, `natura2000-be`, `gebouwen-be`; geen nieuwe aliases zonder live-gepinde bron. Zone-loze regels expliciet taggen (`zone_loos_gedocumenteerd`, `v4_human_review`).
- Nieuwe bronnen worden NIET toegevoegd (fase 2 = curatie op bestaand corpus). Ontbrekende dekking = abstention, geen improvisatie.
- Goldens: bestaande 4 nooit herschrijven; nieuwe goldens alléén via `NSPD_GOLDEN_FREEZE=1`; golden-veldset blijft (verdict/output_rules/formalized/rejected/v2bStatus).
- Track-acceptatie per land: ≥1 gepromoveerde normcard mét formal rule, òf een expliciete abstention-record in de rejected-ledger (`corpus/normcards-rejected-{nl,be}-<track>.json` met track + reden) — beide zijn eerlijke cite-or-abstain-uitkomsten.
- Suite-baseline: 39 offline tests + 4 goldens groen bij start; elke taak laat álles groen.

## ID-conventies fase 2 (verbindend)

| track | normcard-id | evidence NL | evidence BE | objectType (poc/use-cases) |
|---|---|---|---|---|
| bos | NC-BOS-xx | EVB-xx | BVB-xx | forest_planting |
| water | NC-WAT-xx | EVD-xx | BVD-xx | riparian_development |
| bodem | NC-BOD-xx | EVO-xx | BVO-xx | soil_activity |
| mobiliteit | NC-MOB-xx | EVM-xx | BVM-xx | roadside_development |
| landschap | NC-LAN-xx | EVL-xx | BVL-xx | landscape_intervention |
| landbouw | NC-LNB-xx | EVG-xx | BVG-xx | agricultural_expansion |
| wonen | NC-WON-xx | EVH-xx | BVH-xx | housing_development |
| werken | NC-WER-xx | EVJ-xx | BVJ-xx | business_development |
| recreatie | NC-REC-xx | EVR-xx | BVR-xx | recreation_development |
| biomassa | NC-BIO-xx | EVX-xx | BVX-xx | biomass_installation |

Track-keys in TRACKS/use-cases/runs: `<track>-nl` / `<track>-be` (bijv. `bos-nl`). Decision-table-ids: `DT-<track>-<land>-nspd`; prov-namespace `ldttoolbox:poc-nspd:<track>-<land>:`.

Start-trefwoorden (curator mag uitbreiden mits gedocumenteerd): bos (bos, bosbouw, bosaanplant), water (waterkering, oppervlaktewater, grondwater, watervogel), bodem (bodem, bodemkwaliteit, bodemsanering), mobiliteit (weg, verkeer, infrastructuur), landschap (landschap, cultuurlandschap, kernkwaliteit), landbouw (landbouw, agrarisch, glastuinbouw), wonen (wonen, woningbouw), werken (bedrijventerrein, industrie, werken), recreatie (recreatie, dagrecreatie, verblijfsrecreatie), biomassa (biomassa, vergisting).

---

### Task 1: Eindreview-voorbereiding (guards, fixes, doc)

**Files:**
- Create: `poc-nspd/pipeline/quote_guard.py`, `poc-nspd/tests/test_quote_guard.py`, `poc-nspd/fetch_grb_layer.py`, `poc-nspd/tests/test_fetch_grb_layer.py`
- Modify: `poc-nspd/run.py` (fetch_layers-None), `poc-nspd/pipeline/jurisdictie_gate.py` (bron_jur/KeyError), `poc-nspd/tests/test_bbox.py` (tautologie), `poc-nspd/tests/test_run_nspd.py` (tautologie, _NSPD_TRACKS-annotatie wordt task 2), `poc-nspd/run.py` (dubbele inclusionBasis-zin), `poc-nspd/README.md` (geo-tabel 10/10, §4.4/§4.5-interpretaties)
- Test: bovengenoemde testbestanden + golden-testuitbreiding `test_controle_run`

**Interfaces:**
- Produces: `quote_guard.verify_all(corpus_root=Path) -> list[str]` (lege lijst = OK; anders per kaart een foutmelding met id+docId); `fetch_grb_layer.main(out_dir=Path, refresh=False, transport=None) -> Path` (schrijft `viewer-data/layers/grb-gebouwen-be.geojson`, WGS84).

- [ ] **Stap 1: Failing tests** — `test_quote_guard.py`: alle bestaande 16 kaarten (nl+be) moeten slagen (whitespace-genormaliseerde substring; helper hergebruiken/centraliseren); voeg één bewust kapotte kaart toe in-test (tmp corpus) om het faalpad te dekken. `test_fetch_grb_layer.py`: fake transport → bestand geschreven, features EPSG:4326-coördinaten (Lambert72→WGS84 via pyproj, hardcoded klein voorbeeld). `test_jurisdictie_gate.py`-uitbreiding: onbekende jurisdictie ("de") → `JurisdictieError` (geen kale KeyError). `run.py`-fetch_layers-test: monkeypatch `geodata.fetch_layer` die voor sourceId X gooit; twee zones met dezelfde alias → 2 degradations, geen AttributeError. `test_controle_run` (marker golden): draai wind-nl tweemaal (cache-first) → `headline.finalOpportunityKm2` exact gelijk.
- [ ] **Stap 2: Implementatie** — `quote_guard.py` (docId→txt-map: S01→`corpus/nl/CVDR709135/tekst.txt`; S02–S05→`corpus/be/<bestand-zonder-.pdf>.txt` via `corpus/be/META.json`; normalisatie: whitespace collapse + spatie-voor-leesteken zoals fase-1-reviews); run.py-fix: bij `by_source.get(sid) is None` → degradation `{"kind": "layer-fetch", "zone": …, "sourceId": sid, "error": "cached fetch failure for sourceId"}` en continue; jurisdictie_gate: `if jurisdictie not in _BE_NL_TYPES: raise JurisdictieError(...)` vóór gebruik, dode `bron_jur`-regel verwijderen; fetch_grb_layer.py: `fetch_geopunt_wfs(service_url, type_name="GRB:ADP", bbox_l72=nspd_bbox_l72(), …)` → features via pyproj Lambert72→WGS84 → FeatureCollection; README-geo-tabel aanvullen tot 10/10 bronnen uit `data/sources.json`; README-notities §4.4 (xborder-rapport zonder Leaflet-kaart is bewuste keuze: data draagt `land` per rij/feature; kaart via Leia-scène) en §4.5 (havenbedrijven/energie-infra-themalagen niet-gepind: gap, geen geo-pin beschikbaar in fase 2) + dedub van de inclusionBasis-zin in de FR-AOI-01-note.
- [ ] **Stap 3: Verificatie** — `.venv/bin/python -m pytest -q` (39 + nieuw, alles groen); `pytest -m golden -q` (4 + controle-run).
- [ ] **Stap 4: Commit** — `feat(poc-nspd): eindreview-voorbereiding — quote-guard, fetch_layers-degradatie, gate-hardening, GRB-laagfetch, docronde (fase 2, task 1)`.

### Task 2: Scaffold 13 tracks (TRACKS-tabel, use-cases, choices)

**Files:**
- Modify: `poc-nspd/run.py` (`_NSPD_TRACKS`-tabel + parser-choices), `poc-nspd/use-cases/make_aoi.py` (TRACKS-lijst 13)
- Create: `poc-nspd/use-cases/<track>-{nl,be}.json` ×20
- Test: `poc-nspd/tests/test_run_nspd.py` (uitbreiding: TRACKS-lengte 13, alle shards/evidence/normcards-paden resolven ná task 3+ — dus in deze taak alléén pad-patroon-check zonder bestandsassert, of de bestandsassert pas actief als de eerste groepstaak landt: kies een aparte marker `@pytest.mark.xfail(strict=False)`-vrij ontwerp: assert alléén voor de 6 fase-1-tracks; nieuwe tracks in een aparte test met skip-until-file-exists)

Concreet: uitbreiding `_NSPD_TRACKS` met 10 tuples (key, land, dt-id, titel) volgens het ID-conventietabel-patroon; titels in dezelfde Engelse vorm ("Where can forest planting occur in the Dutch part of the NSPD?" etc., BE-variant "…in the Flemish part…"). `make_aoi.py`: TRACKS-tuple uitbreiden, regenereren (20 nieuwe json's, schema-valid). `build_parser`-choices = sorted(TRACKS). Tests: TRACKS==13, use-cases 26 bestanden schema-valid, choices compleet. Commit: `feat(poc-nspd): scaffold 13 tracks — TRACKS-tabel, 26 use-cases, parser-choices (fase 2, task 2)`.

### Tasks 3–7: Curatie-groepen (sjabloon hieronder één keer volledig; per taak de parametertabel)

**Groepsindeling:** T3 = bos + water · T4 = bodem + mobiliteit · T5 = landschap + landbouw · T6 = wonen + werken · T7 = recreatie + biomassa.

**Track-taaksjabloon (letterlijk per track toepassen; de parametertabel per groep staat onderaan deze sectie):**

**Files:**
- Create: `poc-nspd/corpus/evidence-{nl,be}-<track>.json`, `poc-nspd/corpus/normcards-{nl,be}-<track>.json`, `poc-nspd/corpus/formal-rules-{nl,be}-<track>.json`, `poc-nspd/corpus/normcards-rejected-{nl,be}-<track>.json`, `poc-nspd/tests/test_normcards_<track>.json`-validatie in één gedeeld `tests/test_normcards_fase2.py` (parametrisch over de tracks van díe groepstaak)
- Modify: `poc-nspd/tests/test_golden_nspd.py` (TRACKS-tuple += `<track>-nl`)
- Runs: `poc-nspd/runs/<ts>-<track>-{nl,be}/` (committen), `poc-nspd/xborder-runs/<track>/` (committen)

**Stappen per track (tweemaal: nl en be):**
- [ ] Extractie: `extract_candidates`/`merge_brondocumenten` op S01 (nl) resp. S02–S05 (be) met de start-trefwoorden (+ curator-aanvulling, gedocumenteerd in het evidence-bestand via `curator-locatie`-notes zoals fase 1).
- [ ] Curatie (cite-or-abstain): alleen letterlijk dragende citaten → `verified: true`; kaarten in strikte vorm (id/evidenceId per ID-tabel, docId S01 resp. S02–S05, objectType per tabel, `extractedBy: "curator#poc-nspd-fase2-t<N>"`, `extractedAt: <vandaag>`); formal rules alleen voor kaarten; zoneIds uitsluitend de drie aliases of zone-loos getagd.
- [ ] Abstention where empty: rejected-ledger-record met track + reden (geen kaarten fabuleren).
- [ ] Validators: `test_normcards_fase2.py` parametrisch — schema-valid, evidence-link verified, instrumentType↔jurisdictie-allOf, quote-guard via `quote_guard.verify_all` voor de nieuwe bestanden.
- [ ] Runs: `run.py --use-case <track>-nl` en `-be` (cache-first); V2b pass; FR-AOI-01-rij constructie-vorm; run-dirs committen.
- [ ] Golden: TRACKS-tuple += `<track>-nl`; `NSPD_GOLDEN_FREEZE=1 .venv/bin/python -m pytest -m golden -q` (freeze), daarna gewone golden-run groen.
- [ ] Xborder: `python3 -m pipeline.xborder` op de twee runs → `xborder-runs/<track>/` committen.
- [ ] Commit per groep: `feat(poc-nspd): curatie <tracks> NL+BE — evidence/normcards/formalrules + runs + goldens + xborder (fase 2, task N)`.

**Parametertabellen** — per track: id's, objectType, trefwoorden (start), titels (nl/be Engels per patroon hierboven). De tabellen staan in §ID-conventies hierboven; titels volgen het vaste patroon.

### Task 8: Finale — energietoets-xborder, suite, README fase-2-status

**Files:**
- Create: `poc-nspd/xborder-runs/energietoets/` (rapport + geojson, committen)
- Modify: `poc-nspd/README.md` (status "fase 2 afgerond — 13 tracks", tracktabel met per track nl/be-uitkomst: kaartaantal of abstention, golden-aanduiding), `docs/superpowers/specs/2026-10-14-poc-nspd-design.md` (status-regel fase 2 geïmplementeerd)
- [ ] Energietoets-xborder genereren en committen.
- [ ] Volledige suite + goldens (39+新+14 goldens verwacht) groen; werkboom pristine.
- [ ] README/spec-statusupdates; commit `feat(poc-nspd): fase 2 afgerond — 13 tracks, xborder-demo's compleet, README-status (fase 2, task 8)`.

### Eindreview (na task 8)

Brede hele-branch-review over `e2e6724..HEAD` (alleen poc-nspd-commits), met de fase-2-aandachtspunten: curatie-kwaliteit per track (quote-guard blijft groen?), goldens-uitbreiding, xborder-artefacten consistent, README-claims kloppen met artefacten. Daarna eventuele fix-wave, ledger-afsluiting.

## Scope-notitie

Buiten scope (bewust): crosstrack-conflictoverlay over de grens (spec §8 item 11, apart vervolgplan), nieuwe databronnen, scenario-sweeps, Vlaamse vergunningspraktijk.
