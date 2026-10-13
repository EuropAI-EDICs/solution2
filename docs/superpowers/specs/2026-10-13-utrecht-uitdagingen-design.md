# Ontwerp: Utrecht-PoC herstructureerd naar 5 uitdagingen × 13 tracks × 3 scenario's

**Datum:** 2026-10-13
**Status:** ter review
**Aanpak:** Aanpak A — curation-laag bovenop de bestaande scenario-engine; engine, schema's en pipeline onaangetast.

## 1. Doel

De demo-narratief van de Utrecht-PoC wordt georganiseerd rond **beleidsopgaven
(uitdagingen)** in plaats van alleen rond de drie oorspronkelijke tracks
(wind/zon/bos). Elke track toont exact **3 scenario's** naast de control —
de huidige willekeurige aantallen (wind 6, zon 2, bos 2, overige 0) verdwijnen.

Deelnemende tracks: alle 13. De uitdaging is een **curation- en
presentatie-concept** (zoals de crosstrack-overlay dat al is), geen nieuw
schema- of engine-concept.

## 2. De 5 uitdagingen

| id | titel | tracks |
|---|---|---|
| `energietransitie` | Energietransitie | wind, zon, biomassa, energietoets |
| `wonen-werken` | Wonen & Werken | wonen, werken |
| `water-bodem` | Water & Bodem | water, bodem |
| `landschap-infra` | Landschap & Infrastructuur | landschap, mobiliteit |
| `landelijk-gebied` | Landelijk Gebied & Natuur | bos, landbouw, recreatie |

Totaal: 13 tracks × 3 scenario's = **39 scenario's**, elk vergezeld van de
ongemuteerde control. De crosstrack-overlay (wind×zon×bos, Plane C) blijft
onaangetast en wordt in de demo onder `energietransitie` gemonteerd als
conflictzicht; uitbreiding naar alle paren (78 combinaties) valt buiten scope.

## 3. Curation-principe per track

Elke track kiest 3 scenario's die samen drie verschillende beleidsknoppen
laten zien, gemapt op de drie `basis`-typen van het scenario-contract:

1. **`policy_variant`** — een gedocumenteerde discretionaire keuze omgedraaid
   (juridisch onderbouwd debat: "wat als de provincie anders kiest?").
2. **`norm_variance`** of tweede `policy_variant` — een geciteerde parameter
   gevarieerd, of een afwikkellezing gehandhaafd als harde uitsluiting.
3. **`hypothetical`** — expliciet *niet* juridisch onderbouwd; meet de prijs
   van een geabstaineerd onderwerp (het eerlijke tegenbeeld van de
   abstention-ledger). Waar een track geen natuurlijk hypothetical kent
   (mobiliteit), volgt een derde `policy_variant` die een afwijkende
   afwikkellezing meet.

De drie herhaalde aandachtsgebied-buffer-varianten van wind (500/1500/3000 m)
vervallen: 6 → 3.

## 4. De 39 scenario's (intent-niveau)

Bestaande scenario's waar mogelijk behouden; nieuwe aangeduid. Id's en exacte
mutaties worden tijdens implementatie vastgelegd uit de normcards/formalrules
van de canonieke baseline-run per track (`poc/runs/<ts>-<track>`, zie
`poc/README.md`); de onderstaande intenties zijn bindend, de id's volgen het
bestaande `SC-<X>-…`-patroon.

### 4.1 Energietransitie

**wind** (baseline 20260830T113234Z-wind):
1. *NNN-uitzondering province-wide* (`policy_variant`, bestaat) — +322,5 km²,
   de grootste hefboom van de demo.
2. *Stiltegebied als harde uitsluiting* (`policy_variant`, bestaat) — tot −61%.
3. *500 m-setback rond Natura 2000/ganzenrustgebieden* (`hypothetical`,
   bestaat) — prijs van een geabstaineerde afstandsnorm.

**zon** (baseline 20260830T142439Z-zon):
1. *Groene contour als harde uitsluiting* (`policy_variant`, bestaat).
2. *500 m-buffer rond NNN* (`hypothetical`, bestaat als auto-author-voorstel,
   −52,2%) — komt nu in de demo-set.
3. *Designation zonder Natura/ganzen-carve* (`hypothetical`, bestaat) —
   isoleert de voetprint van de interpretieve carve.

**biomassa** (baseline 20261006T120133Z-biomassa; cards NC-BM-01/02, zone =
landelijk ∪ stedelijk vestigingsgebied):
1. *Beperkt tot stedelijk vestigingsgebied* (`policy_variant`) — landelijk-pad
   dicht: terughoudendheid buiten het stedelijk gebied.
2. *Groene contour als harde uitsluiting* (`policy_variant`) — consistentie
   met het zon-scenario: dezelfde contour claimt ook deze energievorm.
3. *500 m-afstand tot woningen/bebouwing* (`hypothetical`) — geen
   provinciale afstandsnorm (abstention-onderwerp); meet de prijs ervan.

