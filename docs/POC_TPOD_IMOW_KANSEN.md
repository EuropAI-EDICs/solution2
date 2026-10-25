# STOP/TPOD/IMOW-kansen voor de RegelRecht-track: van Geonovum-standaard naar gemeten naad

| | |
|---|---|
| **Voor wie** | Ontwikkelaars en architecten van de LDT-toolbox; aansluiting op de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) |
| **Datum** | 20 oktober 2026 |
| **Aanleiding** | Geonovum-hub [STOP/TPOD](https://www.geonovum.nl/omgevingswet/STOPTPOD) en [IMOW 3.0.1](https://docs.geostandaarden.nl/ow/def-im-imow-20231227/) (§ 2, [informatiemodel](https://docs.geostandaarden.nl/ow/def-im-imow-20231227/#x2-320F8A13)) |
| **Code** | `nldt/simulation/regelrecht/tpod/` (module + CLI + `tpod-index/v1`-schema), tests `nldt/tests/test_simulation_tpod.py` |

---

## De kern in één alinea

De Eindhoven-PoC ([`poc-bp2op/`](../poc-bp2op/)) parseert officiële publicaties (CVDR/Gemeenteblad-HTML) omdat de DSO-API's key-gated zijn; de overlap-track (`dso_overlap/`) bevraagt ondertussen wél de DSO Presenteren-API. Dat Presenteren-antwoord ís de STOP/TPOD/IMOW-annotatielaag: regelteksten verankerd via wId, juridische regels met locatie- en activiteitverwijzingen, gebiedsaanwijzingen en locaties met GIO-geometrieverwijzing. Deze pagina vult vier kansen van die laag concreet in en levert er drie deels of geheel **als code**, gebouwd op de bestaande offline-cache: (1) **geo-feiten** voor de `werkingsgebiedRef`-placeholder, (2) **pons** als expliciet contract, (3) **wId-anchoring** per artikel+lid, en (4) de **activiteitstructuur/gebiedsaanwijzingen** als officiële coverage-taal. Alles meetbaar, herhaalbaar en zonder iets te verzinnen: wat de standaard niet levert, staat er expliciet als `beschikbaar: false`.

## De kansenkaart

| # | kans | IMOW-objecten | PoC-naad | status |
|---|---|---|---|---|
| 1 | werkingsgebieden als geo-feiten | Locatie (Gebiedengroep e.a.), GeometrieRef, Regelingsgebied | `werkingsgebiedRef` (MC-11), `in_werkingsgebied`-input in de RegelRecht-export | **geleverd** (feiten-index, GIO-bestanden, punt-toets) |
| 2 | pons — waar het tijdelijk deel nog geldt | Pons (alleen omgevingsplan) | bronpopulatie hfd 22/23, TAM-track | **beantwoord**: OW-aanlevering geïnspecteerd — géén pons-objecten |
| 3 | wId-anchoring van artikelen | Regeltekst (OP-object, wId), Juridische regel → regeltekstRef | regex-join in `dso_overlap/overlap.py`, V2-grounding | **geleverd** (punt + hele-instrument documentstructuur) |
| 4 | activiteitstructuur & gebiedsaanwijzingen | Activiteit (functionele structuur), Gebiedsaanwijzing | thema-clusters in `coverage.json`, `needsNewRules` | **geleverd** (side-by-side, geen verzonnen mapping) |

## Kans 1 — Werkingsgebieden: de placeholder krijgt een adres

**Wat de standaard zegt.** Een omgevingsplan koppelt juridische regels via Locaties (Gebied, Lijn, Punt en groepen) aan de kaart; het Regelingsgebied is de locatie van het hele document. Locaties verwijzen via `GeometrieIdentificatie` naar GML-geometrie in de GIO-aanlevering. De TPOD-onderdelen *Werkwijze geo en locaties*, het BOPA gml-template en de QGIS-plugin *DSO GIO* beschrijven dat pad.

**De naad.** De Eindhoven-PoC houdt werkingsgebieden bewust als placeholder vast (`werkingsgebiedRef`, methodkaart MC-11) en de RegelRecht-export declareert `in_werkingsgebied` als externe input ("buiten wet-YAML; werkingsgebiedRef / zone-engine"). Wat er nooit stond: *welke* locaties er bij een punt horen, onder hun officiële identificatie.

**Gemeten** (Woensel-proxy / Domplein, PRE v8, cache 19-10-2026): de hit bevat **35** (Eindhoven) resp. **11** (Utrecht) locaties, **alle met `geometrieIdentificatie`** — het adres van de GIO-geometrie. `geselecteerdeLocatieRefs` geeft er 4 resp. 9: dat zijn *door de DSO geleverde punt-in-gebied-feiten*. In Eindhoven dragen **41 artikelen** specifieke locatieRefs (buiten het ambtsgebied) — dat is de gebiedsgebonden subset waar de zone-vraag echt speelt. De `geoFeiten`-sectie van de index exporteert dit als feitenlijst (identificatie, type, noemer, geometrieref, `geselecteerdOpPunt`).

**Volgende stap.** GIO-geometrie ophalen via de *Omgevingsdocumenten downloaden*-API of via open-dataset-aliassen zoals PoC-1 die al gebruikt (agrest IMOW-laag), en daarmee de zone-engine van PoC-1 als oplosser van `in_werkingsgebied` koppelen. Voor de fixture-punten geldt de gecachte selectie als orakel.

**Update 20-10-2026: het geometrie-adres is binnen — en kruisgevalideerd.** Met de sleutels (nu in een gitignored `.env`, geladen door `dso_overlap/client.py`) zijn de OW-uitwisselpakketten opgehaald via de asynchrone downloaden-API (aanvraag → status → download; 14,3 MB voor Eindhoven, 56,8 MB voor Utrecht). Eindhoven bevat **151 GIO-GML's** waarvan de bestandsnaam de IMOW-locatie-identificatie is (LVBB-conventie); de `geoFeiten`-locaties dragen daardoor hun `gmlBestand` (34 van de 35 — de 35e is het ambtsgebied, dat terecht uit de bestuurlijke-grenzen-voorziening komt en niet in de aanlevering zit).

Met `--geo` (`tpod/geo.py`, shapely) is de volgende stap ook gezet: **punt-in-polygoon** op de echte geometrie, EPSG:28992, vergeleken met de DSO-puntselectie. Resultaat Woensel-proxy: **34 van de 34 toetsbare locaties in overeenstemming, 0 conflicten** — de Presenteren-annotatie is kruisgevalideerd tegen de aanlevering.

**Update 21-10-2026: de zonevraag is nu ook voor Utrecht registratie-onafhankelijk gesloten.** De parser begrijpt nu ook het Utrechtse GML-patroon (`gml:Surface/gml:patches/gml:PolygonPatch`): 119 van 119 GIO's ontleedbaar. De **sweep** (alle GIO's tegen het punt, zonder registratie-koppeling) vindt er 8 die het Domplein bevatten, en de **naam-afstemming** (genormaliseerde vergelijking: 'Klein open bodemenergiesysteem' ↔ `locaties_Kleinopenbodemenergiesysteem-v1`) matcht die 8 **naam-op-naam met de 8 gebiedsaanwijzingen in de hit — 8 van 8**. Beide instrumenten zijn daarmee op twee onafhankelijke manieren bevestigd: Eindhoven via bestandsnaam-koppeling (34/34), Utrecht via geometrie-sweep + naam-afstemming (8/8).

