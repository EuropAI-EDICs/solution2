# MiniGIM-integratie in de LDT-toolbox (PoC-5)

**MiniGIM** ([minigim.nl](https://minigim.nl/), DMI-ecosysteem/NEPROM) is de
praktijkstandaard voor gebiedsontwikkelaars: één werkwijze voor
omgevingsanalyse, gebiedsindeling en (fase 2) financiële doorrekening.
Dit document legt vast hoe de methodiek in de LDT-toolbox is vertaald,
welke keuzes zijn gemaakt en waar fase 2 aansluit.

## De twee MiniGIM-artefacten → machine-leesbaar

| MiniGIM-artefact | Omvang | Onze vertaling |
|---|---|---|
| Omgevingsanalyse **Lijst v0.91** | 74 items: thema/onderdeel/item × bronregistratie/bronleverancier × prioriteit × risico × formaat × 2D/3D | `poc-minigim/registry/minigim-lijst.json` (gegenereerd uit de gepinde xlsx, schema-gevalideerd) + `lijst-bindings.json`: per item een binding `auto` (14) / `partial` (15) / `manual` (45) naar een sleutelloze open bron, met deterministische derivation-op (`echo_input`, `clip_layer`, `clip_stats`, `count_in_aoi`, `list_in_aoi`, `presence`, `proxy_ratio`, `proxy_entropy`, …) |
| **ILS v0.8 "Input Grex"** | 49 nodes in niveaus 0–3 (uitgeefbaar/mandelig/openbaar → verhard/groen/water → …), IfcExportAs-mapping (IFCSITE/IFCSLAB/IFCROAD/IFCBRIDGE/…), EPset_minigim ("Wat ben je?" → IfcName; "Van wie was je?" → Kadaster/BIMLEGAL; "Van wie wordt je?" → Afnemer) | `poc-minigim/registry/minigim-ils.json` + `minigim/ils.py`: draft-gebiedsindeling afgeleid uit BGT/BAG/BRK — wegen → n2.wegen (IFCROAD), water → n2.water (IFCSITE), groen → n1.groen, verhard onbegroeid terrein → n1.verhard (token-match op functie/fysiek_voorkomen: "verharding" telt wél mee, "onverhard" níet), brug → overbruggingsdeel (IFCBRIDGE), percelen → n2.percelen (kandidaat-uitgeefbaar), panden → n3.bebouwd (IFCBuilding) |

Beide xlsx-bronnen zijn **gepind** onder `poc-minigim/sources/` met sha256 in
de registries; de converter (`tools/convert_minigim_xlsx.py`) is build-time en
reproduceert de registries deterministisch.

## Interpretatie-keuzes (expliciet, per ontwerp)

1. **Niveau 0 = huidige situatie.** De ILS-classificatie beschrijft het
   gebied *zoals het is*: openbare infrastructuur → openbaar; kadastrale
   percelen → kandidaat-uitgeefbaar. De definitieve gebiedsindeling is een
   ontwerpbeslissing van de gebiedsontwikkelaar → elk draft-artefact draagt
   `draft: true` + `v4: pending` (human-in-the-loop).
2. **Eigendom is geen open data.** "Van wie was je?" (EPset_minigim) is
   zakelijk recht — BRK-levering vergt een grondslag. De draft zet de
   eigenschap expliciet op `null` met toelichting; percelen dragen wél
   kadastrale aanduiding (gemeente/sectie/perceelnummer).
3. **Faal-isolatie, geen fake delivery.** Elk checklist-item wordt apart
   uitgevoerd; een bronstoring degradeert dát item naar `not-delivered` met
   risicovlag "hoog-prioriteit niet automatisch geleverd" in plaats van de
   run te breken of te vervalsen. Manual-items (45/74) krijgen een
   `manualPointer` naar de bevoegde bron (KLIC, RO-online, DINO, …).
4. **Proxy's benoemen zichzelf.** CBS-buurtstatistiek (inwoners, WOZ) is
   buurtniveau: oppervlaktegewogen naar de plangrens met `proxyNote`; FSI/GSI/
   MXI zijn open-data-proxy's (`fsiProxy`, `gsiProxy`, `mxiProxy` via
   genormaliseerde Shannon-entropy over gebruiksdoelen) — nooit als exact
   gepresenteerd.
5. **BGT-historie wegfilteren.** PDOK's OGC API levert ook beëindigde
   objecten (`eind_registratie`); de runner filtert die client-side en
   rapporteert `historicalObjectsFiltered` (pilot: 6.854 objecten).
6. **Server-caps zichtbaar.** geo.breda.nl MapServer pagineert niet
   (cap ~1000): bij aanslag op de cap wordt het item gemarkeerd
   `layerCapped` met toelichting.

## Provenance & validatie

- `prov.json`: run-id, AOI-sha256, register-sha256's (Lijst + ILS), per
  bronlaag een fetch-manifest (protocol, url's incl. cursor-paginering,
  pagina-aantal, feature-sha256's, fetchedAt) — nooit volledige
  feature-collecties (compact en diff-baar).
- Validatie V0–V3 zoals PoC-1..4: V0 jsonschema op elk artefact, V1
  geometrie (plangrens geldig, lagen GeoJSON), V2 bron-gronding (de door de
  Lijst gedeclareerde bronregistratie moet herkenbaar zijn in de prov van
  elk delivered item), V3 in-run replay (alle derivaties herberekend en
  byte-vergeleken). Exit 0 uitsluitend bij verdict `pass`. V4 (mens) is
  pending by design — de checklist is input voor de analist, geen
  eindoordeel.

## nLDT-integratie

- Recipe `nldt/recipes/minigim-gebiedscheck.json` (risk low) rond proces
  `minigim-gebiedscheck-run` (replay/execute) — geregistreerd in
  `services/process_adapter/poc_handlers.py`, de catalog-seed en MCP-tool
  `run_minigim_gebiedscheck`. Zie `nldt/04-recipes-and-processes.md`.

## Fase-2-haken (bewust buiten scope)

| fase-2 wens | haak in de code |
|---|---|
| **IFC-export** van de ILS-draft | `ils-draft.features.28992.geojson` draagt per feature `ilsNodeId`, `ifcExportAs` en `epsetMinigim` — een IfcOpenShell-stap kan hier direct op bouwen (spatial structure per nodePath, IfcTypeProduct per IfcExportAs) |
| **GREX-financiële koppeling** | ILS-nodes zijn stabiel geïdentificeerd (ids uit het register); koppeling met de GREX-tabellen (opbrengsten/kosten per gebiedsdeel) kan op `ilsNodeId` joinen |
| **EIGENAARS-database** | `epsetMinigim.vanWieWasJe` is voorbereid maar `null`; een BRK-zakelijk-recht-bron (grondslag vereist) vult dit zonder schema-wijziging |
| **Bestemmingsplan/RO-online** | item `ruimtelijke-ordening.bestemmingsplan` heeft `manualPointer`; fase 2 kan de IMRO-harvester (poc-bp2op-ervaringen) hieraan koppelen |
| **3D (AHN2/LOD2)** | Lijst-items 2D/3D-vlag komt uit het register; de 3d-viewer-ervaring (LOD22) en AHN-grids sluiten aan op `topografie.hoogte.hoogte-maaiveld` (nu manual) |

## Herkomst methodiek-documentatie

- Omgevingsanalyse Lijst v0.91 en ILS v0.8 "Input Grex": MiniGIM-werkgroep
  (DMI-ecosysteem/NEPROM), gepinde snapshots onder `poc-minigim/sources/`
  (sha256 `36ef4993…7ca3c18` resp. `8c6b8686…262f5c6d`).
- Bron-dienstverlening: PDOK (BGT/BAG/BRK/CBS/NWB/RCE/Natura 2000 — alle
  sleutelloos), gemeente Breda (AGOL + geo.breda.nl). Zie
  `poc-minigim/data/sources.json` voor de volledige bronlijst incl. quirks.
