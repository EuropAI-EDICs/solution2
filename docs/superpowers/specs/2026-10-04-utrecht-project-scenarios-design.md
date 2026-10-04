# Ontwerp — Utrecht projectsimulatie's: gebiedsgebonden scenario's uit het provinciale projectenportefeuille

| | |
|---|---|
| **Datum** | 4 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document · **Tranche B**: uitvoering ná de [regeluitbreiding-verordening (tranche A)](2026-10-04-verordening-regeluitbreiding-design.md) — de gebiedsscenario's binden dan primair aan de nieuwe tracks (`wonen`, `water`, `bodem`, …) i.p.v. alleen `zon`/`bos`; zon/bos blijven vangnet |
| **Scope** | `poc/use-cases/areas/` + `poc/use-cases/projects/` + `poc/scenarios/projects/` (nieuw), `poc/run.py` + `poc/scenarios/run.py` (`--area`/`--set`-vlaggen), `nldt/recipes/utrecht-{opportunity-map,scenario-sweep}.json` (optionele `area`-input), `toolbox-sim/build_fixtures.py` (UCS-processen), `nldt/recipes/edic-asset-map.json` (2 dataset-entries) |
| **Bronnen** | [Provinciepagina Projecten en gebiedsontwikkeling](https://www.provincie-utrecht.nl/onderwerpen/ruimtelijke-ontwikkeling/projecten-en-gebiedsontwikkeling) (laatst gewijzigd 3-2-2026) · [`docs/SOLUTIONS_ARCHITECTURE.md`](../../SOLUTIONS_ARCHITECTURE.md) §3.3–3.4 · [`docs/GENAI_SEAMS.md`](../../GENAI_SEAMS.md) · geo-catalog §1 (fetch-mechanica) · [toolbox-sim-ontwerp](2026-10-04-toolbox-sim-design.md) |
| **Keuzes uit de sessie** | vorm: **gebiedsgebonden sweeps** (echte AoI + projectgebonden ScenarioSets, hergebruik van de wind/zon/bos-regelsets) · piloot: **A12-zone + Kromme Rijngebied** · alignatie: **recepten uitbreiden + UCS + EDIC** |

## Context en doel

De provinciepagina noemt vijf gebiedsontwikkelingen: Amersfoort tot Zeist
(Utrechtse Heuvelrug), Marinierskazerne Doorn, Vinkeveense Plassen, de A12-zone
(Groot Merwede) en het Kromme Rijngebied. Dit ontwerp maakt de eerste twee
pilootgebieden — A12-zone en Kromme Rijngebied, de twee met lopende
gebiedsprocessen en bruikbare open geometrie — eersteklas binnen de bestaande
Utrecht-pipeline: elk gebied krijgt een **citeerbare AoI**, per (gebied × track)
een **projectbaseline-run**, en per baseline een **deterministisch
ScenarioSet** dat de werkelijke beleidsvraag van dat gebied verbeeldt —
uitgevoerd via de bestaande receptketen (`utrecht-opportunity-map` →
`utrecht-scenario-sweep` → `utrecht-world-scene`) en ontsloten als UCS-processen
in de toolbox-sim.

Waarom dit werkt zonder nieuwe juridische reconstructie: de verordening is
provinciaal — de regelsets (wind/zon/bos) gelden heel Utrecht. Een
gebiedsscenario is dezelfde deterministische zone-algebra, geknipt op de
gebieds-AoI, met varianten die de beleidskeuze van dat gebied representeren.
De doctrine is ongewijzigd: **cite-or-abstain, geen verzonnen geometrie of
getallen, alles offline herrekenbaar uit de cache**.

## Gegevensbronnen en onthoudingsregel

| Gebied | Bron | Status |
|---|---|---|
| `kromme-rijn` | `Gemeenten_provincie_Utrecht`-FeatureServer (al geregistreerd + gecachet): unie Bunnik + Houten + Wijk bij Duurstede | direct uitvoerbaar; `notes` vermeldt expliciet dat de exacte gebiedsonderzoek-grens nog niet gepubliceerd is (onderzoek feb 2026–mrt 2027) en de gemeentenunie het citeerbare studiegebied-envelope is |
| `a12-zone` | provinceigen ArcGIS (AGOL-org `m4kxECHTi6Dj9hfa` / geo-point Hub search), probes volgens geo-catalog §1 | bij implementatie te proberen; valt terug op een gedocumenteerde samenstelling van deelgebieden (Woonboulevard, Papendorp, Merwedekanaalzone, Galecopperzoom, Westraven, Laagraven, De Liesbosch) als er één officiële zone-laag ontbreekt; **blijkt ook dat onmogelijk: onthouden** — dan schuift A12 uit deze snede en levert Kromme Rijn alleen |

Elke AoI-record voert `source {url, query, retrievedAt, sha256}`; de fetch
landt in de bestaande cache en het geo-register (`role: aoi`), zoals
`Provinciegrens` dat al doet.

## Architectuur

```text
poc/use-cases/areas/
  kromme-rijn.json            AoI-record (28992, bron+sha, projectUrl)
  a12-zone.json                idem (na probe/fallback)
poc/use-cases/projects/
  a12-zon.json  a12-bos.json  krommerijn-zon.json  krommerijn-bos.json
                               zelfde schema als wind.json; AoI uit het register
poc/scenarios/projects/
  a12-zon.json  a12-bos.json  krommerijn-zon.json  krommerijn-bos.json
                               ScenarioSets (scenario-set/schema)
poc/run.py                     --area <id> (nieuw; default = provincie)
poc/scenarios/run.py           --set <pad> (nieuw; baseline zoals nu via --baseline)
nldt/recipes/utrecht-opportunity-map.json   + optionele input "area"
nldt/recipes/utrecht-scenario-sweep.json    + optionele input "area"
toolbox-sim/build_fixtures.py  UCS_PROCESSES + 4 project-id's; CANONICAL_RUNS + 4 runs
nldt/recipes/edic-asset-map.json            + 2 entries (kind "dataset")
```

**Run-identiteit.** `--area` geeft de runmap het achtervoegsel
`<ts>-<use-case>@<area>` (bijv. `20261004T…-zon@a12-zone`);
`latest_baseline_run` matcht bij `--area` op `*-{use_case}@{area}`. De
sweep-runner krijgt projectruns expliciet via `--baseline` + `--set`.

## Scenariocatalogus (deterministisch, per set ≥2 varianten)

Exacte `ruleId`-binding gebeurt bij implementatie tegen de `formalrules.json`
van de desbetreffende baseline; bestaat de beoogde regel niet, dan wordt de
variant **onthouden** en in de set-legger gemotiveerd — nooit gedwongen.

| Set | Scenarioid (kandidaat) | Beleidsgrond (provinciepagina) | Mutatie (vorm) |
|---|---|---|---|
| a12-zon | A12-Z-DENSIFY | "nieuw stedelijk centrum met snelle ov-verbinding" — verdichting heeft voorrang binnen de zone | `drop` op de art.-5.5-zonneveld-inclusieregel |
| a12-zon | A12-Z-KANAALZONE | Merwedekanaalzone/Galecopperzoom als gemengd stedelijk gebied | `set_buffer_distance_m` op een distance-parameter van een relevante zonregel |
| a12-bos | A12-B-GROEN-GROEIT-MEE | "Groen Groeit Mee" (Laagraven Oost): groene compensatie als harde eis | `set_semantics` compensatiemarker → harde `inclusion` binnen de zone |
| a12-bos | A12-B-LIESBOSCH | stedelijke verdichting ontlast de zoekgebied-functie rond De Liesbosch | `drop` op de zoekgebied-inclusieregel |
| krommerijn-zon | KR-Z-HOUTEN-OOST | Houten Oost Claim: woningbouw claimt landbouw/grasland | `drop` zonneveld-inclusie binnen het studiegebied |
| krommerijn-zon | KR-Z-LANDSBELANG | landbouw/natuur eerst (gebiedsonderzoek-thema's) | `set_semantics` → `conditional` |
| krommerijn-bos | KR-B-NATUUR-EERST | natuur/kwaliteit water eerst in het gebiedsonderzoek | `set_semantics` zoekgebied → harde `inclusion` |
| krommerijn-bos | KR-B-BUNNIK-BEDRIJVENPARK | bedrijvenpark Bunnik claimt ruimte | `drop` op de zoekgebiedregel |

Elke spec: `basis.type` `policy_variant` of `norm_variance`, `provenanceNote`
verwijst naar de projectpagina + de concrete projectpassage; `proposedBy
deterministic-scenario-author#poc-v0`. De sweep produceert per gebied de
bekende `ScenarioReport`-uitkomsten (Δ km², IoU t.o.v. de eigen, op het
gebied herrekende controle) en `world-scene` levert per gebied een
`world-scene-specs.json` voor de bestaande copilot-demo.

## Contracten

- **AoI-record** (nieuw jsonschema `area.schema.json` onder `poc/schemas/`):
  `{id, name, geometry (GeoJSON), crs:"EPSG:28992", source{url,query,retrievedAt,sha256}, projectUrl, notes}`;
  V1-stijl controles: geldige, niet-lege geometrie binnen het provinciaal
  extent, bron compleet.
- **Gebruiksinstantie**: ongewijzigd `opportunity-map-request`-schema; de AoI
  komt uit het register. Projectambities komen in `ambitions` met verwijzing
  naar de projectpagina.
- **Recepten**: `area` is een optionele string-input (id uit het AoI-register;
  default = provincie). Bestaande aanroepen gedragen zich identiek —
  achterwaarts compatibel, bestaande nldt-recepttests blijven groen.
- **UCS-processen** (toolbox-sim): `utrecht-opportunity-map-{zon,bos}@{a12-zone,kromme-rijn}`
  (4 nieuwe id's), replay-outputs uit de 4 gecommitte projectbaseline-runs;
  sweep-UCS-id's zijn fase 2.

## Validatie

De bestaande niveaus, ongewijzigd van toepassing op elke projectrun en -sweep:
V0 (schema's, incl. het nieuwe AoI-record), V1 (geometrie), V2
(cite-or-abstain — nu ook op de AoI-bron zelf), V3 (onafhankelijke
herrekening, IoU ≥ 0,98). Projectruns zonder `pass`-verdict worden niet
gecommit als canoniek. Onthoudingen (ontbrekende regel voor een variant,
ontbrekende A12-geometrie) landen in ledgers, niet in stille aanpassingen.

## Tests

1. AoI-register: schema + herkomstcompleetheid + geometrie geldig en binnen
   provinciaal extent (Kromme Rijn direct; A12 na fetch).
2. `--area`-replay: deterministische hergeneratie van één projectrun
   (byte-identieke artefacten behalve run-id/tijdstempels), offline.
3. Nieuwe ScenarioSets: `scenario-set`/`scenario-spec`-schema + grounding
   tegen de eigen baseline (`ruleId`'s bestaan; geen `baseline`-basis).
4. Sweep over één projectset: controle ± varianten, Δ/IoU aanwezig,
   provenance-basis gecontroleerd.
5. nldt: recept-inputschema's accepteren `area` (optioneel); default-gedrag
   ongewijzigd (bestaande tests + één nieuwe).
6. toolbox-sim: `ucs-processes.json` bevat de 4 nieuwe id's met run-id's uit
   de projectruns; fixture-tests bijgewerkt.
7. Bestaande suites (poc, poc-bp2op, nldt, toolbox-sim) blijven groen.

## Fasering

| Fase | Inhoud | Clausule |
|---|---|---|
| 0 | AoI-register + `kromme-rijn` (uit bestaande cache) + schema + tests | mergebaar op zichzelf |
| 1 | A12-probe/fallback/fetch + register | onthoudingsregel expliciet |
| 2 | 4 projectbaseline-runs (`--area`) + `--set`-vlag + determinismetest | |
| 3 | 4 ScenarioSets + sweeps + world-scene per gebied | |
| 4 | recept-`area`-input, UCS-fixtures (4 id's), EDIC-dataset-entries | |
| 5 (optioneel) | verwijzing vanaf nldt-simulatiehub / SOLUTIONS_ARCHITECTURE | |

## Non-doelen

- Geen nieuwe juridische reconstructie of nieuwe tracks; geen LLM-autheur
  (deterministische sets alleen; de S7/Hybrid-laat blijft beschikbaar zoals nu).
- Geen crosstrack-per-gebied in deze snede (fase 2-kandidaat).
- Geen wijziging van zone-algebra, validatieniveaus of de zes
agent-contracten; geen mutatie van de canonieke provinciale runs.
- Geen visual demo-vernieuwing (de bestaande whatif-demo blijft de view).

## Risico's

| Risico | Beheersing |
|---|---|
| Geen publiceerbare A12-geometrie | onthoudingsregel: A12 schuift uit de snede, Kromme Rijn levert alleen; geen bbox-verzonnenheid |
| Gemeentenunie ≠ exacte gebiedsonderzoekgrens | als envelope gelabeld in `notes`; her-te-pinnen zodra de provincie de gebiedsindeling publiceert |
| `latest_baseline_run`-glob botst met `@`-achtervoegsel | matcht per `--area` op `*-{use_case}@{area}`; expliciete `--baseline` blijft altijd mogelijk |
| Scenariomutatie mist beoogde regel | onthoudingsledger per set; geen gedwongen binding |
| Fixturegrootte groeit (4 runs extra) | projectruns committen alleen de compacte artefacten (zones/normcards/formalrules/summary), geometrie via de bestaande cache-referenties |
| Parallelle sessies in de hoofdwerkmap | uitvoering in geïsoleerde worktree op eigen branch (gevestigd patroon) |