### 1a. De cirkel is dicht: de punt-toets (`--toets`)

De geo-feiten zijn niet alleen geïndexeerd maar ook **geëxecuteerd**: `python -m nldt.simulation.regelrecht.tpod --toets` runt de deterministische reference-engine over alle formalized artikelen uit de DSO-hit, met elke `execution.input` opgelost als **feit** (`in_werkingsgebied` via hit-lidmaatschap; `in_…`-zonevelden uniek gematcht op gebiedsaanwijzing-namen — geen match = `false`, gemarkeerd als *afwezig in hit*), **scenario** (voorstelafhankelijke booleans: strijd met tijdelijk deel, verbodsaard, IWT-voorschriften — alle polariteitscombinaties, gelabeld) of **onthouding** (numerieke activiteitparameters; MC-6). Resultaat per instrument (`<stem>.toets.json`, contract `punt-toets/v1`, cache 19-10-2026):

| instrument | formalized in hit | getoetst (feit) | scenario | onthouding | engine-fout |
|---|---|---|---|---|---|
| Omgevingsverordening Utrecht (Domplein) | 7 | **7** | 0 | 0 | 0 |
| Omgevingsplan Eindhoven (Woensel) | 457 | 0 | **434** | 23 | 0 |

Utrecht laat zien wat laag 2 op een echt punt doet: art. 9.17/9.18 `True` (Stedelijk gebied — de gebiedsaanwijzing zit in de hit), art. 5.7 `True` (energie uit biomassa stedelijk gebied), art. 9.19 `False` (kantoor-knooppunt Utrecht Centraal wél, maar de AND met de afwezige zones maakt het resultaat `False`), art. 6.13/8.5/9.2 `False` op afwezigheid. Eindhoven is een ander verhaal — en dat is de bevinding: de formalized subset daar is het **equivalentie-orakel** uit integratiefase 2, dus voorstelafhankelijk: 414 artikelen als strijd-scenario (2 polariteiten), 19 verbod-artikelen (2 polariteiten), art. 10.2 met twee scenariovelden (4 combinaties), en 23 eerlijke onthoudingen voor numerieke limieten (`limiet_m`/`bouwhoogte_m` vragen de gemeten waarde van het voorstel).