**energietoets** (baseline 20261006T171730Z-energietoets; cards NC-ET-01..03,
all-marker):
1. *Netbelastende functies (art. 5.10) als harde uitsluiting*
   (`policy_variant`) — marker-enforcement: wat als de toets ruimtelijk
   blokkeerde.
2. *Drempel "minder dan 10 woningen" verlaagd naar 0* (`norm_variance`) —
   alle woningbouwlocaties telling mee.
3. *Provinciale netcongestie-zones* (`hypothetical`) — zone uit de
   netbeheerder-congestiekaart (data-gegrond, niet juridisch onderbouwd);
   zie [2026-10-13-utrecht-data-kalibratie-design.md](2026-10-13-utrecht-data-kalibratie-design.md)
   §4 voor de `dataGrounding`-extensie.

### 4.2 Wonen & Werken

**wonen** (baseline 20261005T100258Z-wonen; inclusion-compositie stedelijk ∪
kernrand ∪ uitbreidingsgebieden):
1. *Streng: bouwen alleen binnen bestaand stedelijk gebied* (`policy_variant`)
   — de exception-compositie (kernrand, uitbreidingsgebieden) uit de zone.
2. *Flexwoningen (art. 9.14a) uit de compositie* (`policy_variant`).
3. *1 km-buffer rond stiltegebieden voor woningbouw* (`hypothetical`) —
   art. 9.27 is een marker; de afstand is niet geciteerd.

**werken** (baseline 20261006T121921Z-werken; inclusion uitbreiding-
bedrijventerrein ∪ stedelijk):
1. *Detailhandel-verbod (art. 9.20) ook over bedrijventerreinen geencoreerd*
   (`policy_variant`) — de historische eerste-run-fout (WN-03) als
   verhaalbare variant.
2. *Streng: alleen bestaand stedelijk gebied* (`policy_variant`).
3. *500 m-zone rond NNN voor bedrijventerreinen* (`hypothetical`) — meet de
   natuurdruk van bedrijvigheid; niet geciteerd.

### 4.3 Water & Bodem

**water** (baseline 20261004T185116Z-water):
1. *Overstroombaar gebied (art. 2.16) als harde uitsluiting*
   (`policy_variant`) — −1207 km²; het grote "wat als"-verhaal van de track.
2. *Vrijwaringszone regionale waterkering (art. 2.14) als harde uitsluiting*
   (`policy_variant`) — −28 km².
3. *500 m-buffer rond waterbergingsgebied* (`norm_variance`,
   `set_buffer_distance_m`).

**bodem** (baseline 20261004T185509Z-bodem):
1. *Grondwaterbeschermingszone alleen op de letterlijke designation-gebieden*
   (`policy_variant`) — versoepeling t.o.v. de umbrella-superset: +701 km².
2. *Gesloten stortplaatsen (art. 3.108) als harde uitsluiting*
   (`policy_variant`) — klein (0,373 km²) maar juridisch scherp.
3. *500 m-buffer rond de grondwaterbeschermingszone* (`norm_variance`).

### 4.4 Landschap & Infrastructuur

**landschap** (baseline 20261005T070621Z-landschap):
1. *Cultuurhistorische hoofdstructuur (art. 7.9) als harde uitsluiting*
   (`policy_variant`) — −847 km².
2. *Aardkundige waarden (art. 7.12) als harde uitsluiting* (`policy_variant`)
   — −99 km².
3. *100 m-buffer rond de Limes-kernzone* (`norm_variance`,
   `set_buffer_distance_m`).

**mobiliteit** (baseline 20261005T072839Z-mobiliteit; all-marker):
1. *Geluidcontour (art. 4.71) als harde uitsluiting voor geluidgevoelige
   functies* (`policy_variant`) — −37,3 km².
2. *Beperkingengebied provinciale weg (art. 4.7) als harde uitsluiting*
   (`policy_variant`) — −7 km².
3. *Luchtvaartverbod (art. 4.65) zonder activity-scope* (`policy_variant`) —
   de letter "verbod" geëncoreerd als onvoorwaardelijke uitsluiting
   (−1014 km²); illustreert waarom scoping juridisch uitmaakt.

### 4.5 Landelijk Gebied & Natuur

**bos** (baseline 20260830T142446Z-bos; zone = de Groene contour zelf):
1. *Oude bosgroeiplaatsen (art. 6.13) als harde uitsluiting*
   (`policy_variant`, bestaat).
2. *Zoekgebied beperkt tot 500 m-zone rond NNN* (`policy_variant`) — nieuwe
   natuur uitsluitend aansluitend op het netwerk.
3. *1 km-expansieband rond het zoekgebied* (`hypothetical`, bestaat) —
   16,5× groei.

**landbouw** (baseline 20261005T094244Z-landbouw; final 2,26 km²):
1. *Landbouwstabiliseringsgebied (art. 8.3) niet langer uitsluitend*
   (`policy_variant`) — versoepeling: +246,8 km².
2. *250 m-buffer rond de concentratiegebieden glastuinbouw* (`norm_variance`)
   — kleine uitbreidingsband rond de kassenconcentraties.
