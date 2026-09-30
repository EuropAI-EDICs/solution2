# RegelRecht-integratie voor de PoC's (Utrecht & Eindhoven)

Integratieanalyse van de LDT-toolbox-PoC's met
[**RegelRecht**](https://github.com/MinBZK/regelrecht) (MinBZK): hoe de
rule graphs van [PoC-1 Utrecht](POC_RULE_GRAPH.md) en
[PoC-2 Eindhoven](POC_RULE_GRAPH_EINDHOVEN.md) op het regelrecht-platform
aansluiten. Alle feiten over RegelRecht hieronder zijn geverifieerd tegen de
repo's en het schema (versie **v0.7.1**, september 2026); beide voorbeeld-
YAML's in [`examples/regelrecht/`](examples/regelrecht/) zijn daadwerkelijk
gevalideerd tegen dat schema (zie [verificatie](#verificatie)).

## Wat is RegelRecht

RegelRecht is "machine-readable Dutch law execution": wetteksten worden als
gestructureerde YAML opgeslagen (één bestand per versie, padconventie
`regulation/nl/{laag}/{slug}/{ingangsdatum}.yaml`) en door een deterministische
Rust-engine (ook als WASM) uitgevoerd als beslislogica, met een volledige
uitlegbare trail (`trace/v1`-schema) en gedragsconformiteit via
Gherkin-scenario's per wet. De belangrijkste bouwstenen:

- het **[corpus](https://github.com/MinBZK/regelrecht-corpus)**: ~22.000
  wet-YAML's, geoogst uit het landelijke BWB;
- het **versioned JSON Schema** (`schema/v0.7.1/schema.json`): een regeling
  is metadata + `articles[]` met per artikel `number`, `text` (letterlijk,
  markdown), `url` en optioneel `machine_readable` — "an article without
  this key is carried as text only";
- de **machine-leesbare sectie**: `endpoint`, `competent_authority`
  (bevoegd gezag, annotatie-only), en `execution` met `produces`
  (rechtskarakter zoals `TOETS`/`BESCHIKKING`), `parameters`, `input`,
  `output` en `actions` (deterministische operaties: vergelijkingen,
  AND/OR/NOT, IF/cases, datum- en rekenoperaties);
- de **workflow**: LLM-conversievoorstellen op aparte branches, menselijke
  goedkeuring via PR (de `draft-conversions`-aanpak).

## Waarom de PoC's en RegelRecht elkaar aanvullen

RegelRecht en de PoC's zijn elkaars spiegelbeeld:

| | RegelRecht | PoC-1 Utrecht | PoC-2 Eindhoven |
|---|---|---|---|
| vraagvorm | "mag dit hier, voor deze zaak?" (puntbeslissing) | "wáár in de provincie mag dit?" (zonesynthese) | "welke nieuwe regel vangt deze oude af?" (regelconversie) |
| bron | wettekst (BWB) | verordening + GIO + geodata | omgevingsplan + wijzigingsbesluiten |
| geometrie | geen | kern van de zaak | placeholder (`werkingsgebiedRef`, MC-11) |
| executie | eigen engine + trace | eigen zone-engine (shapely) | TF-IDF/Jaccard-matchers |
| validatie | Gherkin + schema | Critic V0–V4 + PROV | Critic V0–V4 + PROV |

De natuurlijke integratie: **RegelRecht wordt de beslislogica-laag, de PoC's
worden de feitenleveranciers** (geo-feiten voor Utrecht, conversie-feiten
voor Eindhoven). Sterker nog: het corpus heeft beide PoC-instrumenten
nog niet. Stand van het corpus (september 2026): 19.946 `wet`, 4.952 `amvb`,
78 `beleidsregel` en 4 `waterschaps_verordening`-bestanden — **geén enkele
gemeentelijke of provinciale verordening**, terwijl het schema de lagen
`GEMEENTELIJKE_VERORDENING` en `PROVINCIALE_VERORDENING` (met
`gemeente_code`/`provincie_code`, CBS-patroon) al defineert. Er is precies
één lokaal precedent: de *Kwijtscheldingsregeling waterschapsbelastingen
HHNK 2023* (CVDR686061, tekst-only). De eerste omgevingsverordening en het
eerste omgevingsplan in het corpus kunnen dus uit deze PoC's komen.

## Conceptmapping

| PoC-concept | RegelRecht-equivalent | Opmerking |
|---|---|---|
| NormCard-bron: artikel + letterlijk citaat + CVDR-uri + versie | `articles[].{number, text, url}` + per element `legal_basis` | de PoC's citereen al verbatim met dieptelinks — dezelfde discipline |
| verordening als geheel (CVDR704250 / CVDR696400) | metadata + `cvdr_id` | **hiaat**: `cvdr_id` bestond in schema v0.5.2 (het HHNK-bestand draagt het) maar is in v0.7.1 komen te vervallen; `additionalProperties` staat open, dus het veld valideert wél maar het law-model leest het niet meer |
| `legalForce` / bevoegd gezag | `machine_readable.competent_authority` (RFC-009) | annotatie-only: de engine rekent hetzelfde, maar alleen het bevoegd gezag produceert een bindende uitkomst |
| FormalRule `conditions` (bijv. `hub_height <= 20`) | `execution.actions` met `LESS_THAN_OR_EQUAL`/`EQUALS`/`AND`/`IF` | één-op-één vertaalbaar; zie het Utrecht-voorbeeld |
| FormalRule `zoneSelector`/`zoneSemantics` | **geen equivalent** — wordt een booleaanse `input` | `inputField.source`: laat `regulation` weg "for external data sources that must be resolved outside the YAML" — de PoC levert het feit |
| omzettabel-rij / kennisbank-paar | `articles[].references` (naar BWB-wetten) | **hiaat**: `references` vereist een `bwb_id` (patroon `BWBR…`), dus de Eindhovense "komt in de plaats van"-relatie *binnen* het eigen omgevingsplan (CVDR→CVDR) past er nog niet in |
| Critic V3 (onafhankelijke her-uitvoering) | de engine + `trace/v1` | RegelRecht kan de tweede, onafhankelijke executor worden |
| PoC-testsuites (167 + 32 tests) | Gherkin-scenario's per wet (`bdd/grammar.yaml`) | DecisionTable-rijen en omzettabel-rijen lenen zich als scenario-bron |

## Integratie PoC-1 (Utrecht) — vier fasen

**Fase 1 — corpus: de Omgevingsverordening als regelrecht-YAML.** De
grootste winst is de simpelste: exporteer de verordening naar het
regelrecht-schema. Voorbeeld (gevalideerd):
[`examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml`](examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml)
— art. 5.3 eerste lid met letterlijke tekst, en `machine_readable` precies
voor zover de Formalizer formaliseren kon (FR-W-03): parameters
`ashoogte_m` en `op_of_in_aansluiting_op_bestaand_bouwperceel`, output
`toegestaan_kleine_windturbine` als AND van drie vergelijkingen. Ambigue
kaarten (13 van de 24) exporteren als tekst-only artikel — exact de
regelmatische conventie ("carried as text only"). De PoC beschikt over alle
onderdelen: verbatim citaten, GIO-join-id's, versie-informatie.

**Fase 2 — engine: puntvragen met geo-feiten van buiten.** Het
zoneSelector-hiaat is geen blokkade maar de naad: verklaar
`in_gebied_kleine_windturbine` als booleaanse **input** zonder
`source.regulation` — een feit dat "buiten de wet-YAML" wordt opgelost. De
zone-engine van de PoC lost het op (punt-in-polygoon tegen de agrest IMOW-
laag, de GIO-alias). Zo antwoordt de RegelRecht-engine (Rust-CLI of WASM in
de pipeline) vraagstukken als *"mag hier een turbine met as van 19 m op een
bestaand bouwperceel?"* — met uitlegbare trail en correct bevoegd gezag. De
PoC kan diezelfde engine daarna als alternatief V3-pad gebruiken.

**Fase 3 — verificatie: zonesynthese tegen engine-sweep.** De PoC heeft al
een H3-brug (`poc/pipeline/h3step.py`). Draai de RegelRecht-engine per
H3-celcentrum over de provincie en vergelijk de toestaan/niet-toestaan-
cellen met de polygoonzone — IoU-stijl kruisvalidatie, in het bestaande
crosstrack/H3-rapport. Afwijkingen tussen beide executiepaden zijn precies
het soort signaal dat nu al als `needs_human` wordt gelogd.

**Fase 4 — upstream: geo als first-class feit.** Op termijn een
schema-voorstel bij RegelRecht: een geo-feittype (GIO-referentie/zone-id)
zodat `zoneSelector` in de wet-YAML zelf kan leven. Fase 1–3 werken ook
zonder; dit is een gepositioneerde bijdrage aan hun roadmap.

## Integratie PoC-2 (Eindhoven) — drie fasen

**Wanneer kan RegelRecht in Eindhoven? Niet pas na de omzetting — het vroegste
moment is nu.** De doelregeling (hoofdstukken 1–21) is sinds het
conversiebesluit van 2023 al *geldend recht*, onafhankelijk van de stand van
de afbouw van het tijdelijk deel. De 762 doelregels kunnen dus vandaag
geformaliseerd en uitgevoerd worden; het antwoord onder huidig recht hangt
nu eenmaal af van of een oude regel ter plaatse nog voortleeft, en dat
overgangsfeit (`strijd_met_tijdelijk_deel`) levert de conversieketen als
externe input aan — precies zoals het art.-10.2-voorbeeld laat zien. Pas aan
het eind van de conversie dekt de executie het héle plan; daartussen ligt de
meest waardevolle inzet: het equivalentie-orakel tijdens de omzetting.

**Fase 1 — corpus: het Omgevingsplan als regelrecht-YAML.** Voorbeeld
(gevalideerd):
[`examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml`](examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml)
— de kernkoppelingsrij uit de canonieke run (OT-001): bronartikel 22.1
(Voorrangsbepaling, tijdelijk deel) én doelartikel 10.2, allebei letterlijk
met dieptelinks, plus een `references`-item naar de Omgevingswet
(BWBR0037885, art. 22.1 onder a — geverifieerd in het corpus). Dit zou het
eerste `GEMEENTELIJKE_VERORDENING`-bestand in het corpus zijn. De volledige
export kan rechtstreeks uit `bronregels.json`/`doelregels.json` van een run
gegenereerd worden: dezelfde parser, ander uitvoercontract.

**Fase 2 — tijdens de omzetting: het equivalentie-orakel.** De Amsterdams
aanpak eist *beleidsneutraal omzetten* (MC-2), maar neutraliteit is in de
PoC alleen tekstueel controleerbaar (V2 verbatim-grounding, V3
Jaccard-herscoring). RegelRecht maakt hem uitvoerbaar controleerbaar:

```text
bronregel formaliseren ─┐  zelfde feiten
                        ├─────────────────> outputs vergelijken
doelregel formaliseren ─┘                       │
                     gelijk  → conversie beleidsneutraal; bewijs in reviewTrail
                     ongelijk → conversie wijzigt beleid  → rij naar jurist (V4)
```

Formaliseer de bronregel en de voorgestelde doelregel vóórdat de rij in de
omzettabel als `voorgesteld` landt, draai dezelfde feiten door beide
machine-leesbare versies, en vergelijk de outputs: **lopen ze uiteen, dan
heeft de omzetting beleid gewijzigd** en hoort de rij bij de jurist in plaats
van bij de automatische stap. Dit past exact op wat RegelRecht al in huis
heeft — de Gherkin-scenario's en mutation testing zijn op gedragsconformiteit
gebouwd. Cruciaal: MC-6 blijft overeind, de engine koppelt nooit — ze levert
bewijs *vóór* de mens op de knop zit; de uitlegbare trail (`trace/v1`) kan
als bewijsstuk in het `reviewTrail` van de rij worden opgenomen.

Ook het tijdelijk deel zelf is deels formaliseerbaar: oude
bestemmingsplanregels ("bouwhoogte max X m binnen bestemming Y") zijn vaak
juist deterministisch, alleen verwijzen ze naar werkingsgebieden — op te
lossen met hetzelfde externe geo-feitenpatroon als Utrecht (GIO/zone-engine,
`werkingsgebiedRef`, MC-11). Daarmee blijven ook overgangsrechtvragen
antwoordbaar zolang de conversie loopt. De eerlijke grens: alleen de
formaliseerbare subset komt in aanmerking — van de 311 rijen in de canonieke
run zijn er 70 al `needs_human`, en open normen onder de doelregels blijven
tekst-only ("carried as text only").

Daarnaast blijven de conversierelaties zelf verrijkingsdata voor het corpus:
de kennisbank (274 relaties) en omzettabel (311 rijen) willen mee, maar
`references` is BWBR-only. Twee routes: (a) upstream een CVDR-referentie
voorstellen, of (b) de relaties als losse enrichment-bestanden naast het
corpus (zoals de `enrich/*`-branches al werken). In beide gevallen geldt de
MC-6-discipline: voorstellen zijn `voorgesteld`, nooit `gekoppeld` — de
PR-goedkeuring van RegelRecht is de natuurlijke mens-op-de-knoppen-instantie.

**Fase 3 — na de omzetting: het eindplaatje.** Als het tijdelijk deel leeg
is (alle 311 bronregels omgezet of vervallen), is het hele omgevingsplan
uitvoerbaar: puntvragen van burger tot vergunningscheck met uitlegbare
trail, geo-feiten via de werkingsgebieden-GIO's. De
`werkingsgebiedRef`-placeholder (MC-11) lost op via exact het geo-feittype
uit Utrecht-fase 4: een GIO van het omgevingsplan als externe input. Daarmee
sluiten de twee PoC's op één RegelRecht-aansluiting aan: Eindhoven levert de
regelconversie, Utrecht de geometrie.

## Upstream-issues voor RegelRecht (geordend op impact)

1. **`cvdr_id` herinvoeren** (bestond in v0.5.2, verdwenen in v0.7.1) —
   zonder CVDR-identificatie is lokale regelgeving alleen via de `url`
   herleidbaar; het HHNK-precedent laat zien dat de behoefte er is.
2. **`legal_basis` en `references` zijn BWBR-only** (patroon `^BWBR\d{7}$`) —
   voor verwijzingen van/naar lokale regelgeving (CVDR, loket
   lokaleregelgeving) past daar nog geen verwijzing in.
3. **Geo-feittype / GIO-referentie** als eersteklas input, zie Utrecht-fase 4.
4. **Harvester-bron voor lokale regelgeving** (lokaleregelgeving OV-API)
   naast BWB, zodat omgevingsplannen en -verordeningen structureel binnenkomen.

## Verificatie

Beide voorbeeldbestanden zijn gevalideerd tegen het officiële schema:

```bash
curl -sL https://raw.githubusercontent.com/MinBZK/regelrecht/main/schema/v0.7.1/schema.json -o /tmp/regelrecht-schema.json
nldt/.venv/bin/python - <<'PY'
import json, yaml
from jsonschema import Draft202012Validator
v = Draft202012Validator(json.load(open('/tmp/regelrecht-schema.json')))
for f in ['docs/examples/regelrecht/omgevingsverordening-utrecht-art5.3.yaml',
          'docs/examples/regelrecht/omgevingsplan-eindhoven-art22.1-en-10.2.yaml']:
    errs = list(v.iter_errors(yaml.safe_load(open(f))))
    print(f, '->', 'VALID' if not errs else errs)
PY
```

Beide: `VALID` (draft 2020-12, schema v0.7.1, 2026-09-29). De voorbeelden
zijn demonstratoren: één artikel( paar) per bestand, met de exacte
publicatiedatum nog uit de CVDR-metadata te halen — de volledige export is
een generatie-stap boven op de bestaande run-artefacten.
