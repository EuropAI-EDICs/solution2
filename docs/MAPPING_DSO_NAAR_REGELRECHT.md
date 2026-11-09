# Mapping DSO-architectuur → RegelRecht-architectuur (+ migratiestappenplan)

| | |
|---|---|
| **Voor wie** | Architecten en ontwikkelaars van de LDT-toolbox; bevoegde gezagen die over executie van regelgeving nadenken; bestuurlijke gedelegeerden van de [bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) |
| **Datum** | 8 november 2026 |
| **DSO-bronnen** | [iplo.nl architectuurdocumenten](https://iplo.nl/digitaal-stelsel/documenten/architectuurdocumenten/): OGAS 2.0.1 (26-03-2020), GAS Toepasbare Regels 2.0.1, GAS LVBB, Bijlage E Bouwblokken, Stelselafspraken v2.5 |
| **RegelRecht-bronnen** | [docs.regelrecht.rijks.app](https://docs.regelrecht.rijks.app) + [NederlandseDigitaleDienst/regelrecht](https://github.com/NederlandseDigitaleDienst/regelrecht) (NDD; schema v0.8.11, vastgepind in `nldt/simulation/regelrecht/schema/`) |
| **Repo-basis** | [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md) · [POC_STTR_IMTR_KANSEN.md](POC_STTR_IMTR_KANSEN.md) · [POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md) · [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) |

---

## De kern in één alinea

DSO en RegelRecht zijn géén concurrenten maar elkaars spiegelbeeld: **DSO is een publicatie- en annotatiestelsel** ("welke regels horen bij deze plek?", vragenbomen per activiteit in het Omgevingsloket) en **RegelRecht is een executiestelsel** ("wat volgt uit deze regels voor dit voorstel?", deterministisch, per artikel, met uitlegbare trace). De mapping hieronder legt vast wat één-op-één aansluit (metingen: 100% van de executie-constructies is first-class DMN), wat een brug nodig heeft (identificatie, geo, granulariteit) en wat bewust niet mapt. Het migratiestappenplan is de doctrine **DSO annoteert · RegelRecht toetst · STTR toepast** als routekaart: niet vervangen, maar de executielaag verhuizen — per fase, met bestaande bouwstenen en klaar-criteria.

## Deel A — Architectuurmapping

### A.1 De twee architecturen op hoofdlijnen

**DSO** (OGAS 2.0.1): stelsel van samenwerkende voorzieningen rond de DSO-LV (Kadaster). Interne componenten: Knooppunt (uitwisseling + IAM), Portalen, Gebruikerstoepassingen (Viewer Regels & Kaart, Checken, Opstellen, Indienen), Stelselcatalogus, **Toepasbare Regels (RTR + Regeluitvoering)**, Ozon (objectgerichte ontsluiting), Aansluitpunt Informatieproducten, Samenwerkfunctionaliteit. Extern: LVBB (bekendmaken + consolideren, STOP/TPOD), informatiesystemen van bevoegde gezagen, Open Stelsel voor Derden, LvO's, GDI-bouwstenen. Drie formele koppelvlakken (Digikoppeling/ebMS): **STOP** (juridische regels), **STTR** (toepasbare regels, DMN+), **STAM** (verzoeken).

**RegelRecht** (NDD): wet- en regelgeving als gestructureerde YAML per versie in een **corpus** (~22.000 bestanden, git), vastgelegd in een **versioned JSON Schema** (v0.8.11: metadata + `articles[]` met `number`/`text`/`url` en optioneel `machine_readable`: `competent_authority`, `execution` met inputs/outputs/actions); een deterministische **Rust-engine** (ook WASM) met uitlegbare trail (`trace/v1`); gedragsconformiteit via **Gherkin/BDD**; een **harvester** (BWB), **editor** (draft-conversions: LLM-voorstellen, menselijke PR-goedkeuring), **wettengraaf** (relatie-analyse), **simulatieomgeving** en **publicatieplatform**.

### A.2 Componentmapping

| DSO-component (OGAS) | RegelRecht-equivalent | Naad / opmerking |
|---|---|---|
| **Toepasbare Regels — Regeluitvoering** (AC05-I: rule-engine, "bepalen conclusie") | **Rust-engine** (packages/engine, WASM) + `trace/v1` | Sterkste overlap. DSO voert vragenbomen per *activiteit* uit; RegelRecht executie per *artikel* met volledige uitlegbaarheid. Kan de onafhankelijke tweede executor (Critic V3) zijn |
| **Toepasbare Regels — RTR** (AC05-I: registratie/validatie/publicatie STTR-bestanden, werkzaamheden, activiteiten) | **Corpus** (git) + schema-versies + PR-review | Registratie wordt versiebeheer. Gat: activiteitenstructuur/werkzaamheden (functionele structuur) heeft geen RegelRecht-equivalent |
| **Bronhouderskoppelvlak STTR** (Digikoppeling, DMN 1.1/1.2) | **draft-conversions**: LLM-conversie + menselijke PR | Aanleveren wordt forken. Constructief 1-op-1 bewezen (crosswalk A.3, 567-testcase); semantische vertaling (boolean toets ↔ conclusie-enum) is een juridische beslissing |
| **LVBB** (extern: STOP/TPOD, juridische consolidatie, officiële bekendmaking) | **Harvester** (BWB) + één YAML per versie (`ingangsdatum`-conventie); consolidatie = git-geschiedenis | Gat: harvester kent alleen BWB — géén CVDR/loket lokale regelgeving (upstream-issue 4). Lokaal instrument alleen via `url` herleidbaar (upstream-issue 1: `cvdr_id` vervallen sinds v0.7.1) |
| **Ozon** (AC06-I: objectvorming, IMOW-objecten, wId's, landelijke objectstructuur) | geen equivalent | RegelRecht kent geen objectgerichte laag. Onze wId-anchoring (TPOD-index) is de brug aan toolbox-zijde |
| **Viewer Regels en Kaart** (AC03a-I) | **Wettengraaf** (tekstueel) — géén kaart | Geo is in RegelRecht een extern feit (input zonder `source.regulation`), geen component. Toolbox levert de zone-engine/GIO-kant |
| **Checken** (AC03b-I: vragenbomen rechten/plichten) | **Engine + simulatieomgeving** (wat-als) | Zelfde vraag, andere vorm: DSO vraagt interactief (interactieregels), RegelRecht neemt feiten in en rekent door. Geen UI-vragenboom |
| **Opstellen + Indienen** (AC03c/d-I) + **STAM**-koppelvlak | geen equivalent | Verzoekketen zit niet in RegelRechts scope; blijft bij DSO |
| **Stelselcatalogus** (AC04-I: begrippen, waardelijsten, DCAT-AP-NL) | schema + wettekst zelf (begrippen als tekst) | Gat: geen begrippenkader/waardenlijst-register. Enum-types in het schema zijn de enige domeinwaarden |
| **Aansluitpunt Informatieproducten** (AC07-I: LvO's, API-profiel "voorinvullen") | `input[].source` — feiten "resolved outside the YAML" | Zelfde patron (externe feiten), andere governance: geen aansluitvoorwaarden/API-profielen. Geo-feittype is upstream-issue 3 |
| **Knooppunt** (AC01: uitwisseling + IAM) | GitHub/git + eigen API's (editor-api, publicatieplatform) | Centraal knooppunt vervalt grotendeels bij git-gebaseerde distributie |
| **Portalen** (AC02-I: omgevingswet-, beheer-, ontwikkelaars-, samenwerkportaal) | docs-site, editor (SSO/Keycloak), GitHub als ontwikkelaarsportaal | Geen burgerportaal: RegelRecht is (nog) geen loket |
| **Samenwerkfunctionaliteit** (AC08-I) | PR-review (mens-op-de-knop, MC-6) | Samenwerking = git-workflow, geen dossierfunctie |
| **Open Stelsel voor Derden** | open corpus + open-source (EUPL-1.2) | Derden kunnen zelfs sterker: eigen executor draaien (WASM) |
| Keten van Plan tot Publicatie | **frontend-lawmaking** + editor + harvester | Wetgevingsproces-visualisatie dekt de vóór-kant |
| *(geen DSO-equivalent)* — **System-1 triage (Laya)** | fine-tuned hints met confidence-gate: `laya_formalizer` (formalisatie-poortwachter per artikel), `laya_router` (verzoek-routing), `laya_bp2op` (conversie-triage) | Nieuwe laag **tussen** annotatie en executie: "AI verkent/trieert" uit de doctrine, nooit in de beslislijn — zie [PLAN_LAYA_INZET.md](PLAN_LAYA_INZET.md) |

### A.3 Informatiemodel-crosswalk (STTR/DMN ↔ RegelRecht-executie)

Bewezen met de [567-testcase](research/sttr-imtr/eindhoven-567-dmn-scan.json) (Eindhovense full export): **100% van de constructieblokken is first-class DMN** — 37 FEEL-`<=`-cellen, 594 booleaanse cellen, 63 geo-inputs, geen enkele operator die STTR 3.0.1 niet kan dragen.

| RegelRecht (schema v0.8.11) | DSO (STTR 3.0.1 / IMTR / IMOW) | opmerking |
|---|---|---|
| `articles[].{number, text, url}` | STOP/TPOD-regelingtekst, AKN-workidentifier (wId) | letterlijk citaat + dieptelink in beide; `cvdr_id`-hiaat (upstream-issue 1) |
| `execution.input[]` (name/type/description) | `uitv:uitvoeringsregel` (vraagTekst, gegevensType) + `dmn:inputData` | boolean→boolean, number→number |
| geo-input (bijv. `in_werkingsgebied`) | `uitv:geoVerwijzing/uitv:locatie @identificatie` (IMOW-locatie/GIO) | Eindhovense RTR-bestanden gebruiken géén `geoVerwijzing` (0/162) — importer mag geo niet aannemen |
| `AND` | conjunctie binnen één `dmn:rule` | hit policy ANY |
| `LESS_THAN_OR_EQUAL` / `EQUALS` | FEEL-cel `<= v` / `true`/`false`/`"optie"` | ook ranges `(a..b)` |
| `IF cases/when/then/default` | meerdere `dmn:rule`-rijen; `default` = rest-rij | |
| `output` boolean (`TOETS`) per **artikel** | Conclusie-enum (`Vergunningplicht`…`NietVanToepassing`) per **activiteit** | de vertaling is een juridische beslissing, géén automatiek |
| artikel + `url` (CVDR/AKN-anker) | `annotationEntry` / `knowledgeSource` | zit in de standaard; ontbreekt in de Eindhovense PRE-bestanden (0/162) |
| `competent_authority` | OIN-namespace + `bedr:functioneleStructuurRef` | granulariteitsverschil: activiteit vs. artikel |
| versie-per-YAML (`ingangsdatum`) | consolidatie + `datumVanaf` (RTR-tijdreis) | beide ondersteunen tijdsreizen |
| Gherkin-scenario's (`bdd/`) | STTR-verificatiematrix / voorbeeldbestanden | DecisionTable-rijen lenen zich als scenario-bron |

### A.4 Wat bewust níet mapt

- **Geen vervanging van het loket**: DSO blijft verantwoordelijk voor officiële bekendmaking (LVBB), de verzoekketen (STAM) en de vragenboom-conclusie per activiteit; RegelRecht is de toetslaag ernaast.
- **Boolean vs. enum, artikel vs. activiteit**: constructies mappen 1-op-1, semantiek niet (zie A.3).
- **Onthouding**: DSO-STTR's zijn compleet modelleerbaar per definitie; RegelRecht kent cite-or-abstain ("an article without `machine_readable` is carried as text only") — open normen worden nooit verzonnen executie.
- **Productie vs. PRE**: RTR-metingen draaiden op pre-productie (401 op prod met PRE-key); productievergelijking is een aparte stap.

## Deel B — Migratiestappenplan

Leidraad: de executielaag verhuizen van DSO-vragenbomen naar RegelRecht-executie **zonder de DSO-annotatie- en publicatiefunctie te breken**. Elke fase levert zelfstandig waarde en stopt bewust waar bewijs ophoudt. Bestaande bouwstenen staan per fase genoemd; klaar-criteria zijn meetbaar.

### Fase 0 — Doctrine verankeren (bestuurlijk, week-maatstaf)

- Ken de driedeling **annotatie (DSO) / toets (RegelRecht) / verkenning (AI)** officieel toe ([bestuurlijke notitie](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md), vraag 1–2).
- Accepteer **onthouding** als volwaardig resultaat; vastleggen dat de enum-vertaling (toegestaan → `Vergunningplicht`/…) uitsluitend door een jurist gaat.
- **Klaar als**: driedeling en onthoudings-regel staan in een besluitnotitie van het bevoegd gezag.

### Fase 1 — Corpus: instrumenten als RegelRecht-YAML (bouwbaar vandaag)

- Exporteer het hele instrument via `full_export` (`build_all.py`, FormalizerPass: deterministische templates + onthouding): Eindhoven CVDR696400 (1.074 artikelen, 567 formalized) en Utrecht CVDR704250 (427/60) bestaan al.
- Dien de export als corpus-bijdrage in: het eerste `GEMEENTELIJKE_VERORDENING`-respectievelijk omgevingsplan-bestand in het landelijke corpus (nu: 0 lokale OV/OP-bestanden).
- Parallel upstream (NDD): `cvdr_id` herinvoeren, `legal_basis`/`references` openen voor CVDR — issue 1–2 uit [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md).
- **Klaar als**: beide instrument-YAML's gevalideerd tegen het vastgepinde schema (pin-test groen) en als PR/branch bij NDD ingediend.

### Fase 2 — Feitenkant: geo en GIO's als externe inputs

- Zet de TPOD/IMOW-index in (wId-anchoring, geo-feiten, GIO-adressen; kruisvalidatie Eindhoven 34/34, Utrecht 8/8) en declareer gebiedsfeiten als booleaanse inputs *zonder* `source.regulation` — het patroon dat schema v0.8.11 al ondersteunt.
- Werk de punt-toets uit tot standaardproduct: DSO-hit → executie op geo-feiten → scorecard (bewezen: 457/457 getoetst op het fixture-voorstel).
- **Klaar als**: elke formalized artikel-hit op een willekeurig RD-punt een trace oplevert of expliciet onthouding.

### Fase 3 — Executie-bridge: STTR ↔ RegelRecht (de nog te bouwen brug)

- **STTR → RegelRecht (eerst, laag risico)**: importer die RTR-bestanden ontleedt tot `machine_readable`-executies — beide DMN-dialecten (118× 1.1 + 44× 1.2 in Eindhoven), identificatie uitsluitend via `functioneleStructuurRef`/OIN (de Tilburg-les: gm-code, nooit naam/aanname), `geoVerwijzing` optioneel. Run de eigen reference-engine ernaast en maak **drift tussen loket-conclusie en artikel-toets** zichtbaar.
- **RegelRecht → STTR (later, autorauteitsroute)**: export van *nieuwe, echte* toepasbare regels als STTR 3.0.1-DMN, gevalideerd tegen de vastgepinde XSD's. Scopebewaking: RFOV-artikelen en conversie-feiten horen niet thuisloos de RTR in.
- **Klaar als**: voor één activiteit geldt: RTR-tabel en RegelRecht-executie geven op dezelfde feiten dezelfde conclusie, of het verschil is gedocumenteerd en aan een jurist voorgelegd.

### Fase 4 — Upstream schemasluiting (geo & lokale bron first-class)

- RFC bij NDD voor: geo-feittype/GIO-referentie (upstream-issue 3), harvester-bron lokaleregelgeving OV-API naast BWB (issue 4), CVDR-referenties (issue 1–2). Fase 1–3 werken ook zonder; dit is de weg naar `zoneSelector` ín de wet-YAML.
- **Klaar als**: ten minste één upstream-RFC is aangenomen en de toolbox-sync (`sync_regelrecht_schema.py`, pin-test) volgt de nieuwe schemaversie.

### Fase 5 — Landschapskoppeling: RTR als derde kennisbank-bron

- Bouw `dso_overlap/rtr.py` volgens het `client.py`-patroon (`fetch_toepasbare_regels(oin)` + `fetch_sttr_bestand(id)`, PRE via `RTR_API_BASE`), leesfuncties in `dso_kb.py`, en de derde statusregel "STTR toepast" per instrument (Tab 7).
- Regel **productie-DSO-toegang** en herhaal de overlapmeting tegen productie (bestuurlijke vraag 4).
- **Klaar als**: de kennisbank per instrument drie statussen toont — uitvoerbaar / onthouding / STTR-toepast — met expliciete absent-status waar een bevoegd gezag niets aanlevert.

### Fase 6 — Inbedding en beheer (doorlopend)

- Periodek her-export van instrument-YAML's bij consolidatiestappen (tijdreisparameters vastleggen; risicotabel bestuurlijke notitie), data-lake-sync (`lake_sync.py`), en de evaluatie: welke vragen verhuizen definitief van het loket-vragenboom-pad naar de RegelRecht-toets, en welke blijven (bekendmaking, verzoeken, samenwerken).
- **Klaar criterium (doorlopend)**: elke migratie-stap blijft herhaalbaar offline (cache + sha256-provenance) en toont coverage eerlijk per locatie en instrument.

## Stand van uitvoering — 8 november 2026, PoC's Utrecht & Eindhoven (niet Gent)

| Fase | Status | Bewijs |
|---|---|---|
| 0 — doctrine | buiten codetraject; bestuurlijke notitie ligt ter besluitvorming | [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) |
| 1 — corpus | **uitgevoerd**: staging in corpus-padconventie + tests | [corpus_export](../nldt/simulation/regelrecht/corpus_export/) (`corpus_export.py`, 3 tests groen): Eindhoven 1.074 artikelen/567 formalized onder `gemeentelijke_verordening/omgevingsplan_gemeente_eindhoven/2026-06-29.yaml`; Utrecht 427/60 onder `provinciale_verordening/…/2025-10-13.yaml`; corpus-stand live gecheckt (alleen `wet`/`amvb`/`beleidsregel`/`waterschaps_verordening`). PR-indiening bewust ná RFC's en mens-op-de-knop |
| 2 — feitenkant | **uitgevoerd**: punt-toets offline herhaald | `tpod --toets`: Eindhoven 434 scenario + 23 onthouding (0 engine-fouten); Utrecht 7/7 getoetst — conform de bestuurlijke notitie |
| 3 — executie-bridge | **gebouwd en geverifieerd** | STTR→RegelRecht-importer (`regelrecht/sttr/`, commit c275171) + index: 162 bestanden · 3.465 decisions · 2.322 projecteerbaar · 2.044 scenario-uitgevoerd (exact de gouden getallen); drift-signaal loket↔annotatie blijft de genoemde vervolgstap |
| 4 — upstream | **concepten klaar, niet ingediend** | [RFC_REGELRECHT_UPSTREAM.md](RFC_REGELRECHT_UPSTREAM.md) — RFC 1 `cvdr_id`, RFC 2 referenties, RFC 3 geo-feittype, RFC 4 lokale harvester, met indien-volgorde |
| 5 — landschapskoppeling | **uitgevoerd** | RTR-client `dso_overlap/rtr.py` + `dso_kb`-leesfuncties (c275171); hub Tab 7 toont de derde status "STTR toepast" en absent-status (rebuild geverifieerd); lake-sync dekt de nieuwe artefacten (164 items in dry-run-plan). Lopend buiten dit spoor: Utrecht-OIN-uitbreiding (`utrecht.rtr.json` binnen) |
| 6 — inbedding | deels: README-herhaalparagraaf, alles offline herhaalbaar; productie-DSO-toegang open | [nldt/simulation/README.md](../nldt/simulation/README.md) §RTR/STTR |

Gent is bewust níet meegenomen (geen DSO/RegelRecht-fasen; `gent-simulatie.html` onaangeroerd, gent-only-verificatie OK). Teststatus van dit spoor: 3 corpus-tests + pin/full-export/overlap/sttr-tests groen; één rode test (`test_fouten_noemen_herstelpad`) hoort bij het lopende Utrecht-OIN-spoor, niet bij de bovenstaande fasen.

## Risico's en beheersing (samengevat)

| Risico | Beheersing |
|---|---|
| Overclaimen van dekking (Eindhoven 56% op punt, Utrecht 6,5%) | percentages per locatie + status formalized/onthouding in elk rapport |
| Semantische vertaling als automatiek behandelen | enum-vertaling uitsluitend via jurist (Fase 0) |
| Verkeerde bevoegd-gezag-koppeling in RTR-materiaal | uitsluitend `functioneleStructuurRef`/OIN; gm-code-verificatie (Tilburg-correctie) |
| Versiedrift DMN 1.1/1.2 en schema-drift | XSD's en schema vastgepind op sha256; pin-tests in CI |
| PRE-metingen als prod_claim | omgeving + sha256 in elk rapport; prod-toegang apart regelen (Fase 5) |

## Verwijzingen

- DSO: [OGAS 2.0.1](https://iplo.nl/publish/pages/243505/dso_gas_overall_gas.pdf) · [GAS Toepasbare Regels](https://iplo.nl/publish/pages/243505/dso_gas_toepasbare_regels.pdf) · [GAS LVBB](https://iplo.nl/publish/pages/243505/dso_gas_landelijke_voorzieningen_bekendmaken_en_beschikbaarstellen_lvbb.pdf) · [STTR/IMTR-hub](https://iplo.nl/digitaal-stelsel/aansluiten/standaarden/sttr-imtr)
- RegelRecht: [docs](https://docs.regelrecht.rijks.app) · [GitHub](https://github.com/NederlandseDigitaleDienst/regelrecht) · [corpus](https://github.com/NederlandseDigitaleDienst/regelrecht-corpus)
- Repo: [POC_REGELRECHT_INTEGRATION.md](POC_REGELRECHT_INTEGRATION.md) · [POC_STTR_IMTR_KANSEN.md](POC_STTR_IMTR_KANSEN.md) · [POC_TPOD_IMOW_KANSEN.md](POC_TPOD_IMOW_KANSEN.md) · [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md](POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) · [GAP_REGISTER_NOVEX_NOTA_RUIMTE.md](GAP_REGISTER_NOVEX_NOTA_RUIMTE.md) (gap G5)
