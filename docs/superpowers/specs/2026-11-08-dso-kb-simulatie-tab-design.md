# Ontwerp — Tab 7 "DSO ↔ RegelRecht" in de simulatiehub

| | |
|---|---|
| **Datum** | 2026-11-08 |
| **Status** | goedgekeurd ontwerp (met drift-kaart) |
| **Scope** | een zevende tab in `simulation/simulation.html` die de DSO-kennisbank ↔ RegelRecht-keten her-speelt; plus één kleine uitbreiding op `ververs()` (rapport-persistentie) die de drift-kaart voedt |
| **Aansluiting** | [DSO-KB MCP-spec 2026-11-07](2026-11-07-dso-kb-mcp-design.md) · [POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE](../../POC_DSO_REGELRECHT_BESTUURLIJKE_NOTITIE.md) · [RUNBOOK_NOTA_EINDHOVEN](../../RUNBOOK_NOTA_EINDHOVEN.md) |
| **Doctrine** | bouwtijd-replay van artefacten — géén runtime-diensten, géén LLM, géén MCP in de pagina |

---

## 1. Doel en niet-doelen

**Doel.** De gemeten verhouding tussen DSO (annotatie/retrieval) en RegelRecht (deterministische toets) zichtbaar maken in de simulatiehub, met de drie instrumenten van het verhaal: dekingscijfers, punttoets + geo-kruisvalidatie, en de drift-les van 7 november (byte-sha's ruisen, canonieke vergelijking spreekt).

**Niet-doelen.** Geen live/MCP-aanroepen vanaf de pagina (enige eventuele uitzondering blijft het bestaande Breda S2-lab); geen wijzigingen aan het Gent-mailpakket of bestaande tabs; geen nieuwe instrumenten/locaties in de kennisbank; geen artikellijsten in full — alleen samenvattingen en begrensde voorbeelden.

## 2. Genomen besluiten

1. **Databron = artefacten, niet `dso_kb`-import**: `build_dso_kb()` leest `dso_overlap/out/*.json` rechtstreeks (het `build_veenendaal`-patroon: JSON lezen, display-vorm versimpelen). De build blijft dependency-vrij (stdlib + json) en faalt hard bij een ontbrekende cache.
2. **Tab 7**, na Veenendaal; Nederlandstalig met de bestaande tweetalige tabkop-stijl aangehaald waar logisch; stappenmotor met 4 stappen (spiegel van de praatplaat).
3. **Drift-kaart** vereist persistentie: `ververs()` schrijft voortaan zijn resultaat naar `{stem}.ververs.json` in de cache (naast de bestaande schrijfacties; geen nieuw netwerk). De tab toont het nieuwste rapport indien aanwezig, anders een cache-versiekaart met sha's en datum.
4. **Geen kaartlaag** in tab 7: twee instrument-panelen (Eindhoven/Woensel, Utrecht/Domplein) met RD-punt, aantallen, balken en getallen volstaan; de hub-kaartmachines blijven onaangetast.

## 3. Componenten

### 3.1 `simulation/build_simulation.py` — `build_dso_kb()`

Leest per instrument × locatie uit `nldt/simulation/regelrecht/dso_overlap/out/`:

- `*.overlap.json` → `dso.counts`, `overlap.{statusCounts, executableCount, abstainCount, coverageExecutable}`, `generatedAt`, `dso.annotatiesSha256` (naar sha-16);
- `*.toets.json` → `tellingen`, top-5 onthoudingsvoorbeelden (artikel + status + eerste reden, begrensd);
- `*.geo-validatie.json` → `validatie.{getoetst, overeenstemming}` en (Utrecht) `sweep.naamAfstemming.naamOvereenkomend`;
- `*.annotaties.meta.json` → `fetchedAt`, sha-16;
- nieuwste `*.ververs.json` (indien aanwezig) → `gegenereerdOp`, `annShaOud/annShaNieuw`, `drift.inhoudelijkeDrift`, `drift.categorieen` (leeg ⇒ "geen").

Datablok-vorm (aan `main()`-dict als `"dsokb"`): `{"instrumenten": [{id, label, cvdr, locatie, locatieLabel, punt, counts, dekking, statusCounts, toets, geo, voorbeelden[], ververs?}], "gegenereerdOp"}`. Getallen ongerond overnemen (display rond af in de template); aantallen begrensd conform bestaande tabs.

### 3.2 `simulation/template.html` — tab 7

Tabregel `id="tab7"`, kop `id="kop7"` met de drielagen-doctrine ("DSO annoteert · RegelRecht toetst · AI verkent — geen LLM in de beslislijn"), sectie met vaste vier-stappen-rail (`makeSim7`, `buildRail7`, stappen drijvende panels):

1. **DSO annoteert** — per instrument: punt (RD, tekst), annotatie-aantallen, sha-16 + fetchedAt.
2. **Koppeling** — DSO-artikelen → uitvoerbaar/onthouding per instrument; statusCounts-balkjes; coverage-percentage groot; 3–5 onthoudingsvoorbeelden met reden.
3. **RegelRecht toetst** — toets-tellingen per instrument + geo-kruisvalidatieregels ("34/34 GIO-punten in overeenstemming", "8/8 naamafstemming").
4. **Verversen & drift** — ververs-rapport: datum, sha oud→nieuw, `"inhoudelijkeDrift": "geen"` prominent; toegelicht: byte-verschil ≠ inhoudelijke drift (datumecho's + volgorde). Zonder rapport: cache-versiekaart.

### 3.3 `nldt/services/dso_kb.py` — `ververs()`-persistentie

`ververs()` schrijft na de drift-berekening `out / f"{stem}.ververs.json"` met exact het resultaat-dict plus `{"gegenereerdOp": <iso-nu>}`. Bestaande velden en returns ongewijzigd; één unit-test erbij (runner-injectie; assert bestand + inhoud). Cache-map is al gitignored.

### 3.4 `simulation/verify_static.mjs`

Nieuw blok: `ds.sim7` bestaat met exact 4 stappen; gouden asserts: Eindhoven `coverageExecutable === 0.5635`, `executableCount === 457`; Utrecht `0.0654`, `7`; geo `34/34` en `8/8`; drift `"geen"` alleen geasserteerd wanneer een ververs-rapport in de data zit (`ververs` veld aanwezig). Bestaande tab-blokken en de Gent-only-check ongewijzigd.

## 4. Foutafhandeling en begrenzing

- Ontbrekend artefact → build stopt met duidelijke melding (huisgedrag, als `missing poc-veenendaal …`).
- Voorbeeldlijsten max 5 items; geen volledige artikel-/GIO-lijsten in de data.
- `--gent-only` raakt tab 7 niet (data-dict blijft zonder `dsokb`; template-patch ongewijzigd).

## 5. Testen

1. `dso_kb`-unit: ververs schrijft rapport (runner-injectie, tmp-out).
2. Build-contract: geverifieerd via een echte build-run + het nieuwe `verify_static.mjs`-blok tegen de echte cache (huisstijl: de build heeft geen eigen pytest; de statische verifier is de contracttest); een lege cache laat de build hard falen — handmatig gecheckt in de taak.
3. `verify_static.mjs`: nieuw blok groen; volledige run blijft groen (alle tabs).
4. Bestaande suites onaangetast (dso_kb 26+1, others idem).

## 6. Bouwvolgorde (globaal, plan verfijnt)

1. `ververs()`-persistentie + test (nldt, klein)
2. `build_dso_kb()` + data-aansluiting in `main()`
3. template: tab 7 + kop + sectie + `makeSim7`/rail
4. `verify_static.mjs`-blok + volledige build- en verify-run
