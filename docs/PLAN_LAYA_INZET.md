# Laya-inzetplan — System-1 triage in de DSO↔RegelRecht-architectuur

| | |
|---|---|
| **Datum** | 8 november 2026 |
| **Vervolg op** | [MAPPING_DSO_NAAR_REGELRECHT.md](MAPPING_DSO_NAAR_REGELRECHT.md) (architectuurmapping + fasen, deels uitgevoerd) |
| **Positie** | Nieuwe rij in de componentmapping: *tussen* de DSO-annotatielaag en de RegelRecht-executielaag |
| **Eerste bouw** | [superpowers/plans/2026-11-08-laya-formalisatie-poortwachter.md](superpowers/plans/2026-11-08-laya-formalisatie-poortwachter.md) (Inzet A) |

---

## De kern in één alinea

Laya (322M, niet-autoregressief, ~ms lokaal op MLX) wordt de **System-1-triagelaag** van de
kennisbank: per artikel, per bronregel en per gebruikersverzoek een getypeerd,
gekalibreerd hint-antwoord met expliciete onthouding (confidence-gate 0,55 + noul-vragen) —
nooit een juridische conclusie, nooit nieuwe cijfers, nooit in de beslislijn. Dat is de
vierde laag van de doctrine (**DSO annoteert · RegelRecht toetst · STTR toepast · AI
verkent/trieert**) operationeel gemaakt: Laya bepaalt de *route* en de *volgorde van
aandacht*, de engines (reference engine, zone-engine, DMN-projectie) rekenen, de mens
beslist.

## Vijf vaste principes (voor élke Laya-inzet)

1. **Gold uit eigen artefacten** — trainingslabels komen uitsluitend deterministisch uit
   bestaande run-artefacten (formalization-reports, omzettabel, scan-runs); nooit
   uitgedacht, nooit door een LLM gegenereerd.
2. **Generalisatie meten, geen parafrase** — splits houden hele eenheden vast (artikelen,
   runs, wijken); de enige claim-waardige meting is op *ongezien* materiaal, bij voorkeur
   kruisinstrument (train op Eindhoven → evalueer op Utrecht).
3. **Onthouding is een antwoord** — onder de gate komt er géén hint, alleen een
   signaal; een noul-antwoord ("weet niet") is een geldige uitkomst.
4. **Vastgepind en herhaalbaar** — checkpoint-sha256 in elk artefact (pin.json-stijl),
   datasetbouw deterministisch (pure sorting, geen seed nodig), uitvoer offline
   reproduceerbaar; checkpoints zelf buiten git (bestaand beleid).
5. **Fail-soft, altijd** — Laya uit/aanwezig verandert niets aan de beslis-keten; elke
   inzet heeft een deterministische fallback en de kernpijplijnen draaien zonder.

## De inzetten, op volgorde

### Inzet A — Formalisatie-poortwachter (nu bouwen)

**Wat.** Nieuw checkpoint `laya_formalizer`, getraind op de twee gecommitte
formalization-reports (Eindhoven 1.074 artikelen/567 formalized; Utrecht 427/60): per
artikel, op de letterlijke tekst, een S1-voorspelling van `voorspelde_status`
(formalized/ambiguous/unmatched) + `heeft_evidence` (noul).

**Waarom dit eerst.** (1) Het is de directe opschaling van wat `laya_utrecht` al doet
(regelstatus-triage op NormCards) naar instrumentniveau. (2) Het versnelt de
draft-conversions-route van RegelRecht zelf (de "analoog-recht-converter" uit hun
ecosysteem): een nieuw instrument zonder templates krijgt binnen milliseconden een
werklijst — *voorspeld formaliseerbaar* → LLM-formaliseervoorstel met context;
*voorspeld open norm* → direct tekst-only ("carried as text only"), geen token verspild.
(3) Voor de eigen full_export geeft het de template-gap-analyse: artikelen die Laya
formaliseerbaar acht maar waarvoor geen template bestaat — precies de werklijst voor
nieuwe templates én de V4-jurist.

**Gouden meetlat.** Kruisinstrument: getraind op Eindhoven, geëvalueerd op álle Utrechtse
artikelen (en vice versa). Pas bij een gate-pas-rate én accuracy boven de
zero-shot-baseline op ongesehen instrumenten is de claim "werkt ook voor een nieuwe
gemeente" geldig. Implementatie: [plan](superpowers/plans/2026-11-08-laya-formalisatie-poortwachter.md).