**Wat de toets opleverde: twee latente template-defecten.** De toets blootlegde dat in de exports `$`-verwijzingen bestonden naar variabelen die nergens als `input` waren gedeclareerd — de engine lost `$`-refs uitsluitend uit input op, dus die paden konden nooit runnen: (1) de smoke-fixture voor art. 10.2 declareerde `voorschriften_verbonden_voor_iwt` als *parameter* in plaats van input; (2) de verbod-/limiet-templates declareerden `activiteit_valt_onder_verbod` resp. de numerieke limiet ook alleen als parameter. Beide gefixt op de bron (`docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml`, `eindhoven_templates.py`) en alle exports/demo/smoke-runs herbouwd (aantallen onveranderd: 567/60 formalized, golden 56). Zonder de punt-toets waren deze paden pas bij de eerste echte executie opgevallen.

**Update 21-10-2026: van scenario's naar een echt voorstel.** Met `--voorstel <fixture>` (contract `voorstel/v1`) worden de scenario-velden én numerieke activiteitparameters ingevuld vanuit een expliciet, gelabeld voorstel; elke uitkomst blijft herleidbaar (bron `voorstel` per input). Het bouwhoogte-scenario uit de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) (vraag 3) draait daarmee end-to-end — fixture [`tpod/fixtures/voorstel-eindhoven-bouwhoogte.json`](../nldt/simulation/regelrecht/tpod/fixtures/voorstel-eindhoven-bouwhoogte.json): "nieuwbouw 12 m, geen verbodsactiviteit, geen IWT-voorschriften, geen strijd met tijdelijk deel":

| | Eindhoven met voorstel | Eindhoven zonder voorstel | Utrecht |
|---|---|---|---|
| getoetst | **457 / 457** | 0 | 7 / 7 |
| scenario | 0 | 434 | 0 |
| onthouding | 0 | 23 | 0 |
| uitkomst | **447 waar / 10 onwaar** | — | — |