3. *Glastuinbouw-verbod (art. 8.6) genegeerd* (`hypothetical`) —
   +1557,8 km² dramatisch tegenbeeld.

**recreatie** (baseline 20261006T114934Z-recreatie; pure inclusion):
1. *Alleen dagrecreatieterreinen (art. 9.22)* (`policy_variant`) —
   recreatiezone (art. 9.23) uit de compositie.
2. *500 m-buffer rond dagrecreatieterreinen* (`norm_variance`).
3. *250 m-zone rond NNN waar recreatie niet mag* (`hypothetical`) —
   nature-first tegenbeeld.

## 5. Architectuur & componenten

```
poc/scenarios/
  uitdagingen.json          # NIEUW: curation-definitie (groepering + metadata)
  wind.json … recreatie.json  # 13 demo-sets, elk exact 3 scenario's (scenario-set-schema)
```

- **`uitdagingen.json`** — puur groepering: per uitdaging `{id, titel,
  beschrijving, tracks[]}` en per track de baseline-run-ref. Geen nieuw
  JSON-schema onder `poc/schemas/`: het bestand is curation-metadata, niet een
  agent-boundary-contract. Validatie gebeurt in tests (zie §7).
- **Demo-sets** — blijven het bestaande `scenario-set`-formaat; `wind.json`,
  `zon.json`, `bos.json` hersneden naar 3; 10 nieuwe sets voor de andere
  tracks. Alle sweep-uitvoering ongewijzigd:
  `python3 poc/scenarios/run.py --use-case <track> --author file`.
- **`deep-agents/scenario_catalog.py`** — `describe_scenario_run` krijgt een
  `uitdaging`-veld (via de mapping uit `uitdagingen.json`); `_FEATURED_SUFFIXES`
  wijzigt naar de 13 nieuwe uitdaging-runs; sortKey groepeert op uitdaging.
  Oude runs (authorcmp, fixtures) vallen onder "overig".
- **`deep-agents/dashboard.html` + `live_server.py`** — de scenario-picker
  toont de 13 runs gegroepeerd in 5 optgroups per uitdaging; crosstrack-hint
  bij `energietransitie`.
- **`deep-agents/prompts/poc/utrecht.md` + `poc_demos.py`** — één nieuwe
  prompt-modus "Uitdaging-overzicht": toont de 5 uitdagingen, hun tracks en
  per track de 3 scenario's + headline-delta's uit de scenario-report.
- **`poc/README.md`** — tabel met de 5 uitdagingen en de 39 scenario's,
  vervangt de losse "headline findings"-opsomming.

## 6. Dataflow

1. Curation: sets + `uitdagingen.json` schrijven (id's gevalideerd tegen de
   normcards van de betreffende canonieke run).
2. Executie: 13 sweeps (`--author file`), elk reproduceert de control (V3,
   ≤0,1% rel) en executeert 3 mutaties → 13 nieuwe `poc/scenario-runs/<ts>-<track>-scen/`.
3. Demo: dashboard groepeert; world-scene-builds blijven on-demand per
   scenario-run (utrecht-world-scene recipe), ongewijzigd.

Foutgedrag ongewijzigd: mutation die niet resolvend is tegen de baseline
belandt in `mutations skipped` + critic-verdict; scenario's die niet
reproduceren (`control` drift) blokkeren de run (exit ≠ 0) — geen nieuwe
gedragsregels nodig.

## 7. Tests

- **Nieuwe pytest (`poc/tests/test_uitdagingen.py`):** (a) `uitdagingen.json`
  definieert precies 5 uitdagingen die samen exact de 13 tracks dekken;
  (b) elke demo-set is schema-valid en telt exact 3 scenario's; (c) elke
  `normCardId`/`ruleId` resolvend is t.o.v. de baseline-run-artifacts;
  (d) de basis-verdeling per track volgt §3; (e) scenario_catalog geeft per
  nieuwe run een uitdaging-groep.
- **Bestaande suite (303 tests) blijft groen**; geen pipeline- of
  formalizer-wijzigingen, dus geen golden-drift.
- **Acceptatie:** alle 13 sweeps sluiten af met verdict `pass`; dashboard
  toont 5 groepen × runs.

## 8. Out of scope

- Geen wijzigingen aan engine (`pipeline/engine.py`), Norm Analyst,
  crosstrack-algoritme of LLM-seams. Het scenario-contract-schema wijzigt
  uitsluitend met de optionele `basis.dataGrounding`-extensie uit
  [2026-10-13-utrecht-data-kalibratie-design.md](2026-10-13-utrecht-data-kalibratie-design.md)
  (§4); verder geen schema-wijzigingen.
- Geen uitbreiding van crosstrack naar meer track-paren.
- Geen eerste-class "uitdaging"-concept in `poc/schemas/` of de deep-agents
  recipes — dat is Aanpak B en wordt pas overwogen als de demo hier om vraagt.
- H3-overlays en Urban Strategy-schermen blijven werken zoals ze zijn (per
  sweep, automatisch mee).
