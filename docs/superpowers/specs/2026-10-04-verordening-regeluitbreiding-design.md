# Ontwerp — Regeluitbreiding Omgevingsverordening: zes tracks voor fysieke en sociaal-economische aspecten (tranche A)

| | |
|---|---|
| **Datum** | 4 oktober 2026 |
| **Status** | ontwerp goedgekeurd in brainstormsessie; wacht op review van dit document |
| **Scope** | zes nieuwe tracks onder `poc/` (evidence-shards, cite-or-abstain-legers, formalizer-templates, zone-aliases, use-cases, canonieke runs), `run.py::TRACKS`-registratie, objectType-enum, GIO-probes + registry-uitbreiding, UCS-processen (toolbox-sim), recept-inputomschrijving |
| **Volgorde** | **Tranche A** van het Utrecht-programma; [projectscenario's-spec A12/Kromme Rijn](2026-10-04-utrecht-project-scenarios-design.md) is tranche B en her-bindt na afronding |
| **Bronnen** | CVDR704250 geldend 13-10-2025 (snapshot `docs/research/sources/cvdr704250-tekst-extract.txt`) · [`docs/research/legal-facts.md`](../../research/legal-facts.md) · geo-catalog §1 · [`docs/SOLUTIONS_ARCHITECTURE.md`](../../SOLUTIONS_ARCHITECTURE.md) §3.3 (trackmodel) · [toolbox-sim-ontwerp](2026-10-04-toolbox-sim-design.md) |
| **Keuzes uit de sessie** | dekking: **volledig** (zes clusters) · granulariteit: **per hoofdstuk-cluster** · volgorde: **regels eerst, projectscenario's daarna** |

## Context en doel

De bestaande tracks (wind, zon, bos) dekken hoofdstuk 5 en deel 6 van de
Omgevingsverordening. Dit ontwerp breidt de regelsets uit over de rest van het
instrument — fysiek (watersysteem, ondergrond/bodem, bereikbaarheid/mobiliteit)
én sociaal-economisch (cultuurhistorie/landschap, landbouw, wonen-werken-
recreëren) — zodat de latere gebiedsscenario's (tranche B) en cross-track-
analyses kunnen redeneren over wonen, water, bedrijvigheid en recreatie in
plaats van alleen energie en natuur.

Zes nieuwe tracks, elk volgens het vaste trackmodel (SOLUTIONS_ARCHITECTURE
§3.3): evidence-shard met letterlijk geciteerde artikelen, cite-or-abstain-
leger, formalizer-templates (ongeformatteerde kaarten worden `ambiguous`,
nooit geraden), zone-aliases naar geregistreerde services, use-case-file met
objectType, en één canonieke run met V0–V3-verdict `pass`. Pipeline, agent-
contracten, validatieniveaus en artefacten veranderen niet.

## De zes tracks

| Track (id) | objectType (vraagstelling) | Verordening-kern | Verwachte zonesoorten (GIO/registry) |
|---|---|---|---|
| `water` | `riparian_development` — waar zijn bouw/activiteiten in en om het watersysteem begrensd | H2: 2.2–2.16 (omgevingswaarden kering/wateroverlast, vrijwaringszone kering 2.14, waterbergingsgebied 2.15, overstroombaar gebied 2.16, waterschaarste 2.17–2.18) | `ow_bwp_overstroombaar` (registry), waterkering- en bergingsgebieden via agrest-GIO-probe |
| `bodem` | `soil_activity` — waar gelden grondwater- en bodembreuk bij grondverzet/infiltratie | H3: 3.1–3.5 (grondwaterbeheer, grondwaterbeschermingszone 3.2-kern, verontreiniging 3.3, grondverzet/rommelterrein 3.4, gesloten stortplaats 3.5) | `ow_bwp_grondwater` (registry), stortplaatsen/beschermingszones via probe |
| `mobiliteit` | `roadside_development` — waar begrensen weg, spoor, vaarweg, geluid en externe veiligheid ontwikkeling | H4: 4.2 provinciale weg, 4.3 lokale spoorweg, 4.4 vaarweg, 4.6 externe veiligheid basisnet, 4.7 geluid provinciale weg | geluidszones/basisnet via probe; bestaande bufferlagen deels herbruikbaar |
| `landschap` | `landscape_intervention` — waar dragen cultuurhistorie en landschapskwaliteit eisen op | H7: 7.1 cultuurhistorie, 7.2 kwaliteit landschap | `Hollandse_Waterlinie` (registry), aardkundig `ow_bwp_*`, landgoederen via probe |
| `landbouw` | `agricultural_expansion` — waar en onder welke voorwaarden kan het agrarisch bedrijf groeien | H8: 8.1 agrarisch bedrijf, 8.2 bodembewerking veengebied | veengebied/agrarische zones via probe; NNN-interactie via bestaande lagen |
| `wonen` | `housing_development` — waar kunnen stedelijke functies (wonen, werken, recreëren) bij en ontstaan | H9: 9.2–9.16 (landelijk gebied: verstedelijkingsverbod 9.3, woning 9.6, enclave/lint 9.7, kernrandzone 9.10, 50-woningen 9.14, flexwoningen 9.14a, uitbreiding woningbouw 9.15, bedrijventerrein 9.16), 9.17–9.21 (stedelijk: verstedelijking, bedrijventerreinen, kantoren, detailhandel, Seveso), 9.22–9.23 (dagrecreatie, recreatiezone) | Landelijk/Stedelijk gebied-GIO (agrest, `NAAM='Landelijk gebied'`-patroon al bekend), kernrandzones/recreatiezones via probe |

**ObjectType is de vraagstelling per track** en wordt bij recon per cluster
geconcretiseerd; de use-case-file legt hem vast (enum-uitbreiding van
`opportunity-map-request`).

## Methode per track (onveranderd trackmodel, stap voor stap)

1. **Recon** tegen de snapshot: per artikel bepalen artikeltekst ↔ toelichting,
   letterlijk citaat opnemen, bronregistratie uitbreiden; regels zonder
   zone-draagvlak of procedureel karakter (omgevingswaarden-monitoring,
   beoordelingsregels, vrijstellingen) gaan met reden naar het
   **onthoudingenleger** — cite-or-abstain, zoals bij de bestaande tracks.
2. **Zone-probe**: agrest Omgevingsverordening-FeatureServer op distinct
   `NAAM`-waarden bevragen (geo-catalog §1-mechanica: `f=json`,
   `returnGeometry=true`, paginering); relevante lagen in `sources.json`
   (rollen `inclusion|exclusion|conditional|aoi`), fetch + cache + sha256.
   **Geen GIO beschikbaar voor een gebiedsaanwijzing → de regel wordt
   `ambiguous`/onthouden, nooit een getekende zone verzonnen.**
3. **Formalisering**: templates alleen waar parameter/operator/waarde/unit
   letterlijk uit de tekst komen; `derivation: legal-text` label.
4. **Use-case + canonieke run**: `poc/run.py --use-case <track>`; verdict
   `pass` (V0–V3, onafhankelijke herrekening) is opnamedrempel voor het
   canonieke run-artefact.
5. **Ontsluiting**: `UCS_PROCESSES` + `utrecht-opportunity-map-<track>` (6
   nieuwe id's) in `build_fixtures.py`; recept-inputomschrijving
   `useCase (wind|zon|bos|water|bodem|mobiliteit|landschap|landbouw|wonen)`;
   EDIC-assetmap: geen nieuwe recept-id's, dus geen nieuwe entries — de
   bestaande `utrecht-opportunity-map`-entry dekt de verbrede enum.

## Validatie

Bestaande niveaus, ongewijzigd: V0 (ook voor de nieuwe evidence-shards en
use-cases), V1 (geometrie; nieuwe lagen doorlopen dezelfde
make_valid/CRS-poort), V2 (citaat-containment tegen de snapshot; bron- en
versievelden verplicht), V3 (onafhankelijke herrekening per nieuwe track).
Nieuwe harde eis: elke nieuwe zone-alias resolveert naar een
registry-entry mét sha256 en `lastChecked`; ontbrekende GIO's leiden tot
onthouding, niet tot surrogaat.

## Tests

1. Per track: evidence-shard-schema, citaat-letterlijkheid (containment tegen
   snapshot), onthoudingenleger compleet (elk niet-geformaliseerd artikel heeft
   een reden).
2. Per track: canonieke run herrekenbaar en deterministisch (hergeneratie
   byte-identiek op artefactniveau); V3-IoU ≥ 0,98.
3. Enum-/contracttests: `objectType`-enum, `TRACKS`-registratie,
   use-case-schema's.
4. Registry: nieuwe bronnen geregistreerd met rol en sha; cache-hit zonder
   netwerk (offline-herrekening).
5. toolbox-sim: `ucs-processes.json` bevat de 6 nieuwe id's met run-id's uit
   de nieuwe canonieke runs.
6. Bestaande suites (poc, nldt, toolbox-sim, poc-bp2op) blijven groen; de
   bestaande canonieke wind/zon/bos-runs blijven byte-identiek.

## Fasering (elke fase zelfstandig mergeerbaar)

| Fase | Tracks | Bijzonderheden |
|---|---|---|
| 0 | methodewiring: TRACKS-registratie, objectType-enum, agrest-NAAM-probe-script | geen run-inhoud nog |
| 1 | `water` + `bodem` | grootste registry-dekking (ow_bwp_* al geregistreerd) |
| 2 | `mobiliteit` + `landschap` | geluid/basisnet-probe; Hollandse Waterlinie hergebruik |
| 3 | `landbouw` + `wonen` | Landelijk/Stedelijk-GIO; kernrandzone/recreatiezone-probe |
| 4 | UCS-fixtures (6 id's) + recept-omschrijving + (optioneel) cross-track-uitbreiding over de nieuwe tracks | doorstart tranche B |

## Non-doelen

- Geen wijziging van pipeline, agent-contracten, validatieniveaus of de zes
  bestaande artefact-soorten; geen mutatie van bestaande tracks en runs.
- Geen LLM-leg in de recon of formalisering (deterministisch; S1/S2-hook
  blijft beschikbaar zoals nu).
- Geen gebiedsscenario's of AoI-register in deze tranche (tranche B).
- Geen actualisatie naar de aankomende wijziging (PS 18-11-2026, in werking
  1-1-2027): corpus-pinning en bronmonitor bestaan; her-recon is expliciet
  vervolgwerk na inwerkingtreding.

## Risico's

| Risico | Beheersing |
|---|---|
| GIO ontbreekt voor gebiedsaanwijzing | onthoudingsleger per regel; geen verzonnen zones (zelfde doctrine als DSO-401) |
| Omgevingswaarden zijn monitoring-normen, niet zonegebonden | systematisch onthouden als `procedural`; geen geforceerde formalisering |
| Omvang: zes tracks juridische reconstructie | fasering per clustergroep; elke fase mergeerbaar; tracks onafhankelijk |
| Snapshot-/versiedrift door aankomende wijziging | pinning geldend 13-10-2025 + bestaande bronmonitor; her-recon als vervolg na 1-1-2027 |
| Track-interactie (water × wonen × natuur) verleidt tot voorlopen op tranche B | cross-track blijft fase 4, optioneel, na de zes basale tracks |
| ArcGIS-churn bij nieuwe lagen | bestaande watchlist-/probe-patronen; registry-driven fetchen met sha |