De 10 afgewezen artikelen zijn precies de limiet-artikelen met een grens onder de voorgestelde 12 m (art. 1.8, 5.21, 5.81, 5.97, 6.7, 6.45, 6.47, 6.55, 6.56, 22.140) — mechanisch verifieerbaar, met de volledige engine-trace als bewijs.

**Update 21-10-2026: de verkenruimte van laag 3, deterministisch.** Met `--sweep` doorloopt de toets de `"variaties"` uit de voorstel-fixture (8 bouwhoogte-stappen, 4→20 m) en bouwt kantelpunten (`<stem>.voorstel-sweep.json`, contract `voorstel-sweep/v1`): de ladder loopt van 450 waar (4 m) naar 446 waar (20 m), en **4 artikelen kantelen** in het bereik — art. 22.140, 5.81, 6.44 en 6.7 (de limieten die tussen 4 en 20 m vallen). Dit is de mechanische onderlaag van "AI verkent" (notitie-laag 3): welke varianten zijn het proberen waard en welke regels zijn gevoelig — deterministisch, gelabeld als verkenning, geen besluit (MC-6).

## Kans 2 — Pons: de machine-leesbare bruidschatgrens

**Wat de standaard zegt.** Pons is een OW-object dat alleen in omgevingsplannen voorkomt en aangeeft waar oude (bouwvlak-)plannen niet meer getoond/geldig zijn — precies de grens van het *tijdelijk deel* waar de PoC zijn 311 bronregels vandaan trekt.

**Beantwoord (20-10-2026): Eindhoven heeft géén pons.** Het volledige OW-uitwisselpakket van het omgevingsplan (downloaden-API, 937 bestanden, 10 OW-bestanden) is geïnspecteerd met de pons-parser (`tpod/pakket.py`): **geen enkel Pons-object** in de aanlevering. De index rapporteert dat nu niet als "onbekend" maar als gecontroleerde afwezigheid (`"pons": {"beschikbaar": false, "aantal": 0, "opmerking": "geen Pons-objecten in de aanlevering"}`). Eindhoven markeert de overgangszones in plaats daarvan met de gebiedsaanwijzing **"ruimtelijke regels tijdelijk deel nog in werking"** (op 16 artikelen, waarvan 15 in de doelregeling: hfd 3: 5×, hfd 5: 5×, hfd 1: 2×, hfd 6: 2×, hfd 10: 1×, hfd 22: 1×). Voor de PoC betekent dat: de gebiedsaanwijzing ís de bruidschatgrens — de coverage-analyse (MC-8) kan die lezen als "doelartikel nog niet zelfstandig"; een pons-lezer is voor Eindhoven niet nodig, wel voor gemeenten die het object wél gebruiken.

**Volgende stap (vervangen).** Niet meer: pons ophalen. Wel: de gebiedsaanwijzing-grenzen in de coverage-analyse en (voor andere gemeenten) een pons-parser blijft beschikbaar in `tpod/pakket.py`.

## Kans 3 — wId-anchoring: het joinpunt wordt officieel

**Wat de standaard zegt.** Elke Regeltekst (OP-object) is verankerd aan de STOP-tekst via het **wId** van een tekstdeel; juridische regels verwijzen via `regeltekstRef` naar hun tekst. Artikel- en lid-granulariteit zit dus in de annotatie zelf.

**De naad.** `dso_overlap/overlap.py` joinde tot nu toe op een regex over wIds (`__art_([\d.]+)`) — artikelniveau, lids kwijt. De tpod-index ontledet het hele wId-pad (hoofdstuk → afdeling → paragraaf → artikel → lid) en groepeert de regels per artikel.

**Gemeten.** Eindhoven: **1.407 regelteksten over 811 artikelen** (942 met lid, 465 zonder), **1.407 regels voor iedereen**, waarvan 1.004 met activiteitverwijzing. Utrecht: 218 regelteksten over 107 artikelen (119 rvi + 99 instructieregels). Kruisvalidatie: `formalizedInHit` komt exact overeen met de overlap-rapporten (Eindhoven 457, Utrecht 7). Tegen de PoC-artikelenpopulatie zit 744/1.074 (Eindhoven) resp. 105/427 (Utrecht) in de punt-hit — de scope van wat op deze locaties geannoteerd is, met `bron.presentatieScope` als waarschuwing dat de hele instrument-populatie hier níét in zit.