### Inzet B — Kennisbank-router (bestaat deels; aanscherpen)

**Wat.** De bestaande `deep-agents/laya_router` routeert verzoeken al (primary_poc,
workflow, critic; 0,96 accuracy na fine-tune). Aanscherping: de vraag-set uitbreiden met
**laagkeuze** — annotatie (`dso_kb`-plekinfo) / toets (RegelRecht-puntvraag) / STTR
(officiële activiteit-conclusie) / verkenning (what-if) — zodat een "mag ik…"-vraag
vanaf de eerste milliseconde de juiste laag kiest in plaats van alleen het juiste
instrument.

**Waarom.** Dit is Tab 7's vierlagen-doctrine als voordeur; de S2-handoff-contracten
(payload + "geen nieuwe cijfers"-badge) staan al in het Breda System-2-ontwerp en zijn
1-op-1 herbruikbaar.

### Inzet C — bp2op-triage in de omzettabel (bestaat; koppelen)

**Wat.** `laya_bp2op` is al getraind (311 bronregels; `doel_hoofdstuk`, `match_band`,
`needs_jurist`) maar de voorspellingen staan nog los van de omzettabel-UX. Koppel
`predictions.json` aan de werklijst: rijen met `needs_jurist=true` en
`match_band≥mogelijk` bovenaan de V4-wachtrij; `match_band=geen` direct naar
"nieuwe regel voorstellen". Dit is de S1-helft van het Eindhovense equivalentie-orakel
(het orakel zelf blijft de engine: zelfde feiten door bron- en doelregel, outputs
vergelijken).

### Inzet D — STTR-onderhoudswacht (later, klein houden)

**Wat.** Signaal-laag op de RTR-cache: vraagtekst-patroonherkenning (de
`contains(?, "Dakkapel")`-expressies uit de 162 Eindhovense bestanden) om
leveranciersdrift en anonieme metadata te vlaggen. **Eerlijk:** versiedrift en
structuurfouten zijn deterministisch parseerbaar (dat doet de sttr-index al); Laya komt
alléén in beeld voor tekstpatronen. Klein houden of laten.

## Expres níet (doctrine-grens)

- **Geen beslislijn**: DSO "bepalen conclusie" en de RegelRecht-engine blijven
  deterministisch; de enum-vertaling (boolean toets ↔ `Vergunningplicht`-enum) blijft een
  juridische beslissing.
- **Geen nieuwe claims**: Laya distilleert bestaande oordelen uit run-artefacten — het is
  snelheid en rust, geen wijsheid; onder de gate zwijgt het.
- **Geen productie-deploy van dit checkpoint**: macOS/MLX is labtaal; voor een landelijke
  voorziening geldt het *patroon* (klein, lokaal, gekalibreerd, gate), niet dit model.

## Beheer en herhaalbaarheid

| Onderwerp | Afspraak |
|---|---|
| Checkpoints | buiten git (`.gitignore`, bestaand beleid); sha256 van checkpoint én dataset in elk uitvoer-artefact |
| Data lake | train/eval + manifest naar `silver/<spoor>/laya/system1/{datasetId}/`, predictions + summary naar `gold/…` (medallion zoals Breda) |
| Eval-protocol | per inzet een vast eval-script met held-out split; rapport in `eval-report.json`; gate-pas-rate altijd naast accuracy (overconfidence is de valkuil — stock-checkpoints zijn over-confident) |
| Koppeling migratiefases | A→fase 1 (corpus/draft-conversions versnellen) · B→fase 5 (kennisbank) · C→fase 3 (equivalentie-orakel) · D→fase 5 (RTR-onderhoud) |

## Volgorde van werk

1. **Nu:** Inzet A bouwen (plan klaar) — dataset uit de twee reports, fine-tune (~15–25 min
   op M3 Max), kruisinstrument-eval, gate-module in `full_export` met apart
   `laya-hints/v1`-artefact (het formalization-report-contract blijft onaangetast).
2. **Daarna:** Inzet C koppelen (klein, puur UI/werklijstwerk), Inzet B aanscherpen
   (vraag-set + laagkeuze), Inzet D pas als de RTR-productie-toegang er is (fase 5).
3. **Doorlopend:** elke nieuwe canonieke run levert gratis nieuwe trainingsdata — de
   datasetbouwers zijn deterministisch, dus hertrainen is een commando, geen project.
