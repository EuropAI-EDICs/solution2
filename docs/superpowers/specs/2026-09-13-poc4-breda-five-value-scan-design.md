# PoC-4 — Breda vijf-waardenscan (design)

**Vraag.** Waar creeert data + AI vandaag al waarde voor de gemeente Breda — per
buurt, voor elk van de vijf waarden van het congres *AI in the City 2026*
(23–25 september 2026, Breda; <https://www.indestad.ai/en/#programme>):
**democratische, ruimtelijke, economische, sociale en autonome waarde** — met
elke indicator herleidbaar naar een naamrijk genoteerde open bron met
retrievedatum, en elke kaartlaag gekoppeld aan een naamrijk programmeonderdeel?

Dit is PoC-4 van de LDT-toolbox en antwoordt letterlijk op de call van het
congres (*"Creating Real Value"*, vijf waarden, *"AI as a layer in the City"*).
De vijf waarden vormen de inhoudelijke index van de scan; het programmeonderdeel
dat elke laag "beantwoordt" wordt in het rapport verbatim geciteerd.

## Waarom deze afbakening

- De vijf waarden zijn het rooster van het congresprogramma; een PoC die per
  waarde één eerlijke, gegevensgedocumenteerde indicator per buurt oplevert,
  maakt het congresverhaal concreet voor Breda zelf (genius loci).
- PoC-1 (`poc/`) is juridisch-zonair en provinciaal; PoC-3 (`poc-rijnland/`) is
  waterkwaliteit en H3. PoC-4 opent het domein *sociaal-ruimtelijke
  buurtstatistiek* — dezelfde deugden (deterministisch, cite-or-abstain,
  PROV, offline-testbaar), nieuwe datasoort (CBS-statistiek + gemeentelijke
  klimaatlagen).

## Data (allemaal sleutelloos, allemaal publiek, per 2026-09-13 geverifieerd)

| id | bron | inhoud | rol |
|---|---|---|---|
| `cbs-buurten-2024` | PDOK WFS `service.pdok.nl/cbs/wijkenbuurten/2024` | buurtvlakken + ±400 statistiekvelden (bevolking, 65+, afstanden tot voorzieningen, woningvoorraad, zonnestroom, bedrijven) | alle ruimtelijke indicatoren + geometrie |
| `breda-gemeentegrens` | data.breda.nl (AGOL `services-eu1.arcgis.com/SgHNk1qzR4I13Wum`, `AER_Gemeentegrens/0`) | gemeentegrens RD | AOI + bbox |
| `breda-wijkdeals` | idem, `Wijkdeals/0` | wijkdeal-vlakken | democratische waarde |
| `breda-hoofdgroenstructuur` | geo.breda.nl `Hoofdgroenstructuur/MapServer/0` | te behouden stedelijk groen | ruimtelijke waarde |
| `breda-verharding` | geo.breda.nl `klimaatportaal/hitte/3` | `P_verhard` per wijk | sociale waarde |
| `breda-kansenkaart` | geo.breda.nl `klimaatportaal/kansenkaart/0` | klimaatkans per wijk (`OMSCHRIJV`) | ruimtelijke waarde |
| `breda-bomen` | data.breda.nl `Bomen/0` | boom-punten | ruimtelijke waarde (density) |

data.breda.nl is een ArcGIS Hub (org *gemeente-breda*); daarmee hergebruikt de
PoC de bestaande ArcGIS-REST-fetcher uit `poc/pipeline/geodata.py`. De CBS-WFS
is een nieuw dialect (OGC WFS 2.0 geojson): **recon-bevinding 13-9-2026** —
`cql_filter` wordt door de PDOK-GoMapserver genegeerd en `bbox`+`startIndex`
heeft een instabiele sorteervolgorde; de standaard OGC-XML `filter` op
`gemeentenaam='Breda'` werkt wél exact (1 pagina, 56 buurten — Breda hanteert
sinds de herindeling een grove indeling van 11 wijken / 56 buurten, geen
aparte water-buurten). De volumecheck in de validator is daarop afgestemd
(≥ 40).

## Indicatoren (per buurt; 0–100, hoger = meer van de betreffende waarde)

1. **Democratische waarde** — *voorzieningentoegankelijkheid*: gemiddelde
   CBS-afstand (huisarts, supermarkt, basisschool, kinderdagverblijf,
   bibliotheek, treinstation) → percentielscore; plus *wijkdeals-dekking*
   (oppervlakteaandeel met ≥1 wijkdeal). Beantwoordt: waarde-thema
   Democratische waarde; workshop *Residents in the driving seat*; sessie
   *Demo: Autonomous and democratic*.
2. **Ruimtelijke waarde** — *groene ruggegraat*: aandeel
   Hoofdgroenstructuur-overlap +CBS `afstandTotOpenbaarGroenTotaal` (invers) +
   bomen per 100 inwoners; plus kansenkaart-vlag per wijk. Beantwoordt:
   *Green Spaces and Water as the backbone of the city* (workshop van de
   gemeente zelf); waarde-thema Ruimtelijke waarde (*genius loci*).
3. **Economische waarde** — *onbenut dakpotentieel*: (100 −
   percentageWoningenMetZonnestroom) × share eengezinswoningen (dak-eigendom-
   proxy) + bedrijvendichtheid (CBS vestigingen/km²). Beantwoordt: AI-walk
   *Energy savings and impact on infrastructure* (TNO); waarde-thema Economische
   waarde.
4. **Sociale waarde** — *hitte-kwetsbaarheid*: genormaliseerd
   `P_verhard` (eigen klimaatportaal) × aandeel 65+ (CBS) → aandachtsscore.
   Beantwoordt: waarde-thema Sociale waarde (klimaatadaptatie).
5. **Autonome waarde** — geen geografische laag maar een **soevereiniteits-
   manifest**: alle bronnen publiek/Europees (PDOK, CBS, gemeente), nul
   API-sleutels, nul cloud-vendor-locks, deterministisch herdraaibaar,
   PROV-provenance met sha256, optionele lokale LLM-seam. Beantwoordt: workshop
   *Sovereignty*; AI-walk *Data sovereignty and -continuity*; lezing *From
   European AI strategy to opportunities for your city* (LDT CitiVERSE EDIC);
   *Is your city ready for AI?* (OECD).

Composiet: per buurt het profiel over de vier ruimtelijke scores (géén
weging/gemiddeld cijfer van de stad — verschillende waarden zijn geen optelsom;
het rapport toont per waarde eigen tops en onderkanten).

## Missing-data-beleid (cite-or-abstain, statistiekvariant)

CBS gebruikt negatieve sentinels (−99995/…97/…98) voor geheim/onbekend; water-
buurten (`water='JA'`) hebben geen statistiek. Elke indicator berekent alleen
uit aanwezige inputs; ontbrekende inputs worden per buurt in `validation.json`
genoteerd onder `needs_human`-stijl registratie — nooit geimputeerd, nooit
genoemd zonder dat de bron het zegt.

## Pipeline (`poc-breda/`, hergebruik patroon PoC-1/3)

```
run.py ─ Intake (request.json, AOI=gemeentegrens)
      ├ Fetch  — ArcGIS via poc.pipeline.geodata (cache RD, cache-first);
      │          CBS-WFS-eigen fetcher (bbox-paging, cache geojson)
      │          → layers.json (manifest: bron, licentie, lastChecked)
      ├ Indicators — shapely-overlays in RD; percentielnormalisatie;
      │          sentinelfilter → indicators.json (schema-gevalideerd)
      ├ Validate — V0 schema's; V1 sanity (aandelen ∈[0,1], count-bereiken,
      │          dekkingschecks); verdict pass/fail → validation.json
      ├ PROV — prov.json (agents=modules, entities+sha256, activities,
      │          hadPrimarySource per laag incl. lastChecked)
      └ Report — report.html (offline Leaflet, laag-per-waarde + overlays,
                 waardenpanelen met programma-citaten, beperkingen),
                 report.md, run_summary.json; exit 0 alleen bij verdict pass
```

Nieuwe bestanden: `poc-breda/run.py`, `breda/{__init__,fetch,indicators,report,
validate}.py`, `breda/report_template.html`, `schemas/indicator.schema.json`,
`schemas/value-scan.schema.json`, `data/sources.json`, `tests/` met fixtures
(mini-CBS + mini-Breda-vlakken) voor volledig offline e2e.

Buiten scope (YAGNI): H3 (buurtvlak is hier de eerlijke eenheid), BGT/BAG-bulk,
LLM at runtime (seam gedocumenteerd, uit), scenario-mutaties.

## Tests

Offline unittest met synthetische fixtures: sentinelfilter, percentiel- en
composietmath, overlay/dekking op handgemaakte vlakken, rapport-escaping
(les uit PoC-1: echte `<`-escapes), schema-validatie, e2e-pipeline op fixtures
(exit-code-0 bij pass), soevereiniteitsmanifest-volledigheid.

## Risico's

- AGOL/geo.breda-lagen kunnen mid-run wijzigen of vertragen → fetcher degradeert
  gepast: betreffende indicator valt weg en wordt in validation geregistreerd
  (zelfde patroniek als PoC-1); nooit giswerk.
- CBS 2024-indeling wijkt mogelijk af van Breda-wijknamen in klimaatportaal →
  joins lopen op wijkcode/statcode waar kan, anders oppervlakte-overlap (deterministisch, herleidbaar).

## Aanvulling (13-9-2026, na de eerste oplevering) — grounded Q&A-seam (S4-analoog)

Toepassing van agentic AI rondom (nooit ín) de pijplijn, conform
`docs/GENAI_SEAMS.md` ("LLMs propose, deterministic engines dispose"):

```
vraag (NL) ─▶ asker (deterministische parser | LLM-voorstel)
                │  gate: schema (scan-query.schema.json) + woordenschatgronding
                │         (buurtNaam moet resolven; vormdrift wordt door de seam
                │          genormaliseerd — PoC-1-les §5.2)
                ▼
           ScanQuery ─▶ deterministische runner (leest alleen value-scan.json)
                ▼
           antwoord ─▶ deterministisch sjabloon | LLM-narratie achter de
                       numerieke grounding-gate (volledige precisie, teken- en
                       duizendtal-vouw, geen buurten buiten de rijen);
                       afkeuring → ledger + deterministische fallback
```

- CLI: `poc-breda/qa_run.py` (--demo golden set, --interactive, --asker/--narrator
  auto|llm met dezelfde `LDT_SCENARIO_LLM_*`-env als PoC-1, Ollama-native transport).
- Identiteitsstempel door de seam (`llm-proposal#<model>`); de query
  `question` wordt door de seam overstemd met de gestelde vraag (geen
  paraphrase-doorvoer).
- Live gevalideerd met qwen3.8: schema-gate ving `'Belcrum'`-in-`focus`-vormdrift,
  eerlijke onthouding gerespecteerd, Nederlandse narratie (duizendtallen,
  komma-decimalen, volle float-precisie) geaccepteerd na drie gate-fixes die
  de eigen collectie betroffen (:g-verkorting, dict-keys, NL-duizendtallen).
- Buiten scope gebleven (bewust): threshold-/combinatievragen (contract biedt
  geen filtertaal — onthouden in plaats van giswerk) en het
  scenario-auteursnaad (S7-analoog; patroon lig klaar in PoC-1).