**Volgende stap.** Het `documentstructuur`-endpoint (link staat in elk cached antwoord) levert de wId-boom van het hele instrument; daarmee kan de anchoring los van het bevraagde punt worden uitgerold en kan V2-grounding (verbatim-tekst) op wId gecontroleerd worden in plaats van op HTML-tokenisatie.

**Update 20-10-2026: uitgerold.** De documentstructuur is gefetcht en gecached voor beide instrumenten en zit als `documentstructuur`-sectie in de index: Eindhoven **1.117 artikelen / 1.176 leden / 24 hoofdstukken** (boomdiepte 7), Utrecht **400 artikelen / 561 leden / 10 hoofdstukken**. Dat is de hele-instrument-populatie, los van het punt — de anchoring en een eventuele wId-gebaseerde V2-controle kunnen nu over het hele document draaien. De delta t.o.v. de PoC-parsing (1.074 resp. 427 artikelen) is zelf informatief: de documentstructuur telt bijlage-artikelen en begripsbepalingen mee die de PoC-parser anders afkapt.

## Kans 4 — Activiteitstructuur en gebiedsaanwijzingen als officiële coverage-taal

**Wat de standaard zegt.** Activiteiten vormen een functionele structuur: één tophaak ("Activiteit gereguleerd in …"), daaronder de instrumentactiviteiten met `bovenliggendeActiviteitRef` en een groep uit de waardelijst (milieubelastende activiteit, bouwactiviteit, …). Gebiedsaanwijzingen duiden gebieden met type+groep.

**Gemeten.** Eindhoven: **98 activiteiten, 13 groepen** (52 milieubelastende activiteiten, 25 bouwactiviteiten, …), boomdiepte 5, en als enige root de **landelijke tophaak** (`nl.imow-mnre1034.activiteit.ActiviteitGevolgenFysiekeLeefomg`) — de lokale toppen ("… gereguleerd in het omgevingsplan", 9 stuks) hangen er als kind onder. Utrecht: 10 activiteiten, 7 groepen, 2 toppen. De PoC-thema's van de bronregels (`gebruik:overig` 153×, `milieu:bodemsanering` 46×, …) staan bewust *naast* deze groepen in het document, niet op ze gemapt: beide kanten hebben officiële concept-IRI's, dus een mapping kan — maar dan verifieerbaar tegen de waardelijsten, niet ad hoc.

**Volgende stap.** Themavocabulaire en IMOW-groepen koppelen via de concept-IRI's uit de Stelselcatalogus-waardelijsten; daarna kan `needsNewRules` (bijv. cluster `gebruik:overig`, 9 regels) tegen de officiële activiteitstructuur worden gelegd.

## Bedienen

```bash
# eenmalig: sleutels in .env (gitignored; client.py laadt die automatisch)
#   DSO_API_KEY=…   RP_API_KEY=…

# caches verversen (Presenteren + RP + documentstructuur; --pakket = OW-uitwisselpakket):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.dso_overlap.compare --instruments eindhoven,utrecht --pakket

# index + punt-toets + geo-validatie bouwen (offline, op de cache):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod --instruments eindhoven,utrecht --toets --geo

# … met een concreet voorstel (scenario-velden + numerieke parameters ingevuld, gelabeld):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod --instruments eindhoven --toets --geo \
  --voorstel nldt/simulation/regelrecht/tpod/fixtures/voorstel-eindhoven-bouwhoogte.json

# … plus variant-sweep over de 'variaties' uit de fixture (kantelpunten):
nldt/.venv/bin/python -m nldt.simulation.regelrecht.tpod --instruments eindhoven --toets --geo --sweep \
  --voorstel nldt/simulation/regelrecht/tpod/fixtures/voorstel-eindhoven-bouwhoogte.json

# alles landen in de data lake (bronze pakket / silver caches+indices / gold runs):
NLDT_LAKE_BACKEND=s3 NLDT_LAKE_ENDPOINT=http://localhost:9000 \
  nldt/.venv/bin/python nldt/scripts/lake_sync.py --poc eindhoven --poc utrecht
```

Artefacten: `nldt/simulation/regelrecht/dso_overlap/out/<instrument>__<locatie>.tpod-index.json`, `….toets.json`, `….pakket-index.json` (pons + GIO's) en `….geo-validatie.json` (punt-in-polygoon), schema-valid tegen `tpod-index/v1`, `punt-toets/v1` respectievelijk `geo-validatie/v1` (een contractbreuk breekt de bouw met een duidelijke fout). In de lake: `bronze/<poc>/dso-uitwisselpakket` (zip as-received), `silver/<poc>/dso-presenteren` (caches, indices, toetsen, geo-validaties), `silver/<poc>/regelrecht-export` (instrument-YAML/report/artikelen), `gold/<poc>/regelrecht-runs`. Provenance zit in elk artefact zelf: sha256 van alle inputs onder `inputs`. Tests: `nldt/.venv/bin/python -m unittest nldt.tests.test_simulation_tpod` (offline op synthetische payloads — de cache zelf is gitignored).

## Eerlijke grenzen

- **PRE, niet prod**: de caches komen uit de pre-productie-API; 1:1-vergelijking met het publieke loket vraagt een productiesleutel (zelfde beheersmaatregel als in de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md)).
- **Punt-scope van de annotaties**: de regelteksten/regels in de index gelden voor de bevraagde geometrie; het hele instrument is gedekt door de documentstructuur (wId-boom) en het OW-uitwisselpakket, maar de *annotatie*-profilering blijft puntgebonden.
- **Pons is beantwoord, niet aanwezig**: Eindhovens pakket geïnspecteerd, nul Pons-objecten; de gebiedsaanwijzing "tijdelijk deel nog in werking" is daar het functionele equivalent.
- **Geometrie**: beide instrumenten tweevoudig bevestigd — Eindhoven via bestandsnaam-koppeling (34/34 punt-getoetst), Utrecht via geometrie-sweep + naam-afstemming (8/8). Wat nog open ligt: de Utrechtse *artikel*-niveau GIO-koppeling (welke regel hangt aan welke GIO). Presenteren biedt geen GIO-endpoint; het besluitzijdige pad (`/besluitversies`, met locatieSelectie) bestaat maar levert de regel→GIO-binding niet zonder meer — blijft een open uitwerkpunt.
- **Laag 3 is hier mechanisch**: de sweep verkent het parameter-bereik deterministisch; echte AI-verkenning (ontwerpvarianten, ruimte/tijd) komt daarbovenop.
- **Geen thema-mapping** zonder waardelijst-concepten (kans 4): side-by-side pas, verzonnen gelijkheid nooit.

## Verwijzingen

- Geonovum TPOD-hub: <https://www.geonovum.nl/omgevingswet/STOPTPOD> — profielen, schema's, waardelijsten, validatiematrix, Presentatiemodel, QGIS-plugin DSO GIO, BOPA gml-template
- IMOW 3.0.1 (27-12-2023): <https://docs.geostandaarden.nl/ow/def-im-imow-20231227/> — § 2 informatiemodel, OP–OW-scharnier (Regeltekst, Divisie, Geometrie)
- TPOD-schema's en zips: <https://geonovum.github.io/TPOD/>; waardelijsten in de Stelselcatalogus
- Technische zusterpagina's: [POC_RULE_GRAPH_EINDHOVEN.md](POC_RULE_GRAPH_EINDHOVEN.md), [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md), [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md)
